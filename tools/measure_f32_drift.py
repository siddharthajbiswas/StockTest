"""Measure what Float32 storage costs the Phase 0 golden parity.

Why this is not just a rounding footnote
----------------------------------------
JavaScript has no float32 arithmetic. Reading an element out of a
`Float32Array` yields a float64 Number whose value is exactly
`float32(original)`. So the TS port will do float64 math on float32-quantized
inputs — which is precisely what this script simulates by quantizing the price
frames and running the *existing* Python engine over them. The resulting
numbers are the numbers the port should be expected to produce.

Tradability is NOT quantized: `build_web_data.py` ships a precomputed
tradability bit derived from the exact float64 volumes, so the port never
re-derives it from a rounded value. Modeling it any other way would overstate
the drift.

Output: build/webdata/precision_report.json

Usage:
    .venv/bin/python tools/measure_f32_drift.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "tools"))

OUT = ROOT / "build" / "webdata"
GOLDEN = ROOT / "golden"

QUANTIZED_FIELDS = ["Open", "High", "Low", "Close"]


def quantize(df: pd.DataFrame) -> pd.DataFrame:
    """float64 -> float32 -> float64 on price columns; Volume left exact."""
    out = df.copy()
    for f in QUANTIZED_FIELDS:
        if f in out.columns:
            out[f] = out[f].to_numpy(dtype=np.float32).astype(np.float64)
    return out


def rel(a: float, b: float) -> float:
    if a == b:
        return 0.0
    denom = max(abs(a), abs(b))
    return abs(a - b) / denom if denom else abs(a - b)


def main() -> int:
    import service
    from gen_golden import CASES, build_payload

    # Build a service whose prices are float32-quantized, by patching the
    # loader the service module resolved at import time.
    original = service.load_prices

    def quantized_loader(tickers=None, *a, **kw):
        return {t: quantize(df) for t, df in original(tickers, *a, **kw).items()}

    service.load_prices = quantized_loader
    try:
        svc = service.EngineService()
    finally:
        service.load_prices = original

    rows = []
    for case in CASES:
        gpath = GOLDEN / f"{case['id']}.json"
        if not gpath.exists():
            continue
        golden = json.loads(gpath.read_text())["result"]
        actual = build_payload(svc, case)["result"]

        gm, am = golden["metrics"], actual["metrics"]
        gc, ac = golden["equity_curve"], actual["equity_curve"]

        curve_rel = 0.0
        if len(gc["aftertax"]) == len(ac["aftertax"]):
            for x, y in zip(gc["aftertax"], ac["aftertax"]):
                if x is not None and y is not None:
                    curve_rel = max(curve_rel, rel(x, y))

        metric_rel = {}
        for k, gv in gm.items():
            av = am.get(k)
            if isinstance(gv, (int, float)) and isinstance(av, (int, float)) \
                    and not isinstance(gv, bool):
                metric_rel[k] = rel(float(gv), float(av))

        rows.append({
            "id": case["id"],
            "trades_golden": len(golden["trades"]),
            "trades_f32": len(actual["trades"]),
            "trades_match": len(golden["trades"]) == len(actual["trades"]),
            "days_match": len(gc["dates"]) == len(ac["dates"]),
            "max_equity_rel": curve_rel,
            "max_metric_rel": max(metric_rel.values()) if metric_rel else 0.0,
            "worst_metric": max(metric_rel, key=metric_rel.get) if metric_rel else None,
            "final_value_golden": gm.get("final_value"),
            "final_value_f32": am.get("final_value"),
            "total_tax_golden": gm.get("total_tax"),
            "total_tax_f32": am.get("total_tax"),
        })

    print(f"{'case':<28} {'trades':>13} {'max equity rel':>15} {'max metric rel':>15}")
    print("-" * 76)
    for r in rows:
        tr = f"{r['trades_golden']}/{r['trades_f32']}"
        flag = "" if r["trades_match"] else "  <-- TRADE COUNT DIFFERS"
        print(f"{r['id']:<28} {tr:>13} {r['max_equity_rel']:>15.3e} "
              f"{r['max_metric_rel']:>15.3e}{flag}")

    worst_eq = max(r["max_equity_rel"] for r in rows)
    worst_mt = max(r["max_metric_rel"] for r in rows)
    all_trades_match = all(r["trades_match"] for r in rows)

    report = {
        "what": "Effect of float32 price storage on the Phase 0 golden cases.",
        "method": "Quantize OHLC float64->float32->float64, rerun the same engine. "
                  "Models JS exactly: reading a Float32Array yields "
                  "float64(float32(x)) and JS arithmetic is float64. Volume is "
                  "left exact because tradability ships as a precomputed bit.",
        "worst_equity_rel": worst_eq,
        "worst_metric_rel": worst_mt,
        "all_trade_counts_match": all_trades_match,
        "phase0_tolerance_python_vs_ts": 1e-9,
        "verdict": (
            "float32 drift EXCEEDS the 1e-9 Phase 0 tolerance"
            if max(worst_eq, worst_mt) > 1e-9 else
            "float32 drift is within the 1e-9 Phase 0 tolerance"
        ),
        "recommendation": (
            "Re-baseline the oracle on float32 inputs: the browser will only ever "
            "see float32 prices, so the goldens should be generated from the same "
            "quantized data. Then Python-vs-TS parity can stay tight (1e-9) "
            "instead of being loosened to absorb a storage artifact."
        ),
        "cases": rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "precision_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")

    print(f"\nworst equity rel error : {worst_eq:.3e}")
    print(f"worst metric rel error : {worst_mt:.3e}")
    print(f"trade counts all match : {all_trades_match}")
    print(f"\n{report['verdict']}")
    print(f"-> wrote {(OUT / 'precision_report.json').relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
