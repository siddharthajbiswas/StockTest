"""Tax-managed momentum: a strategy built around the tax bill rather than around
the signal.

WHY THIS EXISTS
---------------
For a taxable California investor, the S&P 500's structural advantage is not its
returns — it is that buy-and-hold never realizes a gain, so nothing is ever taxed
until the end. Measured on this engine over 1999-2026, an ordinary monthly or
quarterly rotation gives that advantage away completely:

    strategy                          pre-tax     after CA tax     tax drag
    SPY buy & hold                      8.52%           7.38%        1.14 pp
    sector momentum, top 5, monthly     8.72%           4.86%        3.85 pp
    global equity momentum, monthly    10.98%           7.68%        3.30 pp

The active rules earn a real pre-tax edge of +0.2 to +2.5 pp and then hand over
3 to 4 pp to the tax authority. Trading *is* the problem: every rebalance turns
an untaxed unrealized gain into a taxed realized one, and the tax is paid in cash
that then stops compounding.

THE RULE
--------
Keep the signal, delete the tax. Every rebalance, the portfolio wants to be
equal-weighted across the `top_n` highest-momentum names on the menu, but sales
are rationed by a **realized-gain budget**:

  * Selling at a LOSS is always allowed — it banks a deduction and refills
    the budget (tax-loss harvesting).
  * Selling at a GAIN is allowed only while the year's *net* realized gain stays
    under `gain_budget` (a fraction of portfolio value; 0.0 = never end a year
    with a net realized gain). Gains are taken smallest-first and long-term
    before short-term, and the final sale is part-filled to land exactly on the
    budget.
  * A name sold at a loss cannot be repurchased for `wash_days` (default 31),
    so the harvested loss is not disallowed by the wash-sale rule. The cash goes
    to the next name on the list instead.

The emergent behaviour is the oldest advice in trading — let winners run, cut
losers — except here it is forced by the tax code rather than by conviction.
A winner is never sold merely because it drifted above its target weight, so the
gain stays unrealized and compounds; a loser is sold immediately and the proceeds
are recycled into whatever currently leads. Turnover collapses from ~300%/yr to
under 10%/yr, and the tax drag with it.

WHAT IT IS AND IS NOT
---------------------
This is not a better return forecast. Run without taxes it is worth roughly
nothing versus SPY (+0.07 pp). Its entire edge is structural: it lets a momentum
signal reach the after-tax bottom line instead of being eaten on the way there.
Two controls back that up, both in the project's research notes:

  * Replace the momentum ranking with a *random* ranking and keep everything
    else — the after-tax result collapses to SPY's (7.3-7.8% across 40 seeds).
    So the tax rule alone is not the edge.
  * Keep momentum and drop the tax rule — the after-tax result falls below SPY.
    So the signal alone is not the edge either. It is the combination.

The menu matters. It is deliberately restricted to large index ETFs with
continuous, survivorship-free histories, because the per-stock CSVs in data/
only contain companies that still exist today: an equal-weight buy-and-hold of
this repo's point-in-time S&P universe beats the real equal-weight S&P fund
(RSP) by 1.3-2.2 pp/yr, which is bias, not skill. On ETFs there is no such gap.
"""

from __future__ import annotations

from backtester import TaxManagedCombo
from strategies.pickers import MomentumPicker
from strategies.timers import BuyHoldTimer

# Large, still-listed index ETFs. Each becomes eligible on its own inception
# date, so the menu grows through time exactly as it did in reality. Nothing is
# on this list because it performed well — these are simply the big, obvious
# funds a retail investor could have bought on the day the backtest says so.
DEFAULT_MENU = [
    # broad market / style / region
    "SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP",
    # the eleven GICS sectors
    "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
]

# 12-1 momentum: the trailing year, excluding the most recent month. Skipping
# the latest month is the standard academic construction — it sidesteps the
# well-documented one-month reversal effect.
LOOKBACK = 252
SKIP = 21


def TaxManagedMomentum(
    menu: list[str] | None = None,
    top_n: int = 5,
    lookback: int = LOOKBACK,
    skip: int = SKIP,
    rebalance: str = "Q",
    gain_budget: float = 0.01,
    wash_days: int = 31,
) -> TaxManagedCombo:
    """The recommended configuration, as a ready-to-run strategy.

    It is nothing more than `TaxManagedCombo` wired to the momentum picker and
    the buy-and-hold timer over `DEFAULT_MENU`, so every knob the engine exposes
    is still reachable. Pass `menu="universe"` to rank the engine's selectable
    universe instead of the ETF menu — with a point-in-time membership filter
    that makes this a single-stock picker, subject to the survivorship warning
    above.
    """
    return TaxManagedCombo(
        MomentumPicker(lookback=lookback, skip=skip),
        BuyHoldTimer(),
        top_n=top_n,
        rebalance=rebalance,
        menu=None if menu == "universe" else (menu or DEFAULT_MENU),
        gain_budget=gain_budget,
        wash_days=wash_days,
    )


# Default instance so `run_backtest.py --strategy strategies/tax_managed.py`
# runs the recommended configuration with no extra arguments.
strategy = TaxManagedMomentum()
