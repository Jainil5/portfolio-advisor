"""News tool output formatting and symbol resolution (temp DuckDB, no network)."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from backend.news import config, db, ingest, tools
from test_news_parsing import RAW

SCRIPS = pd.DataFrame({
    "symbol": ["TCS", "RELIANCE", "M&M"],
    "company_name": ["Tata Consultancy Services Ltd.", "Reliance Industries Ltd.", "Mahindra & Mahindra Ltd."],
    "scrip_code": ["532540", "500325", "500520"],
    "status": ["resolved"] * 3,
})


@pytest.fixture
def news_db(tmp_path, monkeypatch):
    path = str(tmp_path / "news.duckdb")
    monkeypatch.setattr(config, "NEWS_DB_FILE", path)
    monkeypatch.setattr(config, "FILINGS_DIR", str(tmp_path / "filings"))
    monkeypatch.setattr(tools, "load_scrip_map", lambda: SCRIPS)
    now = datetime(2026, 10, 2, 12, 0)
    monkeypatch.setattr(tools, "_now", lambda: now)

    def row(i, code, sym, hours_ago, subject, headline="h | with pipe"):
        r = dict(RAW, NEWSID=f"n{i}", SCRIP_CD=code, NEWSSUB=subject, HEADLINE=headline,
                 DT_TM=(now - timedelta(hours=hours_ago)).isoformat())
        return ingest.parse_announcement(r, sym)

    db.upsert([
        row(1, 532540, "TCS", 2, "Regulation 30 (LODR)-Acquisition", "TCS acquires X"),
        row(2, 532540, "TCS", 5, "Closure of Trading Window"),
        row(3, 532540, "TCS", 24 * 10, "Old news"),
        row(4, 500325, "RELIANCE", 30, "Board Meeting Outcome", "Results declared"),
    ], path=path)
    return path


def test_resolve_stock_by_symbol_name_and_fuzzy():
    assert tools.resolve_stock("tcs", SCRIPS)[2] == "532540"
    assert tools.resolve_stock("TCS.NS", SCRIPS)[2] == "532540"
    assert tools.resolve_stock("Reliance", SCRIPS)[0] == "RELIANCE"
    assert tools.resolve_stock("Mahindra & Mahindra", SCRIPS)[0] == "M&M"
    assert tools.resolve_stock("Tata Consultancy Servics", SCRIPS)[0] == "TCS"  # typo
    assert tools.resolve_stock("Nonexistent Widgets", SCRIPS) is None


def test_get_stock_news_table_hides_routine_and_old(news_db):
    out = tools.get_stock_news.invoke({"symbol": "TCS", "days": 3})
    assert out.startswith("Tata Consultancy Services Ltd. (TCS, BSE 532540) - last 3 day(s):")
    lines = out.splitlines()
    assert lines[2] == "| date (IST) | category | headline | pdf_url |"
    body = [l for l in lines[4:] if l.startswith("|")]
    assert len(body) == 1
    assert "2026-10-02 10:00" in body[0]
    assert "[BSE critical]" in body[0]
    assert "TCS acquires X" in body[0]
    assert "/AttachLive/" in body[0]


def test_get_stock_news_can_include_routine(news_db):
    out = tools.get_stock_news.invoke({"symbol": "TCS", "days": 3, "include_routine": True})
    assert "[routine]" in out
    assert "h / with pipe" in out  # pipes escaped so the table stays valid


def test_get_stock_news_unknown_and_empty(news_db):
    assert "not one of the tracked stocks" in tools.get_stock_news.invoke({"symbol": "ZZZZ"})
    assert "no announcements found" in tools.get_stock_news.invoke({"symbol": "M&M"})


def test_get_latest_news_all_newest_first_with_symbol(news_db):
    out = tools.get_latest_news_all.invoke({"hours": 48})
    rows = [l for l in out.splitlines() if l.startswith("| 2026")]
    assert "symbol" in out.splitlines()[2]
    assert [r.split("|")[2].strip() for r in rows] == ["TCS", "RELIANCE"]


def test_tools_report_missing_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "NEWS_DB_FILE", str(tmp_path / "missing.duckdb"))
    assert "Run the ingest first" in tools.get_latest_news_all.invoke({})


def test_read_filing_rejects_non_bse_urls():
    out = tools.read_filing.invoke({"pdf_url": "https://evil.example.com/x.pdf"})
    assert "only accepts BSE filing URLs" in out


def test_read_filing_falls_back_to_his_and_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FILINGS_DIR", str(tmp_path))
    calls = []

    class Resp:
        def __init__(self, ok, content):
            self.ok, self.content, self.status_code = ok, content, 200 if ok else 404

    def fake_get(url, headers, timeout):
        calls.append(url)
        return Resp(True, b"%PDF-fake") if "AttachHis" in url else Resp(False, b"<html>")

    class FakePage:
        def extract_text(self):
            return "Board approved a dividend of Rs 10 per share."

    monkeypatch.setattr(tools.requests, "get", fake_get)
    monkeypatch.setattr(tools, "PdfReader", lambda p: type("R", (), {"pages": [FakePage()]})())

    url = f"{config.ATTACHMENT_BASE}/AttachLive/abc-123.pdf"
    assert "dividend of Rs 10" in tools.read_filing.invoke({"pdf_url": url})
    assert [("AttachLive" in c, "AttachHis" in c) for c in calls] == [(True, False), (False, True)]

    calls.clear()
    out = tools.read_filing.invoke({"pdf_url": url, "max_chars": 500})
    assert calls == []  # served from data/filings cache
    assert out.startswith("Board approved")


def test_read_filing_scanned_pdf_message(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FILINGS_DIR", str(tmp_path))
    (tmp_path / "scan.pdf").write_bytes(b"%PDF-")
    monkeypatch.setattr(tools, "PdfReader", lambda p: type("R", (), {"pages": []})())
    out = tools.read_filing.invoke({"pdf_url": f"{config.ATTACHMENT_BASE}/AttachHis/scan.pdf"})
    assert "no extractable text" in out


def test_read_filing_truncates(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FILINGS_DIR", str(tmp_path))
    (tmp_path / "big.txt").write_text("x" * 2000)
    out = tools.read_filing.invoke({"pdf_url": f"{config.ATTACHMENT_BASE}/AttachLive/big.pdf", "max_chars": 600})
    assert out.startswith("x" * 600)
    assert "1400 more characters" in out
