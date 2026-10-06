"""Risk-based allocation and volatility management  (FAMILY_KEY = risk_alloc).

Allocation without return forecasts. Every signal registers as
"risk_alloc.<name>" and runs through kind "weights" (WeightStrategy), so costs,
tax lots, the annual settlement and the liquidation tax are the site's.

  voltarget  Volatility targeting of one risky asset (default SPY):
             exposure e = (target / forecast_vol) ** power, clipped to
             [floor, cap], optionally quantised to `step`. e <= 1: e in the
             asset, 1-e in the first tradable `cash` proxy (SHY / VFISX ...,
             or real cash if none). e > 1 ("levered", only via a leveraged ETF
             because the engine has no margin): mode "mix" holds the 1x asset
             plus the k-x ETF (SSO=2x, UPRO=3x) so that exposure = e with no
             cash; mode "pure" holds only the k-x ETF (e/k) plus cash proxy.
             Vol forecasts ("est"): "simple" rolling std of daily log returns
             over `window`; "ewma" (RiskMetrics, `halflife`); "max" =
             max(simple(window), simple(window2)) (fast de-risk, slow re-risk);
             "vix" = ^VIX / 100 lagged one day (implied vol); "blend" = mean of
             simple(window) and vix. Optional filters: trend (asset below its
             `trend_n`-day SMA -> exposure capped at `trend_cap`) and VIX term
             structure (VIX/VIX3M > `ts_thresh` -> exposure capped at `ts_cap`).
             `const_e` replaces the forecast by a constant exposure (the
             constant-leverage control for a levered vol target).
             Trading: on the WeightStrategy cadence (band = 0), or a no-trade
             band (band > 0): trade only when |target - actual exposure| >
             band, checked every day when `daily` is true.
  riskpar    Multi-asset weights from risk only: "equal", "invvol", "invvar",
             "erc" (equal risk contribution, full covariance), "minvar"
             (long-only minimum variance), "maxdiv" (maximum diversification
             ratio), "hrp" (hierarchical risk parity, Lopez de Prado).
             `budgets` {asset: risk share} turns "erc" into risk budgeting.
             Covariance from `lookback` days (vols optionally from a shorter
             `vol_lookback`), optional shrinkage to the diagonal, per-asset cap.
             Optional portfolio vol target (`target`): scale <= 1 puts the rest
             in `cash`; scale > 1 uses a `lever` map {asset: [etf, k]}.
  cppi       Constant-proportion portfolio insurance / drawdown control:
             e = m * (V - floor * peak) / V with a ratcheting (or periodically
             reset) peak, clipped to [0, cap].
  ddtier     Exposure set by the risky asset's drawdown from its rolling high
             (tiers), e.g. de-risk in deep drawdowns or lever into them.
  volmom     Vol-scaled momentum: "ts" = long-only time-series momentum, each
             asset with positive trailing return gets (asset_target / vol) / N;
             "xs" = top-N by momentum, inverse-vol weighted; both with an
             optional portfolio vol target and cash proxy.
  taxvt      (kind "risk_alloc.taxvt") tax-aware execution of a voltarget
             exposure: equity spread over different-index funds, de-risking
             sells the lots with the least tax per dollar, see TaxVT.
  overlay    Vol-target overlay on ANY other registered signal (e.g. the
             incumbent momentum rotation): scale its weights so the portfolio's
             forecast vol is `target` (cap <= 1 -> rest in cash proxy; cap > 1
             -> `lever` map).

No look-ahead: realized vols use closes up to and including today (orders fill
at today's close); ^VIX / ^VIX3M are read with a one-day lag via blocks.asof.
"""
from __future__ import annotations

import json
import math
from collections import OrderedDict

import numpy as np

from ..blocks import Signal, asof, period_key
from ..registry import SIGNALS, register_signal

SQ252 = math.sqrt(252.0)


# ==========================================================================
# helpers
# ==========================================================================
_PRE: dict = {}          # per-process cache of full-series derived arrays


def _close_arr(t: str) -> np.ndarray:
    k = ("close", t)
    a = _PRE.get(k)
    if a is None:
        from .. import data
        a = _PRE[k] = data.frame(t)["Close"].to_numpy(dtype=float)
    return a


def _vol_arr(t: str, est: str, window: int, halflife: float | None = None) -> np.ndarray:
    """Annualised vol forecast at every bar of `t` (index = bar position),
    computed from log returns up to and including that bar. NaN when short."""
    k = ("vol", t, est, int(window), halflife)
    a = _PRE.get(k)
    if a is not None:
        return a
    import pandas as pd
    c = _close_arr(t)
    r = np.r_[np.nan, np.diff(np.log(c))]          # r[p] = return into bar p
    s = pd.Series(r)
    if est == "simple":
        v = s.rolling(int(window), min_periods=int(window)).std(ddof=0).to_numpy()
    elif est == "ewma":
        lam = 0.5 ** (1.0 / float(halflife))
        r2 = s ** 2
        v = np.sqrt(r2.ewm(alpha=1.0 - lam, adjust=False, ignore_na=True).mean()).to_numpy().copy()
        # need some history before trusting it
        v[: max(int(window), 20) + 1] = np.nan
    elif est == "semi":                            # downside semi-deviation
        neg = np.minimum(s, 0.0)
        v = np.sqrt((neg ** 2).rolling(int(window), min_periods=int(window)).mean() * 2.0).to_numpy()
    else:
        raise ValueError(est)
    a = _PRE[k] = v * SQ252
    return a


def _bar(ctx, t: str) -> int:
    """Index of the latest bar of `t` on or before today (-1 if none)."""
    m = ctx._engine.market
    return m.rows_upto(t, ctx._engine._dv) - 1


def _sma_ok(ctx, t: str, n: int) -> bool | None:
    """True if today's close is above the n-day SMA (None if short)."""
    p = _bar(ctx, t)
    if p + 1 < n:
        return None
    c = _close_arr(t)
    return bool(c[p] > c[p - n + 1:p + 1].mean())


