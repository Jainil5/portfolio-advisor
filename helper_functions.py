import pandas as pd
import yfinance as yf

stocks_df = pd.read_csv("data/stocks.csv")

def get_current_price_by_name(stock_name):
    # 1. Convert to lower case
    search_name = stock_name
    
    match = pd.DataFrame()
    for i in search_name.split():
        match = stocks_df[stocks_df["company_name"] == i]
        if not match.empty:
            break
    
    if match.empty:
        match = stocks_df[stocks_df["company_name"].str.contains(search_name, case=False, na=False)]

    if match.empty:
        print(f"Warning: No match found for stock name: {stock_name}")
        return None

    try:
        stock_ticker = match.ticker.iloc[0]
        stock = yf.Ticker(stock_ticker)
        hist = stock.history(period="1d")
        if hist.empty or "Close" not in hist.columns:
            print(f"Warning: No history found for ticker: {stock_ticker}")
            return None
        current_price = hist["Close"].iloc[-1]
        current_price = round(float(current_price), 3)
        return current_price
    except Exception as e:
        print(f"Error fetching price for {stock_name}: {e}")
        return None

def get_current_price_by_id(stock_id):
    match = stocks_df[stocks_df["stock_id"] == stock_id]

    if match.empty:
        print(f"Warning: No match found for stock id: {stock_id}")
        return None

    try:
        stock_ticker = match.ticker.iloc[0]
        stock = yf.Ticker(stock_ticker)
        hist = stock.history(period="1d")
        if hist.empty or "Close" not in hist.columns:
            print(f"Warning: No history found for ticker: {stock_ticker}")
            return None
        current_price = hist["Close"].iloc[-1]
        current_price = round(float(current_price), 3)
        return current_price
    except Exception as e:
        print(f"Error fetching price for stock ID {stock_id}: {e}")
        return None


if __name__ == "__main__":
    price = get_current_price_by_name("Lodha")
    print(f"Latest Price: {price}")

    price = get_current_price_by_id(1)
    print(f"Latest Price: {price}")



