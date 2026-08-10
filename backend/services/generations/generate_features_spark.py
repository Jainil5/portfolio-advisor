import os
import glob
import shutil

from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F

from backend.config import (
    PRICE_DIR,
    FUNDAMENTAL_DIR,
    STOCKS_FILE,
    SILVER_DIR,
)


# Spark

spark = (
    SparkSession.builder
    .appName("StockAdvisor-Features")
    .getOrCreate()
)


# Read prices
# ============================================================

def read_prices():

    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(os.path.join(PRICE_DIR, "*.csv"))
    )

    return (
        df
        .withColumn("_file", F.input_file_name())
        .withColumn(
            "stock_id",
            F.regexp_extract(
                "_file",
                r"/(\d+)_",
                1
            ).cast("int")
        )
        .withColumn("Date", F.to_timestamp("Date"))
        .withColumn("Close", F.col("Close").cast("double"))
        .withColumn("High", F.col("High").cast("double"))
        .withColumn("Low", F.col("Low").cast("double"))
        .withColumn("Volume", F.col("Volume").cast("double"))
        .filter(
            F.col("stock_id").isNotNull()
            & F.col("Date").isNotNull()
            & F.col("Close").isNotNull()
        )
        .drop("_file")
    )


# Technical features

def add_features(df):

    w = (
        Window
        .partitionBy("stock_id")
        .orderBy("Date")
    )

    w7 = w.rowsBetween(-6, 0)
    w30 = w.rowsBetween(-29, 0)
    w180 = w.rowsBetween(-179, 0)
    w20 = w.rowsBetween(-19, 0)
    w50 = w.rowsBetween(-49, 0)
    w252 = w.rowsBetween(-251, 0)

    # Daily return
    df = (
        df
        .withColumn("_prev", F.lag("Close").over(w))
        .withColumn(
            "_daily_return",
            F.when(
                F.col("_prev") != 0,
                F.col("Close") / F.col("_prev") - 1
            )
        )
    )

    # Returns
    for days, window in [
        (7, w7),
        (30, w30),
        (180, w180)
    ]:

        df = df.withColumn(
            f"return_{days}d",
            F.when(
                F.count("Close").over(window) < 2,
                0.0
            ).otherwise(
                (
                    F.col("Close")
                    / F.first(
                        "Close",
                        ignorenulls=True
                    ).over(window)
                    - 1
                ) * 100
            )
        )

    # Volatility
    for days, window in [
        (7, w7),
        (30, w30),
        (180, w180)
    ]:

        df = df.withColumn(
            f"volatility_{days}d",
            F.coalesce(
                F.stddev_samp(
                    "_daily_return"
                ).over(window)
                * F.sqrt(F.lit(252))
                * 100,
                F.lit(0.0)
            )
        )

    # Average volume
    for days, window in [
        (7, w7),
        (30, w30),
        (180, w180)
    ]:

        df = df.withColumn(
            f"avg_volume_{days}d",
            F.coalesce(
                F.avg("Volume").over(window),
                F.lit(0.0)
            )
        )

    # Moving averages
    df = (
        df
        .withColumn(
            "ma20",
            F.avg("Close").over(w20)
        )
        .withColumn(
            "ma50",
            F.avg("Close").over(w50)
        )
        .withColumn(
            "trend",
            F.when(
                F.col("ma20") > F.col("ma50"),
                "Bullish"
            ).otherwise("Bearish")
        )
    )

    # Current price / daily return
    df = (
        df
        .withColumn("current_price", F.col("Close"))
        .withColumn(
            "daily_return",
            F.col("_daily_return") * 100
        )
        .withColumn(
            "52w_high",
            F.max("High").over(w252)
        )
        .withColumn(
            "52w_low",
            F.min("Low").over(w252)
        )
    )

    # Keep latest date per stock
    latest = (
        Window
        .partitionBy("stock_id")
        .orderBy(F.col("Date").desc())
    )

    return (
        df
        .withColumn(
            "_rn",
            F.row_number().over(latest)
        )
        .filter(F.col("_rn") == 1)
        .drop(
            "_rn",
            "Date",
            "Close",
            "High",
            "Low",
            "Volume",
            "_prev",
            "_daily_return"
        )
    )


# Fundamentals

