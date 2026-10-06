"""Rebuild research/lab/data/VFINXR.csv: VFINX with its 1980-86 unadjusted
capital-gain distribution days replaced by the S&P 500's return that day.

    .venv/bin/python research/lab/fetch_extra.py        # VFINX, ^GSPC first
    .venv/bin/python -m research.lab.tools.build_vfinxr
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from research.lab import data  # noqa: E402

BAD_DAYS = ["1980-12-30", "1981-12-29", "1983-12-28", "1984-12-28", "1985-12-27", "1986-12-09"]


def main() -> None:
    v = data.frame("VFINX", end=None)["Close"]
    g = data.frame("^GSPC", end=None)["Close"]
    rv = v.pct_change()
    rg = g.pct_change().reindex(rv.index)
    for d in BAD_DAYS:
        rv[pd.Timestamp(d)] = rg[pd.Timestamp(d)]
    lvl = (1 + rv.fillna(0)).cumprod()
    lvl = lvl * (v.iloc[-1] / lvl.iloc[-1])
    out = pd.DataFrame({"Open": lvl, "High": lvl, "Low": lvl, "Close": lvl})
    out.index.name = "Date"
    out.to_csv(data.EXTRA_DIR / "VFINXR.csv")


if __name__ == "__main__":
    main()
