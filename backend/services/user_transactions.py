import os
import uuid
from datetime import datetime
import pandas as pd
from backend.config import STOCKS_FILE, TRANSACTIONS_FILE

def load_csv(path: str) -> pd.DataFrame:
    """Safely load a CSV file."""

    if os.path.exists(path):
        return pd.read_csv(path)

    return pd.DataFrame()


def save_csv(df: pd.DataFrame, path: str):
    """Save dataframe."""

    df.to_csv(path, index=False)


def generate_transaction_id():
    """Generate a short transaction id."""
    
    return str(uuid.uuid4())[:8]

# Asset Helpers



def get_stock_name(stock_id: int) -> str:
    """Get stock name using stock id.

    Args:
        stock_id (int): The ID of the stock to look up.

    Returns:
        str: The company name associated with the stock ID.

    Raises:
        ValueError: If ``stock_id`` is ``None`` or cannot be converted to an integer,
            or if the ID does not exist in the CSV.
    """
    if stock_id is None:
        raise ValueError("Stock ID must not be None.")
    stocks = load_csv(STOCKS_FILE)
    try:
        sid = int(stock_id)
    except (ValueError, TypeError):
        raise ValueError(f"Invalid Stock ID type: {stock_id}")
    row = stocks[stocks["stock_id"] == sid]
    if row.empty:
        raise ValueError(f"Invalid Stock ID: {stock_id}")
    return row.iloc[0]["company_name"]

# Transactions

def add_transaction(stock_id: int, quantity: float, price: float, action: str):
    """Add a stock transaction. Action must be 'buy' or 'sell'."""
    if action not in {"buy", "sell"}:
        raise ValueError("Invalid action.")
    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    if price <= 0:
        raise ValueError("Price must be positive.")

    name = get_stock_name(stock_id)

    transaction = {
        "transaction_id": generate_transaction_id(),
        "asset_type": "stock",
        "asset_id": stock_id,
        "name": name,
        "action": action,
        "quantity": quantity,
        "price": price,
        "date": datetime.now().strftime("%Y-%m-%d"),
    }

    transactions = load_csv(TRANSACTIONS_FILE)
    transactions = pd.concat([transactions, pd.DataFrame([transaction])], ignore_index=True)
    save_csv(transactions, TRANSACTIONS_FILE)
    
    update_portfolio()
    print(f"{action.upper()} Successful : {quantity} {name}")

# Portfolio

def update_portfolio():
    """Update the portfolio snapshot using transactions.csv."""
    transactions = load_csv(TRANSACTIONS_FILE)
    if transactions.empty:
        save_csv(pd.DataFrame(), TRANSACTIONS_FILE
        )
        return

    portfolio = []
    grouped = transactions.groupby(["asset_type", "asset_id", "name"])

    for (asset_type, asset_id, name), group in grouped:
        quantity = 0
        total_investment = 0

        for _, row in group.iterrows():
            qty = float(row["quantity"])
            price = float(row["buy_price"])
            if row["action"] == "buy":
                quantity += qty
                total_investment += (qty * price)
            else:
                quantity -= qty
                total_investment -= (qty * price)

        if quantity <= 0:
            continue

        avg_price = round(total_investment / quantity, 2)
        portfolio.append({
            "asset_type": asset_type,
            "asset_id": asset_id,
            "name": name,
            "quantity": round(quantity, 4),
            "avg_buy_price": avg_price,
            "total_investment": round(total_investment, 2),
        })

    portfolio_df = pd.DataFrame(portfolio)
    save_csv(portfolio_df, TRANSACTIONS_FILE)

# Public Functions

def buy_stock(stock_id: int, quantity: float, price: float):
    """Buy a stock."""
    add_transaction(stock_id=stock_id, quantity=quantity, price=price, action="buy")

def sell_stock(stock_id: int, quantity: float, price: float):
    """Sell a stock."""
    add_transaction(stock_id=stock_id, quantity=quantity, price=price, action="sell")

# Retrieval Functions

def get_transactions():
    """Return all transactions."""
    return load_csv(TRANSACTIONS_FILE)


def delete_transaction(transaction_id: str):
    """Delete a transaction."""
    transactions = load_csv(TRANSACTIONS_FILE)
    if transactions.empty:
        return
    transactions = transactions[transactions["transaction_id"] != transaction_id]
    save_csv(transactions, TRANSACTIONS_FILE)
    update_portfolio()

def clear_portfolio():
    """Delete everything."""
    if os.path.exists(TRANSACTIONS_FILE):
        os.remove(TRANSACTIONS_FILE)
    print("Portfolio Cleared.")

# Testing

if __name__ == "__main__":
    buy_stock(stock_id=1, quantity=10, price=1000)
    sell_stock(stock_id=1, quantity=3, price=1300)

    print("\nPortfolio\n")
    print("\nTransactions\n")
    print(get_transactions())