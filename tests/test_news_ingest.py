"""Idempotent DuckDB inserts and ingest behaviour, with BSE mocked."""

import pandas as pd
import pytest

from backend.news import client, db, ingest
from test_news_parsing import RAW


def _raw(i, **over):
    return dict(RAW, NEWSID=f"id-{i}", HEADLINE=f"headline {i}", **over)


def test_upsert_is_idempotent_and_refreshes_pdf_location(tmp_path):
    path = str(tmp_path / "news.duckdb")
    rows = [ingest.parse_announcement(_raw(i), "TCS") for i in range(3)]

    assert db.upsert(rows, path=path) == 3
    assert db.upsert(rows, path=path) == 0  # re-run: nothing new

    # The filing ages: BSE flips PDFFLAG and the URL moves to AttachHis.
    moved = ingest.parse_announcement(_raw(0, PDFFLAG=1), "TCS")
    assert db.upsert([moved, moved], path=path) == 0  # duplicate ids in one batch are fine

    df = db.query("SELECT id, pdf_flag, pdf_url FROM announcements ORDER BY id", path=path)
    assert len(df) == 3
    assert df.loc[0, "pdf_flag"] == 1
    assert "/AttachHis/" in df.loc[0, "pdf_url"]


def test_upsert_empty_is_noop(tmp_path):
    assert db.upsert([], path=str(tmp_path / "x.duckdb")) == 0


class FakeBSE:
    """Serves pages of fake announcements; optionally fails per scrip."""

    def __init__(self, per_scrip, page_size=2, fail=None):
        self.per_scrip, self.page_size, self.fail = per_scrip, page_size, fail or {}
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def announcements(self, page_no, from_date, to_date, scripcode):
        self.calls.append((scripcode, page_no))
        if scripcode in self.fail:
            raise self.fail[scripcode]
        items = self.per_scrip.get(scripcode, [])
        start = (page_no - 1) * self.page_size
        return {"Table": items[start:start + self.page_size], "Table1": [{"ROWCNT": len(items)}]}


@pytest.fixture
def scrip_map(monkeypatch):
    df = pd.DataFrame({
        "symbol": ["TCS", "INFY", "RELIANCE"],
        "company_name": ["TCS Ltd", "Infosys Ltd", "Reliance Ltd"],
        "scrip_code": ["532540", "500209", "500325"],
        "status": ["resolved"] * 3,
    })
    monkeypatch.setattr(ingest, "load_scrip_map", lambda: df)
    return df


def _install(monkeypatch, fake):
    monkeypatch.setattr(ingest, "open_bse", lambda: fake)


def test_run_follows_pagination_and_is_idempotent(tmp_path, monkeypatch, scrip_map):
    tcs = [_raw(i, SCRIP_CD=532540) for i in range(5)]
    fake = FakeBSE({"532540": tcs})
    _install(monkeypatch, fake)
    path = str(tmp_path / "news.duckdb")

    s1 = ingest.run(days=2, symbols=["TCS"], db_path=path, sleep=lambda _: None)
    assert [c for c in fake.calls] == [("532540", 1), ("532540", 2), ("532540", 3)]
    assert s1["fetched"] == 5 and s1["new"] == 5

    s2 = ingest.run(days=2, symbols=["tcs.ns"], db_path=path, sleep=lambda _: None)
    assert s2["new"] == 0


def test_run_logs_403_and_stops_without_crashing(tmp_path, monkeypatch, scrip_map):
    fake = FakeBSE(
        {"532540": [_raw(1)], "500325": [_raw(3)]},
        fail={"500209": ConnectionError("403: Forbidden")},
    )
    _install(monkeypatch, fake)
    path = str(tmp_path / "news.duckdb")

    summary = ingest.run(days=2, db_path=path, sleep=lambda _: None)

    assert summary["blocked"] is True
    assert summary["new"] == 1                      # TCS saved before the block
    assert ("500325", 1) not in fake.calls          # stopped after the 403


def test_transient_errors_retry_with_backoff(monkeypatch):
    waits, attempts = [], []

    def flaky():
        attempts.append(1)
        if len(attempts) < 3:
            raise TimeoutError("timed out")
        return "ok"

    assert client.call_with_retry(flaky, sleep=waits.append) == "ok"
    assert waits == [2.0, 4.0]


def test_run_skips_failing_stock_and_continues(tmp_path, monkeypatch, scrip_map):
    monkeypatch.setattr(client.config, "MAX_RETRIES", 1)
    fake = FakeBSE({"500325": [_raw(3)]}, fail={"500209": TimeoutError("timed out")})
    _install(monkeypatch, fake)

    summary = ingest.run(days=2, db_path=str(tmp_path / "n.duckdb"), sleep=lambda _: None)

    assert summary == {"stocks": 3, "fetched": 1, "new": 1, "errors": 1, "blocked": False}
