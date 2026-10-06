# Family `factor_style`: factor and style tilts and rotation

Module: `research/lab/families/factor_style.py` (signals `factor_style.rotate`, `.ratio`, `.lowvol`,
`.composite`, `.season`, `.macro`; unchanged in this session, so every cached result is still valid).
Every config: `research/lab/scratch/factor_style/grid.py` (each config's `tag` is part of its cache key).
Scripts and logs: `research/lab/scratch/factor_style/`. All runs: `research/lab/results/factor_style_table.csv`
(one row per config x regime x protocol, with a `protocol` column and the exact config JSON).
Numbers are excess after-tax CAGR vs SPY buy-and-hold (VFINX on the long protocols), in percentage points
per year (pp). "Bar 1-3" means PROTOCOL section 3 criteria 1-3 (score > 0, full > 0, 10y beat >= 75%,
15y beat >= 85%, boot_p <= 0.10). Criteria 4-7 are discussed separately.

## Verdict

**No factor or style strategy beats SPY after California tax with good confidence. The family's
winners won because of the 2007-2026 growth era, or because the windows they were scored on start
after the 2000-02 growth crash.**

* **Static tilts.** Over 2000-2026 only *growth* tilts beat SPY by a clear margin. Two late-launched,
  growth-heavy funds also clear bar 1-3: the momentum ETF SPMO and the mega-cap MGC. Every other style
  is negative or below +0.5 pp/yr, with boot_p >= 0.15:
  value, dividend, low-vol, quality and equal-weight lost outright. Small, mid, high-beta, buyback and
  free-cash-flow funds were near zero, because they won in windows starting 2000-09 and lost in every
  window starting 2010-21. The 2000-era large-cap growth funds (IWF, IVW, VIGRX, SPYG, IUSG, QQQ) lost
  1.5-4.2 pp/yr in 5-year windows starting 2000-04 and won 1.1-4.1 pp/yr afterwards. On the full
  protocol, IWF (CA score +1.21, full -0.33, boot_p 0.53) and IVW (+0.91, +0.11, 0.42) fail. The
  late-launched growth funds look confident: VUG (from 2004), MGK (2008), IWY (2009), SCHG, ONEQ and the
  momentum ETF SPMO (2016) clear bar 1-3 in CA. **But so does IWF when it is scored only on the same
  windows** (IWF from 2004-04: score +1.84, full +1.41, boot_p 0.082; from 2008: +2.03, boot_p 0.037).
  Their pass comes from the launch window and the growth era, not from the funds. It is hindsight.
* **Rotation** covers relative momentum between styles, factor momentum, mean reversion, ratio trend,
  low-volatility selection, multi-factor composites, size seasonality and macro switches, about 1,500
  configs in all. **None passes in CA** except one tax-execution artifact, described next. The median
  CA score is -0.3 to -3.0 pp/yr in every group. Switching between styles realizes gains that SPY
  defers, and the pre-tax edge is too small to pay for that. Walk-forward selection among the dynamic
  strategies is negative out of sample in CA (-1.6 pp/yr, 10-year in-sample / 5-year out-of-sample,
  yearly decisions, 0 of 12 decisions beat SPY).
* **Best CA result, which still fails the bar.** A 12-1 value/growth momentum switch between IWD and
  IWF, with 6% score-gap hysteresis, checked monthly and executed tax-managed (1%/yr gain budget):
  `N5_vgh|VG_R|lb252|sk21|M|h0.06|tax1`. Full protocol in CA: score **+1.16**, full **+1.83**, 10-year
  beat 88%, 15-year beat 100%, boot_p **0.040**. That is better than the incumbent preset (+0.66 / +1.54
  / 0.025) on every statistic except boot_p. It is still **not good confidence**:
  1. Its quarterly siblings mostly fail the bootstrap on the full protocol (p = 0.20-0.28; one S&P
     variant passes from 2002).
  2. Its long-history twin on Vanguard's value/growth index funds (1994-2026) fails in CA: score +0.61,
     10-year beat 60%, boot_p 0.22.
  3. On 24 random ETF pairs, the same rule passes only where one leg is a growth or tech fund (2 of 24).
  4. Walk-forward selection picked it in 2019 and it then lost 1.0 pp/yr.
  5. Mechanically it switches only when the position it sells is at a loss (or the gain fits the 1%
     budget), and the gain budget then freezes it. From 2000-07 it switched four times through 2003,
     held mostly value until the 2008 crash, sold value at a loss in 2008-09, and has held growth ever
     since. A start in 2013 buys value and is still about 95% value in 2026 (-2.9 pp/yr to 2026). It is
     the same growth-era bet that the incumbent's frozen 74% growth/tech book makes.
* **Tax-deferred (NONE, diagnostic only).** Value/growth momentum (12-1, quarterly) and a
  small-value / large-growth switch are the family's most persistent pre-tax ideas.
  * `C_pairmom|SVLG|lb126|sk21|Q|std` clears bar 1-3 in NONE on the full protocol (+1.89, full +3.05,
    boot_p 0.037). It has no long-history proxy. On random pairs, only one pair scores higher.
  * The value/growth hysteresis switch clears bar 1-3 in NONE on the long protocol, 1994-2026: +1.37,
    boot_p 0.059, pre-2000 5-year windows +3.6 pp, 5 of 5 beat. It fails on the ETF full protocol in NONE
    (boot_p 0.117).
  * The small-value/large-growth switch loses its edge in CA (score -0.14). The hysteresis switch is
    the CA standout above. Neither is a recommendation for a taxable account.

## What was tested (all of it)

1,661 distinct configs were run: 1,513 strategies and 148 hindsight controls. Records: screen
CA 1,496 / NONE 1,156; full CA 40 / FED 13 / NONE 33; long_screen CA 53 / NONE 31; long CA 9 / NONE 9.
In NONE, `execution: "tax"` and `trade_rule: "tax_managed"` behave exactly like standard execution (no
tax lots exist). Those twins were therefore run in CA only, except where a candidate needed its own NONE
row. They are removed from NONE group statistics and diagnostics. `grid.py` also *defines* 1,416
configs that were **not run**, because of the battery throttle (4 machine-wide slots for most of the
session):

* the unpruned grids of mean reversion (F: 347 not run; the F2 subset of 29 ran in CA and NONE, its 29
  tax-managed versions did not), ratio trend (G: 100), low-vol (H: 228), composite (I: 64), season
  (J: 8) and macro (K: 40);
* factor-momentum tax versions (E: 66, all standard versions negative in both regimes);
* 3-fund pair menus (C: 46, C2: 6);
* `lt5` execution (N1: 14), VG_SP / top-2 (N3: 12), two lookback pairs (N4: 12), and random
  3-fund static blends (N2: 24);
* most of the unpruned long-history grid (a/c/f/g/m: 437; its pruned versions LPb, LNb, LN2b, LN5 and
  LN6, 53 configs, ran).

Groups and their screen results ("score" = mean of the 5-, 10- and 15-year window excess; best and
median in pp):

| group | what | CA n | CA best score | CA median | CA share > 0 | CA pass 1-3 | NONE n | NONE best | NONE median | NONE pass 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|
| A_static | static single-fund tilts (buy and hold) | 74 | +3.05 | -0.30 | 42% | 7 | 74 | +3.45 | -0.34 | 6 |
| B_blend | static blends (buy-hold / annual / band) | 128 | +0.68 | -0.26 | 34% | 0 | 128 | +0.78 | -0.26 | 0 |
| C_pairmom | pair relative momentum (value-growth, size, small-value vs large-growth, EW, low/high vol) | 399 | +0.81 | -1.26 | 15% | 0 | 201 | +2.28 | -0.36 | 4 |
| D_menumom | menu momentum over style menus (top 1-3) | 480 | +0.57 | -2.10 | 3% | 0 | 240 | +3.57 | -1.17 | 3 |
| E_factmom | factor momentum (only styles beating SPY, else SPY) | 61 | -1.70 | -2.97 | 0% | 0 | 59 | -0.10 | -0.97 | 0 |
| F_meanrev | style mean reversion (3-5y losers; ratio z-tilt) | 28 | -0.07 | -0.82 | 0% | 0 | 28 | +1.02 | -0.19 | 0 |
| G_ratiotrend | ratio trend (A/B vs its moving average) | 12 | +0.50 | -0.38 | 25% | 0 | 6 | +1.30 | +0.23 | 0 |
| H_lowvol | low-vol / low-beta / high-beta selection | 12 | +0.42 | -1.13 | 25% | 0 | 6 | +0.45 | -0.38 | 0 |
| H_randpair | control: plain rules on 24 random pairs | n/a | n/a | n/a | n/a | n/a | 48 | +3.01 | -1.22 | 0 |
| HP2_randpair | control: CA rule (quarterly) on 24 random pairs | 24 | +3.89 | -0.69 | 42% | 1 | n/a | n/a | n/a | n/a |
| HP3_randpair | control: CA rule (monthly) on 24 random pairs | 24 | +3.73 | -0.72 | 42% | 2 | n/a | n/a | n/a | n/a |
| I_composite | multi-factor rank composite | 8 | -0.15 | -1.75 | 0% | 0 | 4 | +0.09 | -0.77 | 0 |
| J_season | calendar size timing (small caps around January) | 8 | -2.11 | -2.45 | 0% | 0 | 8 | +1.08 | +0.57 | 1 |
| K_macro | macro style switch (drawdown / curve / VIX) | 12 | +0.61 | -0.36 | 42% | 0 | 6 | +0.93 | +0.27 | 0 |
| L_site | site-expressible Combo / TaxManagedCombo over style menus | 72 | +0.28 | -1.73 | 4% | 0 | 36 | +0.83 | -1.24 | 0 |
| N1_core | 50% SPY core + rotation | 4 | +0.25 | +0.24 | 75% | 0 | 2 | +1.15 | +1.03 | 1 |
| N1_hyst | score-gap hysteresis | 12 | +1.11 | +0.08 | 58% | 1 | 6 | +1.58 | +0.25 | 1 |
| N1_taxexec | CA execution variants (LT-only gains, 5% budget) | 28 | +0.63 | -0.30 | 32% | 1 | n/a | n/a | n/a | n/a |
| N2_randstatic | control: 24 random single ETFs, buy and hold | 24 | +3.79 | -0.36 | 46% | 0 | n/a | n/a | n/a | n/a |
| N3_ltmom | long-horizon (3-5y) style momentum | 24 | +0.73 | -0.03 | 50% | 0 | 8 | +1.27 | +0.29 | 0 |
| N4_vsspy | one style vs SPY (momentum / ratio trend) | 24 | +0.66 | -0.82 | 21% | 0 | 8 | +0.98 | +0.13 | 0 |
| N5_vgh | neighbourhood of the CA standout (quarterly) | 25 | +1.27 | +0.67 | 84% | 11 | n/a | n/a | n/a | n/a |
| N6_vghm | neighbourhood of the CA standout (monthly) | 13 | +1.34 | +0.99 | 100% | 11 | n/a | n/a | n/a | n/a |
| R_nbr | robustness: lookback neighbours | n/a | n/a | n/a | n/a | n/a | 11 | +1.99 | +0.91 | 3 |
| R_sizealt | robustness: other size index pairs | n/a | n/a | n/a | n/a | n/a | 9 | +1.98 | +0.56 | 0 |
| R_vgalt | robustness: other value/growth index pairs | n/a | n/a | n/a | n/a | n/a | 7 | +1.36 | +0.47 | 0 |

Groups N1-N6, HS, HP2-HP4 and OFF were added in this session. Groups A-L were defined by the previous
researcher and their completed screens were reused from the cache.

* **N1** tests CA execution: long-term-gains-only, 5% gain budget, score-gap hysteresis, and a 50% SPY
  core.
* **N3** tests long-horizon (3-5 year) style momentum.
* **N4** tests one style against SPY.
* **N5 and N6** are the neighbourhood of the CA standout.
* **HS** is the launch-window control.
* **HP2-HP4** run each candidate rule on 24 random pairs.
* **OFF** shifts rebalance dates and adds a 1-day execution lag.

## 1. Static tilts: only growth won, and only in the growth era

Screen protocol (yearly starts 2000-2023). The last three columns are the mean CA excess of 5-year
windows by start year.

| style | fund | first start | CA score | CA full | CA 10y beat | CA 15y beat | CA boot p | CA bar 1-3 | NONE score | NONE boot p | CA 5y excess, starts 2000-04 | starts 2005-09 | starts 2010-21 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| growth | QQQ | 2000-01-01 | +2.84 | +0.40 | 88% | 92% | 0.415 | no | +3.31 | 0.417 | -4.18 | +3.84 | +4.09 |
| growth | VIGRX | 2000-01-01 | +0.86 | +0.15 | 94% | 83% | 0.447 | no | +1.01 | 0.436 | -1.89 | +1.43 | +1.47 |
| growth | IWF | 2001-01-01 | +1.28 | +0.58 | 88% | 82% | 0.285 | no | +1.47 | 0.308 | -2.00 | +1.33 | +2.03 |
| growth | IVW | 2001-01-01 | +0.95 | +0.92 | 81% | 91% | 0.124 | no | +1.09 | 0.141 | -1.47 | +1.14 | +1.36 |
| growth | SPYG | 2001-01-01 | +0.87 | +0.03 | 88% | 82% | 0.460 | no | +1.01 | 0.471 | -3.21 | +1.54 | +1.45 |
| growth | IUSG | 2001-01-01 | +0.83 | +0.49 | 88% | 82% | 0.280 | no | +0.97 | 0.288 | -1.73 | +1.36 | +1.15 |
| growth | IJT | 2001-01-01 | +0.61 | +0.98 | 62% | 73% | 0.293 | no | +0.75 | 0.319 | +4.11 | +2.67 | -1.75 |
| growth | IWO | 2001-01-01 | -0.55 | -0.71 | 56% | 55% | 0.653 | no | -0.63 | 0.648 | +1.25 | +2.04 | -2.60 |
| growth | IWP | 2002-01-01 | +0.36 | -0.21 | 67% | 70% | 0.563 | no | +0.44 | 0.566 | +1.74 | +2.09 | -0.88 |
| growth | ONEQ | 2004-01-01 | +2.29 | +2.07 | 100% | 100% | 0.052 | yes | +2.64 | 0.067 | -1.97 | +1.95 | +2.38 |
| growth | VUG | 2005-01-01 | +1.64 | +1.59 | 100% | 100% | 0.073 | yes | +1.90 | 0.081 | n/a | +1.55 | +1.60 |
| growth | VBK | 2005-01-01 | -0.62 | -0.74 | 58% | 43% | 0.652 | no | -0.72 | 0.649 | n/a | +3.32 | -2.24 |
| growth | RPG | 2007-01-01 | +0.51 | +1.37 | 70% | 60% | 0.205 | no | +0.59 | 0.229 | n/a | +4.40 | -0.44 |
| growth | RZG | 2007-01-01 | -1.80 | -1.18 | 30% | 0% | 0.703 | no | -2.11 | 0.690 | n/a | +4.44 | -3.17 |
| growth | MGK | 2008-01-01 | +2.08 | +2.30 | 100% | 100% | 0.032 | yes | +2.37 | 0.034 | n/a | +1.56 | +2.06 |
| growth | IWY | 2010-01-01 | +3.05 | +2.46 | 100% | 100% | 0.033 | yes | +3.45 | 0.041 | n/a | n/a | +2.79 |
| growth | SCHG | 2011-01-01 | +2.41 | +1.96 | 100% | 100% | 0.096 | yes | +2.73 | 0.110 | n/a | n/a | +2.25 |
| momentum | XMMO | 2006-01-01 | +0.51 | +1.08 | 73% | 67% | 0.233 | no | +0.57 | 0.254 | n/a | +0.19 | +0.68 |
| momentum | PDP | 2008-01-01 | -1.21 | -1.24 | 33% | 0% | 0.788 | no | -1.41 | 0.780 | n/a | +0.95 | -1.39 |
| momentum | MTUM | 2014-01-01 | -0.04 | +2.00 | 33% | n/a | 0.188 | no | -0.05 | 0.210 | n/a | n/a | +0.07 |
| momentum | SPMO | 2016-01-01 | +2.52 | +4.56 | 100% | n/a | 0.025 | yes | +2.92 | 0.032 | n/a | n/a | +2.17 |
| broad/mega | VTSMX | 2000-01-01 | +0.13 | +0.10 | 59% | 67% | 0.376 | no | +0.16 | 0.379 | +0.93 | +0.52 | -0.35 |
| broad/mega | DIA | 2000-01-01 | -0.15 | -0.04 | 47% | 67% | 0.515 | no | -0.15 | 0.490 | +0.90 | +0.81 | -1.12 |
| broad/mega | IWB | 2001-01-01 | +0.07 | +0.07 | 62% | 73% | 0.318 | no | +0.08 | 0.346 | +0.41 | +0.27 | -0.14 |
| broad/mega | IWV | 2001-01-01 | -0.03 | +0.04 | 56% | 45% | 0.444 | no | -0.02 | 0.445 | +0.64 | +0.33 | -0.38 |
| broad/mega | OEF | 2001-01-01 | -0.20 | -0.22 | 31% | 27% | 0.694 | no | -0.25 | 0.684 | -1.42 | -0.48 | +0.33 |
| broad/mega | VTI | 2002-01-01 | +0.14 | +0.26 | 60% | 80% | 0.158 | no | +0.18 | 0.170 | +0.90 | +0.61 | -0.25 |
| broad/mega | XLG | 2006-01-01 | +0.29 | +0.36 | 45% | 67% | 0.311 | no | +0.32 | 0.327 | n/a | -0.99 | +0.66 |
| broad/mega | MGC | 2008-01-01 | +0.27 | +0.37 | 89% | 100% | 0.070 | yes | +0.31 | 0.073 | n/a | -0.12 | +0.30 |
| mid/extended | MDY | 2000-01-01 | +0.45 | +1.45 | 59% | 50% | 0.196 | no | +0.59 | 0.195 | +4.71 | +2.49 | -2.10 |
| mid/extended | VEXMX | 2000-01-01 | +0.21 | -0.04 | 59% | 58% | 0.502 | no | +0.28 | 0.504 | +3.73 | +2.13 | -2.07 |
| mid/extended | IJH | 2001-01-01 | +0.25 | +0.72 | 56% | 55% | 0.307 | no | +0.35 | 0.314 | +3.68 | +2.62 | -1.92 |
| mid/extended | IWR | 2002-01-01 | -0.02 | +0.35 | 53% | 40% | 0.408 | no | -0.00 | 0.426 | +3.72 | +1.89 | -1.73 |
| mid/extended | VXF | 2003-01-01 | -0.31 | +0.16 | 50% | 44% | 0.459 | no | -0.36 | 0.471 | +2.76 | +2.28 | -1.98 |
| mid/extended | VO | 2005-01-01 | -0.64 | -0.80 | 42% | 14% | 0.771 | no | -0.74 | 0.757 | n/a | +1.83 | -1.58 |
| small | NAESX | 2000-01-01 | +0.34 | +0.81 | 59% | 50% | 0.305 | no | +0.45 | 0.322 | +4.80 | +2.34 | -2.27 |
| small | IJR | 2001-01-01 | +0.24 | +0.96 | 56% | 55% | 0.311 | no | +0.33 | 0.338 | +4.60 | +1.98 | -2.05 |
| small | IWM | 2001-01-01 | -0.83 | -0.06 | 44% | 27% | 0.520 | no | -0.95 | 0.530 | +3.48 | +1.19 | -3.07 |
| small | VB | 2005-01-01 | -0.91 | -1.01 | 42% | 29% | 0.768 | no | -1.04 | 0.758 | n/a | +2.43 | -2.17 |
| small | SCHA | 2010-01-01 | -2.93 | -1.95 | 0% | 0% | 0.826 | no | -3.41 | 0.811 | n/a | n/a | -2.69 |
| small | SIZE | 2014-01-01 | -1.97 | -2.26 | 0% | n/a | 0.991 | no | -2.35 | 0.986 | n/a | n/a | -1.81 |
| equal weight | RSP | 2004-01-01 | -0.29 | -0.56 | 46% | 50% | 0.687 | no | -0.32 | 0.680 | -0.35 | +1.86 | -1.21 |
| equal weight | QQQE | 2013-01-01 | +0.32 | +0.67 | 50% | n/a | 0.349 | no | +0.38 | 0.347 | n/a | n/a | +0.46 |
| value | VIVAX | 2000-01-01 | -0.80 | -0.20 | 29% | 33% | 0.577 | no | -0.92 | 0.578 | +2.34 | -1.06 | -1.73 |
| value | IJS | 2001-01-01 | -0.38 | +0.57 | 44% | 36% | 0.413 | no | -0.41 | 0.418 | +4.84 | +1.25 | -2.68 |
| value | IUSV | 2001-01-01 | -1.00 | -0.64 | 25% | 18% | 0.742 | no | -1.15 | 0.728 | +2.66 | -1.06 | -1.86 |
| value | SPYV | 2001-01-01 | -1.33 | -1.22 | 6% | 0% | 0.934 | no | -1.55 | 0.918 | +1.21 | -1.34 | -1.91 |
| value | IWN | 2001-01-01 | -1.36 | +0.20 | 25% | 27% | 0.496 | no | -1.57 | 0.497 | +5.47 | +0.10 | -3.80 |
| value | IVE | 2001-01-01 | -1.36 | -1.44 | 6% | 0% | 0.953 | no | -1.59 | 0.936 | +1.39 | -1.46 | -1.97 |
| value | IWD | 2001-01-01 | -1.43 | -0.90 | 25% | 18% | 0.807 | no | -1.66 | 0.776 | +2.46 | -1.11 | -2.60 |
| value | IWS | 2002-01-01 | -0.59 | +0.14 | 47% | 30% | 0.487 | no | -0.67 | 0.478 | +4.82 | +1.40 | -2.58 |
| value | VBR | 2005-01-01 | -1.43 | -1.55 | 33% | 0% | 0.829 | no | -1.66 | 0.810 | n/a | +1.43 | -2.38 |
| value | VTV | 2005-01-01 | -1.44 | -1.30 | 0% | 0% | 0.908 | no | -1.68 | 0.890 | n/a | -0.94 | -1.61 |
| value | RPV | 2007-01-01 | -1.41 | -1.98 | 30% | 0% | 0.772 | no | -1.66 | 0.764 | n/a | +2.92 | -2.22 |
| value | VMVIX | 2007-01-01 | -1.60 | -1.99 | 30% | 0% | 0.902 | no | -1.86 | 0.895 | n/a | +1.83 | -2.23 |
| value | RZV | 2007-01-01 | -2.63 | -2.75 | 10% | 0% | 0.779 | no | -3.10 | 0.769 | n/a | +3.57 | -3.62 |
| value | VLUE | 2014-01-01 | -3.73 | -0.97 | 0% | n/a | 0.615 | no | -4.52 | 0.600 | n/a | n/a | -3.72 |
| quality | SPHQ | 2006-01-01 | -0.36 | -0.74 | 36% | 33% | 0.690 | no | -0.41 | 0.714 | n/a | -2.53 | +0.24 |
| quality | MOAT | 2013-01-01 | +0.33 | -1.26 | 100% | n/a | 0.791 | no | +0.39 | 0.772 | n/a | n/a | +0.29 |
| quality | QUAL | 2014-01-01 | -0.42 | -0.61 | 0% | n/a | 0.824 | no | -0.50 | 0.803 | n/a | n/a | -0.41 |
| low vol | USMV | 2012-01-01 | -1.94 | -3.29 | 0% | n/a | 0.968 | no | -2.31 | 0.961 | n/a | n/a | -1.83 |
| low vol | SPLV | 2012-01-01 | -2.98 | -4.42 | 0% | n/a | 0.982 | no | -3.58 | 0.974 | n/a | n/a | -2.81 |
| high beta | SPHB | 2012-01-01 | +0.05 | +1.56 | 40% | n/a | 0.303 | no | +0.04 | 0.324 | n/a | n/a | +0.06 |
| dividend | FVD | 2004-01-01 | -0.68 | -1.20 | 38% | 50% | 0.746 | no | -0.76 | 0.731 | +5.24 | +2.11 | -2.24 |
| dividend | DVY | 2004-01-01 | -1.77 | -2.03 | 0% | 0% | 0.896 | no | -2.06 | 0.884 | +0.52 | -1.53 | -2.06 |
| dividend | SDY | 2006-01-01 | -1.33 | -2.00 | 27% | 17% | 0.906 | no | -1.53 | 0.899 | n/a | +0.96 | -2.01 |
| dividend | VIG | 2007-01-01 | -0.80 | -0.80 | 20% | 20% | 0.798 | no | -0.91 | 0.798 | n/a | +0.69 | -1.08 |
| dividend | VYM | 2007-01-01 | -1.41 | -1.60 | 20% | 0% | 0.910 | no | -1.63 | 0.904 | n/a | +0.18 | -1.69 |
| dividend | SCHD | 2012-01-01 | -0.97 | -1.97 | 20% | n/a | 0.870 | no | -1.15 | 0.861 | n/a | n/a | -0.91 |
| dividend | QDF | 2013-01-01 | -2.32 | -2.01 | 0% | n/a | 0.981 | no | -2.79 | 0.969 | n/a | n/a | -2.36 |
| dividend | NOBL | 2014-01-01 | -2.56 | -3.25 | 0% | n/a | 0.972 | no | -3.06 | 0.964 | n/a | n/a | -2.24 |
| dividend | DGRO | 2015-01-01 | -1.33 | -1.43 | 0% | n/a | 0.875 | no | -1.57 | 0.868 | n/a | n/a | -1.17 |
| buyback | PKW | 2007-01-01 | +0.01 | -0.35 | 50% | 60% | 0.610 | no | +0.02 | 0.591 | n/a | +3.11 | -0.58 |
| free cash flow | COWZ | 2017-01-01 | +0.48 | -2.48 | n/a | n/a | 0.784 | no | +0.61 | 0.762 | n/a | n/a | +0.48 |

* **Style ranking.** Growth and growth-heavy momentum ETFs beat SPY. Value, dividend, low-vol,
  quality and equal-weight lost. Mid and small caps won in windows starting 2000-04 (+2.8 to +4.8 pp)
  and 2005-09 (+1.2 to +2.6 pp), then lost 1.6-3.1 pp/yr in every window starting 2010-21. Over the
  whole period that nets to roughly zero (scores -0.9 to +0.5).
* **The growth winners' edge is the era.** Every 2000-era large-cap growth fund has negative 5-year
  excess for starts in 2000-04 and positive excess afterwards. Small- and mid-cap growth (IJT, IWO, IWP)
  behave like small and mid caps instead.
* **Random-ETF control (N2, 24 draws, 21 distinct funds, from the pre-registered 2003 pool, buy and
  hold, CA).**
  * 0 of 24 pass, 11 of 24 have a positive score, and the median score is -0.36.
  * The four best draws are SOXX, QQQ, IWF and IVW. Picking the right ETF after the fact is easy.
    Knowing it beforehand is the problem.
* **Launch-window control (HS).** IWF was scored only on the windows of each late fund, on the full
  protocol. In CA it clears bar 1-3 on every one of them:
  * VUG's window: +1.84 / boot_p 0.082 (VUG itself: +1.60 / 0.096).
  * MGK's window: +2.03 / 0.037.
  * IWY's window: +2.19 / 0.073.
  * SPMO's window: +2.58 / 0.091.

  The same IWF from its own 2000-07 launch fails: +1.21, full -0.33, boot_p 0.53.
* **Before 2000 (long history, table in section 5).**
  * VIGRX (growth index fund) beat VFINX by +2.1 pp/yr in 1993-2000, lost 1.8 pp/yr in 2000-10, and
    won +0.9 and +2.1 in 2010-20 and 2020-26. Over 1993-2026 it is +0.65 score with boot_p 0.25 in CA,
    which fails.
  * Small caps (NAESX) lost 8.1 pp/yr in 1986-2000 and value (VIVAX) lost 2.6 pp/yr in 1993-2000.
  * **No static style tilt has a confident edge over 26-40 years. Growth is the only one with a
    positive full-period number, and its sign flips by decade.**
* **Stricter distribution-tax accounting (realism.py) helps growth tilts slightly.** SPY's dividends
  are taxed every year. Results in CA:
  * VUG: +1.40 to +1.52 from 2004.
  * IVW: +0.11 to +0.19 from 2000-07.
  * Hysteresis switch: +1.83 to +1.85 from 2000-07.

  None of these changes a conclusion.

## 2. Full-protocol finalists (quarterly starts 2000-2023)

The `2000(first)-10` column is the excess from the config's first start (2000-01 or the first quarter
after launch) to 2010-01.

