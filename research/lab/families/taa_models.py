"""Published tactical asset allocation (TAA) models -- family `taa_models`.

Every model is a `Signal` returning target weights and runs through the lab's
`WeightStrategy` (execution "standard" = trade to targets each rebalance,
"tax" = the tax-managed rule), so commission, slippage, tax lots, the annual
settlement and the terminal liquidation tax are exactly the site's.

Ticker slots and proxy chains
-----------------------------
Every asset in a model is a *slot*: a ticker ("SPY") or a proxy chain
"EFA|VGTSX" = use EFA when it trades today and has the history the signal
needs, else VGTSX.  Chains let a model run before an ETF existed on the index
mutual fund that tracks the same asset class, and build the long-history
(1986+) versions.  A chain member that is currently held keeps winning (no
forced, taxable switch when the preferred ETF launches).  Configs must set
"requires" to the earliest member of every chain (see `requires_for`).

Momentum / trend measures (`spec` strings)
------------------------------------------
Closes are sampled at calendar-month offsets from today (anchor "cal":
p_k = last close on or before today - k*30.44 days; p_0 = today's close), or
at completed month-ends (anchor "me": p_0 = last month-end close, p_k = the
k-th month-end before it -- the papers' monthly data, traded one day late).
    r{k}        p0/pk - 1                        r12 = 12-month total return
    r{k}s{j}    pj/pk - 1                        r12s1 = classic 12-1 momentum
    sum{a}_{b}  r_a + r_b + ...                  sum1_3_6 = Accelerating DM
    avg{a}_{b}  mean(r_a, r_b, ...)              avg1_3_6_12 = 13612U
    13612w      (12 r1 + 4 r3 + 2 r6 + r12) / 4  Keller (VAA/DAA/BAA canary)
    13612u      (r1 + r3 + r6 + r12) / 4         Keller (HAA, GPM)
    sma{n}      p0 / mean(p0..p_{n-1}) - 1       sma10 = Faber 10-month SMA;
                                                 sma13 = BAA/PAA "SMA(12)"
    dsma{n}     c0 / mean(last n daily closes) - 1
    d{n}        c0 / c_n - 1 (n trading days)
Linear specs (r/sum/avg/13612) also have a T-bill value -- the same
combination of T-bill returns, from ^IRX lagged one day -- for "beats T-bills"
(absolute momentum) tests.

Models (signal names are "taa_models.<name>")
---------------------------------------------
dual       Dual momentum, generalised: Antonacci GEM, Accelerating Dual
           Momentum, Quint switching, any "best of N risky if it beats a
           threshold, else safe" rule.
sleeves    Fixed sleeves each held only while a trend filter is on (Faber
           GTAA-5 / Ivy timing / GTAA-13; Robust Asset Allocation style
           double filter); optional top-k momentum selection (GTAA AGG 3/6).
breadth    Keller-Keuning breadth momentum: VAA (offensive universe is its own
           canary, B=1 for G4 / B=4 for G12) and DAA (separate canary
           universe, CF = bad canaries / B).
paa        Protective Asset Allocation (bond fraction from the number of risky
           assets above their SMA, protection factor a).
baa        Bold Asset Allocation (13612W canary, SMA(12) relative momentum,
           defensive top-3 with a BIL floor).
haa        Hybrid Asset Allocation (TIP canary, 13612U, negative-momentum
           assets swapped for the best of BIL/IEF).
gpm        Generalised Protective Momentum (score r*(1-c), crash protection
           by the share of non-positive scores).
faa        Flexible Asset Allocation (ranks of return, volatility,
           correlation; absolute filter to cash).
eaa        Elastic Asset Allocation (geometric r^wR (1-c)^wC / v^wV score).
cdm        Antonacci Composite Dual Momentum (modules of paired assets).
aaa        Adaptive Asset Allocation (top-k by momentum, min-variance or
           inverse-vol weights).
static     Static mixes (60/40, Permanent Portfolio, All-Weather, Golden
           Butterfly, Ivy B&H, ...) with calendar or tolerance-band rebalancing.
"""
from __future__ import annotations

import math
import re
from functools import lru_cache

import numpy as np

from ..blocks import Signal, asof, np_closes
from ..registry import register_signal

_MONTH_DAYS = 30.4375


# --------------------------------------------------------------------------
# data access
# --------------------------------------------------------------------------
def _series(ctx, t):
    """(close array, date index, number of bars up to and including today)."""
    m = ctx._engine.market
    s = m.series(t, "Close")
    if s is None:
        return None, None, 0
    cache = m.__dict__.setdefault("_np_close", {})
    arr = cache.get(t)
    if arr is None:
        arr = cache[t] = s.to_numpy(dtype=float)
    idx = m._index.get(t)
    pos = m.rows_upto(t, ctx._engine._dv)
    return arr, idx, pos


def _me_index(m, t):
    """Positions of the last bar of each month in t's own series. Position j is
    a month-end iff bar j+1 falls in a later month, so for j < today's bar it
    is decided by bars already seen (no look-ahead)."""
    cache = m.__dict__.setdefault("_taa_me", {})
    v = cache.get(t)
    if v is None:
        idx = m._index.get(t)
        if idx is None or len(idx) < 2:
            v = np.empty(0, dtype=np.int64)
        else:
            mon = idx.astype("datetime64[M]")
            v = np.nonzero(mon[1:] != mon[:-1])[0]
        cache[t] = v
    return v


def samples(ctx, t, ks, anchor="cal"):
    """Closes p_k for each k (months back) in ks, or None if unavailable."""
    arr, idx, pos = _series(ctx, t)
    if arr is None or pos == 0:
        return None
    out = []
    if anchor == "cal":
        today = ctx._engine._dv
        for k in ks:
            if k == 0:
                out.append(arr[pos - 1])
                continue
            target = today - np.timedelta64(int(round(_MONTH_DAYS * k)), "D")
            j = int(idx.searchsorted(target, side="right")) - 1
            if j < 0 or j >= pos:
                return None
            out.append(arr[j])
        return out
    me = _me_index(ctx._engine.market, t)
    n = int(me.searchsorted(pos - 1, side="left"))   # completed month-ends
    for k in ks:
        i = n - 1 - k
        if i < 0:
            return None
        out.append(arr[me[i]])
    return out