def _first_tradable(ctx, chain) -> str | None:
    if not chain:
        return None
    if isinstance(chain, str):
        chain = [chain]
    for t in chain:
        if ctx.price(t) is not None:
            return t
    return None


def _chain_list(chain) -> list:
    if not chain:
        return []
    return [chain] if isinstance(chain, str) else list(chain)


_MEMO: "OrderedDict[str, dict]" = OrderedDict()


def _memo(obj) -> dict:
    """Per-config, per-date memo (one config's starts share the same market and
    stateless raw signal, so starts 2..n reuse start 1's computations)."""
    key = obj._memo_key
    d = _MEMO.get(key)
    if d is None:
        d = _MEMO[key] = {}
        while len(_MEMO) > 6:
            _MEMO.popitem(last=False)
    else:
        _MEMO.move_to_end(key)
    return d


def _pkey(name: str, params: dict) -> str:
    return name + json.dumps(params, sort_keys=True, default=str)


def _aligned(ctx, tickers, n):
    """(n+1) x k forward-filled close matrix ending today, from the market's
    dense mark matrix (NaN before a ticker's first bar)."""
    m = ctx._engine.market
    i = ctx._engine._i
    cols = [m.col(t) for t in tickers]
    lo = i - n
    if lo < 0 or any(c is None for c in cols):
        return None
    return m.mark_values[lo:i + 1][:, cols]


# ---- exposure -> weights --------------------------------------------------
def map_exposure(ctx, e: float, risk: str, lever: str | None, k: float, mode: str,
                 cash_chain) -> dict:
    """Target weights for exposure `e` to `risk` (1.0 = 100%)."""
    w: dict = {}
    e = max(0.0, float(e))
    lev_ok = bool(lever) and ctx.price(lever) is not None
    if e <= 1.0 + 1e-12 or not lev_ok:
        e1 = min(e, 1.0)
        if e1 > 0:
            w[risk] = e1
        rest = 1.0 - e1
    elif mode == "pure":
        x = min(e / k, 1.0)
        w[lever] = x
        rest = 1.0 - x
    else:                                   # "mix": 1x + kx, fully invested
        x = min((e - 1.0) / (k - 1.0), 1.0)
        w[lever] = x
        if 1.0 - x > 1e-12:
            w[risk] = 1.0 - x
        rest = 0.0
    cash = _first_tradable(ctx, cash_chain)
    if cash and rest > 1e-9:
        w[cash] = w.get(cash, 0.0) + rest
    return w


def actual_exposure(ctx, risk_k: dict) -> tuple[float, float]:
    """(exposure, cash fraction) of the current portfolio, where risk_k maps
    ticker -> exposure multiple (e.g. SPY 1, SSO 2)."""
    pv = ctx.portfolio_value
    if pv <= 0:
        return 0.0, 0.0
    e = 0.0
    for t, sh in ctx.positions.items():
        kk = risk_k.get(t)
        if kk:
            px = ctx.price(t)
            if px is None:
                continue
            e += kk * sh * px
    return e / pv, ctx.cash / pv


class _BandMixin:
    """No-trade band on exposure (shared by voltarget / cppi / ddtier)."""

    band = 0.0
    force_reb = False

    def _band_decide(self, ctx, rebalance_day, w, e_target, risk_k, cash_t):
        if self.band <= 0:
            return w if rebalance_day else None
        pos = ctx.positions
        if not pos:
            return w
        if rebalance_day and self.force_reb:
            return w
        e_act, cash_frac = actual_exposure(ctx, risk_k)
        if abs(e_target - e_act) > self.band:
            return w
        # housekeeping: negative cash after a tax payment (would be a free
        # loan), idle cash, or the cash proxy changed (e.g. VFISX -> SHY)
        if cash_frac < -0.005 or (cash_t and cash_frac > 0.03):
            return w
        if cash_t and cash_t not in pos and w.get(cash_t, 0.0) > 0.03:
            return w
        for t in pos:
            if t not in w and t not in risk_k:
                return w
        return None


# ==========================================================================
# voltarget
# ==========================================================================
class VolTarget(_BandMixin, Signal):
    def __init__(self, risk="SPY", vol_ticker=None, est="simple", window=21, window2=126,
                 halflife=20, target=0.15, power=1.0, cap=1.0, floor=0.0, step=0.0,
                 lever=None, lever_k=2.0, lever_mode="mix", cash=("SHY", "VFISX"),
                 band=0.0, daily=False, force_reb=False, trend_n=None, trend_cap=0.0,
                 trend_ticker=None, ts_thresh=None, ts_cap=0.5, vix_scale=1.0,
                 fallback=1.0, const_e=None):
        self.risk = risk
        self.vt = vol_ticker or risk
        self.est, self.window, self.window2, self.halflife = est, int(window), int(window2), halflife
        self.target, self.power = float(target), float(power)
        self.cap, self.floor, self.step = float(cap), float(floor), float(step)
        self.lever, self.k, self.mode = lever, float(lever_k), lever_mode
        self.cash = _chain_list(cash)
        self.band, self.daily, self.force_reb = float(band), bool(daily), bool(force_reb)
        self.trend_n, self.trend_cap = trend_n, float(trend_cap)
        self.trend_ticker = trend_ticker or risk
        self.ts_thresh, self.ts_cap = ts_thresh, float(ts_cap)
        self.vix_scale = float(vix_scale)
        self.fallback = float(fallback)
        self.const_e = None if const_e is None else float(const_e)
        self.risk_k = {risk: 1.0}
        if lever:
            self.risk_k[lever] = self.k

    def forecast_vol(self, ctx) -> float | None:
        est = self.est
        if est in ("simple", "ewma", "semi"):
            p = _bar(ctx, self.vt)
            if p < 0:
                return None
            v = _vol_arr(self.vt, est, self.window, self.halflife)[p]
            return None if not np.isfinite(v) or v <= 0 else float(v)
        if est == "max":
            p = _bar(ctx, self.vt)
            if p < 0:
                return None
            a = _vol_arr(self.vt, "simple", self.window)[p]
            b = _vol_arr(self.vt, "simple", self.window2)[p]
            if not (np.isfinite(a) and np.isfinite(b)):
                return None
            return float(max(a, b))
        if est in ("vix", "blend"):
            vx = asof(ctx, "^VIX", lag_days=1)
            vx = None if vx is None or not np.isfinite(vx) else vx / 100.0 * self.vix_scale
            if est == "vix":
                return vx
            p = _bar(ctx, self.vt)
            rv = _vol_arr(self.vt, "simple", self.window)[p] if p >= 0 else np.nan
            if vx is None or not np.isfinite(rv):
                return None
            return 0.5 * (vx + float(rv))
        raise ValueError(est)

    def exposure(self, ctx) -> float:
        if self.const_e is not None:          # control: constant exposure
            return min(max(self.const_e, self.floor), self.cap)
        v = self.forecast_vol(ctx)
        if v is None:
            e = self.fallback
        else:
            e = (self.target / v) ** self.power
        e = min(max(e, self.floor), self.cap)
        if self.trend_n:
            up = _sma_ok(ctx, self.trend_ticker, int(self.trend_n))
            if up is False:
                e = min(e, self.trend_cap)
        if self.ts_thresh is not None:
            a = asof(ctx, "^VIX", lag_days=1)
            b = asof(ctx, "^VIX3M", lag_days=1)
            if a is not None and b is not None and b > 0 and a / b > self.ts_thresh:
                e = min(e, self.ts_cap)
        if self.step > 0:
            e = round(e / self.step) * self.step
            e = min(max(e, self.floor), self.cap)
        return e

    def weights(self, ctx, rebalance_day):
        e = self.exposure(ctx)
        w = map_exposure(ctx, e, self.risk, self.lever, self.k, self.mode, self.cash)
        cash_t = _first_tradable(ctx, self.cash)
        return self._band_decide(ctx, rebalance_day, w, e, self.risk_k, cash_t)


