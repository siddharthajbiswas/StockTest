# Market timing / trend following on broad US equity (family `trend_timing`)

The question is whether any rule that switches between broad US equity and a
safe asset beats buying and holding SPY. The test is after California tax (48.1%
short-term, 28.1% long-term) and the site's trading costs, and the bar is good
confidence. FED (35/15) is secondary and NONE (no tax) is a diagnostic only.

Every number below comes from the lab (`research/lab`). The lab is the site's
engine, with 5 bps commission plus 5 bps slippage per side. All numbers can be
reproduced from the scripts in `research/lab/scratch/trend_timing/`. "Excess" is
after-tax CAGR minus SPY's, in percentage points per year (pp). "Score" is the
pre-registered `report.score`: the mean of the average 5-, 10- and 15-year
window excess.

This report resumes an interrupted run. The first researcher built the module
and finished the coarse screen (about 500 configs × CA/NONE). Everything else
was done in this session: the full-protocol finalists, execution/tax variants,
neighbourhoods, long history and holdout, hindsight checks, leverage, the new
inverse-ETF hedge, diagnostics, and this write-up. Nothing earlier was
discarded. The family module `research/lab/families/trend_timing.py` was not
edited, so every cached result is still valid.

## 1. Verdict

**No unlevered timing rule beats SPY after California tax with good
confidence. The result is a clean negative.**

* **Screen (2000-2026):** 662 unlevered SPY timing configs were screened. 90
  have a positive CA score, and the best is +1.23 pp. None reaches a 10-year
  beat rate of 0.75; the highest is 0.53. None reaches bootstrap p ≤ 0.10; the
  lowest is 0.285. In NONE the picture is the same: the highest 10-year beat
  rate is 0.59 and the lowest p is 0.144.
* **Best after-tax config (CA, `full`):** EMA(100) crossing EMA(200) with a 1%
  band, switching SPY to intermediate Treasuries (IEF; VFITX before IEF existed):
  * score +1.01 pp and full-period excess +1.36 pp;
  * 10-year beat rate 0.57 (bar 0.75), 15-year 0.74 (bar 0.85), p = 0.29 (bar 0.10);
  * the 1986-1999 holdout contradicts it: 10-year windows ending before 2000
    lose 2.8 pp/yr, and 0% of them beat VFINX;
  * the family's walk-forward is negative out of sample (−1.9 pp/yr), and PBO is 0.69.
* **The whole edge is two bear markets.** Across all 662 screened SPY rules in
  CA, the mean excess of 10-year windows starting 2000-2008 is +1.65 pp/yr.
  For windows starting 2009-2016 it is −4.76 pp/yr. **Not one config beat SPY
  in any 10-year window starting in 2009 or later.** The leader made 6
  switches in 26 years: out Dec 2000–Jul 2003, out Feb 2008–Sep 2009, and out
  Jun 2022–Jun 2023.
* **Drawdown reduction is real, but you pay for it in the wrong decade.**
  Timing cuts SPY's −55% max drawdown to −27% to −43% at roughly zero average
  CA cost over 2000-2026. In 10-year windows starting 2009-2016, though, the
  same rules lose 1 to 5 pp/yr (−3.2 to −3.7 for the low-drawdown ones). A
  never-rebalanced 70/30 SPY/IEF mix gets a −29% drawdown and a better Sharpe
  (0.67 vs 0.60-0.64) at a steady −1.1 pp/yr, or −2.2 pp/yr in the same
  post-2009 windows.
* **Tax-aware exits do not rescue timing.** Selling only long-term or losing
  lots moves CA scores by −0.6 to +0.3 pp. Partial "base" exposure and
  wash-sale handling change little. Gain budgets hurt (−0.6 to −2.1 pp),
  because they block the very exits the rule depends on.
* **Long history (1986-2026, VFINX):** all 35 unlevered timing configs lose to
  VFINX over the full period after CA tax. All of them lose on average in
  both the 5-year and 10-year pre-2000 holdout windows.
* **The only family members that clear items 1-3 in CA are LEVERAGED (flagged).**
  The rule holds a 2x S&P fund (SSO, or the cost-calibrated synthetic
  SYN_SPY2XC / SYN_VFINX2XC) while the same slow EMA trend is up, and bonds or
  bills otherwise:
  * real SSO, 2006-2026: score +6.34, excess +5.94, 10-year beat 1.00, p = 0.034;
  * synthetic, 2000-2026: score +6.17, p = 0.020;
  * synthetic 1986-2026 holdout: 10-year windows ending before 2000 +1.80 pp/yr,
    60% beat.

  It carries 1.6x SPY's volatility and a −59% max drawdown (SPY −55%). Its
  Sharpe is about SPY's: 0.65 vs 0.65 over 2006-2026, 0.57 vs 0.51 over
  2000-2026, 0.59 vs 0.67 over 1986-2026. It fails item 4 narrowly (PBO 0.53).
  This is mostly a bet on more risk, not timing skill. It overlaps the
  `leverage` family's result, which reaches the same "close but no" verdict.

## 2. What was tested

875 distinct configs and 1,868 config × regime × protocol runs:

| protocol | configs | runs |
|---|---:|---:|
| `screen` (Jan starts 2000-2023), CA + NONE | 809 | 1,616 |
| `full` (quarterly starts 2000-2023), CA + FED + NONE | 40 | 120 |
| `long_screen` (Jan starts 1986-2023, VFINX benchmark), CA + NONE | 57 | 114 |
| `long` (quarterly starts 1986-2023), CA + FED + NONE | 6 | 18 |

