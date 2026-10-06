# Stocks family: individual S&P 500 stocks (survivorship-biased, with controls)

Family key `stocks`. Code: `research/lab/families/stocks.py` (module v4). Scripts, logs and pickled
records: `research/lab/scratch/stocks/`. Table of every record: `research/lab/results/stocks_table.csv`.
All numbers come from the lab engine (the site's engine). "Excess" means after-tax CAGR minus SPY
buy-and-hold over the same window, in CAGR fraction (0.01 = 1 percentage point a year). CA is the primary
regime, FED secondary, NONE diagnostic.

## Bottom line

**No individual-stock strategy can be recommended with confidence.** On this data, stock-picking skill
cannot be told apart from data and execution artifacts:

1. **Random picks "beat" SPY.** Picking 20 stocks at random from the point-in-time S&P 500 panel, with the
   site's tax-managed machinery, scores **+3.24 pp/yr in CA** (mean of 10 seeds, full protocol), and **9 of
   10 random seeds pass criteria 1-3 of the confidence bar** (score, full excess, ex10/ex15 beat rates,
   boot_p). With the lab's pro-rata tax execution, 5 of 5 random seeds pass. This is the survivorship
   bias: the panel only has prices for companies that still exist (37% of the 2000 index, 54% of 2010,
   78% of 2020), so every bankrupt or delisted loser is missing.
2. **Signals add nothing measurable over random** with identical machinery. Across 74 credible screened
   configs, strategy minus random averages **-0.43 pp/yr in CA and -1.52 pp/yr in NONE** (38% / 14% of
   configs positive). Finalists on the full protocol: 12-1 momentum quarterly TM (the site preset's rule
   on stocks, F1) -0.19 CA / -2.77 NONE; the same rule with pro-rata execution -0.09 CA (bootstrap p
   0.72); 6-1 momentum semi-annual TM (F2, the best config) +1.02 CA (p 0.14) / -0.37 NONE.
3. **The best result rests on a few stocks.** F2's P&L since 2000 is 69% AAPL, 18% AMD and 7% AMZN (AAPL
   was bought 2000-01-03 and never sold). Removing 9 such names from the universe of the strategy *and*
   of its controls turns F2's edge over random from +1.03 into **-0.92 pp/yr**, and its vs-SPY record
   from ex10_beat 0.94 / boot_p 0.000 into 0.65 / 0.18 (screen protocol). F1 falls to +0.18 pp/yr vs SPY.
   The edge is also episodic: 12-1 momentum trailed random by 6-9 pp/yr for 2005-09 starts and led
   strongly only for 2020-23 starts.
4. **The panel is not neutral across signals.** "Buy the losers" probes (deepest 52-week drawdown, 3-year
   losers, highest volatility, smallest size) beat random by +4 to +7 pp/yr. That is what a survivor-only
   panel produces: every past loser in it is one that recovered. Against the real equal-weight S&P 500 fund
   (RSP), the panel's equal-weight universe runs **+1.6 to +3.1 pp/yr (CA) / +2.5 to +4.8 pp/yr (NONE)
   too high**. It also distorts selection effects: the momentum rules of SPMO/MTUM look 5-8 pp/yr worse
   relative to equal weight on the panel than the real funds did relative to RSP.
5. **An execution artifact.** The site's `TaxManagedCombo` buys targets in alphabetical order with the
   cash it has. When the gain budget blocks sells, the alphabetically first names get filled. In CA, 70-74%
   of a tax-managed 20-stock portfolio drifts into tickers starting with A-C (26% of the universe), and
   94-97% of it since 2015. That is why every finalist rides AAPL, AVGO, AMZN, AMD and AMAT.

**Bias-adjusted:** the RSP-calibrated universe bias (+1.6 to +3.1 pp/yr in CA) is about as large as the
finalists' whole edge over SPY (+2.8 to +4.1). What is left (roughly 0 to +2 pp/yr even for F2) rests on
a handful of stocks, one rebalance calendar and an uncertain correction, and cannot be told from zero.
The one mechanical effect that survives every control is a tax effect, not a picking skill. Over the same
stocks, the tax-managed rule beats standard execution by +0.65 pp/yr in CA (EW-PIT TM vs standard,
bootstrap p 0.004).

## 1. Setup

* **Universe:** the site's `sp500-pit` market: every stock with a price file, restricted each day to that
  day's S&P 500 members (constituents table from 1996). Coverage of the real index:

  | date | index members | trading in the data | share |
  |---|---|---|---|
  | 2000-01 | 491 | 182 | 37% |
  | 2005-01 | 495 | 214 | 43% |
  | 2010-01 | 499 | 270 | 54% |
  | 2015-01 | 499 | 307 | 62% |
  | 2020-01 | 505 | 392 | 78% |
  | 2025-01 | 503 | 470 | 93% |

* **Machinery:** (a) `stocks.combo`: the site's own `Combo` / `TaxManagedCombo` classes driven by a vectorized
  picker; (b) `stocks.weights`: the lab's `WeightStrategy` (standard or `tax` execution with **pro-rata**
  buys, optional loss harvesting into SPY); (c) the site's own `combo` kind for the random and
  equal-weight controls. Costs are 5 bps commission + 5 bps slippage per side. Tax-managed (TM) means
  losses are always sold, net gains are capped at 1% of the portfolio per year, with a 31-day wash guard.
* **Controls (mandatory):** the site's `RandomPicker` with identical machinery (10 seeds on the full
  protocol); **turnover-matched shadow random** (keeps as many of its names as the strategy keeps, so it
  trades as often but picks at random); **equal weight of the whole PIT universe** (EW-PIT, TM and
  standard); SPY. Calibration uses panel analogs of real funds (RSP, SPLV, SPHB, SPMO, MTUM, PDP, XLG,
  OEF) against the real funds over the same windows.