| config | regime | first start | score | full | 10y mean | 10y beat | 15y beat | 20y beat | boot p | max DD | SPY DD | trades | 2000(first)-10 | 2010-20 | 2020-26 | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1 | CA | 2000-07-01 | +1.16 | +1.83 | +1.06 | 88% | 100% | 100% | 0.040 | -53% | -55% | 13 | +1.72 | +1.31 | +1.81 | yes |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1 | FED | 2000-07-01 | +1.26 | +1.88 | +1.16 | 88% | 100% | 100% | 0.041 | -53% | -55% | 13 | +1.82 | +1.41 | +2.00 | yes |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1 | NONE | 2000-07-01 | +1.23 | +1.30 | +1.07 | 78% | 100% | 100% | 0.117 | -51% | -55% | 21 | +2.38 | -0.82 | +2.81 | no |
| N1_hyst\|VG_R\|lb252\|sk21\|Q\|h0.06\|tax1 | CA | 2000-07-01 | +0.94 | +1.03 | +0.84 | 82% | 93% | 92% | 0.199 | -57% | -55% | 9 | -0.14 | +1.20 | +1.80 | no |
| N1_hyst\|VG_R\|lb252\|sk21\|Q\|h0.06\|tax1 | FED | 2000-07-01 | +1.03 | +1.06 | +0.92 | 83% | 93% | 92% | 0.198 | -57% | -55% | 9 | -0.14 | +1.30 | +2.00 | no |
| N1_hyst\|VG_R\|lb252\|sk21\|Q\|h0.06\|tax1 | NONE | 2000-07-01 | +0.95 | +0.64 | +0.83 | 71% | 96% | 100% | 0.289 | -54% | -55% | 13 | +0.42 | -0.49 | +2.81 | no |
| N5_vgh\|GS\|lb252\|sk21\|Q\|h0.06\|tax1 | CA | 2000-07-01 | +1.02 | +0.46 | +1.12 | 82% | 93% | 100% | 0.328 | -59% | -55% | 7 | -1.63 | +1.42 | +1.77 | no |
| N5_vgh\|GS\|lb252\|sk21\|Q\|h0.06\|tax1 | FED | 2000-07-01 | +1.11 | +0.47 | +1.21 | 85% | 93% | 100% | 0.330 | -59% | -55% | 7 | -1.63 | +1.51 | +1.95 | no |
| N5_vgh\|GS\|lb252\|sk21\|Q\|h0.06\|tax1 | NONE | 2000-07-01 | +1.04 | +0.01 | +1.07 | 85% | 91% | 100% | 0.468 | -59% | -55% | 9 | -2.13 | +1.60 | +1.23 | no |
| A_static\|VUG | CA | 2004-04-01 | +1.60 | +1.40 | +1.56 | 100% | 100% | 100% | 0.096 | -51% | -55% | 1 | n/a | +1.02 | +2.19 | yes |
| A_static\|VUG | FED | 2004-04-01 | +1.72 | +1.43 | +1.67 | 100% | 100% | 100% | 0.106 | -51% | -55% | 1 | n/a | +1.09 | +2.39 | no |
| A_static\|VUG | NONE | 2004-04-01 | +1.85 | +1.46 | +1.78 | 100% | 100% | 100% | 0.112 | -51% | -55% | 1 | n/a | +1.15 | +2.58 | no |
| HS_window\|IWF\|from2004-04-01\|as_VUG | CA | 2004-04-01 | +1.84 | +1.41 | +1.83 | 100% | 100% | 100% | 0.082 | -51% | -55% | 1 | n/a | +1.42 | +2.01 | yes |
| HS_window\|IWF\|from2004-04-01\|as_VUG | NONE | 2004-04-01 | +2.12 | +1.48 | +2.08 | 100% | 100% | 100% | 0.097 | -51% | -55% | 1 | n/a | +1.60 | +2.37 | yes |
| A_static\|MGK | CA | 2008-01-01 | +2.10 | +2.30 | +2.24 | 100% | 100% | n/a | 0.032 | -47% | -55% | 1 | n/a | +1.19 | +3.09 | yes |
| A_static\|MGK | NONE | 2008-01-01 | +2.39 | +2.44 | +2.52 | 100% | 100% | n/a | 0.034 | -47% | -55% | 1 | n/a | +1.35 | +3.63 | yes |
| HS_window\|IWF\|from2008-01-01\|as_MGK | CA | 2008-01-01 | +2.03 | +1.89 | +2.22 | 100% | 100% | n/a | 0.037 | -49% | -55% | 1 | n/a | +1.42 | +2.01 | yes |
| HS_window\|IWF\|from2008-01-01\|as_MGK | NONE | 2008-01-01 | +2.32 | +2.01 | +2.50 | 100% | 100% | n/a | 0.042 | -49% | -55% | 1 | n/a | +1.60 | +2.37 | yes |
| A_static\|IWY | CA | 2009-10-01 | +2.99 | +2.46 | +3.27 | 100% | 100% | n/a | 0.030 | -33% | -55% | 1 | n/a | +1.73 | +2.99 | yes |
| A_static\|IWY | NONE | 2009-10-01 | +3.40 | +2.58 | +3.67 | 100% | 100% | n/a | 0.034 | -33% | -55% | 1 | n/a | +1.96 | +3.52 | yes |
| HS_window\|IWF\|from2010-01-01\|as_IWY | CA | 2010-01-01 | +2.19 | +1.83 | +2.43 | 100% | 100% | n/a | 0.073 | -33% | -55% | 1 | n/a | +1.42 | +2.01 | yes |
| HS_window\|IWF\|from2010-01-01\|as_IWY | NONE | 2010-01-01 | +2.49 | +1.93 | +2.73 | 100% | 100% | n/a | 0.085 | -33% | -55% | 1 | n/a | +1.60 | +2.37 | yes |
| A_static\|SPMO | CA | 2016-01-01 | +2.79 | +4.56 | +3.51 | 100% | n/a | n/a | 0.025 | -31% | -55% | 1 | n/a | n/a | +7.14 | yes |
| A_static\|SPMO | NONE | 2016-01-01 | +3.21 | +5.01 | +3.89 | 100% | n/a | n/a | 0.032 | -31% | -55% | 1 | n/a | n/a | +8.30 | yes |
| HS_window\|IWF\|from2016-01-01\|as_SPMO | CA | 2016-01-01 | +2.58 | +2.25 | +2.60 | 100% | n/a | n/a | 0.091 | -33% | -55% | 1 | n/a | n/a | +2.01 | yes |
| HS_window\|IWF\|from2016-01-01\|as_SPMO | NONE | 2016-01-01 | +3.01 | +2.49 | +2.89 | 100% | n/a | n/a | 0.100 | -33% | -55% | 1 | n/a | n/a | +2.37 | yes |
| A_static\|ONEQ | CA | 2003-10-01 | +2.37 | +2.06 | +2.47 | 100% | 100% | 100% | 0.055 | -55% | -55% | 1 | n/a | +2.12 | +2.88 | yes |
| A_static\|ONEQ | NONE | 2003-10-01 | +2.73 | +2.15 | +2.82 | 100% | 100% | 100% | 0.064 | -55% | -55% | 1 | n/a | +2.40 | +3.39 | yes |
| A_static\|IWF | CA | 2000-07-01 | +1.21 | -0.33 | +1.31 | 89% | 89% | 92% | 0.532 | -64% | -55% | 1 | -3.66 | +1.42 | +2.01 | no |
| A_static\|IWF | FED | 2000-07-01 | +1.30 | -0.35 | +1.40 | 89% | 89% | 92% | 0.538 | -64% | -55% | 1 | -3.66 | +1.51 | +2.19 | no |
| A_static\|IWF | NONE | 2000-07-01 | +1.40 | -0.35 | +1.50 | 89% | 89% | 92% | 0.551 | -64% | -55% | 1 | -3.66 | +1.60 | +2.37 | no |
| A_static\|IVW | CA | 2000-07-01 | +0.91 | +0.11 | +1.01 | 86% | 93% | 96% | 0.423 | -57% | -55% | 1 | -2.30 | +1.02 | +2.25 | no |
| A_static\|IVW | FED | 2000-07-01 | +0.99 | +0.11 | +1.09 | 86% | 93% | 96% | 0.427 | -57% | -55% | 1 | -2.30 | +1.09 | +2.46 | no |
| A_static\|IVW | NONE | 2000-07-01 | +1.06 | +0.12 | +1.16 | 86% | 93% | 96% | 0.422 | -57% | -55% | 1 | -2.30 | +1.15 | +2.66 | no |
| A_static\|VIGRX | CA | 2000-01-01 | +0.93 | +0.15 | +1.01 | 93% | 89% | 93% | 0.447 | -57% | -55% | 1 | -1.86 | +0.89 | +2.06 | no |
| A_static\|VIGRX | NONE | 2000-01-01 | +1.09 | +0.15 | +1.18 | 93% | 89% | 93% | 0.436 | -57% | -55% | 1 | -1.86 | +1.01 | +2.44 | no |
| B_blend\|SPY+IWF\|buyhold | CA | 2000-07-01 | +0.64 | -0.16 | +0.69 | 89% | 89% | 92% | 0.532 | -56% | -55% | 2 | -1.68 | +0.73 | +1.03 | no |
| B_blend\|SPY+IWF\|buyhold | FED | 2000-07-01 | +0.69 | -0.17 | +0.74 | 89% | 89% | 92% | 0.551 | -56% | -55% | 2 | -1.68 | +0.78 | +1.12 | no |
| B_blend\|SPY+IWF\|buyhold | NONE | 2000-07-01 | +0.74 | -0.17 | +0.79 | 89% | 89% | 92% | 0.560 | -56% | -55% | 2 | -1.68 | +0.83 | +1.22 | no |
| A_static\|MDY | CA | 2000-01-01 | +0.24 | +1.45 | +0.18 | 57% | 45% | 56% | 0.196 | -55% | -55% | 1 | +5.72 | -0.90 | -3.31 | no |
| A_static\|MDY | NONE | 2000-01-01 | +0.33 | +1.52 | +0.29 | 57% | 45% | 56% | 0.195 | -55% | -55% | 1 | +7.16 | -1.03 | -3.98 | no |
| C_pairmom\|SVLG\|lb63\|sk0\|M\|tax1 | CA | 2001-01-01 | +0.55 | +2.82 | +0.37 | 67% | 93% | 100% | 0.013 | -52% | -55% | 67 | +3.75 | +1.04 | +1.43 | no |
| C_pairmom\|SVLG\|lb63\|sk0\|M\|tax1 | FED | 2001-01-01 | +0.62 | +2.94 | +0.43 | 67% | 93% | 100% | 0.006 | -52% | -55% | 65 | +4.33 | +1.14 | +1.60 | no |
| C_pairmom\|SVLG\|lb63\|sk0\|M\|tax1 | NONE | 2001-01-01 | +1.29 | +1.68 | +1.32 | 79% | 91% | 87% | 0.196 | -55% | -55% | 163 | +4.29 | +1.16 | -1.27 | no |
| C_pairmom\|ML\|lb63\|sk21\|Q\|tax1 | CA | 2000-01-01 | +0.58 | +1.44 | +0.67 | 58% | 43% | 56% | 0.200 | -56% | -55% | 36 | +5.74 | -0.16 | -2.17 | no |
| C_pairmom\|ML\|lb63\|sk21\|Q\|tax1 | FED | 2000-01-01 | +0.68 | +1.49 | +0.78 | 58% | 43% | 56% | 0.198 | -55% | -55% | 40 | +6.45 | -0.14 | -2.39 | no |
| C_pairmom\|ML\|lb63\|sk21\|Q\|tax1 | NONE | 2000-01-01 | -0.43 | +0.78 | -0.47 | 46% | 45% | 37% | 0.306 | -54% | -55% | 107 | +7.08 | -1.96 | -5.57 | no |
| C_pairmom\|VG_R\|lb252\|sk21\|Q\|tax1 | CA | 2000-07-01 | +0.26 | +0.38 | +0.36 | 63% | 56% | 64% | 0.365 | -59% | -55% | 51 | -1.43 | +1.37 | +1.72 | no |
| C_pairmom\|VG_R\|lb252\|sk21\|Q\|tax1 | FED | 2000-07-01 | +0.30 | +0.39 | +0.41 | 63% | 56% | 64% | 0.362 | -59% | -55% | 51 | -1.43 | +1.47 | +1.90 | no |
| C_pairmom\|VG_R\|lb252\|sk21\|Q\|tax1 | NONE | 2000-07-01 | +1.55 | +0.50 | +1.56 | 98% | 100% | 100% | 0.323 | -56% | -55% | 45 | -0.19 | +1.19 | +0.52 | no |
| L_site\|SITE_STYLE8\|lb252\|top1\|Q\|tax_managed | CA | 2000-01-01 | +0.22 | +1.20 | +0.37 | 48% | 45% | 52% | 0.210 | -56% | -55% | 128 | +4.79 | -1.27 | +1.45 | no |
| L_site\|SITE_STYLE8\|lb252\|top1\|Q\|tax_managed | FED | 2000-01-01 | +0.29 | +1.31 | +0.43 | 49% | 47% | 52% | 0.198 | -56% | -55% | 128 | +5.40 | -1.34 | +1.60 | no |
| L_site\|SITE_STYLE8\|lb252\|top1\|Q\|tax_managed | NONE | 2000-01-01 | -1.82 | -0.02 | -1.94 | 12% | 6% | 19% | 0.510 | -63% | -55% | 105 | +2.28 | -2.29 | -0.53 | no |
| D_menumom\|MF5\|lb252\|sk21\|top1\|Q\|tax1 | CA | 2000-01-01 | +0.39 | -0.46 | +0.45 | 66% | 87% | 81% | 0.627 | -60% | -55% | 78 | +1.27 | +0.53 | +1.62 | no |
| D_menumom\|MF5\|lb252\|sk21\|top1\|Q\|tax1 | NONE | 2000-01-01 | +0.37 | -0.12 | +0.40 | 66% | 79% | 67% | 0.517 | -60% | -55% | 89 | +0.18 | +0.41 | -1.47 | no |
| C_pairmom\|VG_R\|lb252\|sk21\|Q\|std | CA | 2000-07-01 | +0.30 | -0.62 | +0.36 | 72% | 69% | 64% | 0.673 | -56% | -55% | 59 | -0.47 | -0.48 | -0.42 | no |
| C_pairmom\|VG_R\|lb252\|sk21\|Q\|std | FED | 2000-07-01 | +0.74 | -0.18 | +0.78 | 91% | 91% | 96% | 0.533 | -56% | -55% | 58 | -0.34 | +0.02 | -0.14 | no |
| C_pairmom\|VG_R\|lb252\|sk21\|Q\|std | NONE | 2000-07-01 | +1.55 | +0.50 | +1.56 | 98% | 100% | 100% | 0.323 | -56% | -55% | 45 | -0.19 | +1.19 | +0.52 | no |
| C_pairmom\|VG_SP\|lb252\|sk21\|Q\|std | CA | 2000-07-01 | +0.22 | -0.69 | +0.25 | 72% | 62% | 64% | 0.689 | -57% | -55% | 63 | -0.70 | -0.77 | +0.36 | no |
| C_pairmom\|VG_SP\|lb252\|sk21\|Q\|std | NONE | 2000-07-01 | +1.45 | +0.41 | +1.43 | 98% | 98% | 100% | 0.325 | -57% | -55% | 45 | -0.54 | +0.73 | +1.50 | no |
| C_pairmom\|SVLG\|lb126\|sk21\|Q\|std | CA | 2001-04-01 | -0.14 | +0.33 | -0.07 | 35% | 48% | 27% | 0.463 | -59% | -55% | 78 | n/a | -0.99 | -1.95 | no |
| C_pairmom\|SVLG\|lb126\|sk21\|Q\|std | FED | 2001-04-01 | +0.44 | +1.28 | +0.49 | 60% | 67% | 55% | 0.207 | -57% | -55% | 79 | n/a | -0.27 | -1.61 | no |
| C_pairmom\|SVLG\|lb126\|sk21\|Q\|std | NONE | 2001-04-01 | +1.89 | +3.05 | +1.89 | 98% | 95% | 100% | 0.037 | -57% | -55% | 64 | n/a | +1.97 | +0.07 | yes |
| C_pairmom\|ML\|lb63\|sk0\|Q\|std | CA | 2000-01-01 | -0.60 | -0.14 | -0.54 | 51% | 32% | 22% | 0.536 | -58% | -55% | 90 | +4.49 | -1.92 | -3.68 | no |
| C_pairmom\|ML\|lb63\|sk0\|Q\|std | NONE | 2000-01-01 | +2.07 | +3.17 | +2.06 | 66% | 87% | 100% | 0.005 | -53% | -55% | 82 | +7.23 | +0.71 | -0.01 | no |
| C_pairmom\|SL_SP\|lb63\|sk0\|Q\|std | CA | 2000-07-01 | -1.55 | -1.15 | -1.49 | 31% | 18% | 8% | 0.754 | -58% | -55% | 108 | +2.97 | -2.72 | -4.14 | no |
| C_pairmom\|SL_SP\|lb63\|sk0\|Q\|std | NONE | 2000-07-01 | +1.39 | +1.97 | +1.43 | 78% | 80% | 100% | 0.070 | -53% | -55% | 100 | +5.21 | +0.75 | -1.58 | no |
| D_menumom\|FACTOR\|lb63+126+252\|sk21\|top1\|Q\|std | CA | 2015-01-01 | -0.41 | +0.12 | -0.77 | 14% | n/a | n/a | 0.480 | -40% | -55% | 46 | n/a | n/a | +3.52 | no |
| D_menumom\|FACTOR\|lb63+126+252\|sk21\|top1\|Q\|std | NONE | 2015-01-01 | +3.11 | +4.50 | +2.80 | 100% | n/a | n/a | 0.044 | -34% | -55% | 39 | n/a | n/a | +9.29 | yes |
| F_meanrev\|MF3\|lb1008\|sk252\|A\|std | CA | 2000-01-01 | -0.27 | -0.10 | -0.23 | 54% | 30% | 30% | 0.517 | -51% | -55% | 27 | +3.34 | -1.32 | -2.51 | no |
| F_meanrev\|MF3\|lb1008\|sk252\|A\|std | NONE | 2000-01-01 | +0.74 | +1.28 | +0.80 | 66% | 74% | 67% | 0.201 | -51% | -55% | 17 | +4.19 | +0.52 | -2.40 | no |

