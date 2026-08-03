"""Freeze out-of-sample validation output as a reference oracle (Phase 4).

`oos_validation.run_validation` is the heaviest thing in the project — it runs
every picker x timer combo once over the span (30 with --price-only, 100
without), then slices those curves into a holdout and a walk-forward track
record. This pins its full output so the TypeScript port can be checked against
it the same way the backtests are.

Also emits Spearman fixtures: pandas delegates `corr(method="spearman")` to
scipy, which uses AVERAGE ranks for ties. A port that uses ordinal ranks agrees
on distinct values and diverges silently the moment two combos tie.

Usage:
    .venv/bin/python tools/gen_validation_golden.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))

OUT = ROOT / "golden" / "validation"

# Pinned so the oracle never rides on a default.
COSTS = dict(commission_pct=0.0005, slippage_pct=0.0005)
TAX = dict(enabled=True, short_term_rate=0.35, long_term_rate=0.15, long_term_days=365)

CASES = [
    {
        "id": "validate_price_only",
        "why": "The default validation path: 3 price-only pickers x 10 timers = "
               "30 combos over a 6-year span, PIT universe. Exercises holdout "
               "ranking, Spearman persistence, and a multi-window walk-forward.",
        "price_only": True,
        "train_years": 3,
        "step_years": 1,
        "split": None,          # exercises the midpoint-split branch
        "config": dict(
            mode="picker", picker_id="momentum", picker_params={},
            timer_id="ma_cross", timer_params={"fast": 50, "slow": 200},
            top_n=15, rebalance="M", universe="sp500-pit",
            start="2016-01-01", end="2021-12-31", tax=TAX, **COSTS,
        ),
    },
    {
        "id": "validate_all_pickers",
        "why": "The full 100-combo sweep (price_only=False), including the "
               "fundamental pickers, over a shorter window. This is the "
               "worst-case compute path the progress reporting exists for.",
        "price_only": False,
        "train_years": 1,
        "step_years": 1,
        "split": "2020-07-01",  # exercises the explicit-split branch
        "config": dict(
            mode="picker", picker_id="relative_strength", picker_params={},
            timer_id="buy_hold", timer_params={},
            top_n=15, rebalance="M", universe="all",
            start="2019-01-01", end="2021-12-31", tax=TAX, **COSTS,
        ),
    },
]


def sanitize(o):
    if isinstance(o, dict):
        return {k: sanitize(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [sanitize(v) for v in o]
    if isinstance(o, bool) or o is None or isinstance(o, (int, str)):
        return o
    if isinstance(o, float):
        return o if np.isfinite(o) else None
    if hasattr(o, "item"):
        return sanitize(o.item())
    return str(o)


def dumps(p) -> str:
    return json.dumps(p, indent=2, sort_keys=True, allow_nan=False) + "\n"


def spearman_fixtures() -> dict:
    """Cases with and without ties, to pin the average-rank behaviour."""
    rng = np.random.default_rng(4)
    out = []
    specs = [
        ("distinct", list(rng.uniform(-0.2, 0.4, 30)), list(rng.uniform(-0.2, 0.4, 30))),
        ("ties_in_a", [1.0, 2.0, 2.0, 3.0, 4.0, 4.0, 4.0, 5.0],
                      [0.1, 0.5, 0.2, 0.9, 0.3, 0.7, 0.4, 0.8]),
        ("ties_in_both", [1.0, 1.0, 2.0, 2.0, 3.0, 3.0],
                         [5.0, 5.0, 1.0, 2.0, 2.0, 9.0]),
        ("perfect", [1.0, 2.0, 3.0, 4.0, 5.0], [10.0, 20.0, 30.0, 40.0, 50.0]),
        ("inverse", [1.0, 2.0, 3.0, 4.0, 5.0], [50.0, 40.0, 30.0, 20.0, 10.0]),
        ("all_equal_b", [1.0, 2.0, 3.0], [7.0, 7.0, 7.0]),
    ]
    for name, a, b in specs:
        r = pd.Series(a).corr(pd.Series(b), method="spearman")
        out.append({"name": name, "a": [float(x) for x in a],
                    "b": [float(x) for x in b],
                    "spearman": None if not np.isfinite(r) else float(r)})
    return {"cases": out}


def main() -> int:
    from models import StrategyConfig
    from oos_validation import run_validation
    from service import EngineService

    # Force the serial path: deterministic and avoids spawning a process pool
    # from a build script. The parallel path preserves result order anyway
    # (ex.map is ordered), so this changes timing only, not output.
    os.environ["STOCKTEST_VALIDATE_JOBS"] = "1"

    t0 = time.time()
    svc = EngineService()
    print(f"engine loaded in {time.time() - t0:.1f}s")

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "spearman.json").write_text(dumps(spearman_fixtures()))
    print("wrote spearman.json")

    for case in CASES:
        t = time.time()
        cfg = StrategyConfig(**case["config"])
        result = run_validation(
            cfg, svc,
            split=case["split"],
            train_years=case["train_years"],
            step_years=case["step_years"],
            price_only=case["price_only"],
        )
        payload = sanitize({
            "id": case["id"],
            "why": case["why"],
            "params": {
                "split": case["split"],
                "train_years": case["train_years"],
                "step_years": case["step_years"],
                "price_only": case["price_only"],
            },
            "config": case["config"],
            "result": result,
        })
        (OUT / f"{case['id']}.json").write_text(dumps(payload))
        m = result["meta"]
        v = result["verdict"]
        print(f"  {case['id']:<24} {m['n_baseline_combos']:>4} combos  "
              f"{len(result['walkforward']['windows'])} windows  "
              f"verdict={v['level']:<6} ({time.time() - t:.0f}s)")

    print(f"\nwrote {len(CASES)} validation goldens -> {OUT.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
