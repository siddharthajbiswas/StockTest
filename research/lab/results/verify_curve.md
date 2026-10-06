# Verification: yield-curve un-inversion candidates (`verify_curve`)

**Verdict: both candidates FAIL as "beats SPY after California tax with good confidence".**
They are not bugs or look-ahead: the engine numbers reproduce exactly and the signal is causal. They are
a two-event backtest. Since 2000 the 10y-3m curve un-inverted 4 times (2001, 2007, 2019, 2024). All of
the after-tax excess comes from being in Treasuries during the 2001-02 and 2008 bear markets: 120% of
the CA log excess for `uninv540 minlen90` and 146% for the gated rule. Every other year added up to
-0.70 / -1.20 pp/yr. 2022 contributed nothing, because neither rule was out of SPY in 2022.

Both candidates fail the protocol bar in CA (10-year beat rate 0.57 / 0.64, 15-year 0.81 / 0.77). No
point of their parameter neighbourhoods passes either: across every `after` from 90 to 930 days, the
CA 10y beat rate never exceeds 0.58 / 0.66. The deflated Sharpe in CA is 0.022 / 0.004 given ~12,000
configs.

On top of that, each candidate has one specific fragility the round-1 write-up did not find:

* **`uninv540 minlen90`: the `min_len 90` filter only works because of a data quirk.** The lab's curve
  (`^TNX - ^IRX`) uses the T-bill *discount* yield, which reads about 10 bp too high. On the standard
  curve (FRED `T10Y3M`, matched within 1 bp by a bond-equivalent conversion of ^IRX), the 2019
  inversion lasted 141 days, not 51 + 71. So `min_len 90` would *not* have skipped 2019, and the rule
  would have sat in Treasuries from Nov 2019 to May 2021 (S&P +40%, Treasuries +6%). Corrected for
  this, the CA score drops from +3.87 to **+2.67** (full-period excess +2.24, 10y beat 0.57, 15y beat
  0.77). The 1989 inversion (93 days) also appears on the standard curve, and the pre-2000 holdout
  then shows nothing (CA ho10 -0.43 pp/yr). Over 1962-1999 the long-hold rule went 0 for 4 (pre-tax
  -1.03 pp/yr in 1962-85, permutation p = 0.42 before 2000).
* **GATED rule: its headline is the luckiest of 28 equivalent rules.** It checks the regime once a
  month, on the first trading day. Checking on any of the other 27 possible days of the month gives a
  CA score of +0.88 to +2.95 (median of all 28: **+1.63**, against +3.12 on the 1st). Reading the signal 8 days
  later gives +1.86. The difference is mostly the COVID crash: the 2 March 2020 check read SPY's
  28 Feb close just below its 200-day average. The standard battery's "offset" test misses this (see §7, a battery
  limitation).

What survives: the timing is not random. Moving the real risk-off spells to random dates with the
same lengths beats the real result in only 0.1-0.4% of 2,000 placements (pre-tax), and the CA
permutation test agrees (§6). The gated rule also reduces max drawdown (-35% vs SPY -55%) and was
positive before 1986 in an off-engine proxy (+1.8 pp/yr pre-tax, similar to plain trend-following).
That is the curve's recession information plus the luck of two crashes. With 2-4 independent events
it is not a basis for "beats SPY with good confidence".

All engine numbers are the lab's (= the site's). "Replica" numbers come from
`scratch/verify_curve/casim.py`, an exact re-implementation of the engine for this all-in SPY <-> bond
switch. It reproduces the engine's after-tax liquidation value of **every** window to a relative
difference of 0.0 in CA, FED and NONE. It was checked with monthly, weekly and daily regime checks,
with shifted check days, and on the long protocol with the FGOVX fallback (it reproduces round-1's
long-protocol numbers to 6 digits). It needs no backtest slot, which made 1,000-plus permutation
runs and 28-way check-day tests feasible on the shared machine. "Off-engine" numbers (1962-1985) are
a pre-tax proxy and **not** site numbers: S&P 500 price + 3.8%/yr dividends, then VFINX and SPY,
against a synthetic 5-year Treasury par bond built from `^FVX` (monthly correlation with VFITX 0.97,
0.7 pp/yr below it).

## 1. The candidates and the headline (standard battery, `verify.battery`, n_trials 12,000)

