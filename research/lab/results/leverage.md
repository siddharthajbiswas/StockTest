# Leveraged-ETF strategies (family `leverage`)

The question: does any strategy built on leveraged ETFs beat buying and holding
SPY **after California tax (48.1% short-term / 28.1% long-term) and trading
costs, with good confidence**? FED (35/15) is secondary; NONE (no tax) is a
diagnostic. Every number below comes from the lab (`research/lab`, the website's
engine, 5 bps commission + 5 bps slippage per side) and is reproducible from the
scripts in `research/lab/scratch/leverage/`. "Excess" is after-tax CAGR minus
SPY's, in percentage points per year (pp). "Score" is the pre-registered
`report.score` (mean of the average 5-, 10- and 15-year window excess).

This report resumes an interrupted run: the coarse screen, the first finalist
selection and part of the `full` runs were done before the interruption; the
long-history holdout, neighbourhoods, execution/timing tests, hindsight checks,
diagnostics and this write-up were completed afterwards. Nothing earlier was
discarded.

## 1. Verdict

**No leveraged-ETF strategy clears every item of the PROTOCOL section 3 bar for
the CA taxable account.** One region comes close, but it was found after the
fact and has a specific, testable fragility.

**The closest rule ("Daily trend 3x, 3% band", found post hoc):** hold 3x S&P.
Switch to intermediate Treasuries when SPY closes more than 3% below its 175-day
average, and switch back when it closes more than 3% above. Checked daily, traded
at the close. Config label: `SYN/trend/on=x3/off=mid/sma175/b0.03/D`. The 3x S&P
leg is UPRO in the real-ETF test and the calibrated synthetic `SYN_SPY3XC` in the
2000-2026 and 1986-2026 tests. The Treasury leg is IEF in the real-ETF test,
Vanguard's VFITX in the 2000-2026 test and the Fidelity government fund FGOVX in
the 1986-2026 test.

| | CA | FED | NONE |
|---|---|---|---|
| 2000-2026 (`full`): score / full excess, pp/yr | +9.65 / +7.10 | +11.26 / +8.57 | +13.67 / +10.71 |
| 10-yr windows beating SPY (worst) / 15-yr beating | 1.00 (+4.81) / 1.00 | 1.00 (+6.06) / 1.00 | 1.00 (+7.97) / 1.00 |
| bootstrap p | 0.029 | 0.016 | 0.007 |
| real ETFs only, 2009-2026: score / p | +9.03 / 0.031 | +10.80 / 0.018 | +13.61 / 0.005 |
| 1986-2026 synthetic (`long`): 10-yr windows ending before 2000 (beat) / p | +7.81 (1.00) / 0.022 | | +10.83 (1.00) / 0.003 |
| max drawdown (SPY), 2000-2026 | -60.5% (-55.2%) | -57.5% (-55.2%) | -54.2% (-55.2%) |

Its 8 neighbours (SMA150-200 x bands 2-4%) all beat SPY in CA (screen scores
+5.5 to +8.9; the rule itself +9.8). 5 of 8 pass items 1-3, and every 3-4% band
member does, on both 2000-2026 and 1986-2026. It averages 2.2x equity exposure,
with after-tax monthly volatility of 24% against SPY's 14%. Its Sharpe ratio is 0.58 against 0.51 (M2
+0.9 pp/yr; 0 to +0.9 across the plateau). Mostly it beats SPY by taking more
risk, and it is modestly better risk-adjusted as well. Why it still does not pass:

1. **Item 4 fails at the family level.** The probability of backtest overfitting
   is 0.67 for the 745-config SYN screen (0.83 on the coarse grid alone), and the
   best config's deflated Sharpe is 0.20 over 900+ configurations. The trend
   sub-family alone has PBO 0.39, but only after the neighbourhood refinements
   were added.
2. **It was selected after seeing the data.** The first run's pre-registered
   finalist was the same rule with a 2% band (`.../sma200/b0.02/D`), which fails
   item 3 in CA (p = 0.117). The 3% band became the leader only in the
   neighbourhood scan. The 1986-1999 holdout was not used to choose it, but the
   1986+ results of the 1-3% band grid had been seen before it was singled out.
3. **Its holdout success hinges on one day.** The one gap crash in 40 years of
   data is 1987-10-19 (-20.5%). Every daily rule in the plateau escaped it
   because VFINX closed 4.5-7% below its 150-200-day averages on Friday
   1987-10-16, and the lab (like the website) trades at the close of the signal
   day. Decide at that close
   but trade at the next one (`lag1`) and the same rule is -58 pp vs the index in
   1987, -79% drawdown, p = 0.21 on 1986-2026. Over 2000-2026 the lag is harmless
   (CA +10.01, p = 0.031). A weekly or monthly check (tested on the SMA200
   version: -60 and -50 pp in 1987) also sells after the crash. So would a band
   wider than the 4.5-7% gap below the average that opened on 10-16.

**Everything else fails more clearly:**

* **The pre-registered finalists.** Daily SMA200 with a 2% band (CA p = 0.117).
  Low-vol gating (CA p = 0.039, but 1/10 neighbours pass and p = 0.12 on
  1986-2026). The first run's top scorer, Monthly-100 3x (CA +6.52, p = 0.100),
  is check-day luck: moving its monthly check by one week cuts the score to +1.1,
  and it held 3x through Black Monday (-50 pp in 1987, -81% drawdown).
* **Static leverage is a regime bet.** UPRO bought in July 2009 (real ETF) beat
  SPY by +17.1 pp/yr after CA tax (p = 0.004). The same 3x exposure bought in
  January 2000 (synthetic, validated against UPRO) trailed SPY by -1.3 pp/yr,
  with a -98% drawdown; its worst start was left with 3% of the money after tax.
  HFEA, 50/50 SSO/SPY and 33/67 UPRO/SPY all fail.
* **Vol targeting, dip buying and the QQQ rules fail.** Vol targeting and dip
  buying are negative in CA. The QQQ rules' edge is the choice of QQQ (on 20
  random menus the median edge is +0.25 pp or below zero).

