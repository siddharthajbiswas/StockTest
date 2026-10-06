"""Round 2: cross-family combinations run as ONE taxable account (family key 'r2_combos').

Kind "r2_combos.sleeves"
------------------------
Several lab strategies run side by side as SLEEVES of one brokerage account:

    {"kind": "r2_combos.sleeves",
     "sleeves": [{"name": "core", "w": 0.5, "role": "core", "cfg": {"kind": "buyhold", "weights": {"SPY": 1}}},
                 {"name": "lev",  "w": 0.5, "role": "lev",  "cfg": {<a "weights" cfg, e.g. verify_lev_robust.trend>}}],
     "skim": true,          # see below (default false = sleeves drift freely)
     "tax": "realized",     # who pays the January tax bill: "realized" (default), "lev", "prorata"
     "requires": [...]}

* Each sleeve runs its own, unchanged rule on its own capital: it sees only its own
  positions, its own (virtual) cash, its own value and its own realized gains (so a
  1% gain budget means 1% of the SLEEVE, exactly as when the rule runs alone).
* All sleeves share ONE tax return: the engine nets every realized gain and loss of
  the account once a year (losses in one sleeve offset gains in another) and takes
  the tax from cash on the first trading day of January. The bill is charged to the
  sleeves in proportion to the tax their own net realized gains caused ("realized"),
  to the leveraged sleeve ("lev"), or by value ("prorata").
* Sleeves trade disjoint tickers. When two sleeves use the same ticker, the later one
  trades an identical-data clone R2C_C<k>_<TICKER> (research/lab/data/), so each
  sleeve keeps its own FIFO lots (= specific-lot identification per sleeve, which any
  broker allows). Signals always READ the original ticker's data. A clone is the same
  security for the wash-sale rule; scratch/r2_combos replays wash sales across
  sleeves for the finalists.
* skim=true: whenever the "lev" sleeve leaves its risk asset (trend exit) -- a sale
  that realizes its gains anyway -- the part of its value above its target share of
  the account is moved, as cash, to the other sleeves (pro rata to their target
  weights), which buy their current holdings pro rata. No other cross-sleeve trade
  ever happens (a never-sold core stays never sold). This keeps the leverage of a
  core-satellite design near its target without realizing any extra gain.

Signals
-------
"r2_combos.ens"   an ENSEMBLE of SMA-band trend rules (verify_lev_robust.trend
                  semantics per tranche): exposure to `risk` = share of tranches whose
                  rule is on, the rest in the first tradable `safe` ticker. Trades only
                  when the share changes (plus the monthly drift check).
"r2_combos.trot"  verify_lev_robust.trend whose risk-off leg is a momentum rotation
                  (tax_rotation.rank, e.g. KX1's ranking of the 22-ETF menu) instead of
                  Treasuries; the rotation is ranked at each exit and refreshed at
                  `rot_check` boundaries while risk is off.

Nothing looks ahead: every rule reads ctx history up to today's close (the fill
price), exactly as when it runs alone.
"""
from __future__ import annotations

import copy

import numpy as np

from backtester import Strategy
from backtester.strategy import Context

from ..blocks import Signal, WeightStrategy, np_closes, normalize, period_key
from ..registry import KINDS, SIGNALS, _WS_KEYS, kind_of, register_kind, register_signal

FAMILY = "r2_combos"


# --------------------------------------------------------------------------
# ticker ownership / clones
# --------------------------------------------------------------------------
def clone_name(k: int, t: str) -> str:
    return f"R2C_C{k}_{t}"


def sleeve_maps(cfg: dict) -> list[dict]:
    """[{orig ticker: engine ticker}] per sleeve. The first sleeve that lists a
    ticker trades it under its own name; later sleeves trade a clone."""
    owned: set = set()
    out = []
    for k, s in enumerate(cfg["sleeves"], start=1):
        ticks = [t for t in kind_of(s["cfg"]).tickers(s["cfg"]) if not t.startswith("^")]
        m = {}
        for t in dict.fromkeys(ticks):
            if t in owned:
                m[t] = clone_name(k, t)
            else:
                m[t] = t
                owned.add(t)
        out.append(m)
    return out