@lru_cache(maxsize=None)
def parse_spec(spec: str):
    s = spec.strip().lower()
    if s == "13612w":
        return ("lin", ((1, 0, 3.0), (3, 0, 1.0), (6, 0, 0.5), (12, 0, 0.25)))
    if s == "13612u":
        return ("lin", ((1, 0, 0.25), (3, 0, 0.25), (6, 0, 0.25), (12, 0, 0.25)))
    m = re.fullmatch(r"r(\d+)(?:s(\d+))?", s)
    if m:
        k, j = int(m[1]), int(m[2] or 0)
        return ("lin", ((k + j, j, 1.0),))
    m = re.fullmatch(r"(sum|avg)([\d_]+)", s)
    if m:
        ks = [int(x) for x in m[2].split("_") if x]
        w = 1.0 if m[1] == "sum" else 1.0 / len(ks)
        return ("lin", tuple((k, 0, w) for k in ks))
    m = re.fullmatch(r"sma(\d+)", s)
    if m:
        return ("sma", int(m[1]))
    m = re.fullmatch(r"dsma(\d+)", s)
    if m:
        return ("dsma", int(m[1]))
    m = re.fullmatch(r"d(\d+)", s)
    if m:
        return ("d", int(m[1]))
    raise ValueError(f"unknown momentum spec {spec!r}")


def months_needed(spec: str) -> int:
    kind, d = parse_spec(spec)
    if kind == "lin":
        return max(k for k, _, _ in d)
    if kind == "sma":
        return d - 1
    return int(math.ceil(d / 21.0))


def mom(ctx, t, spec, anchor="cal"):
    kind, d = parse_spec(spec)
    if kind == "lin":
        ks = sorted({x for (k, j, _) in d for x in (k, j)})
        p = samples(ctx, t, ks, anchor)
        if p is None:
            return None
        pm = dict(zip(ks, p))
        v = 0.0
        for k, j, w in d:
            if pm[k] <= 0:
                return None
            v += w * (pm[j] / pm[k] - 1.0)
        return v
    if kind == "sma":
        p = samples(ctx, t, list(range(d)), anchor)
        if p is None:
            return None
        a = sum(p) / len(p)
        return p[0] / a - 1.0 if a > 0 else None
    if kind == "dsma":
        c = np_closes(ctx, t, d)
        if len(c) < d or c.mean() <= 0:
            return None
        return float(c[-1] / c.mean() - 1.0)
    c = np_closes(ctx, t, d + 1)                              # "d"
    if len(c) < d + 1 or c[0] <= 0:
        return None
    return float(c[-1] / c[0] - 1.0)


def tbill(ctx, spec) -> float:
    """T-bill value of a linear spec from ^IRX (13-week yield, % p.a.), using
    only observations dated before today. 0 for non-linear specs."""
    kind, d = parse_spec(spec)
    if kind != "lin":
        return 0.0
    kmax = max(k for k, _, _ in d)
    y = asof(ctx, "^IRX", lag_days=1, n=21 * kmax + 1)
    if y is None or len(y) == 0:
        return 0.0
    n = len(y)
    v = 0.0
    for k, j, w in d:
        a = max(0, n - 21 * k)
        b = n - 21 * j if j else n
        seg = y[a:b]
        if len(seg) == 0:
            continue
        v += w * float(np.nanmean(seg)) / 100.0 * (k - j) / 12.0
    return v


def has_hist(ctx, t, spec, anchor="cal") -> bool:
    kind, d = parse_spec(spec)
    if kind in ("dsma", "d"):
        n = d + (1 if kind == "d" else 0)
        return len(np_closes(ctx, t, n)) >= n
    k = months_needed(spec)
    return samples(ctx, t, [k], anchor) is not None


def daily_returns(ctx, t, n):
    c = np_closes(ctx, t, n + 1)
    if len(c) < n + 1:
        return None
    return np.diff(c) / c[:-1]


# --------------------------------------------------------------------------
# slots
# --------------------------------------------------------------------------
def chain(slot: str) -> list:
    return [x for x in slot.split("|") if x]


def resolve(ctx, slot, spec=None, anchor="cal"):
    """The chain member to use today: a held, tradable member with enough
    history wins; else the first tradable member with enough history."""
    pos = ctx._engine.portfolio.positions
    first = None
    for t in chain(slot):
        if ctx.price(t) is None:
            continue
        if spec is not None and not has_hist(ctx, t, spec, anchor):
            continue
        if t in pos:
            return t
        if first is None:
            first = t
    return first


def _slots_of(p: dict) -> list:
    out = []
    for key in ("risky", "safe", "cash", "canary", "offensive", "defensive", "menu"):
        v = p.get(key)
        if isinstance(v, str):
            out.append(v)
        elif v:
            out.extend(v)
    for key in ("sleeves", "weights"):
        v = p.get(key)
        if isinstance(v, dict):
            out.extend(v)
        elif v:
            out.extend(v)
    for mod in p.get("modules") or []:
        out.extend(mod)
    for key in ("abs_ref", "cash_floor", "canary_one"):
        v = p.get(key)
        if isinstance(v, str) and v not in ("^IRX", "zero") and not v.startswith("^"):
            out.append(v)
    return out


def tickers_of(p: dict) -> list:
    out = []
    for s in _slots_of(p):
        out.extend(chain(s))
    return list(dict.fromkeys(out))


def requires_for(p: dict) -> list:
    """For a config's "requires": the earliest-launched member of every chain
    (a window may start once every slot has *some* instrument)."""
    from .. import data
    req = []
    for s in dict.fromkeys(_slots_of(p)):
        mem = chain(s)
        req.append(min(mem, key=lambda t: data.first_date(t)))
    return list(dict.fromkeys(req))