Neighbourhood, rebalance-date offsets and execution lag of the CA standout (full protocol):

| config | regime | first start | score | full | 10y mean | 10y beat | 15y beat | 20y beat | boot p | max DD | SPY DD | trades | 2000(first)-10 | 2010-20 | 2020-26 | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N5_vgh\|VG_R\|lb252\|sk21\|Q\|h0.1\|tax1 | CA | 2000-07-01 | +0.94 | +1.02 | +0.87 | 77% | 91% | 92% | 0.201 | -57% | -55% | 9 | -0.16 | +1.42 | +1.67 | no |
| N5_vgh\|VG_R\|lb252\|sk0\|Q\|h0.06\|tax1 | CA | 2000-07-01 | +0.85 | +0.89 | +0.79 | 80% | 91% | 96% | 0.233 | -56% | -55% | 11 | -0.50 | +1.30 | +1.67 | no |
| N5_vgh\|VG_R\|lb252\|sk21\|Q\|h0.06\|tax0 | CA | 2000-07-01 | +0.94 | +0.81 | +0.88 | 82% | 91% | 92% | 0.247 | -60% | -55% | 5 | -0.71 | +1.42 | +2.01 | no |
| N1_hyst\|VG_R\|lb252\|sk21\|Q\|h0.03\|tax1 | CA | 2000-07-01 | +0.66 | +0.87 | +0.70 | 75% | 82% | 84% | 0.240 | -56% | -55% | 31 | -0.49 | -1.31 | +1.72 | no |
| N5_vgh\|VG_SP\|lb252\|sk21\|Q\|h0.06\|tax1 | CA | 2000-07-01 | +0.48 | +0.54 | +0.48 | 78% | 93% | 96% | 0.283 | -59% | -55% | 11 | -1.17 | +0.82 | +2.20 | no |
| N5_vgh\|SPYV/SPYG\|lb252\|sk21\|Q\|h0.06\|tax1 | CA | 2002-01-01 | +0.87 | +1.81 | +0.93 | 81% | 92% | 84% | 0.014 | -54% | -55% | 5 | n/a | +1.08 | +2.13 | yes |
| N1_hyst\|VG_R\|lb252\|sk21\|Q\|h0.06\|std | CA | 2000-07-01 | -0.00 | -0.34 | -0.09 | 45% | 24% | 36% | 0.594 | -56% | -55% | 30 | +0.02 | -1.17 | +1.64 | no |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off7\|lag0 | CA | 2000-07-01 | +0.86 | +1.55 | +0.73 | 75% | 93% | 100% | 0.068 | -60% | -55% | 19 | +1.19 | -0.82 | +1.77 | yes |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off7\|lag0 | NONE | 2000-07-01 | +0.61 | +1.00 | +0.50 | 65% | 82% | 96% | 0.166 | -54% | -55% | 25 | +2.75 | -0.87 | +0.98 | no |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off14\|lag0 | CA | 2000-07-01 | +1.06 | +1.65 | +1.05 | 88% | 96% | 96% | 0.054 | -53% | -55% | 13 | +1.38 | +1.31 | +1.80 | yes |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off14\|lag0 | NONE | 2000-07-01 | +0.59 | +0.38 | +0.48 | 66% | 82% | 96% | 0.349 | -54% | -55% | 25 | +1.30 | -0.84 | +0.73 | no |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off21\|lag0 | CA | 2000-07-01 | +1.02 | +1.12 | +1.01 | 88% | 98% | 100% | 0.149 | -53% | -55% | 17 | +0.11 | +1.30 | +1.83 | no |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off21\|lag0 | NONE | 2000-07-01 | +0.38 | -0.27 | +0.31 | 68% | 69% | 96% | 0.573 | -54% | -55% | 25 | -0.13 | -0.89 | +0.47 | no |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off0\|lag1 | CA | 2000-07-01 | +1.22 | +2.03 | +1.11 | 88% | 100% | 100% | 0.022 | -53% | -55% | 13 | +2.12 | +1.31 | +1.90 | yes |
| N5_vgh\|VG_R\|lb252\|sk21\|M\|h0.06\|tax1\|off0\|lag1 | NONE | 2000-07-01 | +1.15 | +1.31 | +1.01 | 78% | 98% | 100% | 0.109 | -51% | -55% | 21 | +2.63 | -0.80 | +2.51 | no |

