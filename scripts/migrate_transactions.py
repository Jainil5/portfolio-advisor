#!/usr/bin/env python
"""One-off migration: turn the legacy single-file holdings CSV into a proper
append-only transaction ledger plus a derived portfolio file.

The pre-Tier-1 ``transactions.csv`` actually stored net holdings (columns
``stock_id, stock_name, quantity, buy_price, buy_date, asset_type``) with a
different schema than the writers expected — and some rows had a blank
``stock_id``. This script reconstructs a valid ledger (one ``buy`` per legacy
row, resolving any missing stock_id from the stocks master) and then derives
``portfolio.csv`` from it.

Safe to re-run: if the ledger is already in the new format it only refreshes
the derived portfolio.

Usage:
    python scripts/migrate_transactions.py --dry-run
    python scripts/migrate_transactions.py
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.config import settings
from backend.data import repository
from backend.models import Transaction
from backend.services import user_transactions
from backend.utils.market_data import get_id_by_name


def _resolve_stock_id(raw_id, stock_name):
    try:
        if pd.notna(raw_id) and str(raw_id).strip() != "":
            return int(float(raw_id))
    except (ValueError, TypeError):
        pass
    return get_id_by_name(stock_name)


def _parse_date(value):
    try:
        if pd.notna(value) and str(value).strip() != "":
            return pd.to_datetime(value).date()
    except Exception:
        pass
    return date.today()


def build_ledger(old: pd.DataFrame):
    transactions = []
    skipped = []
    for _, row in old.iterrows():
        stock_name = row.get("stock_name") or row.get("name")
        sid = _resolve_stock_id(row.get("stock_id"), stock_name)
        if sid is None or stock_name is None:
            skipped.append(stock_name or row.to_dict())
            continue
        transactions.append(
            Transaction(
                stock_id=int(sid),
                stock_name=str(stock_name),
                action="buy",
                quantity=float(row["quantity"]),
                price=float(row["buy_price"]),
                date=_parse_date(row.get("buy_date")),
            )
        )
    return transactions, skipped


def main():
    parser = argparse.ArgumentParser(description="Migrate legacy transactions CSV to a ledger + portfolio")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    old = repository.read_csv_safe(settings.TRANSACTIONS_FILE)
    if old.empty:
        print("No existing transactions; nothing to migrate.")
        return

    if "action" in old.columns and "transaction_id" in old.columns:
        print("Ledger already in new format; refreshing derived portfolio.")
        if not args.dry_run:
            user_transactions.update_portfolio()
        return

    transactions, skipped = build_ledger(old)

    print(f"Legacy rows: {len(old)} -> new transactions: {len(transactions)}")
    for t in transactions:
        print(f"  {t.action} {t.quantity} x {t.stock_name} (id={t.stock_id}) @ {t.price}")
    if skipped:
        print(f"WARNING: skipped {len(skipped)} rows (unresolvable stock_id/name): {skipped}")

    if args.dry_run:
        print("\nDry run: no files written.")
        return

    ledger = Transaction.dataframe(transactions)
    repository.write_csv(ledger, settings.TRANSACTIONS_FILE)
    portfolio = user_transactions.update_portfolio()
    print(f"\nWrote ledger -> {settings.TRANSACTIONS_FILE}")
    print(f"Wrote portfolio -> {settings.PORTFOLIO_FILE}")
    print(portfolio.to_string(index=False))


if __name__ == "__main__":
    main()
