"""DuckDB storage for BSE announcements.

Connections are short-lived on purpose: DuckDB allows one read-write process
at a time, and the scheduler (writer) and the agent (reader) run in
different processes. Readers retry briefly if the writer holds the lock.

Timestamps are stored as naive TIMESTAMPs in IST (BSE's own clock).
"""

import os
import time
from contextlib import contextmanager

import duckdb

from backend.news import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS announcements (
    id              VARCHAR PRIMARY KEY,   -- BSE NEWSID
    scrip_code      VARCHAR NOT NULL,
    symbol          VARCHAR,
    company_name    VARCHAR,
    headline        VARCHAR,
    subject         VARCHAR,
    category        VARCHAR,
    subcategory     VARCHAR,
    published_at    TIMESTAMP,             -- IST
    attachment_name VARCHAR,
    pdf_flag        INTEGER,
    pdf_url         VARCHAR,
    is_critical     BOOLEAN,
    is_routine      BOOLEAN,
    fetched_at      TIMESTAMP              -- IST, first time we saw it
)
"""

COLUMNS = [
    "id", "scrip_code", "symbol", "company_name", "headline", "subject",
    "category", "subcategory", "published_at", "attachment_name", "pdf_flag",
    "pdf_url", "is_critical", "is_routine", "fetched_at",
]

# Fields BSE can change after first publication (the PDF moves Live -> His).
UPDATABLE = ["pdf_flag", "pdf_url", "attachment_name", "category", "subcategory", "is_critical", "is_routine"]


@contextmanager
def connect(path=None, read_only=False, attempts=10, wait_s=0.5):
    path = path or config.NEWS_DB_FILE
    if read_only and not os.path.exists(path):
        raise FileNotFoundError(f"No news database at {path}. Run the ingest first.")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    for attempt in range(attempts):
        try:
            con = duckdb.connect(path, read_only=read_only)
            break
        except duckdb.IOException:
            if attempt == attempts - 1:
                raise
            time.sleep(wait_s)
    try:
        if not read_only:
            con.execute(SCHEMA)
        yield con
    finally:
        con.close()


def upsert(rows, path=None):
    """Insert announcements idempotently. Returns the number of new ids."""
    if not rows:
        return 0
    unique = {r["id"]: r for r in rows}  # DuckDB rejects duplicate keys within one statement
    values = [[r[c] for c in COLUMNS] for r in unique.values()]
    placeholders = ", ".join("?" for _ in COLUMNS)
    updates = ", ".join(f"{c} = excluded.{c}" for c in UPDATABLE)
    sql = (
        f"INSERT INTO announcements ({', '.join(COLUMNS)}) VALUES ({placeholders}) "
        f"ON CONFLICT (id) DO UPDATE SET {updates}"
    )
    with connect(path) as con:
        ids = list(unique)
        before = con.execute(
            "SELECT count(*) FROM announcements WHERE id IN (SELECT unnest(?))", [ids]
        ).fetchone()[0]
        con.executemany(sql, values)
    return len(ids) - before


def query(sql, params=None, path=None):
    """Run a read-only query and return a pandas DataFrame."""
    with connect(path, read_only=True) as con:
        return con.execute(sql, params or []).df()
