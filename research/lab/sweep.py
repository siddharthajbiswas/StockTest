"""Run many configs over a protocol, in parallel, with an on-disk cache.

    from research.lab import sweep
    recs = sweep.run(configs, protocol="screen", regimes=("CA",), workers=6)
    table = sweep.table(recs)            # one row per (config, regime), key stats

Each (config, regime, protocol, costs) result is cached as one JSON file in
research/lab/cache/runs/, keyed by the config, the costs and a hash of the code
it depends on (so editing a family's module re-runs its configs). Re-running a
sweep is therefore cheap, and many agents can share results.

At most LAB_SLOTS (default 12) backtest tasks run concurrently machine-wide no
matter how many sweeps are running, and at most LAB_HEAVY_SLOTS (default 4)
whole-stock-universe tasks.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
RUNS = LAB / "cache" / "runs"


def _ensure_path():
    for p in (str(ROOT), str(ROOT / "reference")):
        if p not in sys.path:
            sys.path.insert(0, p)


_ensure_path()

from . import core, data, metrics, registry  # noqa: E402


def cfg_id(cfg: dict) -> str:
    return hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:14]


def _key(cfg, regime, protocol, comm, slip) -> str:
    payload = json.dumps([cfg, regime, protocol, comm, slip, registry.code_version(cfg)],
                         sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:20]


def _path(key: str) -> Path:
    return RUNS / key[:2] / f"{key}.json"


def run_one(cfg: dict, regime: str = "CA", protocol: str = "screen",
            comm: float = core.COMMISSION, slip: float = core.SLIPPAGE,
            use_cache: bool = True) -> dict:
    """Run (or load) one config over a protocol for one tax regime."""
    _ensure_path()
    registry.load_families()
    key = _key(cfg, regime, protocol, comm, slip)
    path = _path(key)
    if use_cache and path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    kind = registry.kind_of(cfg)
    prot = core.PROTOCOLS[protocol]
    t_start = time.time()
    with core.cpu_slot(heavy=kind.heavy(cfg)):
        universe = kind.universe(cfg)
        tick = kind.tickers(cfg)
        missing = [t for t in tick if data.path_for(t) is None]
        if missing:
            raise ValueError(f"no data for {missing}")
        mkt = data.market(tick, universe=universe)
        ms = registry.min_start(cfg)
        starts = [s for s in prot.starts if ms is None or s >= ms]
        out = core.run_starts(lambda: kind.build(cfg), mkt, core.policy_for(regime), prot,
                              starts=starts, comm=comm, slip=slip)
    rec = {"id": cfg_id(cfg), "cfg": cfg, "regime": regime, "protocol": protocol,
           "comm": comm, "slip": slip, "elapsed": time.time() - t_start, **out}
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".tmp{os.getpid()}")
    tmp.write_text(json.dumps(rec))
    tmp.replace(path)
    if kind.heavy(cfg):
        data.clear_markets()
    return rec


def _task(args):
    cfg, regime, protocol, comm, slip = args
    try:
        return run_one(cfg, regime, protocol, comm, slip)
    except Exception as e:  # noqa: BLE001
        return {"id": cfg_id(cfg), "cfg": cfg, "regime": regime, "protocol": protocol,
                "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()}


def cached(cfg, regime="CA", protocol="screen", comm=core.COMMISSION, slip=core.SLIPPAGE):
    registry.load_families()
    p = _path(_key(cfg, regime, protocol, comm, slip))
    return json.loads(p.read_text()) if p.exists() else None


def run(configs, protocol: str = "screen", regimes=("CA",), workers: int = 6,
        comm: float = core.COMMISSION, slip: float = core.SLIPPAGE,
        verbose: bool = True) -> list[dict]:
    """Run every config x regime; returns records (cached ones load instantly).

    Failed tasks come back as records with an "error" field (never raised), so
    one bad config does not lose a sweep.
    """
    registry.load_families()
    jobs, recs = [], []
    for cfg in configs:
        for rg in regimes:
            c = cached(cfg, rg, protocol, comm, slip)
            if c is not None:
                recs.append(c)
            else:
                jobs.append((cfg, rg, protocol, comm, slip))
    if verbose:
        print(f"[sweep] {len(recs)} cached, {len(jobs)} to run, workers={workers}", flush=True)
    if not jobs:
        return recs
    t0 = time.time()
    if workers <= 1:
        for j in jobs:
            recs.append(_task(j))
        return recs
    # A process per worker; heavy tasks drop their market after running.
    # "fork", not macOS's default "spawn": spawn re-imports the caller's main
    # module, which fails for stdin/heredoc scripts and needs a __main__ guard.
    # Workers only use pandas/numpy, for which fork is safe.
    import multiprocessing as mp
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*fork.*")
    with ProcessPoolExecutor(max_workers=workers, mp_context=mp.get_context("fork")) as ex:
        futs = [ex.submit(_task, j) for j in jobs]
        for n, f in enumerate(as_completed(futs), 1):
            r = f.result()
            recs.append(r)
            if verbose and (n % max(1, len(jobs) // 20) == 0 or n == len(jobs)):
                el = time.time() - t0
                print(f"[sweep] {n}/{len(jobs)} done, {el:.0f}s elapsed, "
                      f"~{el / n * (len(jobs) - n):.0f}s left", flush=True)
    errs = [r for r in recs if "error" in r]
    if errs and verbose:
        print(f"[sweep] {len(errs)} errors; first: {errs[0]['error']}", flush=True)
    return recs


def table(recs: list[dict], label=None) -> pd.DataFrame:
    """One row per record with the headline statistics (see metrics.summary)."""
    rows = []
    for r in recs:
        if "error" in r:
            continue
        s = metrics.summary(r)
        s["id"] = r["id"]
        s["regime"] = r["regime"]
        s["label"] = label(r["cfg"]) if label else json.dumps(r["cfg"], sort_keys=True)
        rows.append(s)
    df = pd.DataFrame(rows)
    if not df.empty:
        front = ["label", "regime", "full_excess", "full_cagr", "bench_full_cagr",
                 "ex10_mean", "ex10_beat", "ex10_min", "ex5_mean", "ex5_beat", "ex15_mean",
                 "ex15_beat", "ex20_mean", "ex20_beat", "boot_lo", "boot_p", "max_dd",
                 "bench_max_dd", "trades", "turnover"]
        cols = [c for c in front if c in df.columns] + [c for c in df.columns if c not in front]
        df = df[cols]
    return df
