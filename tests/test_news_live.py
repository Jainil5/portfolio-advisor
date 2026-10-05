"""Opt-in end-to-end smoke test against the real BSE API: pytest -m live"""

import pandas as pd
import pytest

from backend.news import config, db, ingest, tools
from backend.news.client import open_bse
from backend.news.scrip_map import resolve

pytestmark = pytest.mark.live

SYMBOLS = ["TCS", "RELIANCE", "INFY"]


def test_live_end_to_end(tmp_path, monkeypatch):
    path = str(tmp_path / "news.duckdb")
    monkeypatch.setattr(config, "NEWS_DB_FILE", path)

    rows = []
    with open_bse() as bse:
        for sym in SYMBOLS:
            code, status = resolve(bse, sym)
            assert status == "resolved", sym
            rows.append({"symbol": sym, "company_name": sym, "scrip_code": code, "status": status})
    scrips = pd.DataFrame(rows)
    monkeypatch.setattr(ingest, "load_scrip_map", lambda: scrips)
    monkeypatch.setattr(tools, "load_scrip_map", lambda: scrips)

    summary = ingest.run(days=30, db_path=path)
    assert not summary["blocked"] and summary["errors"] == 0
    assert summary["fetched"] > 0

    again = ingest.run(days=30, db_path=path)
    assert again["new"] == 0

    out = tools.get_stock_news.invoke({"symbol": "TCS", "days": 30, "include_routine": True})
    assert "| date (IST) |" in out