def _vt_tickers(p):
    risk = p.get("risk", "SPY")
    out = [risk]
    if p.get("vol_ticker"):
        out.append(p["vol_ticker"])
    if p.get("trend_ticker"):
        out.append(p["trend_ticker"])
    if p.get("lever"):
        out.append(p["lever"])
    out += _chain_list(p.get("cash", ("SHY", "VFISX")))
    return list(dict.fromkeys(out))


register_signal("risk_alloc.voltarget", lambda p: VolTarget(**p), _vt_tickers)


# ==========================================================================
# multi-asset risk-based weights
# ==========================================================================
def _proj_simplex(v):
    n = len(v)
    u = np.sort(v)[::-1]
    css = np.cumsum(u)
    rho = np.nonzero(u * np.arange(1, n + 1) > (css - 1))[0][-1]
    theta = (css[rho] - 1) / (rho + 1.0)
    return np.maximum(v - theta, 0.0)


def minvar_simplex(S, iters=3000, tol=1e-12):
    """Long-only, fully-invested minimum variance (active set + PG fallback)."""
    n = len(S)
    if n == 1:
        return np.ones(1)
    active = np.ones(n, bool)
    for _ in range(4 * n + 10):
        idx = np.nonzero(active)[0]
        Sa = S[np.ix_(idx, idx)]
        try:
            x = np.linalg.solve(Sa, np.ones(len(idx)))
        except np.linalg.LinAlgError:
            break
        if x.sum() <= 0:
            break
        w = np.zeros(n)
        w[idx] = x / x.sum()
        if (w[idx] < -1e-12).any():
            j = idx[np.argmin(w[idx])]
            active[j] = False
            continue
        g = S @ w
        lam = w @ g
        viol = (~active) & (g < lam - 1e-12 * max(1.0, abs(lam)))
        if viol.any():
            cand = np.nonzero(viol)[0]
            active[cand[np.argmin(g[cand])]] = True
            continue
        return np.maximum(w, 0.0) / np.maximum(w, 0.0).sum()
    # projected gradient (FISTA) fallback
    L = 2.0 * float(np.linalg.eigvalsh(S).max())
    w = np.ones(n) / n
    y, t = w.copy(), 1.0
    for _ in range(iters):
        w_new = _proj_simplex(y - (2.0 * S @ y) / L)
        t_new = 0.5 * (1 + math.sqrt(1 + 4 * t * t))
        y = w_new + ((t - 1) / t_new) * (w_new - w)
        if np.abs(w_new - w).max() < tol:
            w = w_new
            break
        w, t = w_new, t_new
    return w / w.sum()


def erc_weights(S, iters=200, tol=1e-10, b=None):
    """Equal (or budgeted, `b`) risk contribution via cyclical coordinate
    descent (Griveau-Billion, Richard, Roncalli 2013)."""
    n = len(S)
    b = np.ones(n) / n if b is None else np.asarray(b, float) / float(np.sum(b))
    x = 1.0 / np.sqrt(np.diag(S))
    x /= x.sum()
    for _ in range(iters):
        x_old = x.copy()
        for i in range(n):
            a = S[i, i]
            c = S[i] @ x - a * x[i]
            x[i] = (-c + math.sqrt(c * c + 4.0 * a * b[i])) / (2.0 * a)
        if np.abs(x - x_old).max() < tol * x.max():
            break
    return x / x.sum()


def hrp_weights(S):
    from scipy.cluster.hierarchy import leaves_list, linkage
    from scipy.spatial.distance import squareform
    n = len(S)
    if n == 1:
        return np.ones(1)
    sd = np.sqrt(np.diag(S))
    C = S / np.outer(sd, sd)
    D = np.sqrt(np.clip(0.5 * (1.0 - C), 0.0, None))
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="single")
    order = list(leaves_list(Z))
    w = np.ones(n)

    def cvar(idx):
        s = S[np.ix_(idx, idx)]
        iv = 1.0 / np.diag(s)
        iv /= iv.sum()
        return float(iv @ s @ iv)

    clusters = [order]
    while clusters:
        new = []
        for c in clusters:
            if len(c) <= 1:
                continue
            h = len(c) // 2
            a, b = c[:h], c[h:]
            va, vb = cvar(a), cvar(b)
            alpha = 1.0 - va / (va + vb)
            w[a] *= alpha
            w[b] *= 1.0 - alpha
            new += [a, b]
        clusters = new
    return w / w.sum()


