"""AI stock analysis endpoint.

Runs the existing LangChain stock agent and caches its answer per
(stock, features mtime): the analysis is only stale after a data refresh,
and Ollama runs are slow + non-deterministic, so we never want to redo one
on a plain page reload.
"""

import os
import threading

from fastapi import APIRouter, HTTPException

from backend.api import stocks
from backend.config import settings

router = APIRouter(prefix="/api")

_cache = {}
_lock = threading.Lock()


def invalidate() -> None:
    with _lock:
        _cache.clear()

PROMPT = (
    "Analyze {name} ({ticker}). Use the stock data tools. Give: 1) current "
    "technical picture (trend vs MA20/MA50, volatility, 52w position), 2) "
    "fundamental read (debt levels, cash ratio), 3) what recent news implies, "
    "4) a clear BUY / HOLD / SELL call with conviction and key risks. "
    "Keep it under 250 words."
)


@router.get("/stocks/{stock_id}/analysis")
def get_analysis(stock_id: int, refresh: bool = False):
    profile = stocks.enriched_df()
    row = profile[profile["stock_id"] == stock_id]
    if row.empty:
        raise HTTPException(404, f"Unknown stock_id={stock_id}")
    row = row.iloc[0]

    mtime = os.path.getmtime(settings.FEATURES_FILE)
    key = (stock_id, mtime)
    if not refresh:
        with _lock:
            if key in _cache:
                return _cache[key]

    from backend.agents.stock_agent import query_stock_info

    query = PROMPT.format(name=row["company_name"], ticker=row["ticker"])
    try:
        analysis = query_stock_info(query)
    except Exception as exc:
        raise HTTPException(502, f"AI analysis failed: {exc}") from exc

    result = {
        "stock_id": stock_id,
        "ticker": row["ticker"],
        "company_name": row["company_name"],
        "analysis": analysis,
        "generated_at": mtime,
    }
    with _lock:
        _cache[key] = result
    return result
