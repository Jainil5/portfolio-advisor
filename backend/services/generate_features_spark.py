"""PySpark feature generation — mirrors add_features.py logic."""

import os

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
import shutil
PRICE_DIR = "data/prices"
FEATURES_FILE = "data/features.csv"
STOCKS_FILE = "data/stocks.csv"
FUNDAMENTAL_DIR = "data/fundamentals"

PERIODS = [7, 30, 180]
OUTPUT_COLS = [
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
    "score",
]


def create_spark():
    return (
        SparkSession.builder
        .appName("portfolio-advisor-features")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )


def load_fundamental_features(spark):
    """Load latest fundamental ratios per stock_id (small dataset, pre-Spark)."""
    import pandas as pd

    rows = []
    if not os.path.isdir(FUNDAMENTAL_DIR):
        return spark.createDataFrame([], "stock_id int, debt_to_equity double, debt_to_assets double, cash_ratio double")

    for filename in os.listdir(FUNDAMENTAL_DIR):
        if not filename.endswith(".csv"):
            continue
        try:
            stock_id = int(filename.split("_")[0])
            df = pd.read_csv(os.path.join(FUNDAMENTAL_DIR, filename))
            if df.empty:
                continue

            df["report_date"] = pd.to_datetime(df["report_date"], utc=True, errors="coerce")
            df = df.dropna(subset=["report_date"])
            if df.empty:
                continue

            latest = df.sort_values("report_date").iloc[-1]
            debt = latest.get("Total Debt", 0) or 0
            equity = latest.get("Stockholders Equity", 1) or 1
            assets = latest.get("Total Assets", 1) or 1
            liabilities = latest.get("Total Liabilities Net Minority Interest", 1) or 1
            cash = latest.get("Cash And Cash Equivalents", 0) or 0

            rows.append(
                {
                    "stock_id": stock_id,
                    "debt_to_equity": float(debt / equity if equity else 0),
                    "debt_to_assets": float(debt / assets if assets else 0),
                    "cash_ratio": float(cash / liabilities if liabilities else 0),
                }
            )
        except Exception:
            continue

    if not rows:
        return spark.createDataFrame([], "stock_id int, debt_to_equity double, debt_to_assets double, cash_ratio double")

    return spark.createDataFrame(rows)


def compute_price_features(spark):
    price_glob = os.path.join(PRICE_DIR, "*.csv")
    if not os.path.isdir(PRICE_DIR) or not os.listdir(PRICE_DIR):
        return None

    prices = (
        spark.read.option("header", True)
        .option("inferSchema", True)
        .csv(price_glob)
        .withColumn("stock_id", F.regexp_extract(F.input_file_name(), r"/(\d+)_", 1).cast("int"))
        .withColumn("Date", F.to_timestamp("Date"))
        .filter(F.col("Date").isNotNull() & F.col("Close").isNotNull())
    )

    for col in ("Close", "High", "Low", "Volume"):
        prices = prices.withColumn(col, F.col(col).cast("double"))

    w_asc = Window.partitionBy("stock_id").orderBy("Date")
    w_desc = Window.partitionBy("stock_id").orderBy(F.col("Date").desc())

    prices = (
        prices.withColumn("daily_pct", (F.col("Close") - F.lag("Close").over(w_asc)) / F.lag("Close").over(w_asc))
        .withColumn("MA20", F.avg("Close").over(w_asc.rowsBetween(-19, 0)))
        .withColumn("MA50", F.avg("Close").over(w_asc.rowsBetween(-49, 0)))
        .withColumn("row_count", F.count("Close").over(Window.partitionBy("stock_id")))
        .withColumn("rn_desc", F.row_number().over(w_desc))
    )

    feature_exprs = {
        "current_price": F.col("Close"),
        "daily_return": F.coalesce(F.col("daily_pct") * 100, F.lit(0.0)),
        "52w_high": F.max("High").over(w_asc.rowsBetween(-251, 0)),
        "52w_low": F.min("Low").over(w_asc.rowsBetween(-251, 0)),
        "ma20": F.col("MA20"),
        "ma50": F.col("MA50"),
        "trend": F.when(F.col("MA20") > F.col("MA50"), F.lit("Bullish")).otherwise(F.lit("Bearish")),
    }

    for period in PERIODS:
        window_spec = w_asc.rowsBetween(-(period - 1), 0)
        start_close = F.first("Close").over(window_spec)
        has_enough = F.col("row_count") >= 2

        feature_exprs[f"return_{period}d"] = F.when(
            has_enough,
            F.when(start_close.isNotNull() & (start_close != 0), (F.col("Close") / start_close - 1) * 100).otherwise(F.lit(0.0)),
        ).otherwise(F.lit(0.0))

        vol_window_end = max(period - 2, 0)
        feature_exprs[f"volatility_{period}d"] = F.when(
            has_enough,
            F.coalesce(
                F.stddev("daily_pct").over(w_asc.rowsBetween(-vol_window_end, 0)) * (252 ** 0.5) * 100,
                F.lit(0.0),
            ),
        ).otherwise(F.lit(0.0))

        feature_exprs[f"avg_volume_{period}d"] = F.when(
            has_enough,
            F.coalesce(F.avg("Volume").over(window_spec), F.lit(0.0)),
        ).otherwise(F.lit(0.0))

    for name, expr in feature_exprs.items():
        prices = prices.withColumn(name, expr)

    latest = prices.filter(F.col("rn_desc") == 1)
    select_cols = [F.col("stock_id")] + [F.col(name) for name in feature_exprs]
    return latest.select(*select_cols)


