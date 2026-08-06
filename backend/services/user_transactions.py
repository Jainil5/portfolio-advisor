import os
import uuid
from datetime import datetime

import pandas as pd

# ==========================================================
# Paths
# ==========================================================

TRANSACTIONS_FILE = "data/transactions.csv"
PORTFOLIO_FILE = "data/portfolio.csv"

STOCKS_FILE = "data/stocks.csv"
MF_FILE = "data/mutual_funds.csv"

os.makedirs("data", exist_ok=True)


# ==========================================================
# Helpers
# ==========================================================


def load_csv(path: str) -> pd.DataFrame:
    """Safely load a CSV file."""

    if os.path.exists(path):
        return pd.read_csv(path)

    return pd.DataFrame()


def save_csv(df: pd.DataFrame, path: str):
    """Save dataframe."""

    df.to_csv(path, index=False)


def generate_transaction_id():
    """Generate a short transaction id."""

    return str(uuid.uuid4())[:8]


# ==========================================================
# Asset Helpers
# ==========================================================


def get_stock_name(stock_id: int) -> str:
    """Get stock name using stock id."""

    stocks = load_csv(STOCKS_FILE)

    row = stocks[
        stocks["stock_id"] == stock_id
    ]

    if row.empty:
        raise ValueError(
            "Invalid Stock ID."
        )

    return row.iloc[0]["stock_name"]


def get_mutual_fund_name(mf_id: int) -> str:
    """Get mutual fund name."""

    mfs = load_csv(MF_FILE)

    row = mfs[
        mfs["mf_id"] == mf_id
    ]

    if row.empty:
        raise ValueError(
            "Invalid Mutual Fund ID."
        )

    return row.iloc[0]["scheme_name"]


# ==========================================================
# Transactions
# ==========================================================


def add_transaction(
    asset_type: str,
    asset_id: int,
    quantity: float,
    price: float,
    action: str,
):
    """
    Add a transaction.

    asset_type:
        - stock
        - mf

    action:
        - buy
        - sell
    """

    if asset_type not in {
        "stock",
        "mf",
    }:
        raise ValueError(
            "Invalid asset type."
        )

    if action not in {
        "buy",
        "sell",
    }:
        raise ValueError(
            "Invalid action."
        )

    if quantity <= 0:
        raise ValueError(
            "Quantity must be positive."
        )

    if price <= 0:
        raise ValueError(
            "Price must be positive."
        )

    if asset_type == "stock":
        name = get_stock_name(asset_id)

    else:
        name = get_mutual_fund_name(
            asset_id
        )

    transaction = {

        "transaction_id":
            generate_transaction_id(),

        "asset_type":
            asset_type,

        "asset_id":
            asset_id,

        "name":
            name,

        "action":
            action,

        "quantity":
            quantity,

        "price":
            price,

        "date":
            datetime.now().strftime(
                "%Y-%m-%d"
            ),
    }

    transactions = load_csv(
        TRANSACTIONS_FILE
    )

    transactions = pd.concat(

        [
            transactions,
            pd.DataFrame(
                [transaction]
            )
        ],

        ignore_index=True,

    )

    save_csv(
        transactions,
        TRANSACTIONS_FILE,
    )

    update_portfolio()

    print(
        f"{action.upper()} Successful : "
        f"{quantity} {name}"
    )


# ==========================================================
# Portfolio
# ==========================================================


