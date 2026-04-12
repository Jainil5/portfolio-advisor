import pandas as pd
import yfinance as yf

stocks_df = pd.read_csv("data/stocks.csv")

def get_current_price_by_name(stock_name):
   
    # 1. Convert to lower case
    search_name = stock_name
    
    for i in search_name.split():
        match = stocks_df[stocks_df["company_name"] == i]
        if not match.empty:
            break
    
    if match.empty:
        match = stocks_df[stocks_df["company_name"].str.contains(search_name)]

    stock_ticker = match.ticker.iloc[0]
    stock = yf.Ticker(stock_ticker)
    current_price = stock.history(period="1d")["Close"].iloc[-1]
    current_price = round(current_price,3)    
    date = stock.history(period="1d").index[0]
    return current_price

def get_current_price_by_id(stock_id):
   
    match = stocks_df[stocks_df["stock_id"] == stock_id]

    # if match.empty:
    #     match = stocks_df[stocks_df["company_name"].str.lower().str.contains(search_name)]

    stock_ticker = match.ticker.iloc[0]
    stock = yf.Ticker(stock_ticker)
    current_price = stock.history(period="1d")["Close"].iloc[-1]
    current_price = round(current_price,3)    
    date = stock.history(period="1d").index[0]
    return current_price


if __name__ == "__main__":
    price = get_current_price_by_name("Reliance Industries Ltd.")
    print(f"Latest Price: {price}")

    price = get_current_price_by_id(1)
    print(f"Latest Price: {price}")



