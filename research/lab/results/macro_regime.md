# Macro and cross-asset regime signals (`macro_regime`)

**Verdict (CA, the user's account): no.** No macro or cross-asset regime signal in this family beats
buying and holding SPY after California tax with good confidence. The family's one real effect is the
10y-3m yield-curve signal. After the curve un-inverts, moving to intermediate Treasuries (VFITX) avoided
most of the 2001-02 and 2007-09 bear markets. That gives large backtest gains: the best configs score
+3 to +4 pp/yr, and the edge survives tax, other equity menus and a one-day lag. But the whole edge
rests on **two events** in the ETF era. There were four un-inversions since 2000, and for the
long-hold rules the 2019 and 2024 ones cost money. It fails the beat-rate bar in every CA variant
(on `full`: 10-year beat rate 0.51-0.82; 15-year beat rate at most 0.81 against a bar of 0.85). The family's walk-forward selection is negative out of
sample in CA (-3.38 pp/yr over 449 configs, 10y->5y), and the 2010-2026 sub-periods are negative for
every long-hold variant. In FED, the short-hold variant (risk-off for 150-180 days after an
un-inversion) passes the numeric conditions 1-3 on protocol `full`. It fails them on the 1986-2026
long protocol (boot p 0.14-0.33), it is a narrow spike in parameter space, and the family's
walk-forward is negative in FED too (section 10). In NONE several
variants pass conditions 1-3; NONE is a diagnostic only here.

All numbers below come from the lab's engine (`research.lab`, which matches the site to 0.0). Excess is
after-tax CAGR minus SPY's (VFINX in the long protocols), in pp/yr. "score" is the pre-registered
`report.score` (mean of the 5-, 10- and 15-year mean excess).

## 1. What the family does

One signal, `macro_regime.switch` (`research/lab/families/macro_regime.py`): a list of causal 0/1
"risk-on" indicators is combined into a risk-on fraction f. The rule then holds
`eq = off_eq + (on_eq - off_eq) * f` in the risk book (SPY, VFINX in the long protocols) and the
rest in a safe book (VFITX intermediate Treasuries by default; FGOVX before VFITX existed in 1991).

* **No look-ahead.** Every indicator is computed causally (trailing windows, sequential state
  machines) and read with a lag of at least one calendar day: on day d the rule uses the last value
  dated strictly before d. A lag of 0 is refused in code. Signal-only inputs (^TNX, ^IRX, ^FVX,
  ^TYX, mutual-fund NAVs) are read from the data files and never enter the tradable market. The
  `lag2` / `lag5` variants change nothing material (section 7).
* **Indicator types**: yield-curve slope with inversion episodes (level, delay after inversion, or a
  window anchored at the un-inversion), 10y-yield and T-bill momentum (`diff` in points), credit-spread
  proxies (HY bond fund / Treasury fund ratios: VWEHX/VFITX, HYG/IEF, LQD/IEF, JNK/SHY), stock/bond
  relative momentum, commodity trend (DBC, GSG), gold/stocks (GLD, FSAGX, VGPMX), copper/gold
  (DBB/GLD), risk-appetite ratios (XLY/XLP, XLI/XLU, IWM/SPY, cyclicals/defensives, transports;
  long-history Fidelity Select proxies), sector breadth (9 SPDRs; 27 Fidelity Select funds back to
  1986), DAA-style canaries, breakeven inflation (TIP/IEF, VIPSX), and composites (a five-signal
  composite **pre-registered before any result was seen**, plus clearly labelled post-hoc ones).
* **Combinations**: `all` (risk-off if any indicator is off), `any` (risk-off only if all are off;
  used for the *macro-gated trend* rules), `vote`, `mean` (proportional tilt).
* **Implementations tested**: standard execution; tax execution (wash-sale guard, gain budgets, no
  short-term gains); a 70% core that is never sold plus a timed 30% sleeve (in VTSMX, a different
  index); half switches (`off_eq` 0.5); minimum holding periods; daily, weekly and monthly checks;
  safe asset = short Treasuries (VFISX) or long Treasuries (VUSTX, labelled hindsight).
* **Overlays on the incumbent** (module v2 adds `risk_signal`): the regime scales the site preset's
  12-1 momentum top-5 rotation over the same 22 ETFs. Each overlay is run next to an untimed
  control on the same machinery.

## 2. What was tested

| stage | protocol | configs | runs (config x regime) | regimes | what |
|---|---|---|---|---|---|
| s1 | screen | 240 | 720 | CA,FED,NONE | every indicator type, single signal, SPY <-> VFITX, daily and monthly checks (+3 pre-registered composites) |
| s1L | long_screen | 194 | 388 | CA,NONE | long-history versions of s1 (VFINX; Fidelity Select / Vanguard proxies) |
| s2 | screen | 87 | 261 | CA,FED,NONE | neighbourhoods of the s1 leaders (curve un-inversion, T-bill, credit) + labelled post-hoc composites |
| s3 | screen | 70 | 210 | CA,FED,NONE | allocation / execution / tax variants of 10 leaders (safe asset, half switch, min hold, tax exec, core+sleeve) |
| s2L | long_screen | 42 | 84 | CA,NONE | long-history versions of the s2 curve neighbourhoods |
| s6 | screen | 21 | 63 | CA,FED,NONE | NEW macro-gated SPY trend (danger window AND SPY < SMA200) + trend-only controls |
| s4 | screen | 15 | 44 | CA,FED,NONE | macro overlays on the incumbent 12-1 momentum top-5 rotation (tax 1% / standard) + untimed control + site preset |
| fin_full | full | 12 | 36 | CA,FED,NONE | finalists (first batch) on protocol full |
| s5 | screen | 68 | 144 | CA,FED,NONE | lag / check-cadence variants of two curve leaders + 20 random equity menus timed vs untimed (60 control configs) |
| fin_long | long | 7 | 21 | CA,FED,NONE | long-history finalists on protocol long |
| s6b | screen | 9 | 27 | CA,FED,NONE | neighbourhood / implementation variants of the gated leader |
| fin2_full | full | 10 | 30 | CA,FED,NONE | finalists (second batch: gated, overlays, controls, site preset) on protocol full |
| long_gated | long | 4 | 12 | CA,FED,NONE | long-history gated trend + trend-only control on protocol long |

**750 unique configs** (689 family strategies, 61 controls: 60 random-menu configs and the site preset), **2040 runs** (config x regime x protocol). Finalists are re-runs of screened configs on the finer protocols. Each run is 24-151 engine backtests (one per start date).

Stages s1-s3, s1L and s2L were run by the first researcher. This researcher finished s2L, archived
every record, applied the additive `risk_signal` patch and verified it (16 re-runs of archived
configs, worst checkpoint difference 0.0), then ran s4 (overlays), s5 (robustness and random menus),
s6/s6b (new: macro-gated trend), the finalists on `full` and `long`, and FED on `screen` for the
diagnostics. Records made before the patch are kept in `scratch/macro_regime/records_archive.jsonl`;
the results table is built from the archive plus the cache.

## 3. Screen: every indicator category (protocol `screen`, 24 annual starts 2000-2023)

Best config per category, with the category's median, so failures are shown next to winners. The
label suffix `/ chkM` means the regime is re-evaluated monthly (default: daily).

**CA**

| indicator category | configs | best score | best config | its full excess | its boot p | median score | share score > 0 |
|---|---|---|---|---|---|---|---|
| macro-gated SPY trend | 27 | +4.11 | GATED uninv630 & spy200 / chkM | +3.48 | 0.074 | +2.40 | 0.85 |
| curve un-inversion window | 66 | +4.00 | uninv540 minlen90 / chkM | +3.76 | 0.064 | +0.62 | 0.86 |
| post-hoc composite | 4 | +3.52 | POSTHOC3 vote2 / chkM | +3.13 | 0.165 | +2.29 | 0.75 |
| T-bill momentum (Fed) | 57 | +2.49 | irx fall>0.25 63d off / chkM | +1.72 | 0.242 | +0.66 | 0.63 |
| credit spread proxy | 78 | +2.15 | credit HY/INT sma100 band1% / chkM / safe=LTT(hindsight) | +0.91 | 0.391 | -1.01 | 0.24 |
| overlay on MOM22 rotation | 14 | +1.68 | MOM22 top5 Q std + overlay uninv540 minlen90 | +1.12 | 0.345 | +0.14 | 0.57 |
| canary (DAA-style) | 13 | +0.13 | canary EM+BND(chain) 13612W k2 / chkM / core70+sleeve30(VTSMX) | -0.28 | 0.694 | -0.77 | 0.08 |
| 10y yield trend/momentum | 39 | +0.05 | tnx rise>1.0 63d off / chkM | -0.13 | 0.643 | -1.93 | 0.03 |
| pre-registered composite | 13 | -0.02 | COMP5 vote3 (pre-reg) / chkM / core70+sleeve30(VTSMX) | -0.10 | 0.569 | -0.83 | 0.00 |
| stock/bond relative momentum | 25 | -0.06 | stk/bond SPY/INT sma200 / chkM / core70+sleeve30(VTSMX) | -0.16 | 0.583 | -2.48 | 0.00 |
| curve inversion + delay | 8 | -0.22 | curve10y3m delay365 after180 | -0.93 | 0.857 | -0.31 | 0.00 |
| SPY trend only (control) | 3 | -0.35 | TRENDONLY spy200b2 | -0.18 | 0.553 | -0.38 | 0.00 |
| curve level (inverted = off) | 18 | -0.47 | curve10y5y lvl thr0 / chkM | -0.80 | 0.787 | -1.07 | 0.00 |
| gold / stocks | 12 | -0.84 | gold VGPMX/SPY mom252 lead off / chkM | -1.36 | 0.720 | -4.79 | 0.00 |
| sector breadth | 14 | -1.08 | breadth sect9 sma200>=0.5 / chkM | -1.56 | 0.776 | -2.16 | 0.00 |
| curve level + after | 10 | -1.08 | curve10y3m lvl+after180 thr0.0 / chkM | -1.58 | 0.837 | -1.38 | 0.00 |
| risk-appetite ratio | 24 | -1.32 | appetite XLY/XLP mom126 / chkM | -1.87 | 0.769 | -3.93 | 0.00 |
| breakeven inflation | 8 | -2.52 | breakeven VIPSX/INT sma200 | -3.78 | 0.924 | -5.47 | 0.00 |
| commodity trend | 12 | -4.25 | cmdty DBC<sma200 on / chkM | -3.90 | 0.939 | -6.98 | 0.00 |
| copper / gold | 4 | -4.56 | cu/au DBB/GLD sma200 / chkM | -4.24 | 0.901 | -5.77 | 0.00 |

**NONE (diagnostic)**

| indicator category | configs | best score | best config | its full excess | its boot p | median score | share score > 0 |
|---|---|---|---|---|---|---|---|
| macro-gated SPY trend | 27 | +5.45 | GATED uninv630 & spy200 / chkM | +4.81 | 0.030 | +3.38 | 0.89 |
| credit spread proxy | 78 | +5.26 | credit HY/INT sma100 band1% / chkM / safe=LTT(hindsight) | +3.73 | 0.150 | +0.62 | 0.59 |
| curve un-inversion window | 66 | +5.22 | uninv540 minlen90 / chkM | +4.77 | 0.036 | +1.53 | 0.98 |
| post-hoc composite | 4 | +4.84 | POSTHOC3 vote2 / chkM | +4.74 | 0.077 | +3.30 | 1.00 |
| overlay on MOM22 rotation | 14 | +4.55 | MOM22 top5 Q tax1% + overlay uninv540 minlen90 | +3.99 | 0.094 | +2.43 | 1.00 |
| T-bill momentum (Fed) | 57 | +3.51 | irx fall>0.25 63d off / chkM | +3.00 | 0.084 | +1.43 | 0.68 |
| stock/bond relative momentum | 25 | +1.60 | stk/bond SPY/INT sma200 / chkM / safe=LTT(hindsight) | +1.79 | 0.295 | -1.55 | 0.28 |
| canary (DAA-style) | 13 | +1.42 | canary EM+BND(chain) 13612W k2 / chkM / safe=LTT(hindsight) | +0.32 | 0.458 | +0.57 | 0.62 |
| SPY trend only (control) | 3 | +1.00 | TRENDONLY spy200b2 | +1.78 | 0.283 | +0.81 | 0.67 |
| pre-registered composite | 13 | +0.97 | COMP5 vote3 (pre-reg) / chkM / minhold=63 | +1.67 | 0.295 | +0.38 | 0.54 |
| 10y yield trend/momentum | 39 | +0.65 | tnx rise>1.0 252d off / chkM / safe=LTT(hindsight) | +0.24 | 0.347 | -1.49 | 0.28 |
| curve inversion + delay | 8 | +0.32 | curve10y3m delay180 after180 | -0.11 | 0.479 | +0.09 | 0.75 |
| risk-appetite ratio | 24 | +0.15 | appetite XLY/XLP mom126 / chkM | -0.25 | 0.575 | -3.22 | 0.08 |
| curve level (inverted = off) | 18 | -0.06 | curve5y3m lvl thr0 / chkM | -0.54 | 0.595 | -0.91 | 0.00 |
| sector breadth | 14 | -0.26 | breadth sect9 sma200>=0.5 / chkM | -0.53 | 0.617 | -1.82 | 0.00 |
| gold / stocks | 12 | -0.33 | gold VGPMX/SPY mom252 lead off / chkM | -0.62 | 0.592 | -4.68 | 0.00 |
| curve level + after | 10 | -0.79 | curve10y3m lvl+after180 thr0.0 / chkM | -0.63 | 0.614 | -1.24 | 0.00 |
| breakeven inflation | 8 | -1.66 | breakeven VIPSX/INT sma200 | -3.02 | 0.863 | -5.78 | 0.00 |
| commodity trend | 12 | -2.69 | cmdty GSG<sma200 on / chkM | -2.50 | 0.888 | -6.90 | 0.00 |
| copper / gold | 4 | -3.68 | cu/au DBB/GLD sma200 / chkM | -2.73 | 0.795 | -4.92 | 0.00 |

**Long screen (38 annual starts 1986-2023, VFINX benchmark), CA**

| indicator category | configs | best score | best config | its full excess | its boot p | median score | share score > 0 |
|---|---|---|---|---|---|---|---|
| curve un-inversion window | 44 | +3.66 | L uninv540 minlen90 / chkM | +1.84 | 0.166 | +0.70 | 0.91 |
| post-hoc composite | 4 | +2.84 | L POSTHOC3 vote2 / chkM | +0.36 | 0.463 | +2.15 | 0.75 |
| T-bill momentum (Fed) | 20 | +1.51 | L irx fall>1.0 252d off / chkM | -0.80 | 0.655 | -1.47 | 0.25 |
| curve level + after | 10 | +0.21 | L curve10y3m lvl+after365 thr0.0 / chkM | -1.77 | 0.860 | -0.35 | 0.20 |
| curve inversion + delay | 8 | +0.16 | L curve10y3m delay180 after365 | -1.65 | 0.914 | -0.11 | 0.38 |
| stock/bond relative momentum | 18 | +0.05 | L absmom VFINX/TBILL mom252 / chkM | -1.92 | 0.823 | -2.13 | 0.06 |
| curve level (inverted = off) | 18 | -0.17 | L curve30y3m lvl thr0 | -1.51 | 0.953 | -0.60 | 0.00 |
| 10y yield trend/momentum | 32 | -0.17 | L tnx rise>1.0 63d off / chkM | -0.99 | 0.935 | -3.12 | 0.00 |
| canary (DAA-style) | 4 | -0.18 | L canary INTL+BND(chain) 13612W k2 / chkM | -1.94 | 0.940 | -2.57 | 0.00 |
| gold / stocks | 8 | -0.28 | L gold VGPMX/VFINX mom252 lead off / chkM | -2.49 | 0.906 | -3.34 | 0.00 |
| pre-registered composite | 6 | -0.49 | L COMP5L vote3 (pre-reg) / chkM | -2.66 | 0.912 | -1.77 | 0.00 |
| credit spread proxy | 32 | -0.60 | L credit HY sma100 / chkM | -1.99 | 0.887 | -1.88 | 0.00 |
| sector breadth | 14 | -1.01 | L breadth fsel sma200>=0.33 / chkM | -2.46 | 0.950 | -2.33 | 0.00 |
| risk-appetite ratio | 18 | -2.83 | L appetite FSRPX/FDFAX sma200 / chkM | -4.97 | 0.988 | -5.24 | 0.00 |

What the screen says:

* **Only two signals have a positive median CA score: the curve un-inversion window and T-bill
  momentum (the "Fed is cutting fast" rule).** The composites and gates built from them are also
  positive. The momentum-rotation overlays have a positive median too, but that comes from the
  rotation itself (section 8). Commodity trend, copper/gold, breakeven
  inflation, gold/stocks, risk-appetite ratios, sector breadth, the plain inverted-curve level rule,
  10-year-yield momentum and stock/bond relative momentum all lose to SPY in CA. Most of them also
  lose in NONE.
* Credit-spread rules help in NONE (HY/Treasury ratio vs its 100-day SMA: NONE score up to +3.1 pp/yr
  with VFITX, +5.3 with long Treasuries, which is hindsight). In CA their 100-250 trades over the
  period are taxed away (median CA score -1.0 pp/yr).
* The pre-registered five-signal composite loses in CA on both screens and on `full`
  (CA score -0.82 pp/yr).

## 4. Finalists on protocol `full` (95 quarterly starts, 2000-01 ... 2023-07)

Finalists: 12 from the first researcher's screen plus 10 from this researcher's stages (gated trend,
overlays, controls, and the site preset as a reference row). The site preset row reproduces the
reference numbers exactly (CA score +0.66, full +1.54, 10y beat 0.70, boot p 0.025, maxDD -57%).
"bar 1-3" checks PROTOCOL section 3 conditions 1-3 only: 1 = score and full excess > 0, 2a = ex10 beat >= 0.75,
2b = ex15 beat >= 0.85, 3 = boot p <= 0.10.

**CA** (excess in pp/yr; bar = PROTOCOL 3 conditions 1-3)

| config | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | maxDD (SPY) | trades | turnover | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| uninv540 minlen90 / chkM | +3.87 | +3.76 | +3.99 | 0.57 | -2.11 | 0.81 | 1.00 | 0.064 | -34% (-55%) | 27 | 0.29 | fail 2a,2b |
| POSTHOC3 vote2 / chkM | +3.40 | +3.13 | +3.66 | 0.60 | -3.94 | 0.77 | 1.00 | 0.165 | -33% (-55%) | 51 | 0.52 | fail 2a,2b,3 |
| curve10y3m uninv after630 / chkM | +3.33 | +2.75 | +3.63 | 0.58 | -5.62 | 0.77 | 1.00 | 0.205 | -34% (-55%) | 40 | 0.29 | fail 2a,2b,3 |
| GATED uninv540 & spy200 / chkM | +3.12 | +2.80 | +3.25 | 0.64 | -2.15 | 0.77 | 1.00 | 0.101 | -35% (-55%) | 47 | 0.61 | fail 2a,2b,3 |
| GATED inv+after540 & spy200 / chkM | +2.87 | +2.61 | +3.03 | 0.61 | -3.57 | 0.77 | 1.00 | 0.153 | -35% (-55%) | 57 | 0.86 | fail 2a,2b,3 |
| curve10y3m uninv after540 / chkM | +2.63 | +2.15 | +2.86 | 0.57 | -5.51 | 0.77 | 1.00 | 0.247 | -30% (-55%) | 37 | 0.38 | fail 2a,2b,3 |
| GATED uninv720 & spy200 / chkM | +2.46 | +2.38 | +2.51 | 0.64 | -2.15 | 0.77 | 1.00 | 0.153 | -26% (-55%) | 50 | 0.61 | fail 2a,2b,3 |
| GATED irx fall>1.0 252d & spy200 / chkM | +2.35 | +2.21 | +2.41 | 0.64 | -2.02 | 0.77 | 1.00 | 0.155 | -28% (-55%) | 40 | 0.41 | fail 2a,2b,3 |
| irx fall>1.0 252d off / chkM | +1.56 | +1.42 | +1.67 | 0.57 | -3.88 | 0.72 | 1.00 | 0.310 | -33% (-55%) | 32 | 0.39 | fail 2a,2b,3 |
| MOM22 top5 Q std + overlay uninv540 minlen90 | +1.48 | +1.12 | +1.45 | 0.52 | -4.90 | 0.72 | 0.89 | 0.345 | -33% (-55%) | 631 | 1.41 | fail 2a,2b,3 |
| curve10y3m uninv after540 / chkM / exec=tax gb5% noST | +1.16 | +2.04 | +1.24 | 0.58 | -1.72 | 0.77 | 0.85 | 0.100 | -48% (-55%) | 52 | 0.07 | fail 2a,2b |
| MOM22 top5 Q tax1% + overlay uninv540 minlen90 | +1.00 | -2.02 | +1.18 | 0.75 | -1.56 | 0.62 | 0.63 | 0.783 | -27% (-55%) | 462 | 0.08 | fail 1,2a,2b,3 |
| credit HY/INT sma100 band1% / chkM | +0.78 | +0.47 | +1.05 | 0.55 | -6.27 | 0.72 | 0.44 | 0.446 | -34% (-55%) | 141 | 1.92 | fail 2a,2b,3 |
| MOM22 top5 Q tax1% + overlay untimed | +0.72 | +1.29 | +0.75 | 0.84 | -1.54 | 0.83 | 1.00 | 0.044 | -55% (-55%) | 581 | 0.11 | fail 2b |
| curve10y3m uninv after240 | +0.68 | +0.76 | +0.70 | 0.55 | -1.60 | 0.70 | 0.81 | 0.280 | -56% (-55%) | 34 | 0.40 | fail 2a,2b,3 |
| curve10y3m uninv after150 | +0.68 | +1.04 | +0.67 | 0.82 | -0.70 | 0.70 | 1.00 | 0.075 | -59% (-55%) | 31 | 0.40 | fail 2b |
| SITE preset Beat the S&P (CA) | +0.66 | +1.54 | +0.55 | 0.70 | -1.48 | 0.83 | 1.00 | 0.025 | -57% (-55%) | 295 | 0.11 | fail 2a,2b |
| MOM22 top5 Q tax1% + overlay uninv180 | +0.55 | +1.56 | +0.76 | 0.76 | -2.51 | 0.81 | 1.00 | 0.025 | -55% (-55%) | 521 | 0.13 | fail 2b |
| curve10y3m uninv after180 | +0.46 | +0.47 | +0.48 | 0.79 | -0.70 | 0.77 | 0.78 | 0.267 | -59% (-55%) | 32 | 0.40 | fail 2b,3 |
| curve10y3m uninv after180 / core70+sleeve30(VTSMX) | +0.22 | +0.22 | +0.22 | 0.82 | -0.23 | 0.81 | 0.85 | 0.216 | -56% (-55%) | 32 | 0.13 | fail 2b,3 |
| TRENDONLY spy200 / chkM | -0.61 | -0.38 | -0.60 | 0.52 | -6.43 | 0.38 | 0.30 | 0.573 | -34% (-55%) | 90 | 1.53 | fail 1,2a,2b,3 |
| COMP5 vote3 (pre-reg) / chkM | -0.82 | -0.41 | -0.74 | 0.51 | -6.13 | 0.32 | 0.15 | 0.587 | -31% (-55%) | 121 | 1.57 | fail 1,2a,2b,3 |


**FED** (excess in pp/yr; bar = PROTOCOL 3 conditions 1-3)

| config | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | maxDD (SPY) | trades | turnover | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| uninv540 minlen90 / chkM | +4.40 | +4.25 | +4.54 | 0.57 | -2.17 | 0.81 | 1.00 | 0.044 | -34% (-55%) | 25 | 0.28 | fail 2a,2b |
| POSTHOC3 vote2 / chkM | +3.92 | +3.79 | +4.22 | 0.60 | -3.85 | 0.77 | 1.00 | 0.125 | -25% (-55%) | 50 | 0.52 | fail 2a,2b,3 |
| curve10y3m uninv after630 / chkM | +3.85 | +3.37 | +4.19 | 0.58 | -5.82 | 0.77 | 1.00 | 0.161 | -25% (-55%) | 36 | 0.28 | fail 2a,2b,3 |
| GATED uninv540 & spy200 / chkM | +3.59 | +3.34 | +3.74 | 0.82 | -2.00 | 0.77 | 1.00 | 0.066 | -31% (-55%) | 43 | 0.62 | fail 2b |
| GATED inv+after540 & spy200 / chkM | +3.34 | +3.19 | +3.51 | 0.69 | -3.44 | 0.77 | 1.00 | 0.114 | -31% (-55%) | 54 | 0.89 | fail 2a,2b,3 |
| curve10y3m uninv after540 / chkM | +3.11 | +2.75 | +3.37 | 0.57 | -5.69 | 0.77 | 1.00 | 0.199 | -27% (-55%) | 35 | 0.38 | fail 2a,2b,3 |
| GATED uninv720 & spy200 / chkM | +2.87 | +2.93 | +2.92 | 0.82 | -2.15 | 0.77 | 1.00 | 0.105 | -25% (-55%) | 46 | 0.62 | fail 2b,3 |
| GATED irx fall>1.0 252d & spy200 / chkM | +2.74 | +2.71 | +2.81 | 0.82 | -2.15 | 0.77 | 1.00 | 0.110 | -28% (-55%) | 37 | 0.40 | fail 2b,3 |
| MOM22 top5 Q std + overlay uninv540 minlen90 | +2.26 | +2.06 | +2.24 | 0.52 | -4.64 | 0.74 | 1.00 | 0.256 | -33% (-55%) | 631 | 1.39 | fail 2a,2b,3 |
| irx fall>1.0 252d off / chkM | +1.92 | +1.98 | +2.04 | 0.57 | -3.79 | 0.72 | 1.00 | 0.253 | -27% (-55%) | 33 | 0.38 | fail 2a,2b,3 |
| credit HY/INT sma100 band1% / chkM | +1.36 | +1.25 | +1.68 | 0.57 | -6.46 | 0.74 | 0.63 | 0.360 | -34% (-55%) | 141 | 1.91 | fail 2a,2b,3 |
| curve10y3m uninv after540 / chkM / exec=tax gb5% noST | +1.34 | +2.27 | +1.44 | 0.58 | -1.77 | 0.77 | 1.00 | 0.078 | -47% (-55%) | 50 | 0.07 | fail 2a,2b |
| MOM22 top5 Q tax1% + overlay uninv540 minlen90 | +1.16 | -2.03 | +1.35 | 0.79 | -1.62 | 0.64 | 0.63 | 0.779 | -27% (-55%) | 464 | 0.08 | fail 1,2b,3 |
| curve10y3m uninv after240 | +1.03 | +1.36 | +1.04 | 0.61 | -1.14 | 0.72 | 0.96 | 0.153 | -54% (-55%) | 33 | 0.39 | fail 2a,2b,3 |
| curve10y3m uninv after150 | +1.00 | +1.60 | +0.97 | 0.85 | -0.75 | 0.96 | 1.00 | 0.021 | -57% (-55%) | 30 | 0.39 | pass |
| MOM22 top5 Q tax1% + overlay untimed | +0.81 | +1.34 | +0.85 | 0.85 | -1.59 | 0.85 | 1.00 | 0.044 | -55% (-55%) | 587 | 0.11 | pass |
| SITE preset Beat the S&P (CA) | +0.74 | +1.60 | +0.63 | 0.69 | -1.33 | 0.85 | 1.00 | 0.025 | -57% (-55%) | 297 | 0.11 | fail 2a |
| curve10y3m uninv after180 | +0.74 | +0.96 | +0.75 | 0.88 | -0.75 | 0.98 | 1.00 | 0.096 | -57% (-55%) | 31 | 0.40 | pass |
| MOM22 top5 Q tax1% + overlay uninv180 | +0.61 | +1.62 | +0.83 | 0.79 | -4.00 | 0.81 | 1.00 | 0.023 | -55% (-55%) | 518 | 0.13 | fail 2b |
| curve10y3m uninv after180 / core70+sleeve30(VTSMX) | +0.32 | +0.40 | +0.32 | 0.97 | -0.25 | 0.89 | 1.00 | 0.074 | -55% (-55%) | 31 | 0.14 | pass |
| TRENDONLY spy200 / chkM | -0.31 | +0.21 | -0.28 | 0.52 | -6.59 | 0.40 | 0.41 | 0.484 | -32% (-55%) | 88 | 1.57 | fail 1,2a,2b,3 |
| COMP5 vote3 (pre-reg) / chkM | -0.55 | +0.18 | -0.44 | 0.52 | -6.23 | 0.47 | 0.30 | 0.510 | -29% (-55%) | 121 | 1.54 | fail 1,2a,2b,3 |


**NONE** (excess in pp/yr; bar = PROTOCOL 3 conditions 1-3)

| config | score | full | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | maxDD (SPY) | trades | turnover | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| uninv540 minlen90 / chkM | +5.03 | +4.77 | +5.17 | 0.57 | -2.21 | 0.81 | 1.00 | 0.036 | -34% (-55%) | 15 | 0.28 | fail 2a,2b |
| POSTHOC3 vote2 / chkM | +4.64 | +4.74 | +4.94 | 0.61 | -3.05 | 0.77 | 1.00 | 0.077 | -24% (-55%) | 31 | 0.51 | fail 2a,2b |
| curve10y3m uninv after630 / chkM | +4.51 | +4.05 | +4.86 | 0.60 | -5.94 | 0.77 | 1.00 | 0.128 | -24% (-55%) | 18 | 0.27 | fail 2a,2b,3 |
| MOM22 top5 Q tax1% + overlay uninv540 minlen90 | +4.34 | +3.99 | +4.32 | 0.63 | -2.74 | 0.77 | 1.00 | 0.094 | -33% (-55%) | 628 | 1.37 | fail 2a,2b |
| MOM22 top5 Q std + overlay uninv540 minlen90 | +4.34 | +3.99 | +4.32 | 0.63 | -2.74 | 0.77 | 1.00 | 0.094 | -33% (-55%) | 628 | 1.37 | fail 2a,2b |
| GATED uninv540 & spy200 / chkM | +4.27 | +4.11 | +4.42 | 0.85 | -1.43 | 0.89 | 1.00 | 0.040 | -27% (-55%) | 28 | 0.63 | pass |
| GATED inv+after540 & spy200 / chkM | +4.07 | +4.11 | +4.25 | 0.72 | -2.68 | 0.77 | 1.00 | 0.052 | -27% (-55%) | 40 | 0.92 | fail 2a,2b |
| curve10y3m uninv after540 / chkM | +3.71 | +3.41 | +3.98 | 0.58 | -5.77 | 0.77 | 1.00 | 0.153 | -27% (-55%) | 21 | 0.37 | fail 2a,2b,3 |
| curve10y3m uninv after540 / chkM / exec=tax gb5% noST | +3.71 | +3.41 | +3.98 | 0.58 | -5.77 | 0.77 | 1.00 | 0.153 | -27% (-55%) | 21 | 0.37 | fail 2a,2b,3 |
| GATED uninv720 & spy200 / chkM | +3.43 | +3.68 | +3.47 | 0.85 | -2.27 | 0.85 | 1.00 | 0.060 | -24% (-55%) | 28 | 0.63 | pass |
| GATED irx fall>1.0 252d & spy200 / chkM | +3.26 | +3.28 | +3.33 | 0.85 | -2.27 | 0.85 | 1.00 | 0.060 | -28% (-55%) | 23 | 0.38 | pass |
| credit HY/INT sma100 band1% / chkM | +2.90 | +2.78 | +3.27 | 0.57 | -5.99 | 0.77 | 1.00 | 0.211 | -33% (-55%) | 109 | 1.90 | fail 2a,2b,3 |
| irx fall>1.0 252d off / chkM | +2.41 | +2.79 | +2.54 | 0.57 | -3.15 | 0.74 | 1.00 | 0.183 | -27% (-55%) | 19 | 0.38 | fail 2a,2b,3 |
| curve10y3m uninv after240 | +1.71 | +2.40 | +1.70 | 0.90 | -0.76 | 1.00 | 1.00 | 0.036 | -51% (-55%) | 19 | 0.39 | pass |
| curve10y3m uninv after150 | +1.55 | +2.31 | +1.48 | 0.87 | -0.76 | 0.96 | 1.00 | 0.009 | -55% (-55%) | 17 | 0.38 | pass |
| curve10y3m uninv after180 | +1.27 | +1.65 | +1.25 | 0.88 | -0.76 | 1.00 | 1.00 | 0.014 | -54% (-55%) | 17 | 0.39 | pass |
| MOM22 top5 Q tax1% + overlay uninv180 | +0.77 | +1.32 | +0.59 | 0.60 | -3.52 | 0.62 | 0.93 | 0.205 | -50% (-55%) | 703 | 1.69 | fail 2a,2b,3 |
| TRENDONLY spy200 / chkM | +0.52 | +1.33 | +0.57 | 0.54 | -6.39 | 0.66 | 0.44 | 0.350 | -31% (-55%) | 70 | 1.62 | fail 2a,2b,3 |
| curve10y3m uninv after180 / core70+sleeve30(VTSMX) | +0.49 | +0.67 | +0.49 | 0.97 | -0.25 | 1.00 | 1.00 | 0.019 | -54% (-55%) | 18 | 0.15 | pass |
| COMP5 vote3 (pre-reg) / chkM | +0.26 | +1.19 | +0.38 | 0.52 | -6.15 | 0.68 | 0.44 | 0.380 | -28% (-55%) | 93 | 1.50 | fail 2a,2b,3 |
| SITE preset Beat the S&P (CA) | +0.14 | +0.55 | -0.03 | 0.40 | -2.74 | 0.43 | 0.78 | 0.341 | -52% (-55%) | 713 | 1.45 | fail 2a,2b,3 |
| MOM22 top5 Q tax1% + overlay untimed | +0.14 | +0.55 | -0.03 | 0.40 | -2.74 | 0.43 | 0.78 | 0.341 | -52% (-55%) | 714 | 1.45 | fail 2a,2b,3 |


**Nothing passes conditions 1-3 in CA.** The closest are:

* `curve10y3m uninv after150`: fails only 2b (ex15 beat 0.70). Its neighbours after180 (2b, 3) and
  after240 (2a, 2b, 3) fail more.
* The MOM22 overlays: they fail 2b, and the overlay does not improve its own untimed control (the
  control alone gets ex15 beat 0.83).

In FED, three short-hold curve configs pass conditions 1-3: after150, after180, and after180 with a
70% untouched core.

Side observation for the lead (not a macro strategy): the untimed control `MOM22 top5 Q tax1% +
overlay untimed` is the incumbent's momentum rotation run through the lab's generic tax execution
(`WeightStrategy`, execution "tax", 1% gain budget) instead of the site's `TaxManagedCombo`.
* CA: score +0.72, full +1.29, ex10 beat 0.84, ex15 beat 0.83, boot p 0.044. It fails only 2b,
  where the site class gets 10y beat 0.70.
* FED: it passes conditions 1-3.

## 5. Long history (protocol `long`, 1986-2026) and the pre-2000 holdout

**CA**

| config | score | full (from 1986) | ex10 beat | ex15 beat | boot p | ho5 mean | ho10 mean | maxDD (VFINX) | trades | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| L uninv540 minlen90 / chkM | +3.71 | +1.84 | 0.59 | 0.90 | 0.166 | -0.00 | -0.00 | -34% (-55%) | 34 | fail 2a,3 |
| L curve10y3m uninv after540 / chkM | +3.05 | +0.77 | 0.59 | 0.88 | 0.376 | -0.00 | -0.00 | -33% (-55%) | 48 | fail 2a,3 |
| L GATED uninv540 & vfinx200 / chkM | +3.03 | +1.19 | 0.63 | 0.88 | 0.248 | -0.00 | -0.00 | -36% (-55%) | 59 | fail 2a,3 |
| L GATED uninv720 & vfinx200 / chkM | +2.70 | +0.90 | 0.63 | 0.88 | 0.300 | -0.00 | -0.00 | -33% (-55%) | 62 | fail 2a,3 |
| L GATED irx fall>1.0 252d & vfinx200 / chkM | +1.90 | -0.12 | 0.62 | 0.83 | 0.549 | -1.15 | -1.71 | -41% (-55%) | 65 | fail 1,2a,2b,3 |
| L irx fall>1.0 252d off / chkM | +1.62 | -0.80 | 0.57 | 0.82 | 0.655 | -1.72 | -2.32 | -36% (-55%) | 75 | fail 1,2a,2b,3 |
| L curve10y3m uninv after240 | +1.29 | -0.11 | 0.59 | 0.85 | 0.551 | -0.00 | -0.00 | -56% (-55%) | 42 | fail 1,2a,3 |
| L curve10y3m uninv after180 | +0.62 | -0.41 | 0.72 | 0.88 | 0.756 | -0.00 | -0.00 | -59% (-55%) | 39 | fail 1,2a,3 |
| L curve10y3m uninv after150 | +0.60 | -0.06 | 0.73 | 0.85 | 0.582 | -0.00 | -0.00 | -59% (-55%) | 38 | fail 1,2a,3 |
| L TRENDONLY vfinx200 / chkM | -0.28 | -2.92 | 0.54 | 0.51 | 0.917 | -3.46 | -4.16 | -34% (-55%) | 166 | fail 1,2a,2b,3 |
| L COMP5L vote3 (pre-reg) / chkM | -0.41 | -2.66 | 0.54 | 0.51 | 0.912 | -3.15 | -3.79 | -40% (-55%) | 158 | fail 1,2a,2b,3 |


**FED**

| config | score | full (from 1986) | ex10 beat | ex15 beat | boot p | ho5 mean | ho10 mean | maxDD (VFINX) | trades | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| L uninv540 minlen90 / chkM | +4.23 | +2.50 | 0.59 | 0.90 | 0.098 | -0.00 | -0.00 | -34% (-55%) | 32 | fail 2a |
| L curve10y3m uninv after540 / chkM | +3.53 | +1.50 | 0.59 | 0.88 | 0.268 | -0.00 | -0.00 | -33% (-55%) | 45 | fail 2a,3 |
| L GATED uninv540 & vfinx200 / chkM | +3.47 | +1.88 | 0.73 | 0.89 | 0.146 | -0.00 | -0.00 | -33% (-55%) | 53 | fail 2a,3 |
| L GATED uninv720 & vfinx200 / chkM | +3.11 | +1.59 | 0.73 | 0.88 | 0.178 | -0.00 | -0.00 | -33% (-55%) | 58 | fail 2a,3 |
| L GATED irx fall>1.0 252d & vfinx200 / chkM | +2.27 | +0.69 | 0.72 | 0.83 | 0.349 | -1.23 | -1.52 | -34% (-55%) | 61 | fail 2a,2b,3 |
| L irx fall>1.0 252d off / chkM | +2.01 | +0.06 | 0.57 | 0.82 | 0.485 | -1.83 | -2.11 | -33% (-55%) | 73 | fail 2a,2b,3 |
| L curve10y3m uninv after240 | +1.61 | +0.60 | 0.63 | 0.86 | 0.290 | -0.00 | -0.00 | -54% (-55%) | 42 | fail 2a,3 |
| L curve10y3m uninv after180 | +0.86 | +0.27 | 0.76 | 0.99 | 0.326 | -0.00 | -0.00 | -57% (-55%) | 40 | fail 3 |
| L curve10y3m uninv after150 | +0.86 | +0.66 | 0.75 | 0.96 | 0.136 | -0.00 | -0.00 | -57% (-55%) | 39 | fail 2a,3 |
| L TRENDONLY vfinx200 / chkM | +0.09 | -2.09 | 0.55 | 0.63 | 0.839 | -3.66 | -4.04 | -33% (-55%) | 168 | fail 1,2a,2b,3 |
| L COMP5L vote3 (pre-reg) / chkM | -0.14 | -1.87 | 0.56 | 0.61 | 0.839 | -3.45 | -3.79 | -38% (-55%) | 158 | fail 1,2a,2b,3 |


**NONE**

| config | score | full (from 1986) | ex10 beat | ex15 beat | boot p | ho5 mean | ho10 mean | maxDD (VFINX) | trades | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| L uninv540 minlen90 / chkM | +4.84 | +3.19 | 0.59 | 0.90 | 0.053 | -0.00 | -0.00 | -34% (-55%) | 17 | fail 2a |
| L curve10y3m uninv after540 / chkM | +4.12 | +2.29 | 0.60 | 0.88 | 0.162 | -0.00 | -0.00 | -33% (-55%) | 23 | fail 2a,3 |
| L GATED uninv540 & vfinx200 / chkM | +4.05 | +2.73 | 0.75 | 0.94 | 0.054 | -0.00 | -0.00 | -33% (-55%) | 32 | fail 2a |
| L GATED uninv720 & vfinx200 / chkM | +3.67 | +2.44 | 0.75 | 0.92 | 0.071 | -0.00 | -0.00 | -33% (-55%) | 32 | fail 2a |
| L GATED irx fall>1.0 252d & vfinx200 / chkM | +2.80 | +1.71 | 0.73 | 0.87 | 0.158 | -1.20 | -1.20 | -33% (-55%) | 35 | fail 2a,3 |
| L irx fall>1.0 252d off / chkM | +2.56 | +1.25 | 0.59 | 0.83 | 0.280 | -1.72 | -1.69 | -33% (-55%) | 43 | fail 2a,2b,3 |
| L curve10y3m uninv after240 | +2.18 | +1.63 | 0.77 | 0.99 | 0.046 | -0.00 | -0.00 | -51% (-55%) | 23 | pass |
| L curve10y3m uninv after180 | +1.29 | +1.11 | 0.76 | 0.99 | 0.017 | -0.00 | -0.00 | -54% (-55%) | 23 | pass |
| L curve10y3m uninv after150 | +1.28 | +1.53 | 0.76 | 0.97 | 0.012 | -0.00 | -0.00 | -55% (-55%) | 23 | pass |
| L TRENDONLY vfinx200 / chkM | +1.15 | -0.53 | 0.57 | 0.79 | 0.624 | -3.07 | -3.12 | -33% (-55%) | 134 | fail 1,2a,2b,3 |
| L COMP5L vote3 (pre-reg) / chkM | +0.53 | -0.69 | 0.58 | 0.67 | 0.650 | -3.46 | -3.50 | -38% (-55%) | 121 | fail 1,2a,2b,3 |


* **The pre-2000 holdout cannot test the curve signal.** Between 1986 and 1999 the ^TNX - ^IRX
  spread was below zero on only 6 days (in 1989, at most 3 in a row), so no inversion episode
  registers. Every curve config holds VFINX throughout every holdout window (ho5 / ho10 = 0.00
  exactly). ^IRX is a discount-basis yield, below the bond-equivalent 3-month yield, so the standard
  constant-maturity 10y-3m spread was more negative in 1989. A rule built on it might have
  registered a 1989 episode that this proxy misses. Where the holdout is informative it contradicts the signals:
  T-bill momentum (ho10 -2.32 pp/yr in CA), the pre-registered composite (-3.79), and VFINX trend
  alone (-4.16).
* From a 1986 start in CA, the short-hold curve rules **lose** (full excess -0.06 to -0.41 pp/yr,
  boot p 0.55-0.76). Selling in 2001 realizes 15 years of embedded gains. In FED they are slightly
  positive (+0.27 to +0.66), but boot p is 0.14-0.33.
* **Off-engine 1962-1985 check** (not site numbers: S&P 500 price index plus an assumed 4% dividend
  yield against 3-month T-bills, no tax, no costs; `pre1986_gated.py`, `pre1986_study.py`). This
  period has six un-inversion events.
  * Short-hold rule, uninv180: +1.76 %/yr edge. Supports the rule.
  * Long-hold rules: uninv540 -2.10 %/yr; uninv540 minlen90 -2.04 %/yr. They are **contradicted**:
    staying out for 1.5 years after an un-inversion would have missed the 1974-76 and 1980-83
    rallies.
  * Macro-gated trend: uninv540 & SMA200 +0.85 %/yr, uninv630 +1.04, uninv720 +0.68. Not
    contradicted.
  * T-bill-gated trend: -0.41 %/yr (1962-85) and -1.21 %/yr (1986-99). Contradicted.

## 6. Why the curve signal looks good, and why that is not good confidence

The un-inversion rule triggered at four dates since 2000 (2001-01-25, 2007-05-21, 2019-07-24,
2024-11-18). Off-engine event study (S&P price + 4% dividends vs T-bills, `uninv_events.py`):

| risk-off window after un-inversion | 2001 | 2007 | 2019 | 2024 | helped / events since 1962 |
|---|---|---|---|---|---|
| 180 days | avoided -10.2% | avoided -3.5% | avoided -2.4% | missed +2.4% | 7 / 10 |
| 540 days | avoided -31.5% | avoided -38.2% | missed +44.3% | missed +31.7% | 3 / 8 |

Sub-period excess on `full` (from `subperiods.py`):

| config | regime | 2000-2010 | 2010-2020 | 2020-2026 |
|---|---|---|---|---|
| curve10y3m uninv after180 | CA | +1.66 | -0.70 | +2.13 |
| curve10y3m uninv after180 | FED | +2.13 | -0.75 | +2.71 |
| curve10y3m uninv after150 | CA | +0.94 | -0.70 | +5.81 |
| curve10y3m uninv after150 | FED | +1.36 | -0.75 | +6.86 |
| curve10y3m uninv after240 | CA | +3.89 | -0.70 | -0.30 |
| curve10y3m uninv after240 | FED | +4.68 | -0.75 | +0.07 |
| curve10y3m uninv after540 / chkM | CA | +10.98 | -0.95 | -5.98 |
| curve10y3m uninv after540 / chkM | FED | +12.51 | -1.02 | -6.53 |
| curve10y3m uninv after630 / chkM | CA | +11.50 | -0.95 | -6.14 |
| curve10y3m uninv after630 / chkM | FED | +13.25 | -1.02 | -6.73 |
| uninv540 minlen90 / chkM | CA | +10.98 | -0.00 | -2.99 |
| uninv540 minlen90 / chkM | FED | +12.51 | -0.00 | -3.19 |
| curve10y3m uninv after180 / core70+sleeve30(VTSMX) | CA | +0.76 | -0.23 | +0.64 |
| curve10y3m uninv after180 / core70+sleeve30(VTSMX) | FED | +0.94 | -0.25 | +0.82 |
| curve10y3m uninv after540 / chkM / exec=tax gb5% noST | CA | +5.38 | -0.07 | -4.22 |
| curve10y3m uninv after540 / chkM / exec=tax gb5% noST | FED | +6.13 | -0.07 | -4.62 |
| irx fall>1.0 252d off / chkM | CA | +7.57 | -0.00 | -4.79 |
| irx fall>1.0 252d off / chkM | FED | +8.60 | -0.00 | -5.12 |
| credit HY/INT sma100 band1% / chkM | CA | +7.63 | -2.63 | -5.81 |
| credit HY/INT sma100 band1% / chkM | FED | +9.03 | -2.35 | -6.29 |
| COMP5 vote3 (pre-reg) / chkM | CA | +6.76 | -5.07 | -3.40 |
| COMP5 vote3 (pre-reg) / chkM | FED | +7.94 | -5.34 | -3.56 |
| POSTHOC3 vote2 / chkM | CA | +10.67 | -0.20 | -4.79 |
| POSTHOC3 vote2 / chkM | FED | +12.28 | -0.16 | -5.12 |

* **Long-hold variants** (after 540-630, monthly check) made about +11 pp/yr in 2000-2010. They
  lost in 2010-2020 and lost 3-6 pp/yr in 2020-2026. They are a bet that the next un-inversion
  looks like 2001 or 2007 rather than 2019 or 2024.
* **Short-hold variants** depend on the exact re-entry date. After150's risk-off windows ended on
  2020-03-16 and 2025-04-17, within about a week of both market lows. It made +5.81 pp/yr in
  2020-2026 (CA). After180 re-entered later and made +2.13; after120 is negative on the screen.
* **Parameter cliffs** come from single events:
  * Gated rule, after-window 450 / 540 / 630 / 720 days: CA screen score +0.48 / +3.23 / +4.11 /
    +2.62. After450 re-enters on 2008-08-13, just before the September-October 2008 crash.
  * minlen90 (ignore inversion episodes shorter than 90 days) helps only because it skips the
    2019 episode.

## 7. Robustness and hindsight checks

**Signal lag and check cadence** (s5 and s6b, protocol `screen`): one- to five-day lags and
daily/weekly/monthly checks leave the curve rules essentially unchanged. They are not
same-day artefacts.

**CA**

| config | score | full | ex10 beat | ex15 beat | boot p | maxDD | trades | turnover |
|---|---|---|---|---|---|---|---|---|
| curve10y3m uninv after540 / chkM / lag2 | +2.72 | +2.15 | 0.53 | 0.75 | 0.247 | -30% | 37 | 0.38 |
| curve10y3m uninv after540 / chkM / lag5 | +2.72 | +2.15 | 0.53 | 0.75 | 0.247 | -30% | 37 | 0.38 |
| curve10y3m uninv after540 / chkM / checkW | +2.60 | +2.29 | 0.53 | 0.75 | 0.220 | -29% | 39 | 0.38 |
| curve10y3m uninv after540 / chkM / checkD | +2.53 | +2.21 | 0.53 | 0.75 | 0.230 | -30% | 39 | 0.38 |
| curve10y3m uninv after180 / lag2 | +0.64 | +0.70 | 0.82 | 0.92 | 0.183 | -59% | 32 | 0.40 |
| curve10y3m uninv after180 / lag5 | +0.64 | +0.68 | 0.71 | 0.83 | 0.191 | -59% | 32 | 0.40 |
| curve10y3m uninv after180 / checkW | +0.63 | +0.67 | 0.71 | 0.83 | 0.193 | -59% | 32 | 0.40 |
| curve10y3m uninv after180 / checkM | +0.34 | +0.40 | 0.65 | 0.67 | 0.292 | -59% | 31 | 0.40 |


**Safe asset.** With short Treasuries (VFISX) in place of VFITX:
* uninv540 (monthly check): CA screen score falls from +2.72 to +2.35.
* Gated rule: CA score falls from +3.23 to +3.03.
* uninv180: CA score falls from +0.43 to +0.27.

Long Treasuries (VUSTX, hindsight) add a little. The result does not depend on the bond fund.

**Random menus (PROTOCOL 5.3).** The same curve rule was run on 20 random 5-ETF equity menus from
`common.BROAD_EQUITY_POOL_2003` (annual rebalance, VFITX safe asset), timed vs untimed (`rm_analysis.py`):

| rule | regime | menus | timed - untimed score (mean) | share improved | timed - untimed full excess (mean) | share improved | timed menus: mean score vs SPY | share > 0 | untimed menus: mean score vs SPY |
|---|---|---|---|---|---|---|---|---|---|
| uninv180 | CA | 20 | +0.83 | 1.00 | +0.82 | 1.00 | +0.09 | 0.55 | -0.74 |
| uninv540 chkM | CA | 20 | +3.41 | 1.00 | +2.39 | 1.00 | +2.67 | 1.00 | -0.74 |
| uninv180 | NONE | 20 | +1.66 | 1.00 | +1.95 | 1.00 | +0.96 | 0.75 | -0.70 |
| uninv540 chkM | NONE | 20 | +4.61 | 1.00 | +3.51 | 1.00 | +3.91 | 1.00 | -0.70 |

The timing improved all 20 menus in both regimes, so the effect is not a hindsight choice of
instrument. It is a market-wide bear-market effect, and with the same two events.

**Stricter tax accounting** (`research.lab.realism`: yearly tax on fund distributions; Treasury
interest at the federal ordinary rate and CA-exempt). It moves the excess by -0.0 to -0.24 pp/yr.
The engine's deferral of bond interest does not create these results. Values are engine excess
-> stricter excess, by start year:

| config | regime | from 2000 | from 2005 | from 2010 | from 2015 |
|---|---|---|---|---|---|
| uninv540 minlen90 / chkM | CA | +3.76 -> +3.60 | +2.35 -> +2.29 | -1.36 -> -1.35 | -1.82 -> -1.83 |
| uninv540 minlen90 / chkM | FED | +4.25 -> +4.04 | +2.70 -> +2.58 | -1.35 -> -1.40 | -1.87 -> -1.95 |
| curve10y3m uninv after150 | CA | +1.04 -> +0.95 | +0.65 -> +0.58 | +0.93 -> +0.87 | +1.93 -> +1.85 |
| curve10y3m uninv after150 | FED | +1.60 -> +1.50 | +1.33 -> +1.25 | +1.68 -> +1.61 | +2.71 -> +2.63 |
| curve10y3m uninv after180 | CA | +0.47 -> +0.39 | -0.17 -> -0.22 | -0.47 -> -0.50 | -0.09 -> -0.13 |
| curve10y3m uninv after180 | FED | +0.96 -> +0.87 | +0.41 -> +0.34 | +0.10 -> +0.05 | +0.45 -> +0.38 |
| curve10y3m uninv after540 / chkM | CA | +2.15 -> +2.00 | +0.35 -> +0.30 | -3.82 -> -3.82 | -4.82 -> -4.87 |
| curve10y3m uninv after540 / chkM | FED | +2.75 -> +2.51 | +0.84 -> +0.68 | -3.69 -> -3.81 | -4.93 -> -5.12 |
| GATED uninv540 & spy200 / chkM | CA | +2.80 -> +2.70 | +1.45 -> +1.45 | -1.62 -> -1.58 | -1.89 -> -1.86 |
| GATED uninv540 & spy200 / chkM | FED | +3.34 -> +3.21 | +1.93 -> +1.89 | -1.37 -> -1.36 | -1.74 -> -1.74 |
| curve10y3m uninv after180 / core70+sleeve30(VTSMX) | CA | +0.22 -> +0.20 | -0.02 -> -0.02 | -0.16 -> -0.16 | -0.08 -> -0.09 |
| curve10y3m uninv after180 / core70+sleeve30(VTSMX) | FED | +0.40 -> +0.37 | +0.16 -> +0.15 | +0.00 -> -0.01 | +0.07 -> +0.06 |

## 8. Macro overlays on the incumbent momentum rotation (s4)

**CA**

| config | score | full | ex10 beat | ex15 beat | boot p | maxDD | trades | turnover |
|---|---|---|---|---|---|---|---|---|
| MOM22 top5 Q std + overlay uninv540 minlen90 | +1.68 | +1.12 | 0.53 | 0.75 | 0.345 | -33% | 631 | 1.41 |
| MOM22 top5 Q tax1% + overlay uninv540 minlen90 | +0.87 | -2.02 | 0.65 | 0.50 | 0.783 | -27% | 462 | 0.08 |
| MOM22 top5 Q tax1% + overlay untimed | +0.73 | +1.29 | 0.76 | 0.75 | 0.044 | -55% | 581 | 0.11 |
| SITE preset Beat the S&P (CA) | +0.64 | +1.54 | 0.59 | 0.75 | 0.025 | -57% | 295 | 0.11 |
| MOM22 top5 Q std + overlay uninv540 | +0.64 | +0.05 | 0.53 | 0.58 | 0.502 | -30% | 603 | 1.42 |
| MOM22 top5 Q tax1% + overlay uninv180 | +0.51 | +1.56 | 0.65 | 0.75 | 0.025 | -55% | 521 | 0.13 |
| MOM22 top5 Q tax1% + overlay uninv540 | +0.50 | -2.36 | 0.53 | 0.50 | 0.811 | -27% | 437 | 0.08 |
| MOM22 top5 Q std + overlay irx fall>1.0 252d | +0.18 | +0.12 | 0.53 | 0.50 | 0.506 | -36% | 618 | 1.58 |
| MOM22 top5 Q std + overlay credit HY/INT sma100 b1% | +0.10 | -0.17 | 0.53 | 0.58 | 0.534 | -35% | 741 | 2.80 |
| MOM22 top5 Q tax1% + overlay irx fall>1.0 252d | -0.24 | -3.48 | 0.41 | 0.17 | 0.898 | -33% | 396 | 0.09 |
| MOM22 top5 Q std + overlay uninv180 | -0.94 | -0.84 | 0.35 | 0.25 | 0.735 | -57% | 707 | 1.69 |
| MOM22 top5 Q std + overlay COMP5 vote3 | -0.95 | -0.73 | 0.47 | 0.33 | 0.614 | -31% | 749 | 2.64 |
| MOM22 top5 Q std + overlay untimed | -1.10 | -1.10 | 0.29 | 0.25 | 0.815 | -56% | 714 | 1.46 |
| MOM22 top5 Q tax1% + overlay credit HY/INT sma100 b1% | -1.16 | -4.14 | 0.35 | 0.42 | 0.877 | -16% | 358 | 0.06 |
| MOM22 top5 Q tax1% + overlay COMP5 vote3 | -1.44 | -4.11 | 0.29 | 0.25 | 0.875 | -16% | 320 | 0.07 |


**NONE**

| config | score | full | ex10 beat | ex15 beat | boot p | maxDD | trades | turnover |
|---|---|---|---|---|---|---|---|---|
| MOM22 top5 Q tax1% + overlay uninv540 minlen90 | +4.55 | +3.99 | 0.65 | 0.75 | 0.094 | -33% | 628 | 1.37 |
| MOM22 top5 Q std + overlay uninv540 minlen90 | +4.55 | +3.99 | 0.65 | 0.75 | 0.094 | -33% | 628 | 1.37 |
| MOM22 top5 Q tax1% + overlay credit HY/INT sma100 b1% | +3.74 | +3.79 | 0.59 | 0.75 | 0.133 | -27% | 740 | 2.85 |
| MOM22 top5 Q std + overlay credit HY/INT sma100 b1% | +3.74 | +3.79 | 0.59 | 0.75 | 0.133 | -27% | 740 | 2.85 |
| MOM22 top5 Q tax1% + overlay uninv540 | +3.03 | +2.49 | 0.53 | 0.75 | 0.246 | -28% | 597 | 1.38 |
| MOM22 top5 Q std + overlay uninv540 | +3.03 | +2.49 | 0.53 | 0.75 | 0.246 | -28% | 597 | 1.38 |
| MOM22 top5 Q tax1% + overlay irx fall>1.0 252d | +2.43 | +2.74 | 0.53 | 0.75 | 0.209 | -35% | 615 | 1.60 |
| MOM22 top5 Q std + overlay irx fall>1.0 252d | +2.43 | +2.74 | 0.53 | 0.75 | 0.209 | -35% | 615 | 1.60 |
| MOM22 top5 Q tax1% + overlay COMP5 vote3 | +1.52 | +2.39 | 0.53 | 0.67 | 0.249 | -23% | 742 | 2.59 |
| MOM22 top5 Q std + overlay COMP5 vote3 | +1.52 | +2.39 | 0.53 | 0.67 | 0.249 | -23% | 742 | 2.59 |
| MOM22 top5 Q tax1% + overlay uninv180 | +0.86 | +1.32 | 0.59 | 0.50 | 0.205 | -50% | 703 | 1.69 |
| MOM22 top5 Q std + overlay uninv180 | +0.86 | +1.32 | 0.59 | 0.50 | 0.205 | -50% | 703 | 1.69 |
| SITE preset Beat the S&P (CA) | +0.26 | +0.55 | 0.47 | 0.42 | 0.341 | -52% | 713 | 1.45 |
| MOM22 top5 Q tax1% + overlay untimed | +0.26 | +0.55 | 0.47 | 0.42 | 0.341 | -52% | 714 | 1.45 |
| MOM22 top5 Q std + overlay untimed | +0.26 | +0.55 | 0.47 | 0.42 | 0.341 | -52% | 714 | 1.45 |


* With the incumbent's own tax discipline (1% gain budget), every overlay lowers the untimed
  rotation's CA score, apart from the post-hoc minlen90 version (+0.87 vs +0.73, but full excess
  -2.02 pp/yr and boot p 0.78).