def _sleeves_tickers(cfg: dict) -> list:
    out = []
    for s in cfg["sleeves"]:
        out += list(kind_of(s["cfg"]).tickers(s["cfg"]))
    for m in sleeve_maps(cfg):
        out += [v for v in m.values()]
    return list(dict.fromkeys(out + ["SPY"]))


# --------------------------------------------------------------------------
# sleeve views: an engine-like object the unchanged strategies can talk to
# --------------------------------------------------------------------------
class _Lots:
    def __init__(self, pf):
        self._pf = pf

    def get(self, t, default=None):
        et = self._pf.tmap.get(t)
        if et is None:
            return default if default is not None else []
        return self._pf.eng.portfolio.lots.get(et, default if default is not None else [])


class _SleevePF:
    def __init__(self, eng, tmap: dict):
        self.eng = eng
        self.tmap = dict(tmap)                      # orig -> engine ticker
        self.inv = {v: k for k, v in self.tmap.items()}
        self.cash = 0.0
        self.realized: dict = {}
        self.lots = _Lots(self)
        self.commission_pct = eng.portfolio.commission_pct
        self.commission_per_share = eng.portfolio.commission_per_share

    @property
    def positions(self) -> dict:
        pos = self.eng.portfolio.positions
        return {o: pos[e] for o, e in self.tmap.items() if e in pos}

    def shares(self, t) -> float:
        e = self.tmap.get(t)
        return 0.0 if e is None else self.eng.portfolio.positions.get(e, 0.0)

    def holdings_value(self, prices) -> float:
        tot = 0.0
        for t, q in self.positions.items():
            px = prices.get(t)
            if px is not None:
                tot += q * px
        return tot

    def total_value(self, prices) -> float:
        return self.cash + self.holdings_value(prices)


class _SleeveEng:
    """What Context / WeightStrategy / the lab signals read from `ctx._engine`."""

    def __init__(self, eng, tmap: dict):
        self._eng = eng
        self.portfolio = _SleevePF(eng, tmap)
        self.market = eng.market
        self.calendar = eng.calendar
        self.tax_policy = eng.tax_policy
        self.slippage_pct = eng.slippage_pct
        self.min_order_value = eng.min_order_value
        self.verbose = False

    # passthrough of the current day
    @property
    def _i(self):
        return self._eng._i

    @property
    def _dv(self):
        return self._eng._dv

    @property
    def _date(self):
        return self._eng._date

    @property
    def today_prices(self):
        return self._eng.today_prices

    def current_prices(self) -> dict:
        p = self._eng.current_prices()
        inv = self.portfolio.inv
        return {inv[e]: v for e, v in p.items() if e in inv}

    def tradable_today(self):
        return self._eng.tradable_today()

    def field_today(self, t, f):
        return self._eng.field_today(t, f)

    def history(self, t, f, w):
        return self._eng.history(t, f, w)

    def place_order(self, t: str, shares: float) -> None:
        pf = self.portfolio
        e = pf.tmap.get(t)
        if e is None:
            raise KeyError(f"sleeve trades {t!r}, which it does not own")
        eng = self._eng
        if shares > 0:
            px = eng.today_prices.get(e)
            if px is None:
                return
            fill = px * (1.0 + eng.slippage_pct)
            per = fill + eng.portfolio.commission_per_share + fill * eng.portfolio.commission_pct
            afford = max(0.0, pf.cash) / per if per > 0 else 0.0
            shares = min(shares, afford)
            if shares <= 0:
                return
        cash0 = eng.portfolio.cash
        yr = eng._date.year
        r0 = eng.portfolio.realized.get(yr)
        st0, lt0 = (r0["st"], r0["lt"]) if r0 else (0.0, 0.0)
        eng.place_order(e, shares)
        pf.cash += eng.portfolio.cash - cash0
        r1 = eng.portfolio.realized.get(yr)
        if r1 is not None:
            b = pf.realized.setdefault(yr, {"st": 0.0, "lt": 0.0})
            b["st"] += r1["st"] - st0
            b["lt"] += r1["lt"] - lt0