def _add(w: dict, t, x):
    if t is None or x <= 0:
        return
    w[t] = w.get(t, 0.0) + float(x)


def _st_gain(ctx, t) -> bool:
    """Is t held with a short-term lot that would realize a gain if sold?"""
    lots = ctx.lots(t)
    if not lots:
        return False
    px = ctx.price(t)
    if px is None:
        return False
    net = px * (1.0 - ctx.slippage_pct) * (1.0 - ctx.commission_pct)
    return any((not ctx.is_long_term(d)) and net > c for d, _, c in lots)


# --------------------------------------------------------------------------
# base
# --------------------------------------------------------------------------
class _Base(Signal):
    anchor = "cal"

    def m(self, ctx, t, spec):
        return mom(ctx, t, spec, self.anchor)

    def res(self, ctx, slot, spec=None):
        return resolve(ctx, slot, spec, self.anchor)

    def scored(self, ctx, slots, spec):
        """[(score, ticker, slot_index)] for resolvable slots, best first."""
        out = []
        for i, s in enumerate(slots):
            t = self.res(ctx, s, spec)
            if t is None:
                continue
            v = self.m(ctx, t, spec)
            if v is None:
                continue
            out.append((v, t, i))
        out.sort(key=lambda x: (-x[0], x[2]))
        return out

    def held_adjust(self, ctx, sc, rel_margin=0.0, tax_hold=False):
        """Re-rank scored risky assets with a bonus for the ones already held:
        `rel_margin` (hysteresis: a challenger must beat a held asset by this
        much) and `tax_hold` (a held asset with a short-term gain lot is never
        rotated out for a better-ranked *risky* asset; only taxed regimes have
        lots, so this is a no-op without taxes). Absolute/canary tests still
        apply afterwards, so crash protection is unchanged."""
        if not (rel_margin or tax_hold) or not sc:
            return sc
        held = ctx._engine.portfolio.positions
        adj = []
        for v, t, i in sc:
            b = 0.0
            if t in held:
                b += rel_margin
                if tax_hold and _st_gain(ctx, t):
                    b += 1e6
            adj.append((v + b, v, t, i))
        adj.sort(key=lambda x: (-x[0], x[3]))
        return [(v, t, i) for _, v, t, i in adj]

    def safe_alloc(self, ctx, slots, select, spec, total, n=1):
        """Spread `total` over the safe/cash slots: "first" resolvable, "best"
        n by `spec`, or "split" equally. Empty slots -> engine cash."""
        w = {}
        if total <= 1e-12 or not slots:
            return w
        if select == "split":
            ts = [self.res(ctx, s) for s in slots]
            ts = [t for t in ts if t]
            for t in ts:
                _add(w, t, total / len(ts))
            return w
        if select == "best":
            sc = self.scored(ctx, slots, spec)
            if sc:
                picks = sc[:n]
                for _, t, _ in picks:
                    _add(w, t, total / len(picks))
                return w
        for s in slots:
            t = self.res(ctx, s)
            if t:
                _add(w, t, total)
                return w
        return w


# --------------------------------------------------------------------------
# dual momentum (GEM, Accelerating DM, Quint switching, ...)
# --------------------------------------------------------------------------
class DualMomentum(_Base):
    """Hold the `top` best risky slots by `mom`; each must pass the absolute
    test (abs_mom > threshold) or its share goes to the safe asset.

    abs_on "first": the first risky slot (Antonacci GEM: US stocks vs T-bills)
            decides for everyone; "each": every pick is tested on its own.
    abs_ref "^IRX" (T-bill return over the same horizon), "zero", or a slot
            whose abs_mom is the hurdle (e.g. "BIL").
    """

    def __init__(self, risky, safe, mom="r12", abs_mom=None, abs_ref="^IRX",
                 abs_on="first", top=1, safe_select="first", safe_mom=None,
                 safe_n=1, margin=0.0, rel_margin=0.0, tax_hold=False, anchor="cal"):
        self.rel_margin = rel_margin
        self.tax_hold = tax_hold
        self.risky = list(risky)
        self.safe = [safe] if isinstance(safe, str) else list(safe or [])
        self.mom = mom
        self.abs_mom = abs_mom or mom
        self.abs_ref = abs_ref
        self.abs_on = abs_on
        self.top = top
        self.safe_select = safe_select
        self.safe_mom = safe_mom or mom
        self.safe_n = safe_n
        self.margin = margin
        self.anchor = anchor

    def _hurdle(self, ctx):
        if self.abs_ref == "zero":
            return 0.0
        if self.abs_ref == "^IRX":
            return tbill(ctx, self.abs_mom)
        t = self.res(ctx, self.abs_ref, self.abs_mom)
        v = self.m(ctx, t, self.abs_mom) if t else None
        return tbill(ctx, self.abs_mom) if v is None else v

    def _passes(self, ctx, t, hurdle):
        a = self.m(ctx, t, self.abs_mom)
        return a is not None and a > hurdle + self.margin

    def weights(self, ctx, rebalance_day):
        sc = self.scored(ctx, self.risky, self.mom)
        sc = self.held_adjust(ctx, sc, self.rel_margin, self.tax_hold)
        picks = sc[: self.top]
        slot_w = 1.0 / self.top
        hurdle = self._hurdle(ctx)
        if self.abs_on == "first":
            t0 = self.res(ctx, self.risky[0], self.abs_mom)
            ok_all = t0 is not None and self._passes(ctx, t0, hurdle)
        w, to_safe = {}, 1.0 - slot_w * len(picks)
        for _, t, _ in picks:
            ok = ok_all if self.abs_on == "first" else self._passes(ctx, t, hurdle)
            if ok:
                _add(w, t, slot_w)
            else:
                to_safe += slot_w
        for t, x in self.safe_alloc(ctx, self.safe, self.safe_select, self.safe_mom,
                                    to_safe, self.safe_n).items():
            _add(w, t, x)
        return w


