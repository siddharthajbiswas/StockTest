"""Load the per-ticker CSVs written by download_data.py into DataFrames."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIELDS = ["Open", "High", "Low", "Close", "Volume"]

# CSVs in data/ that are not per-ticker price series and must be kept out of the
# tradable universe (e.g. the fundamentals snapshot written by fetch_fundamentals).
NON_PRICE_FILES = {"fundamentals", "sp500_constituents"}


def available_tickers(data_dir: Path | str = DATA_DIR) -> list[str]:
    """Every ticker that has a price CSV on disk, sorted."""
    return sorted(
        p.stem for p in Path(data_dir).glob("*.csv") if p.stem not in NON_PRICE_FILES
    )


def load_prices(
    tickers: list[str] | None = None,
    data_dir: Path | str = DATA_DIR,
    start: str | None = None,
    end: str | None = None,
) -> dict[str, pd.DataFrame]:
    """Return {ticker: DataFrame} indexed by date with OHLCV columns.

    `tickers=None` loads everything in the folder. `start`/`end` (YYYY-MM-DD)
    clip each frame inclusively. Missing/empty files are skipped with a warning.
    """
    data_dir = Path(data_dir)
    if tickers is None:
        tickers = available_tickers(data_dir)

    out: dict[str, pd.DataFrame] = {}
    for t in tickers:
        path = data_dir / f"{t}.csv"
        if not path.exists():
            print(f"warning: {path} not found, skipping {t}")
            continue
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        df = df[[c for c in FIELDS if c in df.columns]].sort_index()
        if start:
            df = df[df.index >= pd.Timestamp(start)]
        if end:
            df = df[df.index <= pd.Timestamp(end)]
        if df.empty:
            print(f"warning: no rows for {t} in range, skipping")
            continue
        out[t] = df
    if not out:
        raise ValueError("No price data loaded — check tickers/date range/data dir.")
    return out


def trading_calendar(prices: dict[str, pd.DataFrame]) -> pd.DatetimeIndex:
    """Union of all dates across the loaded tickers, sorted ascending."""
    idx = pd.DatetimeIndex([])
    for df in prices.values():
        idx = idx.union(df.index)
    return idx.sort_values()