**Practical answer for this account.** The evidence that a leveraged-ETF rule
beats SPY after California tax is real but not "good confidence" under the lab's
rules. Daily-checked, 3x S&P with a wide trend band and Treasuries as the
off-asset is the one design that survives most checks. Anyone using it holds 3x
S&P exposure about 70% of the time (2.2x on average), with -60% drawdowns and
about -80% in a 1987-style gap.
They also face years like 2000 (-24% against SPY's -9%), 2007 (-18% vs +4%) and
2022 (-43% vs -17%), and the operational burden of acting at the close on the
day of the signal. Size it as a high-risk sleeve, not as a replacement for SPY.

## 2. What was tested

**930 distinct configurations have at least one result**
(2553 were defined in `labels.json`; most of the remainder are the dense
refinement grids that the interrupted run defined but never ran, and they were
pruned for compute). Sub-families:

* **bh**: buy and hold 2x / 3x (S&P, Nasdaq-100, plus every real leveraged ETF in the lab), and 50/50 / 67/33 never-rebalanced mixes.
* **mix**: fixed mixes rebalanced on the calendar (M/Q/A) or by drift bands (5 pp, 10 pp, 25% relative). Covers 2x/3x S&P with 1x SPY, T-bills, intermediate or long Treasuries, 3x Treasuries (HFEA 55/45 UPRO/TMF and neighbours, 50% SSO + 50% SPY, 33% UPRO + 67% SPY, SSO + IEF), plus tax-aware execution with a gain budget.
* **trend**: 2x/3x (or 50% SPY + 50% 3x) while a trend rule is on, else 1x SPY / T-bills / intermediate or long Treasuries / cash. Rules: SMA 75-250, EMA, 50/200 cross, 6/12-month time-series momentum; bands 0-5%; daily/weekly/monthly checks; confirmation days; lag-1; ^GSPC signal; tax-aware execution.
* **trend3**: 3- and 4-state ladders (3x / 2x / 1x / safe by how many trend rules agree).
* **vt**: volatility targeting 10-35% with 2x/3x funds, with and without a trend cap.
* **lowvol**: leverage only while realised volatility (20-120 days, EWMA) or VIX is below a threshold, optionally combined with a trend filter.
* **misc**: yield-curve gate, dip buying, near-high gate.
* **overlay**: never-sold SPY core plus a trend-switched 3x satellite.
* **dualmom / qqq-trend**: leveraged dual momentum (SPY/QQQ, 4 US indexes, SPY/EFA), QQQ-signal 2x/3x trend. Both are QQQ-dependent, so they get hindsight checks.

Instrument sets (the same rule is run on each where it applies):

* **SYN**: 2000-2026. Research-only synthetic daily-reset leveraged series built on the total-return underlying, `L x r - (L-1) x T-bill - expenses`, plus a calibrated swap spread of 0.6%/yr on the borrowed notional ("C" series). Treasuries via Vanguard funds, T-bills via a synthetic T-bill fund. Validation is below.
* **REAL**: the real leveraged ETFs (SSO, UPRO, QLD, TQQQ, TMF ... with BIL, SHY, IEF, TLT). Windows start only once all of them exist (2006-07 or 2009-07), so this is a bull-market-only sample.
* **LONG**: 1986-2026, benchmark VFINX (the `long` / `long_screen` protocols). Synthetic 2x/3x VFINX, synthetic T-bills, FGOVX (government bonds), VUSTX. Windows that end before 2000 (`ho5_*`, `ho10_*`) are a true holdout for rules designed on 2000-2026.
* **RAW**: the brief's uncalibrated synthetic formula (no swap spread), a sensitivity check.

**Synthetic validation.** The calibrated series used by the SPY-based rules track
their real funds within 0.1 pp/yr: SSO +0.07, UPRO +0.03, SPXL +0.04, TMF +0.09.
Other series are within 0.9 pp/yr, the worst being 2x long Treasuries (-0.85) and
3x small caps (+0.52). The leveraged series' daily correlation with their real
funds is 0.985-0.999.

| synthetic | real fund | overlap | CAGR syn | CAGR real | difference /yr | tracking error | daily corr | max DD syn / real |
|---|---|---|---|---|---|---|---|---|
| SYN_TBILL | BIL | 2007-05-30..2026-07-01 | 1.35% | 1.36% | -0.02 | 0.5% | 0.2391 | -0.3% / -0.8% |
| SYN_TBILL | SHV | 2007-01-11..2026-07-01 | 1.42% | 1.58% | -0.16 | 0.3% | 0.3400 | -0.3% / -0.5% |
| SYN_SPY2XC | SSO | 2006-06-21..2026-07-01 | 15.74% | 15.67% | +0.07 | 3.7% | 0.9956 | -84.4% / -84.7% |
| SYN_SPY3XC | UPRO | 2009-06-25..2026-07-01 | 32.85% | 32.82% | +0.03 | 3.0% | 0.9983 | -76.2% / -76.8% |
| SYN_SPY3XC | SPXL | 2008-11-05..2026-07-01 | 28.45% | 28.40% | +0.04 | 4.3% | 0.9971 | -76.2% / -76.9% |
| SYN_QQQ2XC | QLD | 2006-06-21..2026-07-01 | 25.66% | 25.57% | +0.09 | 4.0% | 0.9960 | -82.5% / -83.1% |
| SYN_QQQ3XC | TQQQ | 2010-02-11..2026-07-01 | 43.48% | 43.63% | -0.14 | 3.0% | 0.9989 | -81.5% / -81.7% |
| SYN_VFINX2XC | SSO | 2006-06-21..2026-07-01 | 15.57% | 15.67% | -0.10 | 3.8% | 0.9953 | -84.4% / -84.7% |
| SYN_VFINX3XC | UPRO | 2009-06-25..2026-07-01 | 32.50% | 32.82% | -0.32 | 3.3% | 0.9979 | -76.7% / -76.8% |
| SYN_LTB3XC | TMF | 2009-04-16..2026-07-01 | -5.78% | -5.87% | +0.09 | 3.6% | 0.9967 | -92.7% / -92.7% |
| SYN_MDY2XC | MVV | 2006-06-21..2026-07-01 | 11.21% | 11.59% | -0.38 | 5.3% | 0.9931 | -85.7% / -85.5% |
| SYN_DIA2XC | DDM | 2006-06-21..2026-07-01 | 14.32% | 14.34% | -0.01 | 4.5% | 0.9929 | -81.5% / -81.7% |
| SYN_IWM2XC | UWM | 2007-01-25..2026-07-01 | 7.63% | 7.53% | +0.10 | 4.0% | 0.9968 | -87.8% / -88.2% |
| SYN_IWM3XC | TNA | 2008-11-19..2026-07-01 | 17.16% | 16.65% | +0.52 | 3.5% | 0.9988 | -87.5% / -88.1% |
| SYN_TLT2XC | UBT | 2010-01-21..2026-07-01 | -0.23% | 0.62% | -0.85 | 5.2% | 0.9848 | -78.7% / -78.9% |

Run through the same strategies over the real funds' lifetime, the SYN versions
reproduce the real-ETF results within -0.31 to +0.06 pp/yr (CA and NONE, 9
strategies, from 2006-07 / 2009-07). The synthetic history is therefore a fair
stand-in for 2000-2009.

Configurations with results, by instrument set, sub-family, protocol and regime:

| set | sub-family | screen CA | screen NONE | full CA | full FED | full NONE | long_screen CA | long_screen FED | long_screen NONE | long CA | long NONE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG | bh |  |  |  |  |  | 2 | 2 | 2 |  |  |
| LONG | lowvol |  |  |  |  |  | 16 | 2 | 16 | 2 | 2 |
| LONG | mix |  |  |  |  |  | 4 | 4 | 4 |  |  |
| LONG | trend |  |  |  |  |  | 34 | 8 | 34 | 4 | 4 |
| LONG | vt |  |  |  |  |  | 1 | 1 | 1 |  |  |
| RAW | lowvol |  |  | 1 |  | 1 |  |  |  |  |  |
| RAW | mix |  |  | 1 |  | 1 |  |  |  |  |  |
| RAW | trend |  |  | 2 |  | 2 |  |  |  |  |  |
| REAL | bh | 6 | 6 | 3 | 3 | 3 |  |  |  |  |  |
| REAL | lowvol |  |  | 2 | 2 | 2 |  |  |  |  |  |
| REAL | mix | 52 | 48 | 1 | 1 | 1 |  |  |  |  |  |
| REAL | trend |  |  | 5 | 5 | 5 |  |  |  |  |  |
| REAL | vt |  |  | 1 | 1 | 1 |  |  |  |  |  |
| SYN | bh | 8 | 8 | 4 | 4 | 4 |  |  |  |  |  |
| SYN | dualmom | 28 | 28 | 2 | 2 | 2 |  |  |  |  |  |
| SYN | hindsight random menus | 40 | 40 |  |  |  |  |  |  |  |  |
| SYN | lowvol | 104 | 105 | 3 | 3 | 3 |  |  |  |  |  |
| SYN | misc | 13 | 13 |  |  |  |  |  |  |  |  |
| SYN | mix | 144 | 144 | 4 | 4 | 4 |  |  |  |  |  |
| SYN | overlay | 24 | 24 |  |  |  |  |  |  |  |  |
| SYN | qqq-trend | 24 | 24 | 1 | 1 | 1 |  |  |  |  |  |
| SYN | trend | 304 | 304 | 15 | 15 | 15 |  |  |  |  |  |
| SYN | trend (timing-luck emulation) |  |  | 8 |  | 8 |  |  |  |  |  |
| SYN | trend3 | 24 | 24 |  |  |  |  |  |  |  |  |
| SYN | vt | 79 | 79 | 1 | 1 | 1 |  |  |  |  |  |
| **all** |  | 850 | 847 | 54 | 42 | 54 | 57 | 17 | 57 | 6 | 6 |

Of the 754 SYN configurations screened from 2000 (screen protocol), 19 pass
PROTOCOL items 1-3 in CA: 14 daily or weekly 3x trend rules and 5 low-vol rules,
all on the S&P with Treasuries or SPY as the off-asset. In NONE, 124 pass.

## 3. Headline results (protocol `full`: 95 quarterly starts 2000-01 to 2023-07)

### CA (primary)

| config | from | after-tax CAGR to 2026-07 (SPY) | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | max DD (SPY) | trades | turnover/yr | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | 2000-01 | 14.2% (7.1%) | +9.65 | +7.10 | +9.97 | 1.00 | +4.81 | 1.00 | 1.00 | 0.029 | -60.5% (-55.2%) | 107 | 1.36 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | 2000-01 | 11.9% (7.1%) | +6.07 | +4.84 | +6.19 | 1.00 | +0.22 | 1.00 | 1.00 | 0.117 | -58.8% (-55.2%) | 108 | 1.54 | no |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | 2000-01 | 11.8% (7.1%) | +5.14 | +4.68 | +5.15 | 1.00 | +0.89 | 1.00 | 1.00 | 0.039 | -65.1% (-55.2%) | 68 | 1.03 | yes |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | 2000-01 | 12.2% (7.1%) | +6.52 | +5.06 | +6.47 | 1.00 | +1.16 | 1.00 | 1.00 | 0.100 | -60.9% (-55.2%) | 102 | 1.37 | yes |
| SYN/trend/on=x3/off=tbill/sma100/b0.02/M | 2000-01 | 11.3% (7.1%) | +5.73 | +4.25 | +5.64 | 1.00 | +0.48 | 1.00 | 1.00 | 0.137 | -61.0% (-55.2%) | 96 | 1.37 | no |
| SYN/trend/on=x2/off=mid/sma100/b0.02/M | 2000-01 | 9.7% (7.1%) | +3.10 | +2.60 | +3.08 | 0.82 | -1.81 | 0.83 | 1.00 | 0.157 | -46.6% (-55.2%) | 100 | 1.37 | no |
| SYN/trend/on=x2/off=one/sma100/b0.02/M | 2000-01 | 8.3% (7.1%) | +2.33 | +1.20 | +2.31 | 1.00 | +0.57 | 1.00 | 1.00 | 0.278 | -63.2% (-55.2%) | 91 | 1.41 | no |
| SYN/trend/on=one.5x3.5/off=one/sma200/b0.02/D | 2000-01 | 9.0% (7.1%) | +3.07 | +1.93 | +3.17 | 1.00 | +0.36 | 1.00 | 1.00 | 0.153 | -62.7% (-55.2%) | 549 | 0.94 | no |
| SYN/trend/on=x2/off=one/sma200/b0.02/M | 2000-01 | 8.8% (7.1%) | +2.31 | +1.73 | +2.28 | 0.97 | -0.61 | 1.00 | 1.00 | 0.192 | -62.4% (-55.2%) | 53 | 0.78 | no |
| SYN/trend/on=x3/off=tbill/sma200/b0.0/D | 2000-01 | 7.7% (7.1%) | +2.69 | +0.58 | +2.90 | 0.76 | -4.39 | 0.96 | 0.93 | 0.469 | -67.3% (-55.2%) | 378 | 4.98 | no |
| SYN/lowvol/rv60<0.15/b0.1/on=x2/off=one | 2000-01 | 8.6% (7.1%) | +1.87 | +1.54 | +1.90 | 1.00 | +0.31 | 1.00 | 1.00 | 0.140 | -61.0% (-55.2%) | 67 | 1.03 | no |
| SYN/vt/t0.25/w20/x2/M/eb0.15/trend=sma200 | 2000-01 | 7.4% (7.1%) | +0.94 | +0.32 | +1.02 | 0.73 | -0.86 | 0.89 | 1.00 | 0.419 | -54.6% (-55.2%) | 303 | 2.44 | no |
| SYN/mix/x30.55+b30.45/calQ | 2000-01 | 10.6% (7.1%) | +6.72 | +3.51 | +7.20 | 0.87 | -2.35 | 1.00 | 1.00 | 0.183 | -75.1% (-55.2%) | 214 | 0.30 | no |
| SYN/mix/x30.4+mid0.6/calA | 2000-01 | 7.6% (7.1%) | +1.07 | +0.46 | +1.15 | 0.79 | -0.68 | 0.96 | 1.00 | 0.278 | -49.7% (-55.2%) | 54 | 0.12 | no |
| SYN/mix/x20.5+one0.5/band0.1 | 2000-01 | 8.2% (7.1%) | +1.90 | +1.14 | +1.95 | 0.82 | -4.02 | 0.87 | 0.96 | 0.272 | -72.6% (-55.2%) | 18 | 0.02 | no |
| SYN/mix/x30.3333+one0.6667/calQ | 2000-01 | 7.9% (7.1%) | +2.13 | +0.82 | +2.19 | 0.81 | -6.00 | 0.87 | 0.89 | 0.347 | -78.9% (-55.2%) | 214 | 0.13 | no |
| SYN/bh/x2 | 2000-01 | 7.9% (7.1%) | +2.74 | +0.82 | +2.82 | 0.70 | -9.87 | 0.83 | 0.85 | 0.394 | -88.4% (-55.2%) | 1 | 0.00 | no |
| SYN/bh/x3 | 2000-01 | 5.8% (7.1%) | +3.09 | -1.32 | +3.21 | 0.52 | -21.90 | 0.72 | 0.81 | 0.527 | -98.2% (-55.2%) | 1 | 0.00 | no |
| SYN/dualmom/us4-2x/lb252/top2/safe=mid | 2000-01 | 9.1% (7.1%) | +3.50 | +2.04 | +3.71 | 0.70 | -3.32 | 0.85 | 1.00 | 0.258 | -58.4% (-55.2%) | 636 | 2.07 | no |
| SYN/dualmom/spy/qqq-2x/lb252/top1/safe=mid | 2000-01 | 10.0% (7.1%) | +5.60 | +2.88 | +5.85 | 0.97 | -0.49 | 1.00 | 1.00 | 0.230 | -73.1% (-55.2%) | 106 | 2.26 | no |
| SYN/qtrend/on=q3/off=tbill/qqq-sma200/D | 2000-01 | 7.3% (7.1%) | +5.37 | +0.24 | +5.59 | 0.73 | -14.94 | 0.85 | 0.89 | 0.474 | -95.4% (-55.2%) | 376 | 3.39 | no |

Real ETFs (first start 2009-07 for UPRO/TMF, 2006-07 for SSO/QLD; SPY's drawdown
over the same period in brackets):

| config | from | after-tax CAGR to 2026-07 (SPY) | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | max DD (SPY) | trades | turnover/yr | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | 2009-07 | 20.8% (13.1%) | +9.03 | +7.70 | +9.24 | 1.00 | +4.90 | 1.00 | n/a | 0.031 | -61.4% (-33.7%) | 74 | 1.38 | yes |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | 2009-07 | 17.8% (13.1%) | +4.50 | +4.71 | +3.72 | 1.00 | +0.11 | 1.00 | n/a | 0.157 | -58.8% (-33.7%) | 73 | 1.55 | no |
| REAL/lowvol/rv60<0.15/on=x3/off=one | 2009-07 | 18.1% (13.1%) | +6.43 | +5.01 | +6.11 | 1.00 | +4.29 | 1.00 | n/a | 0.087 | -53.9% (-33.7%) | 67 | 1.10 | yes |
| REAL/trend/on=x3/off=mid/sma100/b0.02/M | 2009-07 | 17.1% (13.1%) | +5.16 | +4.02 | +5.07 | 1.00 | +1.67 | 1.00 | n/a | 0.202 | -60.9% (-33.7%) | 77 | 1.39 | no |
| REAL/trend/on=x3/off=tbill/sma100/b0.02/M | 2009-07 | 17.1% (13.1%) | +5.30 | +4.02 | +5.16 | 1.00 | +0.79 | 1.00 | n/a | 0.213 | -60.9% (-33.7%) | 73 | 1.40 | no |
| REAL/trend/on=x2/off=mid/sma100/b0.02/M | 2006-07 | 11.4% (9.7%) | +1.92 | +1.76 | +1.44 | 0.66 | -1.43 | 0.67 | 1.00 | 0.292 | -47.2% (-55.2%) | 87 | 1.42 | no |
| REAL/lowvol/rv60<0.15/on=x2/off=one | 2006-07 | 11.2% (9.7%) | +1.89 | +1.55 | +2.12 | 1.00 | +1.13 | 1.00 | 1.00 | 0.206 | -60.0% (-55.2%) | 66 | 1.10 | no |
| REAL/mix/x30.55+b30.45/calQ | 2009-07 | 19.5% (13.1%) | +6.28 | +6.35 | +6.83 | 0.76 | -2.28 | 1.00 | n/a | 0.148 | -75.0% (-33.7%) | 138 | 0.30 | no |
| REAL/vt/t0.25/w20/x2/M/trend=sma200 | 2007-07 | 9.7% (9.2%) | +0.47 | +0.53 | +0.43 | 0.59 | -0.77 | 0.76 | n/a | 0.380 | -48.7% (-55.2%) | 228 | 2.50 | no |
| REAL/bh/x2 | 2006-07 | 13.7% (9.7%) | +5.84 | +4.02 | +6.30 | 1.00 | +0.18 | 1.00 | 1.00 | 0.156 | -84.7% (-55.2%) | 1 | 0.00 | no |
| REAL/bh/x3 | 2009-07 | 30.2% (13.1%) | +13.55 | +17.12 | +13.24 | 1.00 | +6.69 | 1.00 | n/a | 0.004 | -76.8% (-33.7%) | 1 | 0.00 | yes |

### FED (secondary)

| config | from | after-tax CAGR to 2026-07 (SPY) | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | max DD (SPY) | trades | turnover/yr | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | 2000-01 | 16.3% (7.7%) | +11.26 | +8.57 | +11.62 | 1.00 | +6.06 | 1.00 | 1.00 | 0.016 | -57.5% (-55.2%) | 107 | 1.39 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | 2000-01 | 13.8% (7.7%) | +7.27 | +6.09 | +7.42 | 1.00 | +0.76 | 1.00 | 1.00 | 0.091 | -57.4% (-55.2%) | 112 | 1.55 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | 2000-01 | 13.6% (7.7%) | +6.31 | +5.97 | +6.29 | 1.00 | +1.34 | 1.00 | 1.00 | 0.014 | -63.2% (-55.2%) | 68 | 1.00 | yes |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | 2000-01 | 14.1% (7.7%) | +7.85 | +6.38 | +7.79 | 1.00 | +2.00 | 1.00 | 1.00 | 0.068 | -56.6% (-55.2%) | 102 | 1.38 | yes |
| SYN/trend/on=x3/off=tbill/sma100/b0.02/M | 2000-01 | 13.1% (7.7%) | +6.93 | +5.41 | +6.82 | 1.00 | +1.22 | 1.00 | 1.00 | 0.103 | -58.9% (-55.2%) | 97 | 1.38 | no |
| SYN/trend/on=x2/off=mid/sma100/b0.02/M | 2000-01 | 11.3% (7.7%) | +3.96 | +3.62 | +3.94 | 0.90 | -1.42 | 0.98 | 1.00 | 0.106 | -42.3% (-55.2%) | 102 | 1.38 | no |
| SYN/trend/on=x2/off=one/sma100/b0.02/M | 2000-01 | 9.7% (7.7%) | +3.21 | +2.06 | +3.18 | 1.00 | +0.65 | 1.00 | 1.00 | 0.159 | -63.2% (-55.2%) | 91 | 1.43 | no |
| SYN/trend/on=one.5x3.5/off=one/sma200/b0.02/D | 2000-01 | 10.4% (7.7%) | +3.86 | +2.74 | +3.96 | 1.00 | +0.37 | 1.00 | 1.00 | 0.079 | -62.7% (-55.2%) | 548 | 0.94 | yes |
| SYN/trend/on=x2/off=one/sma200/b0.02/M | 2000-01 | 10.2% (7.7%) | +3.05 | +2.49 | +3.01 | 0.99 | -0.13 | 1.00 | 1.00 | 0.127 | -61.8% (-55.2%) | 53 | 0.77 | no |
| SYN/trend/on=x3/off=tbill/sma200/b0.0/D | 2000-01 | 8.8% (7.7%) | +3.36 | +1.16 | +3.56 | 0.76 | -4.63 | 0.96 | 0.93 | 0.416 | -67.3% (-55.2%) | 378 | 4.87 | no |
| SYN/lowvol/rv60<0.15/b0.1/on=x2/off=one | 2000-01 | 10.1% (7.7%) | +2.63 | +2.43 | +2.64 | 1.00 | +0.62 | 1.00 | 1.00 | 0.051 | -59.5% (-55.2%) | 69 | 1.01 | yes |
| SYN/vt/t0.25/w20/x2/M/eb0.15/trend=sma200 | 2000-01 | 8.8% (7.7%) | +1.74 | +1.13 | +1.80 | 0.99 | -0.16 | 1.00 | 1.00 | 0.233 | -54.6% (-55.2%) | 303 | 2.45 | no |

| config | from | after-tax CAGR to 2026-07 (SPY) | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | max DD (SPY) | trades | turnover/yr | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | 2009-07 | 24.0% (14.1%) | +10.80 | +9.89 | +11.07 | 1.00 | +6.18 | 1.00 | n/a | 0.018 | -58.4% (-33.7%) | 78 | 1.40 | yes |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | 2009-07 | 20.7% (14.1%) | +5.70 | +6.54 | +4.84 | 1.00 | +0.68 | 1.00 | n/a | 0.107 | -57.6% (-33.7%) | 77 | 1.56 | no |
| REAL/lowvol/rv60<0.15/on=x3/off=one | 2009-07 | 21.2% (14.1%) | +8.12 | +7.05 | +7.79 | 1.00 | +5.72 | 1.00 | n/a | 0.047 | -49.7% (-33.7%) | 67 | 1.06 | yes |
| REAL/bh/x3 | 2009-07 | 31.5% (14.1%) | +14.26 | +17.41 | +13.86 | 1.00 | +7.16 | 1.00 | n/a | 0.004 | -76.8% (-33.7%) | 1 | 0.00 | yes |

### NONE (no tax; diagnostic)

| config | from | after-tax CAGR to 2026-07 (SPY) | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | max DD (SPY) | trades | turnover/yr | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | 2000-01 | 19.0% (8.3%) | +13.67 | +10.71 | +14.07 | 1.00 | +7.97 | 1.00 | 1.00 | 0.007 | -54.2% (-55.2%) | 75 | 1.41 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | 2000-01 | 16.4% (8.3%) | +9.36 | +8.15 | +9.54 | 1.00 | +1.42 | 1.00 | 1.00 | 0.052 | -57.4% (-55.2%) | 96 | 1.56 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | 2000-01 | 16.3% (8.3%) | +8.24 | +8.04 | +8.16 | 1.00 | +1.84 | 1.00 | 1.00 | 0.003 | -60.9% (-55.2%) | 53 | 0.96 | yes |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | 2000-01 | 16.6% (8.3%) | +9.94 | +8.37 | +9.85 | 1.00 | +3.82 | 1.00 | 1.00 | 0.039 | -52.6% (-55.2%) | 78 | 1.39 | yes |
| SYN/trend/on=x3/off=tbill/sma100/b0.02/M | 2000-01 | 15.4% (8.3%) | +8.78 | +7.12 | +8.61 | 1.00 | +2.88 | 1.00 | 1.00 | 0.059 | -58.9% (-55.2%) | 76 | 1.40 | yes |
| SYN/trend/on=x2/off=mid/sma100/b0.02/M | 2000-01 | 13.5% (8.3%) | +5.50 | +5.26 | +5.47 | 0.96 | -0.15 | 1.00 | 1.00 | 0.049 | -37.4% (-55.2%) | 76 | 1.40 | yes |
| SYN/trend/on=x2/off=one/sma100/b0.02/M | 2000-01 | 12.0% (8.3%) | +4.95 | +3.71 | +4.91 | 1.00 | +0.65 | 1.00 | 1.00 | 0.041 | -63.2% (-55.2%) | 72 | 1.44 | yes |
| SYN/trend/on=one.5x3.5/off=one/sma200/b0.02/D | 2000-01 | 12.2% (8.3%) | +5.16 | +3.96 | +5.21 | 1.00 | +0.38 | 1.00 | 1.00 | 0.030 | -62.7% (-55.2%) | 544 | 0.94 | yes |
| SYN/trend/on=x2/off=one/sma200/b0.02/M | 2000-01 | 11.8% (8.3%) | +4.35 | +3.58 | +4.30 | 1.00 | +0.75 | 1.00 | 1.00 | 0.062 | -61.0% (-55.2%) | 42 | 0.75 | yes |
| SYN/trend/on=x3/off=tbill/sma200/b0.0/D | 2000-01 | 10.4% (8.3%) | +4.52 | +2.17 | +4.67 | 0.78 | -4.90 | 0.96 | 0.96 | 0.358 | -67.3% (-55.2%) | 371 | 4.75 | no |
| SYN/lowvol/rv60<0.15/b0.1/on=x2/off=one | 2000-01 | 12.3% (8.3%) | +4.14 | +4.06 | +4.11 | 1.00 | +0.97 | 1.00 | 1.00 | 0.003 | -57.8% (-55.2%) | 49 | 0.98 | yes |
| SYN/vt/t0.25/w20/x2/M/eb0.15/trend=sma200 | 2000-01 | 11.2% (8.3%) | +3.95 | +3.00 | +3.96 | 1.00 | +1.50 | 1.00 | 1.00 | 0.052 | -54.6% (-55.2%) | 303 | 2.46 | yes |

| config | from | after-tax CAGR to 2026-07 (SPY) | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | max DD (SPY) | trades | turnover/yr | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | 2009-07 | 28.7% (15.1%) | +13.61 | +13.62 | +13.91 | 1.00 | +8.16 | 1.00 | n/a | 0.005 | -55.1% (-33.7%) | 55 | 1.42 | yes |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | 2009-07 | 24.9% (15.1%) | +7.66 | +9.79 | +6.66 | 1.00 | +1.40 | 1.00 | n/a | 0.052 | -57.6% (-33.7%) | 66 | 1.56 | yes |
| REAL/lowvol/rv60<0.15/on=x3/off=one | 2009-07 | 26.0% (15.1%) | +11.11 | +10.86 | +10.78 | 1.00 | +8.19 | 1.00 | n/a | 0.012 | -49.7% (-33.7%) | 48 | 1.00 | yes |
| REAL/bh/x3 | 2009-07 | 32.8% (15.1%) | +14.95 | +17.68 | +14.44 | 1.00 | +7.60 | 1.00 | n/a | 0.005 | -76.8% (-33.7%) | 1 | 0.00 | yes |

Tax matters. CA tax removes about 3.3 pp/yr of the Daily-200 rule's excess
(score +9.36 in NONE vs +6.07 in CA). It moves the bootstrap p from 0.05 to 0.12.
Many configurations pass items 1-3 without tax and fail them in CA.

## 4. More return, or better return?

Risk statistics are from the CA `full` runs. Beta, alpha and M2 come from the
monthly after-tax liquidation values (2000 start, or the REAL first start). M2 is
the excess the strategy would have earned scaled to SPY's volatility. Worst 5y /
10y CAGR are the worst after-tax windows. "Worst after-tax wealth" is the lowest
after-tax liquidation value any start ever saw, as a fraction of its initial
investment. P(-50%) and P(-75%) are the shares of starts that were at some
quarter-end down more than 50% / 75% after tax. Sharpe is the daily Sharpe of
the first start's run. SPY's is 0.51 from 2000; REAL rows start in 2006/2009,
when SPY's own Sharpe was higher, and their SPY columns are for the same period.

| config | avg equity lev. | avg bond/T-bill w | beta | alpha after beta | M2 (risk-matched) | vol (SPY) | Sharpe (SPY 0.51) | worst 5y CAGR (SPY) | worst 10y CAGR (SPY) | worst after-tax wealth (SPY) | P(-50%) | P(-75%) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | 2.17 | 28% | 0.94 | +6.79 | +0.91 | 24.0% (14.0%) | 0.58 | +1.16 (-4.68) | +6.24 (-1.81) | 0.51 (0.54) | 0.00 | 0.00 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | 2.21 | 26% | 1.06 | +3.96 | -0.60 | 25.3% (14.0%) | 0.52 | -2.41 (-4.68) | +5.60 (-1.81) | 0.47 (0.54) | 0.02 | 0.00 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | 2.12 | 0% | 1.45 | +1.21 | -0.18 | 23.4% (14.0%) | 0.53 | -5.26 (-4.68) | -0.06 (-1.81) | 0.50 (0.54) | 0.01 | 0.00 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | 2.27 | 24% | 1.02 | +4.44 | -0.48 | 25.3% (14.0%) | 0.51 | +0.71 (-4.68) | +6.09 (-1.81) | 0.50 (0.54) | 0.00 | 0.00 |
| SYN/trend/on=x3/off=tbill/sma100/b0.02/M | 2.27 | 24% | 1.05 | +3.53 | -0.90 | 25.3% (14.0%) | 0.49 | -2.20 (-4.68) | +4.13 (-1.81) | 0.46 (0.54) | 0.03 | 0.00 |
| SYN/trend/on=x2/off=mid/sma100/b0.02/M | 1.51 | 24% | 0.64 | +4.87 | +1.14 | 16.2% (14.0%) | 0.51 | +2.87 (-4.68) | +6.44 (-1.81) | 0.65 (0.54) | 0.00 | 0.00 |
| SYN/trend/on=x2/off=one/sma100/b0.02/M | 1.76 | 0% | 1.33 | -1.16 | -1.30 | 20.2% (14.0%) | 0.44 | -6.52 (-4.68) | -1.16 (-1.81) | 0.44 (0.54) | 0.05 | 0.00 |
| SYN/trend/on=one.5x3.5/off=one/sma200/b0.02/D | 1.74 | 0% | 1.34 | -0.51 | -0.77 | 19.9% (14.0%) | 0.47 | -8.01 (-4.68) | -1.42 (-1.81) | 0.47 (0.54) | 0.03 | 0.00 |
| SYN/trend/on=x2/off=one/sma200/b0.02/M | 1.77 | 0% | 1.39 | -1.07 | -1.19 | 20.9% (14.0%) | 0.44 | -6.40 (-4.68) | -0.83 (-1.81) | 0.47 (0.54) | 0.04 | 0.00 |
| SYN/trend/on=x3/off=tbill/sma200/b0.0/D | 2.22 | 26% | 1.24 | -1.12 | -3.35 | 29.7% (14.0%) | 0.41 | -11.12 (-4.68) | -4.11 (-1.81) | 0.36 (0.54) | 0.02 | 0.00 |
| SYN/lowvol/rv60<0.15/b0.1/on=x2/off=one | 1.56 | 0% | 1.20 | +0.06 | -0.37 | 17.9% (14.0%) | 0.47 | -4.76 (-4.68) | -1.06 (-1.81) | 0.53 (0.54) | 0.00 | 0.00 |
| SYN/vt/t0.25/w20/x2/M/eb0.15/trend=sma200 | 1.59 | 3% | 1.13 | -0.56 | -1.04 | 17.3% (14.0%) | 0.43 | -3.92 (-4.68) | -0.82 (-1.81) | 0.50 (0.54) | 0.00 | 0.00 |
| SYN/mix/x30.55+b30.45/calQ | 1.67 | 44% | 1.55 | -0.56 | -1.98 | 29.0% (14.0%) | 0.49 | -10.24 (-4.68) | -1.32 (-1.81) | 0.35 (0.54) | 0.17 | 0.00 |
| SYN/mix/x30.4+mid0.6/calA | 1.20 | 60% | 0.98 | +0.56 | +0.13 | 14.6% (14.0%) | 0.51 | -4.61 (-4.68) | -0.64 (-1.81) | 0.58 (0.54) | 0.00 | 0.00 |
| SYN/mix/x20.5+one0.5/band0.1 | 1.53 | 0% | 1.57 | -2.85 | -1.84 | 22.2% (14.0%) | 0.46 | -10.45 (-4.68) | -5.83 (-1.81) | 0.35 (0.54) | 0.18 | 0.00 |
| SYN/mix/x30.3333+one0.6667/calQ | 1.67 | 0% | 1.68 | -3.87 | -2.35 | 23.8% (14.0%) | 0.43 | -13.49 (-4.68) | -7.81 (-1.81) | 0.28 (0.54) | 0.28 | 0.00 |
| SYN/bh/x2 | 2.00 | 0% | 2.10 | -6.76 | -3.24 | 29.7% (14.0%) | 0.42 | -17.58 (-4.68) | -11.68 (-1.81) | 0.17 (0.54) | 0.34 | 0.06 |
| SYN/bh/x3 | 3.00 | 0% | 3.28 | -16.82 | -5.16 | 46.9% (14.0%) | 0.41 | -31.90 (-4.68) | -23.71 (-1.81) | 0.03 (0.54) | 0.47 | 0.35 |
| SYN/dualmom/us4-2x/lb252/top2/safe=mid | 1.62 | 19% | 1.03 | +1.68 | -1.25 | 21.9% (14.0%) | 0.46 | -4.00 (-4.68) | +2.79 (-1.81) | 0.50 (0.54) | 0.01 | 0.00 |
| SYN/dualmom/spy/qqq-2x/lb252/top1/safe=mid | 1.59 | 20% | 1.21 | +1.24 | -2.32 | 29.5% (14.0%) | 0.46 | -11.79 (-4.68) | -1.41 (-1.81) | 0.30 (0.54) | 0.03 | 0.00 |
| SYN/qtrend/on=q3/off=tbill/qqq-sma200/D | 2.21 | 26% | 1.79 | -5.16 | -4.70 | 46.3% (14.0%) | 0.42 | -34.71 (-4.68) | -15.86 (-1.81) | 0.07 (0.54) | 0.13 | 0.03 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | 2.45 | 18% | 1.41 | +1.51 | -3.07 | 25.8% (12.6%) | 0.73 | +6.34 (+4.24) | +15.39 (+7.79) | 0.50 (0.76) | 0.02 | 0.00 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | 2.53 | 16% | 1.66 | -4.01 | -4.84 | 27.7% (12.6%) | 0.66 | -0.70 (+4.24) | +10.00 (+7.79) | 0.48 (0.76) | 0.04 | 0.00 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | 2.29 | 0% | 1.67 | -3.92 | -3.60 | 24.1% (12.6%) | 0.69 | +4.78 (+4.24) | +13.11 (+7.79) | 0.62 (0.76) | 0.00 | 0.00 |
| REAL/trend/on=x3/off=mid/sma100/b0.02/M | 2.42 | 19% | 1.34 | -0.68 | -4.44 | 25.3% (12.6%) | 0.63 | +3.05 (+4.24) | +11.14 (+7.79) | 0.52 (0.76) | 0.00 | 0.00 |
| REAL/trend/on=x3/off=tbill/sma100/b0.02/M | 2.42 | 19% | 1.31 | -0.33 | -4.41 | 25.2% (12.6%) | 0.63 | +2.56 (+4.24) | +9.94 (+7.79) | 0.59 (0.76) | 0.00 | 0.00 |
| REAL/trend/on=x2/off=mid/sma100/b0.02/M | 1.61 | 19% | 0.67 | +4.59 | +0.07 | 16.1% (13.8%) | 0.57 | +3.16 (-1.17) | +8.85 (+5.33) | 0.62 (0.54) | 0.00 | 0.00 |
| REAL/lowvol/rv60<0.15/on=x2/off=one | 1.65 | 0% | 1.23 | -0.71 | -1.16 | 18.2% (13.8%) | 0.56 | -2.80 (-1.17) | +7.18 (+5.33) | 0.53 (0.54) | 0.00 | 0.00 |
| REAL/mix/x30.55+b30.45/calQ | 1.70 | 43% | 1.63 | -2.34 | -4.04 | 27.1% (12.6%) | 0.75 | -4.33 (+4.24) | +8.63 (+7.79) | 0.35 (0.76) | 0.11 | 0.00 |
| REAL/vt/t0.25/w20/x2/M/trend=sma200 | 1.69 | 2% | 1.10 | -0.35 | -1.05 | 17.4% (14.5%) | 0.51 | +1.51 (-0.07) | +7.15 (+5.40) | 0.60 (0.54) | 0.00 | 0.00 |
| REAL/bh/x2 | 2.00 | 0% | 2.15 | -7.02 | -3.29 | 29.9% (13.8%) | 0.57 | -11.57 (-1.17) | +5.50 (+5.33) | 0.22 (0.54) | 0.14 | 0.03 |
| REAL/bh/x3 | 3.00 | 0% | 3.37 | -15.03 | -4.55 | 42.9% (12.6%) | 0.81 | +1.47 (+4.24) | +14.48 (+7.79) | 0.33 (0.76) | 0.16 | 0.00 |

How to read it:

* **Every leveraged rule takes much more risk than SPY.** Volatility is 1.2-3.4x
  SPY's, and average equity exposure is 1.2-3x. The Sharpe ratios (daily, from
  the first start) of the pre-registered leaders are within 0.02 of SPY's 0.51
  (Daily-200 with a 2% band 0.52, Low-vol 0.53, Monthly-100 0.51). The daily
  rules with a 3-4% band reach 0.54-0.58 (M2 about 0 to +0.9), so they are
  modestly better risk-adjusted as well (section 6.1). M2 is slightly negative for
  the pre-registered filtered 3x rules in CA (-0.2 to -0.9) and strongly negative
  for static leverage (-2 to -5). With a 2% band or a monthly check, leverage
  plus a timing filter has roughly SPY's return per unit of risk, scaled up; the
  wide-band daily rules add a little on top.