# --------------------------------------------------------------------------
# trend-filtered sleeves (Faber GTAA / Ivy, Robust Asset Allocation style)
# --------------------------------------------------------------------------
class TrendSleeves(_Base):
    """Each sleeve keeps its weight while its trend filter is on, otherwise the
    weight goes to `cash` (a slot, or None = engine cash at 0%).

    filter     spec; "on" when value > 0 (or > T-bills if filter_ref="^IRX")
    filter2    optional second spec (RAA: SMA + time-series momentum);
               combine "both" | "either" | "avg" (weight x share of filters on)
    rank/top   GTAA AGG-k: keep the `top` sleeves by `rank` spec (equal weight
               1/top each), then apply the filter to each.
    unfiltered slots that are always held at full weight.
    """

    def __init__(self, sleeves, filter="sma10", cash=None, filter_ref="zero",
                 filter2=None, filter2_ref="^IRX", combine="both", rank=None,
                 top=None, unfiltered=(), anchor="cal"):
        self.sleeves = dict(sleeves) if isinstance(sleeves, dict) else {s: 1.0 for s in sleeves}
        tot = sum(self.sleeves.values())
        self.sleeves = {k: v / tot for k, v in self.sleeves.items()}
        self.filter = filter
        self.cash = cash
        self.filter_ref = filter_ref
        self.filter2 = filter2
        self.filter2_ref = filter2_ref
        self.combine = combine
        self.rank = rank
        self.top = top
        self.unfiltered = set(unfiltered or ())
        self.anchor = anchor

    def _on(self, ctx, t, spec, ref):
        v = self.m(ctx, t, spec)
        if v is None:
            return None
        h = tbill(ctx, spec) if ref == "^IRX" else 0.0
        return v > h

    def _frac(self, ctx, t, slot):
        if slot in self.unfiltered:
            return 1.0
        a = self._on(ctx, t, self.filter, self.filter_ref)
        if a is None:
            return 0.0
        if not self.filter2:
            return 1.0 if a else 0.0
        b = self._on(ctx, t, self.filter2, self.filter2_ref)
        b = bool(b)
        if self.combine == "both":
            return 1.0 if (a and b) else 0.0
        if self.combine == "either":
            return 1.0 if (a or b) else 0.0
        return (int(a) + int(b)) / 2.0

    def weights(self, ctx, rebalance_day):
        w, to_cash = {}, 0.0
        if self.top:
            slots = list(self.sleeves)
            sc = self.scored(ctx, slots, self.rank or "avg1_3_6_12")
            picks = sc[: self.top]
            sw = 1.0 / self.top
            to_cash += sw * (self.top - len(picks))
            for _, t, i in picks:
                f = self._frac(ctx, t, slots[i])
                _add(w, t, sw * f)
                to_cash += sw * (1.0 - f)
        else:
            for slot, sw in self.sleeves.items():
                t = self.res(ctx, slot, self.filter)
                if t is None:
                    to_cash += sw
                    continue
                f = self._frac(ctx, t, slot)
                _add(w, t, sw * f)
                to_cash += sw * (1.0 - f)
        if to_cash > 1e-12 and self.cash:
            c = self.res(ctx, self.cash)
            _add(w, c, to_cash)
        return w


# --------------------------------------------------------------------------
# breadth momentum: VAA and DAA (Keller & Keuning)
# --------------------------------------------------------------------------
class BreadthMomentum(_Base):
    """CF = min(1, bad / B), where `bad` counts canary assets with momentum
    <= 0 (canary None = the risky universe itself: VAA). (1-CF) goes equally
    into the top `top` risky assets by momentum (only those with momentum > 0
    if risky_abs), CF into the best `cash_top` of the cash universe."""

    def __init__(self, risky, cash, canary=None, B=1, top=1, mom="13612w",
                 canary_mom=None, cash_mom=None, cash_top=1, risky_abs=False,
                 cash_select="best", rel_margin=0.0, tax_hold=False, anchor="cal"):
        self.rel_margin = rel_margin
        self.tax_hold = tax_hold
        self.risky = list(risky)
        self.cash = [cash] if isinstance(cash, str) else list(cash)
        self.canary = list(canary) if canary else None
        self.B = float(B)
        self.top = top
        self.mom = mom
        self.canary_mom = canary_mom or mom
        self.cash_mom = cash_mom or mom
        self.cash_top = cash_top
        self.risky_abs = risky_abs
        self.cash_select = cash_select
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        can = self.canary if self.canary is not None else self.risky
        bad = 0
        for s in can:
            t = self.res(ctx, s, self.canary_mom)
            if t is None:
                continue                      # not available yet: no information
            v = self.m(ctx, t, self.canary_mom)
            if v is None or v <= 0:
                bad += 1
        cf = min(1.0, bad / self.B) if self.B > 0 else (1.0 if bad else 0.0)
        w = {}
        to_cash = cf
        if cf < 1.0:
            sc = self.scored(ctx, self.risky, self.mom)
            if self.risky_abs:
                sc = [x for x in sc if x[0] > 0]
            sc = self.held_adjust(ctx, sc, self.rel_margin, self.tax_hold)
            picks = sc[: self.top]
            sw = (1.0 - cf) / self.top
            for _, t, _ in picks:
                _add(w, t, sw)
            to_cash += sw * (self.top - len(picks))
        for t, x in self.safe_alloc(ctx, self.cash, self.cash_select, self.cash_mom,
                                    to_cash, self.cash_top).items():
            _add(w, t, x)
        return w


