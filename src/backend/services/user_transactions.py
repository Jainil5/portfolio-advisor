"""Portfolio transaction ledger and derived holdings.

Data model (two files, one schema each):
- ``settings.TRANSACTIONS_FILE`` (bronze): append-only ledger of buy/sell
  events, validated against the :class:`Transaction` contract.
- ``settings.PORTFOLIO_FILE`` (silver): holdings derived from the ledger,
  validated against :class:`PortfolioHolding`.

Previously both shared a single file and were overwritten by each other with
different column names, which corrupted the ledger on every write and crashed
the dashboard. That coupling is gone: the ledger is the source of truth and the
portfolio is always recomputed from it.
"""

import os

import pandas as pd

from backend.config import settings
from backend.data import repository
from backend.models import PortfolioHolding, Transaction


def get_stock_name(stock_id: int) -> str:
    """Return the company name for ``stock_id`` from the stocks master.

    Raises:
        ValueError: if ``stock_id`` is None, non-integer, or unknown.
    """
    if stock_id is None:
        raise ValueError("Stock ID must not be None.")
    try:
        sid = int(stock_id)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid Stock ID type: {stock_id}")
    stocks = repository.load_stocks_df()
    row = stocks[stocks["stock_id"] == sid]
    if row.empty:
        raise ValueError(f"Invalid Stock ID: {stock_id}")
    return row.iloc[0]["company_name"]


# --- Ledger (bronze) --------------------------------------------------------

def _read_ledger() -> pd.DataFrame:
    df = repository.read_csv_safe(settings.TRANSACTIONS_FILE)
    if df.empty:
        return pd.DataFrame(columns=list(Transaction.COLUMNS))
    return df


def _write_ledger(df: pd.DataFrame) -> None:
    # Validate the whole ledger before it hits disk: a partial/corrupt write
    # is worse than a loud failure.
    Transaction.validate_dataframe(df)
    repository.write_csv(df.reindex(columns=list(Transaction.COLUMNS)), settings.TRANSACTIONS_FILE)


def add_transaction(stock_id: int, quantity: float, price: float, action: str) -> Transaction:
    """Append a 'buy' or 'sell' transaction and refresh the derived portfolio.

    Validation (action, positive quantity/price, known stock) is enforced by
    the :class:`Transaction` contract; failures raise ``ValueError``.
    """
    tx = Transaction(
        stock_id=int(stock_id),
        stock_name=get_stock_name(stock_id),
        action=action,
        quantity=float(quantity),
        price=float(price),
    )

    ledger = _read_ledger()
    ledger = pd.concat([ledger, pd.DataFrame([tx.to_row()])], ignore_index=True)
    _write_ledger(ledger)

    update_portfolio()
    print(f"{tx.action.upper()} Successful : {tx.quantity} {tx.stock_name}")
    return tx


def get_transactions() -> pd.DataFrame:
    """Return the full append-only transaction ledger."""
    return _read_ledger()


def delete_transaction(transaction_id: str) -> None:
    """Remove one transaction from the ledger and refresh the portfolio."""
    ledger = _read_ledger()
    if ledger.empty:
        return
    ledger = ledger[ledger["transaction_id"] != transaction_id]
    _write_ledger(ledger)
    update_portfolio()


# --- Derived portfolio (silver) --------------------------------------------

def update_portfolio() -> pd.DataFrame:
    """Recompute holdings from the ledger and persist them.

    Net quantity and net invested cost per (stock_id, name); positions that
    are fully sold (quantity <= 0) are dropped.
    """
    ledger = _read_ledger()

    positions: dict[tuple[int, str], list[float]] = {}
    if not ledger.empty:
        for tx in Transaction.validate_dataframe(ledger):
            key = (tx.stock_id, tx.stock_name)
            qty, cost = positions.get(key, [0.0, 0.0])
            signed_qty = tx.quantity if tx.action == "buy" else -tx.quantity
            signed_cost = tx.quantity * tx.price if tx.action == "buy" else -(tx.quantity * tx.price)
            positions[key] = [qty + signed_qty, cost + signed_cost]

    holdings = [
        PortfolioHolding(
            stock_id=sid,
            stock_name=name,
            quantity=round(qty, 4),
            avg_buy_price=round(cost / qty, 2),
            total_investment=round(cost, 2),
        )
        for (sid, name), (qty, cost) in positions.items()
        if qty > 0
    ]

    holdings_df = PortfolioHolding.dataframe(holdings)
    repository.write_csv(holdings_df, settings.PORTFOLIO_FILE)
    return holdings_df


def get_portfolio() -> pd.DataFrame:
    """Return the derived holdings, recomputing from the ledger if missing."""
    if not os.path.exists(settings.PORTFOLIO_FILE):
        return update_portfolio()
    return repository.read_csv_safe(settings.PORTFOLIO_FILE)


# --- Public convenience wrappers -------------------------------------------

def buy_stock(stock_id: int, quantity: float, price: float) -> Transaction:
    """Buy a stock."""
    return add_transaction(stock_id=stock_id, quantity=quantity, price=price, action="buy")


def sell_stock(stock_id: int, quantity: float, price: float) -> Transaction:
    """Sell a stock."""
    return add_transaction(stock_id=stock_id, quantity=quantity, price=price, action="sell")


def clear_portfolio() -> None:
    """Delete the ledger and the derived holdings."""
    for path in (settings.TRANSACTIONS_FILE, settings.PORTFOLIO_FILE):
        if os.path.exists(path):
            os.remove(path)
    repository._csv_cache.clear()
    print("Portfolio Cleared.")


if __name__ == "__main__":
    buy_stock(stock_id=1, quantity=10, price=1000)
    sell_stock(stock_id=1, quantity=3, price=1300)
    print("\nPortfolio\n", get_portfolio())
    print("\nTransactions\n", get_transactions())