* **The trend filter's real contribution is avoiding volatility decay in long bear
  markets.** It adds little or no excess return per unit of risk. Static 2x/3x
  lost 88-98% in 2000-2009 (worst after-tax wealth 0.17 and 0.03 of the start).
  The filtered rules' worst after-tax wealth (0.46-0.51) is close to SPY's (0.54).
  Their worst 10-year window is better than SPY's because the filter sat out
  2000-02 and 2008.
* **Apart from the wide-band daily 3x rules, only low-leverage rules with a
  Treasury sleeve are at least level with SPY risk-adjusted.** The clearest is 2x
  S&P / Treasuries on a monthly SMA100
  (`SYN/trend/on=x2/off=mid/sma100/b0.02/M`): beta 0.64, M2 +1.14 pp, max
  drawdown -46.6%, worst after-tax wealth 0.65. Its CA evidence is weak, though
  (score +3.10, p = 0.157, 15-year beat 0.83), and none of its 8 neighbours even
  passes items 1-2 in CA (median score +1.61). It also fails the long history
  (pre-2000 10-year windows +0.19 pp, -25 pp vs the index in 1987), and it is a
  monthly-check rule with the timing luck shown in section 6. The 40% 3x / 60%
  Treasuries annual mix is level with SPY risk-adjusted (M2 +0.13) but adds
  little (CA score +1.07, p = 0.28).