The family is one signal, `trend_timing.timing`. It holds a risk asset while a
rule is on and a safe asset, or a fallback chain of them, while it is off. A
second kind, `trend_timing.taxaware`, exits by selling only long-term or
losing lots.

* **Rules:**
  * price vs SMA(n), n ∈ {50, 100, 125, 150, 175, 200, 250, 300};
  * price vs EMA, SMA/EMA crosses, and the Faber monthly SMA (3-12 months);
  * time-series momentum over 1-18 months, vs zero, T-bills or bond returns;
  * Donchian channels, MACD, and drawdown or volatility crash filters;
  * enter-on-one/exit-on-another pairs, and stocks/bonds relative strength;
  * ensembles (mean, vote, any, all) and exposure ladders.
* **Rule options:**
  * hysteresis bands of 0-5%, symmetric or asymmetric;
  * confirmation delays of 1-10 days, symmetric or asymmetric;
  * daily, weekly or monthly evaluation;
  * a 1-bar execution lag;
  * signal read on SPY's total return or on the ^GSPC price index.
* **Safe assets:**
  * cash, BIL, SHY, IEF, TLT, AGG and GLD;
  * Vanguard/Fidelity fund chains before the ETFs existed;
  * a trend switch on the safe side: bonds only while bonds trend up, else bills.
* **Risk assets:**
  * SPY, VTI, RSP;
  * QQQ, flagged as hindsight;
  * SSO, UPRO and SPY+SSO mixes, flagged as leverage;
  * synthetic 2x S&P, flagged as leverage and synthetic;
  * 24 random equity ETFs, for the PROTOCOL 5.3 hindsight check.
* **Execution:**
  * standard execution, or the lab's `"tax"` rule with 2%, 5% or 100% gain
    budgets, with or without short-term gains;
  * tax-aware exits: hold short-term-gain lots, or sell short-term lots only if
    the gain is under 5%;
  * 25% or 50% permanent base exposure;
  * wash-sale handling: re-enter via VTI, or wait 31 days.
* **New angle:** an inverse-ETF hedge (keep half the SPY and buy SH) instead of
  selling.
* **Controls:** static SPY/IEF mixes at 80/20, 70/30 and 60/40, both
  annually rebalanced and never rebalanced.

### Screen landscape (score, pp; `screen` protocol)

| block | what | configs | CA best | CA median | CA share>0 | NONE best | NONE median | NONE share>0 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A | price vs SMA(n): bands, confirmation, D/W/M (-> IEF chain) | 197 | +0.39 | -1.12 | 0.04 | +1.81 | -0.52 | 0.35 |
| A2 | price vs SMA -> cash | 42 | -1.05 | -2.00 | 0.00 | -0.53 | -1.76 | 0.00 |
| A3 | asymmetric hysteresis bands | 18 | -0.20 | -1.08 | 0.00 | +1.02 | -0.35 | 0.39 |
| B | MA crosses (SMA/EMA, bands) | 65 | +1.09 | -0.81 | 0.14 | +1.97 | -0.08 | 0.45 |
| C | price vs EMA | 36 | -0.55 | -1.59 | 0.00 | +0.38 | -1.03 | 0.11 |
| D | Faber monthly SMA (k months, bands) | 27 | +0.63 | -0.88 | 0.11 | +2.28 | +0.35 | 0.59 |
| E | time-series momentum (1-18 m; zero/T-bill/bond hurdle; D/W/M) | 60 | -0.07 | -1.85 | 0.00 | +0.66 | -1.47 | 0.08 |
| F | Donchian channels | 13 | -1.04 | -2.73 | 0.00 | -0.46 | -2.23 | 0.00 |
| G | MACD | 6 | -0.51 | -5.77 | 0.00 | +0.58 | -5.72 | 0.17 |
| H | ensembles (mean/vote/any/all) | 24 | +0.10 | -1.31 | 0.04 | +0.79 | -0.57 | 0.21 |
| I | crash/vol filters (SMA + drawdown or vol) | 18 | -0.09 | -1.56 | 0.00 | +0.98 | -1.23 | 0.11 |
| M | signal on ^GSPC price index | 5 | +0.33 | -1.93 | 0.20 | +2.08 | -1.74 | 0.20 |
| P | pair rules (enter on one rule, exit on another) | 4 | -0.34 | -1.24 | 0.00 | +1.12 | -0.36 | 0.25 |
| Q | safe-side trend switch | 7 | +0.60 | -0.31 | 0.43 | +2.08 | +0.36 | 0.50 |
| R | stocks-vs-bonds relative strength as signal | 5 | -1.85 | -4.13 | 0.00 | -0.94 | -2.08 | 0.00 |
| S | asymmetric confirmation delays | 4 | -0.53 | -1.05 | 0.00 | +0.21 | -0.44 | 0.25 |
| T | exposure ladders (partial exposure) | 6 | -2.27 | -3.22 | 0.00 | -2.01 | -2.75 | 0.00 |
| NB | fine neighbourhoods of the three leaders | 45 | +1.23 | +0.31 | 0.64 | +2.98 | +1.25 | 0.84 |
| L, L2, LV, S1bt | execution/tax variants of classic rules and leaders | 61 | +1.15 | -0.01 | 0.49 | +2.68 | +1.35 | 0.84 |
| J | safe-asset sweep | 11 | +0.02 | -1.10 | 0.09 | +1.25 | -0.20 | 0.36 |
| SHH | NEW inverse-ETF (SH) hedge, windows from 2007 | 13 | 0.00 | -2.11 | 0.00 | 0.00 | -2.63 | 0.00 |
| CTRL | static SPY/IEF mixes | 6 | -0.63 | -1.10 | 0.00 | -0.74 | -1.24 | 0.00 |
| K, S3t, S4x | other risk assets (VTI/RSP/QQQ; mixed with safe-asset and leverage variants of leaders) | 40 | +6.28 | -0.06 | 0.45 | +7.47 | +1.00 | 0.72 |
| N, U, S5, F4 | leveraged: SSO/UPRO real and synthetic 2x (flagged) | 26 | +13.53 | +3.72 | 0.88 | +14.94 | +6.11 | 0.96 |
| HS | 24 random equity ETFs: timed vs buy-and-hold (PROTOCOL 5.3) | 70 | +4.40 | -1.91 | 0.20 | +4.96 | -1.08 | 0.31 |