def maxdiv_weights(S):
    sd = np.sqrt(np.diag(S))
    C = S / np.outer(sd, sd)
    y = minvar_simplex(C)
    w = y / sd
    return w / w.sum()


def cap_weights(w, max_w):
    """Cap each weight at max_w, redistributing the excess pro rata."""
    if max_w >= 1.0 or len(w) * max_w < 1.0 - 1e-9:
        return w
    w = w.copy()
    for _ in range(50):
        over = w > max_w + 1e-12
        if not over.any():
            break
        excess = (w[over] - max_w).sum()
        w[over] = max_w
        free = ~over & (w < max_w - 1e-12)
        if not free.any():
            break
        w[free] += excess * w[free] / w[free].sum()
    return w


def risk_weights(method, S, budgets=None):
    n = len(S)
    vol = np.sqrt(np.diag(S))
    if method == "equal":
        w = np.ones(n)
    elif method == "invvol":
        w = 1.0 / vol
    elif method == "invvar":
        w = 1.0 / vol ** 2
    elif method == "erc":
        w = erc_weights(S, b=budgets)
    elif method == "minvar":
        w = minvar_simplex(S)
    elif method == "maxdiv":
        w = maxdiv_weights(S)
    elif method == "hrp":
        w = hrp_weights(S)
    else:
        raise ValueError(method)
    w = np.maximum(w, 0.0)
    return w / w.sum()


def apply_lever(ctx, x: dict, lever: dict | None) -> tuple[dict, float]:
    """Implement exposures x (sum may exceed 1) with at most 100% capital:
    each asset with a lever entry [etf, k] moves the same fraction f of its
    exposure into the k-x ETF. Returns (weights, achieved scale factor)."""
    tot = sum(x.values())
    if tot <= 1.0 + 1e-12:
        return dict(x), 1.0
    lev = {}
    for t, v in x.items():
        spec = (lever or {}).get(t)
        if spec and ctx.price(spec[0]) is not None:
            lev[t] = (spec[0], float(spec[1]))
    # capital needed with full use of levered ETFs
    full = sum(v / lev[t][1] if t in lev else v for t, v in x.items())
    scale = 1.0
    if full > 1.0:                     # infeasible: shrink exposures
        scale = 1.0 / full
        x = {t: v * scale for t, v in x.items()}
        tot = sum(x.values())
    save = sum(v * (1.0 - 1.0 / lev[t][1]) for t, v in x.items() if t in lev)
    f = 0.0 if save <= 0 else min(1.0, max(0.0, (tot - 1.0) / save))
    w = {}
    for t, v in x.items():
        if t in lev:
            etf, k = lev[t]
            if v * (1 - f) > 1e-12:
                w[t] = w.get(t, 0.0) + v * (1.0 - f)
            if v * f > 1e-12:
                w[etf] = w.get(etf, 0.0) + v * f / k
        else:
            w[t] = w.get(t, 0.0) + v
    s = sum(w.values())
    if s > 1.0:
        w = {t: v / s for t, v in w.items()}
    return w, scale


class RiskPar(Signal):
    def __init__(self, menu, method="invvol", lookback=63, vol_lookback=None, shrink=0.0,
                 max_w=1.0, target=None, cap=1.0, floor=0.0, lever=None, cash=("SHY", "VFISX"),
                 est_window=None, min_assets=1, port_lookback=None, fixed=None, budgets=None):
        self.menu = list(menu)
        self.method = method
        self.lb = int(lookback)
        self.vlb = int(vol_lookback) if vol_lookback else None
        self.shrink = float(shrink)
        self.max_w = float(max_w)
        self.target = target
        self.cap, self.floor = float(cap), float(floor)
        self.lever = lever
        self.cash = _chain_list(cash)
        self.min_assets = int(min_assets)
        self.plb = int(port_lookback) if port_lookback else None
        self.fixed = fixed            # optional {ticker: weight} instead of a method
        self.budgets = budgets        # optional {ticker: risk budget} for "erc"
        self._memo_key = _pkey("riskpar", dict(menu=self.menu, method=method, lb=self.lb,
                                               vlb=self.vlb, shrink=self.shrink, max_w=self.max_w,
                                               target=target, cap=cap, floor=floor, lever=lever,
                                               plb=self.plb, fixed=fixed, budgets=budgets))

    def _cov(self, ctx, live, n):
        X = _aligned(ctx, live, n)
        if X is None:
            return None, None
        ok = ~np.isnan(X).any(axis=0)
        return X, ok

    def raw(self, ctx):
        """Risk exposures {ticker: x} (sum = scale, may be > 1) - stateless."""
        memo = _memo(self)
        d = ctx.date
        if d in memo:
            return memo[d]
        live = [t for t in self.menu if ctx.price(t) is not None]
        out = None
        if live:
            n = max(self.lb, self.vlb or 0, self.plb or 0)
            X = _aligned(ctx, live, n)
            if X is not None:
                ok = ~np.isnan(X).any(axis=0)
                names = [t for t, o in zip(live, ok) if o]
                if len(names) >= self.min_assets and names:
                    Xn = X[:, ok]
                    R = np.diff(np.log(Xn), axis=0)
                    Rl = R[-self.lb:]
                    S = np.cov(Rl, rowvar=False, ddof=0).reshape(len(names), len(names)) * 252.0
                    if self.vlb:
                        Rv = R[-self.vlb:]
                        sv = Rv.std(axis=0) * SQ252
                        sl = np.sqrt(np.diag(S))
                        C = S / np.outer(sl, sl)
                        S = C * np.outer(sv, sv)
                    if self.shrink > 0:
                        S = (1 - self.shrink) * S + self.shrink * np.diag(np.diag(S))
                    dg = np.diag(S).copy()
                    if (dg <= 0).any():
                        # an asset with a flat price window (stale fund print):
                        # drop it this time
                        keep = dg > 0
                        names = [t for t, k in zip(names, keep) if k]
                        S = S[np.ix_(keep, keep)]
                        R = R[:, keep]
                    if names:
                        if self.fixed:
                            w = np.array([self.fixed.get(t, 0.0) for t in names], float)
                            w = w / w.sum() if w.sum() > 0 else np.ones(len(names)) / len(names)
                        else:
                            bud = None
                            if self.budgets:
                                bud = [float(self.budgets.get(t, 0.0)) or 1e-6 for t in names]
                            w = risk_weights(self.method, S, bud)
                        w = cap_weights(w, self.max_w)
                        scale = 1.0
                        if self.target:
                            Sp = S
                            if self.plb:
                                Sp = np.cov(R[-self.plb:], rowvar=False, ddof=0).reshape(
                                    len(names), len(names)) * 252.0
                            pv = math.sqrt(max(float(w @ Sp @ w), 1e-12))
                            scale = min(max(float(self.target) / pv, self.floor), self.cap)
                        out = {t: float(x) * scale for t, x in zip(names, w) if x > 1e-9}
        memo[d] = out
        return out

    def weights(self, ctx, rebalance_day):
        x = self.raw(ctx)
        if not x:
            cash = _first_tradable(ctx, self.cash)
            return {cash: 1.0} if cash else {}
        w, _ = apply_lever(ctx, x, self.lever)
        rest = 1.0 - sum(w.values())
        cash = _first_tradable(ctx, self.cash)
        if cash and rest > 1e-9:
            w[cash] = w.get(cash, 0.0) + rest
        return w


