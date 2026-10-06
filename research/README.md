# Beating the S&P 500 after California tax — what actually worked

The question: can a stock-picking strategy, run in a **taxable California
account**, beat simply buying and holding the S&P 500 — after capital-gains tax
and trading costs — not just over the last ten years, but across all the history
this repo has and across many different windows?

Answer: **yes, by about 1.25 percentage points a year**, but almost none of that
comes from picking better. It comes from not handing the gains to the tax
authority. Everything below is reproducible with

```bash
.venv/bin/python research/tax_managed_report.py
```

which runs the real `backtester/` engine (not a research shortcut) and writes
`tax_managed_report.json`.

Tax rates throughout: California single filer, ~$300k taxable income, 2025
schedule — **48.1%** short-term (35% federal + 3.8% NIIT + 9.3% CA) and **28.1%**
long-term (15% + 3.8% + 9.3%). Costs: 5bps commission + 5bps slippage per side.

---

## 1. The thing that kills every active strategy

The S&P's real advantage to a taxable investor is not its returns. It is that
buy-and-hold never realizes a gain, so nothing is taxed until the end. Measured
over 1999-04 → 2026-07:

| strategy | pre-tax CAGR | after CA tax | **tax drag** | turnover |
|---|---|---|---|---|
| SPY buy & hold | 8.52% | 7.38% | 1.14 pp | 0% |
| sector momentum, top 5, monthly | 8.72% | 4.86% | **3.85 pp** | 863%/yr |
| sector momentum, top 5, semi-annual | 10.95% | 6.93% | **4.02 pp** | 266%/yr |
| global equity momentum (GEM+QQQ), monthly | 10.98% | 7.68% | **3.30 pp** | 485%/yr |
| SPY / 200-day MA → bonds, monthly | 8.01% | 5.65% | 2.37 pp | 291%/yr |
| 50/50 SPY+QQQ, never rebalanced | 9.81% | 8.60% | 1.20 pp | ~0% |

The active rules do earn a real pre-tax edge — up to +2.5 pp. They then give
away 3-4 pp in tax. **The tax drag is roughly proportional to turnover, and it
is larger than any edge these signals produce.** Every classic tactical rule
tested — 200-day trend following, dual momentum, GEM, sector rotation at any
cadence — loses to SPY after California tax.

So the design constraint is not "find a better signal". It is "realize almost no
gains while still acting on a signal".

## 2. The rule that fixes it

`TaxManagedCombo` (in `backtester/composite.py`) keeps the picker and the timer
and changes only what the portfolio is *allowed to sell*:

- Selling at a **loss** is always allowed — it banks a deduction and refills the
  budget (tax-loss harvesting).
- Selling at a **gain** is allowed only while the year's *net* realized gain
  stays under `gain_budget` × portfolio value. Gains are taken smallest-first,
  long-term before short-term, and the last sale is part-filled to land exactly
  on the budget.
- A name sold at a loss cannot be repurchased for 31 days, so the harvested loss
  is not disallowed as a wash sale. The cash goes to the next name instead.
  (At the shipped quarterly cadence this guard is inert — the next rebalance is
  ~91 days away regardless — and turning it off changes nothing, as the
  parameter table in the report shows. It is there so the rule stays legal at
  monthly or weekly cadence, where it does bind.)

The emergent behaviour is the oldest advice in trading — let winners run, cut
losers — enforced by the tax code rather than by conviction. Turnover falls from
~300%/yr to under 20%/yr, and the tax drag from ~4 pp to ~0.2 pp.

The shipped configuration (`strategies/tax_managed.py`): **12-1 momentum, top 5,
quarterly, 1%/yr gain budget**, ranked over a menu of **22 large index ETFs**.

## 3. Results, in the project's own engine

Full period, 1998-04 → 2026-07 (28.2 years):

| | strategy | SPY buy & hold |
|---|---|---|
| after-tax CAGR | **8.96%** | 7.71% |
| $100,000 becomes | **$1,128,670** | $815,589 |
| max drawdown | −57.6% | −55.2% |
| Sharpe | 0.58 | 0.53 |
| trades | 274 | 1 |

Every window of a given length, stepped one year:

| window length | windows | beat SPY | median excess | worst | best |
|---|---|---|---|---|---|
| 5-year | 24 | 67% | +0.86 | −2.72 | +6.03 |
| 10-year | 19 | 74% | +0.93 | −1.48 | +2.08 |
| 15-year | 14 | 86% | +1.12 | −0.66 | +2.14 |
| 20-year | 9 | **100%** | +1.47 | **+0.74** | +1.63 |