* Year by year (CA after-tax liquidation value, start 2000-01), the Daily-200 rule
  is a high-tracking-error bet. It gained +11.7% in 2008 (SPY -34.5%), +104.9% in
  2013 (SPY +24.6%) and +87.9% in 2021 (SPY +26.1%). It lost -18.9% in 2007 (SPY
  +3.8%), -19.2% in 2015 (SPY +1.0%), -19.4% in 2018 (SPY -4.0%), -5.1% in 2020
  (SPY +16.3%) and -39.5% in 2022 (SPY -16.8%; stocks and Treasuries fell
  together). With real ETFs since 2009, its CA excess from a 2015 start is +0.1
  pp/yr and from a 2018 start -1.6 pp/yr (section 6.5 table). The SMA175 3%-band
  rule has the same profile (2000 -23.5%, 2007 -18.4%, 2022 -43.1%) but
  whipsawed less in 2018 (-5.2%) and 2020 (+20.6%). With real ETFs its CA excess
  from 2015 is +4.1 pp/yr and from 2018 +2.2 pp/yr.

## 5. The pre-2000 holdout: 1986-2026 on synthetic leveraged VFINX

Long-history translations of the finalists (`long_screen`: 38 yearly starts
1986-2023; VFINX benchmark; CA unless noted). "1987 excess" is calendar 1987
(start 1987-01-01). "1990-2000" is the after-tax excess per year over that
decade.

| config (LONG set) | regime | from | score | full | ho5 mean (beat) | ho10 mean (beat) | ex10 beat | ex15 beat | boot p | max DD (VFINX) | worst wealth | 1987 excess | 1990-2000 excess/yr | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG/trend/on=x3/off=mid/sma175/b0.03/D | CA | 1986-01 | +8.34 | +5.74 | +8.61 (0.80) | +7.31 (1.00) | 1.00 | 1.00 | 0.022 | -60.6% (-55.3%) | 0.51 | +6.0 | +7.17 | yes |
| LONG/trend/on=x3/off=mid/sma175/b0.03/D | NONE | 1986-01 | +11.62 | +10.02 | +11.76 (0.90) | +10.79 (1.00) | 1.00 | 1.00 | 0.003 | -54.7% (-55.3%) | 0.51 | +11.6 | +9.99 | yes |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D | CA | 1986-01 | +6.78 | +4.33 | +8.66 (0.70) | +7.34 (1.00) | 0.97 | 1.00 | 0.092 | -59.6% (-55.3%) | 0.49 | +7.9 | +6.56 | yes |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D | NONE | 1986-01 | +9.58 | +8.23 | +11.53 (0.80) | +10.48 (1.00) | 1.00 | 1.00 | 0.016 | -58.3% (-55.3%) | 0.49 | +15.2 | +8.50 | yes |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | 1986-01 | +4.50 | +2.77 | +5.80 (0.70) | +5.09 (1.00) | 1.00 | 0.92 | 0.116 | -65.6% (-55.3%) | 0.50 | -19.1 | +4.70 | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one | NONE | 1986-01 | +6.89 | +6.10 | +8.01 (0.70) | +7.20 (1.00) | 1.00 | 0.96 | 0.022 | -61.1% (-55.3%) | 0.50 | -18.8 | +6.27 | yes |
| LONG/trend/on=x3/off=mid/sma100/b0.02/M | CA | 1986-01 | +5.72 | +1.94 | +4.42 (0.70) | +3.28 (0.60) | 0.94 | 0.96 | 0.295 | -81.3% (-55.3%) | 0.41 | -50.0 | +5.45 | no |
| LONG/trend/on=x3/off=mid/sma100/b0.02/M | NONE | 1986-01 | +8.39 | +5.25 | +6.55 (0.70) | +5.25 (0.60) | 0.94 | 0.96 | 0.129 | -78.7% (-55.3%) | 0.48 | -51.3 | +7.63 | no |
| LONG/trend/on=x3/off=tbill/sma100/b0.02/M | CA | 1986-01 | +4.84 | +1.22 | +3.60 (0.70) | +2.48 (0.60) | 0.94 | 0.92 | 0.360 | -81.4% (-55.3%) | 0.39 | -50.5 | +4.76 | no |
| LONG/trend/on=x3/off=tbill/sma100/b0.02/M | NONE | 1986-01 | +7.19 | +4.29 | +5.45 (0.70) | +4.08 (0.60) | 0.94 | 0.96 | 0.170 | -78.7% (-55.3%) | 0.45 | -51.8 | +6.68 | no |
| LONG/trend/on=x2/off=mid/sma100/b0.02/M | CA | 1986-01 | +2.92 | +0.07 | +0.94 (0.70) | +0.19 (0.60) | 0.84 | 0.88 | 0.465 | -61.0% (-55.3%) | 0.64 | -25.0 | +0.69 | no |
| LONG/trend/on=x2/off=mid/sma100/b0.02/M | NONE | 1986-01 | +4.96 | +3.00 | +2.35 (0.70) | +1.96 (0.60) | 0.90 | 0.96 | 0.131 | -59.1% (-55.3%) | 0.64 | -26.3 | +2.44 | no |
| LONG/trend/on=x2/off=one/sma100/b0.02/M | CA | 1986-01 | +1.96 | +0.12 | +2.77 (0.70) | +1.94 (0.80) | 0.90 | 0.92 | 0.460 | -66.3% (-55.3%) | 0.46 | -20.0 | +2.98 | no |
| LONG/trend/on=x2/off=one/sma100/b0.02/M | NONE | 1986-01 | +4.18 | +3.42 | +4.90 (0.70) | +4.44 (0.80) | 0.94 | 1.00 | 0.057 | -63.3% (-55.3%) | 0.46 | -21.3 | +5.88 | yes |
| LONG/trend/on=one.5x3.5/off=one/sma200/b0.02/D | CA | 1986-01 | +3.02 | +1.64 | +4.66 (0.70) | +3.76 (1.00) | 0.94 | 1.00 | 0.109 | -63.9% (-55.3%) | 0.50 | -2.2 | +3.99 | no |
| LONG/trend/on=one.5x3.5/off=one/sma200/b0.02/D | NONE | 1986-01 | +4.93 | +4.76 | +7.17 (0.80) | +6.75 (1.00) | 0.94 | 1.00 | 0.004 | -62.9% (-55.3%) | 0.50 | +2.1 | +6.70 | yes |
| LONG/trend/on=x2/off=one/sma200/b0.02/M | CA | 1986-01 | +2.70 | +1.14 | +3.87 (0.70) | +2.88 (0.80) | 0.94 | 1.00 | 0.228 | -65.7% (-55.3%) | 0.49 | -20.0 | +5.09 | no |
| LONG/trend/on=x2/off=one/sma200/b0.02/M | NONE | 1986-01 | +4.67 | +4.04 | +5.95 (0.70) | +5.50 (1.00) | 1.00 | 1.00 | 0.027 | -59.4% (-55.3%) | 0.49 | -21.3 | +7.53 | yes |
| LONG/trend/on=x3/off=tbill/sma200/b0.0/D | CA | 1986-01 | +3.97 | +2.85 | +7.91 (0.60) | +6.56 (1.00) | 0.87 | 0.92 | 0.181 | -69.5% (-55.3%) | 0.46 | +8.4 | +7.39 | no |
| LONG/trend/on=x3/off=tbill/sma200/b0.0/D | NONE | 1986-01 | +6.31 | +6.46 | +12.40 (0.90) | +11.16 (1.00) | 0.87 | 0.92 | 0.053 | -65.0% (-55.3%) | 0.46 | +16.2 | +10.96 | yes |
| LONG/lowvol/rv60<0.15/b0.1/on=x2/off=one | CA | 1986-01 | +1.57 | +0.15 | +2.04 (0.70) | +1.72 (0.80) | 0.87 | 0.85 | 0.434 | -61.4% (-55.3%) | 0.55 | -15.4 | +1.63 | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x2/off=one | NONE | 1986-01 | +3.46 | +3.13 | +3.92 (0.70) | +3.63 (1.00) | 1.00 | 0.96 | 0.018 | -58.0% (-55.3%) | 0.55 | -9.9 | +3.17 | yes |
| LONG/vt/t0.25/w20/x2/M/eb0.15/trend=sma200 | CA | 1986-01 | +0.15 | -1.20 | -0.76 (0.40) | -1.37 (0.20) | 0.55 | 0.73 | 0.828 | -57.4% (-55.3%) | 0.53 | -0.5 | -2.15 | no |
| LONG/vt/t0.25/w20/x2/M/eb0.15/trend=sma200 | NONE | 1986-01 | +3.07 | +2.62 | +2.51 (0.50) | +2.12 (1.00) | 1.00 | 1.00 | 0.037 | -53.3% (-55.3%) | 0.53 | +2.7 | +1.58 | yes |
| LONG/mix/x30.55+b30.45/calQ | CA | 1987-01 | +6.27 | +3.60 | +8.80 (1.00) | +8.18 (1.00) | 0.90 | 1.00 | 0.130 | -75.1% (-55.3%) | 0.35 | -19.2 | +8.48 | no |
| LONG/mix/x30.55+b30.45/calQ | NONE | 1987-01 | +8.47 | +6.04 | +11.21 (1.00) | +10.20 (1.00) | 0.97 | 1.00 | 0.052 | -70.9% (-55.3%) | 0.35 | -12.4 | +9.90 | yes |
| LONG/mix/x30.4+mid0.6/calA | CA | 1986-01 | +0.88 | -0.48 | +1.89 (0.80) | +1.85 (1.00) | 0.84 | 0.88 | 0.692 | -50.8% (-55.3%) | 0.58 | -16.9 | +2.45 | no |
| LONG/mix/x30.4+mid0.6/calA | NONE | 1986-01 | +1.39 | +0.75 | +2.62 (0.80) | +2.53 (1.00) | 0.90 | 1.00 | 0.213 | -50.8% (-55.3%) | 0.60 | -18.3 | +3.10 | no |
| LONG/mix/x20.5+one0.5/band0.1 | CA | 1986-01 | +1.62 | +1.45 | +3.68 (0.90) | +3.77 (1.00) | 0.81 | 0.69 | 0.139 | -76.8% (-55.3%) | 0.38 | -7.0 | +4.87 | no |
| LONG/mix/x20.5+one0.5/band0.1 | NONE | 1986-01 | +1.92 | +2.07 | +4.36 (0.90) | +4.15 (1.00) | 0.81 | 0.69 | 0.087 | -72.6% (-55.3%) | 0.38 | -8.3 | +5.35 | no |
| LONG/mix/x30.3333+one0.6667/calQ | CA | 1986-01 | +1.81 | +1.28 | +4.69 (0.90) | +4.52 (1.00) | 0.81 | 0.69 | 0.212 | -81.8% (-55.3%) | 0.29 | -8.8 | +6.13 | no |
| LONG/mix/x30.3333+one0.6667/calQ | NONE | 1986-01 | +2.52 | +2.71 | +5.98 (0.90) | +5.67 (1.00) | 0.81 | 0.69 | 0.095 | -78.8% (-55.3%) | 0.29 | -7.2 | +7.22 | no |
| LONG/bh/x2 | CA | 1986-01 | +2.30 | +2.89 | +7.05 (0.90) | +7.09 (1.00) | 0.68 | 0.65 | 0.158 | -88.3% (-55.3%) | 0.18 | -15.3 | +9.16 | no |
| LONG/bh/x2 | NONE | 1986-01 | +2.70 | +2.92 | +8.21 (0.90) | +7.70 (1.00) | 0.68 | 0.65 | 0.172 | -88.3% (-55.3%) | 0.18 | -16.6 | +9.90 | no |
| LONG/bh/x3 | CA | 1986-01 | +2.47 | +2.69 | +13.61 (0.70) | +13.00 (1.00) | 0.58 | 0.62 | 0.321 | -98.2% (-55.3%) | 0.03 | -41.3 | +17.86 | no |
| LONG/bh/x3 | NONE | 1986-01 | +2.98 | +2.73 | +15.46 (0.70) | +13.96 (1.00) | 0.58 | 0.62 | 0.334 | -98.2% (-55.3%) | 0.03 | -42.6 | +19.10 | no |

Quarterly-start `long` protocol (151 starts; 37 five-year and 17 ten-year holdout
windows) for the three leaders and their one-day-lag versions:

| config | regime | score | full_excess | ho5_mean | ho10_mean | ho10_beat | ex10_beat | ex15_beat | boot_p | max_dd | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | +4.52 | +2.77 | +6.12 | +5.30 | 1.00 | 0.98 | 0.93 | 0.116 | -65.6% | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one | NONE | +6.92 | +6.10 | +8.05 | +7.26 | 1.00 | 1.00 | 0.97 | 0.022 | -61.1% | yes |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one/lag1 | CA | +4.77 | +3.00 | +6.64 | +5.93 | 1.00 | 0.99 | 0.94 | 0.100 | -65.5% | yes |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one/lag1 | NONE | +7.25 | +6.38 | +8.83 | +8.16 | 1.00 | 1.00 | 0.98 | 0.013 | -61.1% | yes |
| LONG/trend/on=x3/off=mid/sma175/b0.03/D | CA | +8.28 | +5.74 | +8.72 | +7.81 | 1.00 | 0.98 | 1.00 | 0.022 | -60.6% | yes |
| LONG/trend/on=x3/off=mid/sma175/b0.03/D | NONE | +11.46 | +10.02 | +11.44 | +10.83 | 1.00 | 0.99 | 1.00 | 0.003 | -54.7% | yes |
| LONG/trend/on=x3/off=mid/sma175/b0.03/D/lag1 | CA | +6.83 | +3.20 | +3.90 | +2.61 | 0.53 | 0.90 | 0.92 | 0.209 | -79.0% | no |
| LONG/trend/on=x3/off=mid/sma175/b0.03/D/lag1 | NONE | +9.77 | +6.54 | +5.58 | +4.07 | 0.53 | 0.90 | 0.92 | 0.101 | -79.0% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D | CA | +6.68 | +4.33 | +9.07 | +8.02 | 1.00 | 0.93 | 1.00 | 0.092 | -59.6% | yes |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D | NONE | +9.40 | +8.23 | +11.75 | +10.82 | 1.00 | 0.98 | 1.00 | 0.016 | -58.3% | yes |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D/lag1 | CA | +5.92 | +2.33 | +4.14 | +2.62 | 0.53 | 0.91 | 0.92 | 0.270 | -80.0% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D/lag1 | NONE | +8.70 | +5.56 | +5.81 | +3.85 | 0.53 | 0.91 | 0.92 | 0.142 | -80.0% | no |

