"""The standard verification battery for a finalist.

    from research.lab import verify
    out = verify.battery(cfg, label="my strategy")
    print(verify.render(out))

Runs, for one exact config:
  1. protocol "full" in CA / FED / NONE (the headline numbers);
  2. rebalance-timing luck: the same strategy with every rebalance boundary
     shifted by 0..(period-1) weeks (kinds weights_x / combo_x) -- mean, min
     and max of score and full-period excess across offsets;
  3. one-day execution lag (weights kinds only): targets from today's close
     traded at tomorrow's close;
  4. trading costs 0, 15 and 35 bps per side (commission and slippage each);
  5. stricter tax accounting (research.lab.realism) from several start dates:
     annual tax on dividends/interest, collectibles rate on gold;
  6. sub-periods: excess over 2000-2010, 2010-2020, 2020-2026 windows;
  7. a deflated Sharpe ratio for the after-tax monthly excess given how many
     configurations the whole search tried (pass n_trials).
"""
from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd

from . import core, metrics, realism, report, sweep

PERIOD_WEEKS = {"D": 1, "W": 1, "M": 4, "Q": 13, "S": 26, "A": 52, "M2": 8, "M3": 13, "M4": 17, "M6": 26}


def _x_cfg(cfg: dict, offset_days: int = 0, lag: int = 0) -> dict | None:
    c = copy.deepcopy(cfg)
    if c["kind"] in ("weights", "weights_x"):
        c["kind"] = "weights_x"
        c["offset_days"] = offset_days
        c["lag"] = lag
        return c
    if c["kind"] in ("combo", "combo_x"):
        if lag:
            return None
        c["kind"] = "combo_x"
        c["offset_days"] = offset_days
        return c
    return None


def _row(rec) -> dict:
    s = metrics.summary(rec, n_boot=500)
    s["score"] = report.score(s)
    return s