* **Sanity:** the module was patched four times (v1 to v4; each patch only adds opt-in parameters, and the
  patch scripts are in scratch). Two pickled v1/v1.1 configs re-run under v4 match exactly (0.0 difference
  over 1,440 checkpoints each; identical monthly series and run stats), so the stage 1-2 pickles stand.
  Look-ahead test: picks from the full market equal picks from markets clipped at the decision date for
  21 picker variants at 4 dates, with 0 mismatches. The long-history protocol does not apply: PIT
  membership starts in 1996, so no pre-2000 holdout exists for this family.

## 2. What was tested

**Totals: 280 distinct configs and 630 engine runs** (config x regime x protocol). 268 configs are heavy
(whole stock universe); 12 are real-fund buy-and-holds for calibration. Screen protocol: 256 configs /
495 runs (CA + NONE). Full protocol: 66 configs / 135 runs (CA, FED, NONE for finalists).

| role | configs |
|---|---|
| strategy configs (signals x machinery) | 81 |
| survivorship probes (loser-buying, to expose the bias) | 8 |
| control: random picker, identical machinery | 115 |
| control: turnover-matched shadow random | 27 |
| control: equal weight of the (sub)universe | 10 |
| calibration: panel analogs of real funds / real funds | 7 / 12 |
| hindsight and universe checks (stars removed, random halves, top-100 universe) | 8 |
| robustness and late starts (offsets, 1-day lag, `min_start` 2010 / 2015) | 12 |

Stages: **s1** (screen) 19 signals x 2 machineries + 22 controls; **s2** (screen) 3 momentum signals x 12
machineries, composites, weight-based tax execution, turnover-matched shadows, calibration analogs;
**s3** (full) finalists F1 / F2 / F3 with 10-seed random controls, shadows, FED, late starts, timing
offsets, lag, plus screen-protocol size and half-universe checks; **s3b** pro-rata execution on full and
the remove-the-stars check. An interrupted stage (s2b, 4 of 44 runs) was superseded by s3. The random
control has 10 seeds for the main machineries (quarterly TM and monthly standard on screen; quarterly
TM and semi-annual TM on full) and 5 seeds elsewhere.

**Signals covered** (`stocks.py`): momentum 12-1, 6-1, 12-0, 6-0; rank-blended 12/6/3-1; IBD-style
weighted 3/6/9/12-0; z-blended risk-adjusted 12/6-1; risk-adjusted 12-1; frog-in-the-pan; residual
momentum (Blitz-Huij-Martens); trend-filtered momentum (stock above its 200-day SMA; SPY 200-day timer;
SPY below its SMA -> AGG); the site's relative-strength picker; 52-week high; low volatility; low beta;
1-month reversal; same-month seasonality; size (dollar volume); composites (momentum + low vol, momentum +
reversal). Portfolio sizes 10 / 20 / 50 (100-125 for fund analogs); cadences M / Q / S / A; standard vs
tax-managed (gain budget 0 / 1 / 2 / 5%); weight-based tax execution with a short-term-gain ban, loss
harvesting into SPY, inverse-vol weights, a 2% band.

**Best screened configs** (CA, screen protocol; "vs random" = mean over 5/10/15-year windows against the
same-machinery random controls):

| config | CA score vs SPY | vs random | share of 10y windows ahead of random |
|---|---|---|---|
| 12-1 momentum, top 10, Q, TM 1% | +0.0436 | +1.45 | 0.47 |
| 6-1 momentum, top 20, S, TM 1% (F2) | +0.0431 | +1.15 | 0.59 |
| rank-blend 12/6/3-1, top 10, Q, TM 1% | +0.0403 | +1.11 | 0.59 |
| 1-month reversal, top 20, Q, TM 1% | +0.0382 | +0.43 | 0.35 |
| for reference: random 20, Q, TM 1% (10 seeds) | +0.0339 | 0 | |

**Representative failures** (CA, screen): 52-week high monthly standard -0.0458 vs SPY (-2.63 vs random,
ahead in 0% of 10y windows); risk-adjusted momentum monthly -0.0340; trend-filtered (200-day SMA)
momentum monthly -0.0324; frog-in-the-pan monthly -0.0319; 12-1 momentum with a SPY 200-day timer
monthly -0.0353; the 13 plain monthly-standard momentum variants -0.0108 to -0.0169. Low volatility (Q
TM) +0.0086 vs SPY but **-2.52 vs random**; low beta +0.0117 / -2.22; largest size +0.0010 / -3.29;
52-week high (Q TM) +0.0044 / -2.95.

## 3. How large is the survivorship bias?

**(a) Random picks clear the vs-SPY bar.** Full protocol, CA, 20 random stocks with the site's quarterly or
semi-annual TM machinery (`combo` kind, `RandomPicker` seeds 1-10):

| control (CA, full) | mean score | mean full_excess | ex10_beat | ex15_beat | boot_p | seeds passing criteria 1-3 |
|---|---|---|---|---|---|---|
| random 20, quarterly TM 1% | +0.0324 | +0.0576 | 0.90 | 0.95 | 0.030 | **9 / 10** |
| random 20, semi-annual TM 1% | +0.0311 | +0.0664 | 0.89 | 0.92 | 0.004 | **9 / 10** |
| EW-PIT (all members), quarterly TM 1% | +0.0314 | +0.0567 | 1.00 | 1.00 | 0.000 | (one config) passes |
| EW-PIT, quarterly standard | +0.0248 | +0.0298 | 0.87 | 0.89 | 0.016 | (one config) passes |

The real equal-weight S&P 500 fund **RSP** trails SPY in the same engine: CA ex5 -0.31 pp, ex10 -0.27 pp
(windows from 2004, screen protocol).

**(b) Calibration against survivorship-free funds** (screen protocol, identical windows from each fund's
first full year; "gap" = panel analog minus the real fund, mean over 5-year windows):

