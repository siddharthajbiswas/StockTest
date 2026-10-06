"""Window statistics, confidence intervals and overfitting diagnostics.

All comparisons are against the protocol's benchmark (SPY buy-and-hold, or the
VFINX index fund for the long-history protocol) run through the same engine
with the same tax regime and costs, so "excess" is exactly what the site's
"vs S&P 500" panel reports for that window: after-tax CAGR (fully liquidated
at the window's end) minus the benchmark's.
"""
from __future__ import annotations

import itertools
import math

import numpy as np
import pandas as pd
from scipy import stats as sps

from . import core

CASH = core.CASH
BEAT_EPS = 1e-5     # 0.001 pp: below this an "excess" is float noise, not a win
HOLDOUT_END = "2000-01-01"


# --------------------------------------------------------------------------
# windows
# --------------------------------------------------------------------------
def _cagr(liq: float, t0: str, day: str) -> float | None:
    days = (pd.Timestamp(day) - pd.Timestamp(t0)).days
    if days <= 0 or liq <= 0:
        return None
    return (liq / CASH) ** (365.25 / days) - 1.0


def _add_years(s: str, years: int) -> str:
    t = pd.Timestamp(s)
    return (t + pd.DateOffset(years=years)).strftime("%Y-%m-%d")


def window(rec: dict, start: str, end: str) -> float | None:
    st = rec["starts"].get(start)
    if not st:
        return None
    v = st["ck"].get(end)
    if not v:
        return None
    return _cagr(v[0], st["t0"], v[2])


def bench_for(rec: dict) -> dict:
    return core.benchmark(rec["protocol"], rec["regime"], rec.get("comm", core.COMMISSION),
                          rec.get("slip", core.SLIPPAGE))


def windows(rec: dict, bench: dict | None = None, lengths=None) -> pd.DataFrame:
    """Every (start, end) window of the protocol's lengths, plus 'to end'."""
    bench = bench or bench_for(rec)
    prot = core.PROTOCOLS[rec["protocol"]]
    lengths = lengths or prot.lengths
    end_all = core._ts(prot.checkpoints[-1])
    rows = []
    for s in rec["starts"]:
        for L in list(lengths) + ["end"]:
            e = end_all if L == "end" else _add_years(s, L)
            if pd.Timestamp(e) > pd.Timestamp(end_all):
                continue
            a = window(rec, s, e)
            b = window(bench, s, e)
            if a is None or b is None:
                continue
            rows.append((s, e, L, a, b, a - b))
    return pd.DataFrame(rows, columns=["start", "end", "length", "cagr", "bench", "excess"])


# --------------------------------------------------------------------------
# monthly after-tax liquidation series (first start's run)
# --------------------------------------------------------------------------
def monthly_excess(rec: dict, bench: dict | None = None) -> pd.Series:
    """Monthly log excess return of the after-tax liquidation value vs benchmark."""
    bench = bench or bench_for(rec)
    first = min(rec["starts"]) if rec.get("starts") else None
    bm = bench["monthly"]
    if first and min(bench["starts"]) != first:
        bm = core.benchmark_monthly(rec["protocol"], rec["regime"], first,
                                    rec.get("comm", core.COMMISSION), rec.get("slip", core.SLIPPAGE))
    a = pd.Series({pd.Timestamp(k): v[0] for k, v in rec["monthly"].items()}).sort_index()
    b = pd.Series({pd.Timestamp(k): v[0] for k, v in bm.items()}).sort_index()
    a.index = a.index.to_period("M")
    b.index = b.index.to_period("M")
    j = a.index.intersection(b.index)
    a, b = a[j], b[j]
    la = np.log(np.r_[CASH, a.values])
    lb = np.log(np.r_[CASH, b.values])
    x = np.diff(la) - np.diff(lb)
    return pd.Series(x, index=j)