Notes on the table:

* The share > 0 of the neighbourhood (NB) and execution blocks is high only
  because those blocks were built around the leaders.
* The "SHH" best of 0.00 is its aligned SPY buy-and-hold control.
* "N" includes plain leveraged buy-and-hold, with windows starting 2010 for UPRO.

## 3. Unlevered timing in detail

### 3.1 Finalists on the `full` protocol (95 quarterly starts, 2000-2026; SPY: after-tax CAGR 7.10% CA, max DD −55.2%, Sharpe 0.51)

All configs below are SPY timing rules. "-> X" is the safe asset, with
VFITX/VFISX standing in before IEF/SHY launched in 2002 and BIL in 2007.
Columns are in pp except the beat rates, p, Sharpe and trades.

| CA | score | full excess | ex10 mean | ex10 beat | ex10 min | ex15 beat | ex20 beat | boot p | max DD | Sharpe | trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EMA100/225 cross, 1% band, D -> IEF | +1.06 | +1.35 | +1.11 | 0.54 | −2.87 | 0.74 | 0.52 | 0.29 | −42.7 | 0.62 | 25 |
| **EMA100/200 cross, 1% band, D -> IEF** | **+1.01** | **+1.36** | +1.03 | 0.57 | −3.23 | 0.74 | 0.59 | 0.29 | −40.4 | 0.62 | 25 |
| Faber 7-month SMA, 1% band, M -> IEF | +0.85 | +0.71 | +0.94 | 0.55 | −4.50 | 0.74 | 0.44 | 0.41 | −30.8 | 0.65 | 96 |
| EMA100/200, 1% band -> bills (BIL>SHY>VFISX) | +0.73 | +1.07 | +0.74 | 0.55 | −2.85 | 0.70 | 0.52 | 0.33 | −38.0 | 0.62 | 27 |
| SMA100/250 cross, 1% band -> IEF | +0.49 | +1.00 | +0.51 | 0.52 | −4.57 | 0.68 | 0.41 | 0.38 | −36.4 | 0.62 | 57 |
| SMA100, 5% band, tax-aware exit (hold ST-gain lots) | +0.45 | +0.44 | +0.58 | 0.54 | −5.26 | 0.70 | 0.41 | 0.47 | −30.5 | 0.63 | 66 |
| EMA100/200, 1% band -> cash | +0.44 | +0.44 | +0.48 | 0.52 | −2.83 | 0.70 | 0.41 | 0.44 | −40.0 | 0.58 | 7 |
| EMA20/100 cross, 2% band -> IEF | +0.36 | +0.76 | +0.40 | 0.54 | −5.27 | 0.62 | 0.41 | 0.42 | −32.7 | 0.65 | 69 |
| Faber 8-month, 1% band -> IEF | +0.32 | +0.33 | +0.33 | 0.54 | −5.13 | 0.68 | 0.41 | 0.47 | −32.8 | 0.63 | 94 |
| SMA300, 1% band, 5-day confirm -> IEF | +0.21 | +1.03 | +0.15 | 0.52 | −5.49 | 0.49 | 0.41 | 0.38 | −26.7 | 0.64 | 66 |
| SMA100, 5% band -> IEF | +0.15 | −0.26 | +0.29 | 0.52 | −5.60 | 0.70 | 0.41 | 0.58 | −30.9 | 0.59 | 92 |
| SMA150, 4% band -> IEF | +0.13 | −0.15 | +0.26 | 0.54 | −5.92 | 0.68 | 0.41 | 0.55 | −29.5 | 0.60 | 86 |
| SMA200, 3% band -> IEF | −0.35 | +0.02 | −0.33 | 0.52 | −5.64 | 0.34 | 0.30 | 0.53 | −31.1 | 0.62 | 79 |
| golden cross SMA50/200 -> IEF | −0.70 | −0.08 | −0.71 | 0.51 | −6.55 | 0.30 | 0.22 | 0.54 | −33.7 | 0.56 | 82 |
| SMA150, 4% band -> bills | −0.77 | −0.84 | −0.73 | 0.52 | −5.39 | 0.30 | 0.19 | 0.65 | −22.4 | 0.57 | 78 |
| 12-month TSMOM vs T-bills, M -> IEF | −0.98 | −0.12 | −0.99 | 0.51 | −6.72 | 0.32 | 0.22 | 0.54 | −36.7 | 0.56 | 64 |
| SMA150, 4% band -> cash | −1.01 | −1.42 | −0.94 | 0.51 | −5.55 | 0.30 | 0.15 | 0.74 | −23.0 | 0.53 | 39 |
| Faber 10-month SMA, M -> IEF | −1.37 | −0.96 | −1.39 | 0.49 | −7.76 | 0.26 | 0.22 | 0.64 | −34.3 | 0.53 | 102 |
| 200-day SMA, daily, no band -> IEF | −2.57 | −2.38 | −2.53 | 0.13 | −7.07 | 0.09 | 0.04 | 0.80 | −33.1 | 0.46 | 400 |
| *control:* buy-and-hold SPY 80 / VFITX 20 | −0.68 | −0.54 | −0.66 | 0.16 | −1.67 | 0.09 | 0.04 | 0.69 | −37.1 | 0.61 | 2 |
| *control:* buy-and-hold SPY 70 / VFITX 30 | −1.06 | −0.83 | −1.04 | 0.16 | −2.59 | 0.09 | 0.04 | 0.71 | −28.9 | 0.67 | 2 |
| *control:* buy-and-hold SPY 60 / VFITX 40 | −1.48 | −1.15 | −1.45 | 0.16 | −3.59 | 0.09 | 0.04 | 0.73 | −21.6 | 0.74 | 2 |
| *control:* 70/30 rebalanced annually | −1.29 | −1.00 | −1.28 | 0.16 | −3.97 | 0.15 | 0.11 | 0.77 | −37.9 | 0.60 | 54 |