| candidate | regime | score | full | 10y beat | 15y beat | 20y beat | boot p | maxDD (SPY) | DSR |
|---|---|---|---|---|---|---|---|---|---|
| `uninv540 minlen90 \| chkM` (M) | CA | +3.87 | +3.76 | 0.57 | 0.81 | 1.00 | 0.062-0.064 | -34% (-55%) | 0.022 |
| | FED | +4.40 | +4.25 | 0.57 | 0.81 | 1.00 | 0.044-0.048 | -34% | 0.035 |
| | NONE | +5.03 | +4.77 | 0.57 | 0.81 | 1.00 | 0.034-0.036 | -34% | 0.053 |
| `GATED uninv540 & spy200 \| chkM` (G) | CA | +3.12 | +2.80 | 0.64 | 0.77 | 1.00 | 0.101-0.134 | -35% (-55%) | 0.004 |
| | FED | +3.59 | +3.34 | 0.82 | 0.77 | 1.00 | 0.066-0.072 | -31% | 0.008 |
| | NONE | +4.27 | +4.11 | 0.85 | 0.89 | 1.00 | 0.036-0.040 | -27% | 0.017 |

(boot p range: 500 vs 1,000 bootstrap draws; round 1 reported the 1,000-draw value.) Round-1 numbers
reproduce exactly. The 20-year beat rate of 1.00 is not independent evidence: every 20-year window
(starting 2000-2006) contains 2008.

Battery extras, CA: one-day execution lag M +3.72, G +2.81; costs at 35 bps per side M +3.73, G +2.87.
Annual tax on distributions (VFITX interest at 38.8%, CA-exempt Treasury interest): from 2000, M
+3.76 -> +3.60 and G +2.80 -> +2.70. From 2010 both are negative (M -1.36, G -1.62 pp/yr). Sub-periods,
CA: M +10.98 (2000-10), -0.00 (2010-20), -2.99 (2020-26); G +9.02, -0.00, -2.37.

## 2. The events

### 2.1 Since 2000 (engine trade dates, SPY and VFITX total return over each spell)

| rule | out of SPY | back in | SPY | VFITX | helped? |
|---|---|---|---|---|---|
| M | 2001-02-01 | 2002-08-01 | -34.4% | +14.3% | yes |
| M | 2007-06-01 | 2008-12-01 | -45.1% | +20.9% | yes |
| M | 2024-12-02 | 2026-06-01 | +27.9% | +5.9% | no (-17%) |
| G | 2001-02-01 | 2002-04-01 | -15.6% | +5.1% | yes |
| G | 2002-05-01 | 2002-08-01 | -18.4% | +5.7% | yes |
| G | 2008-01-02 | 2008-12-01 | -42.4% | +9.7% | yes |
| G | 2020-03-02 | 2020-06-01 | -0.6% | +3.3% | yes (small) |
| G | 2025-04-01 | 2025-06-02 | +5.7% | -0.1% | no |
| G | 2026-04-01 | 2026-05-01 | +10.0% | +0.1% | no |

**Independent events.** On the lab's curve definition (confirm 5, episodes of at least 30 days), the
10y-3m curve had **4** inversion cycles since 2000 (2000-01, 2006-07, 2019, 2022-24) and **8** since
1962 (1966-67, 1968-70, 1973-74, 1978-81, plus the four). These comprise 14 individual un-inversions.
`min_len 90` keeps 3 of the 4 ETF-era cycles (it drops 2019) and 7 since 1962. On the standard
(FRED/bond-equivalent) curve, 1989 is a ninth cycle and 2019 survives `min_len 90`.

### 2.2 Every un-inversion since 1962 (off-engine proxy, pre-tax; switch = first trading day of the next month)