| real fund (first start) | panel analog | gap NONE | gap CA | panel selection effect (analog minus EW-PIT), NONE | real selection effect (fund minus RSP), NONE |
|---|---|---|---|---|---|
| RSP (2004) | EW-PIT, quarterly | **+3.05** | **+1.97** | | |
| SPLV (2012) | 100 lowest-vol, inv-vol weights | +1.48 | +0.34 | -3.20 | -1.61 |
| SPHB (2012) | 100 highest-beta, beta weights | +5.17 | +2.39 | +4.05 | +1.95 |
| SPMO (2016) | 100 best 12-1 risk-adj. momentum, S | -4.96 | -5.39 | -2.45 | **+5.27** |
| MTUM (2014) | 125 best 6/12-1 risk-adj. momentum, S | -2.51 | -3.10 | -3.03 | **+2.49** |
| PDP (2008) | 100 best 12-month momentum, Q | +0.01 | -1.22 | -3.46 | -0.58 |
| XLG (2006) | 50 largest (dollar volume) | +1.48 | +0.42 | -0.64 | +0.78 |
| OEF (2001) | 100 largest (dollar volume) | +2.27 | +1.18 | -1.16 | +0.43 |

(all in pp/yr). The equal-weight panel runs 1.6-3.1 pp/yr (CA) / 2.5-4.8 pp/yr (NONE) above RSP in every
start period. By 5-year start period, NONE: +4.78 (2001-04), +2.71 (2005-09), +3.26 (2010-14), +3.06
(2015-19), +2.47 (2020-23); CA: +3.11, +1.75, +2.18, +1.91, +1.57. The panel flatters high-risk and
past-loser selections (SPHB rule) and penalizes momentum selections. The SPMO/MTUM rules look 5-8 pp/yr
worse relative to equal weight on the panel than the real funds did relative to RSP. Part of that is
weighting (the real funds are cap-weighted in a mega-cap decade), but the direction is what survivorship
predicts. **So strategy-minus-random on this panel is itself biased: against "avoid the losers" signals
(momentum, 52-week high, low vol) and for "buy the losers" signals.** It is a sanity check, not a
measurement of real-world skill.

**(c) Survivorship probes** (not strategies; they exist to show the bias). Buying the names furthest
below their 52-week high, the 3-year losers, the most volatile or the smallest names beats random by
+4.2 pp/yr (CA) / +7.0 pp/yr (NONE) on average (8 probe configs, screen). Example: 52-week-high
*reversed*, quarterly TM: CA score **+0.0795**, ex10_beat 1.00, boot_p 0.000. In reality, buying the
deepest losers of the index has no such edge; here every loser in the data is one that survived.

**(d) The bias fades as coverage rises.** Mean excess vs SPY of 5-year windows by start period (full
protocol):

| start period | 2000-04 | 2005-09 | 2010-14 | 2015-19 | 2020-23 |
|---|---|---|---|---|---|
| data coverage at start | 37% | 43% | 54% | 62% | 78% |
| random 20, quarterly TM (10 seeds), CA | +7.63 | +2.31 | +2.20 | +0.71 | +0.03 |
| EW-PIT standard, CA | +6.31 | +3.47 | +2.02 | -0.07 | -1.09 |
| EW-PIT standard, NONE | +8.42 | +4.88 | +3.07 | +0.51 | -0.65 |

Even the 2020-23 windows are not bias-free: the panel's EW still beats RSP there by 1.6 (CA) to 2.5 (NONE) pp/yr.

## 4. Stock selection vs random (the key quantity)

**(a) The whole screened grid** (screen protocol, 24 yearly starts; each credible config against the
site's random picker with identical top_n / cadence / trade rule, 5-10 seeds; "vs random" = mean over
5/10/15-year windows of strategy CAGR minus the mean control CAGR):

| regime | credible configs | vs random: mean | median | share > 0 | best | worst | vs SPY: mean score | share > 0 |
|---|---|---|---|---|---|---|---|---|
| CA | 74 | **-0.43** | -0.39 | 38% | +1.45 | -3.29 | +0.78 | 59% |
| NONE | 74 | **-1.52** | -1.38 | 14% | +1.82 | -6.17 | +1.00 | 85% |

By signal (CA, vs random): 12-1/6-1/blended/risk-adjusted/FIP/trend-filtered momentum (56 configs) -0.29;
52-week high -2.79; low volatility -0.58; low beta -0.95; residual momentum -0.85; momentum+low-vol and
momentum+reversal composites -0.77; largest size -1.04; 1-month reversal +0.10; seasonality +0.62 (1
monthly config). By execution, the cells that are positive vs site random are monthly standard (+0.10,
24 configs) and semi-annual (+0.24 standard / +0.34 TM, 3 configs each; F2 is one of them). Every
quarterly or annual cell is negative (quarterly TM, 33 configs: -0.90). The monthly ones turn negative
against the **turnover-matched shadow** (-0.89, -0.37, -0.09 pp for three momentum configs). The site's
random picker reshuffles everything every rebalance, so it pays more tax than a persistent signal does.
The same confound makes monthly low-vol look +1.37 pp/yr better than site random (b10 0.94). Against its
shadow it is -1.30 pp/yr (b10 0.12).

**(b) Finalists, full protocol** (95 quarterly starts 2000-01 to 2023-07; vs SPY):