* Full excess falls by 3.6-5.4 pp/yr for the uninv540, irx, credit and composite overlays. Only the
  uninv180 overlay keeps it (+1.56 vs +1.29).
* With standard (not tax-aware) execution the rotation itself loses to SPY in CA (-1.10). The
  overlays raise it to between -0.95 and +1.68. They help a lot in NONE (+4.55 score with uninv540
  minlen90), where selling is free.
* On `full`: untimed control CA score +0.72, full +1.29, ex10 beat 0.84, ex15 beat 0.83, boot p
  0.044. uninv180 overlay: +0.55, +1.56, 0.76, 0.81, 0.025. **A macro overlay does not add
  after-tax value to the incumbent.**

## 9. Macro-gated trend (new idea, s6 + s6b)

Rule: risk-off only while a macro "danger window" is open **and** SPY is below its 200-day SMA
(combine `any`, so either signal on means risk-on). Gating fixes trend following's whipsaw and the
macro rule's early exit.

* SPY 200-day trend alone (daily): CA screen score -2.54 pp/yr, 397 trades.
* Trend alone, checked monthly: CA score -0.38.
* Gated by the 540-day post-un-inversion window: +3.23 with 47 trades.

s6, protocol `screen`:

**CA**

| config | score | full | ex10 beat | ex15 beat | boot p | maxDD | trades | turnover |
|---|---|---|---|---|---|---|---|---|
| GATED uninv540 & spy200 / chkM | +3.23 | +2.80 | 0.59 | 0.75 | 0.101 | -35% | 47 | 0.61 |
| GATED inv+after540 & spy200 / chkM | +2.99 | +2.61 | 0.59 | 0.75 | 0.153 | -35% | 57 | 0.86 |
| GATED uninv540 & spy200b2 | +2.74 | +2.57 | 0.53 | 0.75 | 0.118 | -35% | 61 | 0.77 |
| GATED uninv720 & spy200 / chkM | +2.62 | +2.38 | 0.59 | 0.75 | 0.153 | -26% | 50 | 0.61 |
| GATED inv+after540 & spy200b2 | +2.53 | +2.41 | 0.53 | 0.75 | 0.163 | -35% | 72 | 1.02 |
| GATED uninv720 & spy200b2 | +2.52 | +2.22 | 0.59 | 0.75 | 0.168 | -26% | 64 | 0.78 |
| GATED irx fall>1.0 252d & spy200b2 | +2.40 | +2.47 | 0.53 | 0.75 | 0.128 | -26% | 66 | 0.85 |
| GATED irx fall>1.0 252d & spy200 / chkM | +2.40 | +2.21 | 0.59 | 0.75 | 0.155 | -28% | 40 | 0.41 |
| GATED uninv540 & spy200 | +2.28 | +2.20 | 0.53 | 0.75 | 0.167 | -41% | 116 | 1.40 |
| GATED irx fall>1.0 252d & spy200 | +2.08 | +2.20 | 0.71 | 0.75 | 0.152 | -26% | 110 | 1.43 |
| GATED inv+after540 & spy200 | +2.06 | +2.08 | 0.53 | 0.75 | 0.204 | -41% | 144 | 2.04 |
| GATED uninv720 & spy200 | +1.97 | +1.78 | 0.59 | 0.75 | 0.230 | -27% | 115 | 1.41 |
| GATED credit HY/INT sma100 b1% & spy200 / chkM | +0.69 | +0.56 | 0.53 | 0.75 | 0.437 | -34% | 93 | 1.33 |
| GATED uninv365 & spy200 / chkM | +0.09 | +0.13 | 0.41 | 0.25 | 0.457 | -59% | 29 | 0.40 |
| GATED uninv365 & spy200b2 | -0.06 | +0.01 | 0.29 | 0.25 | 0.512 | -58% | 43 | 0.60 |
| TRENDONLY spy200b2 | -0.35 | -0.18 | 0.53 | 0.25 | 0.553 | -29% | 116 | 1.60 |
| TRENDONLY spy200 / chkM | -0.38 | -0.38 | 0.53 | 0.42 | 0.573 | -34% | 90 | 1.53 |
| GATED uninv365 & spy200 | -0.56 | -0.52 | 0.18 | 0.17 | 0.665 | -62% | 81 | 1.24 |
| GATED credit HY/INT sma100 b1% & spy200b2 | -1.23 | -1.17 | 0.41 | 0.25 | 0.716 | -43% | 107 | 1.62 |
| GATED credit HY/INT sma100 b1% & spy200 | -2.33 | -2.04 | 0.18 | 0.08 | 0.843 | -39% | 244 | 3.71 |
| TRENDONLY spy200 | -2.54 | -2.16 | 0.18 | 0.17 | 0.787 | -34% | 397 | 6.04 |


