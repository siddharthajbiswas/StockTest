"""Fetch human-readable company names for the tickers in ./data.

Writes data/company_names.csv with one row per ticker:

    ticker, name

Why this is a separate file rather than a column in fundamentals.csv:
`tools/build_web_data.py` bundles EVERY non-ticker column of fundamentals.csv
into fundamentals.json as numeric factor data. A string name column would ride
along into the factor matrix — bloating the payload with data no picker reads,
and pushing a string into a table the engine treats as floats. Names are
presentation metadata, so they travel with the ticker index (tickers.json)
instead. See reference/tickers.py, which prefers this file when it exists.

Names come from yfinance's `.info`, the same source as the fundamentals
snapshot. Unlike those numbers a company name is not point-in-time sensitive —
a ticker that was renamed shows today's name, which is what a user searching for
it would recognize anyway.

Usage:
    python tools/fetch_company_names.py                 # every ticker in ./data
    python tools/fetch_company_names.py --limit 20      # quick smoke test
    python tools/fetch_company_names.py --tickers AAPL MSFT
"""

from __future__ import annotations

import argparse
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtester.data import available_tickers  # noqa: E402

DATA_DIR = ROOT / "data"
OUT_PATH = DATA_DIR / "company_names.csv"

# Preference order. longName is the full legal-ish name ("Apple Inc."),
# shortName a trimmed display form ("Apple"). Either beats nothing.
NAME_FIELDS = ("longName", "shortName", "displayName")


def fetch_one(ticker: str) -> tuple[str, str | None]:
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as exc:  # network, rate limit, delisted symbol
        print(f"  {ticker}: info failed ({exc})")
        return ticker, None
    for field in NAME_FIELDS:
        val = info.get(field)
        if isinstance(val, str) and val.strip():
            return ticker, val.strip()
    return ticker, None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--tickers", nargs="+", help="Specific tickers (default: all in data/).")
    ap.add_argument("--limit", type=int, help="Only fetch the first N tickers.")
    ap.add_argument("--workers", type=int, default=12,
                    help="Concurrent download threads (yfinance is I/O-bound).")
    args = ap.parse_args()

    tickers = args.tickers or available_tickers(DATA_DIR)
    if args.limit:
        tickers = tickers[: args.limit]

    # Merge onto whatever we already have, so a partial run (rate limits are
    # common with 500+ symbols) is additive rather than destructive.
    existing: dict[str, str] = {}
    if OUT_PATH.exists():
        prev = pd.read_csv(OUT_PATH).dropna(subset=["name"])
        existing = dict(zip(prev["ticker"].astype(str), prev["name"].astype(str)))
        print(f"{len(existing)} names already on disk; refetching all {len(tickers)}")

    print(f"Fetching names for {len(tickers)} tickers on {args.workers} threads -> {OUT_PATH}")
    found: dict[str, str] = {}
    done = 0
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(fetch_one, t) for t in tickers]
        for fut in as_completed(futures):
            ticker, name = fut.result()
            if name:
                found[ticker] = name
            with lock:
                done += 1
                if done % 50 == 0 or done == len(tickers):
                    print(f"  {done}/{len(tickers)} ({len(found)} named)", flush=True)

    merged = {**existing, **found}
    rows = [{"ticker": t, "name": merged[t]} for t in sorted(merged)]
    df = pd.DataFrame(rows, columns=["ticker", "name"])
    df.to_csv(OUT_PATH, index=False)

    missing = sorted(set(tickers) - set(merged))
    print(f"\nWrote {len(df)} names to {OUT_PATH}")
    if missing:
        print(f"{len(missing)} still unnamed: {', '.join(missing[:20])}"
              f"{' …' if len(missing) > 20 else ''}")
        print("Rerun to retry just those — results merge onto the existing file.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
