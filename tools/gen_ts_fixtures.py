"""Generate unit-level fixtures for the JavaScript port (Phase 2).

The end-to-end golden cases prove the whole stack agrees, but when they fail
they don't say *where*. These fixtures pin each ported primitive individually —
the numeric reductions, the indicators, the tax netting — so a regression points
at a module instead of a 1,500-day equity curve.

Values are emitted as exact float64 hex ("%a" / Number.prototype.toString style)
alongside the decimal form, so a fixture can be compared bit-for-bit without
worrying about decimal round-tripping.

Usage:
    .venv/bin/python tools/gen_ts_fixtures.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtester.indicators import (  # noqa: E402
    bollinger, macd, realized_vol, sma, total_return, wilder_rsi,
)
from backtester.tax import TaxPolicy, compute_year_tax  # noqa: E402

OUT = ROOT / "web" / "engine" / "test" / "fixtures.json"


def f(x):
    """Exact float, plus its hex form for bit-level comparison."""
    if x is None:
        return None
    x = float(x)
    if not math.isfinite(x):
        return None
    return x


def main() -> int:
    rng = np.random.default_rng(20260731)
    fixtures: dict = {}

    # ---- numeric reductions -------------------------------------------
    red = []
    for n in [1, 2, 7, 8, 9, 20, 50, 100, 127, 128, 129, 136, 200, 252, 255, 256, 257, 600, 1500]:
        x = rng.uniform(1.0, 1000.0, n)
        s = pd.Series(x)
        red.append({
            "n": n,
            "x": [f(v) for v in x],
            "sum": f(np.sum(x)),
            "mean": f(s.mean()),
            "std0": f(s.std(ddof=0)) if n >= 1 else None,
            "std1": f(s.std(ddof=1)) if n >= 2 else None,
            "pct_change": [f(v) for v in s.pct_change().dropna().to_numpy()],
            "ewm_0_1": [f(v) for v in s.ewm(alpha=0.1, adjust=False).mean().to_numpy()],
            "cummax": [f(v) for v in s.cummax().to_numpy()],
        })
    fixtures["reductions"] = red

    # ---- indicators ----------------------------------------------------
    ind = []
    for n in [5, 15, 21, 30, 60, 210, 260, 400]:
        # A random walk looks more like prices than uniform noise, and exercises
        # the RSI/MACD branches with realistic gain/loss mixes.
        steps = rng.normal(0.0, 1.0, n)
        closes = np.abs(np.cumsum(steps) + 100.0) + 1.0
        s = pd.Series(closes)
        m = macd(s)
        b = bollinger(s)
        ind.append({
            "n": n,
            "closes": [f(v) for v in closes],
            "sma_20": f(sma(s, 20)),
            "sma_50": f(sma(s, 50)),
            "sma_200": f(sma(s, 200)),
            "rsi_14": f(wilder_rsi(s, 14)),
            "macd": None if m is None else [f(m[0]), f(m[1])],
            "bollinger": None if b is None else [f(b[0]), f(b[1]), f(b[2])],
            "total_return_20": f(total_return(s, 20)),
            "total_return_252": f(total_return(s, 252)),
            "realized_vol_20": f(realized_vol(s, 20)),
        })
    fixtures["indicators"] = ind

    # ---- tax netting ---------------------------------------------------
    # Hand-picked to cover every branch of compute_year_tax: pure gains, pure
    # losses, mixed, carryforward that fully absorbs, partially absorbs, and
    # spills to the next year.
    policy = TaxPolicy(0.35, 0.15, 365)
    cases = [
        (0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (0.0, 1000.0, 0.0),
        (1000.0, 2000.0, 0.0), (-500.0, 0.0, 0.0), (0.0, -500.0, 0.0),
        (-500.0, 1000.0, 0.0), (1000.0, -500.0, 0.0), (-500.0, -700.0, 0.0),
        (1000.0, 1000.0, 500.0), (1000.0, 1000.0, 5000.0),
        (100.0, 50.0, 120.0), (-100.0, 2000.0, 300.0),
        (12345.67, -2345.67, 1000.0), (1e-9, 1e-9, 1e-9),
    ]
    tax = []
    for st, lt, cf in cases:
        t, new_cf = compute_year_tax(st, lt, cf, policy)
        tax.append({"net_st": f(st), "net_lt": f(lt), "carryforward_in": f(cf),
                    "tax": f(t), "carryforward_out": f(new_cf)})
    fixtures["tax"] = {
        "policy": {"short_term_rate": 0.35, "long_term_rate": 0.15, "long_term_days": 365},
        "cases": tax,
    }

    # ---- sharpe / drawdown / cagr on a realistic curve ------------------
    curve = np.abs(np.cumsum(rng.normal(200.0, 3000.0, 1500)) + 100000.0) + 1000.0
    s = pd.Series(curve)
    r = s.pct_change().dropna()
    peak = s.cummax()
    fixtures["result_metrics"] = {
        "curve": [f(v) for v in curve],
        "sharpe": f(np.sqrt(252) * r.mean() / r.std()),
        "max_drawdown": f((s / peak - 1.0).min()),
        "start_day": 0,
        "end_day": 2190,  # 6 years of calendar days
        "starting_cash": 100000.0,
        "cagr": f((curve[-1] / 100000.0) ** (1 / (2190 / 365.25)) - 1.0),
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fixtures, indent=1, allow_nan=False) + "\n")
    n = sum(len(v) if isinstance(v, list) else 1 for v in fixtures.values())
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size/1e3:.0f} kB, {n} groups)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