s6b, neighbourhood and implementation variants of the gated leader (protocol `screen`):

**CA**

| config | score | full | ex10 beat | ex15 beat | boot p | maxDD | trades | turnover |
|---|---|---|---|---|---|---|---|---|
| GATED uninv630 & spy200 / chkM | +4.11 | +3.48 | 0.65 | 0.83 | 0.074 | -26% | 49 | 0.61 |
| GATED uninv540 & spy200 / chkM / lag2 | +3.23 | +2.80 | 0.59 | 0.75 | 0.101 | -35% | 47 | 0.61 |
| GATED uninv540 & spy250 / chkM | +3.11 | +3.24 | 0.59 | 0.75 | 0.072 | -35% | 39 | 0.40 |
| GATED uninv540 & spy200 / chkM / safe=SHORT | +3.03 | +2.64 | 0.59 | 0.75 | 0.107 | -35% | 45 | 0.61 |
| GATED uninv540 & spy150 / chkM | +2.97 | +2.58 | 0.59 | 0.75 | 0.110 | -31% | 54 | 0.66 |
| GATED uninv540 & spy200 / chkM / checkW | +2.78 | +2.70 | 0.59 | 0.75 | 0.098 | -37% | 65 | 0.74 |
| GATED uninv540 & spy200 / chkM / core70+sleeve30(VTSMX) | +1.27 | +1.10 | 0.59 | 0.75 | 0.161 | -43% | 40 | 0.30 |
| GATED uninv540 & spy200 / chkM / exec=tax gb5% noST | +0.85 | +0.98 | 0.47 | 0.67 | 0.311 | -39% | 46 | 0.10 |
| GATED uninv450 & spy200 / chkM | +0.48 | +0.41 | 0.59 | 0.75 | 0.350 | -55% | 29 | 0.40 |