### What happened in October 1987

VFINX closed 0.75% above its 200-day average on 1987-10-15 and 4.5% below it on
1987-10-16, a Friday (-5.2% that day). On Monday 1987-10-19 it fell 20.5%.

* **Daily-200** (2% band) turned off at the 10-16 close and sold its 3x position
  there, in the lab's convention of deciding and trading at the same close (the
  website's convention). It took the -9% / -7% / -16% 3x losses of 10-14..10-16,
  then sat in bonds: +7.9 pp vs the index in 1987.
* The same rule **deciding on 10-16 but trading at the next close**
  (`D/lag1`), the same rule on **^GSPC with the lab's one-day signal lag**, or
  checked **weekly** (Monday 10-19's close) or **monthly** sold after the crash:
  -47 to -60 pp in 1987, -79% to -80% drawdowns on 1986-2026, and p = 0.18-0.36
  in CA.
* Neighbouring daily parameters split the same way. Every SMA175-225 rule with a
  1-3% band was out by the 10-16 close, except SMA225 with a 3% band, which did
  not cross until 10-19: -57.7 pp in 1987.
* **Low-vol 3x**: VFINX's 60-day volatility crossed the 16.5% exit level only at
  the 10-14 close, so the rule carried 3x through the first part of the slide (the
  3x fund lost about 20% from 10-05 to 10-14): -19 pp vs the index in 1987. Its
  long-history CA score is +4.50, with p = 0.12.

Daily-200 neighbourhood and execution variants on the long history (CA,
`long_screen`):

| config | regime | score | full_excess | ho5_mean | ho10_mean | ho10_beat | ex10_beat | ex15_beat | boot_p | max_dd | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG/trend/on=x3/off=mid/gspc-sma200/b0.02/D | CA | +4.23 | +1.02 | +2.70 | +1.62 | 0.60 | 0.87 | 0.92 | 0.359 | -80.0% | no |
| LONG/trend/on=x3/off=mid/sma100/b0.02/D | CA | -2.35 | -2.60 | +2.77 | +1.89 | 1.00 | 0.52 | 0.31 | 0.749 | -90.2% | no |
| LONG/trend/on=x3/off=mid/sma100/b0.02/M | CA | +5.72 | +1.94 | +4.42 | +3.28 | 0.60 | 0.94 | 0.96 | 0.295 | -81.3% | no |
| LONG/trend/on=x3/off=mid/sma100/b0.02/M/lag1 | CA | +4.72 | +1.06 | +2.20 | +1.16 | 0.60 | 0.90 | 0.92 | 0.375 | -82.0% | no |
| LONG/trend/on=x3/off=mid/sma100/b0.02/W | CA | -1.42 | -4.52 | -3.37 | -3.92 | 0.20 | 0.39 | 0.31 | 0.841 | -83.2% | no |
| LONG/trend/on=x3/off=mid/sma175/b0.01/D | CA | +4.04 | +2.71 | +8.89 | +8.02 | 1.00 | 0.87 | 0.96 | 0.187 | -67.8% | no |
| LONG/trend/on=x3/off=mid/sma175/b0.02/D | CA | +7.69 | +5.41 | +10.75 | +9.52 | 1.00 | 0.97 | 1.00 | 0.038 | -65.4% | yes |
| LONG/trend/on=x3/off=mid/sma175/b0.03/D | CA | +8.34 | +5.74 | +8.61 | +7.31 | 1.00 | 1.00 | 1.00 | 0.022 | -60.6% | yes |
| LONG/trend/on=x3/off=mid/sma175/b0.03/D/lag1 | CA | +6.87 | +3.20 | +3.87 | +2.77 | 0.60 | 0.90 | 0.92 | 0.209 | -79.0% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.01/D | CA | +4.72 | +3.23 | +9.77 | +8.79 | 1.00 | 0.94 | 1.00 | 0.161 | -65.0% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D | CA | +6.78 | +4.33 | +8.66 | +7.34 | 1.00 | 0.97 | 1.00 | 0.092 | -59.6% | yes |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D/lag1 | CA | +6.05 | +2.33 | +3.83 | +2.59 | 0.60 | 0.90 | 0.92 | 0.270 | -80.0% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.02/D/taxexec-noST | CA | +3.71 | +2.50 | +9.69 | +8.70 | 1.00 | 0.74 | 0.85 | 0.222 | -65.6% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.02/M | CA | +6.98 | +3.70 | +7.06 | +5.54 | 0.60 | 0.81 | 1.00 | 0.176 | -78.7% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.02/W | CA | +5.46 | +1.82 | +2.77 | +1.40 | 0.60 | 0.94 | 0.92 | 0.305 | -80.3% | no |
| LONG/trend/on=x3/off=mid/sma200/b0.03/D | CA | +7.46 | +4.92 | +8.28 | +7.24 | 1.00 | 1.00 | 1.00 | 0.068 | -62.0% | yes |
| LONG/trend/on=x3/off=mid/sma200/b0.03/D/lag1 | CA | +7.24 | +3.41 | +6.26 | +5.08 | 0.60 | 0.94 | 0.96 | 0.187 | -80.0% | no |
| LONG/trend/on=x3/off=mid/sma225/b0.01/D | CA | +4.84 | +3.32 | +8.83 | +7.83 | 1.00 | 0.87 | 1.00 | 0.164 | -58.9% | no |
| LONG/trend/on=x3/off=mid/sma225/b0.02/D | CA | +6.93 | +4.99 | +9.63 | +8.75 | 1.00 | 1.00 | 1.00 | 0.069 | -61.3% | yes |
| LONG/trend/on=x3/off=mid/sma225/b0.03/D | CA | +7.12 | +3.55 | +5.95 | +4.62 | 0.60 | 0.94 | 0.96 | 0.193 | -81.1% | no |
| LONG/trend/on=x3/off=one/sma200/b0.02/D | CA | +6.00 | +4.26 | +9.95 | +8.52 | 1.00 | 0.94 | 1.00 | 0.074 | -73.2% | yes |
| LONG/trend/on=x3/off=tbill/sma100/b0.02/M | CA | +4.84 | +1.22 | +3.60 | +2.48 | 0.60 | 0.94 | 0.92 | 0.360 | -81.4% | no |
| LONG/trend/on=x3/off=tbill/sma200/b0.02/D | CA | +5.87 | +3.61 | +8.24 | +6.85 | 1.00 | 0.94 | 1.00 | 0.126 | -60.0% | no |

Low-vol neighbourhood on the long history (CA, `long_screen`):

| config | regime | score | full_excess | ho5_mean | ho10_mean | ho10_beat | ex10_beat | ex15_beat | boot_p | max_dd | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LONG/lowvol/rv40<0.14/b0.1/on=x3/off=one | CA | +2.90 | +1.22 | +5.86 | +5.38 | 1.00 | 0.90 | 0.88 | 0.272 | -65.9% | no |
| LONG/lowvol/rv40<0.15/b0.1/on=x3/off=one | CA | +2.96 | +1.74 | +6.53 | +6.04 | 1.00 | 0.94 | 0.92 | 0.224 | -64.3% | no |
| LONG/lowvol/rv40<0.16/b0.1/on=x3/off=one | CA | +3.33 | +2.37 | +6.98 | +6.51 | 1.00 | 0.84 | 0.92 | 0.178 | -71.4% | no |
| LONG/lowvol/rv60<0.14/b0.1/on=x3/off=one | CA | +3.04 | +1.19 | +5.20 | +4.55 | 1.00 | 0.97 | 0.92 | 0.269 | -66.1% | no |
| LONG/lowvol/rv60<0.15/b0.05/on=x3/off=one | CA | +3.70 | +2.03 | +6.13 | +5.57 | 1.00 | 1.00 | 0.92 | 0.183 | -65.8% | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x2/off=one | CA | +1.57 | +0.15 | +2.04 | +1.72 | 0.80 | 0.87 | 0.85 | 0.434 | -61.4% | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=mid | CA | +4.05 | +1.46 | +2.37 | +1.42 | 0.60 | 0.94 | 0.92 | 0.309 | -51.7% | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | +4.50 | +2.77 | +5.80 | +5.09 | 1.00 | 1.00 | 0.92 | 0.116 | -65.6% | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one/lag1 | CA | +4.75 | +3.00 | +6.35 | +5.73 | 1.00 | 1.00 | 0.92 | 0.100 | -65.5% | yes |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=one/taxexec-noST | CA | +3.23 | +1.50 | +6.76 | +6.14 | 1.00 | 0.87 | 0.88 | 0.263 | -77.3% | no |
| LONG/lowvol/rv60<0.15/b0.1/on=x3/off=tbill | CA | +2.88 | +0.48 | +1.50 | +0.47 | 0.40 | 0.81 | 0.85 | 0.434 | -53.8% | no |
| LONG/lowvol/rv60<0.15/b0.2/on=x3/off=one | CA | +4.01 | +2.12 | +7.63 | +6.62 | 1.00 | 0.90 | 0.92 | 0.204 | -66.6% | no |
| LONG/lowvol/rv60<0.16/b0.1/on=x3/off=one | CA | +6.35 | +4.78 | +12.06 | +11.90 | 1.00 | 1.00 | 1.00 | 0.026 | -65.9% | yes |
| LONG/lowvol/rv90<0.14/b0.1/on=x3/off=one | CA | +3.88 | +2.09 | +5.97 | +4.98 | 1.00 | 1.00 | 0.96 | 0.139 | -67.0% | no |
| LONG/lowvol/rv90<0.15/b0.1/on=x3/off=one | CA | +4.09 | +1.95 | +8.20 | +7.69 | 1.00 | 0.94 | 0.92 | 0.219 | -66.7% | no |
| LONG/lowvol/rv90<0.16/b0.1/on=x3/off=one | CA | +2.65 | +0.60 | +5.32 | +4.58 | 1.00 | 0.87 | 0.92 | 0.403 | -68.9% | no |

So the holdout does not contradict Daily-200 *on average*: pre-2000 five-year
windows average +9.07 pp, and ten-year windows +8.02 pp with a 1.00 beat rate.
Its one survival of a gap crash, though, rests on one day of execution timing. A
real investor using a market-on-close order computed shortly before the close
might or might not have got out on 1987-10-16. The robust reading is that a 3x
rule with a daily trend filter is exposed to any one-day crash that is not
preceded by a sell signal. 2020 was such a crash, though slower; the rule lost
-5.1% that year while SPY gained 16.3%.

## 6. Robustness

### 6.1 Parameter neighbourhoods (screen protocol, 2000-2026)

Immediate neighbours on the same instruments: SMA length +/-25 days, band +/-1 pp
(trend); window 40/60/90 and threshold +/-1 pp (low-vol); weight +/-15 pp (mixes);
target +/-5 pp (vol targeting).

| config | regime | neighbours run | share passing items 1-3 | share passing items 1-2 | share score > 0 | median score | min score | median boot p |
|---|---|---|---|---|---|---|---|---|
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | CA | 8/8 | 0.62 | 1.00 | 1.00 | +8.24 | +5.54 | 0.068 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | NONE | 8/8 | 0.88 | 1.00 | 1.00 | +11.98 | +8.05 | 0.024 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | CA | 8/8 | 0.38 | 1.00 | 1.00 | +6.43 | +2.06 | 0.115 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | NONE | 8/8 | 0.75 | 1.00 | 1.00 | +9.48 | +3.49 | 0.047 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | 10/10 | 0.10 | 1.00 | 1.00 | +3.21 | +2.60 | 0.209 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | NONE | 10/10 | 0.80 | 1.00 | 1.00 | +5.76 | +4.92 | 0.050 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | CA | 8/8 | 0.00 | 0.38 | 1.00 | +4.06 | +2.14 | 0.384 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | NONE | 8/8 | 0.12 | 0.75 | 1.00 | +6.46 | +4.17 | 0.249 |
| SYN/trend/on=x3/off=tbill/sma100/b0.02/M | CA | 8/8 | 0.00 | 0.38 | 1.00 | +3.13 | +1.38 | 0.470 |
| SYN/trend/on=x3/off=tbill/sma100/b0.02/M | NONE | 8/8 | 0.00 | 0.75 | 1.00 | +5.45 | +3.33 | 0.336 |
| SYN/trend/on=x2/off=mid/sma100/b0.02/M | CA | 8/8 | 0.00 | 0.00 | 1.00 | +1.61 | +0.58 | 0.470 |
| SYN/trend/on=x2/off=mid/sma100/b0.02/M | NONE | 8/8 | 0.00 | 0.25 | 1.00 | +3.50 | +2.12 | 0.263 |
| SYN/trend/on=x2/off=one/sma100/b0.02/M | CA | 8/8 | 0.00 | 0.62 | 1.00 | +1.40 | +0.62 | 0.492 |
| SYN/trend/on=x2/off=one/sma100/b0.02/M | NONE | 8/8 | 0.25 | 1.00 | 1.00 | +3.75 | +3.03 | 0.213 |
| SYN/trend/on=one.5x3.5/off=one/sma200/b0.02/D | CA | 8/8 | 0.38 | 1.00 | 1.00 | +2.99 | +1.35 | 0.175 |
| SYN/trend/on=one.5x3.5/off=one/sma200/b0.02/D | NONE | 8/8 | 0.88 | 1.00 | 1.00 | +5.12 | +3.14 | 0.026 |
| SYN/lowvol/rv60<0.15/b0.1/on=x2/off=one | CA | 10/10 | 0.00 | 0.40 | 1.00 | +0.90 | +0.70 | 0.414 |
| SYN/lowvol/rv60<0.15/b0.1/on=x2/off=one | NONE | 10/10 | 0.80 | 1.00 | 1.00 | +2.95 | +2.61 | 0.040 |

Daily-200's neighbours all pass items 1-2 and all have positive scores (median
+6.43 pp). Only 3 of 8 pass the bootstrap test in CA (median p = 0.115). That is a
plateau in return but not in confidence.

**The 3-4% band plateau (post-hoc).** The three Daily-200 neighbours that pass
are all on the wide-band side, so the grid was extended to SMA150-225 x 1-4%
bands, daily, 3x / intermediate Treasuries. These configurations were chosen after
seeing the screen; the 1986-2026 columns were computed after the 1-3% band
versions had already been seen.

