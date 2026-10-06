# r2_gap3: crash protection that never sells the core

Round 2, critic gap 3: index put spreads, collars (SPX options, Section 1256) and a long-volatility sleeve, laid over an S&P 500 core that is bought once and not sold. Primary regime CA (48.1% short-term / 28.1% long-term), secondary FED (35/15), pre-tax NONE as a diagnostic. Every after-tax number comes from the lab's engine (`backtester.Backtest`, extended with an options book, see section 1), scored with the lab's own `metrics.summary` / `report.score` against the lab's own SPY (VFINXR on 1986+) benchmark. "Score" is the pre-registered mean of the average 5-, 10- and 15-year window excess; all excess numbers are after-tax CAGR minus the benchmark's, in percentage points per year.

## Verdict

**No option overlay beats buying and holding SPY after California tax, with or without confidence. Every structure that actually stays hedged loses 0.4 to 3.6 pp/yr; the verdict holds for 2000-2026 and 1986-2026, for actual CBOE index prices and for my calibrated option model, and for every tax treatment I tried. None of the 104 configurations passes bar items 1-3 in CA in either history on the lab's first-start bootstrap.**

One leverage comparator passes items 1-3 on 2000-2026 only when the bootstrap p is averaged over start dates. That is +0.5x long S&P futures with no options: start-averaged p 0.069, first-start p 0.28. It fails item 2 on 1986-2026 (15-year beat 80%), its drawdown is -71% to -73%, and it is leverage, not crash protection; section 8 covers it.

* **It is the price of insurance, not the tax.** Before any tax, CBOE's own strategy indices (traded prices, 1986-2026) trail the S&P 500 total return by 3.2 pp/yr (PPUT, monthly 5% puts), 2.4 (PPUT3M, quarterly 10% puts), 3.1 (CLLZ, zero-cost put-spread collar), 4.5 (CLL3M, 95/110 collar) and 1.3 (VXTH, VIX calls, 2006-2026). PPUT beat the index in 2.5% of 10-year windows. Puts are priced above their average payoff, the variance risk premium.
* **Section 1256 hardly changes that.** For the active overlays the CA score is only 0.0-0.65 pp better than the pre-tax score. The overlay's yearly losses mostly offset the long-term gains realised when core shares are sold to pay premiums. The rest offsets the terminal liquidation at 28.1%. The realistic law for an S&P 500 fund hedged with S&P 500 options or futures is the straddle rules, which make it worse (section 5).
* **Drawdowns do fall**, from SPY's -55% to between -30% and -49%. But a never-rebalanced SPY/Treasury mix buys the same drawdown far more cheaply:
  * a 70/30 SPY/VFITX mix gets -29% at -1.06 pp/yr, where the 95/110 collar gets -30% at -3.59;
  * an 80/20 mix gets -37% at -0.68, where the 95/80 put spread gets -38% at -2.21.
* **Only three kinds of overlay have a positive CA score, and each fails the bar:**
  1. Hedges switched on by the round-1 EMA100/200 trend signal. These are a collar (+0.49), puts (+0.07), short futures (+0.59), and a synthetic SPY-to-IEF switch with futures (+0.99). They inherit that rule's weaknesses:
     * 10-year beat rate 52-57%;
     * bootstrap p averaged over start dates 0.77-0.82;
     * 1986-1999 holdout 10-year windows 0% beaten.
  2. VIX calls only while VIX < 20: +1.01 (+1.41 when scored from 2006). This rule was chosen after I saw pre-tax data. Its edge is one trade (February-March 2020), VXTH without 2020 trails by 4.4 pp/yr, the VIX < 25 neighbour scores -0.02, p is 0.40-0.53, and there is a 52-58% chance of trailing SPY over 10 years.
  3. Long S&P futures on top of the core, with or without put spreads. **This is flagged as leverage.** Scores are +1.1 to +2.7, but p is 0.28-0.55 on the first start and drawdowns are -56% to -86%. The put spreads do not bring the drawdown back to SPY's.
* **The critic's mechanism does not hold for the best timing rule.** I implemented the round-1 EMA100/200 SPY-to-IEF switch with Section 1256 futures instead of sales: short S&P futures plus long Treasury futures, with the core never sold. Its CA score is +0.99, against +1.01 for the version that sells the core. The 2000-start path gains (+1.75 vs +1.36 full excess), but averaged over windows nothing is saved, for three reasons:
  * the hedge's own gains are taxed every year at the 36.1% 60/40 blend;
  * losing hedges force sales of the appreciated core to meet variation margin, for example $191k of long-term gains realised in 2022-23 on the 2000 start;
  * a full futures hedge of an S&P fund probably is a constructive sale, which costs a further 0.09.

The default for the taxable account stays SPY buy-and-hold. For someone who wants a smaller drawdown, a static allocation to Treasuries is three to five times cheaper per point of drawdown than a full option hedge in this data. That holds even after paying a one-time 28.1% tax on the long-term gain realised to fund it (section 6).

## 1. What I built and how it was checked