## 3. The CA standout and why it is not "good confidence"

`N5_vgh|VG_R|lb252|sk21|M|h0.06|tax1` works as follows. Each month it ranks IWD and IWF (Russell 1000
value and growth) by their 12-month return skipping the last month. The signal is computed on VIVAX and
VIGRX closes lagged one day, so it is available from 2000. It switches only if the challenger leads by
more than 6 percentage points. It executes with the lab's tax-managed rule: losses are always sold, and
realized gains are capped at 1% of the portfolio per year.

* **What it actually did.** From 2000-07 it held IWF. It switched to IWD in 2000-12, back to IWF in
  2002-05, back to IWD in 2003-11, and finally to IWF in 2007-09, 2008-01 and 2008-12. Every sale was
  at a loss or small enough to fit the 1% gain budget. Since 2008-12 it has held IWF and never traded
  again: 13 trades in 26 years. The quarterly version switched growth to value once (2001-01) and value
  to growth once (2008-09). A 2013 start buys IWD and is still about 95% value in 2026 (-2.9 pp/yr to
  2026; 2014 start -2.6).
* **Neighbourhood.**
  * Monthly: 11 of 13 screen neighbours clear bar 1-3 in CA (hysteresis 3-10%, skip 0, tax0 and tax5
    budgets, the S&P 500, S&P 900 and IUSV/IUSG style pairs, growth-vs-SPY).
  * Quarterly: 11 of 25 screen neighbours (group N5) clear it.
  * On the full protocol the quarterly versions fail boot_p (0.20-0.28; S&P 500 V/G 0.28; SPYV/SPYG
    0.014 from 2002).
  * The same rule with standard execution scores 0.00.
  * Lookbacks of 189 or 315 days fail.
  * Rebalance offsets of 7, 14 and 21 days plus a 1-day lag give scores +0.86 to +1.22 and boot_p 0.022
    to 0.149. Four of five clear bar 1-3 in CA. In NONE, none does (boot_p 0.11-0.57).
