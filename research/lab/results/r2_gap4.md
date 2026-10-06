# r2_gap4: other ways the position ends (step-up at death, gifts of appreciated shares, a slow sale in retirement)

**Bottom line.** The protocol scores every window as if the whole account were sold on its last day. That is
a convention, and it is not neutral: it charges SPY's deferred gain in full, which flatters strategies that
realize gains along the way. I re-scored every round-1 finalist (plus the verified 2x lead, its neighbours and
calibration controls) under three ways the position can end, from the engine's own tax lots:

* **liquidation** (the protocol);
* **step-up at death / gift of appreciated shares** (unrealized gains forgiven, this year's realized tax still
  owed);
* **a 20-year sale in retirement** (long-term rates, highest-basis lots first, 7%/yr growth and discounting).

What changes:

* **The 2x SMA175/3% conditional lead loses its statistical support in California** when the position ends
  in a step-up or a gift, and becomes borderline under a slow retirement sale.
  * Under a step-up: boot_p 0.077 becomes 0.199 on 2000-2026, and 0.067 becomes 0.219 on 1986-2026. The score
    falls from +4.9 to +4.2 pp/yr, and the worst 10-year window turns negative (-1.5 pp/yr).
  * Under the 20-year retirement sale: boot_p is 0.110 / 0.120.
  * It keeps a positive expected excess in every history.
  * In FED (35/15) it survives (step-up p 0.091 / 0.048).
  * It moves from "conditional, moderate confidence" to "conditional, low confidence" for a CA investor who
    expects to hold until death or give the shares away, and to borderline for one who sells down slowly.
* **Round-2's r2_lev2x designs lose the same way** (§4c).
  * Its pick (2x SSO / IEF, SMA200 3%, deferral) goes from p 0.097 / 0.070 to 0.215 / 0.195 under a step-up,
    and fails the 10y/15y beat rates on 2000-26.
  * Under a step-up even FED loses its 1930-85 pass (p 0.074 → 0.118).
  * The never-sold-core CU.5 design, the only one of them passing all four histories under the protocol,
    fails 2000-26 and 1930-85 under a step-up.
* **Every other verdict stands.**
  * The 3x family still fails. It now also fails bar items 1-3 under the step-up in CA (p 0.108-0.217).
  * The frozen tax-managed rotations (KX3, KX1, the site preset, B378) barely move: score -0.03 to +0.07 under
    the step-up, +0.15 to +0.17 under the retirement sale. They keep failing for their old reasons (items 4, 6
    and 7).
  * Unlevered trend and TAA timing rules lose 0.4-1.7 pp/yr of score and stay failures. The macro curve
    rules lose about 1.1 pp of full-period excess.
* **Nothing new passes. SPY buy-and-hold remains the default for the taxable account, and its case gets
  stronger** for anyone who never intends to sell.

Across all 108 finalists, the step-up changes the CA score by a median of **-0.50 pp/yr** (range -2.49 to
+0.59; FED -0.15). The size of the change tracks turnover (Spearman -0.88). The pure cost of realizing
gains, measured on SPY itself, is **1.6-2.2 times as large under a step-up as under the protocol's liquidation**:

* selling and re-buying SPY every 366 days costs -1.13 pp/yr under liquidation, -2.43 under a step-up and -1.41
  under the retirement sale;
* doing it every 182 days costs -3.01 / -4.84 / -3.61.

All numbers are after-tax excess CAGR versus SPY (VFINXR on 1986+) in percentage points per year, unless
stated. Main regime CA (48.1% short-term / 28.1% long-term), secondary FED (35/15).

## 1. What I built and how it was checked

`research/lab/families/r2_gap4.py` adds `TermGate`, a subclass of `core.Gate`. At every checkpoint and every
month end it values the engine's current state, including its FIFO lots, realized-gain buckets and loss
carryforward, under each of these treatments:

