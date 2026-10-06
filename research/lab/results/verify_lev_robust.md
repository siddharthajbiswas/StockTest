# verify_lev_robust: adversarial check of the leveraged trend finalists

Scope: the four round-1 leveraged finalists. C1 is daily 3x S&P / VFITX with SMA175 and a 3% band, chosen post hoc. C2 is daily 3x with SMA200 and a 2% band, the pre-registered version. C3 is 3x while 60-day vol is under 15%, else 1x SPY. C4 is 2x SSO while EMA100 > EMA200, else IEF/VFITX.

I tested six things: (a) long history, (b) the parameter neighbourhood, (c) walk-forward selection, (d) block-bootstrap risk, (e) a single -20% day, and (f) constant leverage at equal volatility. Primary regime CA (48.1/28.1). All numbers are after-tax excess CAGR vs buy-and-hold of SPY, or of VFINX on long histories, in percentage points per year, unless stated otherwise.

## Verdict in one paragraph

Leverage plus a trend filter is **not a confident after-tax edge**. Four things hold:

* **There is an after-tax excess in every history.** It shows up on 2000-2026, 1986-2026, the 1930-1985 holdout and 1930-2026. Walk-forward parameter selection is positive out of sample, and at equal volatility the trend filter beats constant leverage by a wide margin.
* **The excess is mostly paid-for leverage.** It scales with leverage and is about +1 to +2.6 pp/yr at 1.5x, where volatility matches SPY. That is not significant anywhere (p 0.22-0.46).
* **Statistical confidence collapses once the search is accounted for:**
  * deflated Sharpe 0.003-0.03 for every variant, given about 12.5k configurations tried;
  * PBO about 0.5-0.7 inside the 3x and 2x daily grids;
  * only 13 of 486 neighbourhood configs (2.7%) pass the bar on both 2000-2026 and 1986-2026, and only 1 of 486 passes on all four histories;
  * the 1930-1985 holdout is positive but not significant (C1 p 0.19, C2 p 0.16).
* **The 3x tail risk is unacceptable for a normal taxable account:**
  * a -88% to -93% drawdown in 1929-35;
  * a 15-24% chance of an >80% drawdown within 20 years when 1930-2026 is block-bootstrapped;
  * escaping Black Monday was a one-day coincidence, and with a one-day execution lag the 1986+ drawdown is -78%;
  * one -20% day while invested cuts the 10-year excess by about 7-8 pp/yr.

Verdicts and the acceptable-risk leverage:

* **C1, C2, C3, C4: fail** as "good confidence" recommendations. C3 and C4 also have no edge at all in the 1930-1985 holdout.
* **About 2x is the highest leverage whose risk is acceptable.** That is the daily SMA175-200 rule with a 3-4% band. Its drawdowns are at or below SPY's in every history, and P(>80% drawdown in 20y) is about 0-1.5%. The after-tax excess is about +3 to +5 pp/yr, but the confidence is only moderate (p 0.07-0.27, DSR about 0.004). It is **conditional**, not a pass.

## 0. What I built and how I checked it

* `families/verify_lev_robust.py` contains `verify_lev_robust.trend`, an independent re-implementation of the SMA-band switch. It supports D/W/M checks, a lag, an SMA or EMA, multi-asset risk-on mixes with a drift band, and a fallback list of safe assets. On the engine it reproduces C1 exactly: CA score 0.0965, full 0.0710, p 0.029, maxDD -0.6046.
* `scratch/verify_lev_robust/sim.py` is a numpy re-implementation of the rule plus the engine's tax accounting. That covers ST/LT lots, the January tax payment sold from holdings, the loss pool and the liquidation tax. It also covers 5+5 bps costs and the buy-and-hold benchmark.
  * **Validated to the 4th decimal against the engine.** It matches every window CAGR, the score, boot_p and maxDD for C1 and C2 on `full` and on `long`, and 7 spot checks: weekly and monthly checks, 2x, and the long world. Examples: weekly 3x 200/2% gives 0.0603 / p 0.094 / -0.6184 on both, and long 225/3% gives 0.0726 / 0.172 / -0.8005 on both.
  * This made the 486-config grids, the bootstrap paths, the crash injections and the pre-1986 history possible, at roughly 30x engine speed.
