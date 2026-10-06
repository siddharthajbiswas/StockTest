"""Round 2: moderate leverage + trend filter, tax-aware designs (family 'r2_lev2x').

Kind "r2_lev2x.rule" -- one rule that covers every structure of the pre-registered grid
(research/lab/scratch/r2_lev2x/PREREG.md):

    {"kind": "r2_lev2x.rule", "world": "ETF"|"LONG"|"SPLICE", "safe": "IEF"|"SHY"|"BIL",
     "filters": [[n, band], ...], "check": "D"|"W", "lag": 0|1,
     "core": c, "on": {role: w}, "off": {role: w}, "defer": days}

* K trend filters on the 1x asset's (total-return) close: filter j turns ON once
  close/SMA(n_j) - 1 > +band_j and OFF once < -band_j (hysteresis; the initial state on the start
  day is the sign of the margin). Filters are evaluated every close ("D") or on the first trading
  day of each ISO week ("W"); `lag` = 1 evaluates them on the previous close (trade one day late).
* Portfolio = core + sleeve. The core is `core` x the start value in the 1x asset, bought on the
  start day and never sold (unless the sleeve cannot pay a tax bill). The sleeve holds the ON mix
  in proportion k/K and the OFF mix in proportion 1 - k/K (k = filters ON). Roles: "one" (1x S&P),
  "two" (2x S&P), "three" (3x S&P), "safe" (Treasury / T-bill fund).
* Trades happen only (1) when k changes: the sleeve's on/off split is re-targeted to k/K (ON-mix
  sales pro rata by value, purchases in the mix's weights), and (2) when the January tax payment
  (deducted from cash by the engine) leaves cash negative: the sleeve is sold pro rata to cover it.
  There is no other rebalancing, so nothing else realizes gains.
* `defer` (days, 0 = off): tax-aware exit. A reduction of the ON part that would realize a net
  short-term gain is postponed while every short-term lot it would sell turns long-term within
  `defer` days (re-checked daily; executed as soon as that no longer holds or the lots are LT).

Worlds map roles to the research files built by scratch/r2_lev2x/build_data.py:
  ETF    (protocol "full")      one SPY,     two R2L_SSO,  three R2L_UPRO,  safe R2L_IEF/SHY/BIL
  LONG   (protocol "long_r")    one VFINXR,  two R2L_SSOL, three R2L_UPROL, safe R2L_IEFL/SHYL/BILL
  SPLICE (protocol "r2_splice") one R2L_SPX, two R2L_SSOX, three R2L_UPROX, safe R2L_IEFX/SHYX/BILX
A config may instead give explicit "roles": {"one": "SPY", "two": "SSO", "safe": "IEF"}.

Protocol "r2_splice": yearly starts 1930-01..2023-01, quarterly checkpoints to 2026-07,
benchmark R2L_SPX (^GSPC + dividends before 1980, VFINXR after).
"""
from __future__ import annotations

import numpy as np

from backtester import Strategy

from .. import core as _core
from ..blocks import period_key
from ..registry import register_kind

_core.PROTOCOLS.setdefault("r2_splice", _core._mk("r2_splice", "1930-01-01", "2023-01-01", "1930-04-01",
                                                  benchmark="R2L_SPX", step="YS"))

WORLDS = {
    "ETF": {"one": "SPY", "two": "R2L_SSO", "three": "R2L_UPRO",
            "safe": {"IEF": "R2L_IEF", "SHY": "R2L_SHY", "BIL": "R2L_BIL"}},
    "LONG": {"one": "VFINXR", "two": "R2L_SSOL", "three": "R2L_UPROL",
             "safe": {"IEF": "R2L_IEFL", "SHY": "R2L_SHYL", "BIL": "R2L_BILL"}},
    "SPLICE": {"one": "R2L_SPX", "two": "R2L_SSOX", "three": "R2L_UPROX",
               "safe": {"IEF": "R2L_IEFX", "SHY": "R2L_SHYX", "BIL": "R2L_BILX"}},
}
PROTOCOL_OF = {"ETF": "full", "LONG": "long_r", "SPLICE": "r2_splice"}


