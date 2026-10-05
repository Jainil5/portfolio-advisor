"""Map NSE symbols from the stock list to BSE scrip codes.

    python -m backend.news.scrip_map            # resolve all
    python -m backend.news.scrip_map --only-unresolved

Primary lookup is bse.getScripCode(symbol). If that fails, the symbol's ISIN
(from NSE's index CSV) is looked up and accepted only when BSE returns the
same ISIN. Anything else is written as status=unresolved - never guessed.
"""

import argparse
import io
import os
import time

import pandas as pd
import requests

from backend.news import config
from backend.news.client import BSEBlocked, call_with_retry, logger, open_bse, setup_logging

COLUMNS = ["symbol", "company_name", "scrip_code", "status"]


def load_symbols(path=config.STOCK_LIST_FILE):
    """Return a DataFrame of (symbol, company_name) from the stock list."""
    df = pd.read_csv(path)
    if "is_active" in df.columns:
        df = df[df["is_active"].astype(str).str.lower() == "true"]
    symbols = df[config.SYMBOL_COLUMN].astype(str).str.strip().str.replace(r"\.NS$", "", regex=True)
    names = df[config.NAME_COLUMN] if config.NAME_COLUMN in df.columns else ""
    return pd.DataFrame({"symbol": symbols, "company_name": names}).drop_duplicates("symbol")


def load_isins(url=config.NSE_INDEX_CSV_URL):
    """symbol -> ISIN from NSE's index CSV; empty dict if unavailable."""
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=config.HTTP_TIMEOUT_S)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        return dict(zip(df["Symbol"].str.strip(), df["ISIN Code"].str.strip()))
    except Exception as exc:
        logger.warning("Could not load NSE ISIN list (%s); ISIN fallback disabled.", exc)
        return {}


def resolve(bse, symbol, isin=None, sleep=time.sleep):
    """Return (scrip_code, status) for one symbol."""
    try:
        code = call_with_retry(bse.getScripCode, symbol, what=f"getScripCode({symbol})")
        return str(code), "resolved"
    except ValueError:
        pass
    except BSEBlocked:
        raise
    except Exception as exc:
        logger.warning("getScripCode(%s) failed: %s", symbol, exc)

    if isin:
        sleep(config.SCRIP_LOOKUP_DELAY_S)
        try:
            hit = call_with_retry(bse.lookup, isin, what=f"lookup({isin})")
        except BSEBlocked:
            raise
        except Exception as exc:
            logger.warning("lookup(%s) failed: %s", isin, exc)
            hit = None
        if hit and hit.get("isin") == isin and hit.get("bse_code"):
            return str(hit["bse_code"]), "resolved_isin"

    return "", "unresolved"


def build_scrip_map(only_unresolved=False, out_file=config.SCRIP_MAP_FILE, sleep=time.sleep):
    stocks = load_symbols()
    existing = pd.read_csv(out_file, dtype=str).fillna("") if os.path.exists(out_file) else pd.DataFrame(columns=COLUMNS)
    done = {}
    if only_unresolved:
        done = {
            r.symbol: r._asdict()
            for r in existing.itertuples(index=False)
            if r.status.startswith("resolved")
        }

    isins = load_isins()
    rows = []
    blocked = False
    with open_bse() as bse:
        for i, (symbol, name) in enumerate(zip(stocks["symbol"], stocks["company_name"])):
            if symbol in done:
                rows.append(done[symbol])
                continue
            code, status = "", "unresolved"
            if not blocked:
                if i:
                    sleep(config.SCRIP_LOOKUP_DELAY_S)
                try:
                    code, status = resolve(bse, symbol, isins.get(symbol), sleep=sleep)
                except BSEBlocked:
                    logger.error("Stopping scrip mapping: BSE is blocking requests. "
                                 "Remaining symbols marked unresolved; rerun with --only-unresolved later.")
                    blocked = True
                logger.info("%-12s -> %-7s %s", symbol, code or "-", status)
            rows.append({"symbol": symbol, "company_name": name, "scrip_code": code, "status": status})

    out = pd.DataFrame(rows, columns=COLUMNS)
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    out.to_csv(out_file, index=False)

    unresolved = out[out["status"] == "unresolved"]
    print(f"\nWrote {len(out)} rows to {out_file}")
    print(f"Resolved: {len(out) - len(unresolved)}  Unresolved: {len(unresolved)}")
    if not unresolved.empty:
        print("Fix these by hand (set scrip_code and status=resolved_manual):")
        for r in unresolved.itertuples(index=False):
            print(f"  {r.symbol:<14} {r.company_name}")
    return out


def load_scrip_map(path=config.SCRIP_MAP_FILE):
    """Resolved rows only, as a DataFrame with string scrip codes."""
    if not os.path.exists(path):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(path, dtype=str).fillna("")
    return df[df["status"].str.startswith("resolved") & (df["scrip_code"] != "")]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only-unresolved", action="store_true",
                        help="Keep resolved rows from the existing file; retry only the rest.")
    args = parser.parse_args()
    setup_logging()
    build_scrip_map(only_unresolved=args.only_unresolved)


if __name__ == "__main__":
    main()
