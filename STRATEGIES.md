# Picker × Timer strategy framework

This project factors equity strategies into two independent decisions and lets
you backtest any combination of them:

- **Picker** — *which* stocks to consider owning (value, momentum, quality, …)
- **Timer** — *when* to be long a name you've picked (MA cross, RSI, breakout, …)

A `Combo` wires one picker to one timer. The picker refreshes its basket on a
rebalance cadence (monthly by default); the timer is evaluated every day, so it
can move in and out of the basket between rebalances. Nothing can see the
future — every decision is made from `ctx.history`, which the engine clips to
the current day.

## The 10 pickers (`strategies/pickers.py`)

| Name | Idea | Data |
|------|------|------|
| `momentum` | Highest trailing 6-month return | price ✅ |
| `relative_strength` | Names beating SPY, ranked by excess (goes defensive when few do) | price ✅ |
| `random` | Random subset — a control baseline | price ✅ |
| `value_pe` | Lowest trailing P/E | snapshot ⚠️ |
| `price_to_book` | Lowest price/book (deep value) | snapshot ⚠️ |
| `small_cap` | Lowest market cap | snapshot ⚠️ |
| `quality_roe` | Highest return on equity | snapshot ⚠️ |
| `growth_revenue` | Fastest revenue growth | snapshot ⚠️ |
| `high_dividend` | Highest dividend yield | snapshot ⚠️ |
| `earnings_surprise` | Biggest recent positive earnings surprise | snapshot ⚠️ |

## The 10 timers (`strategies/timers.py`)

| Name | Idea |
|------|------|
| `buy_hold` | Always long — the timing baseline |
| `ma_cross` | Long while 50-day SMA > 200-day SMA |
| `rsi` | Enter when RSI < 30, exit when RSI > 70 |
| `macd` | Long while MACD line > signal line |
| `bollinger` | Buy the lower band, sell the upper band |
| `momentum12` | Long only names up over the trailing 12 months |
| `dual_momentum` | Long only if up *and* beating SPY over the lookback |
| `turtle` | Buy 52-week-high breakouts, exit on the lower channel |
| `vol_reversion` | Buy after a realized-vol spike, betting it reverts |
| `trend_stop` | Trend-follow above the 200-day MA, hard stop at −8% |

## ⚠️ The fundamentals caveat (read this)

Your price data is OHLCV only. The seven fundamental pickers read a **current
snapshot** from `data/fundamentals.csv`, produced by:

```bash
python fetch_fundamentals.py            # all tickers (slow; throttled)
python fetch_fundamentals.py --limit 50 # quick smoke test
```

