"""Scrape BSE corporate announcements for ALL listed companies.

    python -m backend.news.bse_news            # today (incremental)
    python -m backend.news.bse_news --days 3   # backfill last 3 days

Exchange filings are the primary source: under SEBI LODR, companies must
disclose price-sensitive events to the exchanges first, before the media.

How it works:
- BSE's announcements API only returns all companies for a single day, 50 rows
  per page, newest first. So we walk day by day, page by page.
- On the incremental run we stop paging as soon as a page holds a filing we
  already stored - everything after it is older and already saved.
- Rows are deduped on BSE's NEWSID and only the last KEEP_DAYS days are kept.
- `ticker` is filled when the filing belongs to a stock in stocks.csv.

Output: BSE_NEWS_FILE (data/bronze/bse_news.csv), newest first.
"""

import argparse
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from urllib.parse import urlencode

import pandas as pd

from backend.config import BSE_NEWS_FILE, STOCKS_FILE

logger = logging.getLogger("backend.news")

API_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
ATTACH_URL = "https://www.bseindia.com/xml-data/corpfiling/{folder}/{name}"
# BSE rejects requests that don't look like they come from bseindia.com.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.5",
    "Origin": "https://www.bseindia.com",
    "Referer": "https://www.bseindia.com/",
    "Sec-Fetch-Site": "same-site",
}
KEEP_DAYS = 7
PAGE_DELAY_S = 1.0
MAX_PAGES_PER_DAY = 100  # ~1,800 filings/day = ~36 pages; guard against loops

COLUMNS = [
    "id", "published_at", "ticker", "scrip_code", "company_name", "category",
    "subcategory", "subject", "headline", "pdf_url", "is_critical", "is_routine",
]

# Compliance boilerplate that rarely moves a stock (case-insensitive substring).
ROUTINE_KEYWORDS = (
    "trading window", "74 (5)", "74(5)", "loss of share", "duplicate share",
    "duplicate certificate", "newspaper publication", "investor complaints",
    "compliance certificate", "scrutinizer", "book closure",
)


# ------------------------------------------------------------------
# Fetch + parse
# ------------------------------------------------------------------

def _get_json(url):
    """GET a BSE API URL with Scrapling and decode the JSON body."""
    from scrapling.fetchers import Fetcher  # lazy: only needed for live runs

    page = Fetcher.get(url, headers=HEADERS, timeout=30)
    if page.status != 200:
        raise RuntimeError(f"HTTP {page.status} for {url}")
    body = page.body
    return json.loads(body.decode() if isinstance(body, bytes) else body)


def page_url(day, page_no):
    d = day.strftime("%Y%m%d")
    params = {
        "pageno": page_no, "strCat": -1, "subcategory": -1, "strPrevDate": d,
        "strToDate": d, "strSearch": "P", "strscrip": "", "strType": "C",
    }
    return f"{API_URL}?{urlencode(params)}"


def _clean(text):
    text = str(text or "").replace("<BR>", " ").replace("<br>", " ").replace("''", "'")
    return " ".join(text.split())


# Headlines that just point at the PDF carry no information.
_EMPTY_HEADLINE = re.compile(r"^(please )?(refer|find)\b.*(enclosed|attached)|^intimation attached", re.I)


def _norm_name(name):
    """'Bajaj Electricals Ltd-$' / 'Bajaj Electricals Ltd.' -> 'bajaj electricals'."""
    name = re.sub(r"[^a-z0-9& ]", " ", str(name).lower())
    name = re.sub(r"\b(ltd|limited|the)\b", " ", name)
    return " ".join(name.split())


def ticker_lookup(stocks_path=STOCKS_FILE):
    """{bse symbol or normalized company name: ticker} for our stock universe."""
    if not os.path.exists(stocks_path):
        return {}
    stocks = pd.read_csv(stocks_path, dtype=str)
    lookup = {}
    for ticker, name in zip(stocks["ticker"], stocks["company_name"]):
        lookup[ticker.upper().removesuffix(".NS").lower()] = ticker
        lookup[_norm_name(name)] = ticker
    return lookup


def _bse_symbol(nsurl):
    """.../stock-share-price/bajaj-electricals-ltd/bajajelec/500031/ -> 'bajajelec'."""
    parts = [p for p in str(nsurl or "").split("/") if p]
    return parts[-2].lower() if len(parts) >= 2 else ""


