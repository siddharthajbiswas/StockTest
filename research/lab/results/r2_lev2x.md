# r2_lev2x: moderate leverage + a trend filter, in its most robust and tax-efficient form

Round 2, key `lev2x`. The question: starting from the verified rule (2x S&P while SPY is above
its 175-day average, with a 3% band; intermediate Treasuries otherwise), is there a version that
beats buying and holding the S&P 500 **after California tax (48.1% short-term / 28.1% long-term)
and costs, with good confidence**? FED (35/15) is secondary; NONE is a diagnostic.

Every number is the website engine's after-tax liquidation value. Two routes lead to it, and
§2 shows they agree to machine precision:

* The lab's own sweeps (`backtester.Backtest`).
* An event-driven replica of the engine that I validated against it.

"Excess" is after-tax CAGR minus the benchmark's, in pp/yr. The benchmark is buy-and-hold of
SPY (2000-26), of VFINXR (1986-26), or of the spliced S&P total-return series (1930-2026). "Score"
is the lab's pre-registered `report.score`: the mean of the average 5-, 10- and 15-year window
excess. "p" is the lab's one-sided stationary-bootstrap p-value of the monthly after-tax excess,
taken from the first start.

## 1. Verdict

**No moderate-leverage trend design clears the good-confidence bar for the California taxable
account.** I fixed a 96-design grid and a selection rule before running anything new
(`scratch/r2_lev2x/PREREG.md`). The rule picks:

> **2x S&P (SSO) while the S&P 500's close is more than 3% above its 200-day simple average, until
> it closes more than 3% below it. Otherwise hold intermediate Treasuries (IEF). Checked every
> close and traded at that close. One tax-aware twist: when the exit signal fires and selling
> would realize a net short-term gain whose shares all turn long-term within 60 days, wait until
> they do (unless the signal turns back on first).**

Label `S200|A2|IEF|D-h1`. It is essentially tied with the same rule on a 175-day average
(`S175|A2|IEF|D-h1`): worst-history p 0.164 vs 0.166.

The pick in CA (engine numbers; 1930-85 is the holdout no one designed on):

| history | score | full excess | 10y / 15y / 20y windows beating SPY (worst 10y) | p (first start) | p averaged over all starts | max DD (benchmark) | one-day-lag score / p / DD |
|---|---|---|---|---|---|---|---|
| 2000-26 (SPY) | +3.42 | +3.79 | 79% / 87% / 100% (-1.8) | 0.097 | 0.35 | -49% (-55%) | +3.1 / 0.12 / -48% |
| 1986-26 (VFINXR) | +4.57 | +3.15 | 89% / 94% / 100% (-1.8) | 0.070 | 0.25 | -49% (-55%) | +4.3 / 0.18 / **-59%** |
| **1930-85 holdout** | +3.29 | +2.50 | 83% / 95% / 100% (-5.8) | **0.164** | 0.15 | -73% (-81%) | +2.4 / 0.27 / -78% |
| 1930-2026 | +3.96 | +2.51 | 89% / 96% / 100% (-5.8) | 0.068 | 0.14 | -73% (-81%) | +2.9 / 0.18 / -78% |
| FED (35/15): 2000-26 / 1986-26 / 1930-85 | +4.25 / +5.49 / +4.03 | | | 0.059 / 0.021 / 0.074 | | | |

**Why it is not "good confidence"** (PROTOCOL §3):

1. **The holdout is not significant.** On 1930-85 the p-value is 0.164, failing item 3. No design
   that passes the hard filters (40 of 96) gets a 1930-85 p ≤ 0.10; the best is 0.105. Only the
   two UPRO core-satellites get below it (0.085 and 0.046), and both have drawdowns deeper than
   SPY's after 1986. The second also fails 2000-26 (p 0.21). California's higher rates decide it:
   under FED rates (35/15) the same rule passes items 1-3 in every history. Most of the pick's
   realized gains are long-term, so the 28.1% vs 15% long-term rate matters most.
2. **The first-start p-values flatter the modern histories.** January 2000 sits just before a
   slow bear market, which is the best possible start for a trend rule.
   * Averaged over every start date, the p-value is 0.35 on 2000-26, and only 5% of starts reach
     0.10. On 1986-26 the average is 0.25.
   * The excess to the end, averaged over starts, is +1.6 (2000-26) and +2.3 (1986-26), against
     +3.8 and +3.2 from the first start.
3. **There is little edge since 2010.** Ten-year after-tax excess by decade:

   | 1930s | 1940s | 1950s | 1960s | 1970s | 1980s | 1990s | 2000s | 2010s | 2020-26 |
   |---|---|---|---|---|---|---|---|---|---|
   | +4.5 | +0.6 | +9.9 | -1.5 | +4.0 | +6.9 | +3.3 | +9.0 | **+0.6** | **-0.3** |

   Starts from 2010-23 average +1.05 to the end, and 29% of them are negative.
   The edge comes from slow bear markets (1929-32, 1973-74, 2000-02, 2007-09). Fast corrections
   cost it money: 1998, 2011, 2015-16, 2020, 2022. Pre-tax, it trailed SPY in 13 of 26 calendar
   years, by 15-24 pp in 2011, 2015, 2016, 2020 and 2022.
4. **The search is large.** The deflated Sharpe, given about 12,100 configurations tried
   overall, is 0.002-0.006 in every history.
   * Inside the 2x/0x structure, picking the signal or the safe asset in-sample has no skill on
     1930-85: PBO is 0.60 among 27 designs and 0.82 among 9.
   * On the modern histories, PBO is low (0.02-0.27). That mostly reflects the persistence of
     "IEF plus a daily single filter".