def roles_of(c: dict) -> dict:
    if c.get("roles"):
        return dict(c["roles"])
    w = WORLDS[c["world"]]
    return {"one": w["one"], "two": w["two"], "three": w["three"],
            "safe": w["safe"][c.get("safe", "IEF")]}


def _sma_margin(ctx, t: str, n: int, lag: int):
    """close/SMA(n) - 1 on the close `lag` bars ago, via a cached cumulative sum (O(1))."""
    m = ctx._engine.market
    cache = m.__dict__.setdefault("_r2_cs", {})
    ent = cache.get(t)
    if ent is None:
        s = m.series(t, "Close")
        arr = s.to_numpy(dtype=float)
        ent = cache[t] = (arr, np.r_[0.0, np.cumsum(arr)])
    arr, cs = ent
    pos = m.rows_upto(t, ctx._engine._dv) - lag      # bars available through the evaluated close
    if pos < n:
        return None
    return arr[pos - 1] / ((cs[pos] - cs[pos - n]) / n) - 1.0


class Rule(Strategy):
    def __init__(self, roles: dict, filters, check="D", lag=0, core=0.0, on=None, off=None,
                 defer=0):
        self.roles = roles
        self.filters = [(int(n), float(b)) for n, b in filters]
        self.check = check
        self.lag = int(lag)
        self.core = float(core)
        on = on or {"two": 1.0}
        off = off or {"safe": 1.0}
        so, sf = sum(on.values()), sum(off.values())
        self.on_t = {roles[r]: w / so for r, w in on.items() if w > 0}
        self.off_t = {roles[r]: w / sf for r, w in off.items() if w > 0}
        self.one = roles["one"]
        self.sig = roles.get("sig", roles["one"])
        self.defer = int(defer)
        if self.core > 0:
            assert self.one not in self.on_t and self.one not in self.off_t, \
                "core > 0 needs a sleeve that never holds the core's ticker (FIFO lots)"
        assert not (set(self.on_t) & set(self.off_t))

    # ------------------------------------------------------------------ lifecycle
    def initialize(self, ctx) -> None:
        self.K = len(self.filters)
        self.state = [None] * self.K
        self.k_held = None
        self.core_shares = 0.0
        self._last_check = None

    def _update_signal(self, ctx) -> None:
        pk = period_key(ctx.date, self.check)
        if pk == self._last_check:
            return
        self._last_check = pk
        for j, (n, b) in enumerate(self.filters):
            m = _sma_margin(ctx, self.sig, n, self.lag)
            if m is None:
                continue
            s = self.state[j]
            if s is None:
                self.state[j] = m > 0
            elif m > b:
                self.state[j] = True
            elif m < -b:
                self.state[j] = False

    def on_day(self, ctx) -> None:
        self._update_signal(ctx)
        if any(s is None for s in self.state):
            return
        k = int(sum(self.state))
        if self.k_held is None:
            self._start(ctx, k)
            return
        if k != self.k_held and self._retarget(ctx, k):
            return
        if ctx.cash < -1.0:
            self._cover(ctx)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _cost_mult(ctx) -> float:
        return (1.0 + ctx.slippage_pct) * (1.0 + ctx.commission_pct)

    def _buy_mix(self, ctx, mix: dict, amount: float) -> None:
        if amount <= 0:
            return
        cm = self._cost_mult(ctx)
        for t in sorted(mix):
            px = ctx.price(t)
            ctx.order(t, amount * mix[t] / (px * cm) * 0.999999)

    def _sell_frac(self, ctx, tickers, f: float) -> None:
        if f <= 0:
            return
        for t in sorted(tickers):
            q = ctx.shares(t)
            if t == self.one and self.core_shares > 0:
                q -= self.core_shares
            if q > 0:
                ctx.order(t, -min(q, q * f))

    def _priced(self, ctx, tickers) -> dict | None:
        out = {}
        for t in tickers:
            px = ctx.price(t)
            if px is None or px <= 0:
                return None
            out[t] = px
        return out

    def _start(self, ctx, k: int) -> None:
        need = set(self.on_t) | set(self.off_t) | ({self.one} if self.core > 0 else set())
        if self._priced(ctx, need) is None:
            return
        pv = ctx.portfolio_value
        if self.core > 0:
            px = ctx.price(self.one)
            ctx.order(self.one, self.core * pv / (px * self._cost_mult(ctx)) * 0.999999)
            self.core_shares = ctx.shares(self.one)
        cash = ctx.cash
        self._buy_mix(ctx, self.on_t, cash * k / self.K)
        self._buy_mix(ctx, self.off_t, cash * (1.0 - k / self.K))
        self.k_held = k

    def _values(self, ctx, tickers) -> float:
        tot = 0.0
        for t in tickers:
            q = ctx.shares(t)
            if t == self.one and self.core_shares > 0:
                q -= self.core_shares
            if q > 0:
                tot += q * ctx.price(t)
        return tot

    def _st_gain_deferrable(self, ctx, f: float) -> bool:
        """Would selling fraction f of the ON tickers realize a net short-term gain whose lots all
        turn long-term within `defer` days?"""
        net_mult = (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)
        st_gain = 0.0
        max_wait = 0
        any_st = False
        for t in self.on_t:
            q = ctx.shares(t) * f
            px = ctx.price(t) * net_mult
            for d, sh, cost in ctx.lots(t):
                if q <= 1e-12:
                    break
                take = min(q, sh)
                q -= take
                held = (ctx.date - d).days
                if held > 365:
                    continue
                any_st = True
                st_gain += (px - cost) * take
                max_wait = max(max_wait, 366 - held)
        return any_st and st_gain > 0 and max_wait <= self.defer

    def _retarget(self, ctx, k: int) -> bool:
        """Move the sleeve's on/off split to k/K. Returns False if deferred or not tradable."""
        tick = set(self.on_t) | set(self.off_t) | ({self.one} if self.core > 0 else set())
        if self._priced(ctx, tick) is None:
            return False
        pv = ctx.portfolio_value
        v_core = self.core_shares * ctx.price(self.one) if self.core > 0 else 0.0
        S = pv - v_core
        v_on = self._values(ctx, self.on_t)
        v_off = self._values(ctx, self.off_t)
        tgt_on = S * k / self.K
        if tgt_on < v_on:
            f = 1.0 if k == 0 else (v_on - tgt_on) / v_on
            if self.defer > 0 and self._st_gain_deferrable(ctx, f):
                return False
            self._sell_frac(ctx, self.on_t, f)
            self._buy_mix(ctx, self.off_t, ctx.cash / 1.0)
        else:
            tgt_off = S - tgt_on
            f = 1.0 if k == self.K else ((v_off - tgt_off) / v_off if v_off > 0 else 0.0)
            self._sell_frac(ctx, self.off_t, f)
            self._buy_mix(ctx, self.on_t, ctx.cash / 1.0)
        self.k_held = k
        return True

    def _cover(self, ctx) -> None:
        """Pay a negative cash balance (the January tax) by selling the sleeve pro rata."""
        sleeve = (set(self.on_t) | set(self.off_t))
        if self._priced(ctx, sleeve | ({self.one} if self.core > 0 else set())) is None:
            return
        net_mult = (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)
        need = -ctx.cash / net_mult
        v_sl = self._values(ctx, sleeve)
        if v_sl > 0:
            f = min(1.0, need / v_sl)
            self._sell_frac(ctx, sleeve, f)
        if ctx.cash < -1.0 and self.core_shares > 0:
            need = -ctx.cash / net_mult
            q = min(self.core_shares, need / ctx.price(self.one))
            ctx.order(self.one, -q)
            self.core_shares = max(0.0, self.core_shares - q)


def _build(c: dict) -> Strategy:
    return Rule(roles_of(c), c["filters"], c.get("check", "D"), c.get("lag", 0), c.get("core", 0.0),
                c.get("on"), c.get("off"), c.get("defer", 0))


def _tickers(c: dict) -> list:
    r = roles_of(c)
    used = {"one"} | set(c.get("on") or {"two": 1}) | set(c.get("off") or {"safe": 1})
    out = [r[k] for k in ("one", "two", "three", "safe") if k in used]
    if r.get("sig") and not r["sig"].startswith("^"):
        out.append(r["sig"])
    return list(dict.fromkeys(out))


register_kind("r2_lev2x.rule", _build, _tickers)