def battery(cfg: dict, label: str = "", regimes=("CA", "FED", "NONE"), workers: int = 6,
            n_trials: int | None = None, realism_starts=("2000-01-01", "2005-01-01",
                                                         "2010-01-01", "2015-01-01"),
            offsets: bool = True, costs: bool = True) -> dict:
    out: dict = {"label": label, "cfg": cfg}
    # 1. headline
    recs = sweep.run([cfg], protocol="full", regimes=regimes, workers=workers, verbose=False)
    out["full"] = {r["regime"]: _row(r) for r in recs if "error" not in r}
    errs = [r["error"] for r in recs if "error" in r]
    if errs:
        out["errors"] = errs
        return out
    # 2. timing luck
    reb = cfg.get("rebalance", "M")
    if offsets and _x_cfg(cfg) is not None and reb not in ("D", "W"):
        weeks = PERIOD_WEEKS.get(reb, 4)
        step = max(1, weeks // 6)
        offs = [7 * w for w in range(0, weeks, step)]
        xs = [_x_cfg(cfg, o) for o in offs]
        xr = sweep.run(xs, protocol="full", regimes=("CA", "NONE"), workers=workers, verbose=False)
        tab = {}
        for r in xr:
            if "error" in r:
                continue
            s = _row(r)
            tab.setdefault(r["regime"], []).append((r["cfg"]["offset_days"], s["score"], s.get("full_excess")))
        out["offsets"] = {}
        for rg, rows in tab.items():
            sc = np.array([x[1] for x in rows])
            fe = np.array([x[2] for x in rows if x[2] is not None])
            out["offsets"][rg] = {"n": len(rows), "score_mean": float(sc.mean()), "score_min": float(sc.min()),
                                  "score_max": float(sc.max()), "full_mean": float(fe.mean()) if len(fe) else None,
                                  "full_min": float(fe.min()) if len(fe) else None,
                                  "full_max": float(fe.max()) if len(fe) else None,
                                  "share_score_pos": float((sc > 0).mean())}
    # 3. execution lag
    lc = _x_cfg(cfg, 0, 1)
    if lc is not None and cfg["kind"].startswith("weights"):
        lr = sweep.run([lc], protocol="full", regimes=("CA", "NONE"), workers=workers, verbose=False)
        out["lag1"] = {r["regime"]: {k: _row(r).get(k) for k in ("score", "full_excess", "ex10_beat", "boot_p")}
                       for r in lr if "error" not in r}
    # 4. costs
    if costs:
        out["costs"] = {}
        for c in (0.0, 0.0015, 0.0035):
            cr = sweep.run([cfg], protocol="full", regimes=("CA", "NONE"), workers=workers,
                           comm=c, slip=c, verbose=False)
            out["costs"][f"{c * 1e4:.0f}bps"] = {r["regime"]: {k: _row(r).get(k) for k in ("score", "full_excess")}
                                               for r in cr if "error" not in r}
    # 5. realism (taxable regimes)
    out["realism"] = {}
    for rg in [r for r in regimes if core.REGIMES[r] is not None]:
        rows = []
        for s0 in realism_starts:
            try:
                a = realism.adjusted(cfg, rg, s0)
                rows.append({"start": s0, "engine_excess": a["engine_excess"], "real_excess": a["real_excess"]})
            except Exception as e:  # noqa: BLE001
                rows.append({"start": s0, "error": str(e)})
        out["realism"][rg] = rows
    # 6. sub-periods (from the full-protocol windows)
    out["subperiods"] = {}
    for r in recs:
        w = metrics.windows(r)
        sub = {}
        for a, b in (("2000-01-01", "2010-01-01"), ("2010-01-01", "2020-01-01"), ("2020-01-01", "2026-07-01")):
            x = w[(w.start == a) & (w.end == b)]
            if len(x):
                sub[f"{a[:4]}-{b[:4]}"] = float(x.excess.iloc[0])
            else:
                s_, b_ = metrics.window(r, a, b), metrics.window(metrics.bench_for(r), a, b)
                if s_ is not None and b_ is not None:
                    sub[f"{a[:4]}-{b[:4]}"] = s_ - b_
        out["subperiods"][r["regime"]] = sub
    # 7. deflated Sharpe given the size of the search
    if n_trials:
        out["dsr"] = {}
        for r in recs:
            x = metrics.monthly_excess(r)
            out["dsr"][r["regime"]] = metrics.deflated_sharpe(x, n_trials=n_trials)
    return out


def render(out: dict) -> str:
    def f(x):
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return "  n/a"
        return f"{x * 100:+.2f}"
    lines = [f"### {out.get('label', '')}", "", "```json", json.dumps(out["cfg"]), "```", ""]
    if "errors" in out:
        return "\n".join(lines + ["ERRORS: " + "; ".join(out["errors"])])
    lines += ["| regime | score | full | 10y mean | 10y beat | 15y beat | 20y beat | boot p | maxDD (SPY) |",
              "|---|---|---|---|---|---|---|---|---|"]
    for rg, s in out["full"].items():
        lines.append(f"| {rg} | {f(s.get('score'))} | {f(s.get('full_excess'))} | {f(s.get('ex10_mean'))} | "
                     f"{s.get('ex10_beat', 0):.0%} | {s.get('ex15_beat', 0):.0%} | {s.get('ex20_beat', 0):.0%} | "
                     f"{s.get('boot_p', float('nan')):.3f} | {s.get('max_dd', 0):.0%} ({s.get('bench_max_dd', 0):.0%}) |")
    if out.get("offsets"):
        lines += ["", "Rebalance-timing luck (all boundary offsets):", ""]
        for rg, o in out["offsets"].items():
            lines.append(f"- {rg}: score mean {f(o['score_mean'])} [min {f(o['score_min'])}, max {f(o['score_max'])}], "
                         f"full mean {f(o['full_mean'])} [min {f(o['full_min'])}, max {f(o['full_max'])}], "
                         f"{o['share_score_pos']:.0%} of {o['n']} offsets positive")
    if out.get("lag1"):
        lines += ["", "One-day execution lag: " + ", ".join(
            f"{rg} score {f(v['score'])} full {f(v['full_excess'])}" for rg, v in out["lag1"].items())]
    if out.get("costs"):
        lines += ["", "Costs per side: " + "; ".join(
            f"{k}: " + ", ".join(f"{rg} score {f(v['score'])}" for rg, v in d.items()) for k, d in out["costs"].items())]
    if out.get("realism"):
        lines += ["", "Stricter tax accounting (engine -> with annual distribution tax):"]
        for rg, rows in out["realism"].items():
            lines.append(f"- {rg}: " + "; ".join(
                f"from {r['start'][:4]}: {f(r.get('engine_excess'))} -> {f(r.get('real_excess'))}"
                if "error" not in r else f"from {r['start'][:4]}: error" for r in rows))
    if out.get("subperiods"):
        lines += ["", "Sub-periods: " + "; ".join(
            f"{rg}: " + ", ".join(f"{k} {f(v)}" for k, v in d.items()) for rg, d in out["subperiods"].items())]
    if out.get("dsr"):
        lines += ["", "Deflated Sharpe (prob. true after-tax excess Sharpe > 0, given the search size): " + ", ".join(
            f"{rg} {d.get('dsr', float('nan')):.3f}" for rg, d in out["dsr"].items())]
    return "\n".join(lines) + "\n"
