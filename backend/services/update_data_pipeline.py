import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from backend.services.fetch_stocks_data import (
    fetch_fundamental_single,
    fetch_price_single,
    update_stock_master,
)
from backend.services.recommendations import generate_recommendations

METADATA_FILE = "data/metadata.json"
MAX_WORKERS = 10
FEATURE_ENGINE = os.getenv("FEATURE_ENGINE", "pandas").lower()

os.makedirs("data", exist_ok=True)


def _get_feature_generator():
    if FEATURE_ENGINE == "spark":
        from backend.services.generate_features_spark import generate_features as spark_generate
        return spark_generate
    from backend.services.generate_features_pd import generate_features
    return generate_features


def load_metadata():
    if not os.path.exists(METADATA_FILE):
        return None
    with open(METADATA_FILE, "r") as file:
        return json.load(file)


def save_metadata():
    metadata = {"last_updated": datetime.today().strftime("%Y-%m-%d")}
    with open(METADATA_FILE, "w") as file:
        json.dump(metadata, file, indent=4)


def update_required():
    metadata = load_metadata()
    if metadata is None:
        return True
    return metadata.get("last_updated") != datetime.today().strftime("%Y-%m-%d")


def _fetch_stock_data(row):
    fetch_price_single(row)
    fetch_fundamental_single(row)


def update_stocks():
    print("\nUpdating Stocks...\n")

    print("Updating Stock Master Dataset...")
    stocks_df = update_stock_master()
    stocks = stocks_df.to_dict("records")

    print(f"Updating Prices and Fundamentals for {len(stocks)} Stocks...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(_fetch_stock_data, row): row for row in stocks}
        for future in as_completed(futures):
            row = futures[future]
            try:
                future.result()
            except Exception as exc:
                print(f"Stock update error for {row.get('yahoo_ticker', row.get('stock_id'))}: {exc}")

    print("\nStocks Updated Successfully.\n")


def update_recommendations():
    print("\nGenerating Features...")
    generate_features = _get_feature_generator()
    generate_features()

    print("Generating Recommendations...")
    generate_recommendations()
    print("\nRecommendations Updated Successfully.\n")



def update_finance_data(force=False):
    print("\nChecking Finance Data...\n")

    if not force and not update_required():
        print("Finance Data is already updated today.\n")
        return

    try:
        print("\nStarting Finance Update Pipeline...\n")
        update_stocks()
        update_recommendations()
        save_metadata()
        print("\nFinance Data Updated Successfully.\n")
    except Exception as e:
        print("\nFinance Update Failed.\n")
        print(f"Error : {e}")
        raise


if __name__ == "__main__":
    update_finance_data()