* I also re-implemented C3 (vol filter) and C4 (EMA cross) in the simulator. C3 matches the engine (0.051 / p 0.039 / -0.651). C4 matches round-1's synthetic-2x number (0.062 vs 0.0617, p 0.019 vs 0.02).
* I built four histories:
  * **ETF**: protocol `full`, 2000-2026.
  * **LONGX**: protocol `long`, 1986-2026, VFINX world, safe asset VFITX, then VUSTX, then T-bills, using **repaired VFINX** (see bugs).
  * **PRE**: 1930-1985, never seen by round 1. Yearly starts 1930-1975, windows ending by 1985-10. It uses ^GSPC daily prices plus approximate annual dividend yields, ^IRX financing from 1960 and approximate annual T-bill yields before that. Leveraged series use the same cost-calibrated formula as SYN_*C (L x r - (L-1) x bill - 0.9% - (L-1) x 0.6%). The safe asset is T-bills.
  * **SPLICE**: 1930-2026, yearly starts.

## 1. Bugs and data problems found

1. **VFINX has unadjusted distribution days (1980-1986).** The adjusted close misses capital-gain distributions:

   | day | VFINX | S&P |
   |---|---|---|
   | 1980-12-30 | -2.7% | +0.2% |
   | 1981-12-29 | -4.0% | -0.5% |
   | 1983-12-28 | -3.1% | +0.4% |
   | 1984-12-28 | -2.1% | +0.3% |
   | 1985-12-27 | -5.7% | +0.9% |
   | 1986-12-09 | -7.0% | -0.75% |

   There are also a few stale-NAV pairs, in 1987 and 1991.
   * `SYN_VFINX3XC` triples these. On 1986-12-09 it shows -20.9%, while C1 was holding it.
   * The `long` benchmark carries them too.
   * Net effect: the bug **penalised** the leveraged strategies. Repairing it (`sim.vfinx_fixed`, which uses the ^GSPC return on days where the two differ by more than 1.5 pp) moves the 1986-2026 CA results as follows.

   | | score | full | boot_p |
   |---|---|---|---|
   | C1, as round 1 had it | +8.58 | +6.06 | 0.015 |
   | C1, repaired | +8.64 | +6.88 | 0.007 |
   | C2, as round 1 had it | +7.03 | +4.74 | 0.071 |
   | C2, repaired | +7.08 | +5.47 | 0.040 |

   The data files were not edited. This needs fixing in data/ or in the long benchmark.
2. **The realism adjustment ignores SYN_* distributions.** `realism.dist_yield` finds no file for them, so only the VFITX interest is taxed annually. Real UPRO paid 0.0-1.0% a year, about 0.4% on average, all ordinary income and no capital gains so far. SSO paid 4-5% in 2006-07. Taxing UPRO-like payouts at 48.1% while invested costs roughly 0.1-0.2 pp/yr more. A fund-level short-term gain distribution in a strong year, as with SSO in 2006-07, could cost about 2 pp in that year. This is unmodelled tail risk.
3. Minor data issues: VFITX shows -3.2% on 1993-12-31, which is an unadjusted distribution. FGOVX and VUSTX show stale-NAV catch-up jumps in the 1980s, for example VUSTX at +7.8% on 1987-10-22.

## 2. Engine numbers (protocol `full`, CA) and the standard battery

The table uses a 500-draw bootstrap, so boot_p differs by about ±0.02 from the 1000-draw values elsewhere.

| | score | full | 10/15/20y beat | boot_p | maxDD (SPY -55%) | vol | Sharpe (SPY 0.51) | DSR (12k trials) | lag-1 score | 2020-26 |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 3x SMA175/3% | +9.65 | +7.10 | 100/100/100 | 0.029-0.034 | -60% | 35% | 0.58 | 0.013 | +10.04 | +2.09 |
| C2 3x SMA200/2% | +6.07 | +4.84 | 100/100/100 | 0.100-0.117 | -59% | 36% | 0.52 | 0.003 | +7.42 | -0.29 |
| C3 low-vol 3x/1x | +5.14 | +4.68 | 100/100/100 | 0.020-0.039 | -65% | 33% | 0.53 | 0.015 | +5.37 | +5.72 |
| C4 SSO EMA100/200 (2006+) | +6.34 | +5.94 | 100/100/100 | 0.026-0.034 | -59% | 32% | 0.65 (SPY 0.65) | 0.015 | +6.04 | +2.27 |

What the battery shows beyond the table:

