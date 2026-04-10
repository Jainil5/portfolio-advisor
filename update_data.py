import pandas as pd
import yfinance as yf
import os
import re
from datetime import datetime, timedelta
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
    try:
        ticker = row["yahoo_ticker"]
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
        else:
            data = stock.history(period="1y")

        if data is None or data.empty:
            return

        data = data.reset_index()
        data.rename(columns={data.columns[0]: "Date"}, inplace=True)

        data["Date"] = pd.to_datetime(data["Date"], utc=True).dt.date
        data["stock_id"] = stock_id

        data.to_csv(
            file_path,
            mode='a' if os.path.exists(file_path) else 'w',
            header=not os.path.exists(file_path),
            index=False
        )

    except Exception as e:
        print(f"Price error for {ticker}: {e}")


def fetch_fundamental_single(row):
    try:
        ticker = row["yahoo_ticker"]
        stock_id = int(row["stock_id"])
        name = clean_name(row["company_name"])

        file_path = f"{FUNDAMENTAL_DIR}/{stock_id}_{name}.csv"

        stock = yf.Ticker(ticker)
        bs = stock.balance_sheet.T

        if bs is None or bs.empty:
            return

        bs.reset_index(inplace=True)
        bs.rename(columns={"index": "report_date"}, inplace=True)

        bs["report_date"] = pd.to_datetime(bs["report_date"], utc=True, errors="coerce")
        bs = bs.dropna(subset=["report_date"])

        required_cols = [
            "report_date",
            "Total Debt",
            "Stockholders Equity",
            "Total Assets",
            "Total Liabilities Net Minority Interest",
            "Cash And Cash Equivalents"
        ]

        bs = bs[[col for col in required_cols if col in bs.columns]]

        if os.path.exists(file_path):
            existing = pd.read_csv(file_path)

            existing["report_date"] = pd.to_datetime(existing["report_date"], utc=True, errors="coerce")

            last_date = existing["report_date"].max()

            if last_date is not None:
                bs = bs[bs["report_date"] > last_date]

            combined = pd.concat([existing, bs], ignore_index=True)
        else:
            combined = bs

        combined = combined.drop_duplicates(subset=["report_date"])
        combined = combined.sort_values("report_date")

        combined.to_csv(file_path, index=False)

    except Exception as e:
        print(f"Fundamental error for {row['company_name']}: {e}")


def run_data_pipeline():
    print("Updating stock master...")
    stocks_df = update_stock_master()

    print("Updating prices...")
    for _, row in stocks_df.iterrows():
        fetch_price_single(row)

    print("Updating fundamentals...")
    for _, row in stocks_df.iterrows():
        fetch_fundamental_single(row)

    print("\nGenerating final AI datasets...")
    generate_features()
    generate_recommendations()

    print("\nAll data updated successfully")


if __name__ == "__main__":
    run_data_pipeline()