* It is the family's best design on robustness: positive with SMA 150/250, after 540/630/720, weekly
  checks, a two-day lag and a short-Treasury safe asset. It is not contradicted by the off-engine
  1962-85 check.
* It still fails the CA bar on `full`: score +3.12, full +2.80, ex10 beat 0.64, ex15 beat 0.77,
  boot p 0.101.
* It loses from 2010 and 2015 starts (-1.6 and -1.9 pp/yr in CA).
* It passes conditions 1-3 only in NONE (score +4.27, ex10 beat 0.85, ex15 beat 0.89, boot p 0.040).

## 10. Family diagnostics (`report.diagnostics`)

Walk-forward = choose the config with the best trailing excess, score it on the next window. PBO
uses combinatorially symmetric cross-validation (CSCV). DSR is the deflated Sharpe ratio of the best
config given the number of trials. Random-menu controls and the site preset are excluded.

| config set | regime | configs | WF 10y->5y OOS mean | WF beat | avg config OOS | WF 5y->3y OOS mean | WF beat | PBO | DSR of best |
|---|---|---|---|---|---|---|---|---|---|
| all_screen | CA | 449 | -3.38 | 0.00 | -3.48 | +0.82 | 0.25 | 0.081 | 0.008 |
| all_screen | FED | 449 | -3.78 | 0.00 | -3.77 | +1.06 | 0.50 | 0.115 | 0.009 |
| all_screen | NONE | 449 | -2.71 | 0.33 | -3.51 | +1.17 | 0.75 | 0.245 | 0.015 |
| uninv_screen | CA | 67 | -1.13 | 0.33 | -0.74 | +3.23 | 0.25 | 0.372 | 0.791 |
| uninv_screen | FED | 67 | -1.22 | 0.33 | -0.73 | +3.67 | 0.25 | 0.484 | 0.880 |
| uninv_screen | NONE | 67 | -1.31 | 0.33 | -0.43 | +4.16 | 0.25 | 0.600 | 0.949 |
| all_long_screen | CA | 236 | +2.22 | 0.33 | -0.79 | +1.79 | 0.50 | 0.036 | 0.024 |
| all_long_screen | NONE | 236 | +0.53 | 0.17 | -0.05 | +1.30 | 0.38 | 0.178 | 0.103 |
| fin_full | CA | 21 | -1.77 | 0.17 | -1.36 | +2.61 | 0.32 | 0.500 | 0.798 |
| fin_full | FED | 21 | -1.91 | 0.17 | -1.43 | +3.05 | 0.32 | 0.560 | 0.857 |
| fin_full | NONE | 21 | -2.66 | 0.08 | -1.23 | +2.82 | 0.42 | 0.771 | 0.940 |
| fin_long | CA | 11 | +4.15 | 0.58 | +1.90 | +2.81 | 0.33 | 0.317 | 0.497 |
| fin_long | FED | 11 | +4.82 | 0.58 | +2.31 | +3.19 | 0.36 | 0.383 | 0.699 |
| fin_long | NONE | 11 | +5.76 | 0.58 | +3.03 | +3.30 | 0.30 | 0.509 | 0.875 |