5. **The magnitude depends on parameters.** All 34 neighbouring rules have positive scores in all
   four histories, so the sign is robust. But only 5 of 30 single-filter neighbours pass items
   1-3 on both modern histories, and none passes on 1930-85.
6. **The execution has to be exact.** Selling at the same close as the signal is what escaped
   Black Monday. One day late, the rule rode 10-19-1987 at 2x, with a -59% drawdown and 1986-26
   p 0.18. A weekly check has the same problem (-59%).
7. **The edge needs persistent trends, and the tails are real.**
   * Re-run on resampled market paths, it trails SPY over 20 years in 57-66% of paths when trends
     persist only 1-3 months, and in 29-31% with one-year blocks.
   * A single -20% day while invested lowers the 10-year excess by about 3 pp/yr (permanent
     crash) to about 4 pp/yr (the 1987 pattern of crash then rebound).
   * From a 1929 start it still fell 77% by 1932, against 84% for the index.
8. **Part of the edge rests on one instrument.** IEF's lead over T-bills comes from the 1982-2020
   bond bull market. With T-bills as the safe asset, the same rule has p 0.17 / 0.14 / 0.20.
   In 2022 IEF lost money while the rule was out of stocks.

**Recommendation.** At the user's standard of "good confidence", **none is acceptable.** If the
user still wants this exposure as a deliberate expected-value bet, the pick above is the most
robust form found. Its conditions are in §9: market-on-close orders on the signal day, SSO and IEF
held in the taxable account, acceptance of a roughly 1-in-6 to 1-in-4 chance of trailing SPY
after 20 years, and a -50% to -75% drawdown risk. Treat it as a satellite rather than a
replacement for the core holding. Expect roughly +1.5 to +2.5 pp/yr after CA tax, which is the
start-averaged figure, not the +3-4 the first start shows.

## 2. What I built, and how it was checked

* **Rule** `families/r2_lev2x.py`, kind `r2_lev2x.rule`, a custom Strategy. One rule covers every
  structure:
  * K SMA filters with hysteresis bands, checked daily or weekly, with an optional lag.
  * k = the number of filters that are on.
  * A **core** that is never sold, plus a **sleeve** split between an ON mix and an OFF mix in
    proportion k/K.
  * Trades happen only when k changes, or to pay the January tax. The tax is covered by selling
    the sleeve, never the core.
  * An optional `defer` rule for short-term-gain exits.
  * Each world maps roles to tickers (one / two / three / safe). The module also registers the
    yearly-start protocol `r2_splice` (1930-2023 starts, benchmark R2L_SPX).
* **Data** (new research files, prefix `R2L_`, built by `scratch/r2_lev2x/build_data.py`; no
  existing file was touched). These are real tickers from their first day, with a synthetic
  extension before it:
  * `R2L_SSO`: SYN_SPY2XC, then SSO from 2006-06-21.
  * `R2L_UPRO`: SYN_SPY3XC, then UPRO from 2009-06-25.
  * `R2L_IEF`: VFITX, then IEF from 2002-07-30.
  * `R2L_SHY`: VFISX, then SHY.
  * `R2L_BIL`: SYN_TBILL, then BIL.
  * 1986-26 versions run on VFINXR. The 2x/3x series apply the lab's cost-calibrated SYN formula
    to the repaired VFINX.
  * 1930-2026 versions run on ^GSPC plus approximate dividends before 1980 (verify_lev_robust's
    tables), then VFINXR. Financing uses annual T-bill yields before 1960 and ^IRX after.
  * **Synthetic Treasury funds before 1991.** They are built from the 5-year and 10-year
    constant-maturity yields (^FVX, ^TNX, available from 1962), including roll-down. Fitted on
    1991-2026:
    * intermediate = 80% 5y + 20% 10y, which tracks VFITX within 0.05 pp/yr (monthly corr 0.98)
      and IEF within 0.1;
    * short = 58% bills + 42% 5y, which tracks VFISX within 0.2 pp/yr and SHY within 0.0.
    * Before 1962 there are no daily bond yields, so the "IEF" and "SHY" series are T-bills.
  * Checks: S&P total returns match Ibbotson's within about 1 pp in most years (3 pp in 1933).
    The synthetic intermediate series tracks Ibbotson's intermediate government series, mostly
    within 2 pp a year and up to 4 pp in 1982 and 1985.
  * **Six bad prints in ^GSPC were repaired.** These were isolated one-day spikes with a robust
    local z above 5 that reversed the next day: 1935-04-16 (-10%), 1935-05-16, 1935-08-16,
    1936-09-16, 1938-10-10 and 1961-04-17. Each would have cost a daily-reset 2x fund about
    4-5%. verify_lev_robust's 1930-85 numbers include them.
* **Exact replica.** `scratch/r2_lev2x/sim2.py` is an event-driven re-implementation of the rule
  and of the engine's fills, FIFO lots, yearly tax, carryforward and liquidation value.
  * Start by start, it matches the engine to a relative difference of at most 1.8e-15. That covers
    every quarterly checkpoint, month-end, max drawdown and trade count, across 432 comparisons:
    12 structures × 3 worlds × 3 starts × (CA lag 0, CA lag 1, FED, NONE).
  * It matches 67 complete engine `full`-protocol records (95 starts each) to 9e-16.
  * The official engine sweeps of the finalists match it at 0.0 (§5).
  * Its speed (0.3-2.5 s per protocol, against minutes for the engine on the shared machine)
    made the grid, the lag-1 runs, the bootstraps and the crash injections affordable.
* **Lab notes applied.**
  * I used the protocol `long_r` (VFINXR).
  * boot_p and full_excess are also reported averaged over all start dates. The start-averaged p
    bootstraps each start's own quarterly after-tax excess series (stationary bootstrap, 4-quarter
    blocks).
  * DSR uses about 12,100 trials.
  * The wash-sale rule is enforced on both sides in the realism check (§8).