def stationary_bootstrap(x: np.ndarray, n_boot: int = 2000, block: float = 12.0,
                         seed: int = 7) -> np.ndarray:
    """Politis-Romano stationary bootstrap of the mean of `x` (vectorised):
    resample blocks of geometric length (mean `block`), wrapping around."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 6:
        return np.array([np.nan])
    rng = np.random.default_rng(seed)
    r = rng.integers(n, size=(n_boot, n))
    nb = rng.random((n_boot, n)) < (1.0 / block)
    nb[:, 0] = True
    pos = np.where(nb, np.arange(n), 0)
    last = np.maximum.accumulate(pos, axis=1)
    idx = (r[np.arange(n_boot)[:, None], last] + (np.arange(n) - last)) % n
    return x[idx].mean(axis=1)


def boot_stats(x: pd.Series, n_boot: int = 2000) -> dict:
    if len(x) < 12:
        return {}
    bm = stationary_bootstrap(x.values, n_boot=n_boot) * 12.0
    ann = float(x.mean() * 12.0)
    sd = float(x.std(ddof=1) * math.sqrt(12.0))
    return {
        "boot_mean": ann,
        "boot_lo": float(np.percentile(bm, 5)),
        "boot_hi": float(np.percentile(bm, 95)),
        "boot_p": float((bm <= 0).mean()),        # one-sided bootstrap p-value
        "te": sd,                                  # tracking error (after-tax)
        "ir": ann / sd if sd > 0 else 0.0,
    }


_BFULL: dict = {}


def _bench_full_from(rec: dict, start: str) -> dict | None:
    """Benchmark run stats (drawdown, Sharpe, vol) from `start`, so a strategy
    that starts late is compared with SPY over its own period."""
    import hashlib
    import json as _json
    import os
    prot = core.PROTOCOLS[rec["protocol"]]
    comm, slip = rec.get("comm", core.COMMISSION), rec.get("slip", core.SLIPPAGE)
    key = (prot.name, rec["regime"], prot.benchmark, comm, slip, start)
    if key in _BFULL:
        return _BFULL[key]
    h = hashlib.sha1(_json.dumps([*map(str, key), "benchf-v1"]).encode()).hexdigest()[:16]
    path = core.CACHE_DIR / "bench" / f"f{h}.json"
    if path.exists():
        out = _json.loads(path.read_text())
    else:
        from . import data as _data
        m = _data.market([prot.benchmark])
        r = core.run_starts(lambda: core.BuyHoldOne(prot.benchmark), m, core.policy_for(rec["regime"]),
                            prot, starts=[pd.Timestamp(start)], comm=comm, slip=slip, full_stats=True)
        out = r.get("full")
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".tmp{os.getpid()}")
        tmp.write_text(_json.dumps(out))
        tmp.replace(path)
    _BFULL[key] = out
    return out


# --------------------------------------------------------------------------
# the headline summary
# --------------------------------------------------------------------------
def summary(rec: dict, bench: dict | None = None, n_boot: int = 1000) -> dict:
    bench = bench or bench_for(rec)
    prot = core.PROTOCOLS[rec["protocol"]]
    w = windows(rec, bench)
    out: dict = {}
    if not rec["starts"]:
        return out
    first = min(rec["starts"])
    out["first_start"] = first
    full = w[(w.start == first) & (w.length == "end")]
    if len(full):
        out["full_cagr"] = float(full.cagr.iloc[0])
        out["bench_full_cagr"] = float(full.bench.iloc[0])
        out["full_excess"] = float(full.excess.iloc[0])
    for L in prot.lengths:
        x = w[w.length == L].excess
        if len(x) == 0:
            continue
        out[f"ex{L}_n"] = int(len(x))
        out[f"ex{L}_mean"] = float(x.mean())
        out[f"ex{L}_median"] = float(x.median())
        out[f"ex{L}_beat"] = float((x > BEAT_EPS).mean())
        out[f"ex{L}_min"] = float(x.min())
        out[f"ex{L}_p10"] = float(x.quantile(0.10))
    # Pre-2000 holdout: windows that END before the ETF era (long protocols).
    # The ETF-era strategies were designed on 1999-2026 data, so these windows
    # are genuinely out of sample for them.
    ho = w[(w.end <= HOLDOUT_END) & (w.length != "end")]
    for L in (5, 10):
        x = ho[ho.length == L].excess
        if len(x):
            out[f"ho{L}_n"] = int(len(x))
            out[f"ho{L}_mean"] = float(x.mean())
            out[f"ho{L}_beat"] = float((x > BEAT_EPS).mean())
    if rec.get("monthly"):
        out.update(boot_stats(monthly_excess(rec, bench), n_boot=n_boot))
    f = rec.get("full") or {}
    bf = bench.get("full") or {}
    if rec["starts"] and bench.get("starts") and min(rec["starts"]) != min(bench["starts"]):
        bf = _bench_full_from(rec, min(rec["starts"])) or bf
    out["max_dd"] = f.get("max_drawdown")
    out["bench_max_dd"] = bf.get("max_drawdown")
    out["sharpe"] = f.get("sharpe")
    out["bench_sharpe"] = bf.get("sharpe")
    out["vol"] = f.get("vol")
    out["trades"] = f.get("trades")
    out["turnover"] = f.get("turnover")
    out["taxes_paid"] = f.get("taxes_paid")
    out["avg_cash"] = f.get("avg_cash_frac")
    return out


# --------------------------------------------------------------------------
# overfitting diagnostics across a family of configs
# --------------------------------------------------------------------------
def excess_matrix(recs: list[dict], length) -> pd.DataFrame:
    """index = window start, columns = config id, values = excess for windows
    of `length` years (or 'end')."""
    cols = {}
    for r in recs:
        if "error" in r:
            continue
        w = windows(r, lengths=[length] if length != "end" else [])
        w = w[w.length == length]
        cols[r["id"]] = w.set_index("start").excess
    return pd.DataFrame(cols).sort_index()


def walk_forward(recs: list[dict], is_years: int = 10, oos_years: int = 5,
                 step_quarters: int = 4, step_years: int | None = 1) -> dict:
    """Simulate running this search in the past.

    At each decision date T: pick the config with the best excess over the
    trailing `is_years` window (T - is_years -> T), then score it on the next
    `oos_years` (T -> T + oos_years), started fresh at T. Only information
    available at T is used to choose. Compares the chosen config's out-of-
    sample excess with the average config's, and with the in-sample excess the
    winner showed (the 'shrinkage').
    """
    recs = [r for r in recs if "error" not in r]
    if not recs:
        return {}
    prot = core.PROTOCOLS[recs[0]["protocol"]]
    bench = bench_for(recs[0])
    starts = [core._ts(s) for s in prot.starts]
    end_all = pd.Timestamp(prot.checkpoints[-1])
    rows = []
    if step_years:
        # One decision per `step_years` of calendar time (the old index step
        # meant one decision every 4 YEARS on yearly protocols).
        t0 = pd.Timestamp(starts[0])
        dec = [s for s in starts
               if pd.Timestamp(s).month == t0.month and pd.Timestamp(s).day == t0.day
               and (pd.Timestamp(s).year - t0.year) % step_years == 0]
    else:
        dec = starts[::step_quarters]
    for T in dec:
        s_is = _add_years(T, -is_years)
        e_oos = _add_years(T, oos_years)
        if s_is not in starts or pd.Timestamp(e_oos) > end_all:
            continue
        b_is, b_oos = window(bench, s_is, T), window(bench, T, e_oos)
        if b_is is None or b_oos is None:
            continue
        scored = []
        for r in recs:
            a_is, a_oos = window(r, s_is, T), window(r, T, e_oos)
            if a_is is None or a_oos is None:
                continue
            scored.append((a_is - b_is, a_oos - b_oos, r["id"]))
        if not scored:
            continue
        scored.sort(reverse=True)
        best = scored[0]
        allo = np.array([s[1] for s in scored])
        rows.append({"T": T, "chosen": best[2], "is_excess": best[0], "oos_excess": best[1],
                     "oos_rank_pct": float((allo < best[1]).mean()),
                     "avg_oos_excess": float(allo.mean()), "n": len(scored)})
    df = pd.DataFrame(rows)
    if df.empty:
        return {"rows": df}
    return {
        "rows": df,
        "oos_mean": float(df.oos_excess.mean()),
        "oos_beat": float((df.oos_excess > BEAT_EPS).mean()),
        "is_mean": float(df.is_excess.mean()),
        "avg_config_oos_mean": float(df.avg_oos_excess.mean()),
        "mean_oos_rank_pct": float(df.oos_rank_pct.mean()),
    }


def monthly_matrix(recs: list[dict], min_share: float = 0.8) -> pd.DataFrame:
    """Months x configs of monthly after-tax excess. Uses the window covered
    by at least `min_share` of configs and DROPS configs that do not cover it
    (instead of truncating everyone to the latest starter's months)."""
    cols = {}
    for r in recs:
        if "error" in r or not r.get("monthly"):
            continue
        cols[r["id"]] = monthly_excess(r)
    M = pd.DataFrame(cols)
    if M.empty:
        return M
    cov = M.notna().sum(axis=1)
    window = cov[cov >= min_share * M.shape[1]].index
    M = M.loc[window].dropna(axis=1)
    M.attrs["dropped_configs"] = len(cols) - M.shape[1]
    return M


def cscv_pbo(M: pd.DataFrame, n_blocks: int = 16, max_combos: int = 5000, seed: int = 3) -> dict:
    """Probability of Backtest Overfitting (Bailey, Borwein, Lopez de Prado,
    Zhu 2014) via combinatorially-symmetric cross-validation on monthly excess
    returns. PBO = share of IS/OOS splits where the in-sample best config lands
    below the OOS median."""
    X = M.values
    T, N = X.shape
    if N < 2 or T < n_blocks * 2:
        return {}
    blocks = np.array_split(np.arange(T), n_blocks)
    combos = list(itertools.combinations(range(n_blocks), n_blocks // 2))
    rng = np.random.default_rng(seed)
    if len(combos) > max_combos:
        combos = [combos[i] for i in rng.choice(len(combos), max_combos, replace=False)]
    logits, degr = [], []
    for c in combos:
        is_idx = np.concatenate([blocks[i] for i in c])
        oos_idx = np.concatenate([blocks[i] for i in range(n_blocks) if i not in c])
        is_perf = X[is_idx].mean(0)
        oos_perf = X[oos_idx].mean(0)
        b = int(np.argmax(is_perf))
        rank = (sps.rankdata(oos_perf)[b]) / (N + 1)
        logits.append(math.log(rank / (1 - rank)))
        degr.append((is_perf[b] * 12, oos_perf[b] * 12))
    logits = np.array(logits)
    d = np.array(degr)
    return {"pbo": float((logits <= 0).mean()), "n_configs": N, "n_splits": len(combos),
            "is_best_mean": float(d[:, 0].mean()), "oos_of_is_best_mean": float(d[:, 1].mean()),
            "oos_of_is_best_p_pos": float((d[:, 1] > 0).mean())}


def deflated_sharpe(x: pd.Series, n_trials: int, sr_std_across_trials: float | None = None) -> dict:
    """Deflated Sharpe ratio (Bailey & Lopez de Prado 2014) of a monthly excess
    series, given how many configurations were tried. Returns the probability
    that the true (excess) Sharpe is > 0 after accounting for the search."""
    x = np.asarray(x, float)
    T = len(x)
    if T < 24 or x.std(ddof=1) == 0:
        return {}
    sr = x.mean() / x.std(ddof=1)
    sk = float(sps.skew(x))
    ku = float(sps.kurtosis(x, fisher=False))
    v = sr_std_across_trials ** 2 if sr_std_across_trials else (1.0 / T)
    g = 0.5772156649
    N = max(int(n_trials), 2)
    sr0 = math.sqrt(v) * ((1 - g) * sps.norm.ppf(1 - 1.0 / N) + g * sps.norm.ppf(1 - 1.0 / (N * math.e)))
    den = math.sqrt(max(1e-12, 1 - sk * sr + (ku - 1) / 4.0 * sr * sr))
    z = (sr - sr0) * math.sqrt(T - 1) / den
    return {"sr_monthly": sr, "sr_annual": sr * math.sqrt(12), "sr0_monthly": sr0,
            "dsr": float(sps.norm.cdf(z)), "psr": float(sps.norm.cdf(sr * math.sqrt(T - 1) / den))}
