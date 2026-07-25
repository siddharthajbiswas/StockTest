"""Fetch a *current snapshot* of fundamentals for the tickers in ./data.

Writes data/fundamentals.csv with one row per ticker:

    ticker, trailingPE, priceToBook, returnOnEquity, dividendYield,
    marketCap, revenueGrowth, earningsSurprisePct, snapshot_date

⚠️  IMPORTANT — POINT-IN-TIME BIAS
    yfinance's `.info` returns only *today's* fundamentals. There is no cheap
    way to get what a stock's P/E or ROE actually was in, say, 2014. So these
    values are a single snapshot taken on `snapshot_date`. Using them to drive
    a buy decision in the distant past is look-ahead bias (you "knew" a number
    that didn't exist yet) layered on survivorship bias (only today's survivors
    even have a row). Treat fundamental-picker backtests as valid only over a
    recent window near the snapshot date, and read the results with suspicion.
    For honest deep-history factor testing you need point-in-time fundamentals
    from a paid vendor (Sharadar/Nasdaq Data Link, Polygon, Compustat, ...).

Usage:
    python fetch_fundamentals.py                 # every ticker in ./data
    python fetch_fundamentals.py --limit 50      # first 50 (quick smoke test)
    python fetch_fundamentals.py --tickers AAPL MSFT NVDA
"""

from __future__ import annotations

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

from backtester.data import available_tickers

DATA_DIR = Path(__file__).parent / "data"
OUT_PATH = DATA_DIR / "fundamentals.csv"

FIELDS = [
    "trailingPE",
    "priceToBook",
    "returnOnEquity",
    "dividendYield",
    "marketCap",
    "revenueGrowth",
]


def _earnings_surprise_pct(tk: yf.Ticker) -> float | None:
    """Most recent reported earnings surprise in percent, or None if unknown."""
    try:
        df = tk.get_earnings_dates(limit=8)
    except Exception:
        return None
    if df is None or df.empty:
        return None
    col = next((c for c in df.columns if "Surprise" in str(c)), None)
    if col is None:
        return None
    reported = df[df[col].notna()]
    if reported.empty:
        return None
    # Rows are newest-first; take the most recent reported quarter.
    return float(reported.iloc[0][col])


def fetch_one(ticker: str) -> dict:
    tk = yf.Ticker(ticker)
    row: dict[str, object] = {"ticker": ticker}
    try:
        info = tk.info or {}
    except Exception as exc:
        print(f"  {ticker}: info failed ({exc})")
        info = {}
    for f in FIELDS:
        val = info.get(f)
        row[f] = float(val) if isinstance(val, (int, float)) else None
    row["earningsSurprisePct"] = _earnings_surprise_pct(tk)
    row["snapshot_date"] = date.today().isoformat()
    return row


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--tickers", nargs="+", help="Specific tickers (default: all in data/).")
    ap.add_argument("--limit", type=int, help="Only fetch the first N tickers.")
    ap.add_argument("--workers", type=int, default=16,
                    help="Concurrent download threads (yfinance is I/O-bound).")
    args = ap.parse_args()

    tickers = args.tickers or available_tickers(DATA_DIR)
    if args.limit:
        tickers = tickers[: args.limit]

    print(f"Fetching fundamentals for {len(tickers)} tickers "
          f"on {args.workers} threads -> {OUT_PATH}")
    rows = []
    done = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(fetch_one, t): t for t in tickers}
        for fut in as_completed(futures):
            rows.append(fut.result())
            with lock:
                done += 1
                if done % 25 == 0 or done == len(tickers):
                    print(f"  {done}/{len(tickers)}", flush=True)

    df = pd.DataFrame(rows).set_index("ticker").sort_index()
    df.to_csv(OUT_PATH)
    filled = df[FIELDS].notna().sum()
    print("\nNon-null counts by field:")
    print(filled.to_string())
    print(f"\nWrote {len(df)} rows to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
