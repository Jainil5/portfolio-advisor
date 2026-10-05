"""Data-update job: POST /api/update_data runs the full refresh chain

    prices + fundamentals (update_pipeline) -> features -> recommendations
    -> per-stock news (best effort, RSS + LLM summary)

in a background thread, one job at a time. The frontend polls
/api/update_data/status for stage progress.
"""

import threading
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from backend.api import analysis, stocks

router = APIRouter(prefix="/api")

_state = {
    "status": "idle",  # idle | running | done | error
    "stage": None,
    "started_at": None,
    "finished_at": None,
    "error": None,
    "log": [],
}
_run_lock = threading.Lock()


def _stamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _log(msg: str) -> None:
    _state["log"].append(f"{_stamp()} {msg}")


def _run_job(include_news: bool) -> None:
    from backend.pipelines.features import generate_features
    from backend.pipelines.recommendations import generate_recommendations
    from backend.pipelines.update_pipeline import update_finance_data

    try:
        _state["stage"] = "prices"
        _log("Updating stock master, prices and fundamentals...")
        update_finance_data(force=True)

        _state["stage"] = "features"
        _log("Regenerating features...")
        generate_features()

        _state["stage"] = "recommendations"
        _log("Regenerating recommendations...")
        generate_recommendations()

        if include_news:
            _state["stage"] = "news"
            _log("Refreshing per-stock news...")
            try:
                from backend.news import fetch as news_fetch

                news_fetch.run()
            except Exception as exc:
                _log(f"News refresh failed (kept old data): {exc}")

        stocks.invalidate_cache()
        analysis.invalidate()
        _state["status"] = "done"
        _log("All datasets updated.")
    except Exception as exc:
        _state["status"] = "error"
        _state["error"] = str(exc)
        _log(f"Update failed: {exc}")
    finally:
        _state["stage"] = None
        _state["finished_at"] = _stamp()


@router.post("/update_data")
def update_data(include_news: bool = True):
    with _run_lock:
        if _state["status"] == "running":
            raise HTTPException(409, "An update is already running")
        _state.update(
            status="running",
            stage=None,
            started_at=_stamp(),
            finished_at=None,
            error=None,
            log=[],
        )
        threading.Thread(target=_run_job, args=(include_news,), daemon=True).start()
    return {"status": "running", "started_at": _state["started_at"]}


@router.get("/update_data/status")
def update_data_status():
    return dict(_state)