# --------------------------------------------------------------------------
# Protective Asset Allocation (Keller & Keuning 2016)
# --------------------------------------------------------------------------
class ProtectiveAA(_Base):
    """MOM = p0/SMA(L+1 monthly closes) - 1; n = risky assets with MOM > 0;
    bond fraction BF = min(1, (N - n) / (N - a*N/4)); (1-BF) equally in the
    top min(top, n) risky with MOM > 0; BF in the safe asset."""

    def __init__(self, risky, safe, a=2, top=6, L=12, mom=None, safe_select="first",
                 safe_mom=None, anchor="cal"):
        self.risky = list(risky)
        self.safe = [safe] if isinstance(safe, str) else list(safe)
        self.a = a
        self.top = top
        self.mom = mom or f"sma{L + 1}"
        self.safe_select = safe_select
        self.safe_mom = safe_mom or self.mom
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        sc = self.scored(ctx, self.risky, self.mom)
        N = len(sc)
        good = [x for x in sc if x[0] > 0]
        n = len(good)
        if N == 0:
            bf = 1.0
        else:
            n1 = self.a * N / 4.0
            bf = 1.0 if N - n1 <= 0 and n < N else min(1.0, max(0.0, (N - n) / max(N - n1, 1e-9)))
        w = {}
        picks = good[: min(self.top, n)]
        if picks and bf < 1.0:
            for _, t, _ in picks:
                _add(w, t, (1.0 - bf) / len(picks))
        else:
            bf = 1.0
        for t, x in self.safe_alloc(ctx, self.safe, self.safe_select, self.safe_mom, bf).items():
            _add(w, t, x)
        return w


# --------------------------------------------------------------------------
# Bold Asset Allocation (Keller 2022)
# --------------------------------------------------------------------------
class BoldAA(_Base):
    """Canary (13612W): if any canary <= 0 (more than `B`-1 of them), go
    defensive. Offensive: top `top_off` by relative momentum (SMA(12) ratio).
    Defensive: top `top_def` by the same; any whose momentum is below the
    cash floor's (BIL) is replaced by the cash floor."""

    def __init__(self, offensive, defensive, canary, top_off=6, top_def=3,
                 off_mom="sma13", def_mom="sma13", canary_mom="13612w",
                 cash_floor="BIL", B=1, anchor="cal"):
        self.off = list(offensive)
        self.dfn = list(defensive)
        self.canary = list(canary)
        self.top_off = top_off
        self.top_def = top_def
        self.off_mom = off_mom
        self.def_mom = def_mom
        self.canary_mom = canary_mom
        self.cash_floor = cash_floor
        self.B = B
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        bad = 0
        for s in self.canary:
            t = self.res(ctx, s, self.canary_mom)
            if t is None:
                continue
            v = self.m(ctx, t, self.canary_mom)
            if v is None or v <= 0:
                bad += 1
        w = {}
        if bad < self.B:
            sc = self.scored(ctx, self.off, self.off_mom)[: self.top_off]
            for _, t, _ in sc:
                _add(w, t, 1.0 / max(1, len(sc)))
            return w
        sc = self.scored(ctx, self.dfn, self.def_mom)[: self.top_def]
        cf = self.res(ctx, self.cash_floor, self.def_mom) if self.cash_floor else None
        cfv = self.m(ctx, cf, self.def_mom) if cf else None
        for v, t, _ in sc:
            if cf is not None and cfv is not None and v < cfv:
                _add(w, cf, 1.0 / self.top_def)
            else:
                _add(w, t, 1.0 / self.top_def)
        short = self.top_def - len(sc)
        if short > 0 and cf:
            _add(w, cf, short / self.top_def)
        return w


# --------------------------------------------------------------------------
# Hybrid Asset Allocation (Keller 2023)
# --------------------------------------------------------------------------
class HybridAA(_Base):
    """Canary TIP (13612U): if <= 0 hold 100% the best of the cash universe
    (BIL/IEF). Else the top `top` offensive by 13612U, each one with
    momentum <= 0 replaced by the best cash asset."""

    def __init__(self, offensive, cash, canary="TIP", top=4, mom="13612u",
                 canary_mom=None, cash_select="best", rel_margin=0.0, tax_hold=False,
                 anchor="cal"):
        self.rel_margin = rel_margin
        self.tax_hold = tax_hold
        self.off = list(offensive)
        self.cash = [cash] if isinstance(cash, str) else list(cash)
        self.canary = canary if isinstance(canary, list) else [canary]
        self.top = top
        self.mom = mom
        self.canary_mom = canary_mom or mom
        self.cash_select = cash_select
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        risk_on = True
        for s in self.canary:
            t = self.res(ctx, s, self.canary_mom)
            if t is None:
                continue
            v = self.m(ctx, t, self.canary_mom)
            if v is None or v <= 0:
                risk_on = False
        w, to_cash = {}, 0.0
        if not risk_on:
            to_cash = 1.0
        else:
            sc = self.held_adjust(ctx, self.scored(ctx, self.off, self.mom), self.rel_margin,
                                  self.tax_hold)[: self.top]
            sw = 1.0 / self.top
            to_cash += sw * (self.top - len(sc))
            for v, t, _ in sc:
                if v > 0:
                    _add(w, t, sw)
                else:
                    to_cash += sw
        for t, x in self.safe_alloc(ctx, self.cash, self.cash_select, self.mom, to_cash).items():
            _add(w, t, x)
        return w


# --------------------------------------------------------------------------
# Generalised Protective Momentum / Elastic AA (Keller)
# --------------------------------------------------------------------------
def _ew_corr(ctx, tickers, n):
    """Correlation of each ticker's daily returns with the equal-weight
    average of all of them over the last n days."""
    R = []
    keep = []
    for t in tickers:
        r = daily_returns(ctx, t, n)
        if r is None:
            continue
        R.append(r)
        keep.append(t)
    if len(R) < 2:
        return {t: 0.0 for t in keep}, {}
    R = np.vstack(R)
    ew = R.mean(axis=0)
    out = {}
    vol = {}
    for i, t in enumerate(keep):
        a = R[i]
        sa, sb = a.std(), ew.std()
        out[t] = float(np.corrcoef(a, ew)[0, 1]) if sa > 0 and sb > 0 else 0.0
        vol[t] = float(sa * math.sqrt(252))
    return out, vol