## 3. Pre-registration, grid and selection

The pre-registration was written before any new result; the rule's numbers were already known
from round 1. It fixes:

* the instruments;
* the rule: a 3% hysteresis band; decide and trade at the same close; the core never sold;
* the grid:
  * filters S175 (SMA175 / 3%), S200 (SMA200 / 3%), and ENS8 = SMA {100,150,200,250} × band {1%,3%}
    (graded k/8);
  * structures A2 (2x / 0x), A1.5, B (2x / 1x), C.5 (core 0.5 + SSO / safe sleeve);
  * safe assets IEF, SHY, BIL;
  * variants daily (no defer), daily (defer 60), weekly;
  * extras A1.25, A1.75 and CU.5 (core 0.5 + UPRO / IEF sleeve);
* the histories;
* the selection rule.

That gives **96 designs**, each run with a one-day lag as well, in CA, plus FED and NONE for the
overall top 10.

Selection, as pre-registered:

1. Hard filters, all in CA:
   * score > 0 and full > 0 on 2000-26, 1986-26 and 1930-85;
   * max DD no worse than the benchmark's in each;
   * the lag-1 version's score > 0 in each.
2. Rank by the number of those histories that pass PROTOCOL items 1-3, then by the worst p, then
   by the worst score.

40 of 96 designs survive the hard filters. The top of the ranking:

| rank | design | hard filters | histories passing items 1-3 | worst p | 2000-26 score / p | 1986-26 | 1930-85 |
|---|---|---|---|---|---|---|---|
| (1) | S175\|CU.5\|IEF\|D-h0 | **fails**: DD -57% vs -55% (2000-26), -59% vs -55% (1986-26) | 3 | 0.085 | +6.2 / 0.03 | +5.4 / 0.01 | +4.9 / 0.09 |
| **1** | **S200\|A2\|IEF\|D-h1** | ok | 2 | 0.164 | +3.4 / 0.10 | +4.6 / 0.07 | +3.3 / 0.16 |
| 2 | S175\|A2\|IEF\|D-h1 | ok | 2 | 0.166 | +4.3 / 0.08 | +4.7 / 0.05 | +3.7 / 0.17 |
| 3 | S175\|C.5\|IEF\|D-h0 | ok | 2 | 0.193 | +3.0 / 0.08 | +2.8 / 0.07 | +1.9 / 0.19 |
| 4 | S175\|A2\|IEF\|D-h0 (the verified baseline on real tickers) | ok | 2 | 0.195 | +5.3 / 0.07 | +4.9 / 0.06 | +3.4 / 0.20 |
| 5 | S200\|C.5\|IEF\|D-h1 | ok | 1 | 0.157 | +2.0 / 0.14 | +2.6 / 0.08 | +1.9 / 0.16 |

The full grid table, with scores and p-values for all four histories, drawdowns and lag-1 scores
for all 96 designs plus the 30 post-hoc neighbours, is in `results/r2_lev2x_table.csv`.

## 4. The structures compared, (a) to (h)

Representative designs, all CA. Each cell is score / p. The full 96 are in the CSV.