* Rebalance-boundary offsets do not matter for these daily rules (spread of 0.03 pp or less).
* Costs at 35 bps per side, i.e. 70 bps round trip per side pair: C1 +8.60, C2 +4.59. Turnover is low, so costs do not decide anything.
* Stricter annual distribution tax moves the excess by -0.2 to +0.1 pp.
* On 1986-2026 every one of them has a **lower Sharpe than VFINX** (0.55-0.61 vs 0.67). On the long history this is extra risk, not better risk-adjusted return.

## 3. (a) Long history

| history (CA) | C1 3x 175/3 | C2 3x 200/2 | 3x 200/3 | 2x 175/3 | 1.5x 175/3 | C3 | C4 |
|---|---|---|---|---|---|---|---|
| 2000-26 score / p / DD | +9.65 / .029 / -60% | +6.07 / .117 / -59% | +7.42 / .061 / -62% | +4.94 / .077 / -47% | +2.60 / .225 / -39% | +5.1 / .039 / -65% | +6.2 / .019 / -59% |
| 1986-26 repaired | +8.64 / .007 / -60% | +7.08 / .040 / -59% | +7.72 / .027 / -62% | +4.62 / .067 / -47% | +2.55 / .372 / -39% | +4.6 / .046 / -66% | +5.7 / .076 / -60% |
| 1986-26 one-day lag | +7.24 / .133 / **-78%** | +6.38 / .184 / **-79%** | | +3.85 / .264 / -59% | | +4.8 / .029 | +6.1 / .077 |
| **1930-85 holdout** | +6.81 / **.187** / **-88%** | +7.05 / **.159** / **-91%** | +7.17 / .093 / -88% | +2.95 / .27 / -67% | +1.0 / .46 / -53% | +3.3 / **.51**, full -0.3, 10y beat 57% | +0.4 / **.54**, full -0.2, 10y beat 39% |
| 1930-2026 | +7.29 / .046 / -88% | +6.77 / .056 / -91% | +7.48 / .024 / -88% | +3.48 / .13 / -67% | +1.5 / .46 / -53% | +2.8 / .29 / -84% | +1.8 / .28 / -83% |

Benchmark max drawdown is -55% on 2000-2026 and 1986-2026, and -81% (1930-32) on 1930-1985 and 1930-2026. In the 1930-1985 holdout the worst 10-year window for C1 is -14.6 pp/yr and its 10-year beat rate is 83%.

**October 1987.** With SMA175 and a 3% band, VFINX sat 0.9% below the SMA at the 10-15 close. The exit fired at the 10-16 close at -6.0%. That needed a fall of 2.1% or more on 10-16, and the actual fall was -5.2%, so a 3:45pm check would very likely also have fired. C2 needed a 2.7% fall. Across the neighbourhood, these groups **held the 3x fund into the -61% day**:

* 37% of daily configs: every SMA ≥ 275, SMA250 with a band of 2% or more, SMA225 with 3% or more, and SMA200 with 5%;
* 98-100% of weekly and monthly configs;
* 78% of daily configs with a one-day lag.

So the long-history significance of C1 and C2 rests on one day.

**Crash episodes, 1986-2026 repaired.** Pre-tax change from the pre-crash peak to the trough date:

| episode | VFINX | C1 3x (exit) | C1 lag-1 | C2 3x | 2x 175/3 | 3x 200/2 weekly |
|---|---|---|---|---|---|---|
| 1987 crash | -34% | -38% (10-16) | **-76%** | -38% | -24% | -76% |
| 1990 | -19% | -31% | -30% | -28% | -21% | -30% |
| 1998 | -19% | -35% | -49% | -35% | -24% | -49% |
| 2000-02 | -47% | -35% | -41% | -26% | -16% | -28% |
| 2007-09 | -55% | -16% | -15% | -24% | -7% | -26% |
| 2011 | -19% | -32% | -31% | -32% | -21% | -45% |
| 2015-16 | -13% | -19% | -29% | -31% | -12% | -46% |
| 2018 Q4 | -19% | -25% | -21% | -39% | -17% | -27% |
| 2020 | -34% | -33% | -24% | -56% | -23% | -50% |
| 2022 | -25% | -49% | -50% | -47% | -37% | -47% |
| 2025 | -19% | -26% | -25% | -26% | -18% | -26% |