* **CA: the family's walk-forward selection is negative out of sample on the ETF-era search** (10y
  -> 5y: -3.38 pp/yr over 449 configs; the chosen config never beat SPY out of sample).
  * 5y -> 3y is +0.82, but it beat SPY in only 25% of decisions.
  * The deflated Sharpe of the best config is 0.008: it is not significant given the search.
* PBO is low (0.08 on the whole screen). Crash-dodging configs rank consistently across random month
  splits because the 2001-02 and 2008 months dominate. That shows consistency across months, not
  across events.
* **FED is the same**: 10y -> 5y walk-forward -3.78 pp/yr over 449 configs (beat 0.00), -1.22 for
  the curve sub-family; PBO 0.115 / 0.484.
* The long protocols show positive walk-forward means (selection there mostly picks long-hold curve
  rules that paid off in 2001/2008 out of sample). The beat rates are 0.17-0.58.
* PROTOCOL condition 4 is not met in CA or FED.
* Caveat on this tool: on the `screen` protocol (annual starts) `walk_forward(step_quarters=4)`
  steps four *starts*, i.e. four years. That leaves only 3 (10y->5y) or 4 (5y->3y) decision
  points, so these estimates are coarse; on `full`/`long` it steps one year.

## 11. Representative failures

* **Commodity trend** (DBC/GSG vs SMA200, in either direction): best CA score -4.25 pp/yr, median
  -6.98. **Copper/gold**: best -4.56, median -5.77.
