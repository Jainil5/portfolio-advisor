import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import pandas as pd
import yfinance as yf
from backend.config import FUNDAMENTAL_DIR, PRICE_DIR, STOCKS_FILE

IST = ZoneInfo("Asia/Kolkata")


def clean_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '_', name)


def update_stock_master(output_file=STOCKS_FILE):
    url = "https://archives.nseindia.com/content/indices/ind_nifty200list.csv"
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

    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)

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

    os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
    updated_df["stock_id"] = updated_df["stock_id"].astype(int)
    updated_df.to_csv(output_file, index=False)

    return updated_df


def _normalize_history(data, stock_id):
    """Turn a yfinance history frame into rows keyed by IST trading date."""
    data = data.reset_index()
    data.rename(columns={data.columns[0]: "Date"}, inplace=True)
    data["Date"] = pd.to_datetime(data["Date"], utc=True).dt.tz_convert("Asia/Kolkata").dt.date
    data["stock_id"] = stock_id
    return data.drop_duplicates(subset=["Date"], keep="last").sort_values(by="Date")


def _last_saved_date(file_path):
    """Latest Date in a price CSV, or None if the file is missing/empty/unreadable."""
    if not os.path.exists(file_path):
        return None
    try:
        dates = pd.read_csv(file_path, usecols=["Date"])["Date"]
    except (ValueError, pd.errors.EmptyDataError):
        return None
    dates = pd.to_datetime(dates.astype(str).str[:10], errors="coerce").dropna()
    return dates.max().date() if not dates.empty else None


def _truncate_from(file_path, from_date):
    """Cut rows dated >= from_date off the end of a date-sorted CSV, in place."""
    with open(file_path, "r+", newline="") as f:
        f.readline()  # header
        cut = f.tell()
        while True:
            line = f.readline()
            if not line:
                break
            if line[:10] >= from_date.isoformat():
                break
            cut = f.tell()
        f.truncate(cut)


def fetch_price_single(row, output_dir=PRICE_DIR):
    ticker = row["yahoo_ticker"]
    try:
        stock_id = int(row["stock_id"])
        name = clean_name(row["company_name"])
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{stock_id}_{name}.csv")
        stock = yf.Ticker(ticker)
        today = datetime.now(IST).date()

        last_date = _last_saved_date(file_path)

        if last_date is None:
            data = stock.history(period="1y")
            if data is None or data.empty:
                return
            _normalize_history(data, stock_id).to_csv(file_path, index=False)
            return

        # Start from the last saved day (not the day after) so a candle saved
        # mid-session gets replaced by its final values, then fill every
        # missed day through today. yfinance's `end` is exclusive.
        data = stock.history(
            start=last_date.strftime("%Y-%m-%d"),
            end=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
        )
        if data is None or data.empty:
            return

        new_rows = _normalize_history(data, stock_id)
        new_rows = new_rows[new_rows["Date"] >= last_date]
        if new_rows.empty:
            return

        # Append, keeping the existing file's column order.
        columns = pd.read_csv(file_path, nrows=0).columns
        new_rows = new_rows.reindex(columns=columns)
        _truncate_from(file_path, new_rows["Date"].min())
        new_rows.to_csv(file_path, mode="a", header=False, index=False)
    except Exception as e:
        print(f"Price error for {ticker}: {e}")


def fetch_fundamental_single(row, output_dir=FUNDAMENTAL_DIR):
    name = row['company_name']
    try:
        ticker = row["yahoo_ticker"]
        stock_id = int(row["stock_id"])
        filename = clean_name(name)
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, f"{stock_id}_{filename}.csv")

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