In nearly every fast correction (1990, 1998, 2011, 2015-16, 2018, 2022, 2025) the 3x rule loses **more** than the index; in 2020 C1 roughly matched it. It exits after the index is down about 10%, which is a 3x fund down about 30%, and then misses part of the rebound. The edge comes from long calm uptrends at 3x and from sitting out slow bears: 2000-02, 2007-09, 1929-32 (-70% vs -84%) and 1973-74 (-37% vs -44%).

**1930-1985.** C1 still fell **-93% from 1929-09 to 1935-05**, with a pre-tax CAGR of -7.4% in 1929-39 vs -1.5% for the index. Exiting on 1929-10-24 did not save it: it re-entered on 1930s bear-market rallies at 3x.

Big down days in 1928-2026 (repaired data): C1 held the 3x fund on 13 of the 40 days of -6.5% or worse (C2: 14), mostly in 1932-38, against 71% of all days. Neither held it on any of the four days of -10% or worse (1929-10-28, 1929-10-29, 1987-10-19, 2020-03-16).

## 4. (b) Neighbourhood: 486 configs

The grid is SMA 100-300 in steps of 25, band 0-5%, D/W/M checks, and 1.5x/2x/3x leverage. 1.5x is a 50/50 mix of 1x and 2x. The engine version (SPY + SYN_SPY2XC, 5 pp drift band) gives the same CA score of +2.6 and p 0.22.

"Pass" means score > 0, full > 0, ex10_beat ≥ 0.75, ex15_beat ≥ 0.85 and boot_p ≤ 0.10, all in CA.

| history | all 486 pass | 3x daily pass (score > 0) | 3x weekly/monthly pass | 2x daily pass | 1.5x pass | median DD, 3x daily |
|---|---|---|---|---|---|---|
| 2000-26 | 4.3% | 29.6% (98%) | 3.7% / 1.9% | 3.7% | 0% | -62% |
| 1986-26 repaired | 4.9% | 33.3% (87%) | 0% / 3.7% | 7.4% | 0% | -78% |
| 1930-85 | 1.2% | 11.1% (100%) | 0% / 0% | 0% | 0% | -90% |
| 1930-2026 | 3.7% | 33.3% (100%) | 0% / 0% | 0% | 0% | -91% |

* Configs passing **both** 2000-26 and 1986-26: 13 of 486 (2.7%). Eleven are 3x daily with SMA 150-225 and a 3-5% band. The other two are 2x daily: SMA175/3% and SMA200/4%.
* Configs passing **all four** histories: **1 of 486**, the 3x daily SMA200 with a 3% band.
* Scores are positive almost everywhere at 3x. Significance only appears on a ridge whose best band moves with the era:
  * on 2000-26, bands of 3-5% are best;
  * on 1930-85, bands of 0-1% are best, and C1's own setting is not special there (+6.8, p 0.19).

The weekly and monthly checks, which an investor could actually follow more easily, almost never pass. They also hold through gap crashes (1987: -76%).

## 5. (c) Walk-forward and PBO

At each Jan 1, I picked the best config on the trailing 10 years of after-tax CA excess and applied it, freshly started, for the next 5 years. The 5-year out-of-sample windows overlap.

| history (decisions) | universe | OOS mean | OOS beat | IS mean | avg config OOS | fixed C2 OOS |
|---|---|---|---|---|---|---|
| 2000-26 (12) | all 486 | +3.0 | 67% | +14.0 | +0.0 | +5.7 |
| | 3x daily | +6.0 | 83% | +13.2 | +4.8 | |
| | 2x daily | +1.4 | 58% | | +0.5 | |
| | 1.5x daily | -1.0 | 33% | | -1.7 | |
| 1986-26 (26) | all | +5.4 | 85% | +14.5 | +2.4 | +5.8 |
| | 3x daily | +7.2 | 88% | | +4.2 | |
| | 2x daily | +4.1 | 85% | | +2.0 | |
| | 1.5x daily | +2.4 | 69% | | +0.9 | |
| 1930-2026 (82) | all | +5.5 | 73% (worst -13.0) | +12.8 | +3.2 | +8.3 |
| | 3x daily | +7.5 | 85% | | +6.7 | |
| | 2x daily | +3.2 | 82% | | +2.8 | |
| | 1.5x daily | +1.2 | 60% | | +1.0 | |

PBO (CSCV, monthly after-tax excess):

