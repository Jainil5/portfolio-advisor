import os

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd

from backend.services.update_data_pipeline import update_finance_data

PORTFOLIO_FILE = "data/user_portfolio.csv"
STOCKS_FILE = "data/stocks.csv"

os.makedirs("data", exist_ok=True)


def run_data_pipeline(force: bool = False):
    """Run the full finance data refresh pipeline."""
    update_finance_data(force=force)


def add_stock(stock_id: int, quantity: int, buy_price: float):
    """Add or update a stock holding in the user portfolio."""
    if not os.path.exists(STOCKS_FILE):
        raise FileNotFoundError("Stocks database missing. Run the data pipeline first.")

    stocks_df = pd.read_csv(STOCKS_FILE)
    stock_row = stocks_df[stocks_df["stock_id"] == stock_id]
    if stock_row.empty:
        raise ValueError(f"Invalid stock ID: {stock_id}")

    stock_name = stock_row.iloc[0]["company_name"]

    if os.path.exists(PORTFOLIO_FILE):
        portfolio_df = pd.read_csv(PORTFOLIO_FILE)
    else:
        portfolio_df = pd.DataFrame(
            columns=["stock_id", "stock_name", "quantity", "buy_price"]
        )

    existing = portfolio_df[portfolio_df["stock_id"] == stock_id]
    if existing.empty:
        new_row = pd.DataFrame(
            [
                {
                    "stock_id": stock_id,
                    "stock_name": stock_name,
                    "quantity": quantity,
                    "buy_price": buy_price,
                }
            ]
        )
        portfolio_df = pd.concat([portfolio_df, new_row], ignore_index=True)
    else:
        idx = existing.index[0]
        old_qty = float(portfolio_df.at[idx, "quantity"])
        old_price = float(portfolio_df.at[idx, "buy_price"])
        new_qty = old_qty + quantity
        avg_price = ((old_qty * old_price) + (quantity * buy_price)) / new_qty
        portfolio_df.at[idx, "quantity"] = new_qty
        portfolio_df.at[idx, "buy_price"] = round(avg_price, 2)
        portfolio_df.at[idx, "stock_name"] = stock_name

    portfolio_df.to_csv(PORTFOLIO_FILE, index=False)
