"""Stock endpoints: screener dataset, movers/sectors summaries, price
history and per-stock profile.

The screener table needs 100D/365D % changes that features.csv doesn't
carry. They are derived from the bronze price history once per data
refresh and cached, keyed on the features file mtime, so /api/stocks
stays fast and a pipeline run invalidates it automatically.
"""

import os
import threading

import pandas as pd
from fastapi import APIRouter, HTTPException

from backend.api.util import records
from backend.config import settings
from backend.data import repository

router = APIRouter(prefix="/api")

# Calendar-day ranges sliced from the tail of each stock's OHLCV history.
RANGES = {"1w": 5, "1m": 21, "3m": 63, "6m": 126, "1y": 250, "3y": 750, "5y": 1250}

_enrich_cache = {"mtime": None, "df": None}
_enrich_lock = threading.Lock()


def _price_file(stock_id: int) -> str | None:
    prefix = f"{stock_id}_"
    try:
        for fname in os.listdir(settings.PRICE_DIR):
            if fname.startswith(prefix) and fname.endswith(".csv"):
                return os.path.join(settings.PRICE_DIR, fname)
    except FileNotFoundError:
        return None
    return None


def _price_history(stock_id: int) -> pd.DataFrame:
    path = _price_file(stock_id)
    if path is None:
        return pd.DataFrame()
    df = repository.read_csv_cached(path)
    if df.empty or "Close" not in df.columns:
        return pd.DataFrame()
    return df.dropna(subset=["Close"]).sort_values("Date").reset_index(drop=True)


def _pct_change_over(history: pd.DataFrame, rows: int):
    closes = history["Close"]
    if len(closes) <= rows:
        if len(closes) < 2:
            return None
        rows = len(closes) - 1
    first, last = closes.iloc[-rows - 1], closes.iloc[-1]
    if not first:
        return None
    return round((last / first - 1) * 100, 2)


def enriched_df() -> pd.DataFrame:
    """features.csv + return_100d/return_365d, cached per features mtime."""
    mtime = os.path.getmtime(settings.FEATURES_FILE)
    with _enrich_lock:
        if _enrich_cache["mtime"] != mtime or _enrich_cache["df"] is None:
            df = repository.load_features_df().copy()
            hist_100 = {}
            hist_365 = {}
            for sid in df["stock_id"]:
                history = _price_history(int(sid))
                hist_100[int(sid)] = _pct_change_over(history, 100)
                hist_365[int(sid)] = _pct_change_over(history, 250)  # trading days in a year
            df["return_100d"] = df["stock_id"].map(hist_100)
            df["return_365d"] = df["stock_id"].map(hist_365)
            _enrich_cache.update(mtime=mtime, df=df)
        return _enrich_cache["df"]


def invalidate_cache() -> None:
    with _enrich_lock:
        _enrich_cache.update(mtime=None, df=None)


def data_updated_at() -> str | None:
    try:
        return pd.Timestamp(os.path.getmtime(settings.FEATURES_FILE), unit="s", tz="UTC").isoformat()
    except FileNotFoundError:
        return None


@router.get("/stocks")
def get_stocks():
    return records(enriched_df())


@router.get("/movers")
def get_movers(limit: int = 5):
    df = enriched_df()
    df = df.dropna(subset=["daily_return"]).sort_values("daily_return")
    top = df.tail(limit).iloc[::-1]
    losers = df.head(limit)
    return {"gainers": records(top), "losers": records(losers)}


@router.get("/sectors")
def get_sectors():
    df = enriched_df()
    agg = (
        df.dropna(subset=["daily_return"])
        .groupby("sector", as_index=False)
        .agg(
            avg_daily_return=("daily_return", "mean"),
            stock_count=("ticker", "count"),
        )
        .sort_values("avg_daily_return", ascending=False)
    )
    agg["avg_daily_return"] = agg["avg_daily_return"].round(2)
    return records(agg)


@router.get("/stocks/{stock_id}/history")
def get_history(stock_id: int, range: str = "1y"):
    if range not in RANGES:
        raise HTTPException(422, f"range must be one of {', '.join(RANGES)}")
    history = _price_history(stock_id)
    if history.empty:
        raise HTTPException(404, f"No price history for stock_id={stock_id}")
    tail = history.tail(RANGES[range])
    out = []
    for row in tail.to_dict(orient="records"):
        out.append(
            {
                "date": str(pd.to_datetime(row["Date"]).date()),
                "open": row.get("Open"),
                "high": row.get("High"),
                "low": row.get("Low"),
                "close": row.get("Close"),
                "volume": row.get("Volume"),
            }
        )
    return {"stock_id": stock_id, "range": range, "candles": out}


@router.get("/stocks/{stock_id}/profile")
def get_profile(stock_id: int):
    df = enriched_df()
    row = df[df["stock_id"] == stock_id]
    if row.empty:
        raise HTTPException(404, f"Unknown stock_id={stock_id}")
    return records(row)[0]