| history | all 486 | 3x daily | 2x daily |
|---|---|---|---|
| 2000-26 | 0.59 | 0.52 | 0.53 |
| 1986-26 | 0.16 | 0.47 | 0.47 |
| 1930-2026 | 0.26 | 0.71 | 0.60 |

* Walk-forward is positive out of sample, which supports the family.
* Picking parameters within a leverage level is close to a coin flip (PBO about 0.5-0.7). The trailing-best picks drift: SMA125/0-5%, then 250/4%, then 150/5%.
* The low PBO for the full grid comes from **choosing more leverage**. That is the leverage premium, not skill.

## 6. (d) Block-bootstrap risk

**d1, strategy level.** Joint monthly strategy and benchmark returns, with intra-month troughs, stationary blocks of mean length 12 months; 20,000 paths.

| | P(DD > 80%) in 20y | P(DD > 70%) in 20y | P(under SPY after tax), 10y / 20y | SPY P(DD > 60%) in 20y |
|---|---|---|---|---|
| C1 3x, 1986-2026 data | 1.5% | 9.5% | 12% / 5% | 5.7% |
| C2 3x, 1986-2026 | 4.3% | 19% | 20% / 12% | 5.7% |
| C1 3x, 1930-2026 | **17%** | 41% | 29% / 21% | 20% |
| C2 3x, 1930-2026 | **24%** | 47% | 30% / 24% | 20% |
| 2x 175/3, 1986-2026 | 0.0% | 0.3% | 25% / 16% | |
| 2x 175/3, 1930-2026 | 0.7% | 5.4% | 38% / 32% | |
| 1.5x 175/3, 1930-2026 | 0.0% | 0.4% | 53% / 51% | |

With 1-month blocks, the 3x figure for 1930-2026 is 18-21%.

**d2, market paths.** I resampled daily 1985-2026 market rows in blocks, rebuilt the signal and re-ran the rule after tax; 1,500 paths per cell. This used the unrepaired VFINX world, which makes a negligible difference here.

| | 21-day blocks: P(under) 20y | P(DD > 80%) 20y | 63-day blocks: P(under) | 252-day blocks: P(under) | 252-day: P(DD > 80%) |
|---|---|---|---|---|---|
| C1 3x | 62% | 51% | 52% | 21% | 9% |
| C2 3x | 65% | 55% | 55% | 27% | 15% |
| 2x 175/3 | 73% | 9% | 64% | 32% | 0.1% |

The edge needs trends and volatility clusters that persist for months. When paths keep only 1-3 months of persistence, the leveraged rule loses to SPY more often than not, and 3x frequently suffers an 80% drawdown.

## 7. (e) One -20% day while invested

On 1986-2026 (repaired), for every yearly start, I injected the crash on 6 evenly spaced days on which the rule held the fund. "Permanent" means -20% that is never recovered. "1987 pattern" means -20.5%, +5.3%, +9.1%. The rule sees the crash and exits at that close.

| | base 10y excess (beat) | permanent: 10y (beat) | 1987 pattern: 10y (beat) | 20y base, then 1987 pattern (beat) |
|---|---|---|---|---|
| C1 3x | +9.1 (100%) | +2.2 (74%) | +0.8 (54%) | +8.4, then +4.5 (98%) |
| C2 3x | +7.5 (97%) | +0.9 (60%) | -0.6 (43%) | +7.0, then +3.1 (94%) |
| 2x 175/3 | +4.8 (100%) | +2.1 (74%) | +0.8 (60%) | +4.8, then +2.9 (98%) |
| 1.5x 175/3 | +2.6 (87%) | +1.4 (66%) | +0.2 (51%) | +2.8, then +1.7 (90%) |

On 1930-2026 the worst 10-year result for 3x with the crash is about -25 pp/yr. How often to expect it: one such day in 98 years. The rule held 3x on about 33-35% of the large down days, so a -20% day while invested is roughly a 0.35%/yr risk, or about 7% over 20 years. At 3x it removes about 60% of the account in one close.

## 8. (f) Constant leverage at the same volatility

The engine's buy-and-hold mixes of SPY + SYN_SPY2XC, never rebalanced, on 2000-2026 CA:

| mix | score | p | DD | vol | Sharpe |
|---|---|---|---|---|---|
| 1.25x | +1.0 | 0.36 | -60% | 22.5% | 0.48 |
| 1.5x | +1.7 | 0.37 | -69% | 26% | 0.45 |
| 2x | +2.7 | 0.39 | -88% | 39% | 0.42 |

