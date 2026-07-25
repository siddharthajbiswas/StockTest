"""Out-of-sample validation, reusing walkforward.py's engine and metrics.

The heavy lifting — running every combo once over the span, net of everything —
is `walkforward.run_all_curves`, imported and called directly (not reimplemented).
We add the user's *exact* configured combo as an extra curve (so custom params
and manual baskets are validated for real), then compute the holdout rank
persistence and the walk-forward track record using walkforward's own
`window_cagr` / `window_return` helpers.

`ValidationRunner` runs each validation on a single background thread (it is
slower than a plain backtest — it reruns many combos over many windows) and
exposes a simple job registry the API can poll.
"""

from __future__ import annotations

import math
import os
import sys
import threading
import time
import uuid
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import walkforward as wf  # noqa: E402

# Run the combo sweep across several worker processes by default. This is what
# keeps a validation from freezing the whole API: with jobs=1 the sweep runs
# ~30 CPU-bound backtests serially on the runner thread, which holds the GIL for
# a minute-plus and starves every other request (even /health and the page's
# own startup calls). With jobs>1 the heavy work happens in child processes and
# the parent thread just waits on results, releasing the GIL. Override with
# STOCKTEST_VALIDATE_JOBS (set it to 1 to force the old serial behavior).
_DEFAULT_JOBS = max(1, min(4, (os.cpu_count() or 2) - 1))


def _finite(x) -> float | None:
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def _to_request(cfg):
    """Build a BacktestRequest from a StrategyConfig for engine.net_equity_series."""
    from models import BacktestRequest  # local import to avoid a cycle

    base = dict(
        timer_id=cfg.timer_id,
        timer_params=cfg.timer_params,
        start=cfg.start,
        end=cfg.end,
        cash=100_000.0,
        commission_pct=cfg.commission_pct,
        slippage_pct=cfg.slippage_pct,
        tax=cfg.tax,
    )
    if cfg.mode == "manual":
        return BacktestRequest(tickers=cfg.tickers, **base)
    return BacktestRequest(
        picker_id=cfg.picker_id,
        picker_params=cfg.picker_params,
        top_n=cfg.top_n,
        rebalance=cfg.rebalance,
        universe=cfg.universe,
        **base,
    )


def run_validation(
    cfg,
    engine,
    split: str | None = None,
    train_years: int = 3,
    step_years: int = 1,
    price_only: bool = True,
) -> dict:
    # --- 1. Run the walkforward sweep (all baseline combos, net of everything).
    args = SimpleNamespace(
        tickers=None,
        start=cfg.start,
        end=cfg.end,
        universe=cfg.universe if cfg.mode != "manual" else "sp500-pit",
        price_only=price_only,
        cash=100_000.0,
        commission_pct=cfg.commission_pct,
        slippage_pct=cfg.slippage_pct,
        st_rate=cfg.tax.short_term_rate if cfg.tax.enabled else 0.35,
        lt_rate=cfg.tax.long_term_rate if cfg.tax.enabled else 0.15,
        jobs=int(os.environ.get("STOCKTEST_VALIDATE_JOBS", str(_DEFAULT_JOBS))),
    )
    dates, curves, spy = wf.run_all_curves(args)

    # --- 2. The user's EXACT combo, aligned to the sweep's dates.
    series = engine.net_equity_series(_to_request(cfg))
    target = series.reindex(dates).ffill().bfill().to_numpy()

    span_years = (dates[-1] - dates[0]).days / 365.25
    # Keep enough post-train history for at least one out-of-sample step.
    train_years = max(1, min(train_years, int(span_years) - 1)) if span_years > 1 else 1

    holdout = _holdout(dates, curves, spy, target, split)
    walk = _walkforward(dates, curves, spy, target, train_years, step_years)
    verdict = _verdict(holdout, walk)

    return {
        "meta": {
            "n_baseline_combos": len(curves),
            "price_only": price_only,
            "period": {"start": dates[0].date().isoformat(), "end": dates[-1].date().isoformat()},
            "span_years": round(span_years, 1),
            "train_years": train_years,
            "step_years": step_years,
        },
        "holdout": holdout,
        "walkforward": walk,
        "verdict": verdict,
    }


def _holdout(dates, curves, spy, target, split) -> dict:
    if split is None:
        mid = dates[0] + (dates[-1] - dates[0]) / 2
        split = pd.Timestamp(mid.date())
    else:
        split = pd.Timestamp(split)
    tr = (dates[0], split)
    te = (split, dates[-1])

    train, test = [], []
    for c in curves.values():
        a = wf.window_cagr(dates, c, *tr)
        b = wf.window_cagr(dates, c, *te)
        if a == a and b == b:  # not NaN
            train.append(a)
            test.append(b)
    spearman = None
    if len(train) >= 3:
        spearman = _finite(pd.Series(train).corr(pd.Series(test), method="spearman"))

    tgt_train = wf.window_cagr(dates, target, *tr)
    tgt_test = wf.window_cagr(dates, target, *te)
    spy_train = wf.window_cagr(dates, spy, *tr)
    spy_test = wf.window_cagr(dates, spy, *te)

    n = len(test)
    train_rank = 1 + sum(1 for v in train if v > tgt_train)
    test_rank = 1 + sum(1 for v in test if v > tgt_test)

    return {
        "split": split.date().isoformat(),
        "spearman": spearman,
        "n_ranked": n,
        "spy_train_cagr": _finite(spy_train),
        "spy_test_cagr": _finite(spy_test),
        "your_train_cagr": _finite(tgt_train),
        "your_test_cagr": _finite(tgt_test),
        "your_train_rank": train_rank,
        "your_test_rank": test_rank,
        "beats_spy_test": bool(tgt_test == tgt_test and spy_test == spy_test and tgt_test > spy_test),
        "rank_held": bool(n > 0 and test_rank <= max(1, math.ceil(n / 3))),
    }