yfinance only exposes *today's* P/E, ROE, etc. — not what they were in 2014.
Driving an old buy decision with a today-value is **look-ahead bias** on top of
**survivorship bias** (only today's survivors even have a row). So:

- Fundamental-picker results are only trustworthy over a **recent window** near
  the snapshot date.
- For honest **long-history** studies, use `--price-only` (momentum / relative
  strength / random), which need no snapshot and are valid over any period.
- Real point-in-time fundamentals require a paid vendor (Sharadar/Nasdaq Data
  Link, Polygon, Compustat, …).

## Running the grid

```bash
# Honest long-history sweep (price-only pickers, no fundamentals needed):
python grid_combos.py --price-only --start 2010-01-01

# All 100 combos on a recent window (needs data/fundamentals.csv):
python grid_combos.py --start 2022-01-01 --top-n 15

# A focused pairing study:
python grid_combos.py --pickers momentum value_pe --timers turtle rsi
```

The runner prints the top combos by Sharpe, average Sharpe per picker and per
timer, a picker×timer Sharpe matrix, and how many combos beat SPY buy-and-hold.
It writes the full table to `results/combo_grid.csv`. Default cost is 5 bps per
trade (`--commission-pct`); add `--slippage-pct 0.0005` for spread-crossing
slippage. Sort with `--sort-by {sharpe,cagr,net_cagr,excess_cagr,total_return}`.

## Net-of-everything: costs, slippage, and taxes

The real goal is to beat the S&P **net of taxes and costs**, so the engine
models the whole chain, not just gross return:

- **Commission** — `--commission-pct` (fraction of trade value) and/or a
  per-share fee. Folded into each tax lot's cost basis.
- **Slippage** — `--slippage-pct`. Buys fill *above* the close, sells *below*,
  crossing the spread. Also folded into the lots.
- **Capital-gains tax** — `--tax` turns on the tax engine (`backtester/tax.py`):
  - FIFO tax lots per ticker; cost basis already net of commission + slippage.
  - **Short-term** gains (held ≤ `--st-rate` threshold of 365 days, taxed
    `--st-rate`, default 35%) vs **long-term** (`--lt-rate`, default 15%). So a
    high-turnover combo realizes short-term gains constantly while buy-and-hold
    *defers* — that deferral is the S&P's structural head start for a taxable
    investor, and the engine now captures it.
  - Taxes are paid **annually** out of cash (so the drag compounds); net losses
    **carry forward** and offset short-term gains first.
  - A **terminal liquidation tax** settles the final partial year plus the tax
    on all remaining unrealized gains, so a churn-heavy strategy and a
    defer-forever buy-and-hold are comparable on a fully after-tax basis.
    `Result` exposes both pre-tax (`cagr`, `total_return`) and after-tax
    (`after_tax_cagr`, `after_tax_total_return`, `total_tax`) metrics.

  Documented simplifications (all in `tax.py`): no wash-sale rule, no
  $3,000/yr loss-vs-ordinary-income offset, no state tax or 3.8% NIIT, and
  dividends ride in as price appreciation (total-return prices) so they're
  taxed as gains rather than annual income — a break that hits every strategy
  *and* the SPY benchmark, so it largely cancels in the comparison.

```bash
# Full net-of-everything sweep, survivorship-aware, sorted by after-tax CAGR:
python grid_combos.py --start 2000-01-01 --universe sp500-pit --price-only \
    --tax --slippage-pct 0.0005 --sort-by net_cagr
```

## Validating an edge: `walkforward.py`

Sweeping 100 combos and crowning the top number is p-hacking — with that many
tries the "winner" is partly luck. `walkforward.py` runs every combo *once*
over the full span (net of commission + slippage + tax, `sp500-pit` by
default), captures each equity curve, then slices them two honest ways:

- **holdout** — split at `--split`, rank combos by their **train**-window
  return, then judge those same combos on the **untouched test** window.
  Reports rank persistence (Spearman train-vs-test; ≈0 ⇒ in-sample rank is
  noise), how many top-10 combos beat SPY out-of-sample, and the single
  non-cherry-picked "pick the train winner, judge once" result.
- **walkforward** — roll through time: each step pick the combo with the best
  trailing `--train-years` return, earn the next `--step-years`
  out-of-sample, chain those OOS chunks into one track record vs SPY. This
  simulates actually running the thing — every decision uses only past data.

```bash
python walkforward.py holdout --split 2016-01-01 --price-only
python walkforward.py walkforward --train-years 5 --step-years 1 --price-only
```

Caveat: the walk-forward "switch to this year's pick" step ignores the tax
cost of switching baskets between windows, so it slightly flatters the
adaptive strategy — noted in the module docstring, not fatal.

## Survivorship: `--universe sp500-pit`

By default the universe is every ticker with data — which is **today's S&P 500
survivors**, a strong upward bias (the winners are over-represented; the dead
companies are missing entirely). Pass `--universe sp500-pit` to restrict each
day's *selectable* names to the stocks that were **actually in the S&P 500 on
that date** (from `data/sp500_constituents.csv`, point-in-time membership back
to 1996). A position can still be *sold* after its name leaves the index; it
just can't be *bought* outside its real membership window.

```bash
python grid_combos.py --start 2000-01-01 --universe sp500-pit --price-only
```

Effect is large and real: over 2000–2026, momentum × buy&hold drops from
34.8% CAGR / 1.20 Sharpe (biased) to 13.4% / 0.63 (corrected) — most of that
"alpha" was membership look-ahead (e.g. buying TSLA in 2013, years before it
joined the index).

**This is only a partial correction.** It removes membership look-ahead but
cannot resurrect delisted companies (Lehman, Enron, GGP, …) — free data no
longer has their prices, and some symbols were reused by unrelated firms. So
even `sp500-pit` results stay optimistic. A full correction needs a paid
point-in-time dataset (CRSP / Sharadar / Norgate) with delisted prices; the
membership filter is the hook such data would plug into.

## Running a single combo in code

```python
from backtester import Backtest, load_prices, Combo, TaxPolicy
from strategies.pickers import MomentumPicker
from strategies.timers import TurtleBreakoutTimer

prices = load_prices(start="2015-01-01")
combo = Combo(MomentumPicker(lookback=126), TurtleBreakoutTimer(), top_n=15)
res = Backtest(
    combo, prices, cash=100_000,
    commission_pct=0.0005, slippage_pct=0.0005,
    tax_policy=TaxPolicy(short_term_rate=0.35, long_term_rate=0.15),
).run()
res.summary()   # prints pre-tax AND after-tax return / CAGR / total tax
```
