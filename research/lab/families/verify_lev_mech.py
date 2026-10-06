"""verify_lev_mech: helpers for the adversarial audit of the leveraged-trend
finalists (research/lab/results/verify_lev_mech.md).

Registers nothing and patches nothing at import (this module is auto-imported
by every lab process). It only provides pure functions used by the scripts in
research/lab/scratch/verify_lev_mech/:

* replay_taxes(trades, ...): re-books the engine's own trade log FIFO exactly
  as backtester.portfolio does (validated against the engine's taxes_paid and
  terminal_tax), optionally applying the WASH-SALE rule that the engine does
  not model (a loss sale is disallowed to the extent substantially identical
  shares are acquired within 30 days before or after it; the disallowed loss
  is added to the replacement shares' basis and their holding period is
  tacked onto the sold lot's).
* switch_stats(gate): regime switches per year and time in each holding.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

try:
    from backtester.tax import compute_year_tax
except Exception:  # pragma: no cover
    compute_year_tax = None


@dataclass
class _Lot:
    hp_start: pd.Timestamp      # holding-period start (tacked for wash replacements)
    bought: pd.Timestamp        # actual purchase date
    shares: float
    cost: float                 # per share, incl. commission (+ disallowed loss)
    wash_used: float = 0.0      # shares of this lot already used as a wash replacement


def replay_taxes(trades: pd.DataFrame, end_prices: dict, end_day, st_rate: float, lt_rate: float,
                 wash: bool = False, window: int = 30, lt_days: int = 365) -> dict:
    """Realized gains by year, yearly tax (engine netting, carryforward) and the
    terminal liquidation tax, from an engine trade log.

    Returns {"realized": {year: {"st","lt"}}, "tax": {year: tax}, "terminal": x,
             "disallowed": {year: amount}, "n_wash": count}.
    """

    class _P:
        def __init__(self, s, l):
            self.short_term_rate, self.long_term_rate = s, l

    pol = _P(st_rate, lt_rate)
    lots: dict[str, list[_Lot]] = {}
    realized: dict[int, dict[str, float]] = {}
    disallowed: dict[int, float] = {}
    pending: list[list] = []     # [sale_date, ticker, shares_left, loss_per_share, sale_year, held_days]
    n_wash = 0

    def book(year, gain, lt):
        b = realized.setdefault(year, {"st": 0.0, "lt": 0.0})
        b["lt" if lt else "st"] += gain

    def apply_wash(pend, lot, q):
        """Disallow pend's loss on q replacement shares of `lot`."""
        nonlocal n_wash
        sale_date, t, left, lps, yr, held_days, was_lt = pend
        amt = lps * q                                   # positive amount of loss disallowed
        book(yr, amt, was_lt)                           # add the loss back in its year/character
        disallowed[yr] = disallowed.get(yr, 0.0) + amt
        # split the lot: q shares get the higher basis and a tacked holding period
        lst = lots[t]
        i = lst.index(lot)
        rest = lot.shares - q
        new = _Lot(lot.bought - pd.Timedelta(days=held_days), lot.bought, q,
                   lot.cost + lps, lot.wash_used + q)
        if rest > 1e-12:
            lot.shares = rest
            lst.insert(i, new)       # FIFO order among same-day lots is immaterial
        else:
            lst[i] = new
        pend[2] -= q
        n_wash += 1

    tr = trades.sort_index(kind="stable")
    for d, row in tr.iterrows():
        t = row["ticker"]
        sh = float(row["shares"])
        pc = float(row["commission"]) / sh if sh else 0.0
        if row["side"] == "BUY":
            lot = _Lot(d, d, sh, float(row["price"]) + pc)
            lots.setdefault(t, []).append(lot)
            if wash:
                for pend in pending:
                    if pend[1] != t or pend[2] <= 1e-12:
                        continue
                    if (d - pend[0]).days > window:
                        continue
                    q = min(pend[2], lot.shares)
                    if q > 1e-12:
                        apply_wash(pend, lot, q)
                        # after a split the unmatched remainder (if any) is the original object
                        lot = next((x for x in lots[t] if x is lot), None)
                        if lot is None:
                            break
        else:
            proceeds = float(row["price"]) - pc
            rem = sh
            q_lots = lots.get(t, [])
            loss_sh = 0.0
            loss_amt = 0.0
            held_w = 0.0
            lt_loss = 0.0
            while rem > 1e-12 and q_lots:
                lot = q_lots[0]
                take = min(rem, lot.shares)
                gain = (proceeds - lot.cost) * take
                is_lt = (d - lot.hp_start).days > lt_days
                book(d.year, gain, is_lt)
                if gain < 0:
                    loss_sh += take
                    loss_amt += -gain
                    held_w += take * (d - lot.hp_start).days
                    lt_loss += -gain if is_lt else 0.0
                lot.shares -= take
                rem -= take
                if lot.shares <= 1e-12:
                    q_lots.pop(0)
            if wash and loss_sh > 1e-12:
                was_lt = lt_loss > 0.5 * loss_amt
                pend = [d, t, loss_sh, loss_amt / loss_sh, d.year, int(held_w / loss_sh), was_lt]
                # replacement shares bought within `window` days BEFORE the sale and still held
                for lot in list(q_lots):
                    if pend[2] <= 1e-12:
                        break
                    if (d - lot.bought).days <= window and lot.shares - lot.wash_used > 1e-12:
                        q = min(pend[2], lot.shares - lot.wash_used)
                        apply_wash(pend, lot, q)
                pending.append(pend)
                pending = [p for p in pending if (d - p[0]).days <= window and p[2] > 1e-12]

    # yearly tax with the engine's netting and carryforward
    years = sorted(realized)
    last = pd.Timestamp(end_day).year
    tax: dict[int, float] = {}
    carry = 0.0
    for y in years:
        if y >= last:
            continue
        r = realized[y]
        tx, carry = compute_year_tax(r["st"], r["lt"], carry, pol)
        tax[y] = tx
    r = realized.get(last, {"st": 0.0, "lt": 0.0})
    fy, carry2 = compute_year_tax(r["st"], r["lt"], carry, pol)
    st_u = lt_u = 0.0
    for t, q_lots in lots.items():
        px = end_prices.get(t)
        if px is None:
            continue
        for lot in q_lots:
            g = (px - lot.cost) * lot.shares
            if (pd.Timestamp(end_day) - lot.hp_start).days > lt_days:
                lt_u += g
            else:
                st_u += g
    ut, _ = compute_year_tax(st_u, lt_u, carry2, pol)
    return {"realized": realized, "tax": tax, "terminal": fy + ut, "disallowed": disallowed,
            "n_wash": n_wash}


