import os

import pandas as pd

from backend.config import FUNDAMENTAL_DIR, PRICE_DIR, STOCKS_FILE, SILVER_DIR


def get_stock_file_map(price_dir=PRICE_DIR):
    stock_map = {}
    if not os.path.isdir(price_dir):
        return stock_map
    for file in os.listdir(price_dir):
        if file.endswith(".csv"):
            stock_id = int(file.split("_")[0])
            stock_map[stock_id] = os.path.join(price_dir, file)
    return stock_map


def compute_features(df):
    df = df.sort_values("Date")

    results = {}

    for period in [7, 30, 180]:
        temp = df.tail(period)

        if len(temp) < 2:
            results[f"return_{period}d"] = 0
            results[f"volatility_{period}d"] = 0
            results[f"avg_volume_{period}d"] = 0
            continue

        start = temp["Close"].iloc[0]
        end = temp["Close"].iloc[-1]

        results[f"return_{period}d"] = ((end / start) - 1) * 100 if start else 0
        results[f"volatility_{period}d"] = temp["Close"].pct_change().std() * (252 ** 0.5) * 100
        results[f"avg_volume_{period}d"] = temp["Volume"].mean()

    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    ma20 = df["MA20"].iloc[-1]
    ma50 = df["MA50"].iloc[-1]

    results["trend"] = "Bullish" if ma20 > ma50 else "Bearish"
    results["current_price"] = df["Close"].iloc[-1]
    results["daily_return"] = df["Close"].pct_change().iloc[-1] * 100

    results["52w_high"] = df["High"].tail(252).max()
    results["52w_low"] = df["Low"].tail(252).min()

    results["ma20"] = ma20
    results["ma50"] = ma50

    return results


def get_fundamental_features(stock_id, fundamental_dir=FUNDAMENTAL_DIR):
    try:
        if not os.path.isdir(fundamental_dir):
            return {}
        for f in os.listdir(fundamental_dir):
            if f.startswith(f"{stock_id}_"):
                file = os.path.join(fundamental_dir, f)
                df = pd.read_csv(file)

                if df.empty:
                    return {}

                df["report_date"] = pd.to_datetime(df["report_date"], utc=True, errors="coerce")
                df = df.dropna(subset=["report_date"])

                latest = df.sort_values("report_date").iloc[-1]

                debt = latest.get("Total Debt", 0)
                equity = latest.get("Stockholders Equity", 1)
                assets = latest.get("Total Assets", 1)
                liabilities = latest.get("Total Liabilities Net Minority Interest", 1)
                cash = latest.get("Cash And Cash Equivalents", 0)

                return {
                    "debt_to_equity": debt / equity if equity else 0,
                    "debt_to_assets": debt / assets if assets else 0,
                    "cash_ratio": cash / liabilities if liabilities else 0
                }
        return {}
    except Exception:
        return {}


def compute_score(row):
    score = 0

    r30 = row.get("return_30d", 0)
    r180 = row.get("return_180d", 0)
    vol = row.get("volatility_30d", 0)
    trend = row.get("trend", "")

    if r30 > 0:
        score += 1

    if r180 > 0:
        score += 1

    if trend == "Bullish":
        score += 1

    if 0 < vol < 20:
        score += 1
    return score


def generate_features():
    stock_map = get_stock_file_map()

    stocks_df = pd.read_csv(STOCKS_FILE)
    stocks_df["stock_id"] = pd.to_numeric(stocks_df["stock_id"], errors="coerce").astype(int)

    all_data = []

    for stock_id, file_path in stock_map.items():
        try:
            df = pd.read_csv(file_path)

            if "Date" not in df.columns:
                continue

            df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
            df = df.dropna(subset=["Date", "Close"])

            features = compute_features(df)
            features.update(get_fundamental_features(stock_id))
            features["stock_id"] = stock_id

            all_data.append(features)

        except Exception as e:
            print(f"Error for stock {stock_id}: {e}")

    final_df = pd.DataFrame(all_data).fillna(0)

    if final_df.empty:
        print("No data")
        return

    final_df = final_df.merge(stocks_df, on="stock_id", how="left")
    final_df["score"] = final_df.apply(compute_score, axis=1)

    final_df = final_df.sort_values("stock_id")

    cols = [
        "stock_id",
        "company_name",
        "ticker",
        "sector",
        "industry",
        "market_cap",
        "country",
        "exchange",
        "is_active",
        "current_price",
        "daily_return",
        "52w_high",
        "52w_low",
        "ma20",
        "ma50",
        "trend",
        "return_7d",
        "return_30d",
        "return_180d",
        "volatility_7d",
        "volatility_30d",
        "volatility_180d",
        "avg_volume_7d",
        "avg_volume_30d",
        "avg_volume_180d",
        "debt_to_equity",
        "debt_to_assets",
        "cash_ratio",
        "score"
    ]

    final_df = final_df[[c for c in cols if c in final_df.columns]]
    final_df.to_csv(os.path.join(SILVER_DIR, "features.csv"), index=False)
    print("Features generated")


if __name__ == "__main__":
    generate_features()
