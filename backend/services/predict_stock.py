"""Time-series prediction for a single stock from 1 year of OHLCV data."""

import argparse
import glob
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.metrics import accuracy_score, mean_absolute_error
from sklearn.model_selection import train_test_split

PRICE_DIR = "data/prices"
STOCKS_FILE = "data/stocks.csv"
LOOKBACK = 5


def find_price_file(stock_id=None, ticker=None):
    if stock_id is not None:
        matches = glob.glob(os.path.join(PRICE_DIR, f"{stock_id}_*.csv"))
        if matches:
            return matches[0]

    if ticker and os.path.exists(STOCKS_FILE):
        stocks = pd.read_csv(STOCKS_FILE)
        row = stocks[stocks["ticker"] == ticker]
        if not row.empty:
            sid = int(row.iloc[0]["stock_id"])
            matches = glob.glob(os.path.join(PRICE_DIR, f"{sid}_*.csv"))
            if matches:
                return matches[0]

    raise FileNotFoundError("Price file not found. Provide --stock-id or --ticker.")


def load_ohlcv(path):
    df = pd.read_csv(path)
    df["Date"] = pd.to_datetime(df["Date"], utc=True, errors="coerce")
    df = df.dropna(subset=["Date", "Close"]).sort_values("Date")
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.tail(252).reset_index(drop=True)


def build_features(df):
    out = df.copy()
    out["return_1d"] = out["Close"].pct_change()
    out["return_5d"] = out["Close"].pct_change(5)
    out["ma5"] = out["Close"].rolling(5).mean()
    out["ma20"] = out["Close"].rolling(20).mean()
    out["volatility_10d"] = out["return_1d"].rolling(10).std()
    out["volume_ratio"] = out["Volume"] / out["Volume"].rolling(10).mean()
    out["high_low_range"] = (out["High"] - out["Low"]) / out["Close"]
    out["target_price"] = out["Close"].shift(-1)
    out["target_direction"] = (out["target_price"] > out["Close"]).astype(int)
    return out.dropna().reset_index(drop=True)


def train_and_predict(df):
    features = build_features(df)
    if len(features) < 30:
        raise ValueError("Need at least ~30 trading days after feature engineering.")

    feature_cols = [
        "Open", "High", "Low", "Close", "Volume",
        "return_1d", "return_5d", "ma5", "ma20",
        "volatility_10d", "volume_ratio", "high_low_range",
    ]
    feature_cols = [c for c in feature_cols if c in features.columns]

    X = features[feature_cols]
    y_price = features["target_price"]
    y_dir = features["target_direction"]

    X_train, X_test, y_price_train, y_price_test, y_dir_train, y_dir_test = train_test_split(
        X, y_price, y_dir, test_size=0.2, shuffle=False
    )

    reg = GradientBoostingRegressor(random_state=42)
    clf = GradientBoostingClassifier(random_state=42)
    reg.fit(X_train, y_price_train)
    clf.fit(X_train, y_dir_train)

    price_pred = reg.predict(X_test)
    dir_pred = clf.predict(X_test)
    dir_proba = clf.predict_proba(X_test)[:, 1]

    metrics = {
        "mae": mean_absolute_error(y_price_test, price_pred),
        "direction_accuracy": accuracy_score(y_dir_test, dir_pred),
    }

    latest = features.iloc[[-1]][feature_cols]
    next_price = float(reg.predict(latest)[0])
    rise_prob = float(clf.predict_proba(latest)[0, 1])
    current_price = float(df["Close"].iloc[-1])

    return {
        "current_price": current_price,
        "predicted_next_close": next_price,
        "predicted_change_pct": ((next_price / current_price) - 1) * 100 if current_price else 0,
        "rise_probability": rise_prob,
        "predicted_direction": "RISE" if rise_prob >= 0.5 else "FALL",
        "metrics": metrics,
        "last_date": str(df["Date"].iloc[-1].date()),
    }


def predict(stock_id=None, ticker=None):
    path = find_price_file(stock_id=stock_id, ticker=ticker)
    df = load_ohlcv(path)
    result = train_and_predict(df)
    result["price_file"] = path
    return result


def main():
    parser = argparse.ArgumentParser(description="Predict next-day price/direction from OHLCV history")
    parser.add_argument("--stock-id", type=int, help="Stock ID from stocks.csv")
    parser.add_argument("--ticker", type=str, help="Ticker symbol, e.g. RELIANCE.NS")
    args = parser.parse_args()

    if not args.stock_id and not args.ticker:
        parser.error("Provide --stock-id or --ticker")

    out = predict(stock_id=args.stock_id, ticker=args.ticker)
    print(f"File: {out['price_file']}")
    print(f"Last date: {out['last_date']}")
    print(f"Current close: {out['current_price']:.2f}")
    print(f"Predicted next close: {out['predicted_next_close']:.2f} ({out['predicted_change_pct']:+.2f}%)")
    print(f"Direction: {out['predicted_direction']} (rise prob: {out['rise_probability']:.1%})")
    print(f"Holdout MAE: {out['metrics']['mae']:.2f}")
    print(f"Holdout direction accuracy: {out['metrics']['direction_accuracy']:.1%}")


if __name__ == "__main__":
    main()
