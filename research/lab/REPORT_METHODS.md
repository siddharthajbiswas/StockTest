# How the strategy search was run (methods)

This is the methods section of the strategy-search report. Results are in the
main report; everything here is reproducible from `research/lab/`.

## Same numbers as the website

Every backtest runs `backtester.Backtest`, the engine the website's JavaScript
port is pinned to by the golden-oracle suite. `research/lab/validate_lab.py`
re-runs windows through the site's own request path (`reference/service.py`)
and compares after-tax CAGR for the strategy and for its SPY benchmark:
36 comparisons (3 strategies x 3 tax regimes x 4 windows), worst difference
**0.0**.

Settings are the site's: $100,000 start, 5 bps commission + 5 bps slippage per
side, FIFO tax lots, short- vs long-term gains (365 days), annual settlement
in January, loss carryforward, and a terminal "sell everything" tax so that a
churning strategy and a never-selling buy-and-hold are compared fully after
tax.

## Tax regimes

| regime | short-term | long-term | who it describes |
|---|---|---|---|
| CA | 48.1% | 28.1% | California single filer ~$300k (35% fed + 3.8% NIIT + 9.3% CA; 15% + 3.8% + 9.3%) — the site's "Beat the S&P (CA)" preset |
| FED | 35% | 15% | the site's default rates |
| NONE | — | — | IRA / 401(k): no tax |
| ZERO | 0% | 0% | IRA, but with the site's tax accounting switched on at 0% so tax-aware trading rules still operate ("tax enabled, rates 0%" on the site) |

## Many samples, not one backtest

A single start date can make any strategy look good or bad. Each strategy is
run from **95 quarterly start dates (2000-01 … 2023-07)**; each run records the
exact after-tax liquidation value at every later quarter end. That yields
every 3-, 5-, 10-, 15- and 20-year window (and "to mid-2026") — e.g. 67
ten-year windows — each compared with SPY bought and held over the same
window, in the same tax regime, through the same engine.

The checkpoint method is exact, not an approximation: the after-tax value on
day E of a run that continues past E equals that of a run clipped at E (no
strategy can see the future), and the lab recomputes the engine's terminal
tax from the portfolio's own lots. It is verified against clipped runs.

**Long history.** Index and sector mutual funds extend the test back to 1986
(VFINX for the S&P 500; Fidelity Select sector funds; Vanguard bond funds).
Windows that *end before 2000* are a true holdout for any idea designed on
ETF-era data.

## Statistics

* **score** (pre-registered ranking): mean of the average after-tax excess over
  5-, 10- and 15-year windows.
* **beat rates**: share of L-year windows in which the strategy beat SPY.
* **bootstrap**: stationary block bootstrap (12-month mean blocks) of the
  monthly after-tax excess return from the 2000 start; `boot_p` is the
  one-sided probability the true excess is <= 0.
* **walk-forward selection**: at each date, pick the family's best config on
  the trailing 10 (or 5) years, then score it on the next 5 (or 3) — the honest
  estimate of what *running this search* would have earned.
* **PBO** (probability of backtest overfitting, CSCV with 16 blocks) and the
  **deflated Sharpe ratio**, which discount a result by the number of
  configurations tried.
* **Rebalance-timing luck**: every finalist is re-run with its rebalance
  boundaries shifted through the whole period (e.g. 7 offsets for a quarterly
  strategy).

## Stricter-than-the-site tax check

The engine taxes dividends and bond interest as deferred capital gains (prices
are total-return). For finalists, `research/lab/realism.py` replays the exact
daily holdings and charges distributions yearly at their real character —
qualified dividends at the long-term rate, bond interest at ordinary rates
(Treasuries exempt from CA tax), REITs mostly ordinary — credits the basis of
reinvested distributions, and taxes gold-trust gains at the collectibles rate.
SPY gets the same treatment, so the excess stays apples to apples.

## Honesty rules

1. **No look-ahead** — signals see only data up to the trade's close (finalists
   are also re-run with a one-day execution lag).
2. **Survivorship** — the per-stock data contains only today's survivors
   (39% of the S&P 500's 2000 membership), so individual-stock results are
   upper bounds, reported next to random-pick controls.
3. **Hindsight** — instruments that are famous *because* they won (QQQ, XLK,
   TQQQ…) are flagged; menu-based rules are re-tested on random menus drawn
   from a fixed, pre-registered pool of the 90 ETFs that existed by 2003.
4. **Wash sales** — any rule that harvests losses waits 31 days before
   rebuying, and substitutes track a different index.
5. **Everything tried is counted** — the number of configurations sets the
   multiple-testing penalty.
