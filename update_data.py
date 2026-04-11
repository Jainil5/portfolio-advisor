import pandas as pd
import yfinance as yf
import os
import re
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from add_features import generate_features
from recommendations import generate_recommendations


STOCK_FILE = "data/stocks.csv"
PRICE_DIR = "data/prices"
FUNDAMENTAL_DIR = "data/fundamentals"

os.makedirs(PRICE_DIR, exist_ok=True)
os.makedirs(FUNDAMENTAL_DIR, exist_ok=True)


def clean_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


def update_stock_master():
    url = "https://archives.nseindia.com/content/indices/ind_nifty100list.csv"
    df = pd.read_csv(url)

    new_df = pd.DataFrame({
        "ticker": df["Symbol"] + ".NS",
        "company_name": df["Company Name"],
        "sector": df["Industry"],
        "industry": df["Industry"],
        "market_cap": "Large Cap",
        "country": "India",
        "exchange": "NSE",
        "yahoo_ticker": df["Symbol"] + ".NS"
    })

    if os.path.exists(STOCK_FILE):
        existing_df = pd.read_csv(STOCK_FILE)

        existing_df["stock_id"] = pd.to_numeric(existing_df["stock_id"], errors="coerce").fillna(0).astype(int)

        existing_df.set_index("ticker", inplace=True)
        new_df.set_index("ticker", inplace=True, drop=False)

        existing_df.update(new_df)

        existing_df.reset_index(inplace=True)
        new_df.reset_index(drop=True, inplace=True)

        existing_tickers = set(existing_df["ticker"])
        to_add = new_df[~new_df["ticker"].isin(existing_tickers)].copy()

        if not to_add.empty:
            max_id = existing_df["stock_id"].max() if not existing_df.empty else 0
            to_add["stock_id"] = range(max_id + 1, max_id + 1 + len(to_add))
            to_add["is_active"] = True
            updated_df = pd.concat([existing_df, to_add], ignore_index=True)
        else:
            updated_df = existing_df

    else:
        new_df["stock_id"] = range(1, len(new_df) + 1)
        new_df["is_active"] = True
        updated_df = new_df

    updated_df["stock_id"] = updated_df["stock_id"].astype(int)
    updated_df.to_csv(STOCK_FILE, index=False)

    return updated_df


def fetch_price_single(row):
    ticker = row["yahoo_ticker"]
    try:
        stock_id = int(row["stock_id"])
        name = clean_name(row["company_name"])
        file_path = f"{PRICE_DIR}/{stock_id}_{name}.csv"
        stock = yf.Ticker(ticker)
        today = datetime.today().date()

        if os.path.exists(file_path):
            existing = pd.read_csv(file_path)
            if not existing.empty:
                existing["Date"] = pd.to_datetime(existing["Date"], utc=True, errors="coerce")
                last_date = existing["Date"].max().date()
                start_date = last_date + timedelta(days=1)
                
                if start_date > today:
                    return
                data = stock.history(start=start_date.strftime("%Y-%m-%d"))
            else:
                data = stock.history(period="1y")
                existing = pd.DataFrame()
        else:
            data = stock.history(period="1y")
            existing = pd.DataFrame()

        if data is None or data.empty:
            return

        data = data.reset_index()
        data.rename(columns={data.columns[0]: "Date"}, inplace=True)
        data["Date"] = pd.to_datetime(data["Date"], utc=True)
        data["stock_id"] = stock_id

        combined = pd.concat([existing, data], ignore_index=True)
        combined["Date_Only"] = pd.to_datetime(combined["Date"], utc=True).dt.tz_convert('Asia/Kolkata').dt.date
        combined = combined.drop_duplicates(subset=["Date_Only"], keep="last").sort_values(by="Date_Only")
        
        combined["Date"] = combined["Date_Only"]
        combined.drop(columns=["Date_Only"], inplace=True)
        combined.to_csv(file_path, index=False)
    except Exception as e:
        print(f"Price error for {ticker}: {e}")


def fetch_fundamental_single(row):
    name = row['company_name']
    try:
        ticker = row["yahoo_ticker"]
        stock_id = int(row["stock_id"])
        filename = clean_name(name)
        file_path = f"{FUNDAMENTAL_DIR}/{stock_id}_{filename}.csv"

        stock = yf.Ticker(ticker)
        bs = stock.balance_sheet.T
        if bs is None or bs.empty:
            return

        bs.reset_index(inplace=True)
        bs.rename(columns={"index": "report_date"}, inplace=True)
        bs["report_date"] = pd.to_datetime(bs["report_date"], utc=True).dt.date
        
        required_cols = [
            "report_date", "Total Debt", "Total Liabilities Net Minority Interest",
            "Total Assets", "Stockholders Equity", "Cash And Cash Equivalents"
        ]
        bs = bs[[c for c in required_cols if c in bs.columns]]

        if os.path.exists(file_path):
            existing = pd.read_csv(file_path)
            existing["report_date"] = pd.to_datetime(existing["report_date"]).dt.date
            if bs["report_date"].max() <= existing["report_date"].max():
                return
            combined = pd.concat([existing, bs], ignore_index=True)
            combined["rep_dt"] = pd.to_datetime(combined["report_date"])
            combined = combined.drop_duplicates(subset=["report_date"], keep="last").sort_values(by="rep_dt")
            combined.drop(columns=["rep_dt"], inplace=True)
            combined.to_csv(file_path, index=False)
        else:
            bs.sort_values(by="report_date").to_csv(file_path, index=False)
    except Exception as e:
        print(f"Fundamental error for {name}: {e}")


def run_data_pipeline():
    print("🚀 Initializing Data Pipeline...")
    stocks_df = update_stock_master()
    stocks = [row for _, row in stocks_df.iterrows()]

    print(f"📊 Updating Prices for {len(stocks)} stocks (Parallel)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(fetch_price_single, stocks)

    print(f"💎 Updating Fundamentals for {len(stocks)} stocks (Parallel)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(fetch_fundamental_single, stocks)

    print("\n🧠 Generating AI Models & Features...")
    generate_features()
    generate_recommendations()

    print("\n✨ Portfolio Advisor Data is Refresh!")


if __name__ == "__main__":
    run_data_pipeline()