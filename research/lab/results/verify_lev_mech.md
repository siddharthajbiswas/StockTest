# verify_lev_mech: leveraged trend (3x/2x S&P with an SMA/EMA filter, else Treasuries), mechanics and realism

Adversarial audit of the round-1 leveraged-trend finalists. Scope: how the synthetic
leveraged series are built, whether they are too cheap, look-ahead and execution
timing, costs, switching and short-term gains in CA, wash sales, distribution taxes,
and real-ETF numbers next to the synthetic ones on the same windows. I did not
re-audit parameter selection or the 1986+ holdout; the round-1 numbers are cited
where needed. Total configs tried in the whole search is about 12,000, which is
the figure used for the deflated Sharpe.

## Verdict

**The mechanics hold up.** Nothing I found flatters these results by more than about
1 pp/yr of CA excess. The strongest evidence:

* **Synthetic vs real on the same windows.** Over the 2009-07..2026-07 windows, the post-hoc rule on the
  synthetic 3x fund (`SYN_SPY3XC`/IEF) scores CA **+8.86 / full +7.59**. On real
  UPRO/IEF it scores **+9.02 / +7.70**, and on SPXL/IEF **+8.86 / +7.71**. From a 2009-07 start the after-tax CAGR is
  20.71% synthetic and 20.83% real. The synthetic slightly *understates* the real ETF.
* **No look-ahead benefit.** The signal reads today's close and trades at today's close, which is the site
  convention. Deciding on yesterday's close, or executing one day late, does not hurt
  on 2000-2026; it slightly helps every candidate.
* **Costs.** At 35 bps commission plus 35 bps slippage per side, the CA score is still +8.60.
* **Taxes the engine skips.** Wash sales cost 0.03-0.10 pp/yr. Taxing distributions yearly, including
  a modeled payout for the synthetic fund, costs 0.2-0.65 pp/yr.

**Two real defects in the inputs, neither of which flatters the strategy:**

1. **The swap spread depends on the rate level, but the synthetic assumes a fixed 0.6%.**
   The synthetic matches UPRO over the full overlap (+0.05 pp/yr) only because errors in
   opposite directions cancel:
   * at zero rates the synthetic is too *expensive* (-0.22 pp/yr vs UPRO);
   * with T-bills above 2% it is too *cheap* (+0.55 pp/yr vs UPRO, +0.6 vs TQQQ, +1.09 in 2024).

   This matters most for 2000-2008, a synthetic-only period with 1-6% T-bills and
   LIBOR-based swap financing. A conservative rebuild (rate-dependent spread plus a pre-2009 LIBOR premium)
   costs buy-and-hold 3x 1.2 pp/yr in 2000-08, but costs the post-hoc rule only 0.23 of CA
   score (+9.65 -> +9.42). Even a flat 1.5% spread, which is more expensive than any real fund ever was,
   leaves +8.38.