| inverted (lab curve) | days | switch | S&P TR +6m | +12m | +18m | 5y Tsy +18m | S&P max DD in 18m |
|---|---|---|---|---|---|---|---|
| 1966-09-14..1967-02-15 | 154 | 1967-03-01 | +8.2% | +5.9% | +19.1% | +4.4% | -8.8% |
| 1968-12-26..1969-02-18 | 54 | 1969-03-03 | -1.0% | -4.7% | -12.8% | +7.0% | -32.1% |
| 1969-07-10..1969-09-22 | 74 | 1969-10-01 | -0.8% | -5.3% | +13.9% | +27.0% | -28.1% |
| 1969-10-24..1970-02-17 | 116 | 1970-03-02 | -7.4% | +12.3% | +18.4% | +16.3% | -22.6% |
| 1973-06-07..1974-07-02 | 390 | 1974-08-01 | -1.4% | +16.1% | +33.3% | +17.4% | -24.2% |
| 1974-08-07..1974-09-24 | 48 | 1974-10-01 | +32.9% | +35.9% | +72.6% | +15.3% | -13.6% |
| 1978-12-01..1980-05-06 | 522 | 1980-06-02 | +26.6% | +19.7% | +16.0% | +9.1% | -19.0% |
| 1980-10-31..1981-03-24 | 144 | 1981-04-01 | -12.7% | -15.0% | -5.0% | +29.7% | -21.7% |
| 1981-04-30..1981-09-15 | 138 | 1981-10-01 | -3.4% | +6.4% | +33.5% | +48.3% | -18.4% |
| 2000-08-07..2001-01-25 | 171 | 2001-02-01 | -10.6% | -17.3% | -36.7% | +13.9% | -40.9% |
| 2006-08-07..2007-05-21 | 287 | 2007-06-01 | -2.6% | -8.1% | -43.1% | +16.9% | -50.8% |
| 2019-06-03..2019-07-24 | 51 | 2019-08-01 | +12.2% | +13.0% | +33.5% | +8.1% | -33.7% |
| 2019-08-06..2019-10-16 | 71 | 2019-11-01 | -6.6% | +9.9% | +40.1% | +5.3% | -33.7% |
| 2022-11-16..2024-11-18 | 733 | 2024-12-02 | -1.2% | +14.3% | +26.6% | +5.4% | -18.8% |

Only 4 of 14 un-inversions were followed by a lower S&P 18 months later. Only 2001 and 2007 were
followed by a bear market that a 540-day exit fully captures. Most un-inversions came shortly
before or during a recession, but the stock market often bottomed early (1970, 1974, 1982) or
recovered fast (2020).

### 2.3 What the 1962-2026 risk-off spells did (off-engine, pre-tax)

`uninv540 minlen90`: 7 spells, **2 helped** (2001, 2007), 1 neutral (1970), 4 hurt (1967 -12.5%,
1974 -4.4%, 1980-83 -2.8%, 2024-26 -17.2% relative). Annualized edge: 1962-85 **-1.03**, 1986-99 0.00
(no event on the lab curve), 2000-26 +4.77, 1962-2026 +1.59 pp/yr. It is robust to the dividend
assumption: -0.86 to -1.28 pre-1986 for dividend yields of 3-5%.

GATED: 13 spells, 9 helped. 1962-85 **+1.79** pp/yr (3-5% dividends: +1.51 to +2.03), 2000-26 +4.11.
Plain monthly SMA200 trend timing with no curve condition made +1.71 in 1962-85 but -3.95 in 1986-99.
The curve window mainly keeps the trend rule switched off in bull markets.

## 3. The curve-definition artifact (new finding)

`macro_regime` builds the slope as `^TNX - ^IRX`. ^IRX is the 13-week bill's **discount** yield, which
is below its bond-equivalent yield. Compared with FRED `T10Y3M` (the standard 10-year minus 3-month
constant-maturity spread, downloaded once and saved as `scratch/verify_curve/FRED_T10Y3M.csv` for
this check), the lab spread is biased up by +0.12 pp on average (median +0.10). Converting ^IRX to a
bond-equivalent yield, `BEY = 365 d / (360 - 91 d)`, removes the bias: mean +0.011, median +0.003 pp
against FRED. The days with a negative spread then match:

| period | days < 0, FRED | lab ^TNX-^IRX | lab BEY |
|---|---|---|---|
| 1989 | 99 | 6 | 101 |
| 2019 (Mar-Oct) | 104 | 82 | 102 |
| 2006-07 | 232 | 193 | 230 |

Inversion episodes, confirm 5, on FRED: 1989-05-31..09-01 (**93 days**), 2000-07-13..2001-01-26,
2006-07-25..2007-06-05, 2019-05-30..10-18 (**141 days**), 2022-10-31..2024-12-19, plus short ones in
2025. The lab curve instead shows **no 1989 episode** and **splits 2019 into 51 + 71 days**. The new
indicator type `curve_bey` (in `families/verify_curve.py`) reproduces FRED's un-inversion dates to
within 0-3 days (1989-09-01, 2001-01-29, 2007-06-04, 2019-10-17, 2024-12-19).