| SMA | band | 2000-26 score | full | boot p | M2 | items 1-3 | 1986-2026 score | ho10 (beat) | boot p | max DD | 1987 excess | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SMA150 | 2% | +5.54 | +2.10 | 0.333 | -2.45 | no | +4.24 | +7.73 (1.00) | 0.169 | -82.2% | +17.0 | no |
| SMA150 | 3% | +8.64 | +6.04 | 0.068 | +0.21 | yes | +8.23 | +7.96 (1.00) | 0.036 | -59.4% | +5.6 | yes |
| SMA150 | 4% | +8.92 | +6.02 | 0.068 | -0.03 | yes | +7.89 | +6.62 (1.00) | 0.045 | -59.1% | +3.6 | yes |
| SMA175 | 1% | +2.06 | +1.07 | 0.407 | -2.83 | no | +4.04 | +8.02 (1.00) | 0.187 | -67.8% | +9.6 | no |
| SMA175 | 2% | +6.83 | +4.66 | 0.127 | -0.42 | no | +7.69 | +9.52 (1.00) | 0.038 | -65.4% | +6.0 | yes |
| SMA175 | 3% | +9.80 | +7.10 | 0.029 | +0.91 | yes | +8.34 | +7.31 (1.00) | 0.022 | -60.6% | +6.0 | yes |
| SMA175 | 4% | +8.93 | +6.35 | 0.054 | +0.24 | yes | +7.60 | +4.70 (1.00) | 0.075 | -65.3% | +3.6 | yes |
| SMA200 | 1% | +3.52 | +2.81 | 0.232 | -1.51 | no | +4.72 | +8.79 (1.00) | 0.161 | -65.0% | +9.6 | no |
| SMA200 | 2% | +6.33 | +4.84 | 0.117 | -0.60 | no | +6.78 | +7.34 (1.00) | 0.092 | -59.6% | +7.9 | yes |
| SMA200 | 3% | +7.84 | +6.25 | 0.061 | +0.27 | yes | +7.46 | +7.24 (1.00) | 0.068 | -62.0% | +6.0 | yes |
| SMA200 | 4% | +8.76 | +7.89 | 0.020 | +0.89 | yes | +8.63 | +9.68 (1.00) | 0.042 | -64.5% | +3.6 | yes |
| SMA225 | 1% | +4.43 | +3.87 | 0.187 | -1.02 | no | +4.84 | +7.83 (1.00) | 0.164 | -58.9% | +10.7 | no |
| SMA225 | 2% | +6.03 | +5.41 | 0.103 | -0.18 | no | +6.93 | +8.75 (1.00) | 0.069 | -61.3% | +9.6 | yes |
| SMA225 | 3% | +7.40 | +6.64 | 0.055 | +0.16 | yes | +7.12 | +4.62 (0.60) | 0.193 | -81.1% | -57.7 | no |

Every 3-4% band rule that was run passes items 1-3 in CA on both histories except
SMA225 with a 3% band, which missed the 1987-10-16 exit (SMA225 with a 4% band was
not run). 1-2% bands whipsaw more and mostly
fail item 3 in 2000-2026. SMA175 with a 3% band (CA +9.65 on `full`, p = 0.029)
is the strongest rule found. Its one-day-lag version is unchanged on 2000-2026
(CA +10.01, p = 0.031) and fails on 1986-2026 (1987 -58 pp vs the index,
p = 0.21). Every member's 1987 escape is the same single same-close exit on
1987-10-16. Low-vol's neighbours all have positive
scores (+2.6 to +5.5 pp), but only 1 of 10 passes p <= 0.10 in CA. Monthly-100 has
none.

### 6.2 Same rule, different check frequency, execution lag, off-asset and tax-aware execution (screen, CA)

| config / variant (screen) | regime | score | full | ex10 beat | ex15 beat | boot p | max DD | trades |
|---|---|---|---|---|---|---|---|---|
|   SYN/trend/on=x3/off=mid/sma200/b0.02/D/lag1 | CA | +7.67 | +6.18 | 1.00 | 1.00 | 0.071 | -60.7% | 123 |
|   SYN/trend/on=x3/off=mid/sma200/b0.02/D/taxexec-noST | CA | -1.27 | -1.67 | 0.41 | 0.33 | 0.687 | -54.9% | 63 |
|   SYN/trend/on=x3/off=mid/sma200/b0.02/W | CA | +6.29 | +5.38 | 1.00 | 1.00 | 0.094 | -61.8% | 88 |
|   SYN/trend/on=x3/off=mid/sma200/b0.02/M | CA | +5.46 | +4.70 | 0.76 | 1.00 | 0.175 | -76.9% | 57 |
|   SYN/trend/on=x3/off=mid/sma200/b0.02/M/lag1 | CA | +9.05 | +8.50 | 1.00 | 1.00 | 0.014 | -58.1% | 66 |
|   SYN/trend/on=x3/off=mid/sma200/b0.02/M/taxexec-noST | CA | -0.63 | +0.36 | 0.47 | 0.50 | 0.461 | -76.2% | 46 |
|   SYN/trend/on=x3/off=mid/gspc-sma200/b0.02/D | CA | +5.98 | +3.88 | 0.94 | 1.00 | 0.138 | -59.7% | 133 |
|   SYN/trend/on=x3/off=one/sma200/b0.02/D | CA | +5.97 | +3.96 | 1.00 | 1.00 | 0.157 | -69.6% | 99 |
|   SYN/trend/on=x3/off=tbill/sma200/b0.02/D | CA | +5.35 | +3.77 | 1.00 | 1.00 | 0.179 | -59.5% | 101 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | CA | +6.33 | +4.84 | 1.00 | 1.00 | 0.117 | -58.8% | 108 |
|   SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one/lag1 | CA | +5.34 | +4.96 | 1.00 | 1.00 | 0.023 | -65.2% | 67 |
|   SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one/taxexec-noST | CA | +3.87 | +3.82 | 0.94 | 1.00 | 0.072 | -65.3% | 50 |
|   SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one/M | CA | +4.00 | +3.36 | 0.88 | 1.00 | 0.110 | -63.9% | 60 |
|   SYN/lowvol/rv60<0.15/b0.1/on=x3/off=tbill | CA | +3.87 | +4.59 | 0.94 | 0.92 | 0.114 | -50.9% | 71 |
|   SYN/lowvol/rv60<0.15/b0.1/on=x3/off=mid | CA | +5.37 | +6.17 | 1.00 | 1.00 | 0.060 | -45.9% | 88 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | +5.13 | +4.68 | 1.00 | 1.00 | 0.039 | -65.1% | 68 |
|   SYN/trend/on=x3/off=mid/sma100/b0.02/D | CA | +1.05 | -2.66 | 0.65 | 0.67 | 0.707 | -85.5% | 191 |
|   SYN/trend/on=x3/off=mid/sma100/b0.02/D/lag1 | CA | +2.20 | -0.63 | 0.82 | 0.83 | 0.563 | -79.6% | 193 |
|   SYN/trend/on=x3/off=mid/sma100/b0.02/W | CA | -0.51 | -3.29 | 0.29 | 0.42 | 0.760 | -74.9% | 157 |
|   SYN/trend/on=x3/off=mid/sma100/b0.02/M/lag1 | CA | +6.88 | +4.13 | 1.00 | 1.00 | 0.156 | -63.6% | 94 |
|   SYN/trend/on=x3/off=mid/sma100/b0.02/M/taxexec-noST | CA | +2.49 | +1.53 | 0.59 | 0.75 | 0.358 | -65.2% | 57 |
|   SYN/trend/on=x3/off=mid/gspc-sma100/b0.02/M | CA | +5.78 | +3.46 | 1.00 | 1.00 | 0.213 | -63.6% | 106 |
|   SYN/trend/on=x3/off=one/sma100/b0.02/M | CA | +5.74 | +3.67 | 1.00 | 1.00 | 0.177 | -72.3% | 93 |
|   SYN/trend/on=x3/off=tbill/sma100/b0.02/M | CA | +5.81 | +4.25 | 1.00 | 1.00 | 0.137 | -61.0% | 96 |
|   SYN/trend/on=x3/off=long/sma100/b0.02/M | CA | +6.71 | +4.64 | 1.00 | 1.00 | 0.111 | -63.6% | 103 |
|   SYN/trend/on=x3/off=cash/sma100/b0.02/M | CA | +5.72 | +4.00 | 1.00 | 1.00 | 0.155 | -60.9% | 54 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | CA | +6.68 | +5.06 | 1.00 | 1.00 | 0.100 | -60.9% | 102 |

The full protocol for the main execution variants:

| config | regime | score | full_excess | ex10_mean | ex10_beat | ex15_beat | boot_p | max_dd | trades | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | CA | +6.07 | +4.84 | +6.19 | 1.00 | 1.00 | 0.117 | -58.8% | 108 | no |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | FED | +7.27 | +6.09 | +7.42 | 1.00 | 1.00 | 0.091 | -57.4% | 112 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | NONE | +9.36 | +8.15 | +9.54 | 1.00 | 1.00 | 0.052 | -57.4% | 96 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D/lag1 | CA | +7.38 | +6.18 | +7.42 | 1.00 | 1.00 | 0.071 | -60.7% | 123 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D/lag1 | FED | +8.82 | +7.66 | +8.87 | 1.00 | 1.00 | 0.048 | -57.6% | 127 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D/lag1 | NONE | +11.31 | +10.03 | +11.37 | 1.00 | 1.00 | 0.020 | -54.2% | 97 | yes |
| SYN/trend/on=x2/off=mid/sma200/b0.02/D | CA | +2.67 | +2.38 | +2.75 | 0.73 | 0.81 | 0.225 | -44.2% | 106 | no |
| SYN/trend/on=x2/off=mid/sma200/b0.02/D | FED | +3.43 | +3.35 | +3.54 | 0.82 | 0.98 | 0.143 | -42.5% | 108 | no |
| SYN/trend/on=x2/off=mid/sma200/b0.02/D | NONE | +4.95 | +4.99 | +5.09 | 0.85 | 1.00 | 0.076 | -42.5% | 91 | yes |
| SYN/trend/on=x3/off=tbill/sma200/b0.02/D | CA | +5.12 | +3.77 | +5.23 | 1.00 | 1.00 | 0.179 | -59.5% | 101 | no |
| SYN/trend/on=x3/off=tbill/sma200/b0.02/D | FED | +6.17 | +4.83 | +6.29 | 1.00 | 1.00 | 0.142 | -57.9% | 102 | no |
| SYN/trend/on=x3/off=tbill/sma200/b0.02/D | NONE | +7.95 | +6.56 | +8.07 | 1.00 | 1.00 | 0.092 | -57.8% | 92 | yes |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D/taxexec-noST | CA | -1.19 | -1.67 | -1.27 | 0.40 | 0.32 | 0.687 | -54.9% | 63 | no |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D/taxexec-noST | FED | -1.06 | -1.41 | -1.17 | 0.43 | 0.34 | 0.654 | -54.8% | 63 | no |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D/taxexec-noST | NONE | +9.36 | +8.15 | +9.54 | 1.00 | 1.00 | 0.052 | -57.4% | 96 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | +5.14 | +4.68 | +5.15 | 1.00 | 1.00 | 0.039 | -65.1% | 68 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | FED | +6.31 | +5.97 | +6.29 | 1.00 | 1.00 | 0.014 | -63.2% | 68 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | NONE | +8.24 | +8.04 | +8.16 | 1.00 | 1.00 | 0.003 | -60.9% | 53 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one/lag1 | CA | +5.37 | +4.96 | +5.38 | 1.00 | 1.00 | 0.023 | -65.2% | 67 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one/lag1 | FED | +6.58 | +6.27 | +6.57 | 1.00 | 1.00 | 0.010 | -63.4% | 68 | yes |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one/lag1 | NONE | +8.56 | +8.33 | +8.48 | 1.00 | 1.00 | 0.002 | -61.3% | 53 | yes |

* **Check frequency matters enormously for SMA100.** Monthly +6.68, weekly
  -0.51, daily +1.05 (CA score). For SMA200 with a 2% band the three are close:
  daily +6.33, weekly +6.29, monthly +5.46.
* **One-day lag on 2000-2026** does not hurt Daily-200 (CA +7.38, p = 0.07 on
  `full`) or Low-vol (+5.37, p = 0.02). The lag only matters in a gap crash
  (section 5).
* **Off-asset**: intermediate Treasuries beat T-bills or 1x SPY as the off-state
  over 2000-2026 (Daily-200: mid +6.33, T-bills +5.35, SPY +5.97 on the screen).
  That is partly the 2000-2020 bond bull market, a choice with some hindsight in
  it. The T-bill version is reported as the star-removed check: CA +5.12,
  p = 0.18 on `full`.
* **Tax-aware execution backfires.** Selling losses always but never realising a
  short-term gain (`taxexec-noST`) blocks the exits that make the trend rule work:
  Daily-200 drops to -1.19 in CA (15-year beat 0.32).

### 6.3 Rebalance-timing luck of monthly rules

`leverage.regime` evaluates its monthly check on the first trading day of each
month, and `kind=weights_x offset_days` does not move that check. So the monthly
SMA100 rule was re-implemented with `common.trend` (evaluated only on rebalance
days) and run with the month boundary shifted by 0/7/14/21 days. Offset 0
reproduces `leverage.regime` (identical full-period excess +5.06 in CA), which
cross-checks the implementation.

| config | regime | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | trades | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset0 | CA | +6.59 | +5.06 | 1.00 | 1.00 | 0.100 | -60.9% | 102 | yes |
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset0 | NONE | +10.03 | +8.37 | 1.00 | 1.00 | 0.039 | -52.6% | 78 | yes |
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset14 | CA | +3.50 | +3.45 | 0.94 | 0.98 | 0.216 | -71.7% | 94 | no |
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset14 | NONE | +6.26 | +5.80 | 1.00 | 1.00 | 0.144 | -71.7% | 80 | no |
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset21 | CA | +1.47 | -1.67 | 0.67 | 0.70 | 0.620 | -78.5% | 102 | no |
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset21 | NONE | +3.12 | -0.68 | 0.70 | 0.83 | 0.541 | -78.5% | 97 | no |
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset7 | CA | +1.11 | +1.59 | 0.72 | 0.72 | 0.377 | -65.0% | 84 | no |
| SYN/trend-emul/on=x3/off=mid/sma100/b0.02/M/offset7 | NONE | +2.75 | +3.30 | 0.88 | 0.96 | 0.275 | -65.0% | 79 | no |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset0 | CA | +5.81 | +4.25 | 1.00 | 1.00 | 0.137 | -61.0% | 96 | no |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset0 | NONE | +8.86 | +7.12 | 1.00 | 1.00 | 0.059 | -58.9% | 76 | yes |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset14 | CA | +2.31 | +2.28 | 0.88 | 0.94 | 0.307 | -72.1% | 87 | no |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset14 | NONE | +4.52 | +3.91 | 0.94 | 1.00 | 0.233 | -72.1% | 79 | no |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset21 | CA | +0.40 | -2.74 | 0.61 | 0.57 | 0.678 | -81.2% | 101 | no |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset21 | NONE | +1.77 | -2.21 | 0.67 | 0.74 | 0.640 | -81.2% | 97 | no |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset7 | CA | +0.32 | +0.71 | 0.55 | 0.51 | 0.455 | -66.9% | 86 | no |
| SYN/trend-emul/on=x3/off=tbill/sma100/b0.02/M/offset7 | NONE | +1.69 | +2.01 | 0.63 | 0.79 | 0.366 | -66.9% | 77 | no |

