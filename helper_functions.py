import pandas as pd
import yfinance as yf

stocks_df = pd.read_csv("data/stocks.csv")

def get_current_price_by_name(stock_name):
   
    # 1. Convert to lower case
    search_name = stock_name.lower()
    
    # Search for the stock name in the company_name column (case-insensitive)
    # We check for exact match first, then fallback to partial match
    for i in search_name.split():
        match = stocks_df[stocks_df["company_name"].str.lower() == i]
        if not match.empty:
            break
    
    if match.empty:
        # Fallback to partial match if exact match fails
        match = stocks_df[stocks_df["company_name"].str.lower().str.contains(search_name)]

    stock_ticker = match.ticker.iloc[0]
    stock = yf.Ticker(stock_ticker)
    current_price = stock.history(period="1d")["Close"].iloc[-1]
    current_price = round(current_price,3)    
    date = stock.history(period="1d").index[0]
    return current_price,date

if __name__ == "__main__":
    price,date = get_current_price_by_name("Reliance")
    print(f"Latest Price: {price} for date: {date}")
