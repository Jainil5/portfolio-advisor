"""Incremental price ingestion: gap fill, last-day refresh, and append."""

from datetime import date

import pandas as pd

from backend.pipelines import ingest

ROW = {"yahoo_ticker": "TEST.NS", "stock_id": 7, "company_name": "Test Co"}
COLUMNS = ["Date", "Open", "High", "Low", "Close", "Volume", "Dividends", "Stock Splits", "stock_id"]


def _history(days, close=100.0):
    """Fake yfinance history frame: tz-aware IST index, one bar per day."""
    index = pd.DatetimeIndex(pd.to_datetime(days), name="Date").tz_localize("Asia/Kolkata")
    n = len(days)
    return pd.DataFrame(
        {
            "Open": [close] * n,
            "High": [close] * n,
            "Low": [close] * n,
            "Close": [close + i for i in range(n)],
            "Volume": [1000] * n,
            "Dividends": [0.0] * n,
            "Stock Splits": [0.0] * n,
        },
        index=index,
    )


class FakeTicker:
    calls = []
    frame = None

    def __init__(self, ticker):
        pass

    def history(self, **kwargs):
        FakeTicker.calls.append(kwargs)
        return FakeTicker.frame


def _setup(monkeypatch, frame, today):
    FakeTicker.calls = []
    FakeTicker.frame = frame
    monkeypatch.setattr(ingest.yf, "Ticker", FakeTicker)

    class FakeDatetime:
        @staticmethod
        def now(tz=None):
            return pd.Timestamp(today).to_pydatetime()

    monkeypatch.setattr(ingest, "datetime", FakeDatetime)


def _write_existing(path, rows):
    pd.DataFrame(rows, columns=COLUMNS).to_csv(path, index=False)


def test_fills_gap_and_replaces_partial_last_day(tmp_path, monkeypatch):
    path = tmp_path / "7_Test_Co.csv"
    _write_existing(path, [
        ["2026-09-24", 90, 90, 90, 90.0, 500, 0.0, 0.0, 7],
        ["2026-09-25", 95, 95, 95, 95.0, 500, 0.0, 0.0, 7],  # partial intraday candle
    ])
    # Missed 25 (final values), 26-27 weekend, then 28-30 Sep, 1-2 Oct.
    days = ["2026-09-25", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02"]
    _setup(monkeypatch, _history(days), today="2026-10-02 18:00")

    ingest.fetch_price_single(ROW, output_dir=str(tmp_path))

    assert FakeTicker.calls == [{"start": "2026-09-25", "end": "2026-10-03"}]
    out = pd.read_csv(path)
    assert list(out.columns) == COLUMNS
    assert list(out["Date"]) == ["2026-09-24"] + days
    assert out.loc[out["Date"] == "2026-09-25", "Close"].item() == 100.0  # replaced, not 95
    assert out["Date"].is_unique


def test_rerun_same_day_is_idempotent(tmp_path, monkeypatch):
    path = tmp_path / "7_Test_Co.csv"
    _setup(monkeypatch, _history(["2026-10-01", "2026-10-02"]), today="2026-10-02 18:00")
    ingest.fetch_price_single(ROW, output_dir=str(tmp_path))  # fresh 1y fetch
    assert FakeTicker.calls == [{"period": "1y"}]

    _setup(monkeypatch, _history(["2026-10-02"], close=200.0), today="2026-10-02 18:00")
    ingest.fetch_price_single(ROW, output_dir=str(tmp_path))
    ingest.fetch_price_single(ROW, output_dir=str(tmp_path))

    out = pd.read_csv(path)
    assert list(out["Date"]) == ["2026-10-01", "2026-10-02"]
    assert out["Close"].tolist() == [100.0, 200.0]


def test_no_new_data_leaves_file_untouched(tmp_path, monkeypatch):
    path = tmp_path / "7_Test_Co.csv"
    _write_existing(path, [["2026-10-02", 1, 1, 1, 1.0, 1, 0.0, 0.0, 7]])
    before = path.read_bytes()
    _setup(monkeypatch, pd.DataFrame(), today="2026-10-03 10:00")

    ingest.fetch_price_single(ROW, output_dir=str(tmp_path))

    assert path.read_bytes() == before


def test_last_saved_date_handles_missing_and_empty(tmp_path):
    assert ingest._last_saved_date(str(tmp_path / "nope.csv")) is None
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert ingest._last_saved_date(str(empty)) is None
    _write_existing(tmp_path / "x.csv", [["2026-08-07", 1, 1, 1, 1.0, 1, 0.0, 0.0, 7]])
    assert ingest._last_saved_date(str(tmp_path / "x.csv")) == date(2026, 8, 7)