The previous researcher's top rule is mostly check-day luck. Shifting its
monthly decision by one week cuts the CA score from +6.59 to +1.11; across the
four offsets it averages +3.17, and only offset 0 passes items 1-3. The same is
visible in the SMA200 monthly rule with a one-day signal lag, which scores +9.05
against +5.46 without the lag.

### 6.4 Synthetic-cost sensitivity (RAW = no swap spread, `full`)

| config | regime | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | trades | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|
| RAW/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | +5.80 | +5.30 | 1.00 | 1.00 | 0.022 | -65.4% | 68 | yes |
| RAW/lowvol/rv60<0.15/b0.1/on=x3/off=one | NONE | +9.10 | +8.83 | 1.00 | 1.00 | 0.001 | -60.9% | 58 | yes |
| RAW/mix/x30.55+b30.45/calQ | CA | +7.58 | +4.52 | 0.99 | 1.00 | 0.112 | -72.8% | 214 | no |
| RAW/mix/x30.55+b30.45/calQ | NONE | +10.33 | +6.44 | 1.00 | 1.00 | 0.082 | -68.4% | 214 | yes |
| RAW/trend/on=x3/off=mid/sma100/b0.02/M | CA | +7.36 | +5.86 | 1.00 | 1.00 | 0.079 | -60.9% | 103 | yes |
| RAW/trend/on=x3/off=mid/sma100/b0.02/M | NONE | +11.06 | +9.43 | 1.00 | 1.00 | 0.024 | -52.0% | 82 | yes |
| RAW/trend/on=x3/off=mid/sma200/b0.02/D | CA | +6.90 | +5.63 | 1.00 | 1.00 | 0.089 | -58.5% | 113 | yes |
| RAW/trend/on=x3/off=mid/sma200/b0.02/D | NONE | +10.46 | +9.18 | 1.00 | 1.00 | 0.034 | -57.4% | 96 | yes |

The brief's uncalibrated formula (T-bill financing only) flatters every leader by
0.7-1.0 pp/yr and lowers its p-value. Daily-200 would read CA p = 0.089 instead
of 0.117, Monthly-100 0.079 instead of 0.100. The calibrated "C" series match
the real funds over 2006/2009-2026 (section 2), so the calibrated numbers are the
ones to use. A study built on the raw formula would have "passed" item 3 for
these rules.

### 6.5 Stricter tax accounting (`research.lab.realism`)

Distributions are charged yearly at their real character. The leveraged sleeve
uses the real fund's distribution history where it exists (UPRO/SSO/BIL/TMF);
synthetic years before that are not charged. The SPY benchmark gets the same
treatment.

| config | regime | start | engine excess (to 2026-07) | with annual distribution tax | difference |
|---|---|---|---|---|---|
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2000-01-01 | +4.84 | +4.64 | -0.20 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2005-01-01 | +3.91 | +3.87 | -0.05 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2010-01-01 | +3.48 | +3.47 | -0.01 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2015-01-01 | +0.21 | +0.23 | +0.01 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2000-01-01 | +6.10 | +5.77 | -0.32 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2005-01-01 | +5.23 | +5.04 | -0.18 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2010-01-01 | +4.84 | +4.71 | -0.13 |
| SYN/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2015-01-01 | +0.90 | +0.82 | -0.08 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | 2000-01-01 | +4.68 | +4.78 | +0.10 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | 2005-01-01 | +4.67 | +4.77 | +0.10 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | 2010-01-01 | +5.67 | +5.75 | +0.08 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | CA | 2015-01-01 | +4.71 | +4.70 | -0.00 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | FED | 2000-01-01 | +5.97 | +6.01 | +0.04 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | FED | 2005-01-01 | +6.19 | +6.24 | +0.04 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | FED | 2010-01-01 | +7.61 | +7.63 | +0.03 |
| SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one | FED | 2015-01-01 | +6.34 | +6.32 | -0.03 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | CA | 2000-01-01 | +5.06 | +4.99 | -0.07 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | CA | 2005-01-01 | +5.12 | +5.16 | +0.04 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | CA | 2010-01-01 | +2.94 | +3.01 | +0.06 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | CA | 2015-01-01 | +1.99 | +1.95 | -0.04 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | FED | 2000-01-01 | +6.38 | +6.18 | -0.21 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | FED | 2005-01-01 | +6.66 | +6.55 | -0.10 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | FED | 2010-01-01 | +4.36 | +4.30 | -0.06 |
| SYN/trend/on=x3/off=mid/sma100/b0.02/M | FED | 2015-01-01 | +2.92 | +2.78 | -0.14 |
| SYN/mix/x30.55+b30.45/calQ | CA | 2000-01-01 | +3.51 | +3.59 | +0.09 |
| SYN/mix/x30.55+b30.45/calQ | CA | 2005-01-01 | +3.73 | +3.75 | +0.02 |
| SYN/mix/x30.55+b30.45/calQ | CA | 2010-01-01 | +5.83 | +5.84 | +0.01 |
| SYN/mix/x30.55+b30.45/calQ | CA | 2015-01-01 | -0.85 | -0.90 | -0.06 |
| SYN/mix/x30.55+b30.45/calQ | FED | 2000-01-01 | +4.26 | +4.24 | -0.01 |
| SYN/mix/x30.55+b30.45/calQ | FED | 2005-01-01 | +4.66 | +4.59 | -0.07 |
| SYN/mix/x30.55+b30.45/calQ | FED | 2010-01-01 | +7.14 | +7.06 | -0.08 |
| SYN/mix/x30.55+b30.45/calQ | FED | 2015-01-01 | -0.50 | -0.62 | -0.12 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2009-07-01 | +4.71 | +4.80 | +0.09 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2012-01-01 | +5.25 | +5.33 | +0.08 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2015-01-01 | +0.08 | +0.09 | +0.01 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | CA | 2018-01-01 | -1.64 | -1.71 | -0.07 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2009-07-01 | +6.54 | +6.51 | -0.03 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2012-01-01 | +6.88 | +6.84 | -0.03 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2015-01-01 | +0.77 | +0.69 | -0.08 |
| REAL/trend/on=x3/off=mid/sma200/b0.02/D | FED | 2018-01-01 | -1.40 | -1.54 | -0.14 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | CA | 2009-07-01 | +5.01 | +5.09 | +0.07 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | CA | 2012-01-01 | +7.56 | +7.63 | +0.07 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | CA | 2015-01-01 | +4.61 | +4.61 | -0.00 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | CA | 2018-01-01 | +3.57 | +3.49 | -0.08 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | FED | 2009-07-01 | +7.05 | +7.07 | +0.02 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | FED | 2012-01-01 | +9.82 | +9.84 | +0.02 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | FED | 2015-01-01 | +6.23 | +6.21 | -0.03 |
| REAL/lowvol/rv60<0.15/on=x3/off=one | FED | 2018-01-01 | +4.88 | +4.81 | -0.07 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2000-01-01 | +7.10 | +6.86 | -0.23 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2005-01-01 | +7.50 | +7.42 | -0.07 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2010-01-01 | +6.39 | +6.35 | -0.04 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2015-01-01 | +4.04 | +4.02 | -0.02 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2000-01-01 | +8.57 | +8.22 | -0.35 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2005-01-01 | +9.21 | +9.00 | -0.21 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2010-01-01 | +8.06 | +7.91 | -0.16 |
| SYN/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2015-01-01 | +5.30 | +5.18 | -0.12 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2009-07-01 | +7.70 | +7.78 | +0.08 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2012-01-01 | +8.80 | +8.87 | +0.07 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2015-01-01 | +4.09 | +4.09 | +0.00 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | CA | 2018-01-01 | +2.17 | +2.10 | -0.07 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2009-07-01 | +9.89 | +9.84 | -0.05 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2012-01-01 | +10.84 | +10.79 | -0.05 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2015-01-01 | +5.37 | +5.27 | -0.10 |
| REAL/trend/on=x3/off=mid/sma175/b0.03/D | FED | 2018-01-01 | +3.04 | +2.89 | -0.15 |

The engine's deferral of distributions changes the leaders' excess by only -0.2
to +0.1 pp/yr. 3x funds distribute little (UPRO about 0.4%/yr) while SPY
distributes about 1.8%/yr, which partly offsets the yearly tax on the Treasury
off-asset's interest.

### 6.6 Real ETFs only (2009-2026)

On the real-ETF window everything leveraged looks good, because the window
starts after the 2008 crash. UPRO buy-and-hold: CA score +13.55, p = 0.004.
Low-vol: +6.43, p = 0.087 (passes items 1-3). Daily-200: +4.50, p = 0.157.
These numbers say nothing about a 2000-02 or 2008 bear market, which the window
does not contain.

## 7. Family diagnostics (walk-forward, PBO, deflated Sharpe)

`report.diagnostics` on every screened SYN configuration with aligned 2000
starts (hindsight random menus excluded). On the yearly-start screen protocol the
lab-default walk-forward steps four starts, which gives only 3-4 decisions. The
same `metrics.walk_forward` with a step of one start (12 and 19 decisions,
overlapping out-of-sample windows) is shown too.

| regime | sub-family | configs | WF 10y->5y OOS (beat) | WF 5y->3y OOS (beat) | yearly WF 10->5 OOS (beat, n) | avg config OOS | yearly WF 5->3 OOS (beat, n) | PBO | OOS of IS-best (CSCV) | DSR of best | best by monthly mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | ALL | 745 | +7.78 (1.00) | +2.41 (0.50) | +6.45 (0.75, n=12) | +1.65 | +12.71 (0.68, n=19) | 0.667 | -7.72 | 0.199 | SYN/trend/on=x3/off=mid/sma200/b0.02/M/lag1 |
| CA | bh | 8 | +13.35 (1.00) | -3.08 (0.50) | +13.31 (0.75, n=12) | +9.03 | +10.16 (0.58, n=19) | 0.933 | -11.06 | 0.307 | SYN/bh/x2 |
| CA | dualmom | 21 | +3.89 (1.00) | +9.89 (1.00) | +5.57 (0.83, n=12) | +1.17 | +6.26 (0.74, n=19) | 0.936 | -2.61 | 0.407 | SYN/dualmom/spy/qqq-3x/lb252/top1/safe=mid |
| CA | lowvol | 104 | +4.76 (1.00) | +0.87 (0.75) | +6.13 (0.92, n=12) | +2.24 | +4.60 (0.79, n=19) | 0.377 | +0.58 | 0.207 | SYN/lowvol/rv60<0.15/b0.1/on=x3/off=mid |
| CA | misc | 13 | +2.27 (0.67) | +0.63 (0.25) | +4.56 (0.75, n=12) | +3.09 | +1.78 (0.37, n=19) | 0.669 | -3.58 | 0.402 | SYN/nearhigh/dd<0.1/on=x3/off=one |
| CA | mix | 144 | +3.28 (0.67) | -0.92 (0.50) | +4.79 (0.75, n=12) | +2.55 | +4.51 (0.79, n=19) | 0.679 | -0.66 | 0.038 | SYN/mix/x30.7+b30.3/calQ |
| CA | overlay | 24 | -0.81 (0.33) | +5.64 (0.75) | -0.05 (0.42, n=12) | +0.81 | +3.79 (0.68, n=19) | 0.834 | -0.84 | 0.471 | SYN/overlay/core0.5/sat=x3/mid/sma200/M |
| CA | qqq | 24 | +8.85 (1.00) | +9.76 (1.00) | +11.05 (0.92, n=12) | +10.18 | +10.10 (0.84, n=19) | 0.953 | -4.66 | 0.558 | SYN/qtrend/on=q2/off=mid/qqq-sma200/M |
| CA | trend | 304 | +5.79 (1.00) | +15.29 (1.00) | +3.78 (0.67, n=12) | +1.52 | +8.18 (0.79, n=19) | 0.385 | +1.88 | 0.548 | SYN/trend/on=x3/off=mid/sma200/b0.02/M/lag1 |
| CA | trend3 | 24 | +0.98 (0.67) | +7.06 (0.75) | +0.27 (0.50, n=12) | -2.55 | +1.59 (0.58, n=19) | 0.320 | -1.02 | 0.232 | SYN/trend3/sma200+tsmom252x/top=x3/bot=mid/M |
| CA | vt | 79 | -0.83 (0.00) | -0.74 (0.50) | +0.02 (0.25, n=12) | -2.20 | +0.07 (0.53, n=19) | 0.351 | -0.90 | 0.114 | SYN/vt/t0.3/w20/x2/M/eb0.15/trend=sma200 |
| NONE | ALL | 746 | +11.17 (1.00) | +4.37 (0.50) | +10.16 (0.75, n=12) | +3.89 | +16.35 (0.79, n=19) | 0.527 | -2.93 | 0.227 | SYN/trend/on=x3/off=mid/sma200/b0.02/M/lag1 |
| NONE | bh | 8 | +15.71 (1.00) | -2.38 (0.50) | +15.53 (0.75, n=12) | +10.68 | +12.70 (0.58, n=19) | 0.917 | -10.57 | 0.296 | SYN/bh/x2 |
| NONE | dualmom | 21 | +7.68 (1.00) | +14.15 (1.00) | +8.82 (0.92, n=12) | +4.80 | +10.60 (0.89, n=19) | 0.927 | -0.28 | 0.499 | SYN/dualmom/spy/qqq-3x/lb252/top1/safe=mid |
| NONE | lowvol | 105 | +7.94 (1.00) | +1.73 (0.75) | +9.31 (0.92, n=12) | +5.97 | +6.76 (0.79, n=19) | 0.252 | +4.02 | 0.576 | SYN/lowvol/rv60<0.15/b0.1/on=x3/off=mid |
| NONE | misc | 13 | +7.77 (0.67) | +1.14 (0.25) | +7.98 (0.75, n=12) | +5.30 | +3.95 (0.47, n=19) | 0.553 | -1.60 | 0.424 | SYN/nearhigh/dd<0.1/on=x3/off=one |
| NONE | mix | 144 | +4.39 (0.67) | +0.02 (0.50) | +6.65 (0.75, n=12) | +3.66 | +7.12 (0.74, n=19) | 0.552 | +0.57 | 0.004 | SYN/mix/x30.55+b30.45/calQ |
| NONE | overlay | 24 | -0.71 (0.33) | +8.18 (1.00) | +0.32 (0.42, n=12) | +1.39 | +5.58 (0.79, n=19) | 0.662 | +0.12 | 0.563 | SYN/overlay/core0.5/sat=x3/mid/sma200/M |
| NONE | qqq | 24 | +17.67 (1.00) | +13.23 (1.00) | +19.29 (1.00, n=12) | +15.31 | +14.83 (0.89, n=19) | 0.929 | -2.84 | 0.666 | SYN/qtrend/on=q2/off=mid/qqq-sma200/M |
| NONE | trend | 304 | +2.90 (0.67) | +17.11 (1.00) | +3.78 (0.50, n=12) | +3.68 | +10.13 (0.79, n=19) | 0.269 | +5.16 | 0.611 | SYN/trend/on=x3/off=mid/sma200/b0.02/M/lag1 |
| NONE | trend3 | 24 | -7.05 (0.00) | +12.88 (0.75) | -2.06 (0.33, n=12) | -0.76 | +4.09 (0.63, n=19) | 0.239 | +1.31 | 0.330 | SYN/trend3/sma200+tsmom252x/top=x3/bot=mid/M |
| NONE | vt | 79 | +2.67 (1.00) | +2.39 (0.75) | +3.20 (0.83, n=12) | -0.13 | +2.29 (0.58, n=19) | 0.292 | +1.16 | 0.217 | SYN/vt/t0.25/w20/x3/M/eb0.15/trend=sma200 |

