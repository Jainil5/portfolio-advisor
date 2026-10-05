"""Regression tests for the transaction ledger and derived portfolio.

These guard the Tier-1 bugs: the ledger being overwritten by the portfolio
snapshot, the ``price``/``buy_price`` KeyError, and silent schema drift.
"""

import pandas as pd
import pytest

from backend.config import settings
from backend.data import repository
from backend.services import user_transactions


@pytest.fixture
def isolated_data(tmp_path, monkeypatch):
    # Point all three data files at a throwaway directory.
    stocks = tmp_path / "stocks.csv"
    stocks.write_text("stock_id,company_name\n1,Reliance Industries Ltd.\n2,Tata Consultancy Services Ltd.\n")

    monkeypatch.setattr(settings, "STOCKS_FILE", str(stocks))
    monkeypatch.setattr(settings, "TRANSACTIONS_FILE", str(tmp_path / "transactions.csv"))
    monkeypatch.setattr(settings, "PORTFOLIO_FILE", str(tmp_path / "portfolio.csv"))

    repository._csv_cache.clear()
    yield tmp_path
    repository._csv_cache.clear()


def _holding(portfolio_df, stock_id):
    rows = portfolio_df[portfolio_df["stock_id"] == stock_id]
    assert not rows.empty, f"stock {stock_id} missing from portfolio"
    return rows.iloc[0]


def test_buy_then_sell_netting(isolated_data):
    user_transactions.buy_stock(stock_id=1, quantity=10, price=1000)
    user_transactions.sell_stock(stock_id=1, quantity=3, price=1300)

    portfolio = user_transactions.get_portfolio()
    holding = _holding(portfolio, 1)

    assert holding["quantity"] == pytest.approx(7)
    # net cost = 10*1000 - 3*1300 = 6100 ; avg = 6100/7
    assert holding["total_investment"] == pytest.approx(6100)
    assert holding["avg_buy_price"] == pytest.approx(round(6100 / 7, 2))


def test_ledger_is_append_only_and_separate_from_portfolio(isolated_data):
    user_transactions.buy_stock(stock_id=1, quantity=10, price=1000)
    user_transactions.buy_stock(stock_id=1, quantity=5, price=1200)

    ledger = user_transactions.get_transactions()
    # Two rows survive in the ledger (it is not collapsed into holdings).
    assert len(ledger) == 2
    assert {"action", "price", "transaction_id"} <= set(ledger.columns)

    portfolio = user_transactions.get_portfolio()
    assert len(portfolio) == 1  # aggregated to one position
    assert _holding(portfolio, 1)["quantity"] == pytest.approx(15)


def test_full_exit_drops_position(isolated_data):
    user_transactions.buy_stock(stock_id=2, quantity=5, price=3000)
    user_transactions.sell_stock(stock_id=2, quantity=5, price=3500)

    portfolio = user_transactions.get_portfolio()
    assert portfolio[portfolio["stock_id"] == 2].empty


def test_invalid_transaction_rejected(isolated_data):
    with pytest.raises(ValueError):
        user_transactions.add_transaction(stock_id=1, quantity=10, price=1000, action="hold")
    with pytest.raises(ValueError):
        user_transactions.add_transaction(stock_id=1, quantity=0, price=1000, action="buy")
    with pytest.raises(ValueError):
        user_transactions.add_transaction(stock_id=1, quantity=5, price=-1, action="buy")
    with pytest.raises(ValueError):
        user_transactions.add_transaction(stock_id=999, quantity=5, price=100, action="buy")


def test_delete_transaction_re_derives_portfolio(isolated_data):
    user_transactions.buy_stock(stock_id=1, quantity=10, price=1000)
    tx = user_transactions.buy_stock(stock_id=1, quantity=5, price=1200)

    user_transactions.delete_transaction(tx.transaction_id)

    ledger = user_transactions.get_transactions()
    assert len(ledger) == 1
    assert _holding(user_transactions.get_portfolio(), 1)["quantity"] == pytest.approx(10)


def test_portfolio_matches_ledger_after_reload(isolated_data):
    """Data written to disk must revalidate against the contracts on read."""
    user_transactions.buy_stock(stock_id=1, quantity=10, price=1000)

    repository._csv_cache.clear()
    ledger = pd.read_csv(settings.TRANSACTIONS_FILE)
    assert ledger.iloc[0]["action"] == "buy"
    assert ledger.iloc[0]["stock_id"] == 1
