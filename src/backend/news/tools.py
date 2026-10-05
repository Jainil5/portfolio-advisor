"""LangChain tools for the news-analyst subagent (read-only over DuckDB)."""

import difflib
import io
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from langchain.tools import tool
from pypdf import PdfReader

from backend.news import config, db
from backend.news.scrip_map import load_scrip_map

IST = ZoneInfo(config.TIMEZONE)
_ATTACH_RE = re.compile(
    rf"^{re.escape(config.ATTACHMENT_BASE)}/({config.ATTACH_LIVE}|{config.ATTACH_HIS})/([\w\-.]+\.pdf)$",
    re.IGNORECASE,
)
_BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Accept": "application/pdf,*/*",
    "Referer": "https://www.bseindia.com/",
}


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _now():
    return datetime.now(IST).replace(tzinfo=None)


def resolve_stock(query, scrips=None):
    """Return (symbol, company_name, scrip_code) for an NSE symbol or company name, else None."""
    scrips = load_scrip_map() if scrips is None else scrips
    if scrips.empty or not query or not query.strip():
        return None
    q = query.strip().upper().removesuffix(".NS")
    sym = scrips[scrips["symbol"].str.upper() == q]
    if sym.empty:
        names = scrips["company_name"].str.upper()
        sym = scrips[names.str.contains(re.escape(q), na=False)]
    if sym.empty:
        choices = {n.upper(): i for i, n in zip(scrips.index, scrips["company_name"])}
        choices.update({s.upper(): i for i, s in zip(scrips.index, scrips["symbol"])})
        close = difflib.get_close_matches(q, list(choices), n=1, cutoff=0.6)
        if close:
            sym = scrips.loc[[choices[close[0]]]]
    if sym.empty:
        return None
    row = sym.iloc[0]
    return row["symbol"], row["company_name"], row["scrip_code"]


def _cell(value, limit=160):
    text = " ".join(str(value or "").split()).replace("|", "/")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def format_table(df, with_symbol=False):
    """Compact markdown table: date, [symbol], category, headline, pdf_url."""
    header = ["date (IST)"] + (["symbol"] if with_symbol else []) + ["category", "headline", "pdf_url"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in df.itertuples(index=False):
        category = " / ".join(x for x in (r.category, r.subcategory) if x)
        if r.is_critical:
            category += " [BSE critical]"
        if r.is_routine:
            category += " [routine]"
        cells = [f"{r.published_at:%Y-%m-%d %H:%M}"]
        if with_symbol:
            cells.append(r.symbol)
        cells += [_cell(category, 80), _cell(r.headline or r.subject), r.pdf_url or "-"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


_SELECT = """
SELECT published_at, symbol, category, subcategory, headline, subject,
       pdf_url, is_critical, is_routine
FROM announcements
"""


def _safe_query(sql, params):
    try:
        return db.query(sql, params), None
    except FileNotFoundError as exc:
        return None, str(exc)
    except Exception as exc:  # lock held too long, corrupt file, ...
        return None, f"News database unavailable: {exc}"


# ------------------------------------------------------------------
# Tools
# ------------------------------------------------------------------

@tool
def get_stock_news(symbol: str, days: int = 3, include_routine: bool = False) -> str:
    """
    List BSE corporate announcements (results, dividends, board meetings,
    orders, acquisitions, management changes, ...) for ONE stock.

    Args:
        symbol: NSE symbol (e.g. "TCS", "RELIANCE") or company name
            (e.g. "Tata Consultancy"); fuzzy-matched against the tracked stocks.
        days: How many days back to look (default 3, max 90).
        include_routine: Include routine compliance filings (trading-window
            closures, share-certificate losses, newspaper ads, ...). Default False.

    Returns a markdown table (newest first) with date, category, headline and
    pdf_url. "[BSE critical]" marks filings BSE itself flags as critical.
    Use read_filing(pdf_url) when a headline is too vague to understand.
    """
    match = resolve_stock(symbol)
    if not match:
        return f"'{symbol}' is not one of the tracked stocks (or has no BSE scrip code)."
    sym, name, code = match
    days = max(1, min(int(days), 90))
    sql = _SELECT + "WHERE scrip_code = ? AND published_at >= ?"
    if not include_routine:
        sql += " AND NOT is_routine"
    sql += " ORDER BY published_at DESC LIMIT ?"
    df, err = _safe_query(sql, [code, _now() - timedelta(days=days), config.LATEST_ALL_MAX_ROWS])
    if err:
        return err
    title = f"{name} ({sym}, BSE {code}) - last {days} day(s)"
    if df.empty:
        extra = "" if include_routine else " (routine filings excluded)"
        return f"{title}: no announcements found{extra}."
    return f"{title}:\n\n{format_table(df)}"


@tool
def get_latest_news_all(hours: int = 24, include_routine: bool = False) -> str:
    """
    List the latest BSE corporate announcements across ALL tracked stocks,
    newest first, capped at 50 rows. Use this for "what's new today?" or
    "any important filings in my stocks?" style questions.

    Args:
        hours: Look-back window in hours (default 24, max 336).
        include_routine: Include routine compliance filings. Default False.
    """
    hours = max(1, min(int(hours), 336))
    sql = _SELECT + "WHERE published_at >= ?"
    if not include_routine:
        sql += " AND NOT is_routine"
    sql += " ORDER BY published_at DESC LIMIT ?"
    df, err = _safe_query(sql, [_now() - timedelta(hours=hours), config.LATEST_ALL_MAX_ROWS])
    if err:
        return err
    if df.empty:
        return f"No announcements in the last {hours} hour(s)."
    note = f" (showing newest {config.LATEST_ALL_MAX_ROWS})" if len(df) == config.LATEST_ALL_MAX_ROWS else ""
    return f"Announcements in the last {hours} hour(s){note}:\n\n{format_table(df, with_symbol=True)}"


def _download_pdf(folder, name):
    """Fetch a filing, trying the other Live/His folder on 404 (filings move as they age)."""
    other = config.ATTACH_HIS if folder.lower() == config.ATTACH_LIVE.lower() else config.ATTACH_LIVE
    last = None
    for f in (folder, other):
        url = f"{config.ATTACHMENT_BASE}/{f}/{name}"
        resp = requests.get(url, headers=_BROWSER_HEADERS, timeout=config.HTTP_TIMEOUT_S)
        if resp.ok and resp.content[:5] == b"%PDF-":
            return resp.content
        last = f"HTTP {resp.status_code}"
    raise RuntimeError(f"could not download {name} ({last})")


@tool
def read_filing(pdf_url: str, max_chars: int = 15000) -> str:
    """
    Download a BSE filing PDF (a pdf_url returned by get_stock_news or
    get_latest_news_all) and return its extracted text, truncated to
    max_chars. Use it when a headline is vague (e.g. "Press Release",
    "Outcome of Board Meeting") to find out what actually happened.
    Only bseindia.com corpfiling URLs are accepted.
    """
    m = _ATTACH_RE.match((pdf_url or "").strip())
    if not m:
        return "read_filing only accepts BSE filing URLs like https://www.bseindia.com/xml-data/corpfiling/AttachLive/<file>.pdf"
    folder, name = m.groups()
    max_chars = max(500, min(int(max_chars), 100_000))

    os.makedirs(config.FILINGS_DIR, exist_ok=True)
    pdf_path = os.path.join(config.FILINGS_DIR, name)
    txt_path = pdf_path[:-4] + ".txt"

    if os.path.exists(txt_path):
        with open(txt_path, encoding="utf-8") as fh:
            text = fh.read()
    else:
        try:
            if not os.path.exists(pdf_path):
                data = _download_pdf(folder, name)
                with open(pdf_path, "wb") as fh:
                    fh.write(data)
            reader = PdfReader(pdf_path)
            text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        except Exception as exc:
            return f"Could not read filing {name}: {exc}"
        with open(txt_path, "w", encoding="utf-8") as fh:
            fh.write(text)

    if not text.strip():
        return (f"Filing {name} has no extractable text (likely a scanned image PDF). "
                f"Open it manually: {pdf_url}")
    if len(text) > max_chars:
        return text[:max_chars] + f"\n\n[... truncated, {len(text) - max_chars} more characters]"
    return text


NEWS_TOOLS = [get_stock_news, get_latest_news_all, read_filing]