**Data** (research-only, new files `research/lab/data/R2G3_*.csv`):
* 15 CBOE strategy and volatility index histories downloaded from Cboe's own index CDN. Yahoo carries only `^PUT` and `^SKEW` history; `^PPUT`, `^CLL` and `^BXM` return only today's value there. The series are PPUT, PPUT3M, CLL, CLL3M, CLL1M, CLLZ, VXTH, BXM, BXY, BXMD, PUT, CNDR, SKEW, VVIX and SPRO.
* The methodology PDFs are in `scratch/r2_gap3/docs/`.
* Lab data used: ^GSPC, ^VIX, ^VIX3M, ^IRX, ^SP500TR, VFINXR, SPY, IEF/VFITX/FGOVX.

**Option model** (`families/r2_gap3.py`):
* Black-Scholes on the forward. The ATM vol is `a x VIX` interpolated to VIX3M by maturity, with a smile in standardised moneyness (slope `b`, curvatures `cp`/`cc`).
* The ATM ratio and the slope move with the CBOE SKEW index.
* Trades pay a half-spread (`h_rel` x premium + 0.5 bp of the index).
* 5-point strikes. Expiry at the SOQ (^GSPC open, or SPY's overnight gap where ^GSPC opens are stale), third-Friday rolls, new options opened at the roll day's close.
* Trade prices use that day's VIX, because that is the market price at the trade. A lagged VIX would under-price puts bought right after a down day, which favours the strategy.
* Every decision uses only data up to that close (trend rules, the lab convention) or the previous close (VIX conditions).

**Calibration** (`scratch/r2_gap3/calib2.py`): 8 parameters fitted to 10 CBOE indices (puts bought, calls sold, put writes, collars, an iron condor), on both halves of the VIX era at once.

| index (what it trades) | bias 1990-2007 | bias 2008-2026 | tracking error | corr |
|---|---|---|---|---|
| PPUT (5% put bought) | -0.18 | -0.48 | 1.1-1.6%/yr | 0.993-0.996 |
| PPUT3M (10% 3M put bought) | +0.27 | -0.02 | 0.3-0.7% | 0.999 |
| BXM / BXY / BXMD (calls sold) | -0.10 / +0.16 / -0.22 | -0.28 / +0.40 / +0.46 | 1.7-2.8% | 0.96-0.99 |
| CLL3M / CLL1M (collars) | -0.18 / -0.26 | -0.45 / -0.65 | 1.2-2.7% | 0.90-0.99 |
| CLLZ (put-spread collar) | +1.00 | +0.56 | 1.7-2.1% | 0.99 |
| PUT (ATM put write) / CNDR (condor) | n/a / -0.02 | -1.16 / +0.52 | 2.5-3.0% | 0.90-0.98 |

Bias is the replica's CAGR minus the index's, in pp/yr.

* The model is therefore conservative for bought puts: its puts are slightly too dear.
* It is about 0.5-1 pp/yr generous to the CLLZ-type collar.
* A fit on 1990-2007 alone, checked on 2008-2026, was off by +1.3-1.6 pp on call writing, because the smile steepened after 2008. The SKEW term in the final model absorbs that.
* For 1986-1989 there is no VIX. A realised-volatility proxy reproduces PPUT to +0.1 pp/yr outside September-December 1987. Over the whole period it is -2.45, because CBOE bought its put at midday on 16 October 1987 and the replica at that day's close, after a 5% fall.
* An attempt to back an implied level out of the indices (`imp8689.py`) did not improve matters and was dropped.

**Engine** (`OptBacktest`, a subclass of `backtester.Backtest`, following r2_gap1's FutBacktest):
* The SPY core and FIFO tax lots trade through the engine exactly as on the site: 5+5 bps costs, the January settlement, the two-step terminal tax.
* Options are held at model value, settle at the SOQ, and are marked to market on the last trading day of each year.
* Cash earns T-bills less 0.1%/yr; the interest is taxed yearly as ordinary income.
* Cash is never borrowed: a deficit is covered by selling core.
* "Never sells the core" can only be approximate. A hedge costing 3-8% of equity a year has to be paid from somewhere. The default `core` funding keeps a 2% cash reserve and sells core (FIFO) only for premiums, taxes or variation margin beyond it. Payoffs above 4% of equity are swept back into the core at the next roll. The `res` rule pays only from a 5% reserve, and the hedge then dies within about a year.
* The tax ledger is adapted from r2_gap1: federal (with NIIT) and California ledgers, Section 1256 60/40, the federal 3-year 1256 carryback, and California carryforward.
* Tax modes:
  * `T1`: the textbook 1256 treatment the critic proposed;
  * `T1nocb`: T1 without the carryback;
  * `T2`: the straddle rules (section 5);
  * `cs`: a constructive sale on full futures hedges.
* Model-free overlays add the daily return of a CBOE index over the S&P 500 TR, at actual traded prices.

**Checks:**
* With the overlay off, OptBacktest reproduces the lab's SPY benchmark to 1e-10 at every checkpoint (full, CA) and the VFINXR benchmark to 9e-10 (long_r, CA and NONE).
* Pre-tax plumbing, against the CBOE indices over the same days (2000-2026 / 2006-2026):

  | overlay | overlay CAGR | index CAGR |
  |---|---|---|
  | P95-1M replica | 5.46% / 7.96% | PPUT 6.04% / 8.31% |
  | PPUT series | 5.89% / 8.10% | PPUT 6.04% / 8.31% |
  | VXTH series (2006-2026 only) | 9.86% | VXTH 10.01% |
  | CLLZ series | 5.27% / 7.22% | CLLZ 5.47% / 7.44% |
  | CLLZ-type replica | 5.86% / 7.92% | CLLZ 5.47% / 7.44% |

* The engine runs through `run_cfg`/`batch.py`, not `sweep.run`. The records use the sweep format, so `metrics` and `report` apply unchanged.

## 2. Pre-tax reality check: the CBOE indices themselves (1986-2026)

| index | what it holds | from | CAGR | S&P TR | excess | max DD (S&P) | 10y windows beaten |
|---|---|---|---|---|---|---|---|
| PPUT | S&P + monthly 5% OTM put | 1986 | 8.00% | 11.18% | **-3.18** | -42% (-55%) | 2% |
| PPUT3M | S&P + quarterly 10% OTM put | 2004 | 8.63% | 11.07% | **-2.43** | -40% | 0% |
| CLLZ | S&P + 2.5-5% put spread paid by a call | 1986 | 8.12% | 11.21% | **-3.09** | -47% | 3% |
| CLL3M | S&P + quarterly 95 put / 110 call | 2004 | 6.58% | 11.07% | **-4.49** | -30% | 0% |
| CLL | 95 put (quarterly) / 110 call (monthly) | 2008 | 6.93% | 12.59% | **-5.66** | -26% (-47%) | 0% |
| CLL1M | monthly 95 put / ATM call | 2004 | 3.45% | 11.07% | **-7.62** | -24% | 0% |
| VXTH | S&P + 0-1%/month 30-delta VIX calls | 2006 | 9.91% | 11.19% | **-1.28** | -43% | 14% |
| SPRO | S&P buffer-protect (defined outcome) | 2005 | 8.18% | 11.20% | -3.02 | -44% | 0% |
| BXMD / BXY / BXM | covered calls (not hedges) | 1986-2002 | | | -0.56 / -1.07 / -3.91 | | |

The payoffs come from a handful of years, which is the nature of insurance:

* Annual excess of PPUT was +10.7 pp in 1987, +9.8 in 2001, +16.9 in 2008 and +10.7 in 2020, and -3 to -12 pp in most other years.
* VXTH: -1.28 overall, **-4.41 without 2020**, and -5.24 without 2020 and 2008-09.
* PPUT is robust to removing events: -3.41 without 2020, and -3.44 without 1987.

**Conditional use, model-free, pre-tax.** Each monthly roll either holds the index's overlay or not:

| overlay used only… | PPUT | CLLZ | PPUT3M | VXTH |
|---|---|---|---|---|
| always | -3.19 | -3.09 | -2.43 | -1.29 |
| while S&P TR < SMA200 (22% of months) | -0.81 | -0.95 | -0.29 | -0.60 |
| while VIX < 15 | -0.86 | -0.62 | +0.32 | -1.05 |
| while VIX < 20 | -0.77 | -1.39 | -0.63 | **+1.43** |

Selling the index for T-bills on the same monthly SMA200 signal earned -1.97 over the same period.

I saw the VXTH "VIX < 20" cell before writing the after-tax grid and added that rule to it. It is therefore post hoc, and it is 2020 (section 3).

## 3. After-tax results, 2000-2026 (protocol `full`, 95 quarterly starts, SPY core)

**Screen.** 104 configurations were run on `screen` and `long_r_screen` in CA and NONE (`scratch/r2_gap3/grid.py`; all pre-registered except where labelled). Summary by family on 2000-2026, in CA:

* "Active" means the hedge stays on. The `res` funding rule (5% reserve, hedge only what the reserve can pay) runs dry within about a year and then holds almost nothing.
* No family has a configuration that passes items 1-3.

| family | configs (active) | score > 0 | best score | median score, active (NONE) | median max DD, active |
|---|---|---|---|---|---|
| puts (1M 85-95%, 3M 80-95%) | 25 (13) | 0 | -0.09 (inactive) | -1.24 (-1.43) | -47% |
| put spreads (95/85, 95/80, 90/75) | 13 (7) | 0 | -0.03 (inactive) | -1.09 (-1.24) | -44% |
| collars (95/110, 95/105, zero-cost) | 10 (5) | 1 (inactive) | +0.07 | -2.24 (-2.47) | -36% |
| conditional (trend down / VIX low) | 18 (18) | 4 | +0.52 | -0.75 (-0.71) | -45% |
| model-free PPUT / CLLZ (CBOE prices) | 8 (4) | 0 | -0.23 | -1.68 / -2.36 | -45% / -49% |
| model-free VXTH (VIX calls) | 10 (8) | 3 | +1.34 | -0.18 (+0.04) | -51% |
| short futures while trend down | 6 (6) | 2 | +0.71 | -0.77 | -35% |
| synthetic SPY-to-IEF switch (futures) | 4 (4) | 3 | +1.12 | +0.82 (+1.38) | -35% |
| hedged leverage (flagged) | 10 (10) | 8 | +2.60 | +0.72 (+1.62) | -67% |

**Finalists on `full`, with all three regimes and a monthly series for every start.** "boot p (avg)" is averaged over the 95 start dates. The step-up score uses pre-liquidation equity for both sides, for an investor who never liquidates.

| config | CA score | CA full | 10/15/20y beat | boot p (1st / avg) | max DD (SPY -55%) | FED | NONE | step-up |
|---|---|---|---|---|---|---|---|---|
| **LEV** +1.0x futures, no hedge | +2.72 | +0.95 | 85/87/93% | 0.37 / 0.10 | -86% | +3.50 | +4.75 | +1.89 |
| **LEV** +1.0x + 90/75 3M put spread | +2.59 | +1.26 | 75/81/96% | 0.31 / 0.07 | -71% | +3.27 | +4.45 | +1.81 |
| **LEV** +0.5x futures, no hedge | +1.75 | +0.95 | 85/91/100% | 0.28 / 0.07 | -71% | +2.14 | +2.83 | +1.42 |
| VXTH calls while VIX<20, from 2006 (post hoc) | +1.41 | +0.78 | 64/95/100% | 0.40 / 0.53 | -57% | +1.62 | +2.02 | +1.19 |
| **LEV** +0.5x + 90/75 put spread | +1.12 | +0.55 | 63/72/96% | 0.34 / 0.11 | -56% | +1.39 | +1.88 | +0.75 |
| VXTH calls while VIX<20 (post hoc) | +1.01 | +0.59 | 72/64/96% | 0.42 / 0.50 | -57% | +1.19 | +1.54 | +0.87 |
| Synthetic switch (ES short + ZN long) while R1 EMA100/200 off | +0.99 | +1.75 | 57/74/96% | 0.20 / 0.77 | -34% | +1.22 | +1.54 | +0.99 |
| same, constructive sale on each hedge | +0.90 | +1.22 | 55/74/56% | 0.29 / 0.82 | -39% | +1.19 | +1.54 | +0.55 |
| ES short only while R1 off | +0.59 | +1.18 | 55/70/96% | 0.25 / 0.78 | -34% | +0.74 | +0.97 | +0.56 |
| 95/105 1M collar while R1 off | +0.49 | +0.62 | 52/74/100% | 0.28 / 0.78 | -38% | +0.63 | +0.89 | +0.48 |
| 1M 95% puts while R1 off | +0.07 | +0.25 | 52/70/41% | 0.40 / 0.82 | -43% | +0.13 | +0.26 | +0.03 |
| 90/75 3M put spread, half notional | -0.40 | -0.30 | 15/0/4% | 0.78 / 0.79 | -49% | -0.42 | -0.41 | -0.51 |
| VXTH calls, always (CBOE prices) | -0.44 | -1.11 | 40/38/44% | 0.72 / 0.77 | -46% | -0.37 | -0.16 | -0.79 |
| 1M 85% puts, half notional | -0.51 | -0.59 | 0/0/0% | 0.97 / 0.95 | -53% | -0.54 | -0.56 | -0.61 |
| PPUT, half notional (CBOE prices) | -1.08 | -1.03 | 4/0/0% | 0.95 / 0.96 | -48% | -1.16 | -1.23 | -1.29 |
| CLLZ, half notional (CBOE prices) | -1.62 | -1.42 | 3/0/0% | 1.00 / 1.00 | -51% | -1.76 | -1.89 | -1.92 |
| 3M 90% puts | -1.95 | -1.93 | 1/0/0% | 0.96 / 0.98 | -42% | -2.10 | -2.25 | -2.35 |
| zero-cost 95/85 put-spread collar | -2.06 | -2.24 | 18/11/0% | 0.94 / 0.99 | -36% | -2.17 | -2.21 | -2.56 |
| 95/80 3M put spread | -2.21 | -1.74 | 6/0/0% | 0.92 / 0.95 | -38% | -2.38 | -2.55 | -2.70 |
| PPUT, full notional (CBOE prices) | -2.26 | -2.21 | 1/0/0% | 0.96 / 0.97 | -42% | -2.45 | -2.64 | -2.73 |
| zero-cost 97.5/95 put-spread collar (CLLZ-like) | -2.29 | -2.32 | 16/0/0% | 0.98 / 1.00 | -43% | -2.44 | -2.54 | -2.79 |
| 1M 95% puts (PPUT-like) | -2.36 | -2.59 | 1/0/0% | 0.97 / 0.98 | -42% | -2.56 | -2.75 | -2.85 |
| 95/110 3M collar (CLL3M-like) | -3.59 | -3.26 | 6/0/0% | 0.97 / 1.00 | -30% | -3.90 | -4.24 | -4.36 |

Reading the table:

* **Cost and payoff of a full hedge.** The 1M 95% put overlay pays premiums of 8.2% of equity a year and collects 4.2%, for an option P&L of -3.6%/yr. The 3M 95/80 put spread pays 8.2% for its long legs and nets -2.2%/yr after the short legs' premium and payoffs. The 95/110 collar, net of the calls sold, gives up 4.5%/yr.
* **Sharpe.** The equity-curve Sharpe of the static overlays is 0.44-0.52, against SPY's 0.51. The overlays buy lower volatility at full price; they do not improve risk-adjusted return.
* **Never liquidating makes it worse.** Every option overlay's step-up score is below its liquidation score. The overlay's tax losses only pay off when the core is finally sold.
* **Cost scales with notional.** On the screen, the full hedges (h = 1) cost almost exactly twice the half hedges: P95-1M -2.38 vs -1.14, PS95/80-3M -2.24 vs -1.09. Nothing is gained from scale.

## 4. Long history, 1986-2026 (protocol `long_r`, 151 starts, VFINXR core)

Same finalists. "ho10" is the mean CA excess of 10-year windows ending before 2000, which is the holdout.

| config | CA score | CA full | 10/15/20y beat | boot p | max DD (S&P -55%) | ho10 (beat) | NONE |
|---|---|---|---|---|---|---|---|
| **LEV** +1.0x futures, no hedge | +2.42 | +2.00 | 85/75/92% | 0.16 | -83% | +5.54 (100%) | +4.19 |
| **LEV** +1.0x + 90/75 put spread | +1.53 | +1.23 | 67/58/51% | 0.18 | -70% | +3.46 (100%) | +3.03 |
| **LEV** +0.5x, no hedge | +1.51 | +0.89 | 85/80/99% | 0.15 | -73% | +3.00 (100%) | +2.49 |
| VXTH while VIX<20, from 2006 | +1.41 | +0.77 | 64/95/100% | 0.41 | -57% | n/a | +2.01 |
| Synthetic switch while R1 off | +1.08 | -0.48 | 59/83/89% | 0.65 | -34% | **-2.58 (0%)** | +1.73 |
| same, constructive sale | +0.99 | -0.96 | 59/82/75% | 0.75 | -39% | -2.68 (0%) | +1.73 |
| 95/105 collar while R1 off | +0.45 | -0.14 | 56/83/100% | 0.61 | -40% | -0.79 (0%) | +0.79 |
| ES short while R1 off | +0.44 | -1.09 | 58/78/86% | 0.80 | -35% | -3.06 (0%) | +0.83 |
| 1M 95% puts while R1 off | +0.08 | -0.57 | 56/80/67% | 0.83 | -46% | -0.91 (0%) | +0.24 |
| VXTH calls always (2006+) | -0.19 | -1.32 | 26/39/37% | 0.81 | -50% | n/a | +0.00 |
| 90/75 put spread, half notional | -0.52 | -0.66 | 11/0/1% | 0.97 | -50% | -0.76 (0%) | -0.55 |
| PPUT, half notional (CBOE) | -1.35 | -1.83 | 4/0/0% | 1.00 | -51% | -2.17 (0%) | -1.55 |
| zero-cost 97.5/95 put-spread collar | -1.93 | -2.82 | 14/0/0% | 1.00 | -45% | -1.78 (0%) | -2.13 |
| 3M 90% puts | -2.04 | -2.70 | 4/0/0% | 1.00 | -44% | -2.32 (0%) | -2.36 |
| 95/80 3M put spread | -2.24 | -3.09 | 7/0/0% | 1.00 | -42% | -3.34 (0%) | -2.56 |
| PPUT, full notional (CBOE) | -2.75 | -3.75 | 2/0/0% | 1.00 | -47% | -4.29 (0%) | -3.22 |
| 1M 95% puts | -2.87 | -4.07 | 1/0/0% | 1.00 | -48% | -4.28 (0%) | -3.36 |
| 95/110 3M collar | -3.09 | -4.30 | 8/0/0% | 1.00 | -34% | -3.64 (0%) | -3.60 |

The round-1 rule that sells the core (EMA100/200, VFINXR to VFITX/FGOVX), run through the lab on the same protocol, scores CA +1.13 with full excess -1.01, p 0.74 and ho10 -2.9 pp with 0% beaten. Doing the same thing with futures leaves the long-history picture unchanged. Every option overlay loses in the 1986-1999 holdout. That includes 1987, the crash the puts were made for: the October 1987 roll happened at the close of the -5% day, so the hedge was only partly in place.

## 5. Tax law: 1256 helps a little; the straddle rules apply and hurt

**Tax-law and option-price variants (protocol `full`, CA score; FED in brackets).** T2 is the straddle treatment described below the table. The `px` columns use alternative calibrations: without the SKEW term (v1), fitted on 1990-2007 only (early), and with doubled option spreads (wide).

| config | T1 | T1, no carryback | T2 (straddle) | px: v1 | px: early | px: wide |
|---|---|---|---|---|---|---|
| 1M 95% puts | -2.36 (-2.56) | -2.42 | -2.45 (-2.57) | -2.16 | -2.34 | -2.72 |
| 95/80 3M put spread | -2.21 (-2.38) | -2.27 | -2.26 (-2.37) | -2.31 | -3.13 | -2.64 |
| 95/110 3M collar | -3.59 (-3.90) | -3.72 | -3.55 (-3.78) | -3.57 | -3.99 | -4.02 |
| 95/105 collar while R1 off | +0.49 (+0.63) | +0.47 | +0.32 (+0.43) | +0.39 | +0.44 | +0.34 |
| synthetic switch while R1 off | +0.99 (+1.22) | +0.85 | **+0.48** (+0.65) | | | |
| same, constructive sale | +0.90 (+1.19) | +0.74 | +0.37 (+0.61) | | | |
| ES short while R1 off | +0.59 (+0.74) | +0.49 | +0.25 (+0.37) | | | |
| VXTH VIX calls, always | -0.44 (-0.37) | -0.47 | (-1.06)* | | | |
| VXTH while VIX<20 | +1.01 (+1.19) | +1.00 | (+0.76)* | | | |
| **LEV** +1.0x + 90/75 put spread | +2.59 (+3.27) | +2.51 | n/a | +2.53 | **+1.31** | +2.05 |
| **LEV** +0.5x + 90/75 put spread | +1.12 (+1.39) | +1.10 | n/a | +1.08 | +0.17 | +0.72 |
| **LEV** +1.0x, no hedge | +2.72 (+3.50) | +2.53 | n/a | | | |

\* VIX options are probably not offsetting positions to an S&P fund under 1092, so T1 is the applicable treatment and the T2 column is only a stress case. Long futures are not offsetting positions either, so T2 is not shown for the leverage rows.

What the variants show:

* The federal carryback is worth 0.0-0.2 pp.
* The straddle rules cost the futures-based switches 0.3-0.5 pp.
* They change the static option overlays little on average, for two reasons. Those overlays' losses were mostly sheltering the gains from core sales anyway. And T2's one-year start delay saves a year of premium in every window.
* The long-window damage of T2 is in the worked example below.
* No pricing alternative brings a static overlay anywhere near zero; the spread assumption alone is worth about 0.4 pp.
* The hedged-leverage scores are fragile: the 1990-2007 calibration halves or erases them.


The textbook treatment (T1) taxes the overlay as a Section 1256 contract: marked to market every 31 December, 60% long-term and 40% short-term. That is 36.1% blended in CA and 23% in FED, and net losses can be carried back three years federally.

**For an S&P 500 fund hedged with S&P 500 options or futures, the straddle rules of IRC 1092 almost certainly apply.** The hedge is an offsetting position in "substantially similar or related property" (Reg. 1.246-5, overlap close to 100%). Three consequences follow:

* **Loss deferral.** A year's loss on the hedge is deferred to the extent of the core's unrecognised gain, so it is in practice deferred until the core is sold, while hedge gains are taxed at once.
* **Holding period.** The holding period of core lots that are less than a year old when hedged does not run, so lots bought with hedge payoffs stay short-term. This is Temp. Reg. 1.1092(b)-2T, which I approximate by resetting the lot's purchase date.
* **No easy election.** The mixed-straddle elections exist but do not restore the T1 result.

T2 models the first two, and starts hedging only after 366 days so that the first core lot is already long-term. A full futures hedge of the fund also risks being a constructive sale under IRC 1259. That is the `cs` variant: a deemed sale of every appreciated lot each time the hedge is put on.

Worked example, 1M 95% puts with h = 1, started 2000-01, CA:

| outcome | after-tax value on 2026-07-01 |
|---|---|
| SPY buy-and-hold | $616k |
| overlay, T1 | $322k |
| overlay, T2 | $255k |

* **Under T1:** the yearly 1256 losses ($3-26k) exactly offset the long-term gains realised by selling core to pay premiums, so no tax falls due in any year.
* **Under T2:**
  * the losses pile up deferred ($136k by 2025);
  * the core sales are taxed, and by 2015 they are sales of short-term "suspended" lots taxed at 48.1%;
  * the deferred pool only comes back at liquidation.

## 6. Drawdowns and crash episodes

**Crash episodes.** These are pre-tax changes from the pre-crash peak to the trough date, as engine equity. The 1987 column comes from the 1986-start VFINXR run; the rest from the 2000-start SPY run.

| strategy | 1987 | 2000-02 | 2007-09 | 2020 | 2022 | max DD 2000-26 |
|---|---|---|---|---|---|---|
| SPY buy-and-hold | -33.0% | -47.5% | -55.2% | -33.7% | -24.5% | -55.2% |
| 1M 95% puts | -26.6% | -40.6% | -39.9% | -12.7% | -21.7% | -42.1% |
| PPUT overlay (CBOE prices) | -21.9% | -36.2% | -41.2% | -9.1% | -21.6% | -41.6% |
| 3M 90% puts | -15.7% | -40.8% | -37.4% | -21.1% | -19.8% | -41.8% |
| 3M 80% puts (tail hedge) | -25.6% | -48.5% | -48.7% | -30.3% | -25.9% | -48.7% |
| 95/80 3M put spread | -20.6% | -29.9% | -37.3% | -20.1% | -15.4% | -37.7% |
| 95/110 3M collar | -11.8% | -26.1% | -25.0% | -14.5% | -13.8% | -27.0% |
| zero-cost 95/85 put-spread collar | -23.7% | -32.2% | -31.9% | -23.0% | -17.4% | -32.8% |
| VXTH VIX calls | n/a | -46.4% | -41.3% | **+28.0%** | -29.6% | -46.4% |
| 1M 95% puts while R1 off | -32.6% | -36.3% | -40.5% | -33.7% | -22.7% | -40.5% |
| synthetic SPY-to-IEF switch (futures) | -32.2% | **+6.5%** | -5.4% | -33.6% | -23.3% | -33.6% |
| R1 EMA100/200 timing (sells core) | -32.8% | +4.9% | -6.7% | -33.7% | -23.4% | -33.7% |
| R1 2x SMA175/3% (sells, leveraged) | | -17.0% | -5.6% | -22.3% | -37.3% | -40.8% |
| **LEV** +0.5x + 95/80 put spread | -28.7% | -43.5% | -49.4% | -27.7% | -22.8% | -49.8% |

The two kinds of protection are complementary. Options cut fast crashes, where trend rules are still invested: in 2020 the puts lost -9% to -21% against -34%, and VIX calls gained +28%. Trend rules (and their futures twin) cut slow bear markets: about +5% in 2000-02 and -6% in 2008, against -48% / -55%. Only the collar protects in both, at 3.6 pp/yr.


**Price per point of drawdown, full protocol, CA.** The overlays cut SPY's -55% maximum drawdown, but at 2-6 times the cost per point of a static Treasury allocation, and 3-5 times for the full hedges. The mixes cost about 0.04 pp of score per point of drawdown removed; the full option hedges cost 0.11-0.18.

| route to a lower drawdown | CA score | max DD | Sharpe |
|---|---|---|---|
| SPY | 0 | -55% | 0.51 |
| B&H SPY 90 / VFITX 10 | -0.33 | -46% | 0.55 |
| B&H SPY 80 / VFITX 20 | -0.68 | -37% | 0.61 |
| B&H SPY 70 / VFITX 30 | -1.06 | -29% | 0.67 |
| 1M 85% puts, half notional | -0.51 | -53% | 0.50 |
| 90/75 put spread, half notional | -0.40 | -49% | 0.53 |
| 1M 95% puts | -2.36 | -42% | 0.44 |
| 95/80 put spread | -2.21 | -38% | 0.52 |
| zero-cost 95/85 put-spread collar | -2.06 | -36% | 0.51 |
| 95/110 collar | -3.59 | -30% | 0.49 |
| R1 EMA100/200 timing, sells core | +1.01 | -40% | 0.62 |
| R1 2x SMA175/3% (conditional lead) | +4.94 | -47% | 0.58 |

A holder who already has a large embedded gain pays a one-time tax to move into Treasuries. Selling 30% of a position that is 90% gain costs 0.3 x 0.9 x 28.1% = 7.6% of the sold amount, or 2.3% of the portfolio, once. The collar costs about 4.5% a year in option P&L. The one-time sale is cheaper after about half a year.

## 7. The VIX-call sleeve

* **VXTH as published** holds 30-delta 1-month VIX calls, 1% of the portfolio a month when VIX futures are between 15 and 30.
  * Over the S&P core it scores CA -0.44 on `full`. The calls only exist from 2006, so the 2000-2005 years carry no overlay.
  * Scored from 2006 it is -1.14 on the screen; half size gives -0.30, double size -3.80.
  * Its pre-tax deficit is -1.28 pp/yr, all of it cost. The payoffs are 2020 (+95 pp relative in that year) and 2008 (+18 pp).
* **The VIX < 20 version** is the only option-family result above +1. Six facts argue against it:
  * it was chosen after seeing pre-tax data;
  * it is not robust to the threshold: VIX < 25 gives -0.02;
  * its first-start boot p is 0.40, and the average over starts is 0.50-0.53;
  * the bootstrap chance of trailing SPY over 10 years is 52-58%;
  * its deflated Sharpe is 0.000;
  * its 10- and 15-year beats come from windows that contain March 2020.
* VIX options exist only from 2006, so there is no older history to test it on.

## 8. Hedged leverage (flagged; overlaps r2_gap1)

Constant long S&P futures on top of the never-sold core (+0.5x or +1.0x, 1256 taxed) score CA +1.75 / +2.72. Their drawdowns are -71% / -86%, and 2000-start p is 0.28 / 0.37; the start-averaged p is about 0.07-0.10, because 2000 was the worst start.

Adding a 90/75 put spread on the whole exposure costs 0.1-0.6 pp. It cuts the drawdown only to -56% / -71%, never back to SPY's -55%. Tighter hedges (95/85 monthly, 95/80 quarterly) cost 1.5-2.4 pp.

The round-1 trend-switched 2x rule (+4.94, p 0.077, drawdown -47%) dominates every hedged-leverage combination. Options do not make constant leverage acceptable.

## 9. Overfitting diagnostics (lab functions)

* **Walk-forward** (`report.diagnostics` on the 104 screened configs, CA):
  * across all configs: 10-to-5-year out of sample +1.36 pp, beating SPY in 42% of decisions. The gain comes from picking the leverage configs.
  * option overlays only (84 configs): out of sample **-0.73 pp, 17% beat**; 5-to-3-year: -1.29, 21%.
* **PBO:** 0.64 for all configs, 0.55 for options only.
* **Deflated Sharpe** of the best config: 0.02-0.03 within the family, and 0.0000-0.0012 for every finalist given about 12.8k configurations tried overall.
* **Bootstrap of the first start's monthly after-tax excess** (12-month blocks): the chance of trailing SPY after 10 years is 33-40% for the leverage configs, 34% for the synthetic switch and 52-58% for the VXTH VIX < 20 rule. After 20 years it is 24-54%.

## 10. Against SPY and round-1's leads (full protocol, CA)

| strategy | score | full | 10/15y beat | boot p | max DD | verdict |
|---|---|---|---|---|---|---|
| SPY buy-and-hold | 0 | 0 | | | -55% | default |
| round-1 KX3 tax-managed momentum | +0.99 | +1.84 | 90/85% | 0.011 | -54% | failed items 4, 6, 7 |
| round-1 EMA100/200 timing (sells core) | +1.01 | +1.36 | 57/75% | 0.29 | -40% | fail |
| round-1 2x SMA175/3% (sells, leveraged) | +4.94 | +3.80 | 100/100% | 0.077 | -47% | conditional |
| best option hedge that stays on (90/75 spread, half notional) | -0.40 | -0.30 | 15/0% | 0.78 | -49% | fail |
| best conditional option hedge (95/105 collar while R1 off) | +0.49 | +0.62 | 52/74% | 0.28 | -38% | fail |
| synthetic switch with futures (R1 signal) | +0.99 | +1.75 | 57/74% | 0.20 | -34% | fail (= R1 sell version) |
| VXTH VIX calls while VIX<20 (post hoc) | +1.01 | +0.59 | 72/64% | 0.42 | -57% | fail |

## 11. What was tried

* **Configurations: 150.**
  * 104 overlay configurations, in `grid.py`:
    * 60 option structures, hedge ratios and funding rules;
    * 13 model-free CBOE-index overlays;
    * 4 futures hedges;
    * 18 second-stage configurations: round-1 signal via overlay, hedged leverage, ladders;
    * 5 VIX-sleeve variants scored from 2006;
    * 4 synthetic switches.
  * 46 tax-law and pricing variants of 15 finalists.
* **Comparators run through the lab:** the round-1 EMA100/200 rule on 4 protocols and 6 static SPY/Treasury mixes. The round-1 leads were already cached.
* **Calibration:** two option-model versions (6 and 8 parameters) fitted to 10 CBOE indices, a 1990-2007-only refit, and one discarded attempt to back out 1986-89 implied volatility.
* **Runs:** about 725 config x regime x protocol runs (screen and long_r_screen 416; full 96 with monthly series for all 95 starts; long_r 96; variants about 117). That is roughly 50,000 engine backtests.
* **Search size.** The global count rises from about 12.5k to about 12.65k configurations; the deflated Sharpe ratios above use 12.8k.


## 12. Caveats

* **Contract size.** XSP (1/10 SPX) has about $77k notional, so hedging is lumpy below roughly $250k; SPX ($770k) needs about $2M or more. The model trades fractional contracts.
* **The $3,000 deduction against ordinary income is not modelled**, in keeping with the engine. Under T1 it would add up to about $1.3k a year at 44% for loss-making overlays. That is material only for small accounts and is not available under the straddle deferral.
* **Option prices are a calibrated model, not quotes.**
  * The model-free CBOE-index overlays (PPUT, CLLZ, VXTH) carry the same verdict at actual traded prices.
  * The replica is about 0.2-0.5 pp/yr conservative for bought puts and about 0.5-1 pp/yr generous for collars.
  * Pricing sensitivity is in section 5.
* **The model's own conventions:**
  * premiums are funded by selling core (FIFO) once the 2% reserve is used;
  * the reserve's T-bill interest is taxed yearly;
  * the strategy never borrows;
  * futures roll and basis costs are 0.2%/yr for ES and 0.1%/yr for ZN, plus 1-2 bp per trade.
* **Legal treatment.** The straddle and constructive-sale treatment is my reading of IRC 1092/1259 and the regulations. It needs a tax adviser's confirmation before anyone relies on it.

## 13. Files

* `research/lab/families/r2_gap3.py`: option model, Ledger, OptBacktest/OptGate/OverlayStrategy, `run_cfg`/`run_many`.
* `research/lab/scratch/r2_gap3/`:
  * `grid.py` (all configs);
  * `batch.py` and `run_batch.py` (runner);
  * `calib2.py` and `replica2.py` (calibration);
  * `pretax.py` and `cond_quick.py` (CBOE pre-tax);
  * `validate_plumbing.py`;
  * `stage_b.py` / `stage_c.py` (finalists, variants);
  * `diag.py`, `episodes.py`, `run_episodes.py`, `robust.py`, `make_tables.py`, `mixes.py`, `r1_comp.py`;
  * outputs in `out/` (calibration parameters, CSV tables, `finalists.json`, diagnostics);
  * `cboe/` and `docs/` hold the downloaded CBOE histories and methodologies.
* `research/lab/data/R2G3_*.csv`: CBOE index and SKEW/VVIX histories (signals and calibration only, never tradable).