FED and NONE scores for the same configs, in pp:

| config | CA | FED | NONE | p (FED / NONE) |
|---|---:|---:|---:|---|
| EMA100/225, 1% band | +1.06 | +1.30 | +1.61 | 0.23 / 0.16 |
| EMA100/200, 1% band | +1.01 | +1.24 | +1.53 | 0.23 / 0.16 |
| Faber 7-month, 1% band | +0.85 | +1.43 | +2.71 | 0.32 / 0.16 |
| Faber 8-month, 1% band | +0.32 | +0.83 | +2.15 | 0.37 / 0.18 |
| SMA150, 4% band | +0.13 | +0.55 | +1.49 | 0.46 / 0.31 |
| SMA300, 1% band, k5 | +0.21 | +0.57 | +1.23 | 0.29 / 0.18 |
| Faber 10-month | −1.37 | −1.18 | −0.56 | 0.57 / 0.45 |
| 200-day SMA | −2.57 | −2.61 | −2.22 | 0.77 / 0.70 |

**No config passes items 1-3 in any regime.** The highest 10-year beat rate
is 0.57 and the lowest p is 0.153 (NONE). The 10-year beat rates cluster at
0.52-0.57 because nearly every rule wins every 10-year window that contains
2000-02 or 2008 and loses every other one. The gap between NONE and CA is the
tax drag of realized gains. It is 0.5 pp/yr for the rarely-switching EMA cross
and about 1.4 pp/yr for SMA150 b4% (13 round trips).

### 3.2 Why it fails: the edge is two slow bear markets

Sub-period excess (CA, pp/yr) and 10-year windows by start year (`full`):

| config | 2000-10 | 2010-20 | 2020-26 | ex10, starts 2000-08 | ex10, starts 2009-16 | beat10 2000-08 | beat10 2009-16 |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA100/200, 1% band -> IEF | +5.63 | 0.00 | −2.38 | +2.79 | −1.02 | 1.00 | 0.06 |
| EMA100/200, 1% band -> bills | +4.64 | 0.00 | −2.08 | +2.13 | −0.88 | 1.00 | 0.03 |
| SMA150, 4% band -> IEF | +7.07 | −2.51 | −7.16 | +3.68 | −3.72 | 1.00 | 0.00 |
| SMA300, 1% band, k5 -> IEF | +7.81 | −2.87 | −2.82 | +3.02 | −3.17 | 0.97 | 0.00 |
| Faber 7-month, 1% band | +7.82 | −2.62 | −4.83 | +4.23 | −2.87 | 1.00 | 0.03 |
| Faber 10-month | +7.98 | −5.92 | −5.83 | +2.10 | −5.43 | 0.92 | 0.00 |
| 200-day SMA, daily | +3.18 | −5.34 | −5.47 | −0.78 | −4.56 | 0.25 | 0.00 |
| buy-and-hold 70/30 control | +2.38 | −1.96 | −2.75 | −0.09 | −2.15 | 0.31 | 0.00 |
| (incumbent "Beat the S&P (CA)", for reference) | +1.20 | −0.55 | +0.19 | | | | |

The same pattern holds across the whole screened family: 662 unlevered SPY
configs, CA, `screen`:

* 10-year windows starting 2000-2008: mean excess +1.65 pp/yr, and 85% of
  configs are positive.
* 10-year windows starting 2009-2016: mean excess −4.76 pp/yr. **0 of 662
  configs beat SPY in any of those windows.**
* 5-year windows starting 2009 or later: mean −4.41 pp/yr, with a beat rate of
  0.7%.

The best rule, EMA100/200 with a 1% band, was out of the market three times
in 26.5 years: Dec 2000–Jul 2003, Feb 2008–Sep 2009 and Jun 2022–Jun 2023. Its
2010-2020 excess is exactly 0 because it never traded in that decade. Its whole
record is three events.

### 3.3 Tax-aware execution (CA score, pp, `screen`)

