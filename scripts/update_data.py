#!/usr/bin/env python
"""Entry point: refresh the bronze/silver datasets from Yahoo Finance.

Usage:
    python scripts/update_data.py           # daily-idempotent (skips if updated today)
    python scripts/update_data.py --force   # always re-fetch
"""

import argparse
import sys
from pathlib import Path

# Allow running directly from a source checkout without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.pipelines.update_pipeline import update_finance_data


def main():
    parser = argparse.ArgumentParser(description="Update portfolio-advisor data")
    parser.add_argument("--force", action="store_true", help="Force re-fetch even if updated today")
    args = parser.parse_args()
    update_finance_data(force=args.force)


if __name__ == "__main__":
    main()