def _rp_tickers(p):
    out = list(p["menu"])
    for spec in (p.get("lever") or {}).values():
        out.append(spec[0])
    out += _chain_list(p.get("cash", ("SHY", "VFISX")))
    return list(dict.fromkeys(out))


register_signal("risk_alloc.riskpar", lambda p: RiskPar(**p), _rp_tickers)


# ==========================================================================
# CPPI / drawdown control
# ==========================================================================
class CPPI(_BandMixin, Signal):
    daily = True

    def __init__(self, risk="SPY", m=3.0, floor=0.8, cap=1.0, lever=None, lever_k=2.0,
                 lever_mode="mix", cash=("SHY", "VFISX"), band=0.05, reset=None,
                 check="D", min_e=0.0):
        self.risk, self.m, self.fl, self.cap = risk, float(m), float(floor), float(cap)
        self.lever, self.k, self.mode = lever, float(lever_k), lever_mode
        self.cash = _chain_list(cash)
        self.band = float(band)
        self.reset = reset
        self.check = check
        self.min_e = float(min_e)
        self.risk_k = {risk: 1.0}
        if lever:
            self.risk_k[lever] = self.k

    def initialize(self, ctx):
        self.peak = None
        self._rk = None
        self._ck = None

    def weights(self, ctx, rebalance_day):
        pv = ctx.portfolio_value
        if self.check != "D":
            ck = period_key(ctx.date, self.check)
            if ck == self._ck and not rebalance_day and self.peak is not None:
                self.peak = max(self.peak, pv)
                return None
            self._ck = ck
        if self.reset:
            rk = period_key(ctx.date, self.reset)
            if rk != self._rk:
                self._rk = rk
                self.peak = pv
        self.peak = pv if self.peak is None else max(self.peak, pv)
        F = self.fl * self.peak
        e = self.m * max(pv - F, 0.0) / pv if pv > 0 else 0.0
        e = min(max(e, self.min_e), self.cap)
        w = map_exposure(ctx, e, self.risk, self.lever, self.k, self.mode, self.cash)
        cash_t = _first_tradable(ctx, self.cash)
        if not ctx.positions:
            return w
        return self._band_decide(ctx, rebalance_day, w, e, self.risk_k, cash_t)


def _cppi_tickers(p):
    out = [p.get("risk", "SPY")]
    if p.get("lever"):
        out.append(p["lever"])
    out += _chain_list(p.get("cash", ("SHY", "VFISX")))
    return list(dict.fromkeys(out))


register_signal("risk_alloc.cppi", lambda p: CPPI(**p), _cppi_tickers)


class DDTier(_BandMixin, Signal):
    """Exposure from the drawdown of `risk` vs its `hi_window`-day high:
    tiers = [[dd_threshold, exposure], ...] ascending thresholds; the first
    threshold the drawdown is below sets the exposure."""

    def __init__(self, risk="SPY", tiers=((0.1, 1.0), (0.2, 0.5), (1.0, 0.0)), hi_window=252,
                 lever=None, lever_k=2.0, lever_mode="mix", cash=("SHY", "VFISX"), band=0.0,
                 daily=False, force_reb=False):
        self.risk = risk
        self.tiers = [(float(a), float(b)) for a, b in tiers]
        self.hw = int(hi_window)
        self.lever, self.k, self.mode = lever, float(lever_k), lever_mode
        self.cash = _chain_list(cash)
        self.band, self.daily, self.force_reb = float(band), bool(daily), bool(force_reb)
        self.risk_k = {risk: 1.0}
        if lever:
            self.risk_k[lever] = self.k

    def weights(self, ctx, rebalance_day):
        p = _bar(ctx, self.risk)
        c = _close_arr(self.risk)
        if p < 1:
            e = self.tiers[0][1]
        else:
            hi = c[max(0, p - self.hw + 1):p + 1].max()
            dd = 1.0 - c[p] / hi
            e = self.tiers[-1][1]
            for th, ex in self.tiers:
                if dd < th:
                    e = ex
                    break
        w = map_exposure(ctx, e, self.risk, self.lever, self.k, self.mode, self.cash)
        cash_t = _first_tradable(ctx, self.cash)
        return self._band_decide(ctx, rebalance_day, w, e, self.risk_k, cash_t)


register_signal("risk_alloc.ddtier", lambda p: DDTier(**p), _cppi_tickers)