class GeneralizedProtective(_Base):
    """Score z = r * (1 - c): r = `mom` (13612U), c = correlation with the
    equal-weight universe over `corr_days`. bad = #(z <= 0); CF = min(1,
    bad / B) with B = N/2 by default; (1-CF)/top into each of the top `top`
    assets with z > 0 (unfilled slots -> cash), CF into the best cash."""

    def __init__(self, risky, cash, top=3, mom="13612u", corr_days=252, B=None,
                 cash_top=1, cash_select="best", cash_mom=None, anchor="cal"):
        self.risky = list(risky)
        self.cash = [cash] if isinstance(cash, str) else list(cash)
        self.top = top
        self.mom = mom
        self.corr_days = corr_days
        self.B = B
        self.cash_top = cash_top
        self.cash_select = cash_select
        self.cash_mom = cash_mom or mom
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        ts = []
        r = {}
        for s in self.risky:
            t = self.res(ctx, s, self.mom)
            if t is None:
                continue
            v = self.m(ctx, t, self.mom)
            if v is None:
                continue
            ts.append(t)
            r[t] = v
        c, _ = _ew_corr(ctx, ts, self.corr_days)
        z = {t: r[t] * (1.0 - c.get(t, 0.0)) for t in ts}
        N = len(z)
        bad = sum(1 for v in z.values() if v <= 0)
        B = self.B if self.B else max(N / 2.0, 1.0)
        cf = min(1.0, bad / B) if N else 1.0
        good = sorted([(v, t) for t, v in z.items() if v > 0], key=lambda x: (-x[0], x[1]))
        picks = good[: self.top]
        w = {}
        sw = (1.0 - cf) / self.top
        for _, t in picks:
            _add(w, t, sw)
        to_cash = cf + sw * (self.top - len(picks))
        for t, x in self.safe_alloc(ctx, self.cash, self.cash_select, self.cash_mom,
                                    to_cash, self.cash_top).items():
            _add(w, t, x)
        return w


class ElasticAA(_Base):
    """EAA (Keller & Butler 2014): z = (r^wR * (1-c)^wC / v^wV)^(wS+eps) for
    r > 0 (else 0), r = 13612U-style excess over T-bills, c = corr with EW
    universe, v = volatility. Crash protection: cash fraction = share of
    assets with r <= 0. Top `top` by z, weighted by z ("elastic")."""

    def __init__(self, risky, cash, top=None, wR=1.0, wC=1.0, wV=0.0, wS=2.0,
                 mom="13612u", corr_days=252, weighting="z", cash_select="best",
                 cash_mom=None, anchor="cal"):
        self.risky = list(risky)
        self.cash = [cash] if isinstance(cash, str) else list(cash)
        self.top = top
        self.wR, self.wC, self.wV, self.wS = wR, wC, wV, wS
        self.mom = mom
        self.corr_days = corr_days
        self.weighting = weighting
        self.cash_select = cash_select
        self.cash_mom = cash_mom or mom
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        ts, r = [], {}
        rf = tbill(ctx, self.mom)
        for s in self.risky:
            t = self.res(ctx, s, self.mom)
            if t is None:
                continue
            v = self.m(ctx, t, self.mom)
            if v is None:
                continue
            ts.append(t)
            r[t] = v - rf
        if not ts:
            return self.safe_alloc(ctx, self.cash, self.cash_select, self.cash_mom, 1.0)
        c, vol = _ew_corr(ctx, ts, self.corr_days)
        N = len(ts)
        top = self.top or max(1, int(round(1 + math.sqrt(N))))
        z = {}
        for t in ts:
            if r[t] <= 0:
                continue
            vv = max(vol.get(t, 0.0), 1e-6)
            base = (r[t] ** self.wR) * (max(1e-9, 1.0 - c.get(t, 0.0)) ** self.wC) / (vv ** self.wV)
            z[t] = base ** (self.wS + 1e-6)
        cf = sum(1 for t in ts if r[t] <= 0) / N
        picks = sorted(z.items(), key=lambda x: (-x[1], x[0]))[:top]
        w = {}
        if picks and cf < 1.0:
            if self.weighting == "z":
                s = sum(v for _, v in picks)
                for t, v in picks:
                    _add(w, t, (1.0 - cf) * v / s)
            else:
                for t, _ in picks:
                    _add(w, t, (1.0 - cf) / len(picks))
        else:
            cf = 1.0
        for t, x in self.safe_alloc(ctx, self.cash, self.cash_select, self.cash_mom, cf).items():
            _add(w, t, x)
        return w


# --------------------------------------------------------------------------
# Flexible Asset Allocation (Keller & van Putten 2012)
# --------------------------------------------------------------------------
class FlexibleAA(_Base):
    """Rank by return R (desc), volatility V (asc), average correlation C
    (asc) over `lb` trading days; L = wR*rank(R) + wV*rank(V) + wC*rank(C);
    hold the `top` lowest L equally; a pick with R <= 0 goes to cash."""

    def __init__(self, risky, cash, top=3, lb=84, wR=1.0, wV=0.5, wC=0.5, anchor="cal"):
        self.risky = list(risky)
        self.cash = cash
        self.top = top
        self.lb = lb
        self.wR, self.wV, self.wC = wR, wV, wC
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        ts, rets = [], []
        for s in self.risky:
            t = self.res(ctx, s, f"d{self.lb}")
            if t is None:
                continue
            r = daily_returns(ctx, t, self.lb)
            if r is None:
                continue
            ts.append(t)
            rets.append(r)
        w = {}
        if not ts:
            c = self.res(ctx, self.cash)
            _add(w, c, 1.0)
            return w
        Rm = np.vstack(rets)
        R = np.prod(1.0 + Rm, axis=1) - 1.0
        V = Rm.std(axis=1)
        if len(ts) > 1:
            C = np.corrcoef(Rm)
            C = np.nan_to_num(C)
            Cavg = (C.sum(axis=1) - 1.0) / (len(ts) - 1)
        else:
            Cavg = np.zeros(1)

        def rank(x, desc):
            order = np.argsort(-x if desc else x, kind="stable")
            rk = np.empty(len(x))
            rk[order] = np.arange(1, len(x) + 1)
            return rk
        L = self.wR * rank(R, True) + self.wV * rank(V, False) + self.wC * rank(Cavg, False)
        order = sorted(range(len(ts)), key=lambda i: (L[i], -R[i]))
        picks = order[: self.top]
        sw = 1.0 / self.top
        to_cash = sw * (self.top - len(picks))
        for i in picks:
            if R[i] > 0:
                _add(w, ts[i], sw)
            else:
                to_cash += sw
        if to_cash > 0:
            c = self.res(ctx, self.cash)
            _add(w, c, to_cash)
        return w


