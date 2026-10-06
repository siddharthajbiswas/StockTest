"""Family-level reporting: the table every family returns, plus diagnostics.

    from research.lab import report
    print(report.family(recs, label=my_label_fn, regime="CA"))

`diagnostics(recs)` answers "was this family's best config luck?":
  * walk-forward: at each date T choose the config with the best trailing
    window excess, score it on the next window (all info available at T);
  * PBO (CSCV): probability the in-sample best is below median out of sample;
  * deflated Sharpe of the best config's monthly after-tax excess, given the
    number of configs tried.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import metrics, sweep

COLS = ["label", "regime", "first_start", "full_excess", "full_cagr", "bench_full_cagr",
        "ex5_mean", "ex5_beat", "ex10_mean", "ex10_median", "ex10_beat", "ex10_min",
        "ex15_mean", "ex15_beat", "ex20_mean", "ex20_beat", "boot_mean", "boot_lo", "boot_p",
        "max_dd", "bench_max_dd", "sharpe", "trades", "turnover", "avg_cash"]


def score(row) -> float:
    """The lab's single ranking number (pre-registered): the average of the
    mean excess over 5-, 10- and 15-year windows. It rewards being ahead across
    many start dates rather than one lucky full-period run."""
    xs = [row.get(f"ex{L}_mean") for L in (5, 10, 15)]
    xs = [x for x in xs if x is not None and not pd.isna(x)]
    return float(np.mean(xs)) if xs else float("nan")


def table(recs, label=None, regime=None) -> pd.DataFrame:
    t = sweep.table([r for r in recs if regime is None or r.get("regime") == regime], label=label)
    if t.empty:
        return t
    t["score"] = t.apply(score, axis=1)
    cols = ["score"] + [c for c in COLS if c in t.columns]
    return t[cols + [c for c in t.columns if c not in cols]].sort_values("score", ascending=False)


def diagnostics(recs, regime="CA", is_years=10, oos_years=5) -> dict:
    rs = [r for r in recs if r.get("regime") == regime and "error" not in r and r.get("starts")]
    out = {"n_configs": len(rs)}
    if len(rs) < 2:
        return out
    wf = metrics.walk_forward(rs, is_years=is_years, oos_years=oos_years)
    out["walk_forward"] = {k: v for k, v in wf.items() if k != "rows"}
    wf5 = metrics.walk_forward(rs, is_years=5, oos_years=3)
    out["walk_forward_5_3"] = {k: v for k, v in wf5.items() if k != "rows"}
    M = metrics.monthly_matrix(rs)
    out["pbo_configs_dropped_late_start"] = int(M.attrs.get("dropped_configs", 0))
    if M.shape[1] >= 2:
        out["pbo"] = metrics.cscv_pbo(M)
        means = M.mean() * 12
        best = means.idxmax()
        srs = M.mean() / M.std(ddof=1)
        out["dsr_best"] = metrics.deflated_sharpe(M[best], n_trials=M.shape[1],
                                                  sr_std_across_trials=float(srs.std(ddof=1)))
        out["best_by_monthly_mean"] = best
    return out


def family(recs, label=None, regime="CA", top=25) -> str:
    t = table(recs, label=label, regime=regime)
    d = diagnostics(recs, regime=regime)
    with pd.option_context("display.width", 250, "display.max_columns", 40,
                           "display.max_colwidth", 70):
        s = t.head(top).round(4).to_string(index=False)
    return s + "\n\n" + json.dumps(d, indent=1, default=float)