| config | regime | score | full_excess | ex5 | ex10 | ex10_beat | ex10_min | ex15_beat | ex20_beat | boot_p | max_dd (SPY) | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 12-1 mom, top 20, Q, TM 1% | CA | +0.0305 | +0.0677 | +0.0216 | +0.0400 | 0.72 | -0.0377 | 0.70 | 1.00 | 0.004 | -0.593 (-0.552) | 654 | 0.090 |
| | FED | +0.0329 | +0.0694 | +0.0245 | +0.0424 | 0.72 | -0.0425 | 0.72 | 1.00 | 0.006 | -0.592 | 654 | 0.094 |
| | NONE | +0.0012 | +0.0343 | +0.0112 | -0.0035 | 0.39 | -0.0418 | 0.49 | 0.63 | 0.152 | -0.558 | 3235 | 2.148 |
| F2 6-1 mom, top 20, S, TM 1% | CA | **+0.0414** | +0.0860 | +0.0330 | +0.0477 | 0.94 | -0.0091 | 1.00 | 1.00 | 0.000 | -0.606 | 493 | 0.082 |
| | FED | +0.0450 | +0.0877 | +0.0371 | +0.0517 | 0.94 | -0.0099 | 1.00 | 1.00 | 0.000 | -0.605 | 494 | 0.087 |
| | NONE | +0.0265 | +0.0672 | +0.0284 | +0.0252 | 0.93 | -0.0129 | 1.00 | 1.00 | 0.021 | -0.595 | 2009 | 1.849 |
| F3 EW-PIT, Q, TM 1% | CA | +0.0314 | +0.0567 | +0.0293 | +0.0316 | 1.00 | +0.0029 | 1.00 | 1.00 | 0.000 | -0.537 | 4953 | 0.021 |
| | FED | +0.0346 | +0.0585 | +0.0334 | +0.0349 | 1.00 | +0.0035 | 1.00 | 1.00 | 0.000 | -0.535 | 5081 | 0.022 |
| | NONE | +0.0384 | +0.0487 | +0.0393 | +0.0379 | 0.96 | -0.0031 | 1.00 | 1.00 | 0.001 | -0.541 | 33079 | 0.214 |
| random 20, Q TM (10 seeds, mean) | CA | +0.0324 | +0.0576 | +0.0296 | +0.0345 | 0.90 | -0.0254 | 0.95 | 0.97 | 0.030 | -0.575 | 735 | 0.130 |
| | NONE | +0.0288 | +0.0389 | +0.0302 | +0.0279 | 0.81 | -0.0398 | 0.89 | 0.90 | 0.050 | -0.555 | 4108 | 3.834 |
| random 20, S TM (10 seeds CA / 5 NONE) | CA | +0.0311 | +0.0664 | +0.0276 | +0.0339 | 0.89 | -0.0231 | 0.92 | 0.94 | 0.004 | -0.577 | 408 | 0.084 |
| | NONE | +0.0302 | +0.0350 | +0.0321 | +0.0283 | 0.83 | -0.0334 | 0.91 | 0.97 | 0.050 | -0.573 | 2065 | 1.960 |

(Note: in NONE the tax-managed rule has no gains to ration, so "TM" behaves like a plain quarterly or
semi-annual full rebalance.)

**(c) Strategy minus control, full protocol** (paired windows; "d" = mean over 5/10/15-year windows;
"b10" = share of 10-year windows ahead of the control mean; "rank10" = average share of control seeds
beaten in 10-year windows; restricting to starts >= 2010 / >= 2015 uses exactly the same windows as a
`min_start` run):

| strategy | control | regime | d, all starts | b10 | rank10 | d, starts >= 2010 | d, starts >= 2015 |
|---|---|---|---|---|---|---|---|
| F1 | random 20 Q TM (10 seeds) | CA | **-0.19** | 0.46 | 0.46 | +1.79 | +5.51 |
| F1 | random 20 Q TM (5 seeds) | FED | -0.24 | 0.48 | 0.46 | +1.68 | +5.45 |
| F1 | random 20 Q TM (10 seeds) | NONE | **-2.77** | 0.19 | 0.20 | +0.87 | +3.46 |
| F1 | shadow random (5 / 3 seeds) | CA / NONE | +0.21 / -3.09 | 0.51 / 0.15 | 0.52 / 0.16 | +2.01 / +0.26 | +6.35 / +3.44 |
| F1 | EW-PIT TM | CA / NONE | -0.09 / -3.72 | 0.52 / 0.15 | | +1.60 / -0.19 | +6.55 / +2.56 |
| F2 | random 20 S TM (10 seeds) | CA | **+1.02** | 0.58 | 0.55 | +2.84 | +5.08 |
| F2 | random 20 S TM (5 seeds) | NONE | **-0.37** | 0.34 | 0.41 | +1.18 | +1.44 |
| F2 | shadow random (5 / 3 seeds) | CA / NONE | +1.43 / -0.39 | 0.57 / 0.33 | 0.57 / 0.39 | +2.52 / +0.42 | +5.68 / +1.18 |
| F2 | EW-PIT TM | CA / FED / NONE | +1.00 / +1.03 / -1.19 | 0.58 / 0.58 / 0.15 | | +2.11 / +2.20 / +0.19 | +6.06 / +6.40 / +0.62 |
| F3 EW-PIT TM | random 20 Q TM | CA / FED / NONE | -0.10 / -0.07 / +0.96 | 0.49 / 0.49 / 0.94 | | | |
| F3 EW-PIT TM | EW-PIT standard | CA / FED / NONE | +0.65 / +0.46 / +0.11 | 0.85 / 0.70 / 0.96 | | +1.52 / +1.30 / +0.15 | +1.13 / +1.01 / +0.21 |

Stationary bootstrap of the monthly after-tax log excess over the control mean (2000-start run):
F1 vs random +0.95 pp/yr (p 0.28, CA), -0.39 (p 0.56, NONE); F2 vs random +1.67 (p 0.14, CA), +2.76 (p 0.21,
NONE); F1 vs shadow +1.57 (p 0.23, CA); F2 vs shadow +5.46 (p 0.006, CA); F3 vs EW standard +2.40 (p 0.004,
CA). The one "significant" strategy number, F2 vs shadow, comes from a single path: the 2000-start run that
bought AAPL on 2000-01-03 and, under the gain budget, never sold it (section 6). A monthly bootstrap cannot
see that the whole series hangs on one position. The window-averaged difference against the same
controls is +1.43 pp/yr, ahead in 57% of 10-year windows.

**(d) By start period** (5-year windows; strategy minus control mean):