It wins the crisis decades and roughly ties or slightly loses the long bull
decades (2003-13 −0.80, 2010-20 −0.55, 2013-23 −0.79). It does **not** reduce
drawdown; it is slightly worse than SPY there.

## 4. Controls — which half is doing the work

Both halves are necessary, and neither is sufficient:

| | after-tax CAGR | vs SPY |
|---|---|---|
| momentum ranking + tax rule | 8.96% | **+1.25** |
| **random** ranking + tax rule (25 seeds) | 7.29% | −0.42 |
| momentum ranking, **no** tax rule | 6.27% | −1.45 |
| SPY buy & hold | 7.71% | — |

The real strategy beats **100% of 25 random rankings**. So the tax rule alone is
not the edge. And momentum alone is worse than doing nothing. It is the
interaction.

The clearest statement of what this is: at **no tax at all** the strategy beats
SPY by only **+0.30 pp**. It is not a return forecast. It is a tax structure
that lets a mediocre signal survive to the after-tax bottom line.

Because of that, the edge is stable across brackets and costs:

| bracket | short/long | strategy | SPY | excess |
|---|---|---|---|---|
| CA ~$120k | 33.3 / 24.3% | 9.13% | 7.88% | +1.24 |
| CA ~$300k | 48.1 / 28.1% | 8.96% | 7.71% | +1.25 |
| CA ~$700k | 52.1 / 35.1% | 8.57% | 7.38% | +1.19 |
| CA ~$1.5M | 54.1 / 37.1% | 8.45% | 7.26% | +1.18 |

At 35bps+35bps per side (7× the modelled cost) the excess is still +0.89.

## 5. Why the menu is ETFs, not stocks

**This is the most important caveat in the whole exercise.** The per-ticker CSVs
in `data/` only contain companies that still exist today. Companies that went
bankrupt or were acquired are simply absent, so any stock picker drawing on them
is picking from a pool of known survivors.

That bias is measurable. `RSP` is the real equal-weight S&P 500 fund, so an
equal-weight buy-and-hold of this repo's point-in-time S&P universe should track
it closely. It does not:

| window | SPY | RSP (real) | equal-weight of our PIT universe | gap |
|---|---|---|---|---|
| 2003-05 → 2026-07 | 10.06% | 9.87% | 11.14% | **+1.27** |
| 2003-05 → 2013-01 | 5.20% | 7.42% | 9.32% | **+1.90** |
| 2010-01 → 2020-01 | 10.75% | 10.47% | 12.46% | **+1.99** |
| 2013-01 → 2020-01 | 11.18% | 10.28% | 12.46% | **+2.18** |

**The local stock panel is worth +1.3 to +2.2 pp/yr of free, fake return.** Any
stock-level "edge" smaller than that is an artifact. Running this same rule on
individual stocks looks spectacular (+4.8 to +6.2 pp/yr raw over 29 years) and
should not be believed — and for a rule that holds winners for decades the true
haircut is larger than the figure above, which was measured on a portfolio that
keeps rebalancing.

The 22 ETFs have no such problem: every one still trades, and each becomes
eligible only on its own inception date, so the menu grows through time exactly
as it did in reality. Nothing is on the list because it performed well.

## 6. Honest weaknesses

- **It leans on the growth complex.** Remove QQQ from the menu and the full-period
  excess falls from +1.76 to +0.33 (research harness numbers). Momentum holds
  whatever is winning, and 1999-2026 was disproportionately kind to large-cap
  growth. There is no guarantee the next 27 years rhyme.
- **Short horizons are a coin flip.** 67% of 5-year windows, worst −2.72 pp.
- **Drawdown is not improved.** −57.6% vs SPY's −55.2%.
- **Concentration below 5 names breaks it.** top_n=3 gives −0.65, top_n=4 −0.10;
  5, 6 and 8 all work. Annual rebalancing also fails (−0.61). The plateau is
  real but it has edges.
- **Taxable accounts only.** In an IRA or 401(k) there is nothing to defer and
  this whole mechanism is worth zero.
- **The windows overlap.** 19 rolling 10-year windows drawn from 28 years of data
  are not 19 independent trials; treat the beat-rates as descriptive.
- **One dataset, one country, one tax code.** Everything above is a backtest.

## 7. A harness bug this turned up

The app used to clip price data at the backtest's start date, so a strategy
ranking on a 12-month window had nothing to rank for its first year and sat in
cash while the benchmark compounded — a handicap that came from the harness, not
the strategy, and that silently penalised every long-lookback strategy in the
catalog. `warmup_days` fixes it: extra history is loaded before the window,
nothing trades in it, and `Result.since()` clips it back out of the reported
curve and metrics. On a 2010-2020 window it was worth 1.8 pp to this strategy.
