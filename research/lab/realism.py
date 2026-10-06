"""Stricter-than-the-site after-tax accounting for finalists.

The engine (and therefore the website) makes simplifications that are fine for
comparing equity strategies with each other but can flatter some designs:

1. Distributions. Prices are total-return, so dividends and bond interest
   compound inside the price and are taxed only when the position is sold,
   as a capital gain. Reality taxes them every year:
     * US / international equity dividends: qualified -> long-term rate;
     * REIT distributions: mostly ordinary (20% QBI deduction on the federal part);
     * bond interest: ordinary; Treasury interest is exempt from CA state tax;
     * national muni interest: federally exempt, CA-taxable;
     * leveraged / inverse ETF distributions: ordinary (collateral interest).
   Reinvested distributions also raise the cost basis, which lowers later
   capital-gains tax -- credited here at the long-term rate.
2. Collectibles. Physically backed gold/silver ETFs (GLD, IAU, SLV, GLDM) are
   taxed as collectibles: long-term gains at up to 28% federal instead of 15/20%.

`adjusted(cfg, regime, start, end)` reruns the exact strategy, records its
daily holdings, and returns its after-tax CAGR under both accountings, for the
strategy and for SPY over the same window, so the *excess* can be compared.
NONE (tax-deferred account) needs no adjustment.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from . import core, data, registry
from .core import Gate, liquidation_value

DIVS = Path(__file__).resolve().parent / "divs"

TREASURY = {"SHY", "IEF", "TLT", "BIL", "SHV", "SGOV", "GOVT", "VGSH", "VGIT", "VGLT", "EDV",
            "ZROZ", "SCHO", "SCHR", "TLH", "IEI", "TIP", "STIP", "VFISX", "VFITX", "VUSTX",
            "VIPSX", "FGOVX", "FSTGX", "UBT", "TMF"}
BONDS = {"AGG", "BND", "LQD", "HYG", "JNK", "EMB", "MBB", "FLOT", "BSV", "BIV", "BLV", "VCIT",
         "VCSH", "VBMFX", "VWESX", "VWEHX", "VFIIX", "VBISX", "VBIIX"}
MUNI = {"MUB", "VTEB", "VWSTX", "VWITX", "VWLTX"}
REIT = {"VNQ", "IYR", "RWR", "ICF", "XLRE", "VGSIX", "VNQI", "URE"}
COLLECTIBLE = {"GLD", "IAU", "SLV", "GLDM"}
LEVERED = {"SSO", "UPRO", "SPXL", "QLD", "TQQQ", "ROM", "UWM", "SAA", "MVV", "DDM", "UBT",
           "TMF", "UGL", "TNA", "URTY", "SPUU", "USD", "UYG", "DIG", "URE", "SH", "PSQ", "SDS",
           "DOG", "RWM"}
STATE_CA = 0.093
NIIT = 0.038


def rates(regime: str) -> dict:
    """Tax rate per distribution character, plus the collectibles LT rate."""
    if regime == "CA":
        return {"qualified": 0.281, "ordinary": 0.481, "treasury": 0.35 + NIIT,
                "reit": 0.8 * 0.35 + NIIT + STATE_CA, "muni": STATE_CA,
                "lt": 0.281, "collectible_lt": 0.28 + NIIT + STATE_CA}
    if regime == "FED":
        return {"qualified": 0.15, "ordinary": 0.35, "treasury": 0.35, "reit": 0.8 * 0.35,
                "muni": 0.0, "lt": 0.15, "collectible_lt": 0.28}
    raise ValueError("no adjustment for tax-deferred accounts")


def character(t: str) -> str:
    if t in TREASURY:
        return "treasury"
    if t in BONDS:
        return "ordinary"
    if t in MUNI:
        return "muni"
    if t in REIT:
        return "reit"
    if t in LEVERED:
        return "ordinary"
    if t.startswith("SYN_"):
        return "ordinary"
    return "qualified"


@lru_cache(maxsize=None)
def dist_yield(t: str) -> pd.Series:
    """Daily distribution yield on ex-dates: (dividend + capital-gain
    distribution) / previous unadjusted close. Empty if unknown."""
    p = DIVS / f"{t}.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    d = pd.read_csv(p, parse_dates=["Date"], index_col="Date").sort_index()
    amt = d.get("Dividend", 0.0)
    if "CapGain" in d:
        amt = amt + d["CapGain"].fillna(0.0)
    prev = d["Close"].shift(1)
    y = (amt / prev).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return y[y > 0]


class RecordingGate(Gate):
    """Gate that also records each day's position values by ticker."""

    def initialize(self, ctx) -> None:
        super().initialize(ctx)
        self.pos_values: dict = {}
        self.equity: dict = {}

    def on_day(self, ctx) -> None:
        super().on_day(ctx)
        if ctx.date < self.start:
            return
        eng = ctx._engine
        px = eng.current_prices()
        vals = {t: q * px[t] for t, q in eng.portfolio.positions.items() if t in px}
        self.pos_values[ctx.date] = vals
        self.equity[ctx.date] = eng.portfolio.cash + sum(vals.values())


def record(cfg: dict, regime: str, start: str, end: str | None = None,
           comm=core.COMMISSION, slip=core.SLIPPAGE):
    registry.load_families()
    kind = registry.kind_of(cfg)
    mkt = data.market(kind.tickers(cfg), universe=kind.universe(cfg))
    pol = core.policy_for(regime)
    end = end or core._ts(core.PROTOCOLS["full"].checkpoints[-1])
    gate = RecordingGate(kind.build(cfg), start, [pd.Timestamp(end)], pol)
    res = core.run_backtest(gate, mkt, pol, comm, slip)
    return gate, res