2. **The site's SPY closes before about 2010 are noisy against the S&P 500.**
   * Daily tracking error vs the S&P 500 TR index: 6.4%/yr in 2000-02, 2.8% in 2003-07, 5.6% in 2008-09, and 0.8% after 2010.
   * The lag-1 autocorrelation of the difference is -0.47, so this is transient, mean-reverting noise (VFINX's NAV tracks the index within 0.1-0.2%).
   * Example: on 2000-01-06/07 SPY shows -1.6%/+5.8% while the index shows +0.1%/+2.7%.
   * `SYN_SPY3XC` inherits this noise times 3, and the SMA signal reads it.

   The noise *hurts* a same-close trend rule (it sells into transient dips). That is also why
   the one-day-lag tests look better on the SPY-based data. Rebuilding both the signal
   and the 3x fund on the S&P 500 TR index raises the post-hoc rule to CA **+10.10 / +7.75,
   p 0.022**. With conservative costs on top it is +9.87 / +7.39.

**The mechanics cannot fix the non-mechanical problems:**
* **Selection.** The 175/3% rule was picked post hoc. The deflated Sharpe of the after-tax monthly
  excess is 0.013 in CA (0.007 for the real-ETF version), so the excess is not
  statistically distinguishable from the best of 12,000 tries.
* **Risk.** Max drawdown is about -60% vs SPY's -55%, and equity volatility is about 1.8x SPY's.
  Most of the excess is paid-for leverage, 2.2x on average.
* **Recency.** The 2020-2026 sub-period excess is only +2.09 pp/yr in CA (pre-registered rule: -0.29).
* **Gap risk is not mechanical.** Round 1 found that with a one-day lag the 1987 crash costs -58 pp in the 1986+ synthetic.
  A trend filter cannot protect against a crash that starts from above the SMA.

| candidate | verdict | why |
|---|---|---|
| Daily trend 3x, SMA175 3% band (post hoc), SYN_SPY3XC / VFITX | **conditional** | Mechanically sound and survives every mechanical stress (worst CA score +8.38). Conditions: post-hoc pick (DSR 0.013); DD about -60%; recent edge small. |
| Real-ETF version, UPRO / IEF (2009-07+) | **conditional** | Investable; matches the synthetic; CA +9.02 / +7.70 with p 0.048. Bull-market-only sample: from a 2015 start +4.1, 2020-26 +1.85. |
| Daily-200 3x, 2% band (pre-registered) | **fail** (CA bar) | Mechanically fine, but CA boot p is 0.100-0.12 (0.088 on index data). Real UPRO 2009+ p 0.178; 2020-26 -0.29 pp/yr; from 2015 only +0.2; DSR 0.003. |
| Low-vol 3x (60-day vol < 15%), else 1x SPY | **conditional** | Mechanically robust (index data +5.71, p 0.028). Round 1 found 1/10 neighbours pass and the 1986+ CA p is 0.116. DD -65% vs -55%; it never holds less than 1x equity. |
| SSO EMA100/200 cross (2x), else IEF | **conditional** | Real SSO 2006+ CA +6.34 / +5.94, p 0.026 in the battery; synthetic 2000+ +6.17. It rests on 4 switches since 2006; its Sharpe equals SPY's, so the excess is leverage, not skill. Zero short-term gains and no wash sales. |

## 1. How the synthetic leveraged series are built

`research/lab/scratch/leverage/build_synthetic.py` defines the "C" series the conclusions use:

    r_SYN_SPY3XC(t) = 3 r_SPY(t) - 2 irx(t-1)/252 - (0.9% + 2 x 0.6%)/252

* `r_SPY` is the site's *total-return* SPY close-to-close return, so it includes dividends.
* `irx(t-1)` is the 13-week T-bill rate known at the previous close, forward-filled over bond holidays.
* The 0.9%/yr expense ratio is close to UPRO's 0.91-0.92%.
* The 0.6%/yr spread is charged on the borrowed 2x notional and was calibrated to the real funds over 2006/2009-2026 (in-sample).
* The series is daily-reset, the same as the real funds. My rebuild (`VLM_SPY3X_BASE`) matches `SYN_SPY3XC` to 2e-15.
* Open/High/Low are mapped from the underlying. Volume is "unknown", so the series is always tradable.

## 2. Synthetic vs real funds: tracking difference per year

Positive means the synthetic beat the real fund (synthetic too cheap). The source is `scratch/verify_lev_mech/tracking.py`.

| pair | overlap from | syn - real, pp/yr | years with T-bill <= 0.5% | years with T-bill > 2% | worst year |
|---|---|---|---|---|---|
| SYN_SPY3XC vs UPRO | 2009-07 | +0.05 | -0.22 | **+0.55** | +2.87 (2020) |
| SYN_SPY3XC vs SPXL | 2008-11 | +0.36 | -0.36 | +0.16 | +3.32 (2020) |
| SYN_SPY2XC vs SSO | 2006-06 | +0.02 | -0.27 | +0.29 | +0.88 (2020) |
| SYN_QQQ2XC vs QLD | 2006-06 | +0.08 | -0.35 | +0.17 | +0.99 (2008) |
| SYN_QQQ3XC vs TQQQ | 2010-02 | -0.14 | -0.54 | **+0.60** | +2.12 (2020) |

UPRO by year, syn - real in pp:

| | 2010 | 2012 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| syn - UPRO | -1.27 | -1.37 | -0.90 | -0.43 | +0.13 | +0.18 | +2.87 | -0.32 | +0.05 | +0.66 | +1.09 | +0.29 |
| T-bill % | 0.1 | 0.1 | 0.3 | 0.9 | 1.9 | 2.1 | 0.3 | 0.0 | 2.0 | 5.0 | 5.0 | 4.1 |

**Is the synthetic too cheap?**

* **Yes when rates are high:** about +0.5 pp/yr for 3x funds at T-bills of 2-5%. Real swap financing
  is roughly the T-bill rate plus 0.5% plus 0.14x the rate level, and it was LIBOR-based before 2018.
* **No at zero rates:** the synthetic is then too expensive by 0.2-0.5 pp/yr.
* **In crashes the real fund lags the formula.** The 2020 gap (+2.87) comes from March 2020 (+1.75 pp in that month alone).
  The trend rules were out of the market then, having exited 2020-02-28.

Cost-sensitivity rebuilds are in `build_variants.py` and `build_tr.py`. "B&H" below is the effect on 3x buy-and-hold CAGR.

| series | spread on the borrowed 2x | B&H 2000-08 | B&H 2009-26 | vs UPRO 2009+ |
|---|---|---|---|---|
| SYN_SPY3XC (round 1) | 0.6% flat | 0 | 0 | +0.05 |
| VLM_SPY3X_R | 0.5% + 0.14 x T-bill | -0.45 | -0.24 | **-0.21** (costlier than UPRO in every sub-period: -0.45 / -0.39 / -0.56 in 2009-16 / 2017-19 / 2022-26) |
| VLM_SPY3X_RT | R + approximate LIBOR-T-bill premium before 2009 (0.2-1.5%) | -1.22 | -0.24 | -0.21 |
| VLM_SPY3X_S10 | 1.0% flat | -0.58 | -1.04 | about -1.0 |
| VLM_SPY3X_S15 | 1.5% flat | -1.29 | -2.32 | about -2.3 |

## 3. A data defect: the site's SPY closes before about 2010

SPY vs `^SP500TR`, from `scratch/verify_lev_mech` (inline check):

| period | SPY - index: daily tracking error | lag-1 autocorrelation | VFINX - index: tracking error |
|---|---|---|---|
| 2000-02 | 6.41%/yr | -0.47 | 0.23% |
| 2003-07 | 2.78% | -0.47 | 0.07% |
| 2008-09 | 5.64% | -0.42 | 0.11% |
| 2010-19 | 0.83% | -0.49 | 0.32% |
| 2020-26 | 1.17% | -0.58 | 0.68% |

The 2000-2009 SPY closes contain transient errors that revert the next day. Examples are 2000-01-06 at the day's low and 2000-01-07 at the day's high.
These may be the 4:15 pm AMEX closes of that era or bad prints. A real 3x fund resets on the 4:00 pm
index close, so the synthetic built on SPY gets an extra volatility drag: 3x buy-and-hold 2000-09 CAGR is -27.74% vs -27.49% built on the index.

Signal and fill use the *same* noisy close, so there is no look-ahead. The noise makes the rule
sell into transient dips and buy into transient spikes, which hurts it. A one-day lag lets the noise revert before the trade.

**Fix tested.** `VLM_SPXTR` is the TR index used as the signal, and `VLM_SPX3X_TR` is the 3x fund built on the
index with the same costs. `lowvol` keeps real SPY as its 1x leg.

| rule (CA, full) | SPY-based (round 1) | index-based | index + conservative cost (RT) |
|---|---|---|---|
| post175 | +9.65 / +7.10, p 0.034 | **+10.10 / +7.75, p 0.022** | +9.87 / +7.39, p 0.028 |
| pre200 | +6.07 / +4.84, p 0.100 | +6.31 / +5.13, p 0.088 | +6.07 / +4.75, p 0.108 |
| lowvol | +5.14 / +4.68, p 0.020 | +5.71 / +4.66, p 0.028 | +5.50 / +4.38, p 0.032 |

The defect affects every SPY-signal strategy in the lab before 2010, but it is small for slow or monthly rules.

## 4. Look-ahead and execution timing

`leverage.regime` reads `np_closes(ctx, "SPY", n)`, which includes today's close, and the engine fills at today's close.
This is the site convention, not a use of future data, but no one can act on the exact close.
In practice you would place a market-on-close order around 3:45-3:50 pm. With a 2-3% hysteresis band,
the last ten minutes rarely change the decision.

The trade dates show how sensitive the rule is. On 2009+ windows the SPY-signal and index-signal versions differ by a single
whipsaw (2023-10-27 out, 2023-11-10 back in) and by one day in March 2026. That difference is worth +23.7 pp in
2023 and -6.5 pp in 2026 for that one year. Individual years are path-noisy; the full-period result is not.

| test (CA, full) | post175 | pre200 | lowvol |
|---|---|---|---|
| same close (as published) | +9.65 / +7.10 | +6.07 / +4.84 | +5.14 / +4.68 |
| signal on **yesterday's** close, trade at today's close (`conds[].lag = 1`) | +10.01 / +7.13, p 0.036 | +7.38 / +6.18, p 0.050 | +5.37 / +4.96, p 0.010 |
| execution one day late (`weights_x`, `lag: 1`) | +10.04 / +7.55, p 0.022 | +7.42 / +6.62, p 0.036 | +5.37 / +5.09, p 0.008 |
| index data, signal lag 1 | +10.17 / +7.49 | +7.62 / +6.44 | +5.91 / +4.87 |
| index data, execution lag 1 | +10.22 / +7.90, p 0.016 | +7.67 / +6.86, p 0.034 | +5.90 / +5.00 |
| signal lag 1 with RT costs | +9.79 / +6.78, p 0.042 | +7.18 / +5.85 | +5.16 / +4.68 |
| real UPRO/IEF 2009+: same close / execution lag 1 | +9.02 / +7.70 vs +8.95 / +8.04 | | |
| SSO EMA rule: same close / signal lag 1 / execution lag 1 | +6.34 / +5.94 (p 0.026) vs +6.05 / +5.63 (p 0.046) vs +6.04 / +5.70 (p 0.046) | | |

Delaying is never worse than about -0.3 pp on 2000-2026. The *exception* is the 1986+ synthetic history:
round 1 found that the same-close exit on 1987-10-16 avoided Black Monday, while lag 1 costs -58 pp in 1987 and
reaches -79% drawdown, with long-protocol CA p 0.21. That depends on a single gap event and is a risk, not a mechanics bug.

The rebalance-offset part of the standard battery does not apply to these rules. They check daily, so the offset
moves only the monthly cash top-up, and scores agree to within 0.03.

## 5. Costs

From the verify battery, per side, with commission and slippage each set to the value shown.

| CA score / full | 0 bps | 5 bps (site) | 15 bps | 35 bps |
|---|---|---|---|---|
| post175 | +9.83 / +7.30 | +9.65 / +7.10 | +9.30 / +6.70 | +8.60 / +5.92 |
| real175 | +9.22 / +7.92 | +9.02 / +7.70 | +8.64 / +7.27 | +7.88 / +6.41 |
| pre200 | +6.31 / +5.10 | +6.07 / +4.84 | +5.57 / +4.31 | +4.59 / +3.30 |
| lowvol | +5.31 / +4.84 | +5.14 / +4.68 | +4.80 / +4.37 | +4.11 / +3.76 |
| sso_ema | +6.37 / +5.98 | +6.34 / +5.94 | +6.28 / +5.85 | +6.15 / +5.69 |

Real UPRO's spread is 1-2 bps and market-on-close orders fill at the print, so 5+5 bps is already conservative.

## 6. Taxes: switching, short-term gains, wash sales, distributions

Single runs, recomputed from the engine's own trade log (`scratch/verify_lev_mech/taxmech.py`).
My FIFO replay reproduces the engine's `taxes_paid` and `terminal_tax` exactly.

| CA, first start | switches/yr (max in a year) | days in leveraged fund | round trips <= 30 days / entries | realized ST gains / ST losses / LT gains | tax paid/yr (% of equity) | wash-sale cost |
|---|---|---|---|---|---|---|
| post175 (2000) | 1.13 (3) | 72% | 1 / 15 | $0.90M / -$0.84M / $4.24M | 4.1% | **-0.03 pp/yr** (4 events, $107k of disallowed losses in 2022-23) |
| pre200 (2000) | 1.51 (5) | 74% | 4 / 20 | $0.48M / -$0.87M / $2.73M | 4.3% | -0.03 |
| lowvol (2000) | 0.87 (3) | 56% | 1 / 11 | $0.59M / -$0.20M / $1.77M | 5.4% | 0.00 |
| real175 (2009-07) | 1.18 (3) | 82% | 1 / 10 | $0.73M / -$0.62M / $3.06M | 6.5% | -0.07 |
| sso_ema (2006-07) | 0.20 (1) | 87% | 0 / 2 | $0 / -$0.01M / $1.07M | 5.3% | 0 |

Wash-sale cost from the 2005, 2010 and 2015 starts: post175 -0.04 / -0.05 / -0.07; pre200 up to -0.08; real175 up to -0.10.

**Short-term gains are not the problem.** Whipsaw exits realize short-term *losses* that offset the short-term gains,
so net short-term gains are small; most gains are long-term, realized when a multi-year leveraged run ends.
The exception is lowvol, whose net short-term gains are +$0.39M against $1.70M of net long-term gains.
Real-world reporting would add one thing: the 30-day Vanguard round-trip rule on VFITX. With 1-4 round trips of 30 days or less, use IEF.

**Tax drag.** CAGR NONE minus CAGR CA over the full window:

| | strategy | SPY |
|---|---|---|
| post175 | 4.76 pp/yr | 1.15 pp/yr |
| pre200 | 4.47 | 1.15 |
| real175 (2009+) | 7.89 | 1.98 |
| lowvol | 4.51 | 1.15 |
| sso_ema (2006+) | 2.96 | 1.57 |

So the excess shrinks from NONE to CA: post175 from +10.71 to +7.10, real175 from +13.62 to +7.70.
The engine fully charges these taxes, including January payments that compound.

**Distribution taxes charged yearly.** CA excess, engine -> stricter (`scratch/verify_lev_mech/distreal.py`).

* `realism.py` charges nothing for `SYN_*` distributions. I add model A: the synthetic pays UPRO's actual
  distributions from 2009 (SSO's for 2x), and 0.2 x the T-bill rate per year before that.
* Model B is a stress test using SPXL's history, including its 13% (2009) and 3.7% (2017) capital-gain distributions.
* All leveraged-fund distributions are taxed at the ordinary rate. Treasury interest is taxed at the federal ordinary rate plus NIIT.

| start | post175 engine | realism.py | + model A | + model B |
|---|---|---|---|---|
| 2000 | +7.10 | +6.91 | +6.79 | +6.45 |
| 2005 | +7.50 | +7.49 | +7.36 | +6.94 |
| 2010 | +6.39 | +6.43 | +6.35 | +6.18 |
| 2015 | +4.04 | +4.11 | +4.02 | +3.86 |

pre200 from 2000 goes +4.84 -> +4.69 -> +4.57 -> +4.25. lowvol goes +4.68 -> +4.82 -> +4.73 -> +4.67.
real175 (actual UPRO/IEF distributions) goes +6.70 -> +6.77 from 2010. sso_ema goes +5.94 -> +5.70 from 2006.

`verify.battery` limitation: its realism rows for real175 and sso_ema "from 2000/2005" are not valid, because `realism.record` ignores
`requires` and the strategy sat in cash or IEF until UPRO or SSO launched. Use the 2010 and 2015 rows.

## 7. Real ETFs next to the synthetic on the same windows

Every row below uses the same quarterly starts, 2009-07..2023-07, ending 2026-07.

| post175 rule | CA score / full / p | FED | NONE |
|---|---|---|---|
| **real UPRO / IEF** | **+9.02 / +7.70 / 0.048** | +10.80 / +9.89 | +13.61 / +13.62 |
| SPXL / IEF | +8.86 / +7.71 / 0.050 | | +13.43 / +13.67 |
| SYN_SPY3XC / IEF | +8.86 / +7.59 / 0.046 | +10.62 / +9.76 | +13.40 / +13.47 |
| SYN_SPY3XC / VFITX | +8.67 / +7.39 / 0.046 | +10.38 / +9.51 | +13.05 / +13.11 |
| conservative-cost synthetic / IEF | +8.78 / +7.45 / 0.052 | | +13.28 / +13.27 |

| pre200 rule | CA | FED | NONE |
|---|---|---|---|
| real UPRO / IEF | +4.50 / +4.71 / 0.178 | +5.70 / +6.54 | +7.66 / +9.79 |
| SPXL / IEF | +4.35 / +4.71 / 0.172 | | +7.50 / +9.84 |
| SYN_SPY3XC / IEF | +4.30 / +4.57 / 0.180 | +5.48 / +6.39 | +7.41 / +9.62 |

* For the SSO EMA rule on 2006-07+ windows, real SSO gives CA +6.34 / +5.94 and `SYN_SPY2XC` gives +6.24 / +5.92.
* Strategy-level CAGR from 2009-07, pre-tax: real 28.72%, synthetic/IEF 28.57%, SPXL 28.77%. After CA tax: 20.83% / 20.71% / 20.83%.
* Real-ETF max drawdown since 2009 is -61% (post175) vs SPY's -33.7% over the same span. The lab's `bench_max_dd` of -55% is the 2000-start value.

## 8. Off-asset and statistics

* **Off-state asset (post175, CA).** VFITX gives +9.65 / +7.10. VFISX gives +8.97 / +6.44. Synthetic T-bills give +8.46 / +5.83 (p 0.050).
  The 2000-2020 intermediate-Treasury rally adds about 1.2 points but is not what drives the result.
* **Deflated Sharpe** of the after-tax monthly excess, with 12,000 trials, from the battery:

  | candidate | CA | FED | NONE |
  |---|---|---|---|
  | post175 | 0.013 | 0.021 | 0.031 |
  | real175 | 0.007 | | |
  | pre200 | 0.003 | | |
  | lowvol | 0.015 | | |
  | sso_ema | 0.015 | | |

  The PSR vs zero is 0.95 for post175 in CA. The excess has a monthly Sharpe of about 0.09 because its tracking error is large;
  that is consistent with leveraged beta plus a modest timing effect, not a statistically isolated edge.
* **Sub-periods (CA).**

  | candidate | 2000-10 | 2010-20 | 2020-26 |
  |---|---|---|---|
  | post175 | +7.16 | +9.61 | +2.09 |
  | real175 | | +10.32 | +1.85 |
  | pre200 | +6.52 | +6.33 | **-0.29** |
  | lowvol | +2.57 | +6.62 | +5.72 |
  | sso_ema | | +9.06 | +2.27 |

## 9. Bugs and defects found

1. **SPY data noise before 2010.** This is in the input data, not the code: daily tracking error vs the index is 2.8-6.4%/yr and mean-reverting. It is
   inherited x3 by `SYN_SPY3XC`/`SYN_SPY2XC`, and every SPY-signal rule reads it. Impact on these rules is -0.25 to -0.6 of CA score
   (that is, conservative). It also makes "lag 1" look better than it should. Fix: build pre-2010 synthetics and signals on `^SP500TR`.
2. **Fixed 0.6% swap spread.** Too cheap at T-bill rates above 2% (+0.55 pp/yr vs UPRO) and too expensive at zero rates. Impact on the
   post-hoc rule with a conservative rate-dependent rebuild: -0.10 to -0.23 CA score.
3. **`realism.py` charges no distributions on `SYN_*` funds.** Impact: -0.1 to -0.45 pp of CA excess, depending on the model.
4. **`verify.battery` realism ignores `requires`.** Its rows for late-launch funds before launch are meaningless.
5. **`verify.battery` offset test is uninformative for daily-check signals.** Not a bug, but not evidence of robustness either.
6. **The engine does not enforce wash sales.** Measured here at -0.03 to -0.10 pp/yr.

## Appendix A: verify battery, headline tables (full protocol, n_trials 12,000)

### post175

| regime | score | full | ex5 | ex10 | ex10 beat | ex15 beat | ex20 beat | boot p | maxDD (SPY) | CAGR (SPY) | equity vol | Sharpe (SPY) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | +9.65 | +7.10 | +9.02 | +9.97 | 100% | 100% | 100% | 0.034 | -60% (-55%) | 14.20 (7.10) | 35.1% | 0.58 (0.51) | 0.013 |
| FED | +11.26 | +8.57 | +10.47 | +11.62 | 100% | 100% | 100% | 0.016 | -58% (-55%) | 16.25 (7.68) | 34.8% | 0.62 (0.51) | 0.021 |
| NONE | +13.67 | +10.71 | +12.84 | +14.07 | 100% | 100% | 100% | 0.010 | -54% (-55%) | 18.96 (8.25) | 34.6% | 0.68 (0.51) | 0.031 |


exec lag 1: NONE score +14.36 full +11.33 p 0.004, CA score +10.04 full +7.55 p 0.022

costs: 0bps: NONE +13.92/+10.98, CA +9.83/+7.30; 15bps: NONE +13.18/+10.17, CA +9.30/+6.70; 35bps: CA +8.60/+5.92, NONE +12.20/+9.10

realism: CA: 2000 +7.10->+6.91, 2005 +7.50->+7.49, 2010 +6.39->+6.43, 2015 +4.04->+4.11; FED: 2000 +8.57->+8.26, 2005 +9.21->+9.06, 2010 +8.06->+7.98, 2015 +5.30->+5.27

subperiods: FED: 2000-2010 +8.33, 2010-2020 +11.29, 2020-2026 +2.89; NONE: 2000-2010 +10.51, 2010-2020 +14.04, 2020-2026 +4.95; CA: 2000-2010 +7.16, 2010-2020 +9.61, 2020-2026 +2.09

offsets: NONE: score +13.67..+13.67; CA: score +9.65..+9.68

tax drag (full window, CAGR NONE - CA): strategy 4.76 pp/yr, SPY 1.15 pp/yr

### real175

| regime | score | full | ex5 | ex10 | ex10 beat | ex15 beat | ex20 beat | boot p | maxDD (SPY) | CAGR (SPY) | equity vol | Sharpe (SPY) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | +9.02 | +7.70 | +9.88 | +9.24 | 100% | 100% | n/a | 0.048 | -61% (-55%) | 20.83 (13.12) | 36.5% | 0.73 (0.51) | 0.007 |
| FED | +10.80 | +9.89 | +11.48 | +11.07 | 100% | 100% | n/a | 0.026 | -58% (-55%) | 24.00 (14.11) | 36.0% | 0.80 (0.51) | 0.013 |
| NONE | +13.61 | +13.62 | +14.11 | +13.91 | 100% | 100% | n/a | 0.006 | -55% (-55%) | 28.72 (15.10) | 35.7% | 0.89 (0.51) | 0.024 |


exec lag 1: NONE score +13.74 full +14.21 p 0.008, CA score +8.95 full +8.04 p 0.032

costs: 0bps: CA +9.22/+7.92, NONE +13.87/+13.92; 15bps: CA +8.64/+7.27, NONE +13.08/+13.01; 35bps: NONE +12.02/+11.81, CA +7.88/+6.41

realism: CA: 2000 +6.48->+6.54, 2005 +7.39->+7.45, 2010 +6.70->+6.77, 2015 +4.09->+4.09; FED: 2000 +7.91->+7.84, 2005 +9.15->+9.07, 2010 +8.43->+8.38, 2015 +5.37->+5.27

subperiods: FED: 2010-2020 +12.11, 2020-2026 +2.64; CA: 2010-2020 +10.32, 2020-2026 +1.85; NONE: 2010-2020 +15.07, 2020-2026 +4.67

offsets: NONE: score +13.61..+13.61; CA: score +9.02..+9.09

tax drag (full window, CAGR NONE - CA): strategy 7.89 pp/yr, SPY 1.98 pp/yr

### pre200

| regime | score | full | ex5 | ex10 | ex10 beat | ex15 beat | ex20 beat | boot p | maxDD (SPY) | CAGR (SPY) | equity vol | Sharpe (SPY) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | +6.07 | +4.84 | +5.74 | +6.19 | 100% | 100% | 100% | 0.100 | -59% (-55%) | 11.94 (7.10) | 35.9% | 0.52 (0.51) | 0.003 |
| FED | +7.27 | +6.10 | +6.79 | +7.42 | 100% | 100% | 100% | 0.074 | -57% (-55%) | 13.77 (7.68) | 35.5% | 0.56 (0.51) | 0.005 |
| NONE | +9.36 | +8.15 | +8.78 | +9.54 | 100% | 100% | 100% | 0.038 | -57% (-55%) | 16.41 (8.25) | 35.4% | 0.61 (0.51) | 0.009 |


exec lag 1: NONE score +11.35 full +10.59 p 0.014, CA score +7.42 full +6.62 p 0.036

costs: 0bps: NONE +9.70/+8.50, CA +6.31/+5.10; 15bps: NONE +8.67/+7.45, CA +5.57/+4.31; 35bps: NONE +7.31/+6.06, CA +4.59/+3.30

realism: CA: 2000 +4.84->+4.69, 2005 +3.91->+3.93, 2010 +3.48->+3.56, 2015 +0.21->+0.33; FED: 2000 +6.10->+5.82, 2005 +5.23->+5.11, 2010 +4.84->+4.79, 2015 +0.90->+0.92

subperiods: CA: 2000-2010 +6.52, 2010-2020 +6.33, 2020-2026 -0.29; FED: 2000-2010 +7.57, 2010-2020 +7.74, 2020-2026 -0.01; NONE: 2000-2010 +9.56, 2010-2020 +10.22, 2020-2026 +1.60

offsets: CA: score +6.02..+6.07; NONE: score +9.36..+9.36

tax drag (full window, CAGR NONE - CA): strategy 4.47 pp/yr, SPY 1.15 pp/yr

### lowvol

| regime | score | full | ex5 | ex10 | ex10 beat | ex15 beat | ex20 beat | boot p | maxDD (SPY) | CAGR (SPY) | equity vol | Sharpe (SPY) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | +5.14 | +4.68 | +5.11 | +5.15 | 100% | 100% | 100% | 0.020 | -65% (-55%) | 11.78 (7.10) | 33.1% | 0.53 (0.51) | 0.015 |
| FED | +6.31 | +5.97 | +6.24 | +6.29 | 100% | 100% | 100% | 0.008 | -63% (-55%) | 13.65 (7.68) | 32.7% | 0.57 (0.51) | 0.029 |
| NONE | +8.24 | +8.04 | +8.28 | +8.17 | 100% | 100% | 100% | 0.002 | -61% (-55%) | 16.30 (8.25) | 32.5% | 0.63 (0.51) | 0.049 |


exec lag 1: NONE score +8.57 full +8.51 p 0.002, CA score +5.37 full +5.09 p 0.008

costs: 0bps: NONE +8.48/+8.25, CA +5.31/+4.84; 15bps: NONE +7.77/+7.64, CA +4.80/+4.37; 35bps: NONE +6.82/+6.84, CA +4.11/+3.76

realism: CA: 2000 +4.68->+4.82, 2005 +4.67->+4.82, 2010 +5.67->+5.81, 2015 +4.71->+4.78; FED: 2000 +5.97->+6.05, 2005 +6.19->+6.28, 2010 +7.61->+7.70, 2015 +6.34->+6.39

subperiods: CA: 2000-2010 +2.57, 2010-2020 +6.62, 2020-2026 +5.72; FED: 2000-2010 +3.13, 2010-2020 +8.16, 2020-2026 +7.29; NONE: 2000-2010 +3.75, 2010-2020 +11.09, 2020-2026 +10.70

offsets: NONE: score +8.24..+8.24; CA: score +5.10..+5.14

tax drag (full window, CAGR NONE - CA): strategy 4.51 pp/yr, SPY 1.15 pp/yr

### sso_ema

| regime | score | full | ex5 | ex10 | ex10 beat | ex15 beat | ex20 beat | boot p | maxDD (SPY) | CAGR (SPY) | equity vol | Sharpe (SPY) | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | +6.34 | +5.94 | +5.96 | +6.69 | 100% | 100% | 100% | 0.026 | -59% (-55%) | 15.61 (9.67) | 31.9% | 0.65 (0.51) | 0.015 |
| FED | +6.92 | +6.62 | +6.66 | +7.24 | 100% | 100% | 100% | 0.024 | -59% (-55%) | 17.07 (10.46) | 31.6% | 0.68 (0.51) | 0.019 |
| NONE | +7.56 | +7.33 | +7.45 | +7.83 | 100% | 100% | 100% | 0.018 | -59% (-55%) | 18.57 (11.24) | 31.4% | 0.70 (0.51) | 0.021 |


exec lag 1: CA score +6.04 full +5.70 p 0.046, NONE score +7.21 full +7.08 p 0.024

costs: 0bps: NONE +7.59/+7.38, CA +6.37/+5.98; 15bps: NONE +7.49/+7.23, CA +6.28/+5.85; 35bps: CA +6.15/+5.69, NONE +7.34/+7.04

realism: CA: 2000 +5.46->+4.93, 2005 +5.22->+5.03, 2010 +5.81->+5.86, 2015 +3.64->+3.64; FED: 2000 +6.10->+5.53, 2005 +5.86->+5.61, 2010 +6.56->+6.52, 2015 +4.41->+4.34

subperiods: CA: 2010-2020 +9.06, 2020-2026 +2.27; FED: 2010-2020 +9.54, 2020-2026 +2.69; NONE: 2010-2020 +10.00, 2020-2026 +3.17

offsets: NONE: score +7.56..+7.56; CA: score +6.34..+6.35

tax drag (full window, CAGR NONE - CA): strategy 2.96 pp/yr, SPY 1.57 pp/yr


In the battery tables, `vol` and `Sharpe` come from the first start's daily equity. `maxDD (SPY)` shows the lab's
2000-start SPY drawdown even for 2006/2009 windows; SPY's own drawdown was -55% from 2006 and -34% from 2009-07.
The realism rows before a fund's launch are invalid (see section 6).


## Appendix B: every variant run (full protocol)


| variant | regime | score | full | ex10 beat | ex15 beat | ex20 beat | boot p | maxDD (SPY) | first start |
|---|---|---|---|---|---|---|---|---|---|
| post175|cost:VLM_SPY3X_R | CA | +9.55 | +6.88 | 100% | 100% | 100% | 0.038 | -61% (-55%) | 2000-01-01 |
| post175|cost:VLM_SPY3X_R | NONE | +13.53 | +10.41 | 100% | 100% | 100% | 0.010 | -54% (-55%) | 2000-01-01 |
| post175|cost:VLM_SPY3X_RT | CA | +9.42 | +6.74 | 100% | 100% | 100% | 0.038 | -61% (-55%) | 2000-01-01 |
| post175|cost:VLM_SPY3X_RT | NONE | +13.36 | +10.21 | 100% | 100% | 100% | 0.010 | -54% (-55%) | 2000-01-01 |
| post175|cost:VLM_SPY3X_S15 | CA | +8.38 | +5.92 | 100% | 100% | 100% | 0.048 | -60% (-55%) | 2000-01-01 |
| post175|cost:VLM_SPY3X_S15 | NONE | +12.02 | +9.17 | 100% | 100% | 100% | 0.014 | -54% (-55%) | 2000-01-01 |
| post175|cost:VLM_SPY3X_S10 | CA | +9.08 | +6.57 | 100% | 100% | 100% | 0.038 | -60% (-55%) | 2000-01-01 |
| post175|cost:VLM_SPY3X_S10 | NONE | +12.94 | +10.02 | 100% | 100% | 100% | 0.012 | -54% (-55%) | 2000-01-01 |
| post175|condlag1 | CA | +10.01 | +7.13 | 100% | 100% | 100% | 0.036 | -61% (-55%) | 2000-01-01 |
| post175|condlag1 | NONE | +14.33 | +10.77 | 100% | 100% | 100% | 0.016 | -55% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_R | CA | +5.97 | +4.62 | 99% | 100% | 100% | 0.116 | -59% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_R | NONE | +9.22 | +7.87 | 100% | 100% | 100% | 0.042 | -57% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_RT | CA | +5.85 | +4.48 | 99% | 100% | 100% | 0.124 | -59% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_RT | NONE | +9.05 | +7.67 | 100% | 100% | 100% | 0.050 | -57% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_S10 | CA | +5.52 | +4.31 | 94% | 100% | 100% | 0.126 | -59% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_S10 | NONE | +8.63 | +7.47 | 100% | 100% | 100% | 0.054 | -57% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_S15 | CA | +4.84 | +3.67 | 91% | 100% | 100% | 0.158 | -59% (-55%) | 2000-01-01 |
| pre200|cost:VLM_SPY3X_S15 | NONE | +7.73 | +6.62 | 99% | 100% | 100% | 0.080 | -58% (-55%) | 2000-01-01 |
| pre200|condlag1 | CA | +7.38 | +6.18 | 100% | 100% | 100% | 0.050 | -61% (-55%) | 2000-01-01 |
| pre200|condlag1 | NONE | +11.31 | +10.03 | 100% | 100% | 100% | 0.020 | -54% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_R | CA | +5.04 | +4.51 | 100% | 100% | 100% | 0.028 | -65% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_R | NONE | +8.11 | +7.82 | 100% | 100% | 100% | 0.004 | -61% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_RT | CA | +4.93 | +4.40 | 100% | 100% | 100% | 0.030 | -65% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_RT | NONE | +7.97 | +7.68 | 100% | 100% | 100% | 0.004 | -61% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_S10 | CA | +4.70 | +4.27 | 100% | 100% | 100% | 0.032 | -65% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_S10 | NONE | +7.67 | +7.52 | 100% | 100% | 100% | 0.004 | -61% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_S15 | CA | +4.16 | +3.77 | 100% | 100% | 100% | 0.048 | -65% (-55%) | 2000-01-01 |
| lowvol|cost:VLM_SPY3X_S15 | NONE | +6.97 | +6.88 | 100% | 100% | 100% | 0.006 | -61% (-55%) | 2000-01-01 |
| lowvol|condlag1 | CA | +5.37 | +4.96 | 100% | 100% | 100% | 0.010 | -65% (-55%) | 2000-01-01 |
| lowvol|condlag1 | NONE | +8.56 | +8.33 | 100% | 100% | 100% | 0.002 | -61% (-55%) | 2000-01-01 |
| post175|off:SYN_TBILL | CA | +8.46 | +5.83 | 100% | 100% | 100% | 0.050 | -58% (-55%) | 2000-01-01 |
| post175|off:SYN_TBILL | NONE | +11.94 | +8.86 | 100% | 100% | 100% | 0.016 | -51% (-55%) | 2000-01-01 |
| post175|off:VFISX | CA | +8.97 | +6.44 | 100% | 100% | 100% | 0.038 | -60% (-55%) | 2000-01-01 |
| post175|off:VFISX | NONE | +12.66 | +9.74 | 100% | 100% | 100% | 0.010 | -53% (-55%) | 2000-01-01 |
| post175|SPXL+IEF on UPRO windows | CA | +8.86 | +7.71 | 100% | 100% | n/a | 0.050 | -61% (-55%) | 2009-07-01 |
| post175|SPXL+IEF on UPRO windows | NONE | +13.43 | +13.67 | 100% | 100% | n/a | 0.008 | -55% (-55%) | 2009-07-01 |
| post175|VLM_R+IEF on UPRO windows | CA | +8.78 | +7.45 | 100% | 100% | n/a | 0.052 | -61% (-55%) | 2009-07-01 |
| post175|VLM_R+IEF on UPRO windows | NONE | +13.28 | +13.27 | 100% | 100% | n/a | 0.008 | -55% (-55%) | 2009-07-01 |
| pre200|off:SYN_TBILL | CA | +5.12 | +3.77 | 100% | 100% | 100% | 0.152 | -60% (-55%) | 2000-01-01 |
| pre200|off:SYN_TBILL | NONE | +7.94 | +6.56 | 100% | 100% | 100% | 0.086 | -58% (-55%) | 2000-01-01 |
| pre200|off:VFISX | CA | +5.56 | +4.31 | 100% | 100% | 100% | 0.128 | -59% (-55%) | 2000-01-01 |
| pre200|off:VFISX | NONE | +8.61 | +7.39 | 100% | 100% | 100% | 0.052 | -57% (-55%) | 2000-01-01 |
| pre200|SPXL+IEF on UPRO windows | CA | +4.35 | +4.71 | 100% | 100% | n/a | 0.172 | -59% (-55%) | 2009-07-01 |
| pre200|SPXL+IEF on UPRO windows | NONE | +7.50 | +9.84 | 100% | 100% | n/a | 0.066 | -58% (-55%) | 2009-07-01 |
| pre200|VLM_R+IEF on UPRO windows | CA | +4.22 | +4.43 | 93% | 100% | n/a | 0.186 | -59% (-55%) | 2009-07-01 |
| pre200|VLM_R+IEF on UPRO windows | NONE | +7.30 | +9.42 | 100% | 100% | n/a | 0.072 | -58% (-55%) | 2009-07-01 |
| sso_ema|VLM_SPY2X_RT 2000 | CA | +6.03 | +5.37 | 100% | 100% | 100% | 0.026 | -59% (-55%) | 2000-01-01 |
| sso_ema|VLM_SPY2X_RT 2000 | NONE | +7.33 | +6.70 | 100% | 100% | 100% | 0.010 | -59% (-55%) | 2000-01-01 |
| sso_ema|SYN_SPY2XC on SSO windows | CA | +6.24 | +5.92 | 100% | 100% | 100% | 0.028 | -59% (-55%) | 2006-07-01 |
| sso_ema|SYN_SPY2XC on SSO windows | NONE | +7.46 | +7.32 | 100% | 100% | 100% | 0.018 | -59% (-55%) | 2006-07-01 |
| post175|TR condlag1 | CA | +10.17 | +7.49 | 100% | 100% | 100% | 0.028 | -61% (-55%) | 2000-01-01 |
| post175|TR condlag1 | NONE | +14.40 | +11.11 | 100% | 100% | 100% | 0.012 | -55% (-55%) | 2000-01-01 |
| post175|TR+RT cost | CA | +9.87 | +7.39 | 100% | 100% | 100% | 0.028 | -60% (-55%) | 2000-01-01 |
| post175|TR+RT cost | NONE | +13.83 | +10.92 | 100% | 100% | 100% | 0.008 | -54% (-55%) | 2000-01-01 |
| post175|TR execlag1 | CA | +10.22 | +7.90 | 100% | 100% | 100% | 0.016 | -61% (-55%) | 2000-01-01 |
| post175|TR execlag1 | NONE | +14.47 | +11.67 | 100% | 100% | 100% | 0.008 | -55% (-55%) | 2000-01-01 |
| pre200|TR condlag1 | CA | +7.62 | +6.44 | 100% | 100% | 100% | 0.044 | -61% (-55%) | 2000-01-01 |
| pre200|TR condlag1 | NONE | +11.57 | +10.28 | 100% | 100% | 100% | 0.020 | -54% (-55%) | 2000-01-01 |
| pre200|TR execlag1 | CA | +7.67 | +6.86 | 100% | 100% | 100% | 0.034 | -61% (-55%) | 2000-01-01 |
| pre200|TR execlag1 | NONE | +11.63 | +10.83 | 100% | 100% | 100% | 0.010 | -54% (-55%) | 2000-01-01 |
| pre200|TR+RT cost | CA | +6.07 | +4.75 | 100% | 100% | 100% | 0.108 | -59% (-55%) | 2000-01-01 |
| pre200|TR+RT cost | NONE | +9.34 | +8.03 | 100% | 100% | 100% | 0.038 | -58% (-55%) | 2000-01-01 |
| lowvol|TR condlag1 | CA | +5.91 | +4.87 | 100% | 100% | 100% | 0.022 | -64% (-55%) | 2000-01-01 |
| lowvol|TR condlag1 | NONE | +9.10 | +8.18 | 100% | 100% | 100% | 0.002 | -61% (-55%) | 2000-01-01 |
| lowvol|TR execlag1 | CA | +5.90 | +5.00 | 100% | 100% | 100% | 0.016 | -64% (-55%) | 2000-01-01 |
| lowvol|TR execlag1 | NONE | +9.11 | +8.36 | 100% | 100% | 100% | 0.002 | -61% (-55%) | 2000-01-01 |
| lowvol|TR+RT cost | CA | +5.50 | +4.38 | 100% | 100% | 100% | 0.032 | -64% (-55%) | 2000-01-01 |
| lowvol|TR+RT cost | NONE | +8.67 | +7.64 | 100% | 100% | 100% | 0.006 | -61% (-55%) | 2000-01-01 |
| sso_ema|siglag1 | CA | +6.05 | +5.63 | 100% | 100% | 100% | 0.046 | -62% (-55%) | 2006-07-01 |
| sso_ema|siglag1 | NONE | +7.22 | +7.00 | 100% | 100% | 100% | 0.024 | -59% (-55%) | 2006-07-01 |
| pre200|condlag1+RT | CA | +7.18 | +5.85 | 100% | 100% | 100% | 0.066 | -61% (-55%) | 2000-01-01 |
| lowvol|condlag1+RT | CA | +5.16 | +4.68 | 99% | 100% | 100% | 0.018 | -65% (-55%) | 2000-01-01 |
| pre200|TR+RT cost condlag1 | CA | +7.39 | +6.07 | 100% | 100% | 100% | 0.052 | -61% (-55%) | 2000-01-01 |
| post175|condlag1+RT | CA | +9.79 | +6.78 | 100% | 100% | 100% | 0.042 | -61% (-55%) | 2000-01-01 |
| post175|TR+RT cost condlag1 | CA | +9.94 | +7.13 | 100% | 100% | 100% | 0.036 | -61% (-55%) | 2000-01-01 |
| lowvol|TR+RT cost condlag1 | CA | +5.69 | +4.59 | 99% | 100% | 100% | 0.030 | -64% (-55%) | 2000-01-01 |
| post175|UPRO+IEF (real) | CA | +9.02 | +7.70 | 100% | 100% | n/a | 0.048 | -61% (-55%) | 2009-07-01 |
| post175|UPRO+IEF (real) | FED | +10.80 | +9.89 | 100% | 100% | n/a | 0.026 | -58% (-55%) | 2009-07-01 |
| post175|UPRO+IEF (real) | NONE | +13.61 | +13.62 | 100% | 100% | n/a | 0.006 | -55% (-55%) | 2009-07-01 |
| sso_ema|SYN_SPY2XC 2000 | CA | +6.17 | +5.59 | 100% | 100% | 100% | 0.020 | -59% (-55%) | 2000-01-01 |
| sso_ema|SYN_SPY2XC 2000 | FED | +6.80 | +6.26 | 100% | 100% | 100% | 0.014 | -59% (-55%) | 2000-01-01 |
| sso_ema|SYN_SPY2XC 2000 | NONE | +7.51 | +6.97 | 100% | 100% | 100% | 0.006 | -59% (-55%) | 2000-01-01 |
| post175|SYN+VFITX on UPRO windows | CA | +8.67 | +7.39 | 100% | 100% | n/a | 0.046 | -60% (-55%) | 2009-07-01 |
| post175|SYN+VFITX on UPRO windows | FED | +10.38 | +9.51 | 100% | 100% | n/a | 0.024 | -58% (-55%) | 2009-07-01 |
| post175|SYN+VFITX on UPRO windows | NONE | +13.05 | +13.11 | 100% | 100% | n/a | 0.006 | -54% (-55%) | 2009-07-01 |
| post175|SYN+IEF on UPRO windows | CA | +8.86 | +7.59 | 100% | 100% | n/a | 0.046 | -61% (-55%) | 2009-07-01 |
| post175|SYN+IEF on UPRO windows | FED | +10.62 | +9.76 | 100% | 100% | n/a | 0.024 | -58% (-55%) | 2009-07-01 |
| post175|SYN+IEF on UPRO windows | NONE | +13.40 | +13.47 | 100% | 100% | n/a | 0.006 | -55% (-55%) | 2009-07-01 |
| pre200|SYN+VFITX on UPRO windows | CA | +4.28 | +4.52 | 100% | 100% | n/a | 0.176 | -59% (-55%) | 2009-07-01 |
| pre200|SYN+VFITX on UPRO windows | FED | +5.45 | +6.31 | 100% | 100% | n/a | 0.122 | -57% (-55%) | 2009-07-01 |
| pre200|SYN+VFITX on UPRO windows | NONE | +7.36 | +9.48 | 100% | 100% | n/a | 0.070 | -57% (-55%) | 2009-07-01 |
| pre200|SYN+IEF on UPRO windows | CA | +4.30 | +4.57 | 100% | 100% | n/a | 0.180 | -59% (-55%) | 2009-07-01 |
| pre200|SYN+IEF on UPRO windows | FED | +5.48 | +6.39 | 100% | 100% | n/a | 0.120 | -58% (-55%) | 2009-07-01 |
| pre200|SYN+IEF on UPRO windows | NONE | +7.41 | +9.62 | 100% | 100% | n/a | 0.070 | -58% (-55%) | 2009-07-01 |
| pre200|UPRO+IEF (real) | CA | +4.50 | +4.71 | 100% | 100% | n/a | 0.178 | -59% (-55%) | 2009-07-01 |
| pre200|UPRO+IEF (real) | FED | +5.70 | +6.54 | 100% | 100% | n/a | 0.116 | -58% (-55%) | 2009-07-01 |
| pre200|UPRO+IEF (real) | NONE | +7.66 | +9.79 | 100% | 100% | n/a | 0.062 | -58% (-55%) | 2009-07-01 |
| post175|TR | CA | +10.10 | +7.75 | 100% | 100% | 100% | 0.022 | -60% (-55%) | 2000-01-01 |
| post175|TR | FED | +11.75 | +9.28 | 100% | 100% | 100% | 0.012 | -57% (-55%) | 2000-01-01 |
| post175|TR | NONE | +14.15 | +11.42 | 100% | 100% | 100% | 0.006 | -54% (-55%) | 2000-01-01 |
| pre200|TR | CA | +6.31 | +5.13 | 100% | 100% | 100% | 0.088 | -59% (-55%) | 2000-01-01 |
| pre200|TR | FED | +7.54 | +6.43 | 100% | 100% | 100% | 0.062 | -58% (-55%) | 2000-01-01 |
| pre200|TR | NONE | +9.66 | +8.52 | 100% | 100% | 100% | 0.028 | -58% (-55%) | 2000-01-01 |
| lowvol|TR | CA | +5.71 | +4.66 | 100% | 100% | 100% | 0.028 | -64% (-55%) | 2000-01-01 |
| lowvol|TR | FED | +6.95 | +5.94 | 100% | 100% | 100% | 0.008 | -63% (-55%) | 2000-01-01 |
| lowvol|TR | NONE | +8.94 | +8.02 | 100% | 100% | 100% | 0.002 | -61% (-55%) | 2000-01-01 |

## Files

* `research/lab/families/verify_lev_mech.py` holds the FIFO tax replay with the wash-sale rule (validated
  against the engine to the dollar) and the switch statistics. It registers and patches nothing.
* `research/lab/scratch/verify_lev_mech/` holds the scripts and outputs:
  * `run_battery.py` -> `battery/*.json|md`
  * `tracking.py` -> `tracking_*.csv`
  * `build_variants.py`, `build_tr.py` -> `data/VLM_*.csv` (scratch only; loaded in-process by `inject.py`)
  * `run_variants.py` -> `variants.json`
  * `taxmech.py` -> `taxmech.json`
  * `distreal.py` -> `distreal.json`
  * `strat_track.py` -> `strat_track.json`
  * `summarize.py`

About 110 configuration runs were added in this audit; all are robustness variants of the five candidates, not new strategy ideas.