Real SPY/SSO 50/50 from 2006 scores +3.4 (p 0.11, DD -71%). On 1986-2026 the mixes score +0.8 to +2.2 (p 0.13-0.16, DD -66% to -88%, Sharpe 0.55-0.61 vs 0.67).

At equal volatility, the trend rule against constant leverage (simulator, all histories):

| volatility | trend rule | constant leverage |
|---|---|---|
| ~35% | 3x trend: +9.6 / +8.6 / +7.3 (2000-26 / 1986-26 / 1930-2026) | 1.75x: +2.4 / +1.9 / +2.2 |
| ~24% | 2x trend: +4.9 / +4.6 / +3.5 | 1.25x: +1.0 / +0.8 / +0.9 |
| ~18%, about SPY's | 1.5x trend: +2.6 / +2.5 / +1.5, DD -39% / -39% / -53% | SPY: 0, DD -55% / -55% / -81% |

So the trend filter is a much better way to hold leverage than constant leverage, worth about 3-7 pp/yr at the same volatility. Even so, at SPY-like risk the after-tax gain is only +1.5 to +2.6 pp/yr with p 0.22-0.46.

## 9. Verdicts

* **C1, 3x SMA175/3% (post hoc): FAIL** as a good-confidence recommendation.
  * It was picked after the fact, and its deflated Sharpe is 0.013.
  * The 1930-85 holdout gives p 0.19 and a worst 10-year window of -14.6.
  * With a one-day lag on 1986+, p is 0.13-0.21 and drawdown -78%.
  * PBO for the 3x daily grid is 0.47-0.71, and only 1/3 of the 3x daily grid passes. Its robust neighbour, 3x SMA200/3%, is the only config passing all four histories (CA +7.42, p 0.061 on 2000-26).
  * Even that neighbour has -88% drawdowns before 1986 and a 17-24% chance of an >80% drawdown in 20 years.
* **C2, 3x SMA200/2% (pre-registered): FAIL.** It misses the bar in its primary regime (CA p 0.100-0.117), the 1930-85 holdout gives p 0.16, its deflated Sharpe is 0.003, and it carries the same tail risk.
* **C3, low-vol 3x/1x: FAIL.** No edge in the 1930-85 holdout (score +3.3, full -0.3, 10-year beat 57%, p 0.51), a 1987 loss, and drawdowns of -65% to -84%.
* **C4, SSO EMA100/200: FAIL.** No edge in the 1930-85 holdout (+0.4, full -0.2, 10-year beat 39%, p 0.54). On 1930-2026 it scores +1.8 with p 0.28.
* **Derived: 2x daily SMA175/3%, VFITX when off: CONDITIONAL.** This is the leverage at which the risk is acceptable.
  * Drawdowns are at or below SPY's in every history: -47% vs -55% (2000-26), -47% vs -55% (1986-26), -67% vs -81% (1930-85).
  * Engine numbers on 2000-26: CA +4.94, full +3.80, 100% of 10/15/20-year windows beaten, p 0.077. FED +6.00 (p 0.041). NONE +7.74 (p 0.011).
  * On 1986-26 repaired: +4.62 (p 0.067).
  * It fails the p ≤ 0.10 bar on 1930-85 (p 0.27) and 1930-2026 (p 0.13), and its deflated Sharpe is 0.0035.
  * Bootstrapped odds of trailing SPY over 20 years: 10-32%. Under market-path resampling: 32-73%.
  * Conditions for using it: sell at the same day's close (a market-on-close order); accept a 2x daily-reset fund (SSO) and its distribution tax; accept that its edge depends on multi-month trend persistence. It is an expected-value bet with moderate confidence, not a confident edge.

About 495 configurations are added to the search: the 486-point grid plus variants. That brings the total to about 12.5k.

Files: `research/lab/families/verify_lev_robust.py` and `research/lab/scratch/verify_lev_robust/`. The main scratch files are `sim.py` / `simproto.py` (simulator), `validate_sim.py`, `sim_grid.py` and the four `out/grid_*_CA.csv` grid outputs, `walkforward.py`, `pbo.py`, `bootstrap.py`, `crash.py`, `crashdays.py`, `episodes.py`, `constlev.py`, `c3c4.py`, `final_variants.py`, and the four `out/battery_*.md` battery outputs.
