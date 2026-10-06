"""Download per-share distributions for every fund the lab can trade.

The engine's prices are total-return adjusted, so dividends and bond interest
silently compound inside the price and are taxed only as deferred capital gains
when sold. Reality taxes them every year (qualified dividends at long-term
rates, bond interest and non-qualified distributions at ordinary rates). To
measure that gap for finalists, research/lab/realism.py needs each fund's daily
distribution *yield*: distribution / previous unadjusted close.

Writes research/lab/divs/<TICKER>.csv with Date, Dividend, Close (unadjusted).
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / "divs"


def tickers() -> list[str]:
    from research.lab.fetch_extra import GROUPS
    site = ["SPY", "QQQ", "DIA", "IWM", "VTI", "VOO", "VEA", "VWO", "AGG", "TLT", "GLD", "SLV",
            "USO", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB", "XLRE", "XLC",
            "ARKK", "MDY", "IJR", "RSP", "IWD", "IWF", "EFA", "EEM"]
    out = list(site)
    for g, ts in GROUPS.items():
        if g == "index":
            continue
        out += ts
    return list(dict.fromkeys(out))


def main() -> None:
    import sys
    sys.path.insert(0, str(ROOT))
    OUT.mkdir(exist_ok=True)
    for t in tickers():
        p = OUT / f"{t}.csv"
        if p.exists():
            continue
        for attempt in range(3):
            try:
                df = yf.download(t, period="max", auto_adjust=False, actions=True,
                                 progress=False, threads=False)
                break
            except Exception as e:  # noqa: BLE001
                df = None
                time.sleep(2 + 3 * attempt)
        if df is None or df.empty:
            print(t, "empty", flush=True)
            continue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        cols = [c for c in ("Dividends", "Close", "Capital Gains") if c in df.columns]
        d = df[cols].rename(columns={"Dividends": "Dividend", "Capital Gains": "CapGain"})
        d.index.name = "Date"
        d.to_csv(p)
        nz = int((d["Dividend"] > 0).sum()) if "Dividend" in d else 0
        print(t, len(d), "rows", nz, "distributions", flush=True)
        time.sleep(0.3)


if __name__ == "__main__":
    main()