* **Hindsight (PROTOCOL 5.3).**
  * Random pairs, same rule, CA: quarterly 1 of 24 pass (median score -0.69); monthly 2 of 24 (median
    -0.72). The passes are IUSG/SPYV, itself a value/growth pair, and IJR/QQQ. The rule works only where
    one leg is the growth or tech asset that won the era.
  * "Removing the star" by replacing growth with SPY (VS: IWD vs SPY) gives -0.11 (screen, CA).
  * Mid-cap value/growth (IWS/IWP) gives -0.53, and the plain-rule small-cap pairs IJS/IJT and IWN/IWO
    are negative.
* **Long history.** On VIVAX/VIGRX against VFINX, with quarterly starts 1994-2023, the twin fails in CA:
  +0.61 score, +0.79 full, 10-year beat 60%, boot_p 0.224. A 1995 start buys VIGRX and never trades
  again: the 1995 cost basis stayed below the price through 2000-02, so there was no loss to harvest
  and the budget froze it. Its 10-year windows starting 1994-99 are therefore negative. The pre-2000
  5-year windows are positive (+2.4 pp, 4 of 5).
* **Criterion 4.**
  * Family walk-forward selection is positive only when static growth funds are in the pool.
  * Restricted to dynamic strategies it is -1.6 pp/yr (10y/5y) and -0.6 pp/yr (5y/3y).
  * When the walk-forward picked this rule (2019) or its growth-vs-SPY sibling (2021), it lost 1.0 and
    1.9 pp/yr out of sample.
