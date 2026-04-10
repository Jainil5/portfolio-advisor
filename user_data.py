import pandas as pd
import os
from datetime import datetime

PORTFOLIO_FILE = "data/user_portfolio.csv"
STOCKS_FILE = "data/stocks.csv"


def get_stock_name(stock_id):
    stocks_df = pd.read_csv(STOCKS_FILE)
    row = stocks_df[stocks_df["stock_id"] == stock_id]

    if not row.empty:
        return row.iloc[0]["company_name"]
    return "Unknown"


def add_stock(stock_id, quantity, buy_price):
    stock_name = get_stock_name(stock_id)

    new_data = {
        "stock_id": stock_id,
        "stock_name": stock_name,
        "quantity": quantity,
        "buy_price": buy_price,
        "buy_date": datetime.now().strftime("%Y-%m-%d")
    }

    if os.path.exists(PORTFOLIO_FILE):
        df = pd.read_csv(PORTFOLIO_FILE)
        df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
    else:
        df = pd.DataFrame([new_data])

    df.to_csv(PORTFOLIO_FILE, index=False)

    print(f"Added {stock_name} to portfolio")


# Example
if __name__ == "__main__":
    add_stock(stock_id=75 , quantity=10, buy_price=900)
    add_stock(stock_id=62 , quantity=5, buy_price=1000)
    add_stock(stock_id=58 , quantity=15, buy_price=121)