| rule | plain | TA: hold ST lots | TA: ST < 5% | wash: wait 31d | wash: re-enter via VTI | tax 5% budget, no ST | tax 100% budget, no ST | base 50% + 5% band | lag 1 bar | signal on ^GSPC | bonds-trend switch |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EMA100/200, 1% band, D | +1.15 | +1.15 | | | | +0.52 | | | +1.13 | | +0.91 |
| SMA100/250, 1% band, D | +0.64 | +0.64 | | | | −0.51 | | | +0.30 | | +0.54 |
| Faber 8-month, 1% band, M | +0.56 | +0.36 | | | | −1.57 | | | −1.36* | | +0.76 |
| SMA100, 5% band, D | +0.36 | +0.62 | −0.14 | | | −0.99 | −0.20 | +0.30 | +0.62 | +0.47 | |
| SMA150, 4% band, D | +0.35 | +0.27 | +0.35 | | | −1.03 | −0.57 | +0.31 | +0.63 | +0.50 | +0.50 |
| SMA200, 4% band, D | +0.01 | +0.09 | +0.30 | | | −1.35 | −1.18 | +0.22 | +0.03 | +0.02 | |
| SMA200, 3% band, D | −0.09 | −0.31 | | −0.09 | −0.09 | −1.26 | | −0.01 | | | +0.01 |
| Faber 10-month, M | −1.11 | −1.71 | | −1.14 | −1.15 | −1.32 | | −0.48 | | | −1.11 |

\* For month-end rules, `lag=1` means the rule reads month-end closes as of the
day before the first trading day of the month. That is a one-**month**
evaluation delay, not one day. Faber 8m's collapse from +0.56 to −1.36 under a
one-month shift says its result depends on the exact evaluation date.

* **Slow rules barely notice tax-aware exits.** They realize mostly long-term
  gains anyway, so "hold short-term lots" rarely binds.
* **For faster rules, keeping short-term lots means keeping exposure** in the
  very sell-off the rule is trying to avoid.
* **Gain budgets are the worst variant.** They block the exits outright.
* **Wash-sale handling changes nothing.** Waiting 31 days or re-entering via
  VTI after a loss sale gives the same result, so the engine's lack of
  wash-sale enforcement does not flatter these rules.

### 3.4 Safe asset: the Treasury "star" (CA score, pp, `screen`; cash/bills for EMA100/200 from `full`)

| rule | IEF | TLT | AGG | SHY | BIL | GLD | cash |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA100/200, 1% band | +1.15 | +1.08 | +1.16 | +0.96 | (full +0.73) | +0.73 | (full +0.44) |
| SMA150, 4% band | +0.35 | +0.22 | −0.16 | −0.40 | (full −0.77) | −0.04 | (full −1.01) |
| SMA200, 3% band | −0.09 | −0.33 | −0.43 | −0.68 | −0.88 | +0.02 | −1.18 |
| Faber 10-month | −1.11 | −1.14 | −1.28 | −1.59 | −1.77 | −1.10 | −1.99 |
| 200-day SMA, daily | −2.40 | | | | | | −2.75 |

Holding intermediate Treasuries while out contributes 0.6-1.1 pp/yr of every
timing result (IEF vs cash). From 2000 to 2020 Treasuries rallied in every
equity crash. That is a regime, not a law: in 2022 stocks and bonds fell
together. With bills or cash instead, the classic rules lose clearly. GLD as
the safe asset (cash before 2004) is no better than IEF on balance.

### 3.5 Long history, 1986-2026, and the pre-2000 holdout (VFINX benchmark; Vanguard/Fidelity fund proxies)

`long` protocol (151 quarterly starts):

| config | CA score | CA full excess | ex10 beat | 5-yr windows ending ≤ 2000 (beat) | 10-yr windows ending ≤ 2000 (beat) | p | max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA100/200, 1% band -> VFITX>FGOVX | +1.15 | −0.92 | 0.59 | −2.31 (0.00) | −2.78 (0.00) | 0.72 | −40.2 |
| same -> bills (VFISX>VWSTX) | +0.88 | −1.15 | 0.59 | −2.61 (0.00) | −3.09 (0.00) | 0.78 | −40.2 |
| SMA300, 1% band, k5 | +0.77 | −1.17 | 0.55 | −1.41 (0.00) | −1.76 (0.00) | 0.75 | −33.1 |
| SMA150, 4% band | +0.23 | −2.15 | 0.54 | −2.04 (0.11) | −2.65 (0.00) | 0.86 | −27.1 |
| Faber 10-month | −0.65 | −3.32 | 0.52 | −3.54 (0.00) | −4.24 (0.00) | 0.94 | −33.9 |
| buy-and-hold VFINX 70 / FGOVX 30 | −0.98 | −0.86 | 0.14 | −1.58 (0.03) | −1.64 (0.00) | 0.95 | −45.3 |

The `long_screen` protocol (38 January starts) covers all 35 unlevered VFINX
timing configs: the SMA n × band grid, EMA and SMA crosses, Faber 7/8/10,
TSMOM, safe-asset variants, tax-aware exits and the ^GSPC signal.

* **CA:** full-period excess is negative for **35 of 35**, ranging from −0.9 to
  −6.0 pp/yr. Mean excess is negative in both the pre-2000 5-year and 10-year
  windows for **35 of 35**. The highest pre-2000 10-year beat rate is 0.00.
* **NONE:** 12 of 35 have a positive full-period excess, but every one is
  negative in both pre-2000 holdout window lengths.

The 1986-1999 market had the 1987 crash and the 1990 bear. Timing still lost
to buy-and-hold there, so the holdout contradicts the ETF-era leaders
(item 7).

### 3.6 Drawdown bought vs its cost (CA, `full`)