| treatment | value at the window's end | who it describes |
|---|---|---|
| `liq` (protocol) | equity - tax(this year's realized gains) - tax(all unrealized gains, short- or long-term by lot age, after the carryforward) | sells everything that day (the site's number) |
| `eq` | pre-liquidation equity | the critic's cache-only step-up proxy; it forgets the tax still owed on gains realized earlier in the same year |
| `step` | equity - tax(this year's realized gains, net of the carryforward) | dies holding the account: basis is stepped up, unrealized gains **and losses** vanish, the unused carryforward dies |
| `donate` | equity - tax(this year's realized gains + loss lots sold first) | gives the appreciated lots to charity (deduction at market value, same as a cash gift) and harvests the loss lots |
| `ret_g{g}_n{N}` | cash-equivalent value of selling the book in N equal annual slices; headline g = 7%, N = 20 | retires and sells down slowly |

How the `ret_g{g}_n{N}` sell-down works:

* The lots are frozen at the window's end. The strategy stops trading, which favours the strategies that
  realize gains.
* 1/N of the shares is sold at the end of each of years 1..N, so every sale is long-term.
* Lots are sold in minimum-tax order (highest basis/value first, losses first). This is the multi-ticker
  version of HIFO.
* Losses are netted and carried forward, using the carryforward left at the window's end.
* Every asset grows at the same rate g after the window, and g is also the discount rate. This isolates the
  tax state of the two books from what each happened to hold.
* The value is the **cash-equivalent**: the amount of fresh money that, sold down the same way, gives the same
  present value of after-tax proceeds:
  * ret = cash - fy_tax + (H - PV(taxes)) / f, with f = 1 - t_lt (1 - a/N) and a = Σ(1+g)^-k;
  * a book with no embedded gain is worth exactly its value;
  * g = 0 gives liquidation with every lot at the long-term rate (`ret_g0_n20`);
  * g → ∞ tends to the step-up.

The same treatment is applied to the benchmark (SPY bought once, one lot) on the same dates.

Checks:

* **Exact reproduction.** For the 135 (config, regime) records the lab already had cached on `full`, the
  recorder's `liq` and `eq` equal the cached values at every one of 725,423 checkpoints and month ends, with a
  relative difference of 0.0 (`validate_all.py`).
* **Sanity.** SPY run as a strategy shows 0.00 excess under every treatment, on `full` and on `long_r`.
* **Simulator.** For the 1986-2026, 1930-1985 and 1930-2026 histories I extended verify_lev_robust's validated
  single-lot simulator in the same way (`scratch/r2_gap4/simx.py`). On `full` it reproduces the engine
  treatment values for 2x SMA175/3%, 3x SMA175/3% and 3x SMA200/2% in all 847 windows of each config. The
  largest difference in window CAGR is below 0.001 pp, for liq, step and ret alike (`validate_simx.py`).
* **Retirement value.** Unit checks of the retirement valuation: a fresh-basis book is worth its value; g = 0
  gives the long-term liquidation value; g = 5 (500%/yr) gives 99.7% of the step-up value.

Statistics are the protocol's: score = mean of 5/10/15-year mean excess, full = first start to 2026-07, beat
rates, and boot_p (stationary bootstrap of the first start's monthly after-tax excess). Following the lab
note, I also report boot_p averaged over the five yearly starts 2000-2004 (`boot_p_mean`) and the to-end
excess averaged over the first 16 quarterly starts.

## 2. Calibration: what each ending does to a pure realizer

Same pre-tax exposure as the benchmark; the only difference is how often gains are realized.

| SPY, sold and re-bought (control) | protocol liq | step-up | retire 20y g=7% | liq at long-term rates (ret g=0) |
|---|---|---|---|---|
| every 366 days (long-term gains only), 2000-26 CA | -1.13 | **-2.43** | -1.41 | -0.86 |
| every 182 days (short-term gains only), 2000-26 CA | -3.01 | **-4.84** | -3.61 | -2.97 |
| every 366 days, 1986-2026 CA (VFINXR) | -1.24 | -2.69 | -1.51 | -0.99 |
| every 182 days, 1986-2026 CA (VFINXR) | -3.35 | -5.32 | -3.94 | -3.32 |
| every 366 days, 2000-26 FED | -0.84 | -1.37 | -0.88 | -0.58 |
| every 182 days, 2000-26 FED | -2.70 | -3.62 | -3.02 | -2.66 |

Figures are scores in pp/yr.

The protocol's convention has two opposite biases.

* **It charges SPY's deferred gain in full on the last day, which favours realizers.** SPY's 2000-26 book is
  24.7% embedded tax. The step-up removes that charge and the retirement sale shrinks it, to a 15.1% haircut
  at g = 7%.
* **It taxes the realizer's lots younger than a year at short-term rates on that same day, which penalizes
  realizers a little.** Selling at long-term rates instead (ret g = 0) lifts the 2x lead from +4.94 to +5.18.

For anyone who would hold to a step-up, the first bias dominates. For a 20-year sale at g ≥ about 4%, it
still dominates mildly.

End-of-run tax state, CA, from the first start to 2026-07 (`endstate.py`):

| | equity | tax owed on 2026 realized gains | embedded liquidation tax | taxes paid en route |
|---|---|---|---|---|
| SPY buy-and-hold | 818k | 0% | 24.7% | 0 |
| 2x SMA175/3% lead | 1,767k | **6.3%** | 5.9% | 520k |
| 3x SMA175/3% (C1) | 4,003k | 7.5% | 8.3% | 1,084k |
| KX3 | 1,285k | 0.3% | 24.4% | 23k |
| site preset (INC) | 1,198k | 0.3% | 24.7% | 14k |
| uninv540 minlen90 | 1,558k | 1.4% | 0.0% | 550k |

## 3. Every finalist on 2000-2026 (engine, `full`): which conclusions change

Reruns: 109 configs × CA and FED × 10 treatments. The 109 are:

* the 98 distinct round-1 candidate configs in `_lead/r1/*.json`, the incumbent preset among them;
* the verified 2x lead;
* 5 leveraged neighbours, including real SSO;
* 2 constant-leverage controls and 2 churn controls;
* 1 sanity check.

The full tables are in `scratch/r2_gap4/full_tables.md`, `full_table.csv` and `key_tables.md`.

**How many pass bar items 1-3** (score > 0 and full > 0; 10y beat ≥ 0.75 and 15y beat ≥ 0.85; boot_p ≤ 0.10):

| treatment | CA passes | lose vs liq | gain vs liq | FED passes | lose (FED) | gain (FED) |
|---|---|---|---|---|---|---|
| liq (protocol) | 25 | - | - | 31 | - | - |
| eq (critic's proxy) | 13 | 12 | 0 | 24 | 7 | 0 |
| **step-up** | **14** | **11** | 0 | **23** | **8** | 0 |
| donate | 14 | 11 | 0 | 23 | 8 | 0 |
| **retire 20y g=7%** | **25** | 3 | 3 | **30** | 2 | 1 |
| retire 20y g=0 (all lots at long-term rates) | 25 | 1 | 1 | 31 | 0 | 0 |

The counts cover 108 configs, the sanity row excluded. They include the stock-picking configs (survivorship-
biased upper bounds); F2, F3 and W1 pass, and F1 fails, under every treatment.

**Key finalists**, CA, 2000-2026. Each cell is score / full / 10y beat / 15y beat / boot_p, and P = passes
items 1-3.

| finalist | liq (protocol) | step-up | retire 20y, g=7% | verdict before → after |
|---|---|---|---|---|
| **2x SMA175/3% / VFITX (conditional lead)** | +4.94 / +3.80 / 1.00 / 1.00 / 0.077 P | +4.18 / +2.92 / 0.90 / 0.91 / **0.199** | +4.75 / +3.49 / 0.97 / 1.00 / **0.110** | CONDITIONAL → weaker (see §4) |
| KX3 (round-1 unlevered #1) | +0.99 / +1.84 / 0.90 / 0.85 / 0.011 P | +1.06 / +1.85 / 0.90 / 0.85 / 0.019 P | +1.16 / +1.89 / 0.90 / 0.87 / 0.009 P | FAIL (items 4/6/7), unchanged |
| KX1 | +0.93 / +1.82 / 0.91 / 0.89 / 0.011 P | +0.90 / +1.74 / 0.84 / 0.85 / 0.045 P | +1.10 / +1.85 / 0.93 / 0.89 / 0.017 P | FAIL, unchanged |
| site preset (INC) | +0.66 / +1.54 / 0.70 / 0.83 / 0.025 | +0.69 / +1.56 / 0.64 / 0.83 / 0.039 | +0.82 / +1.59 / 0.72 / 0.83 / 0.020 | FAIL, unchanged |
| B378 site combo | +0.79 / +1.05 / 0.82 / 0.91 / 0.073 P | +0.82 / +1.04 / 0.79 / 0.89 / 0.111 | +0.94 / +1.08 / 0.84 / 0.91 / 0.085 P | FAIL, unchanged |
| 3x SMA175/3% (C1, round-1 leveraged lead) | +9.65 / +7.10 / 1.00 / 1.00 / 0.029 P | +9.33 / +6.35 / 1.00 / 1.00 / 0.108 | +9.71 / +6.88 / 1.00 / 1.00 / 0.053 P | FAIL (tail risk), unchanged |
| 3x SMA200/2% (C2) | +6.07 / +4.84 / 1.00 / 1.00 / 0.117 | +5.59 / +4.24 / 0.91 / 1.00 / 0.217 | +6.13 / +4.71 / 0.97 / 1.00 / 0.151 | FAIL, unchanged |
| 3x SMA200/3% | +7.42 / +6.25 / 1.00 / 1.00 / 0.061 P | +6.84 / +5.57 / 0.94 / 1.00 / 0.152 | +7.39 / +6.07 / 1.00 / 1.00 / 0.084 P | FAIL, unchanged |
| low-vol 3x (C3) | +5.14 / +4.68 / 1.00 / 1.00 / 0.039 P | +4.24 / +4.28 / 1.00 / 1.00 / 0.118 | +5.03 / +4.69 / 1.00 / 1.00 / 0.053 P | FAIL, unchanged |
| SSO EMA100/200 (C4, 2006+) | +6.34 / +5.94 / 1.00 / 1.00 / 0.034 P | +6.32 / +5.44 / 1.00 / 1.00 / 0.094 P | +6.38 / +5.72 / 1.00 / 1.00 / 0.053 P | FAIL (holdout), unchanged |
| UPRO/IEF real (2009+) | +9.02 / +7.70 / 1.00 / 1.00 / 0.031 P | +8.13 / +6.39 / 1.00 / 1.00 / 0.154 | +8.93 / +7.30 / 1.00 / 1.00 / 0.069 P | not a candidate, unchanged |
| 2x SMA200/4% | +4.22 / +4.36 / 0.91 / 0.96 / 0.068 P | +3.43 / +3.62 / 0.64 / 0.83 / 0.171 | +4.01 / +4.04 / 0.88 / 0.91 / 0.080 P | neighbour: loses under step-up |
| real SSO 2x SMA175/3% (2006+) | +4.25 / +3.47 / 1.00 / 1.00 / 0.128 | +3.10 / +2.27 / 0.85 / 0.86 / 0.285 | +3.93 / +3.05 / 0.98 / 1.00 / 0.163 | - |
| 1.5x SMA175/3% | +2.63 / +2.08 / 0.81 / 0.77 / 0.220 | +1.62 / +1.14 / 0.57 / 0.74 / 0.372 | +2.35 / +1.73 / 0.69 / 0.77 / 0.267 | - |
| EMA100/200 unlevered | +1.01 / +1.36 / 0.57 / 0.74 / 0.286 | +0.61 / +0.76 / 0.54 / 0.68 / 0.390 | +0.84 / +1.10 / 0.54 / 0.72 / 0.302 | FAIL, by a wider margin |
| uninv540 minlen90 | +3.87 / +3.76 / 0.57 / 0.81 / 0.064 | +3.96 / +2.61 / 0.54 / 0.77 / 0.188 | +3.90 / +3.29 / 0.54 / 0.77 / 0.082 | FAIL, wider |
| GATED uninv540 & spy200 | +3.12 / +2.80 / 0.64 / 0.77 / 0.101 | +2.87 / +1.73 / 0.55 / 0.77 / 0.272 | +3.03 / +2.36 / 0.55 / 0.77 / 0.141 | FAIL, wider |
| TVT (gb 1%) | +3.40 / +4.85 / 0.98 / 1.00 / 0.011 P | +3.70 / +4.98 / 0.98 / 1.00 / 0.022 P | +3.67 / +4.95 / 0.98 / 1.00 / 0.014 P | FAIL (verify_levvt), unchanged |
| value/growth switch N5 | +1.16 / +1.83 / 0.88 / 1.00 / 0.040 P | +1.28 / +1.92 / 0.88 / 1.00 / 0.043 P | +1.25 / +1.89 / 0.88 / 1.00 / 0.024 P | FAIL (static tilt), unchanged |
| cyclical season Oct-May | +0.85 / +1.44 / 0.91 / 0.94 / 0.035 P | +0.90 / +1.46 / 0.84 / 0.87 / 0.039 P | +0.99 / +1.49 / 0.91 / 0.94 / 0.014 P | FAIL (static tilt), unchanged |
| RHN dip sleeve (UPRO, 2009+) | +3.44 / +4.73 / 1.00 / 1.00 / 0.013 P | +2.49 / +3.84 / 0.93 / 1.00 / 0.081 P | +3.34 / +4.60 / 1.00 / 1.00 / 0.027 P | not robust (DSR, walk-forward), unchanged |

Configs that lose the items-1-3 pass:

* **Under the step-up, CA (11).** The 2x lead; C1; the low-vol 3x; real UPRO SMA175; Monthly-100 3x;
  TX ConnorsRSI UPRO; LEV-HAA-UPRO; 3x SMA200/3%; 2x SMA200/4%; VUG buy-and-hold (p 0.096 → 0.112); and the
  B378 site combo (p 0.073 → 0.111).
* **Under the step-up, FED (8).** C2; Monthly-100 3x; the three short curve rules (after150, after180, and
  after180 with a core); RH rsi2 UPRO; INC WS; real SSO 2x.
* **Under the 20-year retirement sale.**
  * Losses: the 2x lead, Monthly-100 3x and LEV-HAA (CA), and two curve rules (FED).
  * Gains: SPY/SSO 50/50 never rebalanced (p 0.111 → 0.085, a constant-leverage control), INC WS (15y beat
    0.83 → 0.85) and the yearly re-fit sector SPY replica.
  * All of these sit on a threshold, and every one of them fails other bar items.

The step-up penalty tracks realization: the score change (step minus liq) against turnover has Spearman
-0.88 in CA (-0.86 FED). The largest loss is -2.49 pp, for the ConnorsRSI UPRO timer `F|crsi<15`.
Frozen books gain slightly under the step-up:

* TVT +0.30;
* VUG +0.25;
* static 3x buy-and-hold +0.59;
* KX3 +0.07.

Their unrealized gains are as large as SPY's or larger, so they benefit as much from the forgiveness.

**Start dependence is bigger than the terminal treatment for the rotations.**

* KX3's boot_p from the 2000-01 start is 0.011 / 0.019 / 0.009 (liq / step / retire), but averaged over the
  five yearly starts 2000-2004 it is 0.254 / 0.291 / 0.255 (max 0.81).
* The incumbent's averaged boot_p is 0.074 / 0.096 / 0.070.
* The 2x lead's averaged boot_p is 0.104 / 0.266 / 0.156. It was already borderline under the protocol, and
  the step-up pushes it clearly out.

## 4. The 2x conditional lead across histories (validated simulator)

The 2x lead is the 2x S&P fund held while SPY is above its 175-day SMA with a 3% band, else VFITX, checked
daily and traded at the close. Each cell is score / full / 10y beat / 15y beat / 10y min / boot_p (mean of 5
yearly starts):

| history (CA) | liq (protocol) | step-up | retire 20y g=7% | liq at long-term rates |
|---|---|---|---|---|
| 2000-2026 | +4.94 / +3.80 / 1.00 / 1.00 / +0.6 / 0.077 (0.104) **P** | +4.18 / +2.92 / 0.90 / 0.91 / **-1.5** / **0.199** (0.266) | +4.75 / +3.49 / 0.97 / 1.00 / -0.1 / **0.110** (0.156) | +5.18 / +3.91 / 1.00 / 1.00 / +0.8 / 0.073 **P** |
| 1986-2026 (repaired VFINX) | +4.62 / +2.79 / 1.00 / 1.00 / +0.3 / 0.067 (0.098) **P** | +3.73 / +2.08 / 0.89 / 0.95 / **-1.8** / **0.219** (0.257) | +4.37 / +2.53 / 0.97 / 1.00 / -0.5 / **0.120** (0.154) | +4.85 / +2.87 / 1.00 / 1.00 / +0.5 / 0.064 **P** |
| 1930-1985 holdout | +2.95 / +1.48 / 0.83 / 0.93 / -7.4 / 0.270 | +2.00 / +0.97 / 0.67 / 0.73 / -8.9 / 0.331 | +2.73 / +1.26 / 0.78 / 0.88 / -7.1 / 0.277 | +3.13 / +1.48 / 0.85 / 0.93 / -7.4 / 0.265 |
| 1930-2026 | +3.48 / +1.77 / 0.89 / 0.96 / -7.4 / 0.129 | +2.54 / +1.47 / 0.76 / 0.81 / -8.9 / 0.210 | +3.25 / +1.66 / 0.86 / 0.94 / -7.1 / 0.151 | +3.70 / +1.80 / 0.90 / 0.96 / -7.4 / 0.126 |
| 1986-2026 with one-day lag | +3.85 / +1.31 / 0.91 / 0.94 / -1.7 / 0.264 | +2.92 / +0.58 / 0.77 / 0.89 / -2.8 / 0.418 | +3.59 / +1.03 / 0.86 / 0.93 / -2.1 / 0.335 | - |
| **FED** 2000-2026 | +6.00 / +4.94 / 1.00 / 1.00 / +1.3 / 0.041 **P** | +5.73 / +4.56 / 1.00 / 1.00 / +0.3 / 0.091 **P** | +6.01 / +4.83 / 1.00 / 1.00 / +1.0 / 0.053 **P** | +6.24 / +5.06 / 1.00 / 1.00 / +1.5 / 0.037 **P** |
| **FED** 1986-2026 | +5.55 / +4.31 / 1.00 / 1.00 / +0.9 / 0.015 **P** | +5.20 / +4.01 / 0.99 / 1.00 / -0.0 / 0.048 **P** | +5.51 / +4.22 / 1.00 / 1.00 / +0.6 / 0.022 **P** | - |

Maximum drawdown is unchanged by the treatment: -47% against SPY's -55% on 2000-26, and -67% against -81% on
1930-85.

**Long horizons look better than the path-level p-value.** Under the step-up the rule still beat SPY in every
20-year window:

| history (CA) | 20-year mean excess, liq → step | worst 20-year window, liq → step | 20-year beat rate under step-up |
|---|---|---|---|
| 2000-26 | +4.53 → +3.58 | +3.17 → +1.98 | 100% |
| 1986-2026 | +4.72 → +3.79 | +1.96 → +0.41 | 100% |
| 1930-85 | +2.87 → +1.85 | -0.17 → -1.22 | 81% |

The 2000-26 and 1986-2026 20-year windows overlap heavily (all of them contain 2008), so they are not
independent evidence. The step-up makes the edge smaller and noisier. It does not remove it.

Retirement-sale sensitivity, 2000-26 CA, boot_p (score):

| g | N | boot_p | score |
|---|---|---|---|
| 0% | 20y | 0.073 | +5.18 |
| 4% | 20y | 0.092 | +4.89 |
| 7% | 20y | 0.110 | +4.75 |
| 10% | 20y | 0.116 | +4.65 |
| 7% | 10y | 0.087 | +4.91 |
| 7% | 30y | 0.121 | +4.64 |

On 1986-2026 the same pattern holds: 0.064 / 0.095 / 0.120 / 0.138, with N = 10 at 0.094 and N = 30 at 0.139.
**On the two modern histories boot_p stays at or below 0.10 only if the account is sold within about 10 years,
or if deferral is worth less than about 4-5%/yr.**

**Why the step-up hurts the p-value so much.** On the 2000-01 path, the monthly after-tax excess changes like
this (`decomp_2x.py`):

| treatment | mean excess | tracking error | strategy's monthly after-tax volatility | SPY's | boot_p |
|---|---|---|---|---|---|
| liq | +3.47 pp/yr | 14.4% | 15.5% | 14.0% | 0.077 |
| step-up | +2.65 pp/yr | 19.5% | 23.6% | 15.2% | 0.199 |

Two things happen:

* **The edge is smaller.** The 2x rule has already paid 520k of tax en route plus 6.3% for 2026, while SPY's
  24.7% embedded tax is forgiven.
* **The noise is larger.** Under liquidation accounting, while a freshly bought 2x lot is in a short-term
  gain, its value moves only about (1 - 48.1%) as much as its price, because the tax absorbs about half of
  every swing. A holder who never sells gets no such damping.

Both effects are real for an investor whose position ends in a step-up. The protocol's p-value is right only
for one who sells.

**Neighbourhood under each treatment.** I re-ran verify_lev_robust's daily grid: SMA 100-300 × band 0-5% ×
1.5/2/3x = 162 configs × 4 histories, CA. See §4b.

## 4b. Neighbourhood (daily grid) under each ending

verify_lev_robust's daily grid: SMA 100-300 × band 0-5% × leverage 1.5/2/3x, 54 configs per leverage,
CA. Each cell is the number of configs passing items 1-3:

| history | leverage | liq | `eq` | step-up | retire 20y g=7% | liq at long-term rates |
|---|---|---|---|---|---|---|
| 2000-26 | 2x | 2 | 0 | **0** | 1 | 2 |
| 2000-26 | 3x | 16 | 2 | 1 | 12 | 15 |
| 1986-2026 | 2x | 4 | 0 | **0** | 1 | 5 |
| 1986-2026 | 3x | 18 | 10 | 7 | 13 | 18 |
| 1930-85 | 2x | 0 | 0 | 0 | 0 | 0 |
| 1930-85 | 3x | 6 | 1 | 1 | 7 | 6 |
| 1930-2026 | 2x | 0 | 0 | 0 | 0 | 1 |
| 1930-2026 | 3x | 18 | 12 | 8 | 18 | 20 |
| any history | 1.5x | 0 | 0 | 0 | 0 | 0 |

Configs passing both 2000-26 and 1986-2026, and how many of those pass all four histories:

| treatment | pass both 2000-26 and 1986-2026 | pass all four |
|---|---|---|
| liq | 13: 2x 175/3% and 200/4%, plus 11 at 3x | 1 (3x 200/3%) |
| step-up | **1** (3x 200/4%) | **0** |
| retire 20y g=7% | 7, all 3x | 1 (3x 200/3%) |

The liq counts reproduce verify_lev_robust's daily-grid results exactly.

Median score falls less under the step-up at 3x (about -0.4 to -0.7 pp/yr) than at 2x (about -0.7 to -1.1
pp/yr). The step-up also forgives the rule's own unrealized gains, and those are larger at 3x. Either way,
what decides pass or fail is boot_p, which roughly doubles.

**Under a step-up no 2x configuration passes items 1-3 in any history, so item 5 (a passing parameter
neighbourhood) fails for the 2x lead. It also fails under the 20-year retirement sale: one config passes each
modern history, but not the same one.**

## 4c. Round-2 finalists from r2_lev2x, re-scored

r2_lev2x finished while this ran. I put its pick, the pick's SMA175 twin, the no-defer 2x rule and its
never-sold-core designs through the same recorder. The configs come from r2_lev2x's own `grid.cfg`, in its
ETF / LONG / SPLICE worlds, on `full`, `long_r` and `r2_splice`. 1930-85 means starts up to 1975 and windows
ending by 1985-10.

The `liq` column reproduces r2_lev2x's official numbers exactly. For example, the pick in CA gives +3.42 / p
0.097 on 2000-26, +4.57 / 0.070 on 1986-2026, +3.29 / 0.164 on 1930-85 and +3.96 / 0.068 on 1930-2026.

Each cell is score / full / 10y beat / 15y beat / boot_p, CA:

| design | history | liq (protocol) | step-up | retire 20y g=7% |
|---|---|---|---|---|
| **pick** `S200\|A2\|IEF\|D-h1` (2x SSO / IEF, SMA200 3%, 60-day short-term deferral) | 2000-26 | +3.42 / +3.79 / 0.79 / 0.87 / 0.097 P | +2.52 / +3.06 / **0.58** / **0.75** / **0.215** | +3.19 / +3.47 / 0.73 / 0.79 / 0.125 |
| | 1986-2026 | +4.57 / +3.15 / 0.89 / 0.94 / 0.070 P | +3.69 / +2.55 / 0.78 / 0.88 / **0.195** | +4.33 / +2.89 / 0.85 / 0.91 / 0.114 |
| | 1930-85 | +3.29 / +2.50 / 0.83 / 0.95 / 0.164 | +2.33 / +1.98 / 0.72 / 0.83 / 0.262 | +3.09 / +2.27 / 0.83 / 0.90 / 0.176 |
| | 1930-2026 | +3.96 / +2.51 / 0.89 / 0.96 / 0.068 P | +3.02 / +2.25 / 0.77 / 0.88 / 0.123 | +3.74 / +2.40 / 0.87 / 0.93 / 0.078 P |
| `S175\|A2\|IEF\|D-h1` (pick's twin) | 2000-26 / 1986-2026 | +4.28 / 0.084 P; +4.67 / 0.054 P | +3.50 / 0.193; +3.81 / 0.173 | +4.10 / 0.120; +4.44 / 0.088 P |
| | 1930-85 / 1930-2026 | +3.66 / 0.166; +4.02 / 0.071 P | +2.74 / 0.267; +3.11 / 0.128 | +3.46 / 0.188; +3.80 / 0.078 P |
| `S175\|A2\|IEF\|D-h0` (no deferral; r2_lev2x instruments) | 2000-26 / 1986-2026 | +5.33 / 0.066 P; +4.88 / 0.060 P | +4.59 / 0.181; +3.99 / 0.208 | +5.16 / 0.103; +4.63 / 0.110 |
| `S175\|C.5\|IEF\|D-h0` (core 0.5 never sold + SSO / IEF sleeve) | 2000-26 / 1986-2026 / 1930-85 | +3.04 / 0.081 P; +2.76 / 0.075 P; +1.93 / 0.193 | +2.60 / 0.207; +2.24 / 0.222; +1.39 / 0.307 | +3.04 / 0.106; +2.73 / 0.107; +1.90 / 0.199 |
| `S175\|CU.5\|IEF\|D-h0` (core 0.5 never sold + UPRO / IEF sleeve) | 2000-26 | +6.16 / +5.07 / 1.00 / 1.00 / 0.031 P | +5.92 / +4.44 / 1.00 / 1.00 / 0.119 | +6.27 / +4.92 / 1.00 / 1.00 / 0.060 P |
| | 1986-2026 | +5.41 / +5.30 / 1.00 / 1.00 / 0.011 P | +5.01 / +4.73 / 0.98 / 1.00 / 0.061 P | +5.46 / +5.13 / 1.00 / 1.00 / 0.020 P |
| | 1930-85 | +4.90 / +3.38 / 0.85 / 0.98 / 0.085 P | +4.47 / +2.95 / 0.83 / 0.88 / 0.178 | +4.97 / +3.21 / 0.85 / 0.95 / 0.109 |
| | 1930-2026 | +4.95 / +4.67 / 0.92 / 0.99 / 0.012 P | +4.55 / +4.41 / 0.90 / 0.94 / 0.036 P | +5.02 / +4.58 / 0.92 / 0.98 / 0.013 P |

What this adds:

* **The r2_lev2x pick fails more of the bar under a step-up.** On 2000-26 it fails not only p (0.215) but
  also the 10y and 15y beat rates (0.58 / 0.75). The 60-day deferral neither helps nor hurts under the
  step-up: SMA175 with it loses 0.78 pp of score, without it 0.74, and the SMA200 pick loses 0.90.
* **FED was this pick's one clean pass, and the step-up breaks it.** r2_lev2x found that under FED rates the
  pick passes items 1-3 in every history (1930-85 p 0.074). Under a step-up its 1930-85 p is **0.118**. Under
  the 20-year sale it is 0.086, still a pass.
* **CU.5 is the only one of these five that passes all four histories under the protocol** (2x when on: a
  never-sold 0.5 core plus a 3x sleeve). r2_lev2x excluded it on drawdown: -57% against SPY's -55% after
  1986. Under a step-up it fails 2000-26
  (p 0.119) and 1930-85 (p 0.178). Its never-sold core does keep the step-up cost small (-0.24 to -0.43
  score), as §7 found.
* **Under the 20-year sale CU.5 fails only the 1930-85 p (0.109),** with drawdown above SPY's after 1986. So
  in CA none of these five round-2 designs passes every history under either the step-up or the 20-year
  sale.

## 5. Frozen books and the long-history twins (engine, `long_r`, 1986-2026, VFINXR benchmark)

Each cell is score / full / boot_p; the pre-2000 holdout is ho5 / ho10:

| twin (CA) | liq | step-up | retire 20y g=7% | pre-2000 holdout liq → step |
|---|---|---|---|---|
| KX3 on LONG_MENU (VFINXR) | +0.94 / -0.29 / 0.607 | +0.99 / -0.38 / 0.644 | +1.12 / -0.30 / 0.615 | -0.18 / -0.32 → -0.30 / -0.51 |
| KX1 on LONG_MENU | +0.66 / -0.72 / 0.749 | +0.52 / -0.90 / 0.790 | +0.79 / -0.76 / 0.755 | -0.41 / -0.34 → -0.73 / -0.67 |
| site preset on LONG_MENU | +0.61 / -0.19 / 0.544 | +0.60 / -0.29 / 0.563 | +0.77 / -0.20 / 0.544 | -0.15 / -0.17 → -0.30 / -0.33 |
| site preset on PRE20 | +0.62 / +0.12 / 0.456 | +0.59 / +0.04 / 0.483 | +0.77 / +0.11 / 0.459 | +0.49 / +0.36 → +0.46 / +0.25 |
| EMA100/200 unlevered | +1.13 / -1.01 / 0.736 | +0.51 / -1.53 / 0.781 | +0.87 / -1.24 / 0.773 | -2.41 / -2.90 → -3.29 / -3.43 |
| GATED (long) | +3.03 / +1.18 / 0.248 | +2.65 / +0.34 / 0.426 | +2.88 / +0.84 / 0.321 | 0 (identical to VFINXR before 2000) |
| uninv540 minlen90 (long) | +3.71 / +1.83 / 0.169 | +3.49 / +0.94 / 0.338 | +3.62 / +1.46 / 0.227 | 0 |
| value/growth VIVAX/VIGRX tax1 (1994+) | +0.61 / +0.79 / 0.224 | +0.64 / +0.80 / 0.227 | +0.68 / +0.79 / 0.220 | ho5 +2.37 → +2.71 |

* None of the twins passes items 1-3 under any treatment, in CA or FED. Nothing changes here.
* The retirement sale lifts the frozen multi-lot books slightly (+0.07 to +0.18 score): selling the
  highest-basis lots first defers more of their tax than SPY's single lot can.
* The step-up lowers the realizers (EMA100/200 -0.62, GATED -0.38).

## 6. The critic's cache-only estimate versus the exact step-up

The critic used pre-liquidation equity (`eq`) for both sides. My `eq` column reproduces the critic's numbers
exactly, for example KX3 +0.0108 / +0.0186, EMA100/200 +0.0075 / +0.0076, 3x SMA175 full +0.0669, uninv540
full +0.0267, GATED +0.0197. It omits the tax still owed on gains realized earlier in the same calendar year.
That tax is small for frozen books and large for realizers, so the proxy understated the step-up penalty:

| CA, 2000-26 | liq | `eq` proxy | exact step-up |
|---|---|---|---|
| 2x lead: score / full / boot_p | +4.94 / +3.80 / 0.077 | +4.60 / +3.20 / 0.162 | +4.18 / +2.92 / 0.199 |
| 3x C1: score / full / boot_p | +9.65 / +7.10 / 0.029 | **+9.85** / +6.69 / 0.080 | **+9.33** / +6.35 / 0.108 |
| TX ConnorsRSI UPRO: score | +7.16 | +6.29 | +5.80 |
| KX3: score / full | +0.99 / +1.84 | +1.08 / +1.86 | +1.06 / +1.85 |

For C1 the proxy shows the score rising under the step-up, but the exact score falls.

Donating appreciated lots and harvesting the loss lots (`donate`) scores within 0.17 pp of the step-up for
every config, and within 0.02 pp for most. Loss lots are rare at window ends.

## 7. Exploratory: a never-sold core keeps more of the edge under a step-up

Never-sold 1x S&P core plus a trend sleeve, from `simx_core.py`. 5 new structures plus the all-in 2x, × 4
histories × CA/FED, 48 runs. Each cell is score / boot_p, and maxDD is shown against SPY's:

| structure (CA) | 2000-26 liq → step | 1986-2026 liq → step | 1930-85 liq → step | 1930-2026 liq → step | maxDD 2000-26 / 1930-85 |
|---|---|---|---|---|---|
| all-in 2x SMA175/3% | +4.94/0.077 → +4.18/0.199 | +4.62/0.067 → +3.73/0.219 | +2.95/0.270 → +2.00/0.331 | +3.48/0.129 → +2.54/0.210 | -47% / -67% |
| core 50% + 2x sleeve | +2.79/0.093 → +2.35/0.222 | +2.60/0.081 → +2.08/0.237 | +1.71/0.264 → +1.17/0.343 | +1.98/0.122 → +1.44/0.205 | -41% / -68% |
| core 67% + 3x sleeve | +4.23/0.038 → +4.03/0.135 | +3.72/0.012 → +3.41/0.077 | +3.39/0.107 → +3.05/0.205 | +3.36/0.015 → +3.05/0.046 | -52% / -76% |
| core 50% + 3x sleeve | +5.83/0.032 → +5.59/0.123 | +5.17/0.011 → +4.77/0.069 | +4.50/0.111 → +4.07/0.208 | +4.57/0.017 → +4.16/0.050 | -56% / -77% |
| core 33% + 3x sleeve | +7.24/0.029 → +6.96/0.115 | +6.46/0.009 → +5.98/0.059 | +5.43/0.124 → +4.90/0.207 | +5.61/0.025 → +5.12/0.060 | -58% / -79% |
| core 50% + 3x SMA200/3% | +4.41/0.078 → +4.02/0.183 | +4.59/0.037 → +4.17/0.130 | +4.58/0.054 → +4.10/0.107 | +4.59/0.014 → +4.15/0.049 | -55% / -77% |

SPY's maximum drawdown is -55% on 2000-26 and -81% on 1930-85.

* With a never-sold core, the step-up costs 0.2-0.55 pp/yr, against 0.76-0.95 for the all-in 2x. The core's own
  gain is forgiven at death exactly like SPY's.
* The 3x sleeves add risk: maximum drawdown is at or above SPY's in the ETF era, and the sleeve itself can
  lose about 90% (1929-35).
* None of these passes items 1-3 in all four histories under the step-up. All fail 2000-26 (p 0.115-0.222)
  and 1930-85 (p 0.107-0.343).
* The sleeve parameters were chosen post hoc. This is a pointer for r2_lev2x / r2_combos, which test such
  structures properly, not a candidate.

## 8. Conclusions

1. **How much the ending matters depends on how much a strategy realizes.** Score change against the
   protocol, CA, 2000-26, by turnover:

   | turnover per year | configs | step-up: median (range) | retire 20y g=7%: median (range) |
   |---|---|---|---|
   | < 0.15 (frozen books) | 47 | +0.05 (-0.25 to +0.59) | +0.15 (-0.05 to +0.53) |
   | 0.15-0.5 | 12 | -0.62 (-1.51 to +0.17) | -0.17 (-0.48 to +0.28) |
   | 0.5-1 | 10 | -1.04 (-1.46 to -0.25) | -0.34 (-0.44 to -0.09) |
   | > 1 | 39 | -1.37 (-2.49 to -0.32) | -0.44 (-0.86 to +0.06) |

   For the realizers the step-up also roughly doubles or triples boot_p. The 2x lead loses 0.76; it holds its
   lots through long uptrends, so its loss is below the median of its turnover bucket.
2. **The 2x SMA175/3% conditional lead.**
   * Liquidation is the protocol's own convention and still the right one for an investor who will spend or
     move the money within about 10 years. Under it the lead keeps the verify_lev_robust status: CONDITIONAL,
     moderate confidence, with p 0.067-0.077 in two histories.
   * **For a CA investor whose position ends in a step-up or a gift, the evidence drops to low confidence.**
     * p is 0.20-0.22 in both modern histories and 0.33 before 1986;
     * the worst 10-year window is negative;
     * the expected excess is still +3.7 to +4.2 pp/yr (+2.0 before 1986).
   * For a slow sale in retirement it is borderline: p 0.11-0.12 at g = 7%, below 0.10 only at g ≤ 4% or
     N ≤ 10.
   * In FED it survives every treatment (2000-26 / 1986-2026 step-up p 0.091 / 0.048). The verifier's other
     caveats are unchanged: post-hoc parameters, DSR ≈ 0.004, one-day-lag fragility, and the 1930-85 holdout.
3. **r2_lev2x's round-2 designs.** None of the five re-scored passes every history in CA under the step-up
   or the 20-year sale (§4c). The pick's FED pass does not survive a step-up (1930-85 p 0.118).
4. **No other verdict changes.**
   * The tax-managed rotations stay where they were, and all of them fail items 4, 6 and 7:
     * KX3 and KX1 pass items 1-3 under every ending;
     * the site preset fails item 2 under every ending (10y beat 0.64-0.72);
     * the B378 site combo's boot_p crosses 0.10 under the step-up (0.073 → 0.111).
   * The 3x rules, unlevered timing, macro, TAA, seasonal, global and stock-picking configs keep their
     verdicts. The step-up widens the failure margins of the realizers.
5. **SPY buy-and-hold remains the default for the taxable account.** For an investor who intends to hold until
   death or to give appreciated shares away, the protocol understates SPY's advantage by about 1.3-1.5 pp/yr
   per unit of full annual realization (the churn control on 2000-26 and on 1986-2026). Any timing or
   leverage edge has to clear that larger hurdle.
6. **Suggestion for the lab.** Report `step` and `ret_g7_n20` next to `liq` for every finalist. The recorder
   costs nothing extra, because it reads the same lots as the liquidation value. It needs the year-to-date
   realized tax, which the cache-only `eq` proxy lacks.

## 9. Caveats

* **Step-up and donation** follow current US law: IRC §1014 for the basis step-up, and the charitable deduction
  at market value for long-term lots. Not modelled:
  * estate tax, which is proportional to value and so nearly cancels in a CAGR comparison;
  * AGI limits on gifts;
  * the cost of waiting until short-term lots become long-term before gifting them;
  * any future change in the law.
* **The retirement sale freezes both books at the window's end.** A strategy that kept trading in retirement
  would realize more, so the sale treatment is generous to realizers. It assumes the same post-window return g
  for every holding, a 3x fund or VFITX included, so that only the tax state is compared. It uses the long-term
  rate for every sale, ignores bracket effects, and ignores state-residency changes in retirement.
* **Within each window the engine's lots are FIFO.** Specific-lot selling during the window is gap5's
  question. The minimum-tax order applies only to the post-window sale.
* **Inherited from the lab.**
  * The engine taxes dividends and interest as deferred gains (prices are total return). The Treasury leg's
    interest would be taxed yearly in reality, which hurts the timing rules further.
  * FED omits the 3.8% NIIT.
  * The two-sided wash-sale rule is not modelled. It is not material for these single-asset switches
    (critic replay).
* **boot_p uses only the first start's path.** I also report the 5-start average, which is much less
  favourable for KX3 and the incumbent under every ending.

## 10. Counts and files

**Re-scoring any later finalist takes a few lines.** Other round-2 results (combos, rotation_final, gap1-3,
gap5, gap6) were not published when this finished. Frozen books will barely move. Realizers should be
re-scored:

```python
from research.lab import registry; registry.load_families()
from research.lab.families import r2_gap4 as G
rec = G.run_terms(cfg, "CA", "full")                     # or "long_r", "r2_splice"
for t in ("liq", "step", "ret_g7_n20"):
    s = G.summary(rec, G.bench_terms("full", "CA"), t); print(t, s["score"], s["full_excess"], s["boot_p"], G.bar_1_3(s))
```


**Configs evaluated: 149**, all under 10 end-of-window treatments, in CA and FED:

* 109 on `full` (engine);
* 11 long-history twins on `long_r` (engine);
* 15 r2_lev2x configs: 5 designs × ETF / LONG / SPLICE worlds (engine);
* 8 leveraged rules × 4 histories (simulator);
* 6 core + sleeve structures × 4 histories (simulator).

Plus the 162-config daily leverage neighbourhood × 4 histories (simulator, CA). Truly new strategies: 4 churn
controls, 5 core + sleeve structures and the real-SSO 2x trend rule. Everything else re-scores existing
configs.
Treatments do not add trials to the deflated-Sharpe count (they are alternative scorings of the same paths),
but the 10 new strategies bring the search total to about 12,500.

* Code: `research/lab/families/r2_gap4.py`. It contains `TermGate`, `term_values`, `retire_value`, `run_terms`,
  `bench_terms`, `summary`, and the `r2_gap4.churn` control kind.
* Scripts in `research/lab/scratch/r2_gap4/`:
  * runners: `run_full.py`, `run_long_twins.py`, `run_long_sim.py`, `run_core_sim.py`, `run_grid_sim.py`,
    `run_lev2x.py`;
  * simulators: `simx.py`, `simx_core.py`;
  * checks: `validate_simx.py`, `validate_all.py`;
  * analysis: `analyze_full.py`, `analyze_long.py`, `analyze_lev2x.py`, `tables.py`, `key_tables.py`, `decomp_2x.py`,
    `endstate.py`, `show_long_sim.py`, `show_core_sim.py`, `show_grid.py`;
  * `critic_stepup.py`: the critic's cache-only script, re-run.
* Outputs in the same folder:
  * `full_table.csv` (109 configs × CA/FED × 10 treatments);
  * `full_tables.md`, `key_tables.md`;
  * `long_r_table.csv`, `long_sim_table.csv`, `core_sim_table.csv`, `grid_sim_table.csv`, `lev2x_table.csv`;
  * the pickles behind them;
  * `cache/`: TermGate records.