* **Verdict.** Criteria 1-3 pass (CA, monthly). Criterion 5 is mixed. Criteria 4, 6 and 7 fail or are
  not supported. Hindsight risk is high. This is a growth-era regime bet in disguise. It would have
  needed a growth regime after its last forced switch, which is what 2008-2026 happened to deliver.

## 4. Rotation and the rest, in CA (screen unless stated)

* **Pair momentum (C, 402 configs).** Pairs: value/growth, small/large, mid/large, small-value vs
  large-growth, equal-weight, low vs high vol.
  * Standard execution destroys the edge in CA.
  * With the 1% gain budget the best is SVLG (IWN vs IWF) 3-month: screen +0.81. On full: +0.55, full
    +2.82, boot_p 0.013, but 10-year beat only 67% because most of its excess is from 2001-04 starts.
  * The mid-cap 3-month rule (MDY vs SPY) is +0.58 on full with 10-year beat 58%.
  * Value/growth 12-1 is +0.26 on full.
* **Menu momentum (D, 480).** Menus: Russell 6 styles, S&P 5 styles, size-3, style-12, Vanguard fund
  menu, "smart beta" ETFs, factor ETFs.
  * Standard execution: CA medians -1.7 to -5.4 pp/yr.
  * Tax-managed: best +0.57 (fund menu), full protocol +0.39, boot_p 0.63.
  * The factor-ETF menu (QUAL/USMV/MTUM/VLUE/SIZE/...) exists only from 2015. It is +3.1 in NONE but
    -0.4 in CA.
* **Factor momentum (E).** Hold only styles beating SPY. Every config is negative (CA best -1.70, NONE
  best -0.10).
* **Mean reversion (F).** Buy the 3-5-year losers. CA best -0.07. NONE best +1.02, which fails
  (10-year beat 71%).
* **Ratio trend (G).** CA best +0.50 (VG n300 tax1, boot_p 0.10, 10-year beat 69%).
* **Long-horizon momentum (N3).** CA best +0.73 (MDY vs SPY, 3-year, annual), 10-year beat 65%.
* **Style vs SPY (N4).** CA best +0.66 (IWF vs SPY ratio trend), boot_p 0.17.
* **Low-vol / low-beta / high-beta (H).** CA best +0.42, boot_p 0.60. Low-vol cuts drawdowns to -42 to
  -45% but earns no excess.
* **Multi-factor composites (I).** All negative in CA.
* **Size seasonality (J).** All -2.1 to -3.1 in CA.
* **Macro switches (K)**, on SPY drawdown, the yield curve or VIX. Best +0.61, boot_p 0.88.
* **Site-expressible.** The website's own Combo / TaxManagedCombo with the momentum picker over
  style-only menus (L). Best: the 8 site style ETFs, 12-1 momentum, top 1, quarterly, tax-managed. CA
  full protocol +0.22, full +1.20, 10-year beat 48%, boot_p 0.21. A style-only menu does worse than the
  incumbent's 22-ETF menu.
* **CA execution variants (N1).**
  * Long-term-gains-only execution is *worse* than the 1% budget in 11 of 14 rule/cadence pairs: it
    realizes long-term gains freely.
  * A 5% budget is worse in 13 of 14. Its one screen pass (`N1_taxexec|VG_R|lb252|sk21|Q|tax5`, +0.49,
    boot_p 0.056) was not taken to full, because the hysteresis variant dominates it.
  * A 50% SPY core halves both excess and risk and passes nothing.

## 5. Long history 1986-2026 and the pre-2000 holdout

Index funds stand in for the style ETFs: VIGRX/VIVAX (value/growth, 1992), NAESX (small, 1980) and
VEXMX (extended market, 1987). The benchmark is VFINX. `ho5`/`ho10` are windows that **end before
2000**.

Protocol `long_screen` (yearly starts):