Consequences:
* M's `min_len 90` exists to drop 2019. On the standard curve 2019 is a 141-day episode, so it is
  not dropped. Corrected M (`curve_bey`, all else equal; engine): CA score **+2.67** (vs +3.87),
  full **+2.24** (vs +3.76), 10y beat 0.57, 15y beat 0.77, **boot p 0.23** (vs 0.06). FED +3.15
  (boot p 0.19), NONE +3.76 (boot p 0.145).
* G is unchanged at 540 days (its `min_len 30` keeps 2019 on either curve): CA +3.12.
* The pre-2000 holdout stops being empty (section 4).

## 4. (a) Long protocol 1986-2026 (VFINX / VFITX, FGOVX before 1991) and the pre-2000 holdout

Replica numbers. The lab-curve rows reproduce round 1's engine numbers exactly. The corrected (BEY)
monthly-M and weekly-G rows were re-run in the engine and match exactly. Their long-protocol CA boot p
is 0.41 / 0.36, and max drawdown -33% / -36% (VFINX -55%).

| config | regime | score | full | 10y beat | 15y beat | ho5 mean (beat) | ho10 mean |
|---|---|---|---|---|---|---|---|
| L M (lab curve) | CA | +3.71 | +1.84 | 0.59 | 0.90 | 0.00 (no event) | 0.00 |
| L M **corrected (BEY)** | CA | +2.99 | +0.59 | 0.61 | 0.88 | -0.11 (0.32) | -0.43 |
| L M corrected | FED | +3.51 | +1.47 | 0.64 | 0.88 | -0.02 (0.38) | -0.13 |
| L M corrected | NONE | +4.17 | +2.43 | 0.74 | 0.89 | +0.24 (0.49) | +0.36 |
| L G (lab curve) | CA | +3.03 | +1.19 | 0.63 | 0.88 | 0.00 (no event) | 0.00 |
| L G **corrected (BEY)** | CA | +2.87 | +0.77 | 0.64 | 0.87 | **-0.75 (0.03)** | **-1.05** |
| L G corrected | FED | +3.32 | +1.56 | 0.74 | 0.89 | -0.78 (0.03) | -0.95 |
| L G corrected, weekly check | CA | +2.63 | +0.68 | 0.65 | 0.87 | -0.63 (0.03) | -0.94 |

* On the lab curve the holdout is empty (ho = 0 exactly), as round 1 said. On the standard curve it
  holds one event (1989-10 to 1991-03). It is mildly negative for M after tax and clearly negative
  for G. G's trend gate whipsawed in 1990: it was out in Feb-Mar and in May 1990, and both were
  followed by gains. Its Sept 1990 - Jan 1991 exit only broke even (VFINX +7.6%, FGOVX +7.9%).
  **The only pre-2000 out-of-sample event in the engine data does not support either rule.**
* From 1986, CA full-period excess is only +0.6 to +1.8 pp/yr, and the 10y beat rate is 0.59-0.65 for
  every variant.

## 5. (b) Parameter neighbourhood: is 540 a lucky spike?

CA score (replica, protocol `full`). Plain rule rows are by `after`, columns by `min_len`:

| after | min_len 0 | 30 | 60 | 90 (cand.) | 120-150 | 180 | 10y beat (ml 90) | 15y beat (ml 90) |
|---|---|---|---|---|---|---|---|---|
| 180 | -0.21 | +0.37 | +0.49 | +0.30 | +0.30 | +0.20 | 0.52 | 0.70 |
| 270 | +0.05 | +0.47 | +0.53 | +0.85 | +0.85 | +0.59 | 0.52 | 0.74 |
| 360 | -0.48 | +0.21 | +0.32 | +0.64 | +0.64 | +0.46 | 0.52 | 0.74 |
| 450 | -0.15 | +0.30 | +0.41 | +1.15 | +1.15 | +0.90 | 0.55 | 0.79 |
| 480 | +0.36 | +0.70 | +0.81 | +1.70 | +1.70 | +1.37 | 0.55 | 0.79 |
| 510 | +1.15 | +1.48 | +1.59 | +2.61 | +2.61 | +2.15 | 0.57 | 0.81 |
| **540** | +2.42 | +2.63 | +2.74 | **+3.87** | +3.87 | +3.21 | 0.57 | 0.81 |
| 570 | +2.03 | +2.15 | +2.26 | +3.39 | +3.39 | +2.68 | 0.57 | 0.81 |
| 600 | +2.52 | +2.67 | +2.78 | +4.00 | +4.00 | +3.22 | 0.58 | 0.83 |
| 630 | +3.19 | +3.33 | +3.44 | +4.67 | +4.67 | +4.00 | 0.58 | 0.83 |
| 720 | +1.77 | +1.63 | +1.75 | +3.18 | +3.18 | +2.39 | 0.57 | 0.81 |
| 900 | +0.83 | +0.75 | +0.86 | +2.23 | +2.23 | +1.75 | 0.57 | 0.81 |