def read_fundamentals():

    df = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(
            os.path.join(
                FUNDAMENTAL_DIR,
                "*.csv"
            )
        )
    )

    df = (
        df
        .withColumn("_file", F.input_file_name())
        .withColumn(
            "stock_id",
            F.regexp_extract(
                "_file",
                r"/(\d+)_",
                1
            ).cast("int")
        )
        .withColumn(
            "report_date",
            F.to_timestamp("report_date")
        )
        .filter(
            F.col("stock_id").isNotNull()
            & F.col("report_date").isNotNull()
        )
    )

    # Latest report
    latest = (
        Window
        .partitionBy("stock_id")
        .orderBy(F.col("report_date").desc())
    )

    df = (
        df
        .withColumn(
            "_rn",
            F.row_number().over(latest)
        )
        .filter(F.col("_rn") == 1)
    )

    debt = F.coalesce(
        F.col("Total Debt").cast("double"),
        F.lit(0.0)
    )

    equity = F.coalesce(
        F.col("Stockholders Equity").cast("double"),
        F.lit(1.0)
    )

    assets = F.coalesce(
        F.col("Total Assets").cast("double"),
        F.lit(1.0)
    )

    liabilities = F.coalesce(
        F.col(
            "Total Liabilities Net Minority Interest"
        ).cast("double"),
        F.lit(1.0)
    )

    cash = F.coalesce(
        F.col(
            "Cash And Cash Equivalents"
        ).cast("double"),
        F.lit(0.0)
    )

    return (
        df
        .withColumn(
            "debt_to_equity",
            F.when(
                equity != 0,
                debt / equity
            ).otherwise(0.0)
        )
        .withColumn(
            "debt_to_assets",
            F.when(
                assets != 0,
                debt / assets
            ).otherwise(0.0)
        )
        .withColumn(
            "cash_ratio",
            F.when(
                liabilities != 0,
                cash / liabilities
            ).otherwise(0.0)
        )
        .select(
            "stock_id",
            "debt_to_equity",
            "debt_to_assets",
            "cash_ratio"
        )
    )


# Score

def add_score(df):

    return df.withColumn(
        "score",

        F.when(
            F.col("return_30d") > 0,
            1
        ).otherwise(0)

        +

        F.when(
            F.col("return_180d") > 0,
            1
        ).otherwise(0)

        +

        F.when(
            F.col("trend") == "Bullish",
            1
        ).otherwise(0)

        +

        F.when(
            (F.col("volatility_30d") > 0)
            &
            (F.col("volatility_30d") < 20),
            1
        ).otherwise(0)
    )


# ============================================================
# Generate
# ============================================================

def generate_features():

    print("Reading prices...")
    prices = read_prices()

    print("Calculating features...")
    features = add_features(prices)

    print("Reading fundamentals...")
    fundamentals = read_fundamentals()

    print("Reading stock metadata...")
    stocks = (
        spark.read
        .option("header", True)
        .option("inferSchema", True)
        .csv(STOCKS_FILE)
        .withColumn(
            "stock_id",
            F.col("stock_id").cast("int")
        )
    )

    # Join everything
    final = (
        features
        .join(
            fundamentals,
            "stock_id",
            "left"
        )
        .join(
            stocks,
            "stock_id",
            "left"
        )
        .fillna(0)
    )

    # Score
    final = add_score(final)

    # Column order
    columns = [
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

    columns = [
        c for c in columns
        if c in final.columns
    ]

    final = final.select(columns)

    # ========================================================
    # Write ONE features.csv
    # ========================================================

    output = os.path.join(
        SILVER_DIR,
        "features.csv"
    )

    temp = os.path.join(
        SILVER_DIR,
        "_features_temp"
    )

    if os.path.exists(output):
        os.remove(output)

    if os.path.exists(temp):
        shutil.rmtree(temp)

    (
        final
        .coalesce(1)
        .write
        .mode("overwrite")
        .option("header", True)
        .csv(temp)
    )

    part = glob.glob(
        os.path.join(
            temp,
            "part-*.csv"
        )
    )

    if not part:
        raise RuntimeError(
            "Spark did not create features.csv"
        )

    shutil.move(
        part[0],
        output
    )

    shutil.rmtree(temp)

    print(
        f"Features generated: {output}"
    )


# Main

if __name__ == "__main__":
    generate_features()