def _fifo_collectible_gains(trades: pd.DataFrame, end_day, end_prices: dict, comm_pct: float):
    """Long-term gains (realized + unrealized at end) on collectible tickers,
    by FIFO lots exactly as the engine books them."""
    lots: dict = {}
    lt_gain = 0.0
    if trades is None or trades.empty:
        return 0.0
    for d, tr in trades.sort_index().iterrows():
        t = tr["ticker"]
        if t not in COLLECTIBLE:
            continue
        sh = float(tr["shares"])
        per_comm = float(tr["commission"]) / sh if sh else 0.0
        if tr["side"] == "BUY":
            lots.setdefault(t, []).append([d, sh, float(tr["price"]) + per_comm])
        else:
            rem = sh
            proceeds = float(tr["price"]) - per_comm
            q = lots.get(t, [])
            while rem > 1e-12 and q:
                lot = q[0]
                take = min(rem, lot[1])
                if (d - lot[0]).days > 365:
                    lt_gain += (proceeds - lot[2]) * take
                lot[1] -= take
                rem -= take
                if lot[1] <= 1e-12:
                    q.pop(0)
    for t, q in lots.items():
        px = end_prices.get(t)
        if px is None:
            continue
        for d, sh, cost in q:
            if (end_day - d).days > 365:
                lt_gain += (px - cost) * sh
    return max(lt_gain, 0.0)


def _adjust_path(gate: RecordingGate, res, regime: str) -> dict:
    """Replay the engine's daily wealth path, charging each year's distribution
    tax in January (like the engine's own settlement), crediting reinvested
    distributions' basis at the long-term rate at the end, and surcharging
    long-term gains on collectibles."""
    r = rates(regime)
    eq = pd.Series(gate.equity).sort_index()
    pv = gate.pos_values
    days = eq.index
    if len(days) < 2:
        return {}
    yields: dict = {}
    W = float(eq.iloc[0])        # real wealth
    k = 1.0                      # real wealth / engine wealth
    reinvested = 0.0             # distributions reinvested (real $) -> basis credit
    owed = 0.0
    year = days[0].year
    dist_total = paid_total = 0.0
    for i in range(1, len(days)):
        d, d0 = days[i], days[i - 1]
        if d.year != year:                       # settle last year's distribution tax
            W -= owed
            paid_total += owed
            owed = 0.0
            year = d.year
            k = W / float(eq.iloc[i - 1]) if eq.iloc[i - 1] > 0 else k
        e0, e1 = float(eq.iloc[i - 1]), float(eq.iloc[i])
        W *= (e1 / e0) if e0 > 0 else 1.0        # the engine's own daily return
        for t, v in pv.get(d0, {}).items():      # ex-date distributions on yesterday's holdings
            ys = yields.get(t)
            if ys is None:
                ys = yields[t] = dist_yield(t)
            if len(ys) and d in ys.index:
                amt = v * float(ys.loc[d]) * k
                dist_total += amt
                owed += amt * r[character(t)]
                reinvested += amt
        k = W / e1 if e1 > 0 else k
    W -= owed                                    # final partial year
    paid_total += owed
    end_day = days[-1]
    liq, eq_end = gate.values[next(iter(gate.values))][:2] if gate.values else (eq.iloc[-1], eq.iloc[-1])
    scale = W / eq_end if eq_end > 0 else 1.0
    terminal_tax = eq_end - liq
    total_cg_tax = (res.taxes_paid or 0.0) + terminal_tax
    credit = min(r["lt"] * reinvested, max(total_cg_tax, 0.0) * scale)
    coll_tax = 0.0
    if not res.trades.empty and res.trades["ticker"].isin(COLLECTIBLE).any():
        held: dict = {}
        for _, tr in res.trades.sort_index().iterrows():
            held[tr["ticker"]] = held.get(tr["ticker"], 0.0) + (
                tr["shares"] if tr["side"] == "BUY" else -tr["shares"])
        mk = {t: v / held[t] for t, v in pv.get(end_day, {}).items() if held.get(t, 0) > 1e-9}
        coll_gain = _fifo_collectible_gains(res.trades, end_day, mk, 0.0)
        coll_tax = coll_gain * (r["collectible_lt"] - r["lt"]) * scale
    real_final = W - terminal_tax * scale + credit - coll_tax
    yrs = (end_day - days[0]).days / 365.25
    return {
        "engine_cagr": (liq / core.CASH) ** (1 / yrs) - 1,
        "real_cagr": (real_final / core.CASH) ** (1 / yrs) - 1 if real_final > 0 else -1.0,
        "dist_income": dist_total, "dist_tax_paid": paid_total, "basis_credit": credit,
        "collectible_extra_tax": coll_tax, "years": yrs,
    }


def adjusted(cfg: dict, regime: str, start: str, end: str | None = None) -> dict:
    """Engine vs stricter after-tax CAGR for the strategy and for SPY."""
    if core.REGIMES[regime] is None:
        raise ValueError("NONE regime needs no adjustment")
    g, res = record(cfg, regime, start, end)
    s = _adjust_path(g, res, regime)
    gb, resb = record({"kind": "buyhold", "weights": {"SPY": 1.0}}, regime, start, end)
    b = _adjust_path(gb, resb, regime)
    return {
        "strategy": s, "spy": b,
        "engine_excess": s["engine_cagr"] - b["engine_cagr"],
        "real_excess": s["real_cagr"] - b["real_cagr"],
    }