GATED (min_len 30), CA score / 10y beat / 15y beat: after 450 +0.41 / 0.61 / 0.68; 480 +0.96;
510 +1.89; **540 +3.12** / 0.64 / 0.77; 600 +3.28; 630 +3.94 / 0.66 / 0.79; 720 +2.46; 900 +1.96.
SMA 100/150/200/250: +2.21 / +2.86 / +3.12 / +3.01. For G, confirm 1-20 days and thresholds of
-0.1..+0.25 give +2.1..+3.3, and a threshold of -0.25 gives +1.0..+2.1.

* 540 is not a single-point spike. It sits on the left edge of a **plateau from about 520 to 720
  days**. Below about 510 days the score falls off a cliff: +3.87 -> +2.61 -> +1.70 -> +1.15 at
  540/510/480/450. The plateau has one cause. The window opened by the 2007-05-21 un-inversion must
  still be open through the September-October 2008 crash, which needs at least ~500-530 days. After
  450 days the rule is back in SPY on 2008-09-02.
* The beat-rate bar fails **everywhere**. The 10y beat rate is at most 0.58 (plain) and 0.66
  (gated), and the 15y beat rate at most 0.83 / 0.79, for every `after` from 90 to 930 days, every
  `min_len`, confirm and threshold. The windows starting after 2009 do not contain a crash, and they
  lose.
* `min_len` from 75 to 150 gives identical results in the ETF era; its only effect is dropping 2019
  (a hindsight choice, and an artifact, see §3).
* Off-engine 1962-85 (pre-tax), 99% of plain variants with `after` of 420 days or more **lose**
  (-2.4 to -0.1 pp/yr; one exception at +0.11). With `min_len 90`, `after` of 90-360 days ranges from
  -0.3 to +1.4. The plateau's location is contradicted out of sample.
* M depends on shallow inversions. With an inversion threshold of -0.25 (the spread must fall below
  -0.25 pp), the 2000-01 and 2006-07 inversions vanish from the lab curve and the CA score collapses
  to -0.11. With threshold -0.10 it is +2.61, with +0.10 it is +2.73. Confirm 1-20 days at threshold
  0 gives +2.65..+3.87.

## 6. (c) Permutation test: shift the real risk-off spells (durations preserved)

The real spells, clipped to 2000-01-01..2026-07-01, are moved to random non-overlapping dates (the
gated rule keeps its SMA200 gate and moves only the curve windows). A circular-shift version moves
all spells together in 30-day steps (322 shifts). p = share of placements with a result at least as
good as the real one.

| test | M score p | M full p | G score p | G full p | real vs placement median / 95th pct (score) |
|---|---|---|---|---|---|
| pre-tax (NONE), 2000 random | 0.0015 | 0.0015 | 0.004 | 0.0045 | M +5.03 vs -1.29 / +2.18; G +4.27 vs -0.20 / +2.77 |
| pre-tax, circular | 0.006 | 0.006 | 0.019 | 0.006 | |
| CA, 1000 random (replica) | 0.0010 | 0.002 | 0.004 | 0.009 | M +3.87 vs -1.43 / +1.47 (best of 1,000: +3.70); G +3.12 vs -0.47 / +1.93 |
| CA, circular | 0.006 | 0.006 | 0.019 | 0.015 | |
| off-engine 1962-2026, 2000 random (pre-tax) | | 0.007 | | 0.0035 | |
| off-engine **1962-1999 only** | | **0.42** | | **0.042** | M -0.66 pp/yr real |

Reading: in the ETF era the real timing is in the top 0.2-2% of random timings. That is the expected
outcome when the spells cover the two largest bear markets of the period. The test is conditional on
the event dates and does not account for `after = 540` and `min_len = 90` having been chosen after
looking at them. Before 2000, where nothing was tuned, M's timing is no better than random (p 0.42).
G's is marginally better (p 0.04, pre-tax, mostly 1969-70, 1974 and 1981-82).

## 7. (d) Lags, check day and execution timing

| test (CA score) | M | G |
|---|---|---|
| headline (check on the 1st trading day, signal = yesterday's close) | +3.87 | +3.12 |
| 1-day execution lag (battery, `weights_x lag 1`) | +3.72 | +2.81 |
| indicator read with a 2 / 8 / 15-calendar-day lag (default 1) | +3.87 / +3.79 / +3.77 | +3.12 / **+1.86** / +1.68 |
| indicator lag 31 days (1 month) / 62 days | +3.24 / +3.60 | **+1.17** / +1.96 |
| check day = any of the 28 possible days of the month: min / **median** / max | +3.14 / **+3.44** / +4.24 (actual ranks 3rd) | +0.88 / **+1.63** / +3.12 (actual ranks **1st of 28**) |
| check-day offsets, 10y beat rate median | 0.57 | 0.55 |
| weekly regime check / daily check | +3.58 / +3.52 | +2.67 / +2.15 |
| corrected curve (BEY) + weekly / daily check | +2.65 / +2.29 | +2.83 / +2.03 |

The FED and NONE patterns are the same (NONE: G's 28 check days give +1.48..+4.27, median +2.39).

* M is insensitive to timing: its spells last 18 months.
* G is not. Its edge depends on the exact day it looks at the 200-day average. On the 1st trading day
  of March 2020 it read the 28 Feb close and left SPY on 2 March. SPY had closed below its SMA200 on
  27-28 Feb, but was back above it on 2 March, so a check one day later would have stayed in. It
  returned on 1 June. With an 8-day-old signal it left on 1 April, after the crash, and returned on
  1 July, missing a +27% rebound. A daily or weekly check (no calendar luck) gives +2.15 / +2.67 in
  CA.
* **Battery limitation (reported, not edited):** `verify.battery`'s "rebalance-timing luck" variants
  shift only the `WeightStrategy` rebalance key (`weights_x offset_days`). `MacroSwitch` computes its
  own check key from the unshifted date (`period_key(ctx.date, self.check)`). For `check="M"` signals
  the offset variants therefore become "check on the 1st **and** on the shifted day", not "check on a
  different day". That is why the battery showed G's offsets as +2.64..+3.12 (all positive) when the
  true spread is +0.88..+3.12. The fix used here: a `check_offset` parameter on `verify_curve.switch`,
  plus `weights_x` with the same `offset_days`, validated against the engine at offsets 3/7/10/14.
  Every `macro_regime` finalist with a monthly check got this optimistic offset test.

## 8. (e) Realism and costs

* Annual tax on VFITX interest (ordinary federal + NIIT; Treasury interest is CA-exempt) and on SPY
  dividends: CA -0.10 to -0.16 pp/yr from 2000. Small, because the rules hold bonds only 11-17% of
  the time.
* Costs: 0 / 15 / 35 bps per side change the CA score by less than 0.25 pp (27-47 trades in 26 years).
* Safe asset (engine, CA score M / G): VFITX +3.87 / +3.12, short Treasuries VFISX +3.55 / +2.93,
  long Treasuries VUSTX +3.99 / +3.24, **cash at 0%** +2.93 / +2.61 (boot p 0.11 / 0.14). The edge
  comes mostly from being out of equities; the bond rally adds 0.5-0.9 pp.
* Practical: VFITX is a mutual fund (Vanguard restricts buying back within 30 days of a sale). G's
  2002 and 2026 round trips are right at that limit; an ETF (IEF) is the real-world substitute after
  2002.

## 9. (f) How much comes from 2008 and 2022 (and 2001-02)

Calendar-year after-tax attribution, from the CA run started 2000-01-01, month-end liquidation values:

| rule | total log excess | 2001-02 | 2008 | 2022 | 2024-26 | all other years |
|---|---|---|---|---|---|---|
| M, CA | +91.4% (26.5 y) | +52.6% (58%) | +57.3% (63%) | -0.5% (~0%) | -19.5% | **-0.70 pp/yr** without 2001-02 and 2008 |
| G, CA | +68.4% | +46.7% (68%) | +53.3% (78%) | +2.6% (tax-basis effect only) | -21.7% | **-1.20 pp/yr** |
| M, NONE | +114.3% | +55.1% | +66.0% | 0.0% | -19.3% | -0.26 pp/yr |
| G, NONE | +98.7% | +47.0% | +64.1% | 0.0% | -15.8% | -0.47 pp/yr |

Counterfactual reruns (replica, CA score / full / 10y beat):

| variant | M | G |
|---|---|---|
| as is | +3.87 / +3.76 / 0.57 | +3.12 / +2.80 / 0.64 |
| hold SPY through all of 2008 | **+0.98** / +1.29 / 0.52 | **+0.35** / +0.39 / 0.40 |
| drop the 2007-08 spell | +0.58 / +1.25 / 0.19 | +0.44 / +0.80 / 0.27 |
| drop the 2001-02 spell | +3.21 / +1.95 / 0.57 | +2.57 / +1.23 / 0.64 |
| hold SPY through all of 2022 | unchanged (+3.87) | unchanged (+3.12) |
| drop **both** 2001 and 2007 spells | **-0.06 / -0.80** / 0.03 | **-0.10 / -0.95** / 0.10 |

2022 contributes nothing because the 2022-24 inversion's un-inversion came in Nov 2024. Neither rule
held Treasuries during the 2022 bond crash, and neither dodged 2022's equity decline. 2008 alone is
about 75-90% of the score. Without the 2001 and 2007 events both rules are slightly negative.

## 10. Multiple testing

Deflated Sharpe of the CA after-tax monthly excess, given ~12,000 configs tried: M 0.022, G 0.004
(FED 0.035 / 0.008; NONE 0.053 / 0.017). The round-1 macro family's own walk-forward was negative
out of sample (-3.38 pp/yr). Neither survives the search-size correction.

## 11. Verdicts

| candidate | verdict | why |
|---|---|---|
| `uninv540 minlen90 \| chkM` | **fail** | Two events. Fails 2a/2b in CA everywhere in its neighbourhood. `min_len 90` relies on a discount-yield artifact (corrected CA score +2.67). Contradicted 1962-99 (0 of 4 spells helped, permutation p 0.42). DSR 0.02. |
| `GATED uninv540 & spy200 \| chkM` | **fail** | Two events. Its check day is the best of 28 (median +1.63 CA). An 8-day signal delay gives +1.86. The corrected-curve holdout is negative (ho10 -1.05 CA). DSR 0.004. A real drawdown reducer (-35% vs -55%), not a way to beat SPY with confidence. |

Most robust versions, if anyone wants to keep watching this signal. These are not recommendations;
they are the honest restatement of each rule:

* M corrected: `curve_bey` (FRED-consistent) with everything else unchanged. Engine-confirmed: CA
  +2.67 / full +2.24 / 10y 0.57 / 15y 0.77 / 20y 1.00 / boot p 0.23 / maxDD -30% (SPY -55%), 36
  trades. FED +3.15 / boot p 0.19. Long protocol CA +2.99 / full +0.59, holdout ho10 -0.43. Fails 2a,
  2b and 3 in CA and FED.
* G corrected: `curve_bey` plus a **weekly** check (removes calendar luck). Engine-confirmed: CA
  +2.83 / full +2.61 / 10y 0.66 / 15y 0.77 / 20y 1.00 / boot p 0.106 / maxDD -31% (SPY -55%), 66
  trades. FED +3.28 / 10y 0.82 / 15y 0.79 / boot p 0.07. Long protocol CA +2.63 / full +0.68,
  holdout ho10 -0.94. Fails 2a, 2b and 3 in CA.

## 12. Files

* `families/verify_curve.py`: signal `verify_curve.switch` (= `macro_regime.switch` plus a `mask`
  indicator for permutations and leave-one-out, a `curve_bey` indicator, and `check_offset`).
* `scratch/verify_curve/`
  * `casim.py`, `validate_casim.py`: exact engine replica and its validation.
  * `simlib.py`: pre-tax replica.
  * `perm_pretax.py`, `perm_casim.py`: permutations.
  * `casim_runs.py`, `casim_checks.py`, `casim_long.py`, `neigh_pretax.py`: neighbourhoods, offsets,
    lags, leave-one-out, long protocol.
  * `offengine.py`: 1962-2026 proxy.
  * `yearly.py`: attribution.
  * `battery_run.py`, `battery_*.pkl`: standard battery.
  * `FRED_T10Y3M.csv`: validation data only.
  * CSV/JSON outputs next to the scripts.
* Configs tried in this verification: about 1,700 replica and engine configurations plus about
  11,000 permutation placements (pre-tax 4,644, CA 2,644, off-engine 4,000). They are verification
  runs, not new strategy search, but they are listed here for the record.