* **Breakeven inflation** (TIP/IEF, VIPSX): best -2.52, median -5.47.
* **Risk-appetite ratios** (XLY/XLP, XLI/XLU, IWM/SPY, cyclicals/defensives): every CA config
  negative; the long-history versions are the worst group (-2.8 to -5.2).
* **Sector breadth** and **gold/stocks**: negative in CA in every variant.
* **Inverted-curve level rule** (out while inverted): negative in every CA variant and on the NONE
  screen. It exits 6-18 months before the peak.
* **T-bill momentum** (out when the Fed has cut more than 1 pp in 12 months): CA full +1.42 on
  `full`, but -0.80 from 1986 and a negative pre-2000 holdout (-2.32 pp/yr over 10 years).
* **Pre-registered composite (COMP5 vote3)**: CA score -0.82 on `full`, -0.41 on `long` (full
  excess -2.66 from 1986).
* **Credit-spread rules** (high-yield bond fund / Treasury fund ratio): good in NONE but taxed away
  in CA (100-250 trades); the HYG/JNK/LQD ETF versions are worse.

## 12. Conclusion

**CA: no macro or cross-asset regime signal passes.** The only robust effect is that a curve
un-inversion has preceded the two big ETF-era bear markets. The site's numbers reward it
(+2.8 to +3.8 pp/yr full-period in CA for the best configs, with drawdowns of -30 to -35% against
SPY's -55%).
But:

* it rests on two events;
* it lost money after 2009;
* it fails the beat-rate bar;
* the family's walk-forward selection is negative out of sample in CA;
* the long-hold versions are contradicted by 1962-85.

The best-founded version is the macro-gated trend rule (`GATED uninv540 & spy200 | chkM`). Treat it
as **crash insurance with a cost**, not as a way to beat SPY:

* CA maximum drawdown -35% vs SPY's -55%;
* it beat SPY in 64% of 10-year windows;
* it is behind SPY from 2010 and 2015 starts.

**FED:** the short-hold rule passes conditions 1-3 on `full`: after150 has score +1.00, boot p
0.021; after180 has +0.74, 0.096. It is still not good confidence:
* It fails condition 3 on the 1986-2026 long protocol (boot p 0.136 / 0.326).
* The family's walk-forward is negative (condition 4).
* The passing region is a narrow spike (condition 5). On the FED screen all 12 passing configs
  are after150-180 with default settings, or their lag / check / execution variants. after120,
  after240, curve thresholds of +0.1 and +0.25, min_len 0, confirm 1 or 20, delays, and the
  5y-3m / 30y-3m curves all fail.

**NONE** (diagnostic): the gated rule and the short-hold curve rules pass conditions 1-3 on `full`.
The family-level walk-forward is negative there too (-2.71 pp/yr on the screen, 10y -> 5y).

**Incumbent:** a macro overlay does not improve the site preset's momentum rotation after tax.

Caveats:

* ^IRX is a discount-basis yield, so the slope differs slightly from the Treasury constant-maturity
  10y-3m spread. The proxy registers no 1989 inversion.
* The four un-inversion dates are this proxy's.
* Results use total-return fund prices; the realism check covers distribution taxation.

## 13. Files

* `research/lab/families/macro_regime.py`: the signal (v2 adds `risk_signal`; old configs verified
  identical).
* `research/lab/scratch/macro_regime/`:
  * `grid.py` (stages s1-s3, s1L, s2L) and `grid2.py` (s4, s5, s6, s6b, finalists);
  * `run_stage.py` and the `*_cfgs.json` config lists;
  * `records_archive.jsonl` (all module-v1 records);
  * `diag_*.json`, `cand_stats.json`, `rm_analysis.json`, `realism.json`, `subperiods.json`;
  * `pre1986_*.py/csv` and `uninv_events.py` (off-engine studies).
* `research/lab/results/macro_regime_table.csv`: `report.table` rows for every config x regime x
  protocol run (column `protocol`, plus `stage` and the exact `cfg_json`).
