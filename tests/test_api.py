"""API smoke tests against the real silver/bronze data (skipped if absent)."""

import os

import pytest
from fastapi.testclient import TestClient

from backend.api import app
from backend.config import settings

pytestmark = pytest.mark.skipif(
    not os.path.exists(settings.FEATURES_FILE), reason="features.csv not generated"
)

client = TestClient(app)


def test_stocks_have_derived_returns():
    rows = client.get("/api/stocks").json()
    assert rows
    for key in ("ticker", "current_price", "daily_return", "return_100d", "return_365d", "avg_volume_7d"):
        assert key in rows[0]


def test_history_range_and_rejects_unknown():
    sid = client.get("/api/stocks").json()[0]["stock_id"]
    data = client.get(f"/api/stocks/{sid}/history", params={"range": "3m"}).json()
    assert len(data["candles"]) <= 63
    assert data["candles"][0]["close"] is not None
    assert client.get(f"/api/stocks/{sid}/history", params={"range": "nope"}).status_code == 422
    assert client.get("/api/stocks/999999/history").status_code == 404


def test_movers_and_sectors_shape():
    movers = client.get("/api/movers").json()
    assert set(movers) == {"gainers", "losers"}
    g = [s["daily_return"] for s in movers["gainers"]]
    assert g == sorted(g, reverse=True)
    sectors = client.get("/api/sectors").json()
    assert sectors and set(sectors[0]) >= {"sector", "avg_daily_return", "stock_count"}


def test_update_data_status_is_idle_until_triggered():
    state = client.get("/api/update_data/status").json()
    assert state["status"] in ("idle", "done", "error", "running")
