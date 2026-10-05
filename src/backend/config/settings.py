"""Central configuration: project paths and environment-derived settings.

All data paths derive from DATA_ROOT, which resolves to <project root>/data by
default and can be overridden with an absolute STOCK_DATA_ROOT env var.
Nothing in this package may build data paths from the current working
directory.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# src/backend/config/settings.py -> repo root
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# Load .env from the project root regardless of the current working directory.
load_dotenv(PROJECT_ROOT / ".env")


def _resolve_data_root() -> str:
    raw = os.getenv("STOCK_DATA_ROOT", "").strip()
    if not raw:
        return str(PROJECT_ROOT / "data")
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path)


DATA_ROOT = _resolve_data_root()

# Bronze — raw data
BRONZE_DIR = os.path.join(DATA_ROOT, "bronze")

PRICE_DIR = os.path.join(BRONZE_DIR, "prices")

FUNDAMENTAL_DIR = os.path.join(BRONZE_DIR, "fundamentals")

STOCKS_FILE = os.path.join(BRONZE_DIR, "stocks.csv")

# Append-only buy/sell ledger (one row per transaction).
TRANSACTIONS_FILE = os.path.join(BRONZE_DIR, "transactions.csv")

# Rolling latest-news per stock (5 headlines + LLM summary), keyed by ticker.
NEWS_FILE = os.path.join(BRONZE_DIR, "stock_news.csv")

# Raw BSE corporate announcements (all listed companies), rolling window.
BSE_NEWS_FILE = os.path.join(BRONZE_DIR, "bse_news.csv")

# Pipeline metadata
METADATA_FILE = os.path.join(BRONZE_DIR, "metadata.json")

# Silver — processed data
SILVER_DIR = os.path.join(DATA_ROOT, "silver")

FEATURES_FILE = os.path.join(SILVER_DIR, "features.csv")

RECOMMENDATIONS_FILE = os.path.join(SILVER_DIR, "recommendations.csv")

# Derived holdings view, recomputed from the transactions ledger.
PORTFOLIO_FILE = os.path.join(SILVER_DIR, "portfolio.csv")