| config | regime | first start | score | full | 10y beat | 15y beat | boot p | ho5 mean | ho5 beat | ho10 mean | ho10 beat | first-2000 | 2000-10 | 2010-20 | 2020-26 | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LA_static\|VIGRX | CA | 1993-01-01 | +0.60 | +0.64 | 71% | 74% | 0.246 | +2.44 | 67% | n/a | n/a | +2.13 | -1.84 | +0.92 | +2.12 | no |
| LA_static\|VIGRX | NONE | 1993-01-01 | +0.72 | +0.65 | 71% | 74% | 0.263 | +2.83 | 67% | n/a | n/a | +2.41 | -1.84 | +1.04 | +2.51 | no |
| LA_static\|VIVAX | CA | 1993-01-01 | -0.56 | -0.73 | 42% | 42% | 0.786 | -2.71 | 33% | n/a | n/a | -2.59 | +1.99 | -0.94 | -2.57 | no |
| LA_static\|VIVAX | NONE | 1993-01-01 | -0.65 | -0.74 | 42% | 42% | 0.776 | -3.20 | 33% | n/a | n/a | -2.97 | +2.37 | -1.07 | -3.09 | no |
| LA_static\|NAESX | CA | 1986-01-01 | -0.50 | -2.38 | 48% | 62% | 0.895 | -4.80 | 30% | -5.23 | 0% | -8.11 | +4.31 | -0.69 | -3.43 | no |
| LA_static\|NAESX | NONE | 1986-01-01 | -0.55 | -2.42 | 48% | 62% | 0.874 | -5.82 | 30% | -5.97 | 0% | -8.89 | +5.39 | -0.79 | -4.14 | no |
| LA_static\|VEXMX | CA | 1988-01-01 | +0.04 | -0.57 | 52% | 67% | 0.676 | -1.44 | 25% | -2.34 | 0% | -1.90 | +2.16 | -0.68 | -2.74 | no |
| LA_static\|VEXMX | NONE | 1988-01-01 | +0.07 | -0.58 | 52% | 67% | 0.663 | -1.72 | 25% | -2.59 | 0% | -2.05 | +2.60 | -0.78 | -3.29 | no |
| LA_blend\|VFINX+VIGRX\|buyhold | CA | 1993-01-01 | +0.32 | +0.34 | 71% | 74% | 0.244 | +1.26 | 67% | n/a | n/a | +1.09 | -0.88 | +0.47 | +1.09 | no |
| LA_blend\|VFINX+VIGRX\|buyhold | NONE | 1993-01-01 | +0.39 | +0.34 | 71% | 74% | 0.259 | +1.47 | 67% | n/a | n/a | +1.24 | -0.88 | +0.53 | +1.29 | no |
| LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|std | CA | 1994-01-01 | +0.28 | -0.84 | 65% | 72% | 0.781 | +3.63 | 100% | n/a | n/a | n/a | -1.47 | +0.19 | -0.26 | no |
| LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|std | NONE | 1994-01-01 | +1.12 | +0.79 | 91% | 89% | 0.201 | +4.22 | 100% | n/a | n/a | n/a | -1.21 | +1.29 | +0.64 | no |
| LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|tax1 | CA | 1994-01-01 | +0.26 | +0.83 | 48% | 78% | 0.210 | +3.63 | 100% | n/a | n/a | n/a | -1.53 | +0.90 | +1.74 | no |
| LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|tax1 | CA | 1994-01-01 | +0.60 | +0.79 | 52% | 94% | 0.224 | +3.49 | 100% | n/a | n/a | n/a | +1.46 | -0.27 | +1.75 | no |
| LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|std | CA | 1994-01-01 | +0.46 | -0.34 | 65% | 50% | 0.658 | +3.49 | 100% | n/a | n/a | n/a | +1.55 | -2.50 | +1.19 | no |
| LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|std | NONE | 1994-01-01 | +1.38 | +1.40 | 83% | 94% | 0.059 | +4.11 | 100% | n/a | n/a | n/a | +2.25 | -1.47 | +2.09 | yes |
| LN5_vgh\|VG_MF\|lb252\|sk21\|Q\|h0.06\|tax1 | CA | 1994-01-01 | +0.34 | -1.18 | 57% | 89% | 0.924 | +1.08 | 50% | n/a | n/a | n/a | -0.07 | -1.04 | +1.75 | no |
| LD_menumom\|MF5\|lb252\|sk21\|top1\|Q\|tax1 | CA | 1994-01-01 | +0.57 | +0.83 | 61% | 83% | 0.209 | +3.62 | 100% | n/a | n/a | n/a | +1.30 | +0.55 | +1.68 | no |
| LC_pairmom\|ML_MF\|lb63\|sk0\|Q\|std | CA | 1989-01-01 | -2.32 | -3.73 | 14% | 13% | 1.000 | -5.28 | 0% | -5.84 | 0% | -5.74 | -0.58 | -2.27 | -2.78 | no |
| LC_pairmom\|ML_MF\|lb63\|sk0\|Q\|std | NONE | 1989-01-01 | +0.62 | +0.25 | 61% | 70% | 0.420 | -1.85 | 14% | -1.55 | 0% | -1.12 | -0.12 | +1.29 | +1.33 | no |
| LC_pairmom\|SL_MF\|lb63\|sk0\|Q\|std | CA | 1986-01-01 | -2.22 | -4.38 | 26% | 19% | 1.000 | -5.69 | 0% | -6.19 | 0% | -7.82 | +0.89 | -2.74 | -3.79 | no |
| LC_pairmom\|SL_MF\|lb63\|sk0\|Q\|std | NONE | 1986-01-01 | +0.46 | -0.84 | 61% | 85% | 0.734 | -3.40 | 0% | -3.46 | 0% | -4.86 | +2.82 | +0.72 | -0.97 | no |
| LJ_season\|NAESX/VFINX\|11-12-1\|std | CA | 1986-01-01 | -2.51 | -3.82 | 6% | 12% | 1.000 | -4.06 | 10% | -4.75 | 0% | -5.71 | +0.60 | -3.46 | -3.14 | no |
| LJ_season\|NAESX/VFINX\|11-12-1\|std | NONE | 1986-01-01 | +1.01 | +0.94 | 90% | 100% | 0.155 | +0.31 | 50% | +0.37 | 80% | -0.03 | +2.51 | +0.40 | +1.23 | no |