| | 2000-04 | 2005-09 | 2010-14 | 2015-19 | 2020-23 |
|---|---|---|---|---|---|
| F1 - random, CA | +0.96 | **-6.16** | -0.66 | +1.80 | +1.70 |
| F1 - random, NONE | -0.23 | **-9.41** | -1.92 | -0.58 | **+11.03** |
| F2 - random, CA | +2.37 | -2.58 | +0.32 | +1.57 | +1.93 |
| F2 - random, NONE | -1.62 | -1.97 | +1.00 | -0.04 | +2.92 |

The "late-start advantage" is one episode. In NONE, F1 is behind random in every start period except
2020-23 (the 2020-2026 semiconductor / AI run). Calendar years of the 2000-start runs (CA) show the same
thing. F2 minus random averages +3.6 pp/yr, but 2009 (+18.8), 2019 (+16.1), 2020 (+31.2) and 2023 (+19.0)
carry it, and 2010-14 is -0.4 pp/yr. Momentum's 2001-09 crashes against its 2019-24 boom is a regime bet,
not a dependable edge, and the panel cannot price the first half of it honestly (section 3b).

## 5. The alphabetical-buy artifact

`backtester/composite.py::TaxManagedCombo.on_day` places its buys `for t in sorted(longs)`, and the engine
caps every buy at the cash on hand (`engine.place_order`). With a 1% gain budget, winners that leave the
target list or grow overweight usually cannot be sold, so the cash for new targets is short. The
alphabetically first targets are filled and the later ones are not. Each rebalance therefore tilts toward
A-C tickers, and the TM rule then freezes whatever grew. One engine run per config from 2000-01-01;
month-end value weights of the stock holdings:

| config | regime | A-C share of $ (avg) | A-C share since 2015 | $-weighted alphabet rank (0 = A, 1 = Z) | effective names (avg) | top-1 weight (avg) | holdings at 2026-07 |
|---|---|---|---|---|---|---|---|
| universe (count share) | | 26% | | 0.50 | | | |
| F1, site TM (alphabetical buys) | CA | **70%** | **97%** | 0.20 | 8.7 | 37% | AAPL 64%, AVGO 15%, AMZN 11%, AZO 4%, ALB 4% |
| random seed 1, site TM | CA | **74%** | **94%** | 0.21 | 12.5 | 16% | AAPL 39%, AMZN 16%, ABBV 10%, ADSK 10%, A 7% |
| EW-PIT, site TM | CA | 42% | 51% | 0.39 | 89.8 | 10% | NVDA 21%, AAPL 20%, AMZN 4% |
| F1, site TM | NONE | 28% | 27% | 0.49 | 19.7 | 6% | STX, WDC, FIX, GLW, LRCX, MU 5% each |
| F1, lab `tax` execution (pro-rata buys) | CA | 34% | 47% | 0.42 | 15.9 | 15% | NVDA 23%, AAPL 23%, AMZN 8%, AVGO 6% |
| random seed 1, lab `tax` execution | CA | 30% | 28% | 0.47 | 24.6 | 11% | NVDA 35%, ADSK 5%, MAR 5% |

The tilt appears only when the gain budget binds (CA, FED). In NONE nothing is rationed and F1 is
alphabet-neutral. The random controls with the same machinery carry the same tilt, so strategy minus
random stays like for like. The absolute "vs SPY" numbers of every site-TM stock portfolio, though, are
partly a lottery on which A-C names happened to be survivors and mega-winners (AAPL, AMZN, AVGO, AMD,
AMAT, ADBE, ABBV...). The lab's pro-rata `tax` execution (`stocks.weights`) removes most of the tilt.
Same rule on the screen protocol, CA: F1 site-TM score +0.0295 vs pro-rata +0.0260; random site-TM
+0.0339 (10 seeds) vs pro-rata +0.0292 (5 seeds). So the alphabet lottery is worth about +0.4 to +0.5
pp/yr in this panel. Strategy minus random is about 0 either way (pro-rata 12-1 momentum vs pro-rata
random, screen: +0.34 pp in 10-year windows, -0.32 pp averaged over 5/10/15-year windows).

**Full protocol, pro-rata execution** (`stocks.weights`, execution `tax`, gain budget 1%; W1 = 12-1
momentum top 20 quarterly, controls = pro-rata random 20, 5 seeds CA / 3 NONE):

| config | regime | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd |
|---|---|---|---|---|---|---|---|---|
| W1 | CA | +0.0276 | +0.0382 | 0.84 | -0.0241 | 1.00 | 0.015 | -0.604 |
| W1 | FED | +0.0301 | +0.0391 | 0.84 | -0.0270 | 1.00 | 0.023 | -0.604 |
| W1 | NONE | +0.0011 | +0.0343 | 0.39 | -0.0418 | 0.49 | 0.152 | -0.558 |
| pro-rata random (5 seeds) | CA | +0.0285 | +0.0527 | 0.89 | -0.0209 | 0.92 | 0.003 | -0.591 |
| pro-rata random (3 seeds) | NONE | +0.0295 | +0.0363 | 0.78 | -0.0390 | 0.89 | 0.051 | -0.573 |

W1 minus pro-rata random: **-0.09 pp/yr in CA** (all windows; ahead in 37% of 10-year windows; bootstrap
of the monthly excess -1.28 pp/yr, p 0.72), +2.00 for starts >= 2010, +4.22 for starts >= 2015; NONE
-2.83 / +1.06 / +3.75. All 5 pro-rata random seeds pass criteria 1-3 vs SPY in CA. Removing the
alphabet artifact lowers everyone's level a little and leaves the conclusion unchanged.

This is the site's own behaviour, reproduced exactly, so it is not a lab bug. It is a design flaw worth
fixing on the site, though: scale all buys pro rata to the available cash, or fill them in signal-rank
order. It matters most for large universes. The incumbent ETF preset buys in alphabetical order too.

## 6. Hindsight checks

**(a) Where the money came from** (`scratch/stocks/stars.py`; one CA run, P&L by ticker = sells - buys +
value held at 2026-07):