# --------------------------------------------------------------------------
# Composite Dual Momentum (Antonacci)
# --------------------------------------------------------------------------
class CompositeDual(_Base):
    """Equal-weight modules; each holds the better of its assets by `mom`
    if that beats T-bills (abs_ref "^IRX") or zero, else `cash`."""

    def __init__(self, modules, cash, mom="r12", abs_ref="^IRX", module_weights=None,
                 anchor="cal"):
        self.modules = [list(m) for m in modules]
        self.cash = cash
        self.mom = mom
        self.abs_ref = abs_ref
        mw = module_weights or [1.0] * len(self.modules)
        s = float(sum(mw))
        self.mw = [x / s for x in mw]
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        h = tbill(ctx, self.mom) if self.abs_ref == "^IRX" else 0.0
        w, to_cash = {}, 0.0
        for mod, mw in zip(self.modules, self.mw):
            sc = self.scored(ctx, mod, self.mom)
            if sc and sc[0][0] > h:
                _add(w, sc[0][1], mw)
            else:
                to_cash += mw
        if to_cash > 0:
            _add(w, self.res(ctx, self.cash), to_cash)
        return w


# --------------------------------------------------------------------------
# Adaptive Asset Allocation (Butler, Philbrick, Gordillo 2012)
# --------------------------------------------------------------------------
def _minvar_long_only(S, iters=300):
    """Long-only minimum-variance weights by projected gradient descent."""
    n = S.shape[0]
    w = np.full(n, 1.0 / n)
    L = float(np.linalg.eigvalsh(S).max()) or 1.0
    step = 1.0 / (2.0 * L)
    for _ in range(iters):
        g = 2.0 * S @ w
        w = w - step * g
        # project onto the simplex
        u = np.sort(w)[::-1]
        css = np.cumsum(u)
        rho = np.nonzero(u * np.arange(1, n + 1) > (css - 1.0))[0]
        rho = rho[-1] if len(rho) else n - 1
        theta = (css[rho] - 1.0) / (rho + 1.0)
        w = np.maximum(w - theta, 0.0)
    return w / w.sum()


class AdaptiveAA(_Base):
    """Top `top` of the universe by `mom` (default 6-month return), weighted
    by minimum variance (cov over `vol_days`) or inverse volatility. Optional
    absolute filter: picks with momentum <= 0 go to cash."""

    def __init__(self, risky, top=5, mom="r6", weighting="minvar", vol_days=60,
                 abs_filter=False, cash=None, anchor="cal"):
        self.risky = list(risky)
        self.top = top
        self.mom = mom
        self.weighting = weighting
        self.vol_days = vol_days
        self.abs_filter = abs_filter
        self.cash = cash
        self.anchor = anchor

    def weights(self, ctx, rebalance_day):
        sc = self.scored(ctx, self.risky, self.mom)[: self.top]
        ts, rets = [], []
        for v, t, _ in sc:
            r = daily_returns(ctx, t, self.vol_days)
            if r is None:
                continue
            ts.append((v, t))
            rets.append(r)
        w = {}
        if not ts:
            if self.cash:
                _add(w, self.res(ctx, self.cash), 1.0)
            return w
        R = np.vstack(rets)
        if self.weighting == "minvar" and len(ts) > 1:
            S = np.cov(R) + np.eye(len(ts)) * 1e-8
            x = _minvar_long_only(S)
        elif self.weighting == "invvol":
            v = R.std(axis=1)
            v = np.where(v > 0, v, np.nan)
            x = np.nan_to_num(1.0 / v)
            x = x / x.sum() if x.sum() > 0 else np.full(len(ts), 1.0 / len(ts))
        else:
            x = np.full(len(ts), 1.0 / len(ts))
        to_cash = 0.0
        for (v, t), xi in zip(ts, x):
            if self.abs_filter and v <= 0:
                to_cash += xi
            else:
                _add(w, t, float(xi))
        if to_cash > 0 and self.cash:
            _add(w, self.res(ctx, self.cash), to_cash)
        return w


# --------------------------------------------------------------------------
# static mixes with calendar or tolerance-band rebalancing
# --------------------------------------------------------------------------
class StaticMix(_Base):
    """Fixed weights. band = 0: rebalance to target on every rebalance day.
    band > 0: on each check (rebalance days, or every day if check="D"),
    rebalance *everything* back to target only if some asset is more than
    `band` (absolute weight) or `rel_band` (relative) away from target
    (e.g. the Permanent Portfolio's 15/35 rule = band 0.10)."""

    def __init__(self, weights, band=0.0, rel_band=0.0, check="reb", anchor="cal"):
        self.w = dict(weights)
        self.band = band
        self.rel_band = rel_band
        self.daily = (check == "D") and (band > 0 or rel_band > 0)
        self.anchor = anchor
        self._init = False

    def initialize(self, ctx):
        self._init = False

    def _targets(self, ctx):
        live = {}
        for s, x in self.w.items():
            t = self.res(ctx, s)
            if t:
                live[t] = live.get(t, 0.0) + x
        tot = sum(self.w.values())
        s = sum(live.values())
        return {t: tot * x / s for t, x in live.items()} if s > 0 else {}

    def weights(self, ctx, rebalance_day):
        if not rebalance_day and not self.daily:
            return None
        tg = self._targets(ctx)
        if not self._init or (self.band <= 0 and self.rel_band <= 0):
            self._init = True
            return tg
        pv = ctx.portfolio_value
        if pv <= 0:
            return None
        pos = ctx.positions
        cur = {}
        for t, q in pos.items():
            px = ctx.price(t)
            if px:
                cur[t] = q * px / pv
        for t in set(tg) | set(cur):
            a, b = cur.get(t, 0.0), tg.get(t, 0.0)
            if self.band > 0 and abs(a - b) > self.band:
                return tg
            if self.rel_band > 0 and b > 0 and abs(a - b) / b > self.rel_band:
                return tg
        return None