class _Sleeve:
    def __init__(self, spec: dict, tmap: dict):
        self.name = spec.get("name", "")
        self.w = float(spec["w"])
        self.role = spec.get("role", "other")
        self.cfg = spec["cfg"]
        self.tmap = tmap
        self.strat = None
        self.view = None
        self.ctx = None

    def value(self) -> float:
        return self.view.portfolio.total_value(self.view.current_prices())


class SkimWS(WeightStrategy):
    """WeightStrategy of the leveraged sleeve: on a trend exit it sells the risk
    asset, lets the parent skim the value above the sleeve's target share, then
    buys the safe asset with what is left (WeightStrategy's own execution)."""

    parent = None

    def _execute(self, ctx, w):
        p = self.parent
        if p is not None and p.skim:
            sig = self.signal
            risk = getattr(sig, "risk", None) or {}
            if getattr(sig, "_state", None) is False and any(ctx.shares(t) > 0 for t in risk):
                for t in sorted(risk):
                    q = ctx.shares(t)
                    if q > 0 and ctx.price(t) is not None:
                        ctx.order(t, -q)
                p.skim_from(self)
        return WeightStrategy._execute(self, ctx, w)


class Sleeves(Strategy):
    def __init__(self, cfg: dict):
        self.cfg = cfg
        maps = sleeve_maps(cfg)
        self.sleeves = [_Sleeve(s, m) for s, m in zip(cfg["sleeves"], maps)]
        self.skim = bool(cfg.get("skim", False))
        self.skim_min = float(cfg.get("skim_min", 0.002))
        self.tax_mode = cfg.get("tax", "realized")
        W = sum(s.w for s in self.sleeves)
        for s in self.sleeves:
            s.wn = s.w / W
            c = s.cfg
            if s.role == "lev" and c["kind"] == "weights":
                factory = SIGNALS[c["signal"]][0]
                kw = {k: c[k] for k in _WS_KEYS if k in c}
                s.strat = SkimWS(factory(c.get("params", {})), **kw)
                s.strat.parent = self
            else:
                s.strat = KINDS[c["kind"]].build(c)
        # diagnostics
        self.n_skims = 0
        self.skimmed = 0.0
        self.min_cash_frac = 0.0

    # ---- lifecycle -------------------------------------------------------
    def initialize(self, ctx) -> None:
        eng = ctx._engine
        self._eng = eng
        for s in self.sleeves:
            s.view = _SleeveEng(eng, s.tmap)
            s.ctx = Context(s.view)
            s.ctx.date = ctx.date
            s.strat.initialize(s.ctx)
        self._funded = False
        self._prev_year = None

    def total_value(self) -> float:
        eng = self._eng
        return eng.portfolio.total_value(eng.current_prices())

    def _settle_tax(self, year_paid: int) -> None:
        eng = self._eng
        gap = eng.portfolio.cash - sum(s.view.portfolio.cash for s in self.sleeves)
        if gap > -1e-7:
            return
        tax = -gap
        pol = eng.tax_policy
        if self.tax_mode == "lev":
            c = [1.0 if s.role == "lev" else 0.0 for s in self.sleeves]
        elif self.tax_mode == "prorata":
            c = [max(0.0, s.value()) for s in self.sleeves]
        else:
            c = []
            for s in self.sleeves:
                r = s.view.portfolio.realized.get(year_paid, {"st": 0.0, "lt": 0.0})
                rs = pol.short_term_rate if pol else 0.0
                rl = pol.long_term_rate if pol else 0.0
                c.append(max(0.0, r["st"] * rs + r["lt"] * rl))
        if sum(c) <= 0:
            c = [max(0.0, s.value()) for s in self.sleeves]
        tot = sum(c) or 1.0
        for s, x in zip(self.sleeves, c):
            s.view.portfolio.cash -= tax * x / tot

    def skim_from(self, lev: _Sleeve | SkimWS) -> None:
        src = lev if isinstance(lev, _Sleeve) else next(s for s in self.sleeves if s.strat is lev)
        P = self.total_value()
        if P <= 0:
            return
        V = src.value()
        excess = min(V - src.wn * P, src.view.portfolio.cash)
        if excess <= self.skim_min * P:
            return
        others = [s for s in self.sleeves if s is not src]
        W = sum(s.w for s in others)
        if W <= 0:
            return
        self.n_skims += 1
        self.skimmed += excess
        for s in others:
            amt = excess * s.w / W
            src.view.portfolio.cash -= amt
            s.view.portfolio.cash += amt
            self._deposit(s, amt)

    def _deposit(self, s: _Sleeve, amt: float) -> None:
        """New cash into a sleeve: buy its current holdings pro rata to value."""
        ctx = s.ctx
        pos = ctx.positions
        vals = {}
        for t, q in pos.items():
            px = ctx.price(t)
            if px is None or q <= 0:
                continue
            blocked = getattr(s.strat, "_wash_blocked", None)
            if blocked is not None and getattr(s.strat, "execution", "") == "tax" and blocked(ctx, t):
                continue
            vals[t] = q * px
        tot = sum(vals.values())
        if tot <= 0:
            return
        cm = (1.0 + ctx.slippage_pct) * (1.0 + ctx.commission_pct)
        for t, v in sorted(vals.items()):
            ctx.order(t, amt * v / tot / (ctx.price(t) * cm) * 0.999999)

    def on_day(self, ctx) -> None:
        eng = ctx._engine
        if not self._funded:
            total = eng.portfolio.cash
            for s in self.sleeves:
                s.view.portfolio.cash = total * s.wn
            self._funded = True
        elif self._prev_year is not None and ctx.date.year != self._prev_year:
            self._settle_tax(self._prev_year)
        self._prev_year = ctx.date.year
        for s in self.sleeves:
            s.ctx.date = ctx.date
            s.strat.on_day(s.ctx)
        pv = eng.portfolio.total_value(eng.current_prices())
        if pv > 0:
            self.min_cash_frac = min(self.min_cash_frac, eng.portfolio.cash / pv)