# ==========================================================================
# vol-scaled momentum
# ==========================================================================
class VolMom(Signal):
    def __init__(self, menu, mode="ts", lookback=252, skip=21, top_n=3, vol_window=63,
                 asset_target=0.10, max_w=1.0, port_target=None, port_window=63, cap=1.0,
                 abs_filter=True, cash=("SHY", "VFISX"), weighting="invvol"):
        self.menu = list(menu)
        self.mode = mode
        self.lbs = list(lookback) if isinstance(lookback, (list, tuple)) else [int(lookback)]
        self.skip = int(skip)
        self.top_n = int(top_n)
        self.vw = int(vol_window)
        self.at = float(asset_target)
        self.max_w = float(max_w)
        self.pt = port_target
        self.pw = int(port_window)
        self.cap = float(cap)
        self.abs_filter = bool(abs_filter)
        self.cash = _chain_list(cash)
        self.weighting = weighting
        self._memo_key = _pkey("volmom", dict(menu=self.menu, mode=mode, lbs=self.lbs,
                                              skip=self.skip, top=self.top_n, vw=self.vw,
                                              at=self.at, mw=self.max_w, pt=self.pt, pw=self.pw,
                                              cap=self.cap, af=self.abs_filter,
                                              wt=weighting))

    def raw(self, ctx):
        memo = _memo(self)
        d = ctx.date
        if d in memo:
            return memo[d]
        live = [t for t in self.menu if ctx.price(t) is not None]
        n = max(max(self.lbs) + self.skip, self.vw, self.pw) + 1
        X = _aligned(ctx, live, n) if live else None
        out = {}
        if X is not None:
            ok = ~np.isnan(X).any(axis=0)
            names = [t for t, o in zip(live, ok) if o]
            Xn = X[:, ok]
            if names:
                last = Xn[-1 - self.skip]
                moms = np.mean([last / Xn[-1 - self.skip - lb] - 1.0 for lb in self.lbs], axis=0)
                R = np.diff(np.log(Xn), axis=0)
                vol = R[-self.vw:].std(axis=0) * SQ252
                vol = np.where(vol > 1e-6, vol, np.nan)
                w = np.zeros(len(names))
                if self.mode == "ts":
                    for j in range(len(names)):
                        if moms[j] > 0 and np.isfinite(vol[j]):
                            w[j] = min(self.at / vol[j], self.max_w) / len(names)
                else:   # cross-sectional
                    order = np.argsort(-moms)
                    picks = [j for j in order[: self.top_n]
                             if (moms[j] > 0 or not self.abs_filter) and np.isfinite(vol[j])]
                    for j in picks:
                        w[j] = (1.0 / vol[j]) if self.weighting == "invvol" else 1.0
                    if w.sum() > 0:
                        w = w / w.sum() * (len(picks) / self.top_n)
                if self.pt and w.sum() > 0:
                    Rp = R[-self.pw:]
                    S = np.cov(Rp, rowvar=False, ddof=0).reshape(len(names), len(names)) * 252.0
                    pvol = math.sqrt(max(float(w @ S @ w), 1e-12))
                    w = w * (float(self.pt) / pvol)
                s = w.sum()
                if s > self.cap:
                    w = w * (self.cap / s)
                out = {t: float(x) for t, x in zip(names, w) if x > 1e-9}
        memo[d] = out
        return out

    def weights(self, ctx, rebalance_day):
        w = dict(self.raw(ctx))
        rest = 1.0 - sum(w.values())
        cash = _first_tradable(ctx, self.cash)
        if cash and rest > 1e-9:
            w[cash] = w.get(cash, 0.0) + rest
        return w


def _vm_tickers(p):
    return list(dict.fromkeys(list(p["menu"]) + _chain_list(p.get("cash", ("SHY", "VFISX")))))


register_signal("risk_alloc.volmom", lambda p: VolMom(**p), _vm_tickers)


# ==========================================================================
# overlay: vol-target any registered signal
# ==========================================================================
class Overlay(Signal):
    def __init__(self, inner, inner_params, target=0.15, lookback=63, cap=1.0, floor=0.0,
                 lever=None, cash=("SHY", "VFISX"), step=0.0):
        factory = SIGNALS[inner][0]
        self.inner = factory(inner_params)
        self.daily = bool(getattr(self.inner, "daily", False))
        self.target, self.lb = float(target), int(lookback)
        self.cap, self.floor = float(cap), float(floor)
        self.lever = lever
        self.cash = _chain_list(cash)
        self.step = float(step)
        self._w = None

    def initialize(self, ctx):
        self.inner.initialize(ctx)
        self._w = None

    def weights(self, ctx, rebalance_day):
        w = self.inner.weights(ctx, rebalance_day)
        if w is None and not rebalance_day:
            return None
        if w is not None:
            self._w = dict(w)
        base = self._w or {}
        names = [t for t, x in base.items() if x > 0]
        scale = 1.0
        if names:
            X = _aligned(ctx, names, self.lb)
            if X is not None and not np.isnan(X).any():
                R = np.diff(np.log(X), axis=0)
                S = np.cov(R, rowvar=False, ddof=0).reshape(len(names), len(names)) * 252.0
                ww = np.array([base[t] for t in names])
                pvol = math.sqrt(max(float(ww @ S @ ww), 1e-12))
                scale = min(max(self.target / pvol, self.floor), self.cap)
                if self.step > 0:
                    scale = min(max(round(scale / self.step) * self.step, self.floor), self.cap)
        x = {t: base[t] * scale for t in names}
        out, _ = apply_lever(ctx, x, self.lever)
        rest = 1.0 - sum(out.values())
        cash = _first_tradable(ctx, self.cash)
        if cash and rest > 1e-9:
            out[cash] = out.get(cash, 0.0) + rest
        return out


def _ov_tickers(p):
    inner = list(SIGNALS[p["inner"]][1](p["inner_params"]))
    for spec in (p.get("lever") or {}).values():
        inner.append(spec[0])
    return list(dict.fromkeys(inner + _chain_list(p.get("cash", ("SHY", "VFISX")))))


register_signal("risk_alloc.overlay", lambda p: Overlay(**p), _ov_tickers)


# ==========================================================================
# taxvt: tax-aware execution of a vol-target exposure (custom kind)
# ==========================================================================
from backtester import Strategy as _Strategy          # noqa: E402
from ..registry import register_kind                   # noqa: E402