# --------------------------------------------------------------------------
# wrappers: an ensemble of models, and signal confirmation
# --------------------------------------------------------------------------
def _sub(part):
    from ..registry import SIGNALS
    factory = SIGNALS[part["signal"]][0]
    return factory(part.get("params", {}))


class Blend(Signal):
    """Weighted average of several registered signals' targets (a model
    ensemble, or tranches of one model rebalanced on different days via
    `offset`). Each part keeps its own state; a part returning None keeps its
    previous targets. Daily if any part is daily; then it trades only on days
    when some part produced new targets."""

    def __init__(self, parts):
        tot = float(sum(p.get("weight", 1.0) for p in parts))
        self.parts = [(_sub(p), p.get("weight", 1.0) / tot) for p in parts]
        self._last = [None] * len(self.parts)
        self.daily = any(getattr(s, "daily", False) for s, _ in self.parts)

    def initialize(self, ctx):
        for s, _ in self.parts:
            s.initialize(ctx)
        self._last = [None] * len(self.parts)

    def weights(self, ctx, rebalance_day):
        w, changed = {}, False
        for k, (s, x) in enumerate(self.parts):
            sw = None
            if rebalance_day or getattr(s, "daily", False):
                sw = s.weights(ctx, rebalance_day)
            if sw is None:
                sw = self._last[k] or {}
            else:
                changed = True
            self._last[k] = sw
            for t, v in sw.items():
                _add(w, t, v * x)
        if not changed and not rebalance_day:
            return None
        return w


class Offset(Signal):
    """Run the inner signal once a month on the first trading day on or after
    day-of-month `day` (instead of the first trading day of the month), to
    measure rebalance-timing luck. Use with rebalance "M"."""

    daily = True

    def __init__(self, inner, day=15):
        self.inner = _sub(inner)
        self.day = int(day)

    def initialize(self, ctx):
        self.inner.initialize(ctx)
        self._done = None

    def weights(self, ctx, rebalance_day):
        key = (ctx.date.year, ctx.date.month)
        if self._done is None:                 # invest at once on the first day
            self._done = key
            return self.inner.weights(ctx, True)
        if self._done == key or ctx.date.day < self.day:
            return None
        self._done = key
        return self.inner.weights(ctx, True)


class Confirm(Signal):
    """Apply a new target only after the inner signal has asked for (nearly)
    the same target on `n` consecutive rebalance days; until then keep the
    current one. The first target is applied at once."""

    def __init__(self, inner, n=2, tol=0.05):
        self.inner = _sub(inner)
        self.n = n
        self.tol = tol

    def initialize(self, ctx):
        self.inner.initialize(ctx)
        self._cur = None
        self._cand = None
        self._count = 0

    def _same(self, a, b):
        if a is None or b is None:
            return False
        return all(abs(a.get(t, 0.0) - b.get(t, 0.0)) <= self.tol for t in set(a) | set(b))

    def weights(self, ctx, rebalance_day):
        w = self.inner.weights(ctx, rebalance_day)
        if w is None:
            return None
        if self._cur is None or self._same(w, self._cur):
            self._cur = w
            self._cand, self._count = None, 0
            return w
        if self._same(w, self._cand):
            self._count += 1
        else:
            self._cand, self._count = w, 1
        if self._count >= self.n:
            self._cur = w
            self._cand, self._count = None, 0
            return w
        return self._cur


def _wrapper_tickers(p):
    from ..registry import SIGNALS
    parts = p.get("parts") or [p["inner"]]
    out = []
    for part in parts:
        out.extend(SIGNALS[part["signal"]][1](part.get("params", {})))
    return list(dict.fromkeys(out))


# --------------------------------------------------------------------------
# registration
# --------------------------------------------------------------------------
def _mk(cls):
    return lambda p: cls(**p)


register_signal("taa_models.dual", _mk(DualMomentum), tickers_of)
register_signal("taa_models.sleeves", _mk(TrendSleeves), tickers_of)
register_signal("taa_models.breadth", _mk(BreadthMomentum), tickers_of)
register_signal("taa_models.paa", _mk(ProtectiveAA), tickers_of)
register_signal("taa_models.baa", _mk(BoldAA), tickers_of)
register_signal("taa_models.haa", _mk(HybridAA), tickers_of)
register_signal("taa_models.gpm", _mk(GeneralizedProtective), tickers_of)
register_signal("taa_models.eaa", _mk(ElasticAA), tickers_of)
register_signal("taa_models.faa", _mk(FlexibleAA), tickers_of)
register_signal("taa_models.cdm", _mk(CompositeDual), tickers_of)
register_signal("taa_models.aaa", _mk(AdaptiveAA), tickers_of)
register_signal("taa_models.static", _mk(StaticMix), tickers_of)
register_signal("taa_models.blend", _mk(Blend), _wrapper_tickers)
register_signal("taa_models.confirm", _mk(Confirm), _wrapper_tickers)
register_signal("taa_models.offset", _mk(Offset), _wrapper_tickers)