| strategy | max DD | score | full excess | Sharpe | vol | ex10, starts 2000-08 | ex10, starts 2009-16 |
|---|---:|---:|---:|---:|---:|---:|---:|
| SPY buy-and-hold | −55.2 | 0 | 0 | 0.51 | 19.3% | 0 | 0 |
| timing: SMA300, 1% band, k5 -> IEF | −26.7 | +0.21 | +1.03 | 0.64 | 14.3% | +3.02 | −3.17 |
| timing: SMA150, 4% band -> IEF | −29.5 | +0.13 | −0.15 | 0.60 | 13.0% | +3.68 | −3.72 |
| timing: SMA150, 4% band -> bills | −22.4 | −0.77 | −0.84 | 0.57 | 12.4% | +1.96 | −3.85 |
| timing: EMA100/200, 1% band -> IEF | −40.4 | +1.01 | +1.36 | 0.62 | 15.9% | +2.79 | −1.02 |
| static: buy-and-hold 70/30 SPY/VFITX | −28.9 | −1.06 | −0.83 | 0.67 | 11.7% | −0.09 | −2.15 |
| static: buy-and-hold 60/40 SPY/VFITX | −21.6 | −1.48 | −1.15 | 0.74 | 9.9% | −0.14 | −2.96 |
| static: 70/30 rebalanced annually | −37.9 | −1.29 | −1.00 | 0.60 | 12.6% | +0.16 | −2.96 |

* **Timing roughly halves SPY's drawdown at about zero average cost in this
  sample.** The cost is a regime bet: +3 to +4 pp/yr in decades with a slow
  bear, −3 to −4 pp/yr in decades without one.
* **A static, never-rebalanced SPY/Treasury mix buys the same drawdown more
  reliably and with a better Sharpe.** Its cost is −1 to −1.5 pp/yr.
* Over 1986-2026 (`long`) the static 70/30 mix was less costly (−0.86 pp/yr
  full period) than every timing rule on that protocol (−0.9 to −3.3 pp/yr).

### 3.7 Robustness and hindsight

* **Neighbourhoods (CA, `screen`):**
  * EMA crosses form a plateau of 0.0 to +1.2 at fast 100 vs slow 150-250
    with 1-2% bands, and at fast 120 with any 0.5-1.5% band. They turn
    negative at fast 20-80 (the one exception is 80/225 with 1.5%, +0.91),
    and at fast 100 with a band under 1%.
  * Faber: k = 6 is positive only with 2-3% bands, and k = 7-8 only with
    bands ≤ 1-1.5%. k = 9, 10 and 12 are negative.
  * SMA: n = 125-175 with 3.5-4.5% bands gives −0.6 to +0.5 (8 of 9 positive).

  Every member fails items 2-3, so no neighbourhood passes.
* **Execution delay:** a 1-day lag leaves the daily leaders intact
  (EMA100/200: 1.15 to 1.13). Reading the signal on ^GSPC instead of SPY's
  total return gives similar numbers (SMA150 b4%: 0.35 to 0.50).
* **Random menus (PROTOCOL 5.3):** the timing rule was applied to 24 random
  ETFs from `BROAD_EQUITY_POOL_2003`, with the signal on the ETF itself and
  the IEF chain as safe asset, and compared with that ETF's own buy-and-hold.
  The "add-on" below is timed score minus buy-and-hold score; max DD figures
  are medians.

  | rule | regime | mean add-on, pp | median add-on, pp | positive for | max DD timed | max DD buy-and-hold |
  |---|---|---:|---:|---:|---:|---:|
  | SMA150, 4% band | CA | −0.65 | −0.77 | 33% | −34% | −61% |
  | SMA150, 4% band | NONE | +0.50 | +0.34 | 58% | | |
  | Faber 10-month | CA | −1.42 | | 17% | −36% | −61% |
  | Faber 10-month | NONE | −0.66 | | 21% | | |

  Timing helped the ETFs that crashed and never recovered (EWQ, EWK, EZU, EWY,
  EWJ: +0.5 to +2.3). It hurt the ones that trended up (SMH, XLK, SOXX, IJT:
  −2.7 to −3.4). It is crash insurance, not a free lunch.
* **Other risk assets:**
  * VTI and RSP timed: −3.8 to +0.6 in CA. The only positive is VTI with the
    EMA rule read on SPY.
  * QQQ timed (hindsight-flagged): −0.2 to +3.6 in CA, but QQQ buy-and-hold
    itself scores +2.8 to +3.4. Timing mostly trims QQQ's −83% drawdown to
    −34% to −53%. A QQQ result is a hindsight bet on QQQ (PROTOCOL 5.3) and
    does not count.
* **Negative in CA in every variant tried** (`screen`): MACD (−0.5 to −7.7),
  Donchian, exposure ladders, pair rules, asymmetric delays, crash/vol
  filters, and stocks/bonds relative strength.

### 3.8 Family diagnostics (`report.diagnostics`, screened unlevered SPY family, first start 2000-01)

| | CA (665 configs) | NONE (663 configs) |
|---|---:|---:|
| walk-forward 10y in-sample / 5y out-of-sample: mean out-of-sample excess (beat) | −1.89 pp (0/3) | −4.89 pp (0/3) |
| winner's in-sample excess | +3.54 pp | +5.58 pp |
| walk-forward 5y / 3y: mean out-of-sample excess (beat) | +1.86 pp (1/4) | +2.00 pp (1/4) |
| PBO (CSCV) | **0.69** | **0.62** |
| in-sample best → out-of-sample (share of splits positive) | +2.28 → −1.49 pp (27%) | +3.80 → −0.41 pp (43%) |
| deflated Sharpe of best config | 0.11 | 0.16 |

