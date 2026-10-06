"""Generic strategy building blocks: signal -> target weights -> execution.

The site's Combo can only express "equal-weight the names a picker likes and a
timer allows". Most allocation ideas need more: unequal weights (inverse vol,
risk parity), partial exposure (vol targeting), a safe-asset fallback, blends.
`WeightStrategy` separates the two decisions:

  * a **signal** returns target weights {ticker: weight} (sum <= 1; the rest is
    cash, which earns nothing in this engine -- use a T-bill/bond ETF if you
    want a yield), and
  * an **execution rule** moves the portfolio toward them through the engine's
    ordinary `ctx.order` -- so commission, slippage, tax lots, the annual tax
    settlement and the terminal liquidation tax all apply exactly as on the site.

Execution rules
---------------
"standard"  trade to the targets (optionally only names whose weight drifted
            more than `band` away), sells first, then buys scaled to the cash
            actually available (no leverage, no alphabetical priority).
"tax"       TaxManagedCombo's rule generalised to arbitrary weights: losses are
            always sold, gains only while the year's net realized gain stays
            under `gain_budget` x portfolio value (smallest gains first, long-
            term before short-term, last sale part-filled), a name sold at a loss
            cannot be rebought for `wash_days`. `st_gains=False` additionally
            forbids realizing any short-term gain at all.

Optional tax-loss harvesting (`harvest`): on every `harvest_freq` period, any
position whose unrealized loss exceeds `harvest` (e.g. 0.05 = 5%) is sold,
and if `substitutes` maps it to a different-index fund that fund is bought
with the proceeds (so exposure is kept). The original is barred for
`wash_days`; the substitute is swapped back at the next rebalance only if that
does not realize a gain the budget forbids.

Nothing here can see the future: signals read `ctx.history`, which the engine
clips to today.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from backtester import Strategy


# --------------------------------------------------------------------------
# small helpers shared by signals
# --------------------------------------------------------------------------
def period_key(date: pd.Timestamp, cadence: str):
    if cadence == "D":
        return date.date()
    if cadence == "W":
        iso = date.isocalendar()
        return (iso.year, iso.week)
    if cadence == "M":
        return (date.year, date.month)
    if cadence == "Q":
        return (date.year, (date.month - 1) // 3)
    if cadence == "S":
        return (date.year, (date.month - 1) // 6)
    if cadence == "A":
        return (date.year,)
    if cadence.startswith("M") and cadence[1:].isdigit():      # every k months
        k = int(cadence[1:])
        return (date.year * 12 + date.month - 1) // k
    raise ValueError(f"unknown cadence {cadence!r}")


def closes(ctx, t: str, n: int | None = None) -> pd.Series:
    return ctx.history(t, "Close", n)


def tret(ctx, t: str, lookback: int, skip: int = 0) -> float | None:
    """Total return over `lookback` bars ending `skip` bars ago (None if short)."""
    need = lookback + skip + 1
    c = ctx.history(t, "Close", need)
    if len(c) < need:
        return None
    a = float(c.iloc[0])
    b = float(c.iloc[len(c) - 1 - skip])
    if a <= 0:
        return None
    return b / a - 1.0


def rvol(ctx, t: str, n: int) -> float | None:
    c = ctx.history(t, "Close", n + 1)
    if len(c) < n + 1:
        return None
    r = c.pct_change().dropna()
    s = float(r.std(ddof=0))
    return s * math.sqrt(252) if s > 0 else None


def sma(ctx, t: str, n: int) -> float | None:
    c = ctx.history(t, "Close", n)
    if len(c) < n:
        return None
    return float(c.mean())


# ---- fast numpy access (10x faster than ctx.history for hot loops) -------
def np_closes(ctx, t: str, n: int | None = None) -> np.ndarray:
    """Closes up to and including today as a numpy array (last `n`)."""
    m = ctx._engine.market
    s = m.series(t, "Close")
    if s is None:
        return np.empty(0)
    cache = m.__dict__.setdefault("_np_close", {})
    arr = cache.get(t)
    if arr is None:
        arr = cache[t] = s.to_numpy(dtype=float)
    pos = m.rows_upto(t, ctx._engine._dv)
    if n is None or n >= pos:
        return arr[:pos]
    return arr[pos - n:pos]


# ---- side-channel series (indices such as ^VIX, ^IRX, ^TNX) -------------
_SIDE: dict = {}


def side_series(t: str) -> pd.Series:
    """Full close series of a signal-only ticker (never part of the market)."""
    s = _SIDE.get(t)
    if s is None:
        from . import data
        s = _SIDE[t] = data.frame(t)["Close"].astype(float)
    return s


def asof(ctx, t: str, lag_days: int = 1, n: int = 1):
    """Value(s) of a side-channel series known before today's close.

    lag_days=1 (default) uses only observations dated strictly before today,
    which is conservative (index closes such as VIX settle after the stock
    close). Returns a float for n == 1, else a numpy array of the last n.
    """
    s = side_series(t)
    cut = ctx.date - pd.Timedelta(days=lag_days - 1) if lag_days > 0 else ctx.date
    pos = int(s.index.searchsorted(cut, side="left" if lag_days > 0 else "right"))
    if pos <= 0:
        return None if n == 1 else np.empty(0)
    if n == 1:
        return float(s.iloc[pos - 1])
    return s.iloc[max(0, pos - n):pos].to_numpy()


def tradable(ctx, t: str) -> bool:
    return ctx.price(t) is not None


def has_history(ctx, t: str, n: int) -> bool:
    return len(ctx.history(t, "Close", n)) >= n


def normalize(w: dict, total: float = 1.0) -> dict:
    s = sum(v for v in w.values() if v > 0)
    if s <= 0:
        return {}
    return {k: total * v / s for k, v in w.items() if v > 0}


# --------------------------------------------------------------------------
# Signals
# --------------------------------------------------------------------------
class Signal:
    """Return target weights. `daily=True` signals are asked every day
    (return None for "no change"); others only on rebalance days."""

    daily = False

    def initialize(self, ctx) -> None:
        pass

    def weights(self, ctx, rebalance_day: bool) -> dict | None:
        raise NotImplementedError


class FixedWeights(Signal):
    """A static allocation (rebalanced back to it on each rebalance day)."""

    def __init__(self, weights: dict):
        self.w = dict(weights)

    def weights(self, ctx, rebalance_day):
        live = {t: w for t, w in self.w.items() if tradable(ctx, t)}
        # Not every fund exists yet (e.g. before inception): scale up the rest.
        return normalize(live, sum(self.w.values())) if live else {}


# --------------------------------------------------------------------------
# The strategy
# --------------------------------------------------------------------------
class WeightStrategy(Strategy):
    def __init__(
        self,
        signal: Signal,
        rebalance: str = "M",
        execution: str = "standard",
        band: float = 0.0,
        gain_budget: float = 0.01,
        wash_days: int = 31,
        st_gains: bool = True,
        harvest: float | None = None,
        harvest_freq: str = "M",
        substitutes: dict | None = None,
        min_trade_frac: float = 0.0,
    ):
        self.signal = signal
        self.rebalance = rebalance
        self.execution = execution
        self.band = band
        self.gain_budget = gain_budget
        self.wash_days = wash_days
        self.st_gains = st_gains
        self.harvest = harvest
        self.harvest_freq = harvest_freq
        self.substitutes = dict(substitutes or {})
        self.min_trade_frac = min_trade_frac

    # ---- lifecycle --------------------------------------------------------
    def initialize(self, ctx) -> None:
        self.signal.initialize(ctx)
        self._last = None
        self._last_h = None
        self._loss_sale: dict = {}
        self._target: dict = {}

    def on_day(self, ctx) -> None:
        key = period_key(ctx.date, self.rebalance)
        reb = key != self._last
        if reb:
            self._last = key
        w = None
        if reb or self.signal.daily:
            w = self.signal.weights(ctx, reb)
        if w is not None:
            self._target = dict(w)
            self._execute(ctx, w)
        elif self.harvest is not None:
            hk = period_key(ctx.date, self.harvest_freq)
            if hk != self._last_h:
                self._last_h = hk
                self._harvest(ctx)

    # ---- tax helpers ------------------------------------------------------
    @staticmethod
    def _gain_if_sold(ctx, t, qty, net_px):
        rem = qty
        gain = 0.0
        all_lt = True
        for d, sh, cost in ctx.lots(t):
            if rem <= 1e-12:
                break
            take = min(rem, sh)
            gain += (net_px - cost) * take
            if not ctx.is_long_term(d):
                all_lt = False
            rem -= take
        return gain, all_lt

    def _net_px(self, ctx, px):
        return px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)

    def _wash_blocked(self, ctx, t) -> bool:
        last = self._loss_sale.get(t)
        return last is not None and (ctx.date - last).days <= self.wash_days

    # ---- execution --------------------------------------------------------
    def _execute(self, ctx, w: dict) -> None:
        pv = ctx.portfolio_value
        if pv <= 0:
            return
        pos = ctx.positions
        tgt: dict = {}
        for t in set(w) | set(pos):
            px = ctx.price(t)
            if px is None or px <= 0:
                continue                       # cannot trade it today: leave as is
            want = pv * w.get(t, 0.0) / px
            held = pos.get(t, 0.0)
            if t in w and w[t] > 0 and self.band > 0:
                cur_w = held * px / pv
                if abs(cur_w - w[t]) < self.band:
                    continue                   # inside the tolerance band
            if self.min_trade_frac > 0 and abs(want - held) * px < self.min_trade_frac * pv and want > 0:
                continue
            tgt[t] = want

        # ---- sells
        if self.execution == "tax":
            self._tax_sells(ctx, pv, tgt)
        else:
            for t in sorted(tgt):
                held = ctx.shares(t)
                if tgt[t] < held - 1e-12:
                    ctx.order(t, tgt[t] - held)

        # ---- buys, scaled to the cash actually available
        self._buys(ctx, tgt)

    def _tax_sells(self, ctx, pv, tgt) -> None:
        st, lt = ctx.realized_this_year()
        room = self.gain_budget * pv - (st + lt)
        cands = []
        for t, target in tgt.items():
            held = ctx.shares(t)
            if held <= 0 or target >= held - 1e-12:
                continue
            qty = held - target
            net = self._net_px(ctx, ctx.price(t))
            gain, all_lt = self._gain_if_sold(ctx, t, qty, net)
            cands.append((gain > 0, not all_lt, gain, t, qty))
        cands.sort(key=lambda c: (c[0], c[1], c[2], c[3]))
        for is_gain, is_short, gain, t, qty in cands:
            if not is_gain:
                sell = qty
            elif is_short and not self.st_gains:
                continue
            elif gain <= room + 1e-9:
                sell = qty
            elif room > 1e-9:
                frac = room / gain
                if frac <= 0.02:
                    continue
                sell = qty * frac
            else:
                continue
            room -= gain * (sell / qty)          # a loss (gain < 0) refills it
            ctx.order(t, -sell)
            if gain < 0:
                self._loss_sale[t] = ctx.date

    def _buys(self, ctx, tgt) -> None:
        buys = []
        for t in sorted(tgt):
            delta = tgt[t] - ctx.shares(t)
            if delta <= 1e-12:
                continue
            if self.execution == "tax" and self._wash_blocked(ctx, t):
                continue
            buys.append((t, delta))
        if not buys:
            return
        cost_mult = (1.0 + ctx.slippage_pct) * (1.0 + ctx.commission_pct)
        need = sum(d * ctx.price(t) * cost_mult for t, d in buys)
        cash = ctx.cash
        if need <= 0 or cash <= 0:
            return
        scale = min(1.0, cash / need * 0.999999)
        for t, d in buys:
            ctx.order(t, d * scale)

    # ---- tax-loss harvesting between rebalances --------------------------
    def _harvest(self, ctx) -> None:
        pos = ctx.positions
        sold_any = False
        for t in sorted(pos):
            px = ctx.price(t)
            if px is None:
                continue
            lots = ctx.lots(t)
            if not lots:
                continue
            basis = sum(sh * c for _, sh, c in lots)
            shares = sum(sh for _, sh, _ in lots)
            if shares <= 0 or basis <= 0:
                continue
            val = shares * self._net_px(ctx, px)
            if val / basis - 1.0 > -self.harvest:
                continue
            ctx.order(t, -pos[t])
            self._loss_sale[t] = ctx.date
            sold_any = True
            sub = self.substitutes.get(t)
            if sub and ctx.price(sub) is not None and not self._wash_blocked(ctx, sub):
                cash_for = val
                ctx.order(sub, cash_for / (ctx.price(sub) * (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)) * 0.999999)
        return None