class TaxVT(_Strategy):
    """Vol targeting implemented for a taxable account.

    The exposure target e comes from a VolTarget signal (same parameters). The
    1x equity exposure is spread over `vehicles` -- funds tracking DIFFERENT
    indexes (e.g. SPY = S&P 500, IWB = Russell 1000, VTI = CRSP US Total
    Market), so selling one at a loss while holding another is a legitimate
    harvest (PROTOCOL 5.4). The engine relieves lots FIFO within a ticker, so
    a single-ticker vol-target de-risks by selling its OLDEST (lowest-basis)
    lots. Here:
      * de-risking sells, lot by lot, whichever vehicle's next FIFO lot costs
        the least tax per dollar (losses first, then long-term gains, then
        short-term gains; cost = gain x applicable rate);
      * re-risking buys go into the vehicle whose oldest open lot is the
        newest (an empty one first) and that is not wash-blocked (sold at a
        loss within `wash_days`), so lot vintages stay separated and new,
        high-basis lots can be sold first later;
      * optional `gain_budget` caps net realized gains per calendar year as a
        fraction of portfolio value (losses always allowed); `st_gains=False`
        never realizes a short-term gain;
      * optional `harvest`: when a vehicle's position is down more than
        `harvest` (fraction of its basis) it is swapped into another
        non-blocked vehicle (exposure unchanged).
    Levered exposure (e > 1) uses `lever` vehicles [[ticker, k], ...] in "mix"
    mode (1x vehicles + k-x fund, fully invested); the rest (e < 1) sits in the
    first tradable `cash` proxy.
    """

    def __init__(self, signal: dict, vehicles=("SPY",), lever=None, cash=("SHY", "VFISX"),
                 band=0.1, check="D", gain_budget=None, wash_days=31, harvest=None,
                 harvest_freq="M", st_gains=True):
        sp = dict(signal)
        sp.setdefault("cash", list(_chain_list(cash)))
        sp.pop("band", None)
        sp.pop("daily", None)
        self.sig = VolTarget(**sp)
        self.veh = list(vehicles)
        self.lev = [(t, float(k)) for t, k in (lever or [])]
        self.cash = _chain_list(cash)
        self.band = float(band)
        self.check = check
        self.gain_budget = gain_budget
        self.wash_days = int(wash_days)
        self.harvest = harvest
        self.harvest_freq = harvest_freq
        self.st_gains = bool(st_gains)

    def initialize(self, ctx):
        self.sig.initialize(ctx)
        self._ck = None
        self._hk = None
        self._loss_sale = {}

    # ---- helpers ----------------------------------------------------------
    def _rates(self, ctx):
        pol = ctx._engine.tax_policy
        if pol is None:
            return None
        return pol.short_term_rate, pol.long_term_rate

    def _blocked(self, ctx, t):
        d = self._loss_sale.get(t)
        return d is not None and (ctx.date - d).days <= self.wash_days

    def _val(self, ctx, t):
        sh = ctx.shares(t)
        if sh <= 0:
            return 0.0
        px = ctx.price(t)
        if px is None:
            m = ctx._engine.market
            px = m.mark_values[ctx._engine._i, m.col(t)]
        return sh * float(px)

    def _sell_amount(self, ctx, tickers, amount, rates, room):
        """Sell `amount` dollars across `tickers` lot by lot, cheapest tax first.
        Returns (dollars sold, remaining gain room)."""
        if amount <= 1e-6:
            return 0.0, room
        fronts = {}
        for t in tickers:
            if ctx.shares(t) <= 0 or ctx.price(t) is None:
                continue
            lots = [list(l) for l in ctx.lots(t)] if rates else [[ctx.date, ctx.shares(t), 0.0]]
            if not lots:
                lots = [[ctx.date, ctx.shares(t), 0.0]]
            fronts[t] = lots
        plan = {}
        left = amount
        while left > 1e-6 and fronts:
            best = None
            for t, lots in fronts.items():
                if not lots:
                    continue
                d, sh, cost = lots[0]
                px = ctx.price(t)
                net = px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)
                if rates:
                    lt = ctx.is_long_term(d)
                    rate = rates[1] if lt else rates[0]
                    c = (net - cost) / net * rate
                    if net - cost > 0 and room is not None and room <= 1e-9:
                        continue
                    if net - cost > 0 and not lt and not self.st_gains:
                        continue                    # never realize a short-term gain
                else:
                    c = 0.0
                if best is None or c < best[0]:
                    best = (c, t)
            if best is None:
                break
            t = best[1]
            d, sh, cost = fronts[t][0]
            px = ctx.price(t)
            net = px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)
            take_sh = min(sh, left / px)
            gain = (net - cost) * take_sh if rates else 0.0
            if rates and gain > 0 and room is not None and gain > room:
                take_sh = take_sh * max(room, 0.0) / gain
                gain = (net - cost) * take_sh
            if take_sh <= 1e-12:
                fronts[t].pop(0)
                continue
            plan[t] = plan.get(t, 0.0) + take_sh
            left -= take_sh * px
            if room is not None and rates:
                room -= gain
            fronts[t][0][1] -= take_sh
            if fronts[t][0][1] <= 1e-12:
                fronts[t].pop(0)
        sold = 0.0
        for t, sh in plan.items():
            if rates:
                # register loss sales for the wash guard (aggregate check)
                net = ctx.price(t) * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)
                rem, g = sh, 0.0
                for d, s0, cost in ctx.lots(t):
                    if rem <= 1e-12:
                        break
                    k = min(rem, s0)
                    g += (net - cost) * k
                    rem -= k
                if g < 0:
                    self._loss_sale[t] = ctx.date
            sold += sh * ctx.price(t)
            ctx.order(t, -sh)
        return sold, room

    def _pick_buy(self, ctx, tickers):
        best, best_key = None, None
        for t in tickers:
            if ctx.price(t) is None or self._blocked(ctx, t):
                continue
            lots = ctx.lots(t)
            if ctx.shares(t) <= 0:
                key = (2, 0)                       # empty vehicle: best
            elif lots:
                key = (1, lots[0][0].value)        # newest oldest-lot
            else:
                key = (0, 0)
            if best_key is None or key > best_key:
                best, best_key = t, key
        return best

    # ---- main -------------------------------------------------------------
    def on_day(self, ctx):
        if self.check != "D":
            ck = period_key(ctx.date, self.check)
            if ck == self._ck and ctx.cash > -0.005 * ctx.portfolio_value:
                self._maybe_harvest(ctx)
                return
            self._ck = ck
        pv = ctx.portfolio_value
        if pv <= 0:
            return
        e = self.sig.exposure(ctx)
        lev = [(t, k) for t, k in self.lev if ctx.price(t) is not None]
        lk = lev[0][1] if lev else 2.0
        lev_t = [t for t, k in lev if k == lk]       # usable lever vehicles (same k)
        if e > 1.0 and lev_t:
            wl = min((e - 1.0) / (lk - 1.0), 1.0)
            w1, wc = 1.0 - wl, 0.0
        else:
            e = min(e, 1.0)
            wl, w1, wc = 0.0, e, 1.0 - e
        v1 = sum(self._val(ctx, t) for t in self.veh)
        vl = {t: self._val(ctx, t) for t, _ in self.lev}
        kmap = dict(self.lev)
        e_act = (v1 + sum(kmap[t] * v for t, v in vl.items())) / pv
        cash_t = _first_tradable(ctx, self.cash)
        cash_frac = ctx.cash / pv
        others = [t for t in ctx.positions
                  if t not in self.veh and t not in vl and t != cash_t]
        stray = [t for t, v in vl.items() if v > 0 and t not in lev_t]
        need = (not ctx.positions or abs(e - e_act) > self.band or cash_frac < -0.005
                or cash_frac > 0.03 or others or stray)
        if not need:
            self._maybe_harvest(ctx)
            return
        rates = self._rates(ctx)
        room = None
        if self.gain_budget is not None and rates:
            st, ltg = ctx.realized_this_year()
            room = self.gain_budget * pv - (st + ltg)
        # ---- sells
        for t in others:                              # e.g. a superseded cash proxy
            ctx.order(t, -ctx.shares(t))
        for t in stray:                               # lever funds of another k
            _, room = self._sell_amount(ctx, [t], vl[t], rates, room)
        vl_use = sum(vl[t] for t in lev_t)
        if vl_use > wl * pv + 1e-6:
            _, room = self._sell_amount(ctx, lev_t, vl_use - wl * pv, rates, room)
        if v1 > w1 * pv + 1e-6:
            _, room = self._sell_amount(ctx, self.veh, v1 - w1 * pv, rates, room)
        vc = self._val(ctx, cash_t) if cash_t else 0.0
        if cash_t and vc > wc * pv + 1e-6:
            ctx.order(cash_t, -(vc - wc * pv) / ctx.price(cash_t))
        # ---- buys (scaled to the cash on hand)
        buys = []
        v1n = sum(self._val(ctx, t) for t in self.veh)
        if w1 * pv - v1n > 1e-6:
            b = self._pick_buy(ctx, self.veh)
            if b:
                buys.append((b, w1 * pv - v1n))
        if lev_t:
            vln = sum(self._val(ctx, t) for t in lev_t)
            if wl * pv - vln > 1e-6:
                b = self._pick_buy(ctx, lev_t)
                if b:
                    buys.append((b, wl * pv - vln))
        if cash_t:
            vcn = self._val(ctx, cash_t)
            if wc * pv - vcn > 1e-6:
                buys.append((cash_t, wc * pv - vcn))
        if buys:
            cm = (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)
            need_cash = sum(v * cm for _, v in buys)
            scale = min(1.0, max(ctx.cash, 0.0) / need_cash * 0.999999) if need_cash > 0 else 0.0
            for t, v in buys:
                if scale > 0:
                    ctx.order(t, v * scale / ctx.price(t))

    def _maybe_harvest(self, ctx):
        if not self.harvest or self._rates(ctx) is None:
            return
        hk = period_key(ctx.date, self.harvest_freq)
        if hk == self._hk:
            return
        self._hk = hk
        for t in list(self.veh) + [x for x, _ in self.lev]:
            sh = ctx.shares(t)
            px = ctx.price(t)
            if sh <= 0 or px is None:
                continue
            lots = ctx.lots(t)
            basis = sum(s * c for _, s, c in lots)
            net = px * (1 - ctx.slippage_pct) * (1 - ctx.commission_pct)
            if basis <= 0 or sh * net / basis - 1.0 > -self.harvest:
                continue
            kmap = dict(self.lev)
            if t in self.veh:
                cands = [x for x in self.veh if x != t]
            else:
                cands = [x for x, k in self.lev if x != t and k == kmap[t]]
            sub = self._pick_buy(ctx, cands)
            if sub is None:
                continue                     # no different-index substitute: keep
            val = sh * net
            ctx.order(t, -sh)
            self._loss_sale[t] = ctx.date
            ctx.order(sub, val / (ctx.price(sub) * (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)) * 0.999999)


def _taxvt_build(c):
    return TaxVT(signal=c["signal"], vehicles=c.get("vehicles", ["SPY"]), lever=c.get("lever"),
                 cash=c.get("cash", ["SHY", "VFISX"]), band=c.get("band", 0.1),
                 check=c.get("check", "D"), gain_budget=c.get("gain_budget"),
                 wash_days=c.get("wash_days", 31), harvest=c.get("harvest"),
                 harvest_freq=c.get("harvest_freq", "M"), st_gains=c.get("st_gains", True))


def _taxvt_tickers(c):
    out = list(c.get("vehicles", ["SPY"])) + [t for t, _ in (c.get("lever") or [])]
    out += _chain_list(c.get("cash", ["SHY", "VFISX"]))
    vt_t = c["signal"].get("vol_ticker") or c["signal"].get("risk")
    if vt_t:
        out.append(vt_t)
    return list(dict.fromkeys(out + ["SPY"]))


register_kind("risk_alloc.taxvt", _taxvt_build, _taxvt_tickers)