Before the neighbourhood refinements were added (the interrupted run's coarse
grid, `diag_sub_screen.json`):

| regime | sub-family | configs | WF 10y->5y OOS (beat) | WF 5y->3y OOS (beat) | yearly WF 10->5 OOS (beat, n) | avg config OOS | yearly WF 5->3 OOS (beat, n) | PBO | OOS of IS-best (CSCV) | DSR of best | best by monthly mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | ALL | 532 | +6.98 (1.00) | -1.45 (0.50) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.828 | -9.36 | 0.055 | SYN/trend/on=x3/off=mid/sma100/b0.02/M |
| CA | lowvol | 28 | +1.04 (0.67) | -0.88 (0.75) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.371 | +0.39 | 0.340 | SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one |
| CA | mix | 138 | +3.28 (0.67) | -0.92 (0.50) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.677 | -0.63 | 0.036 | SYN/mix/x30.7+b30.3/calQ |
| CA | trend | 184 | -0.21 (0.67) | +13.06 (1.00) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.700 | -1.04 | 0.309 | SYN/trend/on=x3/off=mid/sma100/b0.02/M |
| CA | vt | 72 | -1.79 (0.00) | -0.97 (0.50) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.521 | -1.96 | 0.070 | SYN/vt/t0.25/w60/x2/M/eb0.15/trend=sma200 |
| NONE | ALL | 531 | +9.97 (1.00) | +4.37 (0.50) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.736 | -5.35 | 0.082 | SYN/trend/on=x3/off=mid/sma100/b0.02/M |
| NONE | lowvol | 27 | +3.03 (0.67) | +1.55 (0.75) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.269 | +4.01 | 0.773 | SYN/lowvol/rv60<0.15/b0.1/on=x3/off=one |
| NONE | mix | 138 | +4.39 (0.67) | +0.02 (0.50) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.547 | +0.61 | 0.003 | SYN/mix/x30.55+b30.45/calQ |
| NONE | trend | 184 | +1.75 (0.67) | +14.74 (1.00) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.551 | +1.38 | 0.434 | SYN/trend/on=x3/off=mid/sma100/b0.02/M |
| NONE | vt | 72 | +2.67 (1.00) | +4.55 (0.75) | n/a (n/a, n=None) | n/a | n/a (n/a, n=None) | 0.279 | +0.97 | 0.269 | SYN/vt/t0.25/w20/x3/M/eb0.15/trend=sma200 |

* **Walk-forward selection** ("pick the best leveraged config on the trailing
  window, run it forward") is positive out of sample in CA in all four variants
  for the whole family (+2.4 to +12.7 pp), and for trend and low-vol. Part of that
  is simply that most leveraged configs beat SPY over 2010-2026: the average
  config is also positive out of sample (+1.6 pp in CA for the yearly 10->5
  version). With 3 to 19 overlapping decisions, these are weak tests.
* **PBO is 0.67 for the whole family** (0.83 on the coarse grid alone), so the
  ranking inside the family is mostly noise. For the trend sub-family it fell from
  0.70 to 0.39 once the neighbourhoods and the post-hoc plateau were added. That fall reflects adding many
  near-copies of the winners, which makes ranks more stable, not new evidence.
* The deflated Sharpe ratio of the best config's after-tax monthly excess is
  0.04-0.56 across sub-families and 0.20 for the family (it needs about 0.95):
  nothing survives the multiple-testing penalty.

Item 4 therefore fails at the family level.

## 8. Hindsight checks (PROTOCOL 5.3)

* **SPY-based rules** use no star instrument. The off-asset (intermediate
  Treasuries) benefited from falling rates; the T-bill and 1x-SPY off-state
  versions are reported throughout.
* **QQQ-based rules** (leveraged dual momentum SPY/QQQ, 3x QQQ trend) were re-run
  with (b) QQQ removed and (a) the same rule on 20 random "SPY + X" menus and 20
  random "3x X trend" funds. X is drawn with fixed seeds from
  `common.BROAD_EQUITY_POOL_2003` (QQQ and SPY near-duplicates excluded). Each X is
  held through a cost-calibrated synthetic 2x/3x series.

QQQ removed (screen):

| config | regime | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | trades | items 1-3 |
|---|---|---|---|---|---|---|---|---|---|
| SYN/dualmom/spy/dia-2x/lb252/top1/safe=mid | CA | +3.55 | +2.39 | 0.76 | 0.83 | 0.222 | -62.7% | 113 | no |
| SYN/dualmom/spy/dia-2x/lb252/top1/safe=mid | NONE | +6.90 | +5.42 | 0.82 | 1.00 | 0.072 | -58.9% | 95 | yes |
| SYN/dualmom/spy/iwm-2x/lb252/top1/safe=mid | CA | -3.48 | -1.85 | 0.50 | 0.27 | 0.698 | -67.9% | 130 | no |
| SYN/dualmom/spy/iwm-2x/lb252/top1/safe=mid | NONE | -1.70 | +0.64 | 0.50 | 0.36 | 0.447 | -65.1% | 115 | no |
| SYN/dualmom/spy/mdy-2x/lb252/top1/safe=mid | CA | +0.01 | +0.49 | 0.53 | 0.50 | 0.434 | -59.8% | 112 | no |
| SYN/dualmom/spy/mdy-2x/lb252/top1/safe=mid | NONE | +2.18 | +2.86 | 0.59 | 0.58 | 0.237 | -58.9% | 100 | no |
| SYN/dualmom/spy/qqq-2x/lb252/top1/safe=mid | CA | +5.52 | +2.88 | 0.94 | 1.00 | 0.230 | -73.1% | 106 | no |
| SYN/dualmom/spy/qqq-2x/lb252/top1/safe=mid | NONE | +9.12 | +5.78 | 0.94 | 1.00 | 0.113 | -73.1% | 102 | no |
| SYN/dualmom/us3-noqqq-2x/lb252/top1/safe=mid | CA | +1.91 | +0.54 | 0.59 | 0.67 | 0.442 | -60.9% | 134 | no |
| SYN/dualmom/us3-noqqq-2x/lb252/top1/safe=mid | NONE | +4.89 | +3.29 | 0.65 | 0.75 | 0.209 | -58.9% | 114 | no |

Random menus (screen):

| rule | regime | random menus | QQQ original score | median score | mean score | share score > 0 | share full > 0 | share >= QQQ original | median boot p | share passing items 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| dualmom-rand | CA | 20 | +5.52 | +0.25 | +0.74 | 0.55 | 0.75 | 0.05 | 0.402 | 0.05 |
| dualmom-rand | NONE | 20 | +9.12 | +2.74 | +2.95 | 0.80 | 1.00 | 0.00 | 0.199 | 0.20 |
| qtrend-rand | CA | 20 | +4.70 | -4.07 | -2.86 | 0.40 | 0.35 | 0.20 | 0.695 | 0.00 |
| qtrend-rand | NONE | 20 | +7.33 | -3.29 | -1.97 | 0.40 | 0.35 | 0.15 | 0.633 | 0.10 |

The QQQ results are mostly the choice of QQQ. With QQQ removed, leveraged dual
momentum over SPY and MDY/DIA/IWM, or over SPY+MDY+DIA, loses most of its edge
(table above). On 20 random "SPY + X" menus the same rule has a median CA score of
+0.25 pp (QQQ original +5.52); only 1 of 20 menus did as well (XLY), and 1 of 20
passes items 1-3 (S&P 500 growth, SPYG). The 3x trend rule on a random fund has a
median CA score of -4.07 pp (QQQ original +4.70), and 13 of 20 had drawdowns
deeper than -80%. Neither QQQ rule passed the bar to begin with (CA p 0.23 and
0.47).

## 9. Representative failures

* **Static 3x S&P (never rebalanced)**: CA full -1.32 pp/yr from 2000. Max
  drawdown -98.2%. Worst after-tax wealth 0.03 of the start. 47% of starts were at
  some point down more than 50% after tax, and 35% down more than 75%.
* **Static 2x**: CA full +0.82, drawdown -88.4%, P(-50%) 0.34.
* **HFEA 55/45 UPRO/TMF (quarterly)**: CA score +6.72 but full +3.51, p = 0.18,
  drawdown -75.1%. 2000-2010 -0.40 pp/yr; 2020-2026 -6.28 pp/yr (2022: -61.6%
  vs SPY -16.8%). 0 of 17 neighbours pass items 1-3. On the 1986+ history it
  scores +6.27 but p = 0.13 with a -75% drawdown.
* **Volatility targeting** (79 configs): CA median score -1.3 pp, best +2.4 pp
  on the screen, and none passes items 1-3. The lab-default walk-forward is
  negative (10->5: -0.8 pp). The 10% vol targets trailed SPY by 2.5-4.3 pp/yr.
* **Daily SMA rules without a band** whipsaw: 3x/T-bills SMA200 with 0% band, CA
  full +0.58, 378 trades, turnover 5/yr, p = 0.47.
* **Leveraged dip-buying** (3x after a 10-30% drawdown): all six negative in CA
  (-0.8 to -5.7 pp).
* **3x QQQ trend**: CA score +5.37 but full +0.24 with a -95.4% drawdown.
* **The 3-state SMA200 + SMA50 ladder (daily)**: the worst configs in the family
  (-4.6 to -5.5 pp in CA).

## 10. Taxable-account realities

* A trend switch realises the leveraged position's gain, often short-term.
  Daily-200 makes about 4 trades a year (turnover 1.5x/yr), Low-vol about 2.6
  (1.0x). CA tax costs the leaders about 3 pp/yr of excess relative to NONE.
* Fixed leveraged mixes have to be rebalanced (the leveraged sleeve drifts
  fast), and rebalancing realises gains: HFEA traded 214 times in 26.5 years.
  Never-rebalanced versions avoid that tax but are only static leverage: 50% SPY
  + 50% 2x bought in 2000 scores +1.58 in CA (full +0.43, p = 0.37, drawdown
  -69%), and 67% SPY + 33% 3x scores +2.01 (full -0.40). The same 67/33 bought
  in 2010 with real funds scores +6.33 (p = 0.023), the bull-market sample again.
* Tax-aware execution, which defers gains, defeats a timing rule's purpose
  (section 6.2).
* Leveraged ETFs distribute little (taxed as ordinary income when they do). The
  Treasury off-asset's interest is taxed yearly at ordinary rates (CA-exempt).
  Net effect: under 0.3 pp/yr (section 6.5).

## 11. PROTOCOL section 3 checklist, CA

| item | Daily 3x, SMA175 3% band (post hoc) | Daily-200 3x, 2% band (pre-registered) | Low-vol 3x | Monthly-100 3x |
|---|---|---|---|---|
| 1. score > 0, full > 0 | yes (+9.65, +7.10) | yes (+6.07, +4.84) | yes (+5.14, +4.68) | yes (+6.52, +5.06) |
| 2. 10y beat >= 0.75, 15y beat >= 0.85 | yes (1.00, 1.00; worst 10y +4.81) | yes (1.00, 1.00) | yes (1.00, 1.00) | yes (1.00, 1.00) |
| 3. boot p <= 0.10 | yes (0.029; 0.022 on 1986-2026; 0.031 real ETFs 2009+) | **no** (0.117; 0.09 on 1986-2026) | yes (0.039; **0.12 on 1986-2026**) | yes (0.100; 0.29 on 1986-2026) |
| 4. family walk-forward > 0 and PBO < 0.5 | **no** at family level (walk-forward positive, PBO 0.67, family DSR 0.20); trend sub-family PBO 0.39 after refinements | **no** (same family) | **no** at family level (low-vol sub-family PBO 0.38) | **no** |
| 5. neighbourhood passes | yes (5/8 pass items 1-3, all 3-4% band members do, on both histories; 8/8 pass items 1-2) | **partly** (3/8 on 2000-26, 4/8 on 1986-2026; 8/8 pass items 1-2) | **no** (1/10) | **no** (0/8; 1-week check shift: +1.1) |
| 6. no hindsight instrument | yes (S&P; Treasuries as off-asset; selected post hoc) | yes (T-bill version p = 0.18) | yes | yes |
| 7. pre-2000 holdout does not contradict | **fragile**: ho10 +7.81 (1.00), but 1987 survival depends on same-close execution (lag-1: -58 pp in 1987, -79% drawdown, p = 0.21) | **fragile** (lag-1: -57.7 pp in 1987, -80% drawdown) | **weak** (p = 0.12, -19 pp in 1987) | **contradicts** (-50 pp in 1987, -81% drawdown) |

In FED, all four pass items 1-3. SMA175 3% band has p = 0.016, Daily-200
0.091, Low-vol 0.014 and Monthly-100 0.068. Items 4, 5 and 7 are as above.

## 12. Conclusion

Leveraged ETFs raise expected return by raising equity exposure. Over 2000-2026
a filter that steps out of the market in long bear markets turned that extra
exposure into a large average after-tax excess over SPY, even in California. The
pre-registered 3x rules made +5 to +6.5 pp/yr, and the wide-band daily rules
found afterwards made +8 to +10 pp/yr, beating SPY in every 10- and 15-year
window.

The best of them (daily SMA175 with a 3% band, 3x S&P / Treasuries) passes
items 1-3 on 2000-2026, on real ETFs since 2009 and on the 1986-2026 synthetic
history. Its neighbourhood is a plateau, and it is modestly better risk-adjusted
than SPY (Sharpe 0.58 vs 0.51). It still falls short of "good confidence" for
three reasons. It came out of a 900+ configuration search whose family-level
overfitting diagnostics fail (PBO 0.67, DSR 0.20). It was singled out after the
fact. And the only gap crash in the data was survived through one same-close
trade on 1987-10-16; the version that trades a day later lost 58 pp vs the
index that year and fell 79%.

A real investor would implement it with UPRO and IEF, placing market-on-close
orders on signal days. They should expect long stretches of underperformance
(2000, 2007, 2015, 2022), drawdowns of -60% (about -80% in a 1987-style gap) and
about 1.7x SPY's volatility (2.2x average equity exposure, 3x when invested). That is a high-risk sleeve with a plausible but unproven
edge, not a proven replacement for SPY.

## Files

* `research/lab/families/leverage.py`: signals `leverage.bandmix`, `leverage.regime`, `leverage.voltarget`, `leverage.dualmom`, `leverage.overlay` (unchanged since the first run).
* `research/lab/scratch/leverage/`: `build_synthetic.py` (SYN series and validation), `grids.py` (all grids), `run_screen1/2.py`, `run_stage3.py` (first run), `run_stage4.py` (this run: stages A-I), `run_hindsight.py`, `run_posthoc*.py` (the 3-4% band plateau), `run_realism.py`, `run_exposures.py`, `run_diag2.py`, `final_report2.py`, `build_md.py` + `md_template.md` (build this report), `candidates_out.py`, `labels.json` (label of every config), `logs/`.
* `research/lab/results/leverage_table.csv`: every cached result (all protocols and regimes) with a `protocol` column.