def wash_impact(gate, res, st_rate: float, lt_rate: float) -> dict:
    """First-order effect of the wash-sale rule on terminal after-tax wealth:
    extra tax paid in year y+1 (January, like the engine) compounded at the
    strategy's own growth to the end, plus the change in terminal tax."""
    eq = pd.Series(gate.equity).sort_index()
    end_day = eq.index[-1]
    pv_end = gate.pos_values.get(end_day, {})
    held: dict = {}
    for _, tr in res.trades.sort_index().iterrows():
        held[tr["ticker"]] = held.get(tr["ticker"], 0.0) + (tr["shares"] if tr["side"] == "BUY" else -tr["shares"])
    end_px = {t: v / held[t] for t, v in pv_end.items() if held.get(t, 0) > 1e-9}
    base = replay_taxes(res.trades, end_px, end_day, st_rate, lt_rate, wash=False)
    ws = replay_taxes(res.trades, end_px, end_day, st_rate, lt_rate, wash=True)
    dW = 0.0
    for y in set(base["tax"]) | set(ws["tax"]):
        d_tax = ws["tax"].get(y, 0.0) - base["tax"].get(y, 0.0)
        pay = eq.index[eq.index.searchsorted(pd.Timestamp(f"{y + 1}-01-01"))] if pd.Timestamp(f"{y + 1}-01-01") <= end_day else end_day
        g = float(eq.iloc[-1] / eq.loc[pay]) if eq.loc[pay] > 0 else 1.0
        dW -= d_tax * g
    dW -= ws["terminal"] - base["terminal"]
    liq = next(iter(gate.values.values()))[0] if gate.values else float(eq.iloc[-1]) - base["terminal"]
    yrs = (end_day - eq.index[0]).days / 365.25
    c0 = (liq / 100_000.0) ** (1 / yrs) - 1
    c1 = ((liq + dW) / 100_000.0) ** (1 / yrs) - 1 if liq + dW > 0 else -1.0
    return {"base": base, "wash": ws, "engine_taxes_paid": res.taxes_paid, "engine_terminal": res.terminal_tax,
            "replay_taxes_paid": sum(base["tax"].values()), "replay_terminal": base["terminal"],
            "dW": dW, "liq": liq, "cagr": c0, "cagr_wash": c1, "cagr_cost": c0 - c1, "years": yrs}


def switch_stats(gate) -> dict:
    """Days in each holding, switches per year (change of the largest holding)."""
    days = sorted(gate.pos_values)
    st = []
    for d in days:
        pv = gate.pos_values[d]
        st.append(max(pv, key=pv.get) if pv else "cash")
    s = pd.Series(st, index=pd.DatetimeIndex(days))
    ch = (s != s.shift(1)).iloc[1:]
    yrs = (days[-1] - days[0]).days / 365.25
    by_year = ch.groupby(ch.index.year).sum()
    return {"share": s.value_counts(normalize=True).to_dict(), "switches": int(ch.sum()),
            "per_year": float(ch.sum() / yrs), "max_in_year": int(by_year.max()) if len(by_year) else 0,
            "by_year": {int(k): int(v) for k, v in by_year.items()}, "state": s}


def short_stays(state: pd.Series, risk: str, max_days: int = 30) -> dict:
    """Round trips into `risk` that lasted <= max_days calendar days (whipsaws)."""
    on = state == risk
    runs = []
    start = None
    for d, v in on.items():
        if v and start is None:
            start = d
        elif not v and start is not None:
            runs.append((start, d))
            start = None
    n_short = sum(1 for a, b in runs if (b - a).days <= max_days)
    return {"entries": len(runs), "short_round_trips": n_short}


def nan(x):
    return x is None or (isinstance(x, float) and math.isnan(x))