def _sleeves_build(c):
    return Sleeves(c)


register_kind(f"{FAMILY}.sleeves", _sleeves_build, _sleeves_tickers)


# --------------------------------------------------------------------------
# helpers shared by the signals
# --------------------------------------------------------------------------
def _cur_weights(ctx) -> dict:
    eng = ctx._engine
    prices = eng.current_prices()
    pos = eng.portfolio.positions
    pv = eng.portfolio.cash + sum(q * prices.get(t, 0.0) for t, q in pos.items())
    if pv <= 0:
        return {}
    return {t: q * prices.get(t, 0.0) / pv for t, q in pos.items()}


def _closes(ctx, t: str, n: int, lag: int) -> np.ndarray:
    if lag <= 0:
        return np_closes(ctx, t, n)
    c = np_closes(ctx, t, n + lag)
    return c[:-lag] if len(c) > lag else c[:0]


# --------------------------------------------------------------------------
# r2_combos.ens: ensemble of SMA-band trend rules
# --------------------------------------------------------------------------
class Ens(Signal):
    daily = True

    def __init__(self, sig="SPY", tranches=((200, 0.03),), check="D", risk=None, safe=None,
                 lag=0, mdrift=0.05, sdrift=0.0):
        self.sig = sig
        self.tr = [(int(n), float(b)) for n, b in tranches]
        self.check = check
        self.risk = dict(risk or {"SYN_SPY2XC": 1.0})
        self.safe = [safe] if isinstance(safe, str) else list(safe or ["VFITX"])
        self.lag = int(lag)
        self.mdrift = mdrift
        self.sdrift = sdrift

    def initialize(self, ctx):
        self._st = [None] * len(self.tr)
        self._last_check = None
        self._key = None

    def _update(self, ctx):
        nmax = max(n for n, _ in self.tr)
        c = _closes(ctx, self.sig, nmax, self.lag)
        for k, (n, b) in enumerate(self.tr):
            if len(c) < n:
                continue
            m = c[-1] / c[-n:].mean() - 1.0
            st = self._st[k]
            if st is None:
                self._st[k] = m > 0
            elif m > b:
                self._st[k] = True
            elif m < -b:
                self._st[k] = False

    def _alloc(self, ctx, f: float) -> dict:
        w = {}
        if f > 0:
            live = {t: v for t, v in self.risk.items() if v > 0 and ctx.price(t) is not None}
            if not live:
                return {}
            for t, v in normalize(live, sum(self.risk.values())).items():
                w[t] = f * v
        if f < 1:
            for t in self.safe:
                if ctx.price(t) is not None:
                    w[t] = w.get(t, 0.0) + (1.0 - f)
                    break
        return w

    def weights(self, ctx, rebalance_day):
        pk = period_key(ctx.date, self.check)
        if pk != self._last_check:
            self._last_check = pk
            self._update(ctx)
        known = [s for s in self._st if s is not None]
        if not known:
            return None
        f = sum(1 for s in known if s) / len(known)
        tgt = self._alloc(ctx, f)
        if not tgt:
            return None
        key = (round(f, 9), tuple(sorted(tgt)))
        if key != self._key:
            self._key = key
            return tgt
        if rebalance_day:
            cur = _cur_weights(ctx)
            ab = max(abs(cur.get(t, 0.0) - tgt.get(t, 0.0)) for t in set(cur) | set(tgt))
            thr = self.mdrift if len(tgt) > 1 else self.sdrift
            if thr is not None and ab > thr:
                return tgt
        return None


