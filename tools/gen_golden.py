"""Freeze the Python engine as a reference oracle.

Phase 0 of the TypeScript port: run a fixed set of (picker, timer, window,
params) combos through the *same* entry point the web app uses
(`EngineService.run_backtest`) and dump the full result — equity curves, trade
blotter, tax numbers, round trips, and headline metrics — to JSON.

Those JSON files are the contract the TS port must reproduce. See
`golden/test_golden_parity.py`, which re-runs every case and diffs it against
the frozen output, so the oracle keeps checking itself as the Python evolves.

Usage:
    .venv/bin/python tools/gen_golden.py            # write golden/
    .venv/bin/python tools/gen_golden.py --check    # verify, write nothing

Every case pins cash, costs, tax rates, top_n and rebalance explicitly rather
than leaning on model defaults, so a future default change shows up as a parity
failure instead of silently rebasing the oracle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "golden"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))


# ---------------------------------------------------------------------------
# The cases. Each one is chosen to exercise a path where a port tends to drift.
# ---------------------------------------------------------------------------
BASKET = ["AAPL", "MSFT", "JNJ", "XOM", "KO"]

# Shared cost/tax settings — pinned so the oracle never rides on a default.
COSTS = {"cash": 100_000.0, "commission_pct": 0.0005, "slippage_pct": 0.0005}
TAX_ON = {"enabled": True, "short_term_rate": 0.35, "long_term_rate": 0.15, "long_term_days": 365}
TAX_OFF = {"enabled": False, "short_term_rate": 0.35, "long_term_rate": 0.15, "long_term_days": 365}

CASES: list[dict] = [
    {
        "id": "manual_buyhold_tax",
        "why": "Baseline. Minimal churn, so the terminal liquidation tax on "
               "unrealized long-term gains dominates — isolates that path.",
        "req": dict(tickers=BASKET, timer_id="buy_hold", timer_params={},
                    rebalance="M", start="2016-01-01", end="2021-12-31",
                    tax=TAX_ON, **COSTS),
    },
    {
        "id": "manual_buyhold_notax",
        "why": "Same run with taxes off. Diffing it against manual_buyhold_tax "
               "isolates the entire tax engine; pretax and aftertax must agree.",
        "req": dict(tickers=BASKET, timer_id="buy_hold", timer_params={},
                    rebalance="M", start="2016-01-01", end="2021-12-31",
                    tax=TAX_OFF, **COSTS),
    },
    {
        "id": "manual_macross_tax",
        "why": "High churn: in-and-out repeatedly, so realized short- vs "
               "long-term gains and the January annual settlement both fire.",
        "req": dict(tickers=BASKET, timer_id="ma_cross",
                    timer_params={"fast": 50, "slow": 200},
                    rebalance="M", start="2016-01-01", end="2021-12-31",
                    tax=TAX_ON, **COSTS),
    },
    {
        "id": "manual_macross_gfc",
        "why": "Spans 2008. Net-loss years exercise the loss carryforward and "
               "the losses-against-short-term-gains-first netting order.",
        "req": dict(tickers=BASKET, timer_id="ma_cross",
                    timer_params={"fast": 50, "slow": 200},
                    rebalance="M", start="2007-01-01", end="2010-12-31",
                    tax=TAX_ON, **COSTS),
    },
    {
        "id": "momentum_buyhold_m",
        "why": "Picker mode: monthly rebalance ranking, equal-weight basket "
               "rewrites, and the order_target_percent sizing path.",
        "req": dict(picker_id="momentum", picker_params={}, timer_id="buy_hold",
                    timer_params={}, top_n=15, rebalance="M",
                    start="2016-01-01", end="2021-12-31", universe="all",
                    tax=TAX_ON, **COSTS),
    },
    {
        "id": "momentum_macross_pit",
        "why": "Point-in-time S&P 500 universe — membership changes by date, "
               "the trickiest data-layout path to port.",
        "req": dict(picker_id="momentum", picker_params={}, timer_id="ma_cross",
                    timer_params={"fast": 50, "slow": 200}, top_n=15,
                    rebalance="M", start="2016-01-01", end="2021-12-31",
                    universe="sp500-pit", tax=TAX_ON, **COSTS),
    },
    {
        "id": "relstr_rsi_q",
        "why": "Different picker+timer math (relative strength, RSI hysteresis) "
               "and the quarterly rebalance cadence.",
        "req": dict(picker_id="relative_strength", picker_params={},
                    timer_id="rsi",
                    timer_params={"period": 14, "oversold": 30.0, "exit_level": 70.0},
                    top_n=10, rebalance="Q", start="2016-01-01", end="2021-12-31",
                    universe="all", tax=TAX_ON, **COSTS),
    },
    {
        "id": "value_trendstop_w",
        "why": "Fundamental picker (snapshot lookup + look-ahead-flagged) and a "
               "timer that depends on entry_price, plus weekly cadence.",
        "req": dict(picker_id="value_pe", picker_params={}, timer_id="trend_stop",
                    timer_params={"ma_window": 200, "stop": 0.08}, top_n=10,
                    rebalance="W", start="2019-01-01", end="2021-12-31",
                    universe="all", tax=TAX_ON, **COSTS),
    },
    {
        "id": "momentum_daily_covid",
        "why": "Daily rebalance across the COVID crash — max churn against a "
               "violent drawdown; stresses cash/no-leverage clamping.",
        "req": dict(picker_id="momentum", picker_params={}, timer_id="buy_hold",
                    timer_params={}, top_n=10, rebalance="D",
                    start="2019-01-01", end="2020-12-31", universe="all",
                    tax=TAX_ON, **COSTS),
    },
    {
        "id": "random_seeded",
        "why": "RandomPicker(seed=42), which draws from random.Random.sample "
               "(Mersenne Twister). Phase 0 flagged this as unportable; Phase 3 "
               "made it portable by reimplementing MT19937, getrandbits, "
               "_randbelow and sample in web/engine/src/mt19937.ts, so the TS "
               "engine reproduces the stream exactly.",
        "portable": True,
        "req": dict(picker_id="random", picker_params={"seed": 42},
                    timer_id="buy_hold", timer_params={}, top_n=10,
                    rebalance="M", start="2016-01-01", end="2021-12-31",
                    universe="all", tax=TAX_ON, **COSTS),
    },
]

# ---------------------------------------------------------------------------
# Component coverage (added in Phase 3).
#
# The cases above exercise only 4 of the 10 pickers and 4 of the 10 timers.
# A port can pass all of them and still have a broken MACD or a mis-ranked
# dividend screen. These add one case per otherwise-untested component over a
# common short window, so every picker and every timer is pinned by an
# end-to-end golden rather than by inspection.
#
# The fundamental pickers matter most here: `high_dividend` (110 tie groups)
# and `growth_revenue` (113) rank on columns with many duplicate values, and
# pandas' sort_values uses a NON-stable quicksort — so these cases are what
# reveal whether tie ordering at the top-n cutoff is reproducible at all.
# ---------------------------------------------------------------------------
_WINDOW = dict(start="2019-01-01", end="2021-12-31", universe="all")

for _timer_id, _params in [
    ("macd", {"fast": 12, "slow": 26, "signal": 9}),
    ("bollinger", {"window": 20, "k": 2.0}),
    ("momentum12", {"lookback": 252, "threshold": 0.0}),
    ("dual_momentum", {"lookback": 252, "benchmark": "SPY"}),
    ("turtle", {"entry_window": 252, "exit_window": 100}),
    ("vol_reversion", {"short": 20, "long": 100, "spike": 1.5}),
]:
    CASES.append({
        "id": f"cover_timer_{_timer_id}",
        "why": f"Component coverage for the {_timer_id} timer, which no other "
               f"golden exercises.",
        "req": dict(picker_id="momentum", picker_params={}, timer_id=_timer_id,
                    timer_params=_params, top_n=10, rebalance="M",
                    tax=TAX_ON, **_WINDOW, **COSTS),
    })

CASES.append({
    "id": "cover_picker_high_dividend_topn25",
    "why": "Deliberately pushes the top-n cutoff PAST the first tie divergence. "
           "dividendYield has 110 tie groups and pandas' default quicksort "
           "orders them differently from a stable sort starting at rank 11, so "
           "top_n=10 hides the problem and top_n=25 exposes it. This case exists "
           "to keep tie ordering pinned.",
    "req": dict(picker_id="high_dividend", picker_params={}, timer_id="buy_hold",
                timer_params={}, top_n=25, rebalance="M",
                tax=TAX_ON, **_WINDOW, **COSTS),
})

for _picker_id in [
    "price_to_book", "small_cap", "quality_roe",
    "growth_revenue", "high_dividend", "earnings_surprise",
]:
    CASES.append({
        "id": f"cover_picker_{_picker_id}",
        "why": f"Component coverage for the {_picker_id} picker, which no other "
               f"golden exercises. Fundamental snapshot ranking — see the note "
               f"about non-stable tie ordering.",
        "req": dict(picker_id=_picker_id, picker_params={}, timer_id="buy_hold",
                    timer_params={}, top_n=10, rebalance="M",
                    tax=TAX_ON, **_WINDOW, **COSTS),
    })


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------
def sanitize(obj):
    """Make a payload strict-JSON safe.

    Python's json emits bare NaN/Infinity, which is invalid JSON and blows up
    JSON.parse on the TS side. Map non-finite floats to null so the golden files
    are parseable by any conforming reader. Ints stay ints; everything else is
    passed through unchanged so float precision is preserved exactly (repr
    round-trips in CPython).
    """
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]
    if isinstance(obj, bool) or obj is None or isinstance(obj, (int, str)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    # pandas/numpy scalars and Timestamps
    if hasattr(obj, "item"):
        try:
            return sanitize(obj.item())
        except Exception:
            pass
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def dumps(payload: dict) -> str:
    # sort_keys so byte-comparison is meaningful; allow_nan=False to assert the
    # sanitize pass actually caught everything.
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_fingerprint() -> dict:
    """A digest of the price/fundamental inputs.

    Goldens are only meaningful against the data that produced them, so record
    a combined hash over every CSV. If someone re-downloads prices, this changes
    and the parity failures are explained rather than mysterious.
    """
    data_dir = ROOT / "data"
    files = sorted(p for p in data_dir.glob("*.csv"))
    combined = hashlib.sha256()
    for p in files:
        combined.update(p.name.encode())
        combined.update(sha256_file(p).encode())
    fundamentals = data_dir / "fundamentals.csv"
    return {
        "n_files": len(files),
        "combined_sha256": combined.hexdigest(),
        "fundamentals_sha256": sha256_file(fundamentals) if fundamentals.exists() else None,
    }


def env_fingerprint() -> dict:
    import numpy, pandas  # noqa: E402

    def git(*args):
        try:
            return subprocess.run(["git", "-C", str(ROOT), *args],
                                  capture_output=True, text=True, check=True).stdout.strip()
        except Exception:
            return None

    return {
        "python": sys.version.split()[0],
        "pandas": pandas.__version__,
        "numpy": numpy.__version__,
        "git_commit": git("rev-parse", "HEAD"),
        "git_dirty": bool(git("status", "--porcelain")),
    }


# ---------------------------------------------------------------------------
def build_payload(svc, case: dict) -> dict:
    from models import BacktestRequest

    req = BacktestRequest(**case["req"])
    result = svc.run_backtest(req)
    return sanitize({
        "id": case["id"],
        "why": case["why"],
        "portable": case.get("portable", True),
        "request": case["req"],
        "result": result,
    })


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="Regenerate and compare against golden/ without writing.")
    args = ap.parse_args()

    from service import EngineService

    t0 = time.time()
    svc = EngineService()
    print(f"engine loaded in {time.time() - t0:.1f}s ({len(svc.available)} tickers)")

    GOLDEN_DIR.mkdir(exist_ok=True)
    manifest_cases = []
    failures = []

    for case in CASES:
        t = time.time()
        payload = build_payload(svc, case)

        # Determinism gate: the same case run twice must serialize identically.
        # A failure here means the oracle itself is unstable and nothing
        # downstream can be trusted.
        again = build_payload(svc, case)
        if dumps(payload) != dumps(again):
            failures.append(f"{case['id']}: NOT DETERMINISTIC across two runs")
            print(f"  {case['id']:32} NON-DETERMINISTIC")
            continue

        text = dumps(payload)
        out = GOLDEN_DIR / f"{case['id']}.json"
        m = payload["result"]["metrics"]
        n_trades = len(payload["result"]["trades"])
        n_days = len(payload["result"]["equity_curve"]["dates"])

        if args.check:
            if not out.exists():
                failures.append(f"{case['id']}: golden file missing")
            elif out.read_text() != text:
                failures.append(f"{case['id']}: differs from golden")
        else:
            out.write_text(text)

        manifest_cases.append({
            "id": case["id"],
            "why": case["why"],
            "portable": case.get("portable", True),
            "file": out.name,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "n_days": n_days,
            "n_trades": n_trades,
            "final_value": m.get("final_value"),
            "total_tax": m.get("total_tax"),
        })
        print(f"  {case['id']:32} {n_days:>5}d {n_trades:>6} trades  "
              f"final=${m.get('final_value', 0):>14,.2f}  {time.time() - t:.1f}s")

    manifest = {
        "purpose": "Reference-oracle outputs frozen from the Python engine. "
                   "The TypeScript port must reproduce these within tolerance.",
        "generated_by": "tools/gen_golden.py",
        "entry_point": "reference/service.py::EngineService.run_backtest",
        "tolerance": {
            "python_vs_python": "exact (byte-identical serialization)",
            "python_vs_typescript": "rel 1e-9 on equity/metrics; trade counts, "
                                    "tickers, sides and dates must match exactly",
        },
        "portability_notes": [
            "RESOLVED in Phase 3: the random picker's CPython Mersenne Twister "
            "is reimplemented in web/engine/src/mt19937.ts, so random_seeded is "
            "now portable and passes parity.",
            "Float formatting differs between Python repr and JS toString; "
            "compare parsed numbers, never serialized strings.",
            "pandas .std() defaults to ddof=1 (sample) — a naive TS std() with "
            "ddof=0 will drift. pandas .mean()/.sum() use NumPy pairwise "
            "summation, not a left-to-right loop.",
            "pandas pct_change is x[i]/x[i-1]-1, and ewm(adjust=False) is "
            "a*x+(1-a)*prev; the algebraically equivalent rewrites of either "
            "are not bit-identical.",
            "Python round(x, n) is half-to-even on the float's EXACT value. "
            "JS toFixed rounds half away from zero and scaling by 10^n first "
            "destroys the tie — see serialize.ts::pyRound.",
            "Fundamental pickers rank with sort_values(kind='stable'). The "
            "pandas default (quicksort) is not stable, and several columns have "
            "many duplicate values, which made the top-n SELECTION an artifact "
            "of the sort implementation whenever a tie straddled the cutoff. "
            "cover_picker_high_dividend_topn25 pins this.",
        ],
        "env": env_fingerprint(),
        "data": data_fingerprint(),
        "cases": manifest_cases,
    }
    mpath = GOLDEN_DIR / "manifest.json"
    if not args.check:
        mpath.write_text(dumps(manifest))

    if failures:
        print("\nFAILURES:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\n{len(manifest_cases)} cases {'verified' if args.check else 'written'} "
          f"-> {GOLDEN_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
