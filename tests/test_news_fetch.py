"""Rolling news: RSS parsing, 5-item rollover, summary refresh (no network)."""

import pandas as pd

from backend.news import fetch


def rss(*items):
    body = "".join(
        f"<item><title>{t} - {src}</title><link>https://x/{i}</link>"
        f"<pubDate>{d}</pubDate><source url='https://s'>{src}</source></item>"
        for i, (t, src, d) in enumerate(items)
    )
    return f"<rss><channel>{body}</channel></rss>".encode()


def day(n):
    return f"Thu, {n:02d} Oct 2026 10:00:00 GMT"


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def invoke(self, prompt):
        self.calls += 1
        return type("Msg", (), {"content": f" summary {self.calls} "})()


def test_parse_rss_strips_source_and_sorts_newest_first():
    items = fetch.parse_rss(rss(("Old news", "Mint", day(1)), ("New news", "ET", day(2))))
    assert [h["title"] for h in items] == ["New news", "Old news"]
    assert items[0] == {"title": "New news", "source": "ET",
                        "published_at": "2026-10-02 10:00", "link": "https://x/1"}


def test_merge_keeps_five_newest_and_dedupes():
    old = [{"title": f"t{i}", "source": "", "published_at": f"2026-10-0{i}", "link": ""}
           for i in range(1, 6)]
    new = [{"title": "T5", "source": "", "published_at": "2026-10-05", "link": ""},
           {"title": "t6", "source": "", "published_at": "2026-10-06", "link": ""}]
    merged = fetch.merge_headlines(old, new)
    assert [h["title"].lower() for h in merged] == ["t6", "t5", "t4", "t3", "t2"]


def test_run_rolls_news_and_only_resummarizes_on_change(tmp_path):
    stocks = tmp_path / "stocks.csv"
    pd.DataFrame({"ticker": ["TCS.NS", "INFY.NS"],
                  "company_name": ["Tata Consultancy Services Ltd.", "Infosys Ltd."],
                  "is_active": [True, False]}).to_csv(stocks, index=False)
    news = tmp_path / "news.csv"
    llm = FakeLLM()
    feed = rss(*[(f"h{i}", "ET", day(i)) for i in range(1, 7)])

    def run(xml):
        return fetch.run(fetch=lambda url: xml, llm=llm, stocks_path=stocks,
                         news_path=news, sleep=lambda s: None)

    assert run(feed) == {"stocks": 1, "updated": 1, "failed": 0}
    row = fetch.load_news(news).iloc[0]
    assert row["ticker"] == "TCS.NS"
    assert [h["title"] for h in row["headlines"]] == ["h6", "h5", "h4", "h3", "h2"]
    assert row["summary"] == "summary 1"

    run(feed)  # nothing new -> summary kept, no LLM call
    assert llm.calls == 1

    run(rss(("h7", "ET", day(7))))  # newest pushes h2 out
    row = fetch.load_news(news).iloc[0]
    assert [h["title"] for h in row["headlines"]] == ["h7", "h6", "h5", "h4", "h3"]
    assert row["summary"] == "summary 2"


def test_fetch_failure_keeps_previous_row(tmp_path):
    stocks = tmp_path / "stocks.csv"
    pd.DataFrame({"ticker": ["TCS.NS"], "company_name": ["TCS"]}).to_csv(stocks, index=False)
    news = tmp_path / "news.csv"
    fetch.run(fetch=lambda u: rss(("h1", "ET", day(1))), with_summary=False,
              stocks_path=stocks, news_path=news)

    def boom(url):
        raise RuntimeError("blocked")

    assert fetch.run(fetch=boom, stocks_path=stocks, news_path=news)["failed"] == 1
    assert fetch.load_news(news).iloc[0]["headlines"][0]["title"] == "h1"