| run | top contributors (share of total P&L) | top 5 | top 10 |
|---|---|---|---|
| F1 from 2000-01 | AAPL 64.5%, AVGO 15.3%, AMZN 10.4%, AZO 3.5%, BKNG 3.0% | 96.8% | 101.7% |
| F1 from 2010-01 | AMD 28.2%, AVGO 22.6%, AMAT 16.8%, MA 7.3%, AZO 4.1% | 79.1% | 95.3% |
| F2 from 2000-01 | AAPL 68.8%, AMD 18.3%, AMZN 7.2%, CBRE 1.9%, BKNG 1.4% | 97.6% | 100.0% |

F2 bought AAPL on 2000-01-03 and held it to the end (3 trades). Both strategies' results are a handful of
survivor mega-winners frozen by the gain budget, and almost all of them sort early in the alphabet
(section 5).

**(b) Remove the stars** (screen protocol, CA). The 9 names above (AAPL, AVGO, AMZN, AMD, AMAT, AZO, BKNG,
MA, CBRE) are removed from the universe of the strategy **and** of its controls:

| config (CA, screen) | vs SPY score | full_excess | ex10_beat | boot_p | minus random (same universe) | ... starts >= 2010 | ... starts >= 2015 |
|---|---|---|---|---|---|---|---|
| F1 12-1 mom Q TM, with stars | +0.0295 | +0.0677 | 0.65 | 0.004 | -0.33 (5 seeds) | +1.00 | +7.16 |
| F1, **stars removed** | **+0.0018** | -0.0137 | 0.41 | 0.770 | **-1.90** | -0.61 | +5.53 |
| F2 6-1 mom S TM, with stars | +0.0431 | +0.0860 | 0.94 | 0.000 | +1.03 (quarterly random) / +1.15 (semi-annual) | +2.97 | +6.85 |
| F2, **stars removed** | **+0.0116** | +0.0188 | 0.65 | 0.176 | **-0.92** (quarterly random) | -1.06 | +1.92 |
| W1 pro-rata 12-1 mom, with stars | +0.0260 | +0.0382 | 0.82 | 0.015 | 0.00 (2 seeds) | +2.53 | +6.39 |
| W1, **stars removed** | +0.0121 | +0.0217 | 0.65 | 0.091 | **-0.88** | +1.04 | +3.32 |
| EW-PIT TM, stars removed | +0.0277 (vs +0.0321 with) | +0.0494 | 1.00 | 0.000 | | | |
| random 20 Q TM, stars removed (5 seeds) | +0.0208 (vs +0.0328 with) | | | | | | |

Nine names out of about 500 carry the momentum results. Without them, F2 no longer passes the vs-SPY
criteria (ex10_beat 0.65, boot_p 0.18), every momentum variant trails random over all windows, and F1 is
level with SPY. The equal-weight universe loses only 0.4 pp/yr, so the stars matter to the strategies
because the strategies concentrated in them, not because the universe depends on them. The random
TM portfolios lose 1.2 pp/yr: they froze AAPL/AMZN too (alphabet artifact). Criterion 6 fails. (F2's
stars-removed control is the quarterly random picker; with the stars, quarterly vs semi-annual controls
differ by only 0.1 pp/yr for F2.)