def _walkforward(dates, curves, spy, target, train_years, step_years) -> dict:
    start_y = dates[0].year + train_years
    end_y = dates[-1].year
    combos = list(curves)

    oos_growth = 1.0
    spy_growth = 1.0
    picks: list = []
    windows: list[dict] = []
    y = start_y
    while y < end_y:
        tr_start = pd.Timestamp(f"{y - train_years}-01-01")
        tr_end = pd.Timestamp(f"{y}-01-01")
        te_end = pd.Timestamp(f"{min(y + step_years, end_y + 1)}-01-01")
        scored = [(wf.window_cagr(dates, curves[c], tr_start, tr_end), c) for c in combos]
        scored = [(v, c) for v, c in scored if v == v]
        if not scored:
            y += step_years
            continue
        _, best = max(scored, key=lambda x: x[0])
        r = wf.window_return(dates, curves[best], tr_end, te_end)
        sr = wf.window_return(dates, spy, tr_end, te_end)
        if r == r and sr == sr:
            oos_growth *= 1 + r
            spy_growth *= 1 + sr
            picks.append(f"{best[0]} × {best[1]}")
            windows.append(
                {
                    "start": tr_end.date().isoformat(),
                    "end": te_end.date().isoformat(),
                    "picked": f"{best[0]} × {best[1]}",
                    "combo_return": _finite(r),
                    "spy_return": _finite(sr),
                }
            )
        y += step_years

    n_years = (dates[-1] - pd.Timestamp(f"{start_y}-01-01")).days / 365.25
    adaptive_cagr = oos_growth ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    spy_cagr = spy_growth ** (1 / n_years) - 1 if n_years > 0 else float("nan")

    # The user's own combo, out-of-sample (the post-train span).
    oos_start = pd.Timestamp(f"{start_y}-01-01")
    your_oos = wf.window_cagr(dates, target, oos_start, dates[-1])
    spy_oos = wf.window_cagr(dates, spy, oos_start, dates[-1])

    return {
        "has_windows": len(windows) > 0,
        "adaptive_oos_cagr": _finite(adaptive_cagr),
        "spy_oos_cagr": _finite(spy_cagr),
        "adaptive_beats_spy": bool(adaptive_cagr == adaptive_cagr and adaptive_cagr > spy_cagr),
        "your_oos_cagr": _finite(your_oos),
        "your_oos_beats_spy": bool(your_oos == your_oos and spy_oos == spy_oos and your_oos > spy_oos),
        "windows": windows,
        "most_picked": [{"combo": c, "count": n} for c, n in Counter(picks).most_common(3)],
    }


def _verdict(holdout: dict, walk: dict) -> dict:
    signals = [
        holdout["beats_spy_test"],
        holdout["rank_held"],
        walk["your_oos_beats_spy"],
    ]
    score = sum(1 for s in signals if s)
    if score >= 2:
        level = "held"
    elif score == 0:
        level = "failed"
    else:
        level = "mixed"
    return {
        "level": level,
        "score": score,
        "beats_spy_out_of_sample": holdout["beats_spy_test"],
        "rank_held": holdout["rank_held"],
        "walkforward_beats_spy": walk["your_oos_beats_spy"],
    }


# --------------------------- background job runner -------------------------
class ValidationRunner:
    """Runs validations one-at-a-time on a background thread (serialized, which
    also guards walkforward's module-global worker state), with a pollable job
    registry."""

    def __init__(self, engine):
        self.engine = engine
        self._ex = ThreadPoolExecutor(max_workers=1, thread_name_prefix="validate")
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def submit(self, cfg, params: dict) -> str:
        jid = uuid.uuid4().hex[:12]
        with self._lock:
            self._jobs[jid] = {"status": "running", "created": time.time()}
        self._ex.submit(self._run, jid, cfg, params)
        return jid

    def _run(self, jid: str, cfg, params: dict) -> None:
        try:
            result = run_validation(cfg, self.engine, **params)
            with self._lock:
                self._jobs[jid] = {"status": "done", "result": result}
        except Exception as e:  # surface a readable error to the poller
            with self._lock:
                self._jobs[jid] = {"status": "error", "error": str(e)}

    def get(self, jid: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(jid)
            return dict(job) if job else None
