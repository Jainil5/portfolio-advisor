"""BSE announcements: parsing, ticker matching, paging, incremental stop (no network)."""

from datetime import datetime
from urllib.parse import parse_qs, urlparse

import pandas as pd
import pytest

from backend.news import bse_news

NOW = datetime(2026, 10, 1, 23, 0)


def raw(i, name="Tata Consultancy Services Ltd", sym="tcs", headline="Order win", **kw):
    row = {
        "NEWSID": f"id{i}", "SCRIP_CD": 532540, "SLONGNAME": name,
        "NEWSSUB": f"{name} - 532540 - Update", "HEADLINE": headline,
        "DissemDT": f"2026-10-01T{i % 24:02d}:00:00.1", "CATEGORYNAME": "Company Update",
        "SUBCATNAME": "General", "ATTACHMENTNAME": f"f{i}.pdf", "PDFFLAG": 0,
        "CRITICALNEWS": "0", "NSURL": f"https://www.bseindia.com/stock-share-price/x/{sym}/532540/",
    }
    row.update(kw)
    return row


@pytest.fixture
def stocks(tmp_path):
    path = tmp_path / "stocks.csv"
    pd.DataFrame({"ticker": ["TCS.NS", "BAJAJELEC.NS"],
                  "company_name": ["Tata Consultancy Services Ltd.", "Bajaj Electricals Ltd."]}
                 ).to_csv(path, index=False)
    return path


def test_parse_row_matches_ticker_by_symbol_or_name(stocks):
    lookup = bse_news.ticker_lookup(stocks)
    assert bse_news.parse_row(raw(1), lookup)["ticker"] == "TCS.NS"
    by_name = raw(2, name="Bajaj Electricals Ltd-$", sym="unknown")
    row = bse_news.parse_row(by_name, lookup)
    assert row["ticker"] == "BAJAJELEC.NS"
    assert row["company_name"] == "Bajaj Electricals Ltd"
    assert bse_news.parse_row(raw(3, name="Some Smallcap Ltd", sym="small"), lookup)["ticker"] == ""


def test_parse_row_cleans_text_and_flags():
    row = bse_news.parse_row(raw(1, headline="Sales for Sep''26", PDFFLAG=1, CRITICALNEWS="1"), {})
    assert row["headline"] == "Sales for Sep'26"
    assert row["pdf_url"].endswith("/AttachHis/f1.pdf")
    assert row["is_critical"] and not row["is_routine"]
    assert row["published_at"] == "2026-10-01 01:00:00"
    boiler = bse_news.parse_row(raw(2, headline="Please find attached herewith the intimation"), {})
    assert boiler["headline"] == ""
    routine = bse_news.parse_row(raw(3, headline="Closure of Trading Window"), {})
    assert routine["is_routine"]


class FakeBSE:
    """Serves `rows` (newest first) in pages of `size`, like BSE's API."""

    def __init__(self, rows, size=2):
        self.rows, self.size, self.pages = rows, size, []

    def __call__(self, url):
        page = int(parse_qs(urlparse(url).query)["pageno"][0])
        self.pages.append(page)
        chunk = self.rows[(page - 1) * self.size: page * self.size]
        return {"Table": chunk, "Table1": [{"ROWCNT": len(self.rows)}]}


def test_run_pages_then_stops_at_known_filings(tmp_path, stocks):
    out = tmp_path / "bse.csv"
    api = FakeBSE([raw(i) for i in range(5, 0, -1)])
    kw = dict(days=1, fetch=api, path=out, stocks_path=stocks, sleep=lambda s: None, now=NOW)

    assert bse_news.run(**kw)["new"] == 5
    assert api.pages == [1, 2, 3]

    api.rows.insert(0, raw(6))  # one new filing on top
    api.pages = []
    summary = bse_news.run(**kw)
    assert summary == {"new": 1, "new_for_our_stocks": 1, "stored": 6, "errors": 0}
    assert api.pages == [1]  # page 1 already had known ids -> stop
    df = bse_news.load_bse_news(out)
    assert df["id"].tolist() == [f"id{i}" for i in range(6, 0, -1)]


def test_old_filings_roll_off_and_errors_keep_existing(tmp_path, stocks):
    out = tmp_path / "bse.csv"
    old = bse_news.parse_row(raw(1, DissemDT="2026-09-01T10:00:00"), {})
    bse_news.save_bse_news(pd.DataFrame([old]), out, now=datetime(2026, 9, 2))

    def boom(url):
        raise RuntimeError("403")

    summary = bse_news.run(days=1, fetch=boom, path=out, stocks_path=stocks, now=NOW)
    assert summary["errors"] == 1
    assert bse_news.load_bse_news(out).empty  # month-old filing aged out of the 7-day window
