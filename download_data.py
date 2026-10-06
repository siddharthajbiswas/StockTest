"""Download historical daily stock data into ./data as one CSV per ticker.

Uses yfinance (Yahoo Finance). Each CSV has columns:
    Date, Open, High, Low, Close, Volume
with prices split/dividend adjusted (auto_adjust=True).

Usage:
    python download_data.py                 # full S&P 500 universe, max history
    python download_data.py --period 5y     # limit history
    python download_data.py --tickers AAPL MSFT NVDA
    python download_data.py --force         # re-download even if CSV exists
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).parent / "data"
WIKI_SP500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"

# Broad-market ETFs + a few large names worth having regardless of index membership.
EXTRA_TICKERS = [
    "SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "VEA", "VWO", "AGG", "TLT",
    "GLD", "SLV", "USO", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI",
    "XLU", "XLB", "XLRE", "XLC", "ARKK",
    # Size / style / region index funds. These complete the survivorship-free
    # menu that strategies/tax_managed.py ranks over — see its docstring for why
    # that menu is ETFs rather than single stocks.
    "MDY", "IJR", "RSP", "IWD", "IWF", "EFA", "EEM",
    # The 2x trend-switch preset (timer "trend_switch"): a 2x S&P 500 ETF and
    # intermediate Treasuries. Manual/menu mode only — both are listed in
    # backtester.data.UNIVERSE_EXCLUDE, so stock pickers never see them.
    "SSO", "IEF",
]

# Fallback if Wikipedia is unreachable — a solid mega/large-cap set.
FALLBACK = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "GOOG", "META", "TSLA", "BRK-B",
    "JPM", "V", "MA", "UNH", "HD", "PG", "JNJ", "XOM", "CVX", "ABBV", "LLY",
    "AVGO", "COST", "PEP", "KO", "WMT", "MRK", "BAC", "CRM", "ADBE", "NFLX",
    "AMD", "INTC", "CSCO", "ORCL", "QCOM", "TXN", "IBM", "PYPL", "DIS", "NKE",
]


def sp500_tickers() -> list[str]:
    """Fetch current S&P 500 symbols from Wikipedia, normalized for Yahoo."""
    import io
    import urllib.request

    req = urllib.request.Request(WIKI_SP500, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8")
    table = pd.read_html(io.StringIO(html))[0]
    # Yahoo uses '-' where the index uses '.' (e.g. BRK.B -> BRK-B).
    return [s.replace(".", "-") for s in table["Symbol"].astype(str).tolist()]


def build_universe() -> list[str]:
    try:
        tickers = sp500_tickers()
        print(f"Fetched {len(tickers)} S&P 500 tickers from Wikipedia.")
    except Exception as e:  # noqa: BLE001
        print(f"Wikipedia fetch failed ({e}); using fallback list.")
        tickers = list(FALLBACK)
    # Merge with extras, dedupe, keep order.
    seen: dict[str, None] = {}
    for t in tickers + EXTRA_TICKERS:
        seen.setdefault(t, None)
    return list(seen)


def download_one(ticker: str, period: str, force: bool) -> str:
    out = DATA_DIR / f"{ticker}.csv"
    if out.exists() and not force:
        return "skip"
    df = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
        threads=False,
    )
    if df is None or df.empty:
        return "empty"
    # yfinance returns a MultiIndex column frame for single tickers; flatten it.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.index.name = "Date"
    df.to_csv(out)
    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tickers", nargs="+", help="Explicit tickers instead of S&P 500.")
    ap.add_argument("--period", default="max", help="yfinance period (max, 10y, 5y, 1y...).")
    ap.add_argument("--force", action="store_true", help="Re-download existing CSVs.")
    ap.add_argument("--sleep", type=float, default=0.5, help="Seconds between requests.")
    args = ap.parse_args()

    DATA_DIR.mkdir(exist_ok=True)
    tickers = args.tickers if args.tickers else build_universe()
    print(f"Downloading {len(tickers)} tickers -> {DATA_DIR} (period={args.period})\n")

    counts = {"ok": 0, "skip": 0, "empty": 0, "error": 0}
    failed: list[str] = []
    for i, t in enumerate(tickers, 1):
        try:
            status = download_one(t, args.period, args.force)
        except Exception as e:  # noqa: BLE001
            status, msg = "error", str(e)
            failed.append(t)
        else:
            msg = ""
        counts[status] += 1
        print(f"[{i:>3}/{len(tickers)}] {t:<7} {status}{(' - ' + msg) if msg else ''}")
        if status == "ok":
            time.sleep(args.sleep)

    print("\nDone:", ", ".join(f"{k}={v}" for k, v in counts.items()))
    if failed:
        print("Failed:", " ".join(failed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