def _ens_tickers(p):
    out = list((p.get("risk") or {"SYN_SPY2XC": 1.0}).keys())
    safe = p.get("safe") or ["VFITX"]
    out += [safe] if isinstance(safe, str) else list(safe)
    sig = p.get("sig", "SPY")
    if not sig.startswith("^"):
        out.append(sig)
    return list(dict.fromkeys(out))


register_signal(f"{FAMILY}.ens", lambda p: Ens(**p), _ens_tickers)


# --------------------------------------------------------------------------
# r2_combos.trot: leveraged trend whose risk-off leg is a momentum rotation
# --------------------------------------------------------------------------
def _trend_cls():
    from .verify_lev_robust import Trend
    return Trend


def _make_trot(p):
    Trend = _trend_cls()
    from .tax_rotation import Rank

    class TrendRot(Trend):
        def __init__(self, rot=None, rot_check="Q", **kw):
            super().__init__(**kw)
            self.rot = Rank(**rot)
            self.rot_check = rot_check

        def initialize(self, ctx):
            super().initialize(ctx)
            self.rot.initialize(ctx)
            self._rk = None
            self._rw = None
            self._prev_on = None

        def _alloc(self, ctx, on):
            if on:
                self._prev_on = True
                return Trend._alloc(self, ctx, True)
            k = period_key(ctx.date, self.rot_check)
            if self._rw is None or self._prev_on or k != self._rk:
                w = self.rot.weights(ctx, True) or {}
                self._rw = {t: x for t, x in w.items() if x > 0}
                self._rk = k
            self._prev_on = False
            live = {t: x for t, x in self._rw.items() if ctx.price(t) is not None}
            if not live:
                return Trend._alloc(self, ctx, False)
            return normalize(live, 1.0)

    q = dict(p)
    return TrendRot(**q)


def _trot_tickers(p):
    from .verify_lev_robust import _tickers as tt
    from .tax_rotation import _rank_tickers
    q = {k: v for k, v in p.items() if k not in ("rot", "rot_check")}
    return list(dict.fromkeys(tt(q) + _rank_tickers(p["rot"])))


register_signal(f"{FAMILY}.trot", _make_trot, _trot_tickers)


# --------------------------------------------------------------------------
# small helpers for scratch scripts (not used by the strategies)
# --------------------------------------------------------------------------
def combo(sleeves: list, skim=False, tax="realized", requires=None, min_start=None, **extra) -> dict:
    c = {"kind": f"{FAMILY}.sleeves", "sleeves": copy.deepcopy(sleeves), "skim": bool(skim), "tax": tax}
    if requires:
        c["requires"] = list(requires)
    if min_start:
        c["min_start"] = min_start
    c.update(extra)
    return c
