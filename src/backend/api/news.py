"""News endpoints over the BSE announcements DuckDB (news/ pipeline).

Short-lived read-only connections: the ingest scheduler holds the writer
lock in another process, and db.connect retries briefly.
"""

from fastapi import APIRouter

from backend.news import db, fetch

router = APIRouter(prefix="/api")

COLUMN_SQL = ", ".join(db.COLUMNS)


def _rows(sql: str, params=None, limit: int = 30) -> list:
    try:
        with db.connect(read_only=True) as con:
            cur = con.execute(sql, params or [])
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchmany(limit)]
    except FileNotFoundError:
        return []


def _serialize(rows: list) -> list:
    out = []
    for r in rows:
        item = {}
        for key, value in r.items():
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            elif hasattr(value, "item"):
                value = value.item()
            item[key] = value
        out.append(item)
    return out


@router.get("/news")
def get_news(symbol: str | None = None, limit: int = 20):
    if symbol:
        where = "WHERE UPPER(symbol) = ? OR company_name ILIKE ?"
        params = [symbol.upper(), f"%{symbol}%"]
    else:
        where = ""
        params = []
    rows = _rows(
        f"SELECT {COLUMN_SQL} FROM announcements {where} ORDER BY published_at DESC NULLS LAST",
        params,
        limit=min(max(limit, 1), 100),
    )
    return _serialize(rows)


@router.get("/news/summary/{ticker}")
def get_stock_news_summary(ticker: str):
    """Rolling per-stock headlines + LLM summary maintained by news/fetch."""
    df = fetch.load_news()
    if df.empty:
        return {"ticker": ticker, "headlines": [], "summary": None}
    row = df[df["ticker"].str.upper() == ticker.upper()]
    if row.empty:
        return {"ticker": ticker, "headlines": [], "summary": None}
    rec = row.iloc[0].to_dict()
    return {
        "ticker": ticker,
        "company": rec.get("company_name"),
        "headlines": rec.get("headlines") or [],
        "summary": rec.get("summary"),
        "updated_at": rec.get("updated_at"),
    }
