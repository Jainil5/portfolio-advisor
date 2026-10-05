"""Fetch BSE corporate announcements for mapped stocks into DuckDB.

    python -m backend.news.ingest --days 2
    python -m backend.news.ingest --days 7 --symbols TCS,INFY

Requires data/scrip_map.csv (see backend.news.scrip_map).
Re-running is safe: rows are upserted on BSE's NEWSID.
"""

import argparse
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from backend.news import config, db
from backend.news.client import (
    BSEBlocked,
    attachment_url,
    call_with_retry,
    logger,
    open_bse,
    setup_logging,
)
from backend.news.scrip_map import load_scrip_map

IST = ZoneInfo(config.TIMEZONE)


def is_routine(*texts, keywords=config.ROUTINE_KEYWORDS):
    """True if any routine-compliance keyword appears in any of the texts."""
    blob = " ".join(t for t in texts if t).lower()
    return any(k in blob for k in keywords)


def _clean(text):
    return " ".join(str(text or "").replace("<BR>", " ").replace("<br>", " ").split())


def parse_announcement(raw, symbol="", company_name="", fetched_at=None):
    """Map one BSE `Table` row (field names verified against live data) to a DB row."""
    subject = _clean(raw.get("NEWSSUB"))
    headline = _clean(raw.get("HEADLINE"))
    subcategory = _clean(raw.get("SUBCATNAME"))
    pdf_flag = int(raw.get("PDFFLAG") or 0)
    attachment = (raw.get("ATTACHMENTNAME") or "").strip()
    published = pd.to_datetime(raw.get("DT_TM") or raw.get("NEWS_DT"), errors="coerce")
    return {
        "id": str(raw["NEWSID"]).strip(),
        "scrip_code": str(raw["SCRIP_CD"]).strip(),
        "symbol": symbol,
        "company_name": company_name or _clean(raw.get("SLONGNAME")),
        "headline": headline,
        "subject": subject,
        "category": _clean(raw.get("CATEGORYNAME")),
        "subcategory": subcategory,
        "published_at": None if pd.isna(published) else published.to_pydatetime(),
        "attachment_name": attachment,
        "pdf_flag": pdf_flag,
        "pdf_url": attachment_url(attachment, pdf_flag),
        "is_critical": str(raw.get("CRITICALNEWS") or "0").strip() == "1",
        "is_routine": is_routine(subject, headline, subcategory),
        "fetched_at": fetched_at or datetime.now(IST).replace(tzinfo=None),
    }


def fetch_scrip(bse, scrip_code, from_date, to_date, sleep=time.sleep):
    """All announcement rows for one scrip in a date range, following pagination."""
    rows, page = [], 1
    while True:
        res = call_with_retry(
            bse.announcements, page_no=page, from_date=from_date, to_date=to_date,
            scripcode=scrip_code, what=f"announcements({scrip_code}, p{page})",
        )
        table = res.get("Table") or []
        rows.extend(table)
        total = int(((res.get("Table1") or [{}])[0]).get("ROWCNT") or 0)
        if not table or len(rows) >= total:
            return rows
        page += 1
        sleep(config.INGEST_DELAY_S)


def run(days=config.SCHEDULED_LOOKBACK_DAYS, symbols=None, db_path=None, sleep=time.sleep):
    """Ingest the last `days` days for all mapped (or the given) symbols.

    Returns a summary dict. Never raises on BSE errors - they are logged.
    """
    scrips = load_scrip_map()
    if scrips.empty:
        logger.error("No resolved scrips in %s. Run scrip_map first.", config.SCRIP_MAP_FILE)
        return {"stocks": 0, "fetched": 0, "new": 0, "errors": 0, "blocked": False}

    if symbols:
        wanted = {s.strip().upper().removesuffix(".NS") for s in symbols if s.strip()}
        missing = wanted - set(scrips["symbol"].str.upper())
        if missing:
            logger.warning("Not in scrip map (or unresolved): %s", ", ".join(sorted(missing)))
        scrips = scrips[scrips["symbol"].str.upper().isin(wanted)]

    now = datetime.now(IST).replace(tzinfo=None)
    from_date, to_date = now - timedelta(days=days), now
    logger.info("Ingest start: %d stocks, %s -> %s", len(scrips), f"{from_date:%Y-%m-%d}", f"{to_date:%Y-%m-%d}")

    rows, errors, blocked = [], 0, False
    with open_bse() as bse:
        for i, s in enumerate(scrips.itertuples(index=False)):
            if i:
                sleep(config.INGEST_DELAY_S)
            try:
                raw = fetch_scrip(bse, s.scrip_code, from_date, to_date, sleep=sleep)
            except BSEBlocked:
                blocked = True
                break
            except Exception as exc:
                errors += 1
                logger.warning("%s (%s): giving up for this run: %s", s.symbol, s.scrip_code, exc)
                continue
            rows.extend(parse_announcement(r, s.symbol, s.company_name, now) for r in raw)

    new = db.upsert(rows, path=db_path)
    summary = {"stocks": len(scrips), "fetched": len(rows), "new": new, "errors": errors, "blocked": blocked}
    logger.info("Ingest done: %s", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Fetch BSE announcements into DuckDB.")
    parser.add_argument("--days", type=int, default=config.SCHEDULED_LOOKBACK_DAYS,
                        help="Backfill window in days (default %(default)s).")
    parser.add_argument("--symbols", type=lambda s: s.split(","), default=None,
                        help="Comma-separated NSE symbols, e.g. TCS,INFY (default: all mapped).")
    args = parser.parse_args()
    setup_logging()
    run(days=args.days, symbols=args.symbols)


if __name__ == "__main__":
    main()