The 5y/3y walk-forward is positive only because of the one 2008 decision. That
decision picked a crash-dodger in Jan 2008 and gained +11.4 pp/yr over
2008-2010; the other three decisions returned −4.0, 0.0 and 0.0. Item 4 fails
clearly.

## 4. Leveraged timing (FLAGGED: leverage, plus synthetic data before 2006)

The same slow trend switch is applied to a 2x daily S&P fund: SSO (real,
launched 2006-06), or the leverage family's cost-calibrated synthetic
SYN_SPY2XC (1993) and SYN_VFINX2XC (1980). Those synthetics are daily-reset 2x,
minus T-bill financing, minus 0.6%/yr swap spread, minus 0.9%/yr expense. The
signal is read on SPY or VFINX.

| CA | windows from | score | full excess | ex10 beat (min) | ex15 beat | boot p | max DD | vol | Sharpe (SPY's) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **SSO, EMA100/200, 1% band -> IEF** | 2006-07 | **+6.34** | **+5.94** | 1.00 (+2.62) | 1.00 | **0.034** | −59.3 | 31.9% | 0.65 (0.65) |
| SSO, EMA100/200, 1% band -> bills | 2006-07 | +6.32 | +5.84 | 1.00 (+2.87) | 1.00 | 0.026 | −59.3 | | 0.65 |
| SSO, SMA300, 1% band, k5 -> IEF | 2006-07 | +3.08 | +3.72 | 0.98 (−0.05) | 1.00 | 0.107 | −48.2 | | 0.61 |
| SSO, SMA150, 4% band -> IEF | 2006-07 | +3.42 | +2.97 | 0.76 (−1.67) | 0.95 | 0.183 | −44.8 | 24.8% | 0.62 |
| *control:* buy-and-hold SPY 50 / SSO 50 | 2006-07 | +3.39 | +2.35 | 1.00 (+0.09) | 1.00 | 0.111 | −70.8 | 28.5% | 0.59 |
| synthetic 2x, EMA100/200, 1% band -> IEF | 2000-01 | +6.17 | +5.59 | 1.00 (+2.67) | 1.00 | 0.020 | −59.2 | 30.3% | 0.57 (0.51) |
| synthetic 2x, EMA100/150, 1% band | 2000-01 | +6.01 | +5.35 | 1.00 | 1.00 | 0.022 | −61.2 | | 0.56 |
| synthetic 2x, EMA100/200, 1% band -> bills | 2000-01 | +5.88 | +5.28 | 1.00 | 1.00 | 0.021 | −58.9 | | 0.57 |
| synthetic 2x, SMA100/250, 1% band | 2000-01 | +4.93 | +4.80 | 1.00 | 1.00 | 0.018 | −59.8 | | 0.56 |
| synthetic 2x, SMA300, 1% band, k5 | 2000-01 | +4.58 | +4.94 | 0.97 | 0.98 | 0.033 | −48.1 | | 0.58 |
| synthetic 2x, SMA150, 4% band | 2000-01 | +4.80 | +3.26 | 0.85 | 0.98 | 0.125 | −44.8 | 24.5% | 0.54 |
| synthetic 2x, SMA200, 3% band | 2000-01 | +3.73 | +3.37 | 0.78 | 0.89 | 0.132 | −49.2 | | 0.55 |
| *control:* synthetic 2x buy-and-hold | 2000-01 | +2.74 | +0.82 | 0.70 | 0.83 | 0.39 | −88.4 | | 0.42 |
| *control:* SPY 50 / synthetic 2x 50 buy-and-hold | 2000-01 | +1.71 | +0.43 | 0.70 | 0.83 | 0.37 | −68.7 | 26.3% | 0.45 |

Long history on synthetic 2x VFINX (`long_screen`, 1986-2026, CA):

| config | score | full excess | 5-yr windows ending ≤ 2000 (beat) | 10-yr windows ending ≤ 2000 (beat) | p | max DD | Sharpe (VFINX's) |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA100/200, 1% band | +5.68 | +3.36 | +2.75 (0.5) | +1.80 (0.6) | 0.10 | −61.3 | 0.59 (0.67) |
| EMA100/150, 1% band | +6.13 | +3.93 | +3.50 (0.5) | +2.74 (0.6) | 0.05 | −61.2 | 0.61 |
| SMA300, 1% band, k5 | +5.04 | +3.06 | +3.94 (0.7) | +3.78 (1.0) | 0.09 | −59.1 | 0.61 |
| *control:* 2x buy-and-hold | +2.30 | +2.89 | +7.05 (0.9) | +7.09 (1.0) | 0.16 | −88.3 | 0.55 |

Synthetic 2x leveraged timing with a slow trend filter:

* **Beats SPY in CA in every full-protocol 10- and 15-year window.** The
  neighbourhood holds: 17 of 17 timed variants on synthetic 2x have a
  positive CA score.
* **Does not depend on the Treasury safe asset.** Bills and cash work too.
* **Survives the 1986-1999 holdout on synthetic data.** It did so even though
  this slow rule exited only *after* the 1987 crash, on 1987-11-30.

Why it still is not a pass:

1. **It is leverage.**
   * Volatility is 30-32% vs SPY's 19%, and max drawdown −59% vs −55%.
   * Sharpe is about SPY's: equal over 2006-2026, +0.06 over 2000-2026, and
     −0.08 over 1986-2026 against VFINX.
   * The excess return is mostly payment for risk. The trend filter's real
     contribution is avoiding the −88% drawdowns that leveraged buy-and-hold
     suffers in slow bear markets.
2. **Item 4 fails narrowly.** On the 18-config leveraged sub-grid,
   walk-forward out-of-sample is +6.1 pp (10y/5y, 3/3) and +1.7 pp (5y/3y,
   2/4). But PBO is 0.53 (CA) and 0.65 (NONE), and the deflated Sharpe is
   0.75.
3. **It rests on very few events.** The real-SSO record has 4 switches in 20
   years: out Feb 2008–Sep 2009 and Jun 2022–Jun 2023. The 1986-2026 synthetic
   record has 10.
4. **Real-world frictions are missing.**
   * Leveraged ETFs' occasional capital-gain distributions and tracking error
     are not modelled.
   * Before 2006 no such fund existed, so the synthetic history is only an
     approximation.

The `leverage` family studies this space in depth (3x, overlays, vol
targeting) and reports the same shape of result. These rows are a
cross-check, not a separate claim.

## 5. New angle: hedge with SH instead of selling (windows from 2007, CA `screen`)

The idea: when the trend turns off, keep half the SPY and buy the same amount
of SH (−1x S&P). Net exposure is about zero, but only half the position's
gains are realized.

| rule | sell to IEF | 50% base + IEF | 50% SPY + 50% SH | SH hedge with tax rule (5% budget, no ST) |
|---|---:|---:|---:|---:|
| SMA150, 4% band | −2.11 | −1.04 | −2.68 | −1.48 |
| SMA200, 3% band | −2.72 | −1.51 | −3.20 | −1.81 |
| Faber 10-month | −4.03 | −2.16 | −4.24 | −1.85 |

**It does not work.** SH's costs and decay, and giving up the bond return,
outweigh the deferred tax. Note that every 2007+ timing variant loses heavily
in CA (−1 to −4 pp/yr).

## 6. Honest conclusion

* **Unlevered timing (CA taxable account): do not use it to beat SPY.** The
  best after-tax rules post +1 pp/yr in 2000-2026 with a 57% 10-year win
  rate, and that +1 pp is two bear markets.
* **The 1986-1999 holdout and the post-2009 record both reject it.** Not one
  of 662 rules beat SPY in any 10-year window starting after 2008. All 35
  long-history rules lost to VFINX after tax.
* **Selection noise dominates.** PBO is 0.69 and the deflated Sharpe is 0.11.
* **If the goal is a smaller drawdown,** two rules cut it from −55% to about
  −27% to −30% at roughly zero average after-tax cost in 2000-2026: SMA300
  with a 1% band and 5-day confirmation, or SMA150 with a 4% band, both to
  IEF. Expect −3 to −4 pp/yr in a decade without a slow bear market.
* **A never-rebalanced 70/30 SPY/Treasury mix** buys the same drawdown with a
  steadier −1 pp/yr cost and a higher Sharpe.
* **IRA (NONE) diagnostic:** the best is Faber 7-month with a 1% band, at
  +2.71 pp. That is neighbourhood-mined: k = 9-10 lose, and a one-month
  evaluation shift turns Faber 8 negative. It still fails items 2-3 (10-year
  beat 0.57, p 0.16), and its long history is negative before 2000.
* **Leveraged timing does beat SPY with statistical confidence.** It holds 2x
  S&P only while a slow trend is up. But it does so by carrying 1.6x the
  volatility and a deeper drawdown, with about the same Sharpe. It belongs to
  the leverage discussion, not to "timing skill".

## 7. Caveats

* **Distributions:** prices are total-return, and the engine defers tax on
  dividends and bond interest. Timing holds IEF about 20-27% of the time
  (average risk weight 0.73-0.81), so the bond leg is somewhat flattered in
  CA, as PROTOCOL 5.5 warns.
* **Cash earns 0%.** "-> cash" variants are therefore pessimistic; the
  bills chains are the realistic alternative.
* **Engine `elapsed` times in the cache include waiting for a slot and frozen
  (SIGSTOP) time.** They are not compute measures.
* **`common.mix` with a fund that does not exist yet silently renormalizes** to
  the funds that do (100% bonds before SPY launched in 1993). The earlier
  researcher's long-history "SPY 80/VFITX 20" control would have been wrong
  for that reason; it was replaced by VFINX/FGOVX.

## 8. Reproduce

* **Module:** `research/lab/families/trend_timing.py` (unchanged in this
  session).
* **Grid builders:** `research/lab/scratch/trend_timing/grid.py`.
* **Resume plan and stages:** `research/lab/scratch/trend_timing/v2/queue2.json`
  and `v2/st_*.json`, run by `v2/pipeline2.py`.
* **Analysis scripts (all `research/lab/scratch/trend_timing/v2/`):**
  * `an_full.py`, `an_long.py`, `an_stage.py` (tables);
  * `an_exec.py` (execution pivot), `an_nbhd.py` (neighbourhoods);
  * `cohorts.py`, `subperiods.py`, `ddcost.py` (regime analyses);
  * `an_hindsight.py` (random menus);
  * `diag_cached.py`, `diag_lev.py` (diagnostics), `candidates.py`
    (candidate stats).
* **Full table:** `research/lab/results/trend_timing_table.csv`. It has every
  record, with a `protocol` column, a block tag and the exact config JSON.