def add_score(df):
    vol_ok = (F.col("volatility_30d") > 0) & (F.col("volatility_30d") < 20)
    return df.withColumn(
        "score",
        (F.when(F.col("return_30d") > 0, 1).otherwise(0))
        + (F.when(F.col("return_180d") > 0, 1).otherwise(0))
        + (F.when(F.col("trend") == "Bullish", 1).otherwise(0))
        + (F.when(vol_ok, 1).otherwise(0)),
    )


def generate_features(spark=None):
    own_spark = spark is None

    if own_spark:
        spark = create_spark()

    try:
        print("Loading price data...")
        price_features = compute_price_features(spark)

        if price_features is None:
            print("No price data found.")
            return None

        # Avoid converting to RDD
        if price_features.limit(1).count() == 0:
            print("No price data found.")
            return None

        print("Loading fundamentals...")
        fundamentals = load_fundamental_features(spark)

        print("Loading stock master...")
        stocks = (
            spark.read
            .option("header", True)
            .option("inferSchema", True)
            .csv(STOCKS_FILE)
            .withColumn("stock_id", F.col("stock_id").cast("int"))
        )

        print("Generating final feature dataset...")

        result = (
            price_features
            .join(fundamentals, on="stock_id", how="left")
            .join(stocks, on="stock_id", how="left")
            .transform(add_score)
            .fillna(0)
            .orderBy("stock_id")
        )

        present_cols = [c for c in OUTPUT_COLS if c in result.columns]

        # Cache so Spark doesn't recompute
        result = result.select(*present_cols).cache()

        count = result.count()

        print("Saving features.csv...")

        temp_dir = "data/features_tmp"

        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

        (
            result
            .coalesce(1)
            .write
            .mode("overwrite")
            .option("header", True)
            .csv(temp_dir)
        )

        part_files = [
            f
            for f in os.listdir(temp_dir)
            if f.startswith("part-") and f.endswith(".csv")
        ]

        if not part_files:
            raise FileNotFoundError("Spark did not generate features.csv")

        part_file = part_files[0]

        if os.path.exists(FEATURES_FILE):
            os.remove(FEATURES_FILE)

        os.rename(
            os.path.join(temp_dir, part_file),
            FEATURES_FILE,
        )

        shutil.rmtree(temp_dir)

        print(f"Features generated successfully ({count} stocks)")

        return result

    finally:
        if own_spark:
            spark.stop()

if __name__ == "__main__":
    generate_features()
