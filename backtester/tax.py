"""Capital-gains tax accounting for the backtester.

The goal this project is chasing — beat the S&P *net of taxes* — can't even be
scored without this. The core facts it models:

  * A sale realizes a gain/loss = proceeds - cost basis (both net of commission
    and slippage, since those are folded into the lot prices).
  * Gains are **short-term** (position held <= 1 year, taxed as ordinary income,
    ~35%) or **long-term** (held > 1 year, ~15-20%). High-turnover strategies
    realize short-term gains constantly; buy-and-hold defers tax indefinitely.
    That deferral is the S&P's structural head start for a taxable investor.
  * Taxes are paid annually (the following-year settlement is approximated as a
    January payment), so the drag compounds. Net losses carry forward.

Deliberately NOT modeled (documented simplifications):
  * Wash-sale rule (disallowed losses on repurchase within 30 days).
  * The $3,000/yr capital-loss offset against ordinary income.
  * State taxes and the 3.8% NIIT (fold into the rates if you want them).
  * Dividend taxes: prices are total-return adjusted (auto_adjust), so dividends
    show up as price appreciation and are taxed as capital gains here rather
    than as annual income — a small break that applies to every strategy AND the
    SPY benchmark, so it largely cancels in the relative comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaxPolicy:
    """Tax rates and the long-term holding threshold."""

    short_term_rate: float = 0.35
    long_term_rate: float = 0.15
    long_term_days: int = 365

    def is_long_term(self, holding_days: int) -> bool:
        return holding_days > self.long_term_days


@dataclass
class Lot:
    """One tax lot: shares bought on a date at a cost basis per share (which
    already includes commission and slippage)."""

    date: object          # pd.Timestamp
    shares: float
    cost_per_share: float


def compute_year_tax(
    net_st: float, net_lt: float, carryforward_loss: float, policy: TaxPolicy
) -> tuple[float, float]:
    """Tax owed for a year, plus the loss carryforward into the next year.

    `net_st` / `net_lt` are the year's net short- and long-term realized gains
    (negative = net loss). `carryforward_loss` is the accumulated unused loss
    from prior years (a non-negative magnitude). Losses are pooled and applied
    against short-term gains first (they're taxed higher, so this is the
    taxpayer-optimal ordering and a close approximation of the IRS netting).
    Returns (tax_owed, new_carryforward_loss).
    """
    pool = carryforward_loss + max(0.0, -net_st) + max(0.0, -net_lt)
    gain_st = max(0.0, net_st)
    gain_lt = max(0.0, net_lt)

    used = min(pool, gain_st)
    gain_st -= used
    pool -= used
    used = min(pool, gain_lt)
    gain_lt -= used
    pool -= used

    tax = gain_st * policy.short_term_rate + gain_lt * policy.long_term_rate
    return tax, pool