**(c) Random half-universes** (the stock analog of PROTOCOL 5.3's random menus; screen protocol, CA). A
fixed pseudo-random 50% of tickers (`subset_frac` 0.5, seeds 1-4); 12-1 momentum quarterly TM against
random picks (2 seeds) and the equal weight of the same half:

| half | momentum vs SPY (score) | EW of the half vs SPY | momentum - random | momentum - EW of half |
|---|---|---|---|---|
| 1 | +0.0365 | +0.0405 | -0.60 | -0.40 |
| 2 | +0.0220 | +0.0322 | -1.23 | -1.02 |
| 3 | +0.0257 | +0.0329 | -0.82 | -0.72 |
| 4 | +0.0357 | +0.0363 | +0.29 | -0.06 |
| full universe (10 random seeds) | +0.0295 | +0.0321 (EW-PIT TM) | -0.44 | -0.26 |

Every half "beats SPY" by 2-4 pp/yr. Momentum trails the plain equal weight of its own half in all four.

**(d) A lower-bias universe: the 100 largest names by 63-day dollar volume** (`size_top` 100; large
companies were far less likely to vanish; screen protocol, 5 random seeds):

| regime | momentum (top-100) vs SPY | b10 | EW top-100 vs SPY | momentum - random | momentum - EW |
|---|---|---|---|---|---|
| CA | +0.0342 | 1.00 | +0.0233 | +0.89 (b10 0.71) | +1.09 |
| NONE | +0.0217 | 0.88 | +0.0227 | +0.66 | -0.11 |

Momentum is a little better than random among the largest names (+0.7 to +0.9 pp/yr, 5 seeds, screen
only). That is the most favourable selection result in the family, and it is small, not tested on the
full protocol, and still inside a biased panel. The panel's top-100-by-volume analog of OEF runs +1.2 pp/yr
(CA) / +2.3 pp/yr (NONE) above the real OEF.

## 7. Robustness and late starts

**(a) Late starts** (cfg `min_start`; full protocol, vs SPY; coverage 54% at 2010, 62% at 2015).
Note: the `bench_max_dd` the lab reports for these records is SPY's 2000-2026 drawdown (-0.552), not the
drawdown since the late start (see lab issues):

| config | from | regime | score | full_excess | ex5 | ex10 | ex10_beat | ex10_min | boot_p | max_dd | strategy - random (same windows) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | 2010 | CA | +0.0336 | +0.0258 | +0.0198 | +0.0598 | 0.96 | -0.0012 | 0.100 | -0.373 | +1.79 |
| F1 | 2010 | NONE | +0.0120 | +0.0423 | +0.0119 | +0.0065 | 0.63 | -0.0242 | 0.120 | -0.357 | +0.87 |
| F1 | 2015 | CA | +0.0707 | +0.1426 | +0.0231 | +0.1182 | 1.00 (7) | +0.0545 | 0.002 | -0.498 | +5.51 |
| F1 | 2015 | NONE | +0.0280 | +0.0680 | +0.0206 | +0.0354 | 1.00 (7) | +0.0231 | 0.076 | -0.357 | +3.46 |
| F2 | 2010 | CA | +0.0387 | +0.0612 | +0.0182 | +0.0533 | 1.00 | +0.0099 | 0.001 | -0.333 | +2.84 |
| F2 | 2010 | NONE | +0.0158 | +0.0631 | +0.0161 | +0.0132 | 0.81 | -0.0129 | 0.071 | -0.346 | +1.18 |
| F2 | 2015 | CA | +0.0658 | +0.1397 | +0.0166 | +0.1150 | 1.00 (7) | +0.0932 | 0.002 | -0.500 | +5.08 |
| F2 | 2015 | NONE | +0.0085 | +0.0733 | +0.0044 | +0.0127 | 0.43 (7) | -0.0129 | 0.140 | -0.346 | +1.44 |
| F3 EW-PIT TM | 2010 | CA | +0.0176 | +0.0220 | +0.0112 | +0.0173 | 1.00 | +0.0029 | 0.000 | -0.360 | +0.19 |
| F3 EW-PIT TM | 2010 | NONE | +0.0139 | +0.0134 | +0.0158 | +0.0145 | 0.89 | -0.0031 | 0.120 | -0.378 | +1.06 |
| F3 EW-PIT TM | 2015 | CA | +0.0052 | +0.0155 | +0.0016 | +0.0088 | 1.00 (7) | +0.0029 | 0.023 | -0.371 | -1.04 |
| F3 EW-PIT TM | 2015 | NONE | +0.0024 | +0.0013 | +0.0043 | +0.0004 | 0.57 (7) | -0.0031 | 0.469 | -0.378 | +0.90 |

Starting 2015, momentum looks excellent in CA (+7 pp/yr, ahead of 10 random seeds in every 10-year window).
But 2015+ has only 7 ten-year windows, all sharing 2016-2025. The 5-year windows by start period
(section 4d) show the edge sits in the 2020-23 starts, i.e. the 2020-2026 semiconductor/AI run (AMD,
AVGO, AMAT, NVDA-era momentum). The equal-weight universe's own edge over SPY fades to about zero for
2015+ starts, as the panel's coverage rises and mega-caps lead the index.

**(b) Rebalance-timing luck and a one-day execution lag** (CA, full protocol, vs SPY; `offset_days`
shifts every rebalance boundary, `lag` 1 decides on the previous close):

| config | variant | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd | passes 1-3 vs SPY |
|---|---|---|---|---|---|---|---|---|---|
| F1 (Q) | offset 0 d | +0.0305 | +0.0677 | 0.72 | -0.0377 | 0.70 | 0.004 | -0.593 | no |
| | offset 23 d | +0.0285 | +0.0755 | 0.81 | -0.0206 | 0.94 | 0.000 | -0.583 | yes |
| | offset 46 d | +0.0294 | +0.0616 | 0.84 | -0.0200 | 0.91 | 0.000 | -0.580 | yes |
| | offset 69 d | +0.0258 | +0.0765 | 0.79 | -0.0262 | 0.81 | 0.000 | -0.576 | no |
| | lag 1 d | +0.0305 | +0.0706 | 0.72 | -0.0327 | 0.74 | 0.000 | -0.617 | no |
| F2 (S) | offset 0 d | +0.0414 | +0.0860 | 0.94 | -0.0091 | 1.00 | 0.000 | -0.606 | yes |
| | offset 46 d | +0.0463 | +0.0916 | 0.99 | -0.0023 | 1.00 | 0.000 | -0.562 | yes |
| | offset 91 d | +0.0293 | +0.0795 | **0.69** | -0.0370 | **0.62** | 0.000 | -0.594 | **no** |
| | offset 137 d | +0.0433 | +0.0875 | 0.91 | -0.0130 | 1.00 | 0.000 | -0.622 | yes |
| | lag 1 d | +0.0369 | +0.0941 | 0.93 | -0.0036 | 0.98 | 0.000 | -0.576 | yes |

Every timing variant stays well ahead of SPY, but so does random stock picking (section 3a); vs SPY is
not the informative comparison here. F2's beat rates depend on which months it rebalances: rebalancing
in April/October instead of January/July (offset 91 d) drops it to ex10_beat 0.69 / ex15_beat 0.62.

## 8. Family diagnostics

`report.diagnostics` on the screened grid (screen protocol, s1 + s2: 96 strategy configs, or 85 after
dropping the 11 bias probes / reversal configs). Plus a control-relative walk-forward: at each date pick
the config with the best trailing excess **over its own random control**, then score its next 5 (or 3)
years against that control (72 config-control pairs). Saved in
`scratch/stocks/diag_s1_screen_s2_screen.json`.

| | CA, all 96 | CA, credible 85 | NONE, all 96 | NONE, credible 85 |
|---|---|---|---|---|
| walk-forward 10y -> 5y: OOS mean excess vs SPY | +5.68 | **-0.02** | +8.09 | **-3.30** |
| ... OOS beat rate / average config OOS | 1.00 / +0.07 | 0.33 / -0.31 | 0.67 / +1.24 | 0.33 / +0.54 |
| walk-forward 5y -> 3y: OOS mean | +8.94 | +0.18 | +0.81 | -1.89 |
| PBO (CSCV) | 0.02 | 0.02 | 0.35 | **0.60** |
| deflated Sharpe of best config (DSR) | 0.63 | 0.63 | 0.69 | 0.55 |
| walk-forward vs own random control, 10y -> 5y | | +1.63 (beat 0.67) | | -1.10 (beat 0.25) |
| walk-forward vs own random control, 5y -> 3y | | **-0.92** (beat 0.47) | | -1.09 (beat 0.47) |

The "all configs" walk-forward is a warning in itself. It reliably picks the loser-buying probes and
"earns" +5.7 pp/yr out of sample with a PBO of 0.02, because the bias is present in every window and
the diagnostics cannot see it. Among credible configs, walk-forward selection vs SPY earns about 0 in
CA and -3.3 pp/yr in NONE. Against each config's own random control it is +1.6 or -0.9 pp/yr depending on
the window lengths, so it is not positive out of sample. Criterion 4 of the bar fails. The low CA PBO
(0.02) only says that configs which do well vs SPY keep doing well. That describes persistent exposure
to the panel's bias and the frozen-winner TM machinery, not selection skill.

## 9. Conclusion

* **What the panel says vs SPY:** almost every tax-managed stock portfolio, random ones included, beats
  SPY in CA by 2.5-4.5 pp/yr. That is a property of the data, not of any rule. 9/10 random portfolios pass
  criteria 1-3 of the bar.
* **What selection adds:** across the grid, about 0 to slightly negative vs random with identical
  machinery (CA -0.43, NONE -1.52 pp/yr on average). For the finalists: F1 (12-1, quarterly, the site
  preset's rule on stocks) -0.19 CA / -2.77 NONE; F2 (6-1, semi-annual) +1.02 CA (p 0.14) / -0.37 NONE.
  It also depends on period: momentum lost badly to random for 2005-09 starts and won for 2020-23 starts.
* **Bias adjustment:** the universe-level bias calibrated on RSP (+1.6 to +3.1 pp/yr in CA, +2.5 to +4.8
  in NONE) is as large as the finalists' entire edge over SPY. Subtracting it leaves roughly 0 to +2 pp/yr
  for the best config (F2) and about 0 to +1 for the others. That residual rests on three stocks (AAPL,
  AMD, AMZN), on one rebalance calendar (it fails at the 91-day offset), on an alphabetical execution
  artifact, and on a bias correction that is itself uncertain by a point or more. It is not
  distinguishable from zero.
* **Confidence bar** (PROTOCOL section 3), in CA: F2 passes 1-3 vs SPY but fails 4 (walk-forward vs
  control not positive out of sample), 5 (its neighbourhood: F1, 12-1 momentum, fails 2; the 91-day
  offset fails 2), 6 (star dependence, section 6) and the survivorship rule (results are upper bounds; the
  random control passes too). F1 fails 2 and 4-6. F3 (EW-PIT TM) passes 1-3 but *is* the universe control:
  its excess is the survivorship bias plus the TM rule's tax deferral (+0.65 pp/yr over the same universe
  traded with standard execution). Criterion 7 cannot be checked (no pre-2000 PIT holdout).
* **Recommendation for the user:** do not adopt an individual-stock strategy on the strength of these
  backtests. If stock momentum is of interest, the survivorship-free evidence is the real funds
  (SPMO/MTUM/PDP, the factor and ETF families): SPMO beat SPY after CA tax by about 2.2 pp/yr in 5-year
  windows since 2016, one regime only; MTUM was about even since 2014; PDP about -1.1 pp/yr since 2008.
  The one robust mechanical lesson here is the tax-managed execution: rationing realized gains and
  harvesting losses is worth about +0.65 pp/yr in CA over the same stocks managed without it (EW-PIT TM
  vs standard, b10 0.85, bootstrap p 0.004). That is a tax effect, it does not depend on picking skill,
  and in reality it applies to whatever one holds.
* **What would change this:** a survivorship-free price history with delisted stocks (CRSP, Norgate,
  Sharadar). With it, the same code (`stocks.combo` / `stocks.weights` plus the random and shadow
  controls) could measure selection honestly.

## 10. Lab and site issues found

* **Alphabetical buy order in `TaxManagedCombo`** (site class, reproduced exactly by the lab). Buys go
  in `sorted(ticker)` order and are capped by cash, so under a binding gain budget the portfolio drifts
  into A-C tickers (section 5). A design flaw rather than a lab bug, but it moves every site-TM stock
  result by about 0.4-0.5 pp/yr and concentrates portfolios (8.7 effective names out of a target of 20).
  It can also touch small-menu ETF presets whenever cash is short.
* **`metrics.summary` benchmark stats for late-start records:** `bench_max_dd` / `bench_sharpe` come from
  the benchmark's run from the protocol's first start (2000), even when the record starts later
  (`min_start`). The window excesses and the bootstrap correctly use the record's own start.
* **Cache invalidation by module hash:** any edit to a family file, even adding an opt-in parameter,
  re-keys every config of that family. The previous researcher's three patches left 256 cached stock runs
  unreachable under the current code. Their pickled results were kept and verified to be reproduced
  exactly by v4.
* In NONE (no tax policy) the TM rule cannot see lots, so it rebalances fully. That is consistent with
  "no tax, nothing to manage", but it means TM and standard execution coincide in NONE (the `ZERO` regime
  in `families/variants.py` exists for tax-aware rules in an IRA).

## 11. Not tested (ideas)

* A survivorship-free stock panel (with delisted names) is the precondition for any honest
  stock-selection test. Everything here would be worth re-running on one.
* Cap-weighted stock portfolios (true direct indexing with loss harvesting against SPY): the site has no
  point-in-time market caps. The equal-weight TM result (+0.65 pp/yr over standard execution) hints at the
  tax alpha. In reality, harvesting would have far more losers to work with (the bankrupt names missing
  here).
* Pro-rata or rank-priority buys in the site's `TaxManagedCombo` (a site change), then re-test the ETF
  presets.
* The top-100 (large-cap) momentum result (+0.7 to +0.9 pp/yr vs random, screen only) on the full
  protocol with 10 seeds and the remove-the-stars check. It is the most favourable selection cell but
  small, and the large-cap panel is still biased (+1.2 to +2.3 pp/yr vs the real OEF).
* 12-1 momentum with top 10 (best screened config vs random, +1.45 pp/yr) on the full protocol. Not
  promoted: it is more concentrated than F1/F2, so it is likely even more dependent on stars.