def update_portfolio():
    """
    Update the portfolio snapshot
    using transactions.csv.
    """

    transactions = load_csv(
        TRANSACTIONS_FILE
    )

    if transactions.empty:

        save_csv(
            pd.DataFrame(),
            PORTFOLIO_FILE,
        )

        return

    portfolio = []

    grouped = transactions.groupby(

        [
            "asset_type",
            "asset_id",
            "name",
        ]

    )

    for (

        asset_type,
        asset_id,
        name,

    ), group in grouped:

        quantity = 0
        total_investment = 0

        for _, row in group.iterrows():

            qty = float(
                row["quantity"]
            )

            price = float(
                row["price"]
            )

            action = row["action"]

            if action == "buy":

                quantity += qty

                total_investment += (
                    qty * price
                )

            else:

                quantity -= qty

                total_investment -= (
                    qty * price
                )

        # Completely sold.

        if quantity <= 0:
            continue

        avg_price = round(
            total_investment / quantity,
            2,
        )

        portfolio.append(

            {
                "asset_type":
                    asset_type,

                "asset_id":
                    asset_id,

                "name":
                    name,

                "quantity":
                    round(
                        quantity,
                        4,
                    ),

                "avg_buy_price":
                    avg_price,

                "total_investment":
                    round(
                        total_investment,
                        2,
                    ),
            }

        )

    portfolio_df = pd.DataFrame(
        portfolio
    )

    save_csv(
        portfolio_df,
        PORTFOLIO_FILE,
    )


# ==========================================================
# Public Functions
# ==========================================================


def buy_stock(
    stock_id: int,
    quantity: float,
    price: float,
):
    """Buy a stock."""

    add_transaction(
        asset_type="stock",
        asset_id=stock_id,
        quantity=quantity,
        price=price,
        action="buy",
    )


def sell_stock(
    stock_id: int,
    quantity: float,
    price: float,
):
    """Sell a stock."""

    add_transaction(
        asset_type="stock",
        asset_id=stock_id,
        quantity=quantity,
        price=price,
        action="sell",
    )


def buy_mutual_fund(
    mf_id: int,
    units: float,
    nav: float,
):
    """Buy a mutual fund."""

    add_transaction(
        asset_type="mf",
        asset_id=mf_id,
        quantity=units,
        price=nav,
        action="buy",
    )


def sell_mutual_fund(
    mf_id: int,
    units: float,
    nav: float,
):
    """Sell a mutual fund."""

    add_transaction(
        asset_type="mf",
        asset_id=mf_id,
        quantity=units,
        price=nav,
        action="sell",
    )


# ==========================================================
# Retrieval Functions
# ==========================================================


def get_transactions():
    """Return all transactions."""

    return load_csv(
        TRANSACTIONS_FILE
    )


def get_portfolio():
    """Return portfolio."""

    return load_csv(
        PORTFOLIO_FILE
    )


def delete_transaction(
    transaction_id: str,
):
    """
    Delete a transaction.
    """

    transactions = load_csv(
        TRANSACTIONS_FILE
    )

    if transactions.empty:
        return

    transactions = transactions[

        transactions[
            "transaction_id"
        ] != transaction_id

    ]

    save_csv(
        transactions,
        TRANSACTIONS_FILE,
    )

    update_portfolio()


def clear_portfolio():
    """
    Delete everything.
    """

    if os.path.exists(
        TRANSACTIONS_FILE
    ):
        os.remove(
            TRANSACTIONS_FILE
        )

    if os.path.exists(
        PORTFOLIO_FILE
    ):
        os.remove(
            PORTFOLIO_FILE
        )

    print(
        "Portfolio Cleared."
    )


# ==========================================================
# Testing
# ==========================================================

if __name__ == "__main__":

    # Stocks
    buy_stock(
        stock_id=1,
        quantity=10,
        price=1500,
    )

    buy_stock(
        stock_id=1,
        quantity=5,
        price=1700,
    )

    sell_stock(
        stock_id=1,
        quantity=3,
        price=1900,
    )

    # Mutual Funds
    # buy_mutual_fund(
    #     mf_id=10,
    #     units=25,
    #     nav=75,
    # )

    # sell_mutual_fund(
    #     mf_id=10,
    #     units=5,
    #     nav=100,
    # )

    print("\nPortfolio\n")
    print(get_portfolio())

    print("\nTransactions\n")
    print(get_transactions())