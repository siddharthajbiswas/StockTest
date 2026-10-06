# r2_combos: cross-family combinations run as one taxable account

Round 2, key `combos`. The question: can a combination of the round-1 survivors, held as ONE
taxable brokerage account, beat buying and holding SPY after California tax (48.1% / 28.1%) with
good confidence, and is any combination more robust than its best component (beat rates, worst
windows, holdouts), not just better on the headline? Secondary regime FED (35% / 15%, no NIIT).

All numbers are after-tax excess CAGR over SPY buy-and-hold (VFINXR on 1986+ histories), in
percentage points per year (pp), from the lab engine (= the website's engine) or from a simulator
that reproduces it exactly (section 1). "score" = mean of the 5/10/15-year average excess.

## Verdict

**No combination clears the good-confidence bar, in CA or in FED, and none beats its best
component on the pre-registered robustness test.** Combining buys *risk control*, not
*confidence*.

What combining does buy (the never-sold SPY core + leveraged-trend sleeve, group A, is the clearest case):

* Drawdowns at or below SPY's in every history, with the excess still positive everywhere.
  A3 (75% SPY + 25% 3x trend sleeve) has max drawdown −47% vs SPY −55% on 2000-2026 and 1986-2026, and
  −75% vs SPY −81% in 1930-1985. The 3x sleeve alone has −62% and −88%.
* Much smaller worst windows. In 1930-1985, A3's worst 10-year window is −1.5 pp/yr vs −11.8 for its 3x sleeve run alone.
* Lower crash odds than SPY itself. Block-bootstrapping 1930-2026, A3's chance of a >60% drawdown within
  20 years is 16% (SPY 20%, the sleeve alone 69%); A1's is 7%.
* Across the whole parameter plane (SMA 100-300 × band 0-5%), a core + 3x sleeve has a positive median excess in all
  four histories and beats holding the same average leverage constantly by a wide margin
  (A3 +2.08 pp, p 0.060, DD −47% vs constant 1.25x +0.98 pp, p 0.27, DD −65%).

What it does not buy:

* **Significance.** Mixing a sleeve with SPY scales its excess and its tracking error by the same
  factor, so after tax the after-tax information ratio stays ≈ the sleeve's (A2/A3 0.29-0.30 vs 3x sleeve 0.28;
  A1 0.24 = the 2x sleeve's 0.24). The never-sold core does not even improve the after-tax retention of the excess
  (CA/NONE score ratio 0.62-0.66 vs 0.64-0.68 for the sleeves alone).
* **A clean holdout.** On the 1930-1985 holdout the core + 3x structure has median p 0.17 across the parameter
  grid (items 1-3 pass for 13-15% of parameters, 0% for 2x sleeves). The pre-registered A2/A3 use the 3x
  SMA200/3% sleeve that the round-1 verifier picked *because* it passed all four histories, so their
  1930-1985 numbers (p 0.12-0.13) are not out of sample anyway.
* **Robust parameter choice.** Inside each structure, choosing the trend parameters on past data is
  worthless out of sample: walk-forward OOS ≈ the average parameter's OOS, and PBO is 0.59-0.75 on 1930-1985 /
  1930-2026. The within-family control E1 shows how much rides on the post-hoc band. E1 averages
  8 SMA-band rules (bands 1% and 3%) and scores +1.34 pp, p 0.39, vs +4.94 for the post-hoc SMA175/3%.
* **Execution realism on 1986+.** With a one-day signal lag, no A-design passes p ≤ 0.10 on 1986-2026
  (A1 0.27, A2 0.11, A3 0.12), exactly as for the sleeves alone. The same-close exit before Black
  Monday is still doing the work.
* **The multiple-testing deflation.** Deflated Sharpe ≤ 0.04 for every combination (12,360 trials).

Per group:

| group | design | verdict |
|---|---|---|
| A | never-sold SPY core + leveraged-trend sleeve (skimmed at exits) | **most robust structure; conditional, moderate-to-low confidence.** Passes items 1-3 on 2000-26 and 1986-26 (A2, A3), drawdown ≤ SPY's, but holdout p 0.12-0.30, PBO within the structure ≥ 0.5 in the 1930+ histories, lag-1 kills 1986+ significance, DSR ≤ 0.04. A3 is the best balance. |
| B | tax-managed momentum rotation (KX1/KX3) + 2x trend sleeve | **fail.** Higher IR than the 2x sleeve alone (diversification: excess correlation 0.21), but the rotation sleeve is flat or negative before 2000 (1986-99 analog menu), and the rotation's menu hindsight carries over (section 9). Weak since 2019 (5-year windows from 2019 beat SPY 0-27% of the time). |
| C | leveraged trend with the safe leg replaced by SPY or by a momentum rotation | **fail.** Keeping ≥1x equity in the off state removes the trend rule's crash protection: drawdowns −61% to −68% (SPY −55%), −83% to −85% in 1930-85; p no better than the Treasury-leg versions. The rotation off-leg is worse than SPY. |
| D | equal-risk mixes of the round-1 best-of-family candidates | **fail.** Best Sharpe ratios (0.62-0.66 vs SPY 0.51) and among the smallest drawdowns (−35% to −44%), but small excess (+0.95 to +2.28), p 0.03-0.11, 0% of 5-year windows since 2019 ahead of SPY, the testable subset (D3) is flat before 2000 (p 0.31), DSR ≤ 0.012. |
| E | within-family control: ensemble of 8 SMA-band 2x rules | **fail** (+1.34, p 0.39): the leveraged-trend edge in CA depends on the wide band chosen after the fact. |

**If the user wants to use the leveraged trend at all, the only form this round can defend is A3-like:**
keep ≥ 75% in SPY that is never sold and run a 25% sleeve that holds a 3x S&P fund while SPY is
above its 200-day average (3% band, checked daily, traded at the close) and intermediate Treasuries
otherwise, moving the sleeve's excess to the core at each exit. The honest expectation is about **+1.5
to +2 pp/yr after CA tax** (grid median for this structure: +1.4 / +1.8 / +1.9 / +1.6 pp on 2000-26 / 1986-26 /
1930-85 / 1930-2026). Drawdowns are roughly SPY's or smaller, and the bootstrapped chance of trailing SPY over 20 years is about 21%.
**That is an expected-value bet with moderate-to-low confidence, not a "good confidence" strategy.**

## 1. What I built and how it was checked

* `research/lab/families/r2_combos.py`:
  * **kind `r2_combos.sleeves`.** Any lab strategies run side by side as sleeves of one account. Each sleeve runs
    its own, unchanged rule on its own capital (virtual cash). It sees only its own positions, value
    and realized gains, so a "1% gain budget" is 1% of the sleeve. All sleeves share one tax return:
    the engine nets every gain and loss of the account once a year.
    * The January tax bill is charged to the sleeves in proportion to the tax their own net gains caused.
    * A ticker used by two sleeves is traded by the later one through an identical-data clone
      (`research/lab/data/R2C_C<k>_<T>.csv`), so each sleeve keeps its own FIFO lots, which is specific-lot
      identification by sleeve.
    * `skim`: at each trend exit of the leveraged sleeve, which realizes its gains anyway, the value above its
      target share is moved to the other sleeves, which buy their current holdings pro rata. No other
      cross-sleeve trade ever happens, so a never-sold core stays never sold.
  * **signals.** `r2_combos.ens` is an ensemble of SMA-band trend rules: exposure = the share of rules on.
    `r2_combos.trot` is a leveraged trend whose off-leg is a momentum rotation.
* **Validation (`scratch/r2_combos/v0_validate.py`, single starts).**
  * A one-sleeve combo of L2 reproduces L2 exactly (CA and NONE); the same holds for KX1 (difference 7e-16).
  * A core-only combo = SPY buy-and-hold (8e-7, from the 0.999999 fill factor).
  * L2 split into two half sleeves through clones gives L2 (4e-6).
  * KX1 split in two gives KX1 within 0.6%. That rule is path-chaotic: dust orders and partial-sale thresholds act on halves.
  * Sleeve cash always sums to engine cash.
* **Simulator (`scratch/r2_combos/sim2.py`, `simrun.py`).** A lot-level re-implementation of the SPY-core + trend-sleeve
  designs and the ensemble, with the engine's tax accounting. Checked against the engine on every window of
  every start (`v1_sim2.py`):
  * 2000-2026: 10 designs × CA/NONE, max |CAGR difference| on any window 0.013 pp;
  * 1986-2026: 10 designs, max 0.07 pp;
  * score, full excess, boot_p and max DD identical to 4 decimals.

  It runs the verifier's 1930-1985 holdout (PRE) and 1930-2026 (SPLICE) worlds unchanged, and reproduces
  their L2/L3 numbers (PRE L2 +2.95; SPLICE L2 +3.48 / p 0.129, L3 +7.48 / p 0.024).
* New research data (no existing file touched): `R2C_VFINXR2XC` / `R2C_VFINXR3XC`, which are the SYN_*C formula applied to
  VFINXR (the repaired VFINX), so 1986+ leveraged legs carry the distribution-day fix. Plus the clone files.

## 2. The pre-registered set (`scratch/r2_combos/out/prereg.json`, written before any combination ran)

Components (exact round-1 / verification configs):

* **L2**: 2x S&P, SMA175, 3% band, daily, VFITX off (the verified conditional rule);
* **L3**: 3x, SMA200/3%, the verifier's only config passing all four histories;
* **KX1 / KX3**: tax-managed rotations;
* **VG**: value/growth switch;
* **SEAS**: tax-managed cyclical season;
* **EMA**: unlevered EMA100/200 → IEF/VFITX.

| | design | exposure trend on / off |
|---|---|---|
| A1 | 50% SPY never sold + 50% L2 sleeve, skim | 1.5x / 0.5x |
| A2 | 50% SPY + 50% L3 sleeve, skim | 2.0x / 0.5x |
| A3 | 75% SPY + 25% L3 sleeve, skim | 1.5x / 0.75x |
| A1d, A2d | A1, A2 without skim (sleeves drift) | drifts up (A2d: sleeve 83% of the account by 2025) |
| B1 | 75% KX1 + 25% L2, skim | 1.25x / 0.75x |
| B2 | 50% KX1 + 50% L2, skim | 1.5x / 0.5x |
| B3 | 50% KX3 + 50% L2, skim | 1.5x / 0.5x |
| B2d | B2 without skim | |
| C1 | L2 with SPY as the off leg (all-in) | 2x / 1x |
| C2 | 50% SPY never sold + 50% sleeve (3x SMA200/3% ↔ SPY), skim | 2x / 1x |
| C3 | L2 with KX1's ranking of the 22-ETF menu as the off leg | 2x / top-5 momentum ETFs |
| D1 | inverse-vol KX1 .235 / VG .235 / SEAS .231 / EMA .299 | ≈0.9x (estimated) |
| D2 | inverse-vol KX1 .196 / VG .196 / SEAS .192 / EMA .249 / L2 .167 | ≈1.0x (estimated) |
| D2te | inverse tracking error: KX1 .301 / VG .213 / SEAS .294 / EMA .113 / L2 .079 | 1.03x on average (measured) |
| D3 | inverse-vol KX1 .32 / EMA .407 / L2 .273 (the subset with 1986+ analogs) | ≈1.0x (estimated) |
| E1 | 2x ensemble: SMA {100,150,200,250} × band {1%, 3%}, daily, VFITX off | 0-2x in steps of 0.25 |

* **Excluded from D:**
  * TVT and the macro curve rules (verified fails: frozen leverage, two events);
  * stocks (survivorship);
  * TAA/global (≈0).
* **Weights.** Inverse vol uses each component's standalone 2000-2026 volatility: a disclosed mild hindsight on
  risk, none on return.
* **Average realized exposure, 2000 start** (`p10_inspect.py`): A1 1.22x, A2 1.59x, A3 1.30x, A2d 1.91x,
  B2 1.22x, C2 1.75x, D2te 1.03x. Skim needed only 3-5 transfers in 26 years.
* **Decision rules** (in `prereg.json`):
  * Q1 is the PROTOCOL §3 bar, with boot_p also averaged over the yearly starts 2000-2006.
  * Q2 asks whether a combination beats its best component on all of: (a) 10/15y beat rates, (b) worst 5/10y windows,
    (c) multi-start boot_p, (d) the long-history holdouts, (e) max drawdown.

## 3. ETF era, 2000-2026 (protocol `full`, 95 quarterly starts)

CA (primary). Bootstrap p for the 2000 start is from the first-start path; the "mean of 7 starts" column is
the stationary bootstrap of quarterly after-tax excess from each yearly start 2000-2006 (block 4 quarters),
averaged. DSR uses 12,360 trials.

| | score | full | 10y mean | beat 10/15/20y | worst 5y / 10y | boot p (2000 start) | boot p, mean of 7 starts | from 2002: score, beat 10/15y | max DD (SPY) | after-tax IR | Sharpe (SPY) | turnover | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L2 | +4.94 | +3.80 | +5.13 | 1.00 / 1.00 / 1.00 | -4.10 / +0.64 | 0.077 | 0.124 | +4.66, 1.00/1.00 | -47% (-55%) | 0.24 | 0.58 (0.51) | 1.33 | 0.004 |
| L3 | +7.42 | +6.25 | +7.53 | 1.00 / 1.00 / 1.00 | -6.32 / +0.81 | 0.061 | 0.082 | +6.92, 1.00/1.00 | -62% (-55%) | 0.28 | 0.55 (0.51) | 1.18 | 0.008 |
| KX1 | +0.93 | +1.82 | +1.07 | 0.91 / 0.89 / 0.96 | -4.96 / -0.47 | 0.011 | 0.128 | +0.80, 0.90/0.87 | -57% (-55%) | 0.45 | 0.57 (0.51) | 0.07 | 0.050 |
| KX3 | +0.99 | +1.84 | +1.17 | 0.90 / 0.85 / 0.96 | -6.01 / -0.38 | 0.011 | 0.218 | +0.81, 0.88/0.82 | -54% (-55%) | 0.42 | 0.58 (0.51) | 0.05 | 0.038 |
| VG | +1.16 | +1.83 | +1.06 | 0.88 / 1.00 / 1.00 | -4.84 / -3.13 | 0.040 | 0.037 | +1.11, 0.86/1.00 | -53% (-55%) | 0.32 | 0.58 (0.52) | 0.04 | 0.012 |
| SEAS | +0.64 | +1.18 | +0.71 | 0.84 / 0.91 / 1.00 | -2.01 / -0.79 | 0.025 | 0.173 | +0.49, 0.81/0.90 | -57% (-55%) | 0.28 | 0.54 (0.51) | 0.10 | 0.006 |
| EMA | +1.01 | +1.36 | +1.03 | 0.57 / 0.74 / 0.59 | -6.16 / -3.23 | 0.286 | 0.497 | +0.47, 0.51/0.69 | -40% (-55%) | 0.13 | 0.62 (0.51) | 0.21 | 0.000 |
| A1 | +2.58 | +1.99 | +2.66 | 1.00 / 1.00 / 1.00 | -1.97 / +0.36 | 0.079 | 0.127 | +2.43, 1.00/1.00 | -38% (-55%) | 0.24 | 0.60 (0.51) | 0.63 | 0.003 |
| A2 | +4.01 | +3.29 | +4.04 | 1.00 / 1.00 / 1.00 | -2.53 / +0.40 | 0.052 | 0.074 | +3.71, 1.00/1.00 | -41% (-55%) | 0.30 | 0.56 (0.51) | 0.53 | 0.009 |
| A3 | +2.08 | +1.68 | +2.09 | 1.00 / 1.00 / 1.00 | -1.23 / +0.20 | 0.060 | 0.074 | +1.92, 1.00/1.00 | -47% (-55%) | 0.29 | 0.55 (0.51) | 0.24 | 0.009 |
| A1d | +2.79 | +2.31 | +2.90 | 1.00 / 1.00 / 1.00 | -1.97 / +0.32 | 0.093 | 0.144 | +2.62, 1.00/1.00 | -40% (-55%) | 0.22 | 0.58 (0.51) | 0.94 | 0.003 |
| A2d | +4.41 | +4.16 | +4.49 | 1.00 / 1.00 / 1.00 | -2.53 / +0.41 | 0.078 | 0.096 | +4.07, 1.00/1.00 | -55% (-55%) | 0.27 | 0.53 (0.51) | 0.93 | 0.006 |
| B1 | +2.05 | +1.67 | +2.14 | 0.99 / 0.94 / 1.00 | -3.31 / -0.03 | 0.058 | 0.066 | +1.90, 0.98/0.92 | -47% (-55%) | 0.32 | 0.59 (0.51) | 0.37 | 0.011 |
| B2 | +3.06 | +2.38 | +3.18 | 1.00 / 1.00 / 1.00 | -3.13 / +0.29 | 0.056 | 0.074 | +2.87, 1.00/1.00 | -39% (-55%) | 0.28 | 0.61 (0.51) | 0.67 | 0.006 |
| B3 | +3.04 | +2.73 | +3.21 | 1.00 / 0.98 / 1.00 | -3.97 / +0.62 | 0.036 | 0.084 | +2.83, 1.00/0.97 | -39% (-55%) | 0.32 | 0.63 (0.51) | 0.65 | 0.011 |
| B2d | +3.19 | +2.97 | +3.35 | 1.00 / 1.00 / 1.00 | -3.09 / +0.07 | 0.035 | 0.080 | +2.97, 1.00/1.00 | -40% (-55%) | 0.31 | 0.62 (0.51) | 0.86 | 0.009 |
| C1 | +3.50 | +1.96 | +3.63 | 1.00 / 1.00 / 1.00 | -2.71 / +0.42 | 0.143 | 0.107 | +3.77, 1.00/1.00 | -62% (-55%) | 0.21 | 0.47 (0.51) | 1.38 | 0.002 |
| C2 | +3.55 | +2.34 | +3.58 | 1.00 / 1.00 / 1.00 | -1.58 / +1.18 | 0.085 | 0.062 | +3.69, 1.00/1.00 | -61% (-55%) | 0.25 | 0.49 (0.51) | 0.59 | 0.005 |
| C3 | +3.54 | +1.90 | +3.65 | 1.00 / 1.00 / 1.00 | -2.47 / +0.36 | 0.156 | 0.091 | +3.81, 1.00/1.00 | -61% (-55%) | 0.18 | 0.47 (0.51) | 1.47 | 0.001 |
| D1 | +0.95 | +1.38 | +0.99 | 0.86 / 0.98 / 1.00 | -3.42 / -1.22 | 0.106 | 0.165 | +0.78, 0.85/0.97 | -38% (-55%) | 0.24 | 0.63 (0.52) | 0.12 | 0.003 |
| D2 | +1.76 | +2.06 | +1.82 | 0.91 / 1.00 / 1.00 | -2.67 / -0.82 | 0.067 | 0.120 | +1.57, 0.90/1.00 | -35% (-55%) | 0.28 | 0.66 (0.52) | 0.48 | 0.005 |
| D2te | +1.33 | +1.65 | +1.39 | 0.91 / 1.00 / 1.00 | -3.10 / -0.71 | 0.032 | 0.060 | +1.20, 0.90/1.00 | -44% (-55%) | 0.34 | 0.62 (0.52) | 0.31 | 0.012 |
| D3 | +2.28 | +2.32 | +2.39 | 0.85 / 0.85 / 1.00 | -2.79 / -0.70 | 0.105 | 0.190 | +1.94, 0.83/0.82 | -39% (-55%) | 0.25 | 0.65 (0.51) | 0.59 | 0.004 |
| E1 | +1.34 | +0.88 | +1.39 | 0.67 / 0.77 / 0.96 | -3.81 / -2.41 | 0.390 | 0.448 | +0.95, 0.63/0.72 | -48% (-55%) | 0.06 | 0.48 (0.51) | 2.17 | 0.000 |

FED (35/15) is uniformly better for the trend sleeves (lower short-term rate). Compact:

| | score | full | 10y mean | beat 10/15/20y | worst 5y / 10y | boot p (2000 start) | boot p, mean of 7 starts | from 2002: score, beat 10/15y | max DD (SPY) | after-tax IR | Sharpe (SPY) | turnover | DSR |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| L2 | +6.00 | +4.94 | +6.23 | 1.00 / 1.00 / 1.00 | -4.42 / +1.33 | 0.041 | 0.064 | +5.73, 1.00/1.00 | -44% (-55%) | 0.30 | 0.64 (0.51) | 1.36 | 0.008 |
| L3 | +8.82 | +7.71 | +8.96 | 1.00 / 1.00 / 1.00 | -6.75 / +1.45 | 0.038 | 0.054 | +8.30, 1.00/1.00 | -60% (-55%) | 0.32 | 0.59 (0.51) | 1.19 | 0.013 |
| KX1 | +1.05 | +1.96 | +1.20 | 0.93 / 0.91 / 1.00 | -5.51 / -0.46 | 0.009 | 0.108 | +0.91, 0.92/0.90 | -56% (-55%) | 0.47 | 0.58 (0.51) | 0.07 | 0.064 |
| KX3 | +1.10 | +1.94 | +1.30 | 0.90 / 0.87 / 1.00 | -6.73 / -0.38 | 0.006 | 0.181 | +0.91, 0.88/0.85 | -54% (-55%) | 0.44 | 0.58 (0.51) | 0.05 | 0.048 |
| VG | +1.26 | +1.88 | +1.16 | 0.88 / 1.00 / 1.00 | -5.38 / -3.36 | 0.041 | 0.038 | +1.21, 0.86/1.00 | -53% (-55%) | 0.32 | 0.58 (0.52) | 0.04 | 0.013 |
| SEAS | +0.73 | +1.22 | +0.81 | 0.85 / 0.94 / 1.00 | -2.22 / -0.76 | 0.027 | 0.163 | +0.57, 0.83/0.92 | -57% (-55%) | 0.28 | 0.54 (0.51) | 0.10 | 0.007 |
| EMA | +1.24 | +1.84 | +1.26 | 0.57 / 0.74 / 0.96 | -6.83 / -3.45 | 0.225 | 0.427 | +0.64, 0.51/0.69 | -34% (-55%) | 0.17 | 0.69 (0.51) | 0.20 | 0.001 |
| A1 | +3.17 | +2.64 | +3.29 | 1.00 / 1.00 / 1.00 | -2.12 / +0.73 | 0.042 | 0.064 | +3.03, 1.00/1.00 | -36% (-55%) | 0.30 | 0.64 (0.51) | 0.65 | 0.009 |
| A2 | +4.84 | +4.18 | +4.90 | 1.00 / 1.00 / 1.00 | -2.92 / +0.73 | 0.032 | 0.047 | +4.52, 1.00/1.00 | -42% (-55%) | 0.34 | 0.59 (0.51) | 0.58 | 0.016 |
| A3 | +2.54 | +2.18 | +2.57 | 1.00 / 1.00 / 1.00 | -1.42 / +0.37 | 0.034 | 0.046 | +2.37, 1.00/1.00 | -46% (-55%) | 0.34 | 0.57 (0.51) | 0.28 | 0.016 |
| A1d | +3.44 | +3.14 | +3.58 | 1.00 / 1.00 / 1.00 | -2.12 / +0.68 | 0.053 | 0.078 | +3.27, 1.00/1.00 | -39% (-55%) | 0.28 | 0.63 (0.51) | 1.02 | 0.006 |
| A2d | +5.32 | +5.36 | +5.42 | 1.00 / 1.00 / 1.00 | -2.92 / +0.75 | 0.050 | 0.067 | +4.95, 1.00/1.00 | -55% (-55%) | 0.30 | 0.57 (0.51) | 1.00 | 0.011 |
| B1 | +2.43 | +2.07 | +2.54 | 1.00 / 1.00 / 1.00 | -3.69 / +0.29 | 0.022 | 0.026 | +2.27, 1.00/1.00 | -47% (-55%) | 0.40 | 0.62 (0.51) | 0.38 | 0.030 |
| B2 | +3.69 | +3.09 | +3.84 | 1.00 / 1.00 / 1.00 | -3.43 / +0.76 | 0.026 | 0.028 | +3.50, 1.00/1.00 | -37% (-55%) | 0.35 | 0.66 (0.51) | 0.69 | 0.018 |
| B3 | +3.67 | +3.35 | +3.87 | 1.00 / 1.00 / 1.00 | -4.40 / +1.13 | 0.015 | 0.035 | +3.45, 1.00/1.00 | -38% (-55%) | 0.38 | 0.66 (0.51) | 0.68 | 0.026 |
| B2d | +3.87 | +3.79 | +4.06 | 1.00 / 1.00 / 1.00 | -3.38 / +0.53 | 0.012 | 0.031 | +3.64, 1.00/1.00 | -38% (-55%) | 0.37 | 0.67 (0.51) | 0.92 | 0.022 |
| C1 | +4.41 | +2.81 | +4.54 | 1.00 / 1.00 / 1.00 | -2.16 / +0.47 | 0.068 | 0.040 | +4.78, 1.00/1.00 | -62% (-55%) | 0.28 | 0.51 (0.51) | 1.41 | 0.007 |
| C2 | +4.32 | +3.06 | +4.36 | 1.00 / 1.00 / 1.00 | -1.33 / +1.32 | 0.052 | 0.037 | +4.53, 1.00/1.00 | -61% (-55%) | 0.29 | 0.52 (0.51) | 0.62 | 0.009 |
| C3 | +4.46 | +2.75 | +4.56 | 1.00 / 1.00 / 1.00 | -2.47 / +0.36 | 0.076 | 0.034 | +4.82, 1.00/1.00 | -61% (-55%) | 0.25 | 0.51 (0.51) | 1.50 | 0.004 |
| D1 | +1.08 | +1.52 | +1.13 | 0.88 / 1.00 / 1.00 | -3.75 / -1.18 | 0.076 | 0.122 | +0.89, 0.86/1.00 | -38% (-55%) | 0.28 | 0.65 (0.52) | 0.12 | 0.005 |
| D2 | +2.10 | +2.52 | +2.18 | 0.92 / 1.00 / 1.00 | -2.83 / -0.61 | 0.029 | 0.066 | +1.90, 0.92/1.00 | -33% (-55%) | 0.33 | 0.69 (0.52) | 0.53 | 0.012 |
| D2te | +1.54 | +1.88 | +1.62 | 0.91 / 1.00 / 1.00 | -3.35 / -0.61 | 0.017 | 0.031 | +1.40, 0.90/1.00 | -44% (-55%) | 0.40 | 0.63 (0.52) | 0.34 | 0.026 |
| D3 | +2.78 | +2.97 | +2.91 | 0.94 / 0.98 / 1.00 | -3.14 / -0.39 | 0.042 | 0.104 | +2.42, 0.93/0.97 | -35% (-55%) | 0.31 | 0.71 (0.51) | 0.66 | 0.009 |
| E1 | +1.90 | +1.61 | +1.97 | 0.72 / 0.79 / 1.00 | -4.28 / -2.22 | 0.298 | 0.337 | +1.50, 0.68/0.74 | -45% (-55%) | 0.11 | 0.53 (0.51) | 2.14 | 0.000 |

* **Recency.** Five-year windows starting 2019 or later, with mean excess and share beating SPY:
  * L3 +4.0 (82%), A2 +2.0 (82%), A3 +1.0 (82%);
  * L2 −0.3 (55%), A1 −0.0 (55%);
  * B −1.2 to −1.7 (0-27%), D −1.3 to −2.1 (0%), KX1 −2.8 (9%);
  * C1/C2 +2.8/+3.9 (100%).
* **2020-2026 sub-period:** A2 −0.13, A3 −0.07, L2 −1.24, L3 −0.28, B2 −0.30, D2te −0.28.
* **Pre-tax, NONE regime.** Every combination looks strong before tax: A1 +4.15 (p 0.002), B2 +4.49 (p 0.000),
  D2te +1.72 (p 0.004). The CA/NONE score ratio is unchanged by the core:
  * L2 0.64, A1 0.62;
  * L3 0.68, A2 0.66, A3 0.65;
  * B1 0.77 and D2te 0.77, because the rotation sleeves are tax-efficient.

## 4. Long history 1986-2026 (protocol `long_r`, repaired VFINX, 151 quarterly starts)

Mapping:

* leveraged legs are `R2C_VFINXR2XC/3XC`, the core is VFINXR, the safe leg is VFITX > VUSTX > T-bills;
* KX sleeves run on PRE20, the pre-ETF analog of the 22-ETF menu, with a 1-day lag (mutual funds);
* `ho5`/`ho10` are windows ending before 2000, the true holdout for ETF-era designs.

CA:

| | score | full | beat 10/15y | worst 10y | ho5 mean (beat) | ho10 mean (beat) | boot p | max DD (VFINX) | DSR |
|---|---|---|---|---|---|---|---|---|---|
| L2 | +4.64 | +2.78 | 1.00 / 1.00 | +0.30 | +3.98 (0.92) | +3.38 (1.00) | 0.067 | -47% (-55%) | 0.004 |
| L3 | +7.77 | +6.19 | 1.00 / 1.00 | +0.74 | +9.86 (0.95) | +9.34 (1.00) | 0.028 | -62% (-55%) | 0.018 |
| KX1 | +0.95 | -0.91 | 0.66 / 0.80 | -3.29 | -0.16 (0.49) | -0.37 (0.41) | 0.893 | -61% (-55%) | 0.000 |
| KX3 | +1.08 | -0.29 | 0.67 / 0.83 | -1.77 | +0.32 (0.59) | -0.15 (0.41) | 0.624 | -54% (-55%) | 0.000 |
| EMA | +1.20 | -0.90 | 0.59 / 0.83 | -3.69 | -2.03 (0.00) | -2.50 (0.00) | 0.718 | -40% (-55%) | 0.000 |
| A1 | +2.44 | +1.39 | 1.00 / 1.00 | +0.18 | +2.14 (0.92) | +1.76 (1.00) | 0.088 | -38% (-55%) | 0.003 |
| A2 | +4.22 | +3.14 | 1.00 / 1.00 | +0.36 | +5.46 (0.95) | +5.07 (1.00) | 0.038 | -49% (-55%) | 0.017 |
| A3 | +2.20 | +1.58 | 1.00 / 1.00 | +0.18 | +2.90 (0.95) | +2.67 (1.00) | 0.046 | -47% (-55%) | 0.013 |
| A1d | +2.61 | +1.72 | 1.00 / 1.00 | +0.15 | +2.14 (0.92) | +1.82 (1.00) | 0.082 | -40% (-55%) | 0.003 |
| A2d | +4.61 | +4.50 | 1.00 / 1.00 | +0.38 | +5.53 (0.95) | +5.52 (1.00) | 0.038 | -58% (-55%) | 0.016 |
| B1 | +2.04 | +0.48 | 0.89 / 0.92 | -2.44 | +1.10 (0.86) | +0.87 (0.82) | 0.244 | -51% (-55%) | 0.000 |
| B2 | +2.98 | +1.37 | 0.93 / 0.96 | -1.24 | +2.18 (0.89) | +1.75 (1.00) | 0.087 | -43% (-55%) | 0.003 |
| B3 | +3.03 | +1.28 | 0.98 / 0.96 | -0.35 | +2.41 (0.89) | +1.71 (1.00) | 0.106 | -40% (-55%) | 0.002 |
| B2d | +3.04 | +1.45 | 0.91 / 0.97 | -1.32 | +2.15 (0.89) | +1.71 (1.00) | 0.132 | -42% (-55%) | 0.001 |
| C1 | +2.92 | +1.76 | 0.93 / 1.00 | -1.89 | +4.45 (0.78) | +3.77 (1.00) | 0.096 | -63% (-55%) | 0.003 |
| C2 | +3.44 | +2.63 | 0.95 / 1.00 | -0.95 | +5.53 (0.92) | +5.06 (1.00) | 0.046 | -61% (-55%) | 0.014 |
| C3 | +2.79 | +1.66 | 0.91 / 0.98 | -2.59 | +4.47 (0.76) | +3.80 (1.00) | 0.124 | -68% (-55%) | 0.002 |
| D3 | +2.26 | +0.63 | 0.85 / 0.88 | -1.70 | +0.43 (0.59) | +0.09 (0.65) | 0.310 | -40% (-55%) | 0.000 |
| E1 | +1.83 | +0.50 | 0.79 / 0.89 | -2.28 | +2.80 (0.89) | +2.36 (1.00) | 0.378 | -48% (-55%) | 0.000 |

* The A-designs keep 100% of pre-2000 10-year windows ahead (A1 +1.76, A2 +5.07, A3 +2.67 pp).
* The rotation sleeve is flat before 2000 (KX1 ho10 −0.37, p 0.89; KX3 −0.15), which drags every B and D design.
  B1 has p 0.24, B3 0.11, D3 0.31.
* **One-day signal lag** (decide on yesterday's close, trade today; simulator = engine), 1986-2026, CA:

  | | p, same close → lag 1 | max DD, same close → lag 1 | score, same close → lag 1 |
  |---|---|---|---|
  | L2 | 0.067 → 0.266 | −47% → −59% | +4.64 → +3.86 |
  | L3 | 0.028 → 0.115 | −62% → −79% | +7.77 → +7.57 |
  | A1 | 0.088 → 0.274 | −38% → −48% | +2.44 → +2.05 |
  | A2 | 0.038 → 0.108 | −49% → −63% | +4.22 → +4.14 |
  | A3 | 0.046 → 0.117 | −47% → −51% | +2.20 → +2.16 |
  | C2 | 0.046 → 0.120 | −61% → −63% | +3.44 → +3.36 |

  The combination does not remove the components' dependence on exiting on 1987-10-16's close.

## 5. 1930-1985 holdout and 1930-2026 (simulator)

These are the verifier's worlds, unchanged:

* the S&P with approximate dividends before 1986, then repaired VFINX;
* T-bill financing and a T-bill safe leg pre-1986;
* yearly starts; PRE windows end by 1985-10.

CA:

| | PRE: score / p / beat 10y / worst 10y / max DD | SPLICE: score / p / beat 10y / worst 10y / max DD |
|---|---|---|
| L2 | +2.95 / 0.289 / 0.83 / -7.41 / -67% | +3.48 / 0.129 / 0.89 / -7.41 / -67% |
| L3 | +7.17 / 0.123 / 0.87 / -11.75 / -88% | +7.48 / 0.024 / 0.93 / -11.75 / -88% |
| A1 | +1.59 / 0.295 / 0.85 / -2.51 / -68% | +1.85 / 0.132 / 0.90 / -2.51 / -68% |
| A2 | +3.99 / 0.122 / 0.91 / -3.30 / -77% | +4.09 / 0.031 / 0.95 / -3.30 / -77% |
| A3 | +2.08 / 0.132 / 0.91 / -1.53 / -75% | +2.13 / 0.034 / 0.95 / -1.53 / -75% |
| A1d | +1.71 / 0.292 / 0.83 / -2.51 / -68% | +1.98 / 0.122 / 0.89 / -2.51 / -68% |
| A2d | +4.58 / 0.086 / 0.89 / -3.30 / -77% | +4.59 / 0.014 / 0.94 / -3.30 / -77% |
| C1 | +2.82 / 0.334 / 0.70 / -6.05 / -85% | +2.70 / 0.216 / 0.79 / -6.05 / -85% |
| C2 | +3.97 / 0.125 / 0.83 / -3.10 / -83% | +3.67 / 0.030 / 0.89 / -3.10 / -83% |
| E1 | +3.02 / 0.203 / 0.83 / -5.18 / -67% | +2.33 / 0.231 / 0.82 / -5.18 / -67% |

* **Selection caveat.** L3 (SMA200/3%) was chosen in verification *because* it passed all four histories,
  1930-85 included. A2/A3/C2 numbers in PRE/SPLICE are therefore not out of sample for the sleeve. Section 6 removes
  the choice by running the whole parameter plane.
* **FED.** In 1930-85 the p-values fall below 0.10 for A2 (0.072), A3 (0.075), A2d (0.046), C2 (0.061) and E1 (0.096),
  but not for L2/A1 (0.18).
* **One-day lag, 1930-85:** A3 p 0.132 → 0.198, A2 0.122 → 0.191, A1 0.295 → 0.293, L3 0.123 → 0.217.

## 6. The core + sleeve structure across its parameter plane (post hoc, simulator)

The grid is core share {50%, 75%} × sleeve leverage {2x, 3x} × SMA {100…300 step 25} × band {0…5%},
daily, skim, CA. That is 216 configs per history. "All-in" is the verifier's grid of the same rules without a core.
Columns:

* **pass 1-3**: the share of parameter settings passing items 1-3;
* **WF**: walk-forward that picks the best trailing-10y parameter each year and scores its next 5 years;
* **avg**: the average parameter's 5-year OOS.

| history | structure | pass 1-3 | median score | median p | median 10y beat | median worst 10y | median max DD | WF OOS (beat) | avg OOS | PBO |
|---|---|---|---|---|---|---|---|---|---|---|
| 2000-26 | 75% core + 3x | 28% | +1.38 | 0.145 | 0.96 | -0.38 | -52% | +1.45 (0.87) | +1.23 | 0.50 |
| 2000-26 | 50% core + 3x | 31% | +2.65 | 0.141 | 0.94 | -0.78 | -48% | +2.78 (0.85) | +2.33 | 0.47 |
| 2000-26 | 75% core + 2x | 4% | +0.63 | 0.218 | 0.66 | -0.77 | -49% | +0.24 (0.57) | +0.11 | 0.58 |
| 2000-26 | 50% core + 2x | 4% | +1.17 | 0.220 | 0.66 | -1.58 | -42% | +0.43 (0.57) | +0.18 | 0.54 |
| 2000-26 | all-in 3x | 30% | +4.86 | 0.146 | 0.93 | -1.80 | -62% | - | - | - |
| 2000-26 | all-in 2x | 4% | +2.05 | 0.230 | 0.64 | -3.45 | -49% | - | - | - |
| 1986-26 | 75% core + 3x | 31% | +1.82 | 0.138 | 0.95 | -0.50 | -52% | +2.00 (0.93) | +1.31 | 0.35 |
| 1986-26 | 50% core + 3x | 35% | +3.44 | 0.122 | 0.95 | -1.04 | -63% | +3.89 (0.94) | +2.41 | 0.36 |
| 1986-26 | 75% core + 2x | 2% | +0.97 | 0.279 | 0.81 | -0.80 | -48% | +1.16 (0.83) | +0.67 | 0.47 |
| 1986-26 | 50% core + 2x | 6% | +1.83 | 0.273 | 0.81 | -1.65 | -48% | +2.17 (0.83) | +1.22 | 0.46 |
| 1986-26 | all-in 3x | 33% | +6.12 | 0.126 | 0.95 | -2.42 | -78% | - | - | - |
| 1986-26 | all-in 2x | 7% | +3.35 | 0.265 | 0.80 | -3.64 | -59% | - | - | - |
| 1930-85 | 75% core + 3x | 13% | +1.85 | 0.173 | 0.83 | -1.87 | -74% | +2.90 (0.94) | +2.87 | 0.68 |
| 1930-85 | 50% core + 3x | 15% | +3.50 | 0.166 | 0.82 | -4.15 | -75% | +4.84 (0.89) | +5.39 | 0.61 |
| 1930-85 | 75% core + 2x | 0% | +0.72 | 0.282 | 0.83 | -1.22 | -71% | +0.97 (0.86) | +1.13 | 0.75 |
| 1930-85 | 50% core + 2x | 0% | +1.36 | 0.287 | 0.80 | -2.59 | -66% | +1.83 (0.86) | +2.17 | 0.74 |
| 1930-85 | all-in 3x | 11% | +5.85 | 0.192 | 0.78 | -15.87 | -90% | - | - | - |
| 1930-85 | all-in 2x | 0% | +2.33 | 0.314 | 0.78 | -8.29 | -77% | - | - | - |
| 1930-2026 | 75% core + 3x | 41% | +1.64 | 0.104 | 0.82 | -1.98 | -74% | +2.41 (0.90) | +2.07 | 0.62 |
| 1930-2026 | 50% core + 3x | 43% | +3.09 | 0.100 | 0.82 | -4.37 | -75% | +4.29 (0.88) | +3.87 | 0.59 |
| 1930-2026 | 75% core + 2x | 0% | +0.69 | 0.287 | 0.78 | -1.32 | -71% | +0.99 (0.83) | +0.85 | 0.64 |
| 1930-2026 | 50% core + 2x | 0% | +1.31 | 0.297 | 0.77 | -2.86 | -66% | +1.87 (0.83) | +1.61 | 0.59 |
| 1930-2026 | all-in 3x | 33% | +5.40 | 0.137 | 0.79 | -16.04 | -91% | - | - | - |
| 1930-2026 | all-in 2x | 0% | +2.29 | 0.320 | 0.75 | -8.76 | -77% | - | - | - |

* **The structure is robust in sign, not in significance.** With a 3x sleeve, the median parameter has a
  positive excess in every history and median p 0.10-0.17. Items 1-3 pass for 13-43% of parameters.
* **With a 2x sleeve nothing is significant** (median p 0.22-0.29).
* **Versus all-in.** The core trades excess for tail risk at about the same pass rate:
  * the median worst 10-year window is −1.9 to −4.4 pp instead of −16 pp (3x, 1930-85 / 1930-2026);
  * the median drawdown is −74/−75% instead of −90/−91% (SPY −81%).
* **Choosing parameters is noise.** Walk-forward OOS ≈ the average parameter's, and PBO within each
  structure is 0.47-0.58 (2000-26), 0.35-0.47 (1986-26), 0.61-0.75 (1930-85) and 0.59-0.64 (1930-2026).
  Across the whole grid, PBO is low (0.11-0.29) only because the selection picks *more leverage*.
* **Band.** The 1930-85 holdout does not favour the wide bands the ETF era favours: for 3x sleeves with band ≥ 3%,
  0% of parameters pass items 1-3 there (median p 0.25).

## 7. Bootstrap risk (1930-2026 monthly after-tax paths, stationary 12-month blocks, 20,000 draws, CA)

| | max DD from 1930 | P(trail SPY) 10y / 20y | median excess 20y | 5th pct 20y | P(DD>60%) 20y (SPY) | P(DD>70%) 20y | P(DD>80%) 20y |
|---|---|---|---|---|---|---|---|
| L2 | -67% | 0.37 / 0.32 | +1.58 | -3.93 | 0.197 (0.199) | 0.053 | 0.008 |
| L3 | -88% | 0.26 / 0.19 | +4.71 | -4.59 | 0.685 (0.199) | 0.404 | 0.222 |
| A1 | -68% | 0.38 / 0.33 | +0.79 | -2.05 | 0.069 (0.199) | 0.014 | 0.002 |
| A2 | -77% | 0.26 / 0.20 | +2.39 | -2.35 | 0.282 (0.199) | 0.099 | 0.021 |
| A3 | -75% | 0.27 / 0.21 | +1.19 | -1.33 | 0.159 (0.199) | 0.055 | 0.009 |
| A1d | -68% | 0.37 / 0.32 | +1.05 | -2.46 | 0.090 (0.199) | 0.020 | 0.003 |
| A2d | -77% | 0.24 / 0.16 | +3.93 | -2.54 | 0.531 (0.199) | 0.229 | 0.063 |
| C1 | -85% | 0.42 / 0.37 | +0.78 | -2.97 | 0.521 (0.199) | 0.265 | 0.102 |
| C2 | -83% | 0.28 / 0.20 | +1.82 | -1.74 | 0.437 (0.199) | 0.207 | 0.078 |
| E1 | -67% | 0.43 / 0.39 | +0.85 | -3.97 | 0.180 (0.199) | 0.047 | 0.007 |

* A1 and A3 are the only designs whose chance of a >60% drawdown within 20 years is *below* SPY's.
* Every design trails SPY over 20 years in 20-39% of resampled paths.

## 8. Q2: does any combination beat its best component on robustness?

| combination | best-component comparison (CA) | (a) beat 10/15y | (b) worst 5/10y | (c) multi-start p | (d) holdouts | (e) max DD | all five? | IR combo vs components |
|---|---|---|---|---|---|---|---|---|
| A1 | vs L2 | yes | no | no | no | yes | no | 0.24 vs L2 0.24 |
| A2 | vs L3 | yes | no | yes | no | yes | no | 0.30 vs L3 0.28 |
| A3 | vs L3 | yes | no | yes | no | yes | no | 0.29 vs L3 0.28 |
| A1d | vs L2 | yes | no | no | no | yes | no | 0.22 vs L2 0.24 |
| A2d | vs L3 | yes | no | no | no | yes | no | 0.27 vs L3 0.28 |
| B1 | vs KX1, L2 | no | no | yes | no | no | no | 0.32 vs KX1 0.45, L2 0.24 |
| B2 | vs KX1, L2 | yes | no | yes | no | yes | no | 0.28 vs KX1 0.45, L2 0.24 |
| B3 | vs KX3, L2 | no | no | yes | no | yes | no | 0.32 vs KX3 0.42, L2 0.24 |
| B2d | vs KX1, L2 | yes | no | yes | no | yes | no | 0.31 vs KX1 0.45, L2 0.24 |
| C1 | vs L2 | yes | no | yes | no | no | no | 0.21 vs L2 0.24 |
| C2 | vs L3 | yes | yes | yes | no | yes | no | 0.25 vs L3 0.28 |
| C3 | vs L2, KX1 | yes | no | yes | yes | no | no | 0.18 vs L2 0.24, KX1 0.45 |
| D1 | vs KX1, VG, SEAS, EMA | no | no | no | n/a | yes | no | 0.24 vs KX1 0.45, VG 0.32, SEAS 0.28, EMA 0.13 |
| D2 | vs KX1, VG, SEAS, EMA, L2 | no | no | no | n/a | yes | no | 0.28 vs KX1 0.45, VG 0.32, SEAS 0.28, EMA 0.13, L2 0.24 |
| D2te | vs KX1, VG, SEAS, EMA, L2 | no | no | no | n/a | no | no | 0.34 vs KX1 0.45, VG 0.32, SEAS 0.28, EMA 0.13, L2 0.24 |
| D3 | vs KX1, EMA, L2 | no | no | no | no | yes | no | 0.25 vs KX1 0.45, EMA 0.13, L2 0.24 |
| E1 | vs L2 | no | no | no | no | no | no | 0.06 vs L2 0.24 |

* **Pre-registered answer: no combination passes all five.**
* **The A-designs.** They win (a) beat rates, (c) multi-start p (A2, A3) and (e) drawdown. They lose (b) and (d)
  because a 25-50% sleeve next to SPY has proportionally smaller worst-window and holdout *means*, a scale effect.
* **Scale-free comparison.** Beat rates in the holdouts are equal or better: PRE ex10 beat A1 0.85 vs L2 0.83,
  A2/A3 0.91 vs L3 0.87, SPLICE 0.95 vs 0.93. The rest is unchanged:
  * after-tax IR is about equal (A2/A3 0.29-0.30 vs 0.28);
  * P(trailing SPY at 20 years) is unchanged (A3 0.21 vs L3 0.19; A1 0.33 vs L2 0.32);
  * holdout p is unchanged (PRE A3 0.132 vs L3 0.123; SPLICE 0.034 vs 0.024).

  **The combination is safer, not more certain.**
* **B and D.** The rotation-containing combinations have a higher IR than their leveraged component but a lower
  one than KX1's (0.45). Their pre-2000 holdout is worse than the 2x sleeve's.

## 9. Rotation-containing combinations: hindsight, random menus, neighbourhood

Hindsight: the same combinations with QQQ removed from the rotation's menu (-Q), and with QQQ and XLK removed
(-QX; for D the seasonal basket also loses XLK). CA, protocol `full`:

| | score | full | beat 10/15y | worst 10y | boot p | multi-start p | after-tax IR | score from 2002 |
|---|---|---|---|---|---|---|---|---|
| KX1 | +0.93 | +1.82 | 0.91 / 0.89 | -0.47 | 0.011 | 0.128 | 0.45 | +0.80 |
| KX1-Q | +0.50 | +1.29 | 0.61 / 0.74 | -2.91 | 0.071 | 0.237 | 0.31 | +0.19 |
| KX1-QX | +0.12 | +0.14 | 0.49 / 0.64 | -4.09 | 0.443 | 0.667 | 0.03 | -0.34 |
| B1 | +2.05 | +1.67 | 0.99 / 0.94 | -0.03 | 0.058 | 0.066 | 0.32 | +1.90 |
| B1-Q | +1.73 | +1.25 | 0.85 / 0.85 | -1.68 | 0.147 | 0.126 | 0.23 | +1.44 |
| B1-QX | +1.45 | +0.99 | 0.72 / 0.81 | -2.91 | 0.218 | 0.343 | 0.18 | +1.07 |
| B2 | +3.06 | +2.38 | 1.00 / 1.00 | +0.29 | 0.056 | 0.074 | 0.28 | +2.87 |
| B2-Q | +2.84 | +2.10 | 0.97 / 0.94 | -0.84 | 0.090 | 0.117 | 0.24 | +2.56 |
| B2-QX | +2.66 | +1.81 | 0.84 / 0.89 | -1.80 | 0.138 | 0.201 | 0.21 | +2.32 |
| B3 | +3.04 | +2.73 | 1.00 / 0.98 | +0.62 | 0.036 | 0.084 | 0.32 | +2.83 |
| B3-Q | +2.70 | +1.99 | 0.97 / 0.94 | -0.05 | 0.107 | 0.194 | 0.24 | +2.43 |
| B3-QX | +2.45 | +2.06 | 0.84 / 0.87 | -2.17 | 0.095 | 0.230 | 0.24 | +2.13 |
| D2 | +1.76 | +2.06 | 0.91 / 1.00 | -0.82 | 0.067 | 0.120 | 0.28 | +1.57 |
| D2-QX | +1.56 | +1.90 | 0.78 / 0.91 | -2.12 | 0.086 | 0.214 | 0.27 | +1.31 |
| D2te | +1.33 | +1.65 | 0.91 / 1.00 | -0.71 | 0.032 | 0.060 | 0.34 | +1.20 |
| D2te-QX | +1.02 | +1.43 | 0.77 / 0.87 | -2.56 | 0.095 | 0.225 | 0.29 | +0.78 |

* **Without the two tech funds chosen with hindsight, the B and D combinations lose their significance.**
  * Multi-start p: B2 0.074 → 0.201, B1 0.066 → 0.343, B3 0.084 → 0.230, D2te 0.060 → 0.225, D2 0.120 → 0.214.
  * B1-QX also fails the 10-year beat rate (0.72).
  * Their after-tax IR falls to the 2x sleeve's level or below (0.18-0.29 vs 0.24).
* **What these combinations gain over the 2x sleeve alone runs through QQQ/XLK**, the same criterion-6
  failure as KX1/KX3 themselves (KX1-QX: +0.12, p 0.44).
* In FED, B2-QX and B3-QX keep boot p ≈ 0.05, but their multi-start p is 0.10-0.13.

Random menus: the 30 menus of verify_taxrot_robust (seeds 1-30, 15-25 funds drawn from BROAD_EQUITY_POOL_2003),
protocol `screen`, CA.

| | mean score | menus with score > 0 | mean full excess | mean 10y beat | mean boot p | menus passing items 1-3 |
|---|---|---|---|---|---|---|
| KX1 on the random menus | +0.42 | 70% | +0.70 | 0.48 | 0.344 | 3% |
| B1 on the random menus | +1.79 | 100% | +1.46 | 0.81 | 0.162 | 17% |
| B2 on the random menus | +2.97 | 100% | +2.27 | 0.95 | 0.073 | 63% |
| L2 alone (same protocol) | +5.12 | | +3.80 | 1.00 | 0.062 | |

* **B2 passes on 63% of the menus because its 2x sleeve passes on its own.**
  * B2's score is +0.21 pp above the linear mix 0.5 × rotation + 0.5 × sleeve (t 14). That is a small, consistent
    interaction from the skim and the shared tax return.
  * B2 is not more significant than the sleeve alone (mean p 0.073 vs 0.062).
* **The rotation half adds only its own random-menu edge**, about +0.4 pp × 0.5.

Neighbourhood of B2: the 2x sleeve's SMA {150, 175, 200, 225} × band {2, 3, 4%}, rotation share 50%.

| SMA / band | score | boot p | multi-start p | beat 10/15y |
|---|---|---|---|---|
| 150 / 2% | +1.81 | 0.158 | 0.203 | 0.96 / 0.87 |
| 150 / 3% | +2.74 | 0.111 | 0.144 | 0.96 / 1.00 |
| 150 / 4% | +2.92 | 0.097 | 0.130 | 0.91 / 0.94 |
| 175 / 2% | +2.21 | 0.158 | 0.194 | 0.84 / 0.94 |
| 175 / 3% | +3.06 | 0.056 | 0.074 | 1.00 / 1.00 |
| 175 / 4% | +2.82 | 0.087 | 0.088 | 0.97 / 0.98 |
| 200 / 2% | +1.95 | 0.164 | 0.198 | 0.78 / 0.85 |
| 200 / 3% | +2.45 | 0.096 | 0.141 | 0.87 / 0.89 |
| 200 / 4% | +2.78 | 0.044 | 0.091 | 0.96 / 0.94 |
| 225 / 2% | +1.84 | 0.146 | 0.195 | 0.81 / 0.83 |
| 225 / 3% | +2.33 | 0.063 | 0.130 | 0.87 / 0.89 |
| 225 / 4% | +2.22 | 0.095 | 0.168 | 0.73 / 0.79 |

* The pre-registered base (175/3%) is the best of the 12 settings.
* 6 of 12 settings pass items 1-3. Only 3 of 12 keep multi-start p ≤ 0.10: 175/3%, 175/4%, 200/4%.
* **Rotation share** (KX1 or KX3 at 25/50/75%, 2x sleeve at the rest):
  * KX1w0.25: score +4.01, p 0.055, multi-start p 0.098, IR 0.26;
  * KX1w0.5: score +3.06, p 0.056, multi-start p 0.074, IR 0.28;
  * KX1w0.75: score +2.05, p 0.058, multi-start p 0.066, IR 0.32;
  * KX3w0.25: score +4.00, p 0.053, multi-start p 0.104, IR 0.27;
  * KX3w0.5: score +3.04, p 0.036, multi-start p 0.084, IR 0.32;
  * KX3w0.75: score +2.08, p 0.029, multi-start p 0.070, IR 0.39;
  * every share passes items 1-3 on the incumbent menu;
  * a larger rotation share raises the IR but lowers the excess.

## 10. Battery for the finalists (A1, A2, A3, B2, B3, D2te; CA unless noted)

| | CA base: score, p | costs 15 / 35 bps per side: score (p) | 1986-2026, signal lag 1: score, p, ho10 (beat), max DD | annual distribution tax, CA excess engine → stricter, from 2000 / 2005 / 2010 / 2015 | wash-sale replay from 2000 / 2010 |
|---|---|---|---|---|---|
| A1 | +2.58, 0.079 | +2.41 (0.104) / +2.08 (0.164) | +2.05, 0.274, +0.39 (0.53), -48% | +1.99→+1.90 / +1.57→+1.58 / +0.53→+0.57 / +0.05→+0.10 | 1 events, 0.011 pp / 1 events, 0.018 pp |
| A2 | +4.01, 0.052 | +3.83 (0.058) / +3.49 (0.070) | +4.14, 0.108, +3.54 (0.82), -63% | +3.29→+3.20 / +2.83→+2.83 / +1.62→+1.66 / +0.23→+0.28 | 1 events, 0.010 pp / 1 events, 0.017 pp |
| A3 | +2.08, 0.060 | +1.99 (0.064) / +1.81 (0.082) | +2.16, 0.117, +1.88 (0.82), -51% | +1.68→+1.64 / +1.45→+1.45 / +0.82→+0.84 / +0.11→+0.14 | 1 events, 0.004 pp / 1 events, 0.007 pp |
| B2 | +3.06, 0.056 | +2.86 (0.044) / +2.44 (0.160) | +2.58, 0.435, +0.25 (0.53), -45% | +2.38→+2.33 / +2.35→+2.37 / +0.86→+0.93 / -0.23→-0.18 | 2 events, 0.005 pp / 1 events, 0.012 pp |
| B3 | +3.04, 0.036 | +2.86 (0.072) / +2.49 (0.140) | +2.63, 0.329, +0.34 (0.65), -46% | +2.73→+2.68 / +1.96→+1.98 / +1.00→+1.07 / +1.03→+1.08 | 1 events, 0.008 pp / 1 events, 0.013 pp |
| D2te | +1.33, 0.032 | +1.23 (0.038) / +1.04 (0.058) | n/a (no 1986+ version) | +1.91→+1.89 / +1.16→+1.18 / +0.65→+0.69 / +0.18→+0.21 | 10 events, 0.002 pp / 7 events, 0.003 pp |

Rotation-schedule offsets: the rotation sleeve's quarterly or semiannual rebalance months shifted by 1 or 2 months. Score, boot p and multi-start p, versus the base in brackets:

* B2 (base +3.06, p 0.056, multi-start 0.074): +1 month: +2.95, p 0.050, multi-start 0.127; +2 month: +2.89, p 0.064, multi-start 0.112.
* B3 (base +3.04, p 0.036, multi-start 0.084): +1 month: +2.96, p 0.014, multi-start 0.051; +2 month: +2.99, p 0.032, multi-start 0.062.
* D2te (base +1.33, p 0.032, multi-start 0.060): +1 month: +1.25, p 0.038, multi-start 0.089; +2 month: +1.24, p 0.046, multi-start 0.077.

* **Costs barely matter for the low-turnover designs.** At 35 bps per side, A2, A3 and D2te keep p ≤ 0.10
  (0.070 / 0.082 / 0.058).
  A1, B2 and B3, which have more turnover, lose it (0.14-0.16).
* **Wash sales cost ≤ 0.02 pp/yr.** The trend sleeve occasionally sells its 2x/3x fund at a loss and re-enters within
  30 days. Cross-sleeve matches appear only in D2te ($2k), where the clones overlap.
* **Annual distribution tax moves CA excess by −0.09 to +0.07 pp.** The Treasury off-leg is taxed yearly at the
  federal ordinary rate; the dividend tax on the SPY core also hits the benchmark.
  * Leveraged-fund payouts are not modelled. verify_lev_mech measured −0.1 to −0.45 pp for the all-in 3x rule,
    so roughly a quarter to a half of that applies to a 25-50% sleeve.
* **The excess is front-loaded.** Starts in 2010 or later earn far less (engine excess from 2015: A1 +0.05,
  A2 +0.23, A3 +0.11, B2 −0.23 pp/yr). The edge comes mostly from sidestepping the 2000-02 and 2008 bears.
* **One-day signal lag removes the 1986-2026 significance of every finalist.** The lagged pre-2000 10-year holdout
  stays positive for A2/A3 (+3.5 / +1.9 pp, 82% beat) but is near zero for A1, B2 and B3 (+0.25 to +0.39, 53-65% beat).

## 11. Diagnostics across the pre-registered set (CA, protocol `full`)

* **Walk-forward** (10y in-sample → 5y out of sample, yearly decisions): OOS +3.83 pp, beat SPY 92%, vs the
  average config's +2.15. The 5→3-year version gives +4.01.
* **PBO (CSCV)** on monthly after-tax excess:
  * 0.464 on the default window, where 3 late starters (D1/D2/D2te from 2000-07) are dropped;
  * 0.468 on the common window from 2000-08 (17 configs);
  * SPY-core / leverage subset (A, C, E) 0.51; rotation / equal-risk subset (B, D) 0.21.
* **Deflated Sharpe** at 12,360 trials ≤ 0.012 in CA for every combination (FED ≤ 0.04). Within the set alone
  (14 trials, observed Sharpe dispersion) the best config's DSR is 0.77.
* **Component after-tax excess correlations** (monthly, 2000-08..2026-07): L2-KX1 0.21, L2-SEAS −0.15, L2-EMA 0.63,
  KX1-VG 0.38, KX1-SEAS 0.14. The diversification is real, but the IRs it combines are 0.13-0.45.

## 12. Exploratory (after pre-registration): a loss-harvesting core next to the sleeve

This idea was added *after* pre-registration. It is the round-1 critic's first combination idea:
a SPY core that harvests losses next to a leveraged-trend sleeve that realizes gains, in one account,
so that the core's harvested losses offset the sleeve's gains in the joint tax return.

* **Core:** tax_structures' best SPY chain: SPY → IWB → VTI → VV → SCHX → IWV → SCHB at −15%, checked monthly,
  no swap back.
* **Sleeve and skim:** unchanged.
* X1 compares with A3, X2 with A1, X3 with A2.

| | score | full | beat 10/15y | worst 5y / 10y | boot p | multi-start p | IR | max DD | same with a never-sold core |
|---|---|---|---|---|---|---|---|---|---|
| X1 CA | +2.37 | +2.12 | 1.00 / 1.00 | -1.23 / +0.20 | 0.046 | 0.068 | 0.34 | -45% | A3: +2.08, p 0.060, multi-start 0.074, IR 0.29 |
| X1 FED | +2.78 | +2.49 | 1.00 / 1.00 | -1.42 / +0.37 | 0.030 | 0.050 | 0.36 | -45% | A3: +2.54, p 0.034, multi-start 0.046, IR 0.34 |
| X2 CA | +2.76 | +2.27 | 1.00 / 1.00 | -1.97 / +0.36 | 0.064 | 0.117 | 0.26 | -36% | A1: +2.58, p 0.079, multi-start 0.127, IR 0.24 |
| X2 FED | +3.32 | +2.82 | 1.00 / 1.00 | -2.12 / +0.73 | 0.036 | 0.064 | 0.32 | -36% | A1: +3.17, p 0.042, multi-start 0.064, IR 0.30 |
| X3 CA | +4.20 | +3.56 | 1.00 / 1.00 | -2.53 / +0.40 | 0.049 | 0.072 | 0.31 | -42% | A2: +4.01, p 0.052, multi-start 0.074, IR 0.30 |
| X3 FED | +4.98 | +4.35 | 1.00 / 1.00 | -2.92 / +0.73 | 0.031 | 0.049 | 0.34 | -43% | A2: +4.84, p 0.032, multi-start 0.047, IR 0.34 |

* **Harvesting adds +0.2 to +0.3 pp/yr in CA** and lowers p slightly.
* **The gain comes from one bear market.** From the 2000 start the core harvested twice: SPY → IWB in 2001-04 and
  IWB → VTI in 2002-08. Its later VTI purchases are skim deposits. From the 2010 start it never harvested, because
  the core was never 15% below its cost.
* **Wash-sale replay** (both directions, clones and identical indexes as one security): 1 event,
  $3,537 of $105,208 realized losses disallowed, cost 0.004 pp/yr.
* **Reading:** it is a real but small structural gain, and it does not change any verdict.
* **Not tested on 1986+:** the substitute chain has no pre-2000 funds, so there is no long-history check.

## 13. Configurations tried

About 340 new configurations, all reported. Count them in the DSR as 12,000 + 360 = 12,360 trials.

* **Pre-registered:** 17 combinations on 2000-2026 (CA/FED/NONE = 51 engine records), their 14 long-history versions
  plus 6 long-history component versions on 1986-2026 (CA/FED = 40 records).
* **Simulator, validated equal to the engine:**
  * 10 designs × 4 histories × CA/FED;
  * a one-day-lag variant of 7 designs × 3 histories;
  * the bootstrap of 10 designs;
  * the 216-point core + sleeve parameter plane × 4 histories (864 evaluations).
* **Rotation-combination robustness:**
  * hindsight 10 configs × CA/FED;
  * neighbourhood 15 new configs;
  * 60 random-menu combinations, plus 30 cached rotation controls and the 2x sleeve on `screen`.
* **Exploratory:** 3 harvesting-core combinations × CA/FED, plus the harvesting core alone.
* **Battery:**
  * 12 cost runs;
  * 5 one-day-lag 1986+ runs;
  * 6 rebalance-offset variants;
  * 48 single-start realism runs and 14 wash-sale replays.
* **Single-start validation and inspection runs:** 17.
* **Selection:** only the 17 pre-registered combinations were candidates. Everything else is a control,
  neighbourhood, holdout or stress test, and is reported as such.

## 14. Notes for the lab

1. **The sleeves kind's cache key** hashes `r2_combos.py` and the lab core, not the modules of the sleeves' own kinds or
   signals (`verify_lev_robust`, `tax_rotation`, `tax_structures`, ...). It is the same class of gap round 1 reported for
   wrapped signals. None of those files changed during these runs.
2. **`realism.py` charges no distributions on clones or on `SYN_*` funds.** For the battery I mapped clones to their
   originals in-process. Leveraged-fund payouts remain unmodelled; verify_lev_mech measured −0.1 to −0.45 pp for
   the all-in 3x rule, so roughly a quarter to a half of that applies to a 25-50% sleeve.
3. **Late starters still distort comparisons.** `metrics.monthly_matrix` now drops late starters for PBO, which silently
   removes the D-designs (2000-07 start) from the default-window PBO. I report a common-window PBO as well.
4. **The FED regime omits the 3.8% NIIT**, as noted in round 1. FED results above are therefore slightly flattering.

## Files

* Module: `research/lab/families/r2_combos.py`.
* Scripts (`research/lab/scratch/r2_combos/`):
  * `util.py` (configs, clones, statistics);
  * `v0_validate.py`, `v1_sim2.py` (validation);
  * `p1_prereg.py` (pre-registration), `p2_run.py` (engine runs), `p3_analyze.py` (statistics and diagnostics);
  * `sim2.py`, `simrun.py`, `p4_sim_holdout.py` (1930-85, 1930-2026, bootstrap);
  * `p5_grid.py`, `p5_analyze.py` (parameter plane);
  * `p6_bd.py`, `p6_analyze.py` (hindsight, random menus, neighbourhood);
  * `p7_battery.py`, `wash.py` (battery);
  * `p9_extras.py` (harvesting core), `p10_inspect.py` (mechanics), `p11_lag_sim.py` (one-day lag);
  * `p8_tables.py` (these tables).
* Outputs: `out/` (`prereg.json`, `p3_stats.json`, `p4_hist.json`, `p4_boot.json`, `p5_summary.json`,
  `grid_*_CA.csv`, `p6_summary.json`, `p7_*.json`, `p9_cfgs.json`, `p10_inspect.json`, `p11_lag_sim.json`,
  `p8_tables.md`).
* Data added: `research/lab/data/R2C_*.csv`, which are the clones and the VFINXR-based 2x/3x series.