Protocol `long` (quarterly starts, finalists' twins):

| config | regime | first start | score | full | 10y beat | 15y beat | boot p | ho5 mean | ho5 beat | ho10 mean | ho10 beat | first-2000 | 2000-10 | 2010-20 | 2020-26 | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|tax1 | CA | 1994-01-01 | +0.61 | +0.79 | 60% | 94% | 0.224 | +2.37 | 80% | n/a | n/a | n/a | +1.46 | -0.27 | +1.75 | no |
| LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|tax1 | NONE | 1994-01-01 | +1.37 | +1.40 | 79% | 92% | 0.059 | +3.64 | 100% | n/a | n/a | n/a | +2.25 | -1.47 | +2.09 | yes |
| LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|std | CA | 1994-01-01 | +0.45 | -0.34 | 57% | 48% | 0.658 | +2.95 | 100% | n/a | n/a | n/a | +1.55 | -2.50 | +1.19 | no |
| LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|std | NONE | 1994-01-01 | +1.37 | +1.40 | 79% | 92% | 0.059 | +3.64 | 100% | n/a | n/a | n/a | +2.25 | -1.47 | +2.09 | yes |
| LA_static\|VIGRX | CA | 1993-01-01 | +0.65 | +0.64 | 73% | 80% | 0.246 | +2.65 | 89% | n/a | n/a | +2.13 | -1.84 | +0.92 | +2.12 | no |
| LA_static\|VIGRX | NONE | 1993-01-01 | +0.77 | +0.65 | 73% | 80% | 0.263 | +3.10 | 89% | n/a | n/a | +2.41 | -1.84 | +1.04 | +2.51 | no |
| LA_static\|NAESX | CA | 1986-01-01 | -0.51 | -2.38 | 47% | 58% | 0.895 | -4.81 | 30% | -5.90 | 0% | -8.11 | +4.31 | -0.69 | -3.43 | no |
| LA_static\|NAESX | NONE | 1986-01-01 | -0.58 | -2.42 | 47% | 58% | 0.874 | -5.89 | 30% | -6.79 | 0% | -8.89 | +5.39 | -0.79 | -4.14 | no |
| LA_static\|VIVAX | CA | 1993-01-01 | -0.59 | -0.73 | 40% | 39% | 0.786 | -2.88 | 11% | n/a | n/a | -2.59 | +1.99 | -0.94 | -2.57 | no |
| LA_static\|VIVAX | NONE | 1993-01-01 | -0.69 | -0.74 | 40% | 39% | 0.776 | -3.41 | 11% | n/a | n/a | -2.97 | +2.37 | -1.07 | -3.09 | no |
| LA_static\|VEXMX | CA | 1988-01-01 | +0.00 | -0.57 | 51% | 66% | 0.676 | -1.72 | 28% | -3.20 | 0% | -1.90 | +2.16 | -0.68 | -2.74 | no |
| LA_static\|VEXMX | NONE | 1988-01-01 | +0.01 | -0.58 | 51% | 66% | 0.663 | -2.07 | 28% | -3.57 | 0% | -2.05 | +2.60 | -0.78 | -3.29 | no |
| LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|std | CA | 1994-01-01 | +0.19 | -0.84 | 66% | 59% | 0.781 | +3.13 | 100% | n/a | n/a | n/a | -1.47 | +0.19 | -0.26 | no |
| LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|std | NONE | 1994-01-01 | +1.03 | +0.79 | 89% | 92% | 0.201 | +3.78 | 100% | n/a | n/a | n/a | -1.21 | +1.29 | +0.64 | no |
| LC_pairmom\|ML_MF\|lb63\|sk0\|Q\|std | CA | 1988-07-01 | -2.36 | -3.71 | 14% | 5% | 1.000 | -5.20 | 0% | -5.94 | 0% | -5.57 | -0.58 | -2.27 | -2.78 | no |
| LC_pairmom\|ML_MF\|lb63\|sk0\|Q\|std | NONE | 1988-07-01 | +0.56 | +0.25 | 62% | 70% | 0.389 | -2.12 | 7% | -2.12 | 0% | -1.06 | -0.12 | +1.29 | +1.33 | no |
| LC_pairmom\|SL_MF\|lb63\|sk0\|Q\|std | CA | 1986-01-01 | -2.12 | -4.38 | 24% | 20% | 1.000 | -5.33 | 0% | -6.04 | 0% | -7.82 | +0.89 | -2.74 | -3.79 | no |
| LC_pairmom\|SL_MF\|lb63\|sk0\|Q\|std | NONE | 1986-01-01 | +0.50 | -0.84 | 63% | 84% | 0.734 | -3.37 | 5% | -3.64 | 0% | -4.86 | +2.82 | +0.72 | -0.97 | no |

* **The ETF-era size winners are contradicted by the holdout.**
  * The 3-month mid/large switch (ML_MF) has a pre-2000 5-year mean of -2.1 pp in NONE (7% beat) and
    -5.2 pp in CA.
  * The small/large switch (SL_MF) has -3.4 pp (NONE) and -5.3 pp (CA).
  * Both are negative over 1986-2026 in CA (-2.4 and -2.1 score).
* **Value/growth 12-1 momentum is consistent in NONE but not in CA.**
  * VG_MF in NONE: +1.03, 10-year beat 89%, boot_p 0.20, pre-2000 5-year windows +3.8 pp (100%).
  * The hysteresis version clears bar 1-3 in NONE (+1.37, boot_p 0.059).
  * In CA both fail (+0.19, boot_p 0.78; +0.61, boot_p 0.22).
* **Long-history grid diagnostics (53 configs).**
  * CA walk-forward is -0.1 pp/yr (10y/5y) and -1.2 pp/yr (5y/3y), with PBO 0.60.
  * NONE has PBO 0.81-0.86, which means the in-sample best is usually below the median out of sample.

## 6. Overfitting diagnostics (`report.diagnostics`, CA and NONE)

The screen grid has 1,424 configs in CA and 815 in NONE, controls excluded and NONE tax twins dropped.
The lab default walk-forward steps 4 *starts*. On the yearly `screen` protocol that is one decision
every 4 years, only 3 decisions for 10y/5y. The "yearly" columns rerun `metrics.walk_forward` with
`step_quarters=1`.

| regime | subset | configs | WF 10y/5y OOS (lab default) | beat | WF 10y/5y OOS (yearly) | beat | avg config OOS | WF 5y/3y OOS (yearly) | beat | PBO | DSR of best | best by monthly mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | all | 1424 | +4.23 | 100% | +2.29 | 67% | -1.82 | +0.34 | 58% | 0.266 | 0.002 | A_static\|SPMO |
| CA | full_history | 898 | +4.23 | 100% | +2.29 | 67% | -1.67 | +1.81 | 74% | 0.183 | 0.021 | A_static\|QQQ |
| CA | dynamic_full_history | 772 | -2.13 | 0% | -1.63 | 0% | -1.73 | -0.56 | 32% | 0.339 | 0.008 | C_pairmom\|SVLG\|lb126\|sk21\|Q\|tax1 |
| NONE | all | 815 | +5.10 | 100% | +2.69 | 75% | -1.22 | +0.63 | 58% | 0.401 | 0.336 | A_static\|QQQ |
| NONE | full_history | 502 | +5.10 | 100% | +2.69 | 75% | -1.11 | +1.32 | 68% | 0.405 | 0.376 | A_static\|QQQ |
| NONE | dynamic_full_history | 400 | -1.58 | 33% | -1.18 | 33% | -0.99 | -0.43 | 53% | 0.565 | 0.260 | C_pairmom\|SVLG\|lb126\|sk21\|Q\|std |

Long-history grid (`long_screen`, 53 configs CA / 31 NONE):

| regime | subset | configs | WF 10y/5y OOS (lab default) | beat | WF 10y/5y OOS (yearly) | beat | avg config OOS | WF 5y/3y OOS (yearly) | beat | PBO | DSR of best | best by monthly mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| CA | all | 53 | -0.09 | 50% | -0.09 | 54% | -0.10 | -1.24 | 24% | 0.596 | 0.095 | LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|tax1 |
| CA | full_history | 49 | -0.09 | 50% | -0.09 | 54% | -0.10 | -1.04 | 27% | 0.441 | 0.029 | LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|tax1 |
| CA | dynamic_full_history | 41 | -0.27 | 33% | -0.45 | 38% | -0.21 | -1.16 | 24% | 0.348 | 0.036 | LC_pairmom\|VG_MF\|lb252\|sk21\|Q\|tax1 |
| NONE | all | 31 | +1.03 | 83% | +1.18 | 73% | +0.76 | -1.23 | 42% | 0.862 | 0.542 | LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|std |
| NONE | full_history | 28 | +1.03 | 83% | +1.18 | 73% | +0.76 | -0.64 | 45% | 0.812 | 0.497 | LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|std |
| NONE | dynamic_full_history | 20 | +0.78 | 67% | +1.17 | 69% | +0.91 | -0.70 | 42% | 0.813 | 0.573 | LN6_vghm\|VG_MF\|lb252\|sk21\|M\|h0.06\|std |

How to read this:

* The family "passes" criterion 4 only through **static growth funds**: the yearly walk-forward picks
  QQQ every year from 2015 to 2021 and it keeps winning. SPMO is the best config by monthly mean.
* Among strategies that actually rotate, out-of-sample selection loses in both regimes. CA: -1.6 pp/yr
  (10y/5y, 0 of 12 decisions positive), -0.6 pp/yr (5y/3y). NONE: -1.2 and -0.4. The NONE PBO is 0.57.
* The deflated Sharpe of the best config is 0.002-0.02 in CA.

## 7. Hindsight checks (PROTOCOL 5.3), summary

| check | result |
|---|---|
| late-launch growth funds (VUG, MGK, IWY, SCHG, ONEQ, SPMO) | pass in CA only on post-crash windows; IWF on the same windows passes too (HS) |
| random single ETFs, buy and hold (N2, CA) | 0 / 24 pass; best draws SOXX, QQQ, IWF, IVW |
| CA hysteresis rule on random pairs (HP2 quarterly, HP3 monthly, CA) | 1 / 24 and 2 / 24 pass, only pairs with a growth/tech leg; medians -0.69 / -0.72 |
| plain value/growth 12-1 rule on random pairs (HP, NONE) | 0 / 24 pass, median -2.11; VG_R (+1.76) would rank 2nd of 25 |
| plain 3-month size rule on random pairs (HP, NONE) | 0 / 24 pass, median -0.58; MDY/SPY (+2.28) would rank 2nd of 25 |
| SVLG 6-1 rule on random pairs (HP4, NONE) | 1 / 24 pass (IJR/QQQ), median -1.59; one pair scores above SVLG |
| other value/growth index families, plain 12-1 rule (ROB1, NONE) | large-cap pairs positive (SPYV/SPYG +0.51, IUSV/IUSG +0.47, RPV/RPG +0.93, VTV/VUG +1.36), none passes; mid/small pairs negative (IWS/IWP -0.37, IJS/IJT -1.27, IWN/IWO -2.09) |
| other size index families, 3-month rule (ROB1, NONE) | mid vs large positive (IJH/IVV +1.98, MDY/IVV +1.94) but 10y beat 63-69%; small vs large weaker (IJR/IVV +1.12, IWM/SPY +0.61); IJR/MDY -1.68 |
| pre-2000 holdout (long protocols) | contradicts the size rules (ho5 -2.1 to -5.3 pp); supports value/growth momentum only in NONE |

## Conclusion

For a California taxable account, this family offers **no strategy that beats SPY with good
confidence**.

* **Static tilts.** No static tilt except growth beat SPY over 2000-2026 by a meaningful margin.
  Value, dividend and low-vol lost; small and mid caps netted to about zero. The growth tilt's win comes
  from 2007-2026 and reverses in 2000-2009. Funds launched after the crash look confident only because
  their windows skip it. A growth tilt today is a bet that the 2010s-2020s regime continues, not a
  measured edge.
* **Rotations.** In CA, rotating between styles mostly converts deferred gains into realized ones. The
  one rule that survives CA taxes does so by *not* rotating after 2008 (tax-frozen in growth). Its
  long-history twin, its random-pair control and its out-of-sample walk-forward do not support it.
* **For a tax-deferred account**, value/growth momentum and the small-value/large-growth switch are
  the most persistent ideas, but none clears every criterion.
* **Comparison with the incumbent.** The incumbent's CA edge (+0.66 score) comes from 2000-10. Since
  2010 it, too, is mostly a frozen growth/tech book. Nothing here diversifies that bet. Every
  factor/style config that clears bar 1-3 in CA does one of two things:
  * holds large-cap growth, or a growth-heavy mega-cap or momentum fund, over windows that start after
    the 2000-02 crash; or
  * is a value/growth switch whose post-2008 holdings are growth (verified for the monthly and quarterly
    base rules).

## Notes, caveats and lab issues

* **Proxies.** Value/growth signals on IWD/IWF use VIVAX/VIGRX closes lagged one day, so 12-month
  lookbacks work from 2000. Those funds track S&P/Barra, then MSCI, then CRSP indexes, not Russell.
  Trading is always in the ETF. A one-day execution lag (OFF) does not change the CA result (+1.22).
* **Mutual-fund switching.** NAESX/VFINX timing (season J, long-history pairs) ignores the funds'
  frequent-trading restrictions.
* **Distributions.** The engine taxes distributions as deferred gains. That *understates* growth tilts
  slightly versus SPY in CA (see realism) and overstates dividend and value tilts, which lose anyway.
* **Comparisons and sources.** All comparisons are the engine's after-tax liquidation values, the
  website's numbers. Previous-researcher results are reused only where the config, the code hash and
  the cache are identical. Incumbent figures are the lead's (`_lead/verify_incumbent.log`).
* **Lab issues noticed (reported, not changed).**
  * **Walk-forward step on yearly protocols.** `metrics.walk_forward` steps `step_quarters` *starts*.
    On the yearly `screen` and `long_screen` protocols the default of 4 means one decision every 4
    years, only 3 decisions for 10y/5y on screen. `report.diagnostics` inherits this. Section 6 adds
    yearly-step results.
  * **realism.py bypasses the CPU slots.** `realism.record` runs backtests without `core.cpu_slot`, so
    it ignores the machine-wide limit and the battery throttle. This session wrapped its calls in a
    slot.
  * **`elapsed` includes slot waiting.** `sweep.run_one` starts its timer before acquiring a slot, so
    `elapsed` in cached records measures queueing, not compute.
  * **Duplicate tax twins in NONE.** Tax-execution configs are behaviourally identical to their
    standard twins in NONE but have different cache keys. Running both wastes compute and inflates
    NONE config counts in diagnostics. This session removes them in its own diagnostics.