def parse_row(raw, lookup):
    subject = _clean(raw.get("NEWSSUB"))
    headline = _clean(raw.get("HEADLINE"))
    subcategory = _clean(raw.get("SUBCATNAME"))
    name = _clean(raw.get("SLONGNAME"))
    attachment = (raw.get("ATTACHMENTNAME") or "").strip()
    folder = "AttachHis" if int(raw.get("PDFFLAG") or 0) == 1 else "AttachLive"
    blob = f"{subject} {headline} {subcategory}".lower()
    published = str(raw.get("DissemDT") or raw.get("NEWS_DT") or "")[:19].replace("T", " ")
    return {
        "id": str(raw["NEWSID"]).strip(),
        "published_at": published,
        "ticker": lookup.get(_bse_symbol(raw.get("NSURL"))) or lookup.get(_norm_name(name), ""),
        "scrip_code": str(raw.get("SCRIP_CD") or "").strip(),
        "company_name": name.removesuffix("-$").strip(),
        "category": _clean(raw.get("CATEGORYNAME")),
        "subcategory": subcategory,
        "subject": subject,
        "headline": "" if _EMPTY_HEADLINE.search(headline) else headline,
        "pdf_url": ATTACH_URL.format(folder=folder, name=attachment) if attachment else "",
        "is_critical": str(raw.get("CRITICALNEWS") or "0").strip() == "1",
        "is_routine": any(k in blob for k in ROUTINE_KEYWORDS),
    }


# ------------------------------------------------------------------
# Storage
# ------------------------------------------------------------------

def load_bse_news(path=BSE_NEWS_FILE):
    if not os.path.exists(path):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    for col in ("is_critical", "is_routine"):
        df[col] = df[col].str.lower() == "true"
    return df


def save_bse_news(df, path=BSE_NEWS_FILE, keep_days=KEEP_DAYS, now=None):
    cutoff = ((now or datetime.now()) - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    df = df[df["published_at"] >= cutoff]
    df = df.drop_duplicates("id", keep="first").sort_values("published_at", ascending=False)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.tmp"
    df[COLUMNS].to_csv(tmp, index=False)
    os.replace(tmp, path)  # atomic: readers never see a half-written file
    return df


# ------------------------------------------------------------------
# Run
# ------------------------------------------------------------------

def fetch_day(day, known_ids, lookup, fetch=_get_json, full=False, sleep=time.sleep):
    """New filings for one day, newest first. Stops at the first known filing
    unless `full` is set (use that to repair a run that was cut short)."""
    rows, seen = [], 0
    for page_no in range(1, MAX_PAGES_PER_DAY + 1):
        if page_no > 1:
            sleep(PAGE_DELAY_S)
        data = fetch(page_url(day, page_no))
        table = (data or {}).get("Table") or []
        if not table:
            break
        seen += len(table)
        fresh = [r for r in (parse_row(raw, lookup) for raw in table) if r["id"] not in known_ids]
        rows += fresh
        total = int(((data.get("Table1") or [{}])[0]).get("ROWCNT") or 0)
        if (len(fresh) < len(table) and not full) or seen >= total:
            break
    return rows


def run(days=2, full=False, fetch=_get_json, path=BSE_NEWS_FILE,
        stocks_path=STOCKS_FILE, sleep=time.sleep, now=None):
    """Fetch the last `days` days (today included) and merge into the CSV."""
    now = now or datetime.now()
    existing = load_bse_news(path)
    known = set(existing["id"])
    lookup = ticker_lookup(stocks_path)

    new_rows, errors = [], 0
    for offset in range(days):
        day = now - timedelta(days=offset)
        try:
            rows = fetch_day(day, known, lookup, fetch=fetch, full=full, sleep=sleep)
        except Exception as exc:
            errors += 1
            logger.warning("BSE %s: stopped early: %s", f"{day:%Y-%m-%d}", exc)
            continue
        new_rows += rows
        known.update(r["id"] for r in rows)

    merged = pd.concat([pd.DataFrame(new_rows, columns=COLUMNS), existing], ignore_index=True)
    saved = save_bse_news(merged, path, now=now)
    summary = {
        "new": len(new_rows),
        "new_for_our_stocks": sum(1 for r in new_rows if r["ticker"]),
        "stored": len(saved),
        "errors": errors,
    }
    logger.info("BSE news done: %s", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Scrape BSE corporate announcements.")
    parser.add_argument("--days", type=int, default=2,
                        help="Days to walk back, today included (default %(default)s).")
    parser.add_argument("--full", action="store_true",
                        help="Walk every page instead of stopping at known filings.")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(run(days=args.days, full=args.full))


if __name__ == "__main__":
    main()