| structure | design | 2000-26 | 1986-26 | 1930-85 | 1930-2026 | lag-1, 1986-26 | max DD 2000-26 / 1930-85 |
|---|---|---|---|---|---|---|---|
| (a) 2x / Treasuries, SMA175 (the verified baseline, real tickers) | `S175\|A2\|IEF\|D-h0` | +5.3 / 0.07 | +4.9 / 0.06 | +3.4 / 0.20 | +3.9 / 0.09 | +4.1 / 0.26 | -48% / -66% |
| (a) 2x / Treasuries, SMA200 | `S200\|A2\|IEF\|D-h0` | +3.9 / 0.13 | +4.3 / 0.13 | +3.2 / 0.16 | +3.8 / 0.09 | +4.3 / 0.23 | -49% / -73% |
| (b) 1x floor: SSO on, SPY off | `S175\|B\|-\|D-h0` | +3.6 / 0.14 | +3.0 / 0.08 | +3.0 / 0.29 | +2.9 / 0.18 | +2.5 / 0.30 | **-62% / -85%** |
| (b) 1x floor, SMA200 | `S200\|B\|-\|D-h0` | +3.0 / 0.15 | +2.7 / 0.12 | +3.0 / 0.27 | +2.8 / 0.17 | +2.6 / 0.26 | -61% / -86% |
| (c) core 0.5 SPY never sold + SSO / IEF sleeve (1.5x / 0.5x) | `S175\|C.5\|IEF\|D-h0` | +3.0 / 0.08 | +2.8 / 0.07 | +1.9 / 0.19 | +2.2 / 0.08 | +2.3 / 0.25 | -42% / -68% |
| (c') core 0.5 + UPRO / IEF sleeve (2x / 0.5x) | `S175\|CU.5\|IEF\|D-h0` | +6.2 / 0.03 | +5.4 / 0.01 | +4.9 / 0.09 | +5.0 / 0.01 | +4.6 / 0.09 | **-57%** / -77% |
| (d) graded ensemble ENS8, 0x-2x (SSO / IEF) | `ENS8\|A2\|IEF\|D-h0` | +1.5 / 0.37 | +1.9 / 0.38 | +3.3 / 0.13 | +2.7 / 0.17 | +2.4 / 0.40 | -49% / -67% |
| (d) graded ENS8, 1x-2x (SPY / SSO), as briefed | `ENS8\|B\|-\|D-h0` | +1.6 / 0.38 | +1.3 / 0.37 | +2.8 / 0.27 | +2.0 / 0.30 | +1.4 / 0.39 | -63% / -84% |
| (d) graded ENS8 core-satellite, 0.5x-1.5x | `ENS8\|C.5\|IEF\|D-h0` | +0.9 / 0.39 | +1.1 / 0.40 | +1.9 / 0.13 | +1.5 / 0.18 | +1.3 / 0.41 | -37% / -65% |
| (d, post hoc) graded SMA100-250, 3% bands only | `ENS4x3\|A2\|IEF\|D-h0` | +2.6 / 0.24 | +2.9 / 0.24 | +3.0 / 0.19 | +2.9 / 0.17 | +3.1 / 0.30 | -50% / -70% |
| (e) 1.25x on (75% SPY + 25% SSO) / IEF | `S175\|A1.25\|IEF\|D-h0` | +1.7 / 0.34 | +1.6 / 0.61 | +0.4 / 0.50 | +0.9 / 0.63 | +1.2 / 0.77 | -36% / -50% |
| (e) 1.5x on (50 / 50) / IEF | `S175\|A1.5\|IEF\|D-h0` | +3.0 / 0.20 | +2.8 / 0.34 | +1.5 / 0.35 | +2.0 / 0.34 | +2.2 / 0.59 | -41% / -56% |
| (e) 1.75x on (25 / 75) / IEF | `S175\|A1.75\|IEF\|D-h0` | +4.2 / 0.10 | +3.9 / 0.14 | +2.5 / 0.25 | +3.0 / 0.16 | +3.2 / 0.40 | -45% / -61% |
| (f) safe asset SHY | `S175\|A2\|SHY\|D-h0` | +4.4 / 0.10 | +4.1 / 0.11 | +3.4 / 0.21 | +3.5 / 0.11 | +3.2 / 0.37 | -46% / -66% |
| (f) safe asset T-bills (BIL) | `S175\|A2\|BIL\|D-h0` | +4.0 / 0.14 | +3.6 / 0.15 | +3.3 / 0.23 | +3.2 / 0.15 | +2.7 / 0.45 | -44% / -66% |
| (g) weekly check | `S175\|A2\|IEF\|W-h0` | +3.7 / 0.23 | +3.0 / 0.47 | +2.2 / 0.29 | +2.3 / 0.35 | +3.3 / 0.37 | -45% (1986-26: **-59%**) / -68% |
| (h) tax-aware exit, SMA175 | `S175\|A2\|IEF\|D-h1` | +4.3 / 0.08 | +4.7 / 0.05 | +3.7 / 0.17 | +4.0 / 0.07 | +3.7 / 0.26 | -47% / -66% |
| (h) tax-aware exit, SMA200 = **the pick** | `S200\|A2\|IEF\|D-h1` | +3.4 / 0.10 | +4.6 / 0.07 | +3.3 / 0.16 | +4.0 / 0.07 | +4.3 / 0.18 | -49% / -73% |

What the comparison shows:

* **(a) 2x / 0x stays the best structure at acceptable risk.** Its confidence improves with
  leverage up to 2x. Along the (e) ladder the 1930-85 p falls from 0.50 to 0.35, 0.25 and 0.20,
  and the modern p-values fall the same way.
  * The leverage premium earned in calm uptrends is the most consistent part of the excess.
  * Lower leverage lowers the drawdown but not the uncertainty.
* **(b) The 1x floor fails on risk.** Holding SPY through bear markets gives up the slow-bear
  protection, and the 2x exposure before each exit adds to the loss. Drawdowns are -61% to -62%
  (2000-26) and -85% to -86% (1930-85), worse than SPY's. It has no better p either.
* **(c) The never-sold core does not change confidence.** With the core never selling, the
  portfolio is roughly 0.5 × SPY plus 0.5 × the 2x / 0x rule, so the excess and tracking error
  both halve and the p-value stays put.
  * C.5 is a lower-risk form of A2: its 2000-26 drawdown is -42%, against -48%.
  * **The UPRO version (c')** is the statistically strongest design in the grid, with p 0.03 /
    0.01 / 0.085. But its drawdowns are deeper than SPY's in 2000-26 and 1986-26. It has the
    worst 1929-35 of the group: -85% from a 1929 start, and 0.68x by 1935 against 0.77x for the
    index. In the strategy-level bootstrap its chance of a 70% drawdown within 20 years is 18%,
    against 11% for SPY. The pre-registered filter rejects it, and I agree: it is not moderate
    leverage.
* **(d) Ensembles did not remove the parameter risk; they diluted the edge.**
  * The pre-registered ENS8 includes 1% bands. Those turn over about 2.1x a year (against 1.0-1.3
    for single filters), realize more short-term results, and trigger hundreds of wash sales.
    Its 2000-26 and 1986-26 scores are therefore +0.5 to +1.9, with p 0.35-0.66.
  * In 1930-85 it is as good as the single filters (+3.3, p 0.13).
  * A post-hoc ensemble with 3% bands only lands in between everywhere (p 0.12-0.34 across its
    four versions).
  * Averaging filters averages the era-dependence (wide bands win after 1986, narrow bands before);
    it does not remove it.
  * The briefed "1x-2x" ensemble (`ENS8|B`) is the worst of both: low excess and SPY-plus
    drawdowns.
* **(f) IEF beats SHY, which beats T-bills, in every history.** The ranking holds in 1930-85 too,
  but there "IEF" is T-bills before 1962 and a synthetic intermediate fund after, so the gap is
  only +0.1. After 1986 IEF adds about 1.0-1.4 pp/yr. That is the bond bull market: in 2000-02, 2008
  and 2020 Treasuries rallied while the rule was out of stocks, and in 2022 they fell (the pick's
  2022 drawdown was -41%, against -24% for SPY).
* **(g) Weekly checks fail.**
  * 1987: the 1986-26 drawdown is -59% to -62%.
  * p is 0.23-0.32 (2000-26), 0.41-0.61 (1986-26) and 0.29-0.34 (1930-85).
  * One-day-lag versions of the daily 2x / IEF rules keep positive scores in every history (+2.1
    to +5.6). The 1987 day still breaks the drawdown (as deep as -59%), and the 1986-26 p becomes
    0.18-0.40.
* **(h) The tax-aware exit is a small, real improvement for the taxable account.**
  * It postponed 2 of 13 exits in 2000-26 and 3 of 51 in 1930-2026.
  * Realized short-term results turn net negative: short-term losses, long-term gains.
  * Turnover falls from 1.17-1.33 to 0.97-1.08.
  * In CA it lowers the 1930-85 p for SMA175 (0.195 → 0.166) and leaves it unchanged for SMA200
    (0.164). It lowers the 1986-26 p for SMA200 (0.13 → 0.07).
  * In 2000-26 it costs SMA175 one point of score (+5.3 → +4.3), because waiting held 2x into some
    declines. It does nothing in NONE.

## 5. The pick in detail

Exact config: the ETF world, i.e. real tickers with their synthetic pre-inception history:

```json
{"kind": "r2_lev2x.rule", "world": "ETF", "safe": "IEF", "filters": [[200, 0.03]], "check": "D", "lag": 0,
 "core": 0.0, "on": {"two": 1.0}, "off": {"safe": 1.0}, "defer": 60}
```

In this world `two` = R2L_SSO (SSO from 2006-06-21, SYN_SPY2XC before) and `safe` = R2L_IEF (IEF
from 2002-07-30, VFITX before). The signal is SPY's total-return close. The same rule on real
tickers only (`"roles": {"one": "SPY", "two": "SSO", "safe": "IEF"}`, starts from 2006-07) is in
§8. 1986-26 and 1930-2026 use `"world": "LONG"` and `"world": "SPLICE"`.

Engine (official `sweep`) results:

| history | regime | score | full | p | max DD (bench) | Sharpe (bench) | trades / turnover |
|---|---|---|---|---|---|---|---|
| 2000-26 | CA | +3.42 | +3.79 | 0.097 | -49.3% (-55.2%) | 0.56 (0.51) | 65 / 0.97 |
| 2000-26 | FED | +4.25 | +4.90 | 0.059 | -47.1% | 0.62 | |
| 2000-26 | NONE | +6.29 | +6.24 | 0.032 | -44.7% | 0.69 | |
| 1986-26 | CA / FED / NONE | +4.57 / +5.49 / +6.74 | +3.15 / +4.73 / +6.17 | 0.070 / 0.021 / 0.005 | -49.3% (-55.3%) | 0.64 / 0.72 / 0.78 (0.68) | |
| 1930-85 | CA / FED / NONE | +3.29 / +4.03 / +5.03 | +2.50 / +3.69 / +5.18 | 0.164 / 0.074 / 0.031 | -72.9% (-80.8%) | | |
| 1930-2026 | CA / FED / NONE | +3.96 / +4.85 / +6.15 | +2.51 / +4.06 / +5.71 | 0.068 / 0.013 / 0.000 | | | |

All rows are official lab sweeps of the exact config. The 1930-2026 rows run through the
`r2_splice` protocol; 1930-85 is restricted to starts up to 1975 and windows ending by 1985-10.
Every record matches the replica's with a relative difference of 0.0.

* **Short-term gains.** Over the 1930-2026 run, net realized short-term results are -15% of all
  net realized gains: short-term losses exceed short-term gains. Without the defer the share is
  -3% to -6% for SMA200 and +6% to +8% for SMA175.
* **Volatility.** Daily volatility is 24.7%, against SPY's 19.3% (2000-26). The equity-curve
  Sharpe in CA is 0.56 against 0.51 (2000-26) but 0.64 against 0.68 (1986-26). The January tax
  payments count against it; in NONE the figures are 0.69 and 0.78. Most of the excess is
  paid-for leverage.
* **Sub-periods** (CA after-tax excess, pp/yr): 2000-10 +9.1, 2010-20 +0.6, 2020-26 -0.3. Pre-2000
  windows inside 1986-26 (ho5 / ho10): +4.2 (92% beat) / +3.7 (100% beat).
* **Episodes** (pre-tax, from the index's pre-crash peak to its trough):

  | episode | index | pick |
  |---|---|---|
  | 1929-32 | -84% | -46% |
  | 1937-38 | -52% | -42% |
  | 1973-74 | -44% | -30% |
  | 1987 | -33% | -30%, out at the 10-16 close |
  | 2000-02 | -48% | +2% |
  | 2007-09 | -55% | -14% |
  | 1998 | -19% | -36% |
  | 2011 | -19% | -30% |
  | 2015-16 | -13% | -38% |
  | 2020 | -34% | -36% |
  | 2022 | -24% | -41% |

* **1929-35** (a start on 1929-01-02): max drawdown -77% against -84%. Value by 1935: 1.31x
  against 0.77x pre-tax, and 1.17x against 0.77x after tax.

## 6. Risk

**Strategy-level stationary bootstrap.** Joint monthly strategy and benchmark returns,
12-month mean blocks, intra-month troughs included, 20,000 paths. Benchmark figures in brackets.

| design | data | P(trail SPY after tax) 10y / 20y | median excess, 20y | P(DD > 60%) in 20y | P(DD > 70%) | P(DD > 80%) |
|---|---|---|---|---|---|---|
| **pick** | 1930-2026 | 32% / 25% | +2.2 | 27% (20%) | 8.2% (10.9%) | 1.4% (4.0%) |
| **pick** | 1986-2026 | 25% / 16% | +2.7 | 7% (5%) | 1.1% (0.9%) | 0.1% (0.1%) |
| **pick** | 2000-2026 | 23% / 14% | +3.3 | 12% (12%) | 2.5% (2.8%) | 0.3% (0.3%) |
| S175\|A2\|IEF\|D-h0 | 1930-2026 | 34% / 27% | +2.0 | 18% (20%) | 5.0% (10.9%) | 0.7% (4.0%) |
| S175\|C.5\|IEF\|D-h0 | 1930-2026 | 34% / 27% | +1.4 | 10% (20%) | 2.4% (10.9%) | 0.2% (4.0%) |
| S175\|CU.5\|IEF\|D-h0 | 1930-2026 | 22% / 13% | +4.1 | **46% (20%)** | **18% (10.9%)** | 4.6% (4.0%) |

**Market-path bootstrap.** Daily rows of every instrument are resampled in blocks and the rule is
re-run after CA tax; 600 paths per cell.

| design | data | block | P(trail) 10y / 20y | median excess, 20y | P(DD > 80%) in 20y | median DD (SPY) |
|---|---|---|---|---|---|---|
| pick | 1928-2026 | 21 days | 62% / 62% | -1.2 | 10.7% | -66% (-43%) |
| pick | 1928-2026 | 63 days | 56% / 57% | -0.6 | 7.7% | -63% (-45%) |
| pick | 1928-2026 | 252 days | 36% / 31% | +1.6 | 4.8% | -59% (-49%) |
| pick | 1985-2026 | 21 / 63 / 252 days | 60% / 66%; 52% / 57%; 33% / 29% | -1.6 / -0.6 / +1.8 | 5.0% / 1.8% / 0.3% | |

The edge exists only in paths whose trends persist for many months. With 1-3-month persistence,
the leveraged rule loses to SPY more often than not, as verify_lev_robust also found.

**One -20% day while invested.** Six evenly spaced invested days per yearly start; the rule sees
the crash and exits at that close.

| design | starts | base 10y excess (beat) | permanent -20%: 10y (beat) | 1987 pattern: 10y (beat) | worst 10y | median max DD |
|---|---|---|---|---|---|---|
| pick | 1986-2016 | +4.7 (94%) | +1.8 (72%) | +0.6 (53%) | -6.4 | -50% |
| pick | 1930-2016 | +3.9 (89%) | +1.0 (62%) | -0.1 (46%) | -11.4 | -51% |
| S175\|CU.5 | 1930-2016 | +5.0 (92%) | +0.9 (57%) | +0.3 (45%) | -5.1 | -59% |

A -20% day removes about 40% of the account in one close. The pick held 2x on about 72% of days.

## 7. Overfitting diagnostics

* **CSCV PBO** on the monthly after-tax excess:

  | universe | 2000-26 | 1986-26 | 1930-85 | 1930-2026 |
  |---|---|---|---|---|
  | all 96 | 0.19 | 0.02 | 0.06 | 0.00 |
  | the 27 2x / 0x designs | 0.27 | 0.03 | **0.60** | 0.08 |
  | the 9 daily 2x / 0x without defer | 0.10 | 0.02 | **0.82** | 0.15 |

  The low PBO across all 96 reflects choosing the 2x / 0x structure, leverage and IEF. Choosing
  among filters inside that structure has no skill before 1986. Splitting each history in half,
  the in-sample best of the three signals ends up worst out of sample in 53% (2000-26) and 87%
  (1930-2026) of the 30 cells.
* **Walk-forward.** Each January, choose the best trailing-10-year design and run it for the next
  5 years.
  * Over all 96, out of sample: +4.4 (2000-26, 100% positive), +4.3 (1986-26, 96%), +4.6
    (1930-2026, 88%), +4.2 (1930-85 only, 80%).
  * The average design out of sample: +0.8, +1.9, +2.2 and +2.5.
  * Inside the 2x / 0x structure on 1930-85, walk-forward (+3.7) only matches the average design
    (+3.6), so the selection skill comes from the structure, not the parameters.
  * The pick held fixed over the same 5-year windows: +1.5 (67% positive), +4.3 (85%), +4.5 (85%),
    +4.3 (83%).
* **Deflated Sharpe** (about 12,100 trials): 0.004 (2000-26), 0.006 (1986-26), 0.002 (1930-85),
  0.006 (1930-2026). Deflated against the spread of this 96-design grid alone: 0.28-0.54. The
  probabilistic Sharpe without deflation is 0.82-0.92.
* **Neighbourhood** (post hoc, 2x / IEF daily, SMA 150 / 175 / 200 / 225 / 250 × band 2/3/4%,
  with and without the defer, plus two 3%-band ensembles; 34 rules):
  * every rule has a positive score in all four histories, including its lag-1 version: scores
    +0.7 to +5.9, 1930-85 p 0.14-0.49;
  * passing items 1-3 on 2000-26: 5 of 34; on 1986-26: 13; on 1930-85: 0;
  * wider bands do better after 1986 and narrower bands before: band 2% has the best 1930-85 p
    (0.139 for SMA200 with the defer), band 4% the best modern p (0.049 / 0.022 for SMA200 with
    the defer, but 1930-85 p 0.26).

Neighbourhood, CA, each cell score / p (post hoc):

| rule (2x/IEF, daily) | 2000-26 score / p | 1986-26 | 1930-85 | 1930-2026 | passes items 1-3 in |
|---|---|---|---|---|---|
| ENS3x3 no defer | +3.5 / 0.14 | +4.3 / 0.14 | +2.9 / 0.21 | +3.4 / 0.12 | - |
| ENS3x3 defer | +2.9 / 0.20 | +4.3 / 0.15 | +3.1 / 0.19 | +3.5 / 0.12 | - |
| ENS4x3 no defer | +2.6 / 0.24 | +2.9 / 0.24 | +3.0 / 0.19 | +2.9 / 0.17 | - |
| ENS4x3 defer | +2.4 / 0.29 | +3.1 / 0.34 | +3.2 / 0.16 | +2.9 / 0.19 | - |
| N150b2 no defer | +2.6 / 0.41 | +2.2 / 0.34 | +2.8 / 0.23 | +2.6 / 0.23 | - |
| N150b2 defer | +1.7 / 0.43 | +2.0 / 0.49 | +3.2 / 0.20 | +2.3 / 0.26 | - |
| N150b3 no defer | +4.6 / 0.13 | +4.8 / 0.10 | +2.7 / 0.25 | +3.3 / 0.14 | 1986-26 |
| N150b3 defer | +3.4 / 0.23 | +4.5 / 0.28 | +3.3 / 0.19 | +3.2 / 0.18 | - |
| N150b4 no defer | +4.9 / 0.12 | +4.7 / 0.10 | +2.2 / 0.32 | +3.2 / 0.18 | 1986-26 |
| N150b4 defer | +4.9 / 0.12 | +5.1 / 0.07 | +2.5 / 0.30 | +3.5 / 0.14 | 1986-26 |
| N175b2 no defer | +3.4 / 0.21 | +4.4 / 0.10 | +3.7 / 0.18 | +3.9 / 0.09 | 1986-26 |
| N175b2 defer | +2.8 / 0.20 | +4.5 / 0.06 | +4.0 / 0.15 | +4.1 / 0.07 | 1986-26 |
| N175b3 no defer | +5.3 / 0.07 | +4.9 / 0.06 | +3.4 / 0.20 | +3.9 / 0.09 | 2000-26, 1986-26 |
| N175b3 defer | +4.3 / 0.08 | +4.7 / 0.05 | +3.7 / 0.17 | +4.0 / 0.07 | 2000-26, 1986-26 |
| N175b4 no defer | +4.6 / 0.11 | +4.4 / 0.14 | +2.8 / 0.20 | +3.5 / 0.09 | - |
| N175b4 defer | +4.6 / 0.11 | +4.9 / 0.09 | +2.9 / 0.20 | +3.7 / 0.09 | 1986-26 |
| N200b2 no defer | +2.9 / 0.21 | +3.8 / 0.18 | +3.6 / 0.15 | +3.6 / 0.11 | - |
| N200b2 defer | +3.1 / 0.15 | +4.5 / 0.08 | +3.8 / 0.14 | +3.9 / 0.06 | 1986-26 |
| N200b3 no defer | +3.9 / 0.13 | +4.3 / 0.13 | +3.2 / 0.16 | +3.8 / 0.09 | - |
| N200b3 defer | +3.4 / 0.10 | +4.6 / 0.07 | +3.3 / 0.16 | +4.0 / 0.07 | 2000-26, 1986-26 |
| N200b4 no defer | +4.3 / 0.07 | +5.0 / 0.10 | +2.3 / 0.26 | +3.5 / 0.12 | 2000-26, 1986-26 |
| N200b4 defer | +4.9 / 0.05 | +5.9 / 0.02 | +2.4 / 0.26 | +3.8 / 0.07 | 2000-26, 1986-26 |
| N225b2 no defer | +2.6 / 0.21 | +3.8 / 0.16 | +2.8 / 0.28 | +3.4 / 0.18 | - |
| N225b2 defer | +2.8 / 0.13 | +4.2 / 0.09 | +2.8 / 0.28 | +3.6 / 0.14 | 1986-26 |
| N225b3 no defer | +3.5 / 0.11 | +4.1 / 0.24 | +2.5 / 0.31 | +2.9 / 0.24 | - |
| N225b3 defer | +3.2 / 0.13 | +4.4 / 0.21 | +2.5 / 0.31 | +3.0 / 0.22 | - |
| N225b4 no defer | +3.2 / 0.16 | +4.8 / 0.18 | +2.4 / 0.30 | +3.0 / 0.21 | - |
| N225b4 defer | +3.6 / 0.13 | +5.0 / 0.16 | +2.4 / 0.30 | +3.1 / 0.20 | - |
| N250b2 no defer | +2.1 / 0.23 | +3.4 / 0.32 | +3.0 / 0.23 | +2.9 / 0.22 | - |
| N250b2 defer | +1.8 / 0.24 | +3.3 / 0.33 | +3.0 / 0.23 | +2.8 / 0.22 | - |
| N250b3 no defer | +1.7 / 0.25 | +3.3 / 0.31 | +2.2 / 0.36 | +2.6 / 0.31 | - |
| N250b3 defer | +1.6 / 0.25 | +3.3 / 0.32 | +2.2 / 0.36 | +2.5 / 0.32 | - |
| N250b4 no defer | +2.3 / 0.20 | +4.2 / 0.25 | +0.8 / 0.49 | +2.0 / 0.39 | - |
| N250b4 defer | +3.1 / 0.14 | +4.7 / 0.20 | +0.7 / 0.49 | +2.1 / 0.36 | - |

## 8. Realism checks

* **Wash sales**, enforced on both sides: a purchase within 30 days after a loss sale, or a
  separate purchase within 30 days before it. The disallowed loss is added to the replacement
  lot's basis.

  | | 2000-26 | 1986-26 | 1930-2026 | wash events per run |
  |---|---|---|---|---|
  | pick | -0.04 pp/yr (worst start -0.10) | -0.03 | -0.02 | 1-2 |
  | graded ENS8 | -0.12 to -0.13 | | | 150-750 |

* **Trading costs** (2000-26, CA, the same cost applied as commission and as slippage on each
  side):

  | cost per side | score | p | 10y windows beating SPY |
  |---|---|---|---|
  | 0 | +3.58 | 0.089 | |
  | 5 + 5 bps (site default) | +3.42 | 0.097 | |
  | 15 + 15 bps | +3.10 | 0.12 | |
  | 35 + 35 bps | +2.46 | 0.19 | 63% |

  The rule trades about 2.5 times a year, so costs do not decide anything.
* **Real tickers only** (SPY / SSO / IEF; windows start once SSO exists, from 2006-07).
  * Over the same starts, results are identical to the spliced R2L series: relative difference
    1e-9 across 3,174 checkpoints.
  * Because the sample begins after the 2000-02 bear market, it is weaker:

    | regime | score | full | p | 10y beat |
    |---|---|---|---|---|
    | CA | +1.61 | +2.57 | 0.21 | 66% |
    | FED | +2.30 | | 0.14 | |
    | NONE | +4.21 | | 0.073 | |

  * Max DD -49% against SPY's -55%.
  * On the same real-ticker sample, the SMA175 runner-up scores +3.04 (p 0.14), well ahead of the
    pick's +1.61. The 175-versus-200 choice is noise that moves sub-samples by about 1.5 pp/yr.
  * The UPRO core-satellite on real tickers from 2009-07 scores +5.31 (p 0.049), but its drawdown
    is -54% against SPY's -34% over that period.
* **Distributions taxed every year** (`realism.adjusted` on the real-ticker rule). SSO
  distributions are taxed as ordinary income, IEF interest as Treasury interest (CA-exempt), and
  SPY dividends as qualified. Engine excess → realistic excess, pp/yr:

  | start | CA | FED |
  |---|---|---|
  | 2007 | +2.45 → +2.40 | +3.47 → +3.31 |
  | 2010 | -0.19 → -0.18 | +0.68 → +0.60 |
  | 2015 | -0.62 → -0.64 | -0.12 → -0.22 |
  | 2020 | -0.26 → -0.34 | -0.09 → -0.23 |

  In CA the adjustment is -0.08 to +0.02. Because Treasury interest is CA-exempt, the engine's
  48.1% short-term treatment of bond gains is harsher than reality, which offsets SSO's
  ordinary-income payouts. The three starts from 2010 on are slightly negative. Across all 55
  quarterly starts in 2010-23, the to-the-end excess averages +1.05 pp/yr and is negative for 29%
  of them. For the SMA175 baseline the figures are -0.47 and 47%.

* **Dividends and interest taxed yearly.** The engine taxes them only at sale; the realism rows
  above price the difference. Treasury interest is CA-exempt, taxed at 38.8% federally including
  NIIT. The FED regime used here omits NIIT.
* **FIFO only.** A real investor can choose lots (HIFO) and would do slightly better on the
  graded designs. The single-filter pick sells whole positions, so lot choice barely matters.

## 9. Conditions, if the user takes the bet anyway

1. **Execution.** Evaluate at about 3:45 pm on the day's price, and send a market-on-close order
   for SSO→IEF or IEF→SSO. A one-day delay turns the 1987 escape into a -59% drawdown.
2. **The defer rule.** When an exit would realize a short-term gain on shares that turn long-term
   within 60 days, wait for that date unless the signal turns back on. Otherwise exit at once.
3. **Hold it as a satellite.** Expect:
   * drawdowns of -50% (modern history) to -75% (the 1930s);
   * losing to SPY in about half of calendar years, sometimes by 20 pp;
   * no edge in choppy decades such as the 2010s;
   * a 1-in-4 to 1-in-6 bootstrap chance of trailing SPY over 20 years after tax, and worse if
     trends persist less than history suggests.
4. **Fund risk.** SSO is a daily-reset swap-based fund. Its distributions are taxed as
   ordinary income, and in some years they are large (4-5% of value in 2006-07). The realism rows
   in §8 include them.

## 10. Counts and files

* **Configurations: 126 distinct designs.** The 96 pre-registered ones, plus 30 post-hoc
  neighbourhood or ensemble rules (the 34 neighbours less 4 that duplicate grid designs).
  * Each design was also run with a one-day lag.
  * The top 10 were also run in FED and NONE.
  * The finalists were re-run on the engine and with costs.
  * About 950 protocol-level runs in all (46-151 window starts each), plus about 26,000
    single-path simulations for the bootstraps and crash injections.
* **New trial count for DSR:** about 12,000 + 126.
* **Code:** `research/lab/families/r2_lev2x.py`, the kind `r2_lev2x.rule` and the protocol
  `r2_splice`.
* **Data:** `research/lab/data/R2L_*.csv`, 16 files built by
  `scratch/r2_lev2x/build_data.py`.
* **Scripts** (`research/lab/scratch/r2_lev2x/`):
  * `PREREG.md`, `grid.py`
  * `sim2.py` (exact replica), `validate_sim2.py` with outputs `out/validate_sim2_*.json`
  * `sim_grid.py` → `out/grid_*.csv`
  * `choose.py` → `out/selection_CA.csv`
  * `diag.py` → `out/diag.json`, `out/wf_*.csv`
  * `neigh.py` → `out/neigh_CA.csv`
  * `risk.py` (d1 / d2 / crash) → `out/risk_*.json`
  * `episodes.py` → `out/episodes.json`
  * `wash.py` → `out/wash.json`
  * `finalists.py` → `out/finalists.json`
  * `engine_final.py` → `out/engine_*.json`
  * `tables.py` → `results/r2_lev2x_table.csv`
  * engine-format records cached in `out/rec/`
* **Lab notes:**
  * ^GSPC has bad prints in 1935-38 and 1961 (repaired only in my R2L files).
  * `realism` cannot price R2L_ or SYN_ tickers: it has no distribution files for them and treats
    them as qualified dividends. Use real tickers for realism.
  * A custom kind gets no lag or offset from `verify.battery`. Here lag is a rule parameter, and
    offsets are irrelevant for daily rules.
