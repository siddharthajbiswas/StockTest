# Family `global` — international and global rotation

Module: `research/lab/families/global.py` (signals `global.rot`, `global.ratio`). Scripts, logs and
finalist lists: `research/lab/scratch/global/` (`s00`-`s17` sweeps, `q01`-`q03` queues, `a01`-`a07`
analysis, `fin1.json`/`fin2.json` finalists). Every run, every regime and protocol:
`research/lab/results/global_table.csv` (one row per config x regime x protocol; `protocol`, `block`
and `cfg_json` columns). All numbers are the site engine's (lab = site to 0.0), after the site's
5 + 5 bps costs and, in CA/FED, after tax with the terminal liquidation tax.

## Verdict

**No. Going global did not beat buying and holding SPY after California (or federal) tax with good
confidence, and nothing in this family clears the PROTOCOL section 3 bar in CA, FED or NONE.**
1459 distinct configurations were run (1277 on the ETF-era grid, 67 on the
1986-2026 long-history grid, 96 hindsight controls, plus finalist twins and timing variants).

* **Static international exposure lost.** Every buy-and-hold or rebalanced mix of SPY with
  international funds (VGTSX, EFA, VEU, VXUS, ACWI, VT, EEM, VEIEX, regional funds, 20 country funds)
  trails SPY over 2000-2026 in CA and NONE; the best, SPY 80 / VEIEX 20 never rebalanced, scores
  -0.08 pp/yr in CA on the full protocol. International diversification paid only in
  windows that ended by 2010.
* **The positive after-tax results are, with small exceptions, one bet on emerging markets in the
  2000s.** 133 of the 140 ETF-era family configs with a positive CA screen score have VEIEX or EEM in
  the menu (the other 7 are slow SPY-vs-VGTSX switches scoring at most +0.84 pp/yr, 10-year
  beat <= 0.53); the large ones hold Vanguard's emerging-markets index fund (VEIEX) through
  roughly 2002-2011. None of them has a 10-year beat rate above 0.53 (the bar is 0.75).
  The family's best CA score, a slow SPY-vs-VEIEX price-ratio switch (N1: 30-month
  ratio momentum, 5% band, quarterly), scores +2.67 pp/yr with boot_p
  0.04 on the full protocol, but it traded **twice in 26 years** (into VEIEX in
  April 2001, back to SPY in January 2012), its 10-year beat rate is 0.46 and its
  15-year beat rate 0.66, it is flat to negative in every 5-year window starting
  2010 or later (beat rate 0.00), its ETF twin (SPY vs EEM, 2005+) scores
  -2.06 pp/yr, and the same rule with 24 random funds in place of VEIEX averages
  -0.29 pp/yr (screen protocol).
* **Classic dual momentum (Antonacci's GEM) loses after tax, and before tax on ETFs.** SPY vs EFA with a T-bill test and an
  aggregate-bond fallback: -3.04 pp/yr CA score (-2.36 NONE),
  10-year beat rate 0.23; with the longer mutual-fund history (SPY vs VGTSX, 2000+)
  -0.79 CA / +0.34 NONE.
* **Country rotation, regional rotation, "cheap country" reversal and global equal weight all lose,
  most of them even before tax.** Best CA screen scores: country rotation
  -3.18, regional ETF rotation -5.65,
  long-term reversal / value-momentum among countries -1.15
  (best NONE -0.82), US/international reversal
  -3.27; equal-weight 20 countries + SPY -2.36 (full).
  Adding the 20 country funds to the incumbent preset's 22-ETF menu lowers it (full protocol, CA
  +0.34 vs the incumbent's +0.66; 10-year beat 0.34 vs 0.70).
* **Pre-2010 vs 2010-2026: opposite answers.** On the full protocol, the mean excess of 5-year
  windows ending by 2010 is +1.97 to +24.47 pp/yr across all finalists (CA and NONE);
  for 5-year windows starting in 2010 or later it is -11.74 to 0.00 pp/yr with
  beat rates 0.00-0.19. The 1986-1999 long-history holdout sides with 2010-2026:
  all 12 distinct long twins that can hold an international fund before 2000 (they use PRITX)
  lost to the S&P 500 fund in 5-year windows ending before 2000 in CA (holdout means -0.82
  to -3.78 pp/yr; FED -0.81 to -4.01; NONE +0.22 to
  -3.56). The VEIEX-only switches carry no pre-2000 information (VEIEX starts in 1994;
  their holdout excess is 0.00 to +0.03). The 2000s were the exception, not the rule.
* **The family-level overfitting diagnostics are negative.** Walk-forward selection (pick the best
  config on the trailing 10 years, hold it 5) earns -3.41 pp/yr out of
  sample in CA (beat rate 0.00) and -7.76 in NONE;
  PBO 0.64 (CA) / 0.59 (NONE); deflated Sharpe of the best config
  0.39 / 0.13.

For a California taxable account, this family's answer is: hold SPY (or the incumbent), not an
international rotation. If someone wants the 2000s-style emerging-markets bet, they should know it is
a single macro call, not a repeatable edge.

## What was tested

Signals (all target-weight signals run through the lab's `WeightStrategy`, so costs, lots, the
annual settlement and the terminal tax are the engine's; nothing reads the future: closes up to
today, the T-bill hurdle from `^IRX` lagged one day):

* `global.rot` - relative momentum over a menu (single or blended lookbacks, skip-month, rank or
  mean blend, Sharpe-scaled, 52-week-high, long-term reversal, value+momentum), top-N with
  hysteresis, absolute-momentum filter vs 0 / T-bills / another ticker (per pick, or on SPY alone
  as in GEM), safe-asset fallback or best-of-bonds, SPY core + rotation sleeve, trend gate, breadth gate.
* `global.ratio` - a US-vs-international switch on the price ratio away/home (ratio vs its SMA, SMA
  cross, or ratio momentum with a +-band; state persists, so the band is real hysteresis), full
  switch or 70/30 tilt, optional T-bill gate to bonds.
* Static mixes (`common.mix`, `buyhold`) and the site's own `TaxManagedCombo` (`combo`).

Instruments: SPY; mutual-fund proxies with pre-2000 history VGTSX (total international, 1996),
VEIEX (emerging markets, 1994), VEURX / VPACX (Europe / Pacific, 1990), PRITX, FOSFX, VWIGX, VTRIX
(active international, 1980s); ETFs EFA (2001), EEM (2003), VEA, VWO, VEU, VXUS, ACWI, VT, VGK, VPL,
ILF, EPP; 20 iShares country funds (17 from March 1996, EWZ/EWT/EWY from mid-2000); bonds/T-bills
VBMFX, VFISX, VFITX, VUSTX (VFIIX before 1986-12). Late-launch funds are gated with `requires` /
`require_days` (EFA/EEM menus start 2004-05, VEU 2009, VXUS 2013) so no window waits in cash for a
launch. Long-history configs use VFINX (benchmark), PRITX/VWIGX/VTRIX/FOSFX/VEURX/VPACX/VEIEX.

| block | idea | configs |
|---|---|---|
| S0 baselines | buy-and-hold / annual-rebalanced international mixes, ACWI, VT, VEU, VXUS, EW countries, the incumbent preset | 29 |
| A US-vs-intl rotation (GEM-style) | 5 menus (SPY/VGTSX, SPY/VGTSX/VEIEX, SPY/VEURX/VPACX/VEIEX, SPY/EFA, SPY/EFA/EEM) x 6 lookbacks x abs filter (none, T-bill on SPY, T-bill per pick) x 3 safe assets x hysteresis 0/3% x top 1/2 | 672 |
| F US/intl price-ratio switch | SPY vs VGTSX / VEIEX / VGTSX+VEIEX / EFA / EEM x SMA 100-400, ratio momentum 6-24m, SMA cross x band x full/70-30 tilt x T-bill gate | 195 |
| B country rotation | 20 country funds (+SPY) x 3 lookbacks x top 1/2/3/5 x monthly/quarterly x T-bill filter | 96 |
| E long-term reversal / value-momentum countries | buy the 3- or 5-year losers among countries (annual), value+momentum blend, long-term momentum contrast | 30 |
| C regional ETF rotation | EFA, EEM, VGK, VPL, EWJ, ILF, EPP (+SPY), 2004+ | 24 |
| H site TaxManagedCombo with countries | the site's momentum TaxManagedCombo / Combo on SPY+20 countries and on the incumbent's 22 ETFs + 20 countries | 16 |
| J SPY-anchored intl rotation | hold SPY unless an international fund (or country) beats SPY by 0 or 5% | 16 |
| K US/intl long-term reversal | hold the 3- or 5-year loser of SPY vs VGTSX (vs VEIEX) | 8 |
| N neighbourhood/cadence of A,F winners | lookback, hysteresis/band and cadence (M/Q/A) around the best A and F configs | 114 |
| X EW regions, ADM, ETF-only twins | equal-weight regions, 'accelerating dual momentum' (1-3-6m, long-Treasury fallback), the A winner on ETF-only menus | 11 |
| T tax-execution variants | the top 3 CA configs of every block with tax-managed execution (1% gain budget; 10% budget with no short-term gains) and a 50% drift band (CA only) | 61 |
| Y late ETFs, country refinements, core-satellite, TLH mixes | GEM with VEU/VXUS, country rotation with cash/short-Treasury/breadth/trend/inverse-vol variants, 50% SPY core + sleeve, global mixes with tax-loss harvesting | 16 |
| N+ controls of the N winner (without VEIEX; ETF twin SPY vs EEM) | the N winner's rule with VGTSX instead of VEIEX, and with EEM (2005+) | 2 |
| **ETF-era grid (unique)** | screened on `screen` (24 yearly starts 2000-2023) in CA and NONE (T: CA only) | **1277** |
| L1-L5 long classic (VFINX vs PRITX/VEIEX) | long-history proxies on `long_screen` (38 yearly starts 1986-2023, VFINX benchmark) | 36 |
| L6 long regional/FOSFX/VWIGX/VTRIX | long-history proxies on `long_screen` (38 yearly starts 1986-2023, VFINX benchmark) | 31 |
| Z hindsight controls | PROTOCOL 5.3 random menus / random 'away' funds (4 rules x 24) | 96 |
| finalists | 22 configs on `full` (95 quarterly starts) x CA/FED/NONE; 15 distinct long-history twins on `long` (151 starts) x CA/FED/NONE | |
| timing battery | rebalance-boundary offsets + 1-day execution lag for A1, F1, N1 (`full`, CA/NONE) | 18 |
| **all distinct configs** | | **1459** |

## Static international exposure (the baseline question)

Screen protocol (24 yearly starts), score in pp/yr; `pre-2010` = mean excess of 5-year windows that
end by 2010-01, `post-2010` = 5-year windows that start 2010-01 or later.

| allocation | first start | CA score | CA full excess | CA 10y beat | NONE score | CA 5y pre-2010 | CA 5y post-2010 | max DD (SPY -55%) |
|---|---|---|---|---|---|---|---|---|
| bh[SPY1.0] | 2000-01-01 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | -55% |
| bh[VFINX1.0] | 2000-01-01 | -0.03 | -0.04 | 0.00 | -0.04 | 0.00 | -0.04 | -55% |
| bh[SPY0.8,VEIEX0.2] | 2000-01-01 | -0.06 | -0.25 | 0.35 | -0.04 | +3.36 | -1.42 | -59% |
| mix[SPY0.8,VEIEX0.2] ; std/A req=SPY+VEIEX | 2000-01-01 | -0.30 | -0.19 | 0.35 | -0.22 | +2.64 | -1.64 | -57% |
| bh[SPY0.7,VGTSX0.3] | 2000-01-01 | -0.79 | -0.67 | 0.24 | -0.91 | +1.73 | -1.81 | -57% |
| bh[SPY0.6,VGTSX0.3,VEIEX0.1] | 2000-01-01 | -0.86 | -0.82 | 0.29 | -0.99 | +3.34 | -2.57 | -59% |
| mix[SPY0.7,VGTSX0.3] ; std/A req=SPY+VGTSX | 2000-01-01 | -1.01 | -0.85 | 0.29 | -1.12 | +1.56 | -2.01 | -57% |
| mix[SPY0.6,VGTSX0.3,VEIEX0.1] ; std/A req=SPY+VGTSX+VEIEX | 2000-01-01 | -1.16 | -0.95 | 0.29 | -1.25 | +2.90 | -2.82 | -58% |
| bh[SPY0.333,VGTSX0.333,VEIEX0.333] | 2000-01-01 | -1.33 | -1.27 | 0.29 | -1.54 | +6.73 | -4.65 | -62% |
| bh[SPY0.5,VGTSX0.5] | 2000-01-01 | -1.40 | -1.19 | 0.24 | -1.63 | +2.80 | -3.10 | -59% |
| mix[SPY0.333,VGTSX0.333,VEIEX0.333] ; std/A req=SPY+VGTSX+VEIEX | 2000-01-01 | -1.66 | -1.34 | 0.29 | -1.83 | +6.13 | -4.92 | -61% |
| mix[SPY0.5,VGTSX0.5] ; std/A req=SPY+VGTSX | 2000-01-01 | -1.68 | -1.43 | 0.24 | -1.90 | +2.62 | -3.34 | -58% |
| bh[SPY0.6,EFA0.3,EEM0.1] | 2004-01-01 | -1.73 | -1.15 | 0.08 | -2.03 | +2.19 | -2.52 | -58% |
| bh[SPY0.25,VEURX0.25,VPACX0.25,VEIEX0.25] | 2000-01-01 | -1.86 | -1.70 | 0.29 | -2.17 | +5.86 | -4.95 | -61% |
| bh[VEIEX1.0] | 2000-01-01 | -1.93 | -1.41 | 0.35 | -2.34 | +12.98 | -8.29 | -67% |
| mix[SPY0.6,EFA0.3,EEM0.1] ; std/A req=SPY+EFA+EEM | 2004-01-01 | -2.08 | -1.49 | 0.08 | -2.36 | +1.93 | -2.77 | -58% |
| mix[SPY0.25,VEURX0.25,VPACX0.25,VEIEX0.25] ; std/A req=SPY+VEURX+VPACX+VEIEX | 2000-01-01 | -2.09 | -1.79 | 0.29 | -2.37 | +5.44 | -5.14 | -60% |
| mixEW[C20+SPY] ; std/A | 2000-01-01 | -2.31 | -1.35 | 0.29 | -2.61 | +7.78 | -6.41 | -63% |
| mixEW[C20+SPY] ; std/Q | 2000-01-01 | -2.38 | -1.62 | 0.29 | -2.67 | +7.62 | -6.39 | -63% |
| mixEW[C20] ; std/A | 2000-01-01 | -2.43 | -1.44 | 0.29 | -2.77 | +8.16 | -6.74 | -63% |
| mixEW[C20] ; std/Q | 2000-01-01 | -2.50 | -1.70 | 0.29 | -2.82 | +8.00 | -6.71 | -64% |
| bh[PRITX1.0] | 2000-01-01 | -3.31 | -3.79 | 0.24 | -3.95 | +1.89 | -6.15 | -61% |
| bh[VGTSX1.0] | 2000-01-01 | -3.35 | -2.88 | 0.24 | -4.00 | +5.19 | -6.61 | -61% |
| bh[VEURX1.0] | 2000-01-01 | -3.42 | -2.90 | 0.24 | -4.08 | +4.33 | -6.11 | -63% |
| bh[VT1.0] | 2009-01-01 | -3.45 | -3.01 | 0.00 | -4.03 | n/a | -3.35 | -34% |
| bh[ACWI1.0] | 2009-01-01 | -3.49 | -3.05 | 0.00 | -4.07 | n/a | -3.37 | -34% |
| bh[VPACX1.0] | 2000-01-01 | -3.56 | -3.35 | 0.24 | -4.25 | +3.75 | -6.42 | -55% |
| bh[EFA1.0] | 2002-01-01 | -4.21 | -2.87 | 0.13 | -5.03 | +4.99 | -6.31 | -61% |
| bh[EWJ1.0] | 2000-01-01 | -4.69 | -4.70 | 0.00 | -5.61 | +1.23 | -6.24 | -59% |
| bh[EEM1.0] | 2004-01-01 | -5.43 | -2.75 | 0.15 | -6.55 | +9.65 | -8.79 | -66% |
| bh[VXUS1.0] | 2012-01-01 | -6.41 | -6.23 | 0.00 | -7.86 | n/a | -6.18 | -36% |
| bh[VEU1.0] | 2008-01-01 | -6.46 | -5.78 | 0.00 | -7.73 | n/a | -6.56 | -59% |

Not one static international allocation beats SPY over 2000-2026 in either regime. All of them were
ahead on average in the 5-year windows that ended by 2010 (the 2000-02 US bust, the 2003-07
emerging-markets boom) and behind in every single 5-year window that started in 2010 or later (beat
rate 0 for all of them, CA and NONE). ACWI / VT / VEU / VXUS exist only from 2008-2012, so they only
see the losing era.

## Screen results by block

Score = mean of the 5-, 10- and 15-year average after-tax excess (pp/yr). "pass bar" counts configs
with score > 0, full excess > 0, 10-year beat >= 0.75, 15-year beat >= 0.85 and boot_p <= 0.10 (the
per-config parts of the bar; the family-level parts fail anyway, see Diagnostics).

ETF era (`screen`):

| block | configs | CA: median score | CA: share > 0 | CA: best score (its ex10 beat, boot p) | NONE: median | NONE: best score (ex10 beat, boot p) | pass bar CA / NONE |
|---|---|---|---|---|---|---|---|
| S0 baselines | 29 | -2.31 | 0.03 | +0.64 (0.59, 0.03) | -2.61 | +0.26 (0.47, 0.34) | 0 / 0 |
| A US-vs-intl rotation (GEM-style) | 672 | -3.02 | 0.02 | +0.97 (0.41, 0.39) | -2.42 | +2.38 (0.53, 0.25) | 0 / 0 |
| F US/intl price-ratio switch | 195 | -1.51 | 0.14 | +1.44 (0.47, 0.36) | -0.69 | +2.63 (0.47, 0.18) | 0 / 0 |
| B country rotation | 96 | -4.62 | 0.00 | -3.18 (0.29, 0.56) | -3.95 | -0.61 (0.35, 0.33) | 0 / 0 |
| E long-term reversal / value-momentum countries | 30 | -4.50 | 0.00 | -1.15 (0.35, 0.62) | -4.68 | -0.82 (0.35, 0.50) | 0 / 0 |
| C regional ETF rotation | 24 | -7.60 | 0.00 | -5.65 (0.08, 0.93) | -8.36 | -5.42 (0.08, 0.73) | 0 / 0 |
| H site TaxManagedCombo with countries | 16 | -2.72 | 0.06 | +0.44 (0.35, 0.46) | -2.57 | -0.26 (0.41, 0.30) | 0 / 0 |
| J SPY-anchored intl rotation | 16 | -2.77 | 0.06 | +0.05 (0.47, 0.61) | -1.38 | +2.58 (0.47, 0.16) | 0 / 0 |
| K US/intl long-term reversal | 8 | -4.24 | 0.00 | -3.27 (0.24, 0.94) | -4.67 | -3.50 (0.24, 0.91) | 0 / 0 |
| N neighbourhood/cadence of A,F winners | 114 | +0.67 | 0.73 | +2.77 (0.47, 0.04) | +1.55 | +3.49 (0.53, 0.04) | 0 / 0 |
| X EW regions, ADM, ETF-only twins | 11 | -1.80 | 0.00 | -0.51 (0.47, 0.54) | -1.83 | +2.89 (0.53, 0.12) | 0 / 0 |
| T tax-execution variants | 61 | -1.61 | 0.31 | +2.25 (0.47, 0.16) | - | - | 0 / - |
| Y late ETFs, country refinements, core-satellite, TLH mixes | 16 | -2.74 | 0.00 | -0.28 (0.35, 0.65) | -1.50 | +0.74 (0.41, 0.22) | 0 / 0 |
| N+ controls of the N winner (without VEIEX; ETF twin SPY vs EEM) | 2 | -0.57 | 0.50 | +0.84 (0.41, 0.09) | -0.33 | +1.15 (0.41, 0.11) | 0 / 0 |

Long history (`long_screen`, 1986-2026, VFINX benchmark):

| block | configs | CA: median score | CA: share > 0 | CA: best score (its ex10 beat, boot p) | NONE: median | NONE: best score (ex10 beat, boot p) | pass bar CA / NONE |
|---|---|---|---|---|---|---|---|
| L1-L5 long classic (VFINX vs PRITX/VEIEX) | 36 | -0.65 | 0.36 | +1.87 (0.52, 0.53) | +0.28 | +3.64 (0.61, 0.16) | 0 / 0 |
| L6 long regional/FOSFX/VWIGX/VTRIX | 31 | -1.49 | 0.13 | +0.34 (0.48, 0.78) | -0.36 | +2.07 (0.55, 0.31) | 0 / 0 |

Best config of each block (by CA score, then by NONE score):

* S0 baselines [CA]: `combo[INC22] momentum252s21 top5 Q tax_managed0.01` +0.64
* S0 baselines [NONE]: `combo[INC22] momentum252s21 top5 Q tax_managed0.01` +0.26
* A US-vs-intl rotation (GEM-style) [CA]: `rot[SPY/VGTSX/VEIEX] 252s0 top1 hyst0.03 ; std/M` +0.97
* A US-vs-intl rotation (GEM-style) [NONE]: `rot[SPY/VGTSX/VEIEX] 252s0 top1 abs=tbill:SPY safe=VBMFX hyst0.03 ; std/M` +2.38
* F US/intl price-ratio switch [CA]: `ratio[SPY v VEIEX] mom504s0 band0.05 tilt1.0 ; std/M` +1.44
* F US/intl price-ratio switch [NONE]: `ratio[SPY v VEIEX] sma400 band0.03 tilt1.0 ; std/M` +2.63
* B country rotation [CA]: `rot[C20+SPY] 126s0 top1 abs=tbill:each safe=VFITX ; std/M` -3.18
* B country rotation [NONE]: `rot[C20+SPY] 126s0 top1 abs=tbill:each safe=VFITX ; std/M` -0.61
* E long-term reversal / value-momentum countries [CA]: `rot[C20+SPY] lt_mom1260s0 top5 ; std/A` -1.15
* E long-term reversal / value-momentum countries [NONE]: `rot[C20+SPY] lt_mom1260s0 top5 ; std/A` -0.82
* C regional ETF rotation [CA]: `rot[REG7+SPY] 126s0 top2 ; std/M req=EFA+EEM` -5.65
* C regional ETF rotation [NONE]: `rot[REG7+SPY] 126s0 top3 ; std/M req=EFA+EEM` -5.42
* H site TaxManagedCombo with countries [CA]: `combo[C20+SPY+QQQ+DIA+MDY+IWM+IJR+EFA+EEM+IWD+IWF+RSP+XLB+XLC+XLE+XLF+XLI+XLK+XLP+XLRE+XLU+XLV+XLY] momentum252s21 top5 Q tax_managed0.01` +0.44
* H site TaxManagedCombo with countries [NONE]: `combo[C20+SPY+QQQ+DIA+MDY+IWM+IJR+EFA+EEM+IWD+IWF+RSP+XLB+XLC+XLE+XLF+XLI+XLK+XLP+XLRE+XLU+XLV+XLY] momentum126s0 top3 Q tax_managed0.01` -0.26
* J SPY-anchored intl rotation [CA]: `rot[VGTSX/VEIEX] 126s0 top1 abs=vsSPY+0.05:each safe=SPY ; std/M` +0.05
* J SPY-anchored intl rotation [NONE]: `rot[VGTSX/VEIEX] 126s0 top1 abs=vsSPY+0.05:each safe=SPY ; std/M` +2.58
* K US/intl long-term reversal [CA]: `rot[SPY/VGTSX/VEIEX] lt_rev1260s0 top1 hyst0.1 ; std/Q` -3.27
* K US/intl long-term reversal [NONE]: `rot[SPY/VGTSX/VEIEX] lt_rev1260s0 top1 hyst0.1 ; std/Q` -3.50
* N neighbourhood/cadence of A,F winners [CA]: `ratio[SPY v VEIEX] mom630s0 band0.05 tilt1.0 ; std/Q` +2.77
* N neighbourhood/cadence of A,F winners [NONE]: `ratio[SPY v VEIEX] mom630s0 band0.05 tilt1.0 ; std/Q` +3.49
* X EW regions, ADM, ETF-only twins [CA]: `rot[SPY/VGTSX] 21-63-126s0 top1 abs=zero:each safe=VUSTX ; std/M` -0.51
* X EW regions, ADM, ETF-only twins [NONE]: `rot[SPY/VGTSX] 21-63-126s0 top1 abs=zero:each safe=VUSTX ; std/M` +2.89
* T tax-execution variants [CA]: `ratio[SPY v VEIEX] mom630s0 band0.05 tilt1.0 ; tax0.1noST/Q` +2.25
* Y late ETFs, country refinements, core-satellite, TLH mixes [CA]: `rot[VGTSX/VEIEX] 252s0 top1 abs=vsSPY:each safe=SPY core=SPY0.5 ; std/M` -0.28
* Y late ETFs, country refinements, core-satellite, TLH mixes [NONE]: `rot[VGTSX/VEIEX] 252s0 top1 abs=vsSPY:each safe=SPY core=SPY0.5 ; std/M` +0.74
* N+ controls of the N winner (without VEIEX; ETF twin SPY vs EEM) [CA]: `ratio[SPY v VGTSX] mom630s0 band0.05 tilt1.0 ; std/Q` +0.84
* N+ controls of the N winner (without VEIEX; ETF twin SPY vs EEM) [NONE]: `ratio[SPY v VGTSX] mom630s0 band0.05 tilt1.0 ; std/Q` +1.15
* L1-L5 long classic (VFINX vs PRITX/VEIEX) [CA]: `rot[VFINX/PRITX/VEIEX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; std/M` +1.87
* L1-L5 long classic (VFINX vs PRITX/VEIEX) [NONE]: `rot[VFINX/PRITX/VEIEX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; std/M` +3.64
* L6 long regional/FOSFX/VWIGX/VTRIX [CA]: `rot[VFINX/VWIGX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX ; std/M` +0.34
* L6 long regional/FOSFX/VWIGX/VTRIX [NONE]: `rot[VFINX/VWIGX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX ; std/M` +2.07

## Finalists on the full protocol (95 quarterly starts 2000-2026, SPY benchmark)

All values pp/yr except beat rates, boot p, drawdowns, trades and turnover (first-start run).
A = rotation (`global.rot`), F/N = ratio switch (`global.ratio`), B = countries, E = reversal,
S = static, H = site TaxManagedCombo, J = SPY-anchored; "b" = the same rule without VEIEX,
"e" = ETF twin. Exact configs: `fin1.json`, `fin2.json` and the CSV's `cfg_json`.

| finalist | regime | score | full_excess | ex5_mean | ex10_mean | ex10_beat | ex10_min | ex15_beat | ex20_beat | boot_p | max_dd | bench_max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | CA | +0.91 | +0.74 | +1.63 | +0.68 | 0.42 | -4.04 | 0.49 | 0.67 | 0.39 | -70% | -55% | 45 | 0.61 |
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | FED | +1.26 | +1.31 | +1.99 | +0.98 | 0.42 | -3.97 | 0.49 | 0.74 | 0.33 | -68% | -55% | 44 | 0.60 |
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | NONE | +1.87 | +2.14 | +2.68 | +1.49 | 0.43 | -3.56 | 0.53 | 0.85 | 0.23 | -65% | -55% | 32 | 0.59 |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | CA | +0.68 | +1.00 | +1.52 | +0.50 | 0.51 | -8.57 | 0.47 | 0.59 | 0.40 | -41% | -55% | 78 | 1.18 |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | FED | +1.09 | +1.65 | +1.89 | +0.89 | 0.51 | -9.01 | 0.49 | 0.67 | 0.33 | -40% | -55% | 78 | 1.18 |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | NONE | +2.14 | +2.93 | +2.91 | +1.92 | 0.51 | -8.87 | 0.53 | 0.85 | 0.25 | -38% | -55% | 62 | 1.17 |
| A3 rot SPY/VGTSX/VEIEX 1-3-6-12m blend top1 hyst3% | CA | +0.67 | +0.69 | +1.71 | +0.35 | 0.43 | -5.89 | 0.49 | 0.59 | 0.41 | -71% | -55% | 64 | 0.91 |
| A3 rot SPY/VGTSX/VEIEX 1-3-6-12m blend top1 hyst3% | FED | +1.19 | +1.49 | +2.18 | +0.87 | 0.43 | -5.79 | 0.51 | 0.74 | 0.31 | -67% | -55% | 64 | 0.91 |
| A3 rot SPY/VGTSX/VEIEX 1-3-6-12m blend top1 hyst3% | NONE | +2.25 | +2.72 | +3.19 | +1.91 | 0.45 | -4.50 | 0.53 | 0.85 | 0.17 | -63% | -55% | 45 | 0.89 |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | CA | -0.79 | -0.20 | -0.17 | -0.91 | 0.43 | -7.83 | 0.43 | 0.33 | 0.55 | -34% | -55% | 102 | 1.62 |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | FED | -0.54 | +0.36 | +0.02 | -0.67 | 0.46 | -8.14 | 0.47 | 0.41 | 0.47 | -34% | -55% | 100 | 1.64 |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | NONE | +0.34 | +1.56 | +0.87 | +0.20 | 0.51 | -7.66 | 0.47 | 0.52 | 0.32 | -34% | -55% | 78 | 1.65 |
| A5 classic GEM ETF SPY/EFA + T-bill test -> VBMFX (2003+) | CA | -3.04 | -3.19 | -2.18 | -3.36 | 0.23 | -8.54 | 0.11 | 0.00 | 0.88 | -34% | -55% | 106 | 1.79 |
| A5 classic GEM ETF SPY/EFA + T-bill test -> VBMFX (2003+) | FED | -3.03 | -2.69 | -2.25 | -3.38 | 0.23 | -8.97 | 0.17 | 0.00 | 0.83 | -34% | -55% | 105 | 1.81 |
| A5 classic GEM ETF SPY/EFA + T-bill test -> VBMFX (2003+) | NONE | -2.36 | -1.41 | -1.69 | -2.73 | 0.30 | -8.49 | 0.31 | 0.00 | 0.69 | -34% | -55% | 81 | 1.82 |
| F1 ratio SPY vs VEIEX 24m momentum band5% | CA | +1.37 | +1.04 | +2.34 | +1.07 | 0.45 | -4.08 | 0.49 | 0.85 | 0.36 | -67% | -55% | 24 | 0.32 |
| F1 ratio SPY vs VEIEX 24m momentum band5% | FED | +1.69 | +1.54 | +2.67 | +1.36 | 0.45 | -4.10 | 0.51 | 0.85 | 0.30 | -67% | -55% | 25 | 0.30 |
| F1 ratio SPY vs VEIEX 24m momentum band5% | NONE | +2.14 | +2.18 | +3.12 | +1.78 | 0.45 | -3.85 | 0.55 | 0.93 | 0.22 | -67% | -55% | 20 | 0.29 |
| F2 ratio SPY vs VEIEX SMA400 band3% | CA | +1.36 | +0.89 | +2.23 | +1.05 | 0.45 | -3.05 | 0.53 | 0.78 | 0.36 | -71% | -55% | 31 | 0.44 |
| F2 ratio SPY vs VEIEX SMA400 band3% | FED | +1.86 | +1.58 | +2.71 | +1.54 | 0.45 | -2.87 | 0.53 | 0.85 | 0.28 | -67% | -55% | 33 | 0.43 |
| F2 ratio SPY vs VEIEX SMA400 band3% | NONE | +2.56 | +2.46 | +3.39 | +2.21 | 0.45 | -2.39 | 0.55 | 0.93 | 0.18 | -63% | -55% | 22 | 0.42 |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | CA | +1.23 | +0.98 | +1.80 | +1.01 | 0.43 | -1.88 | 0.62 | 0.96 | 0.28 | -67% | -55% | 218 | 0.21 |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | FED | +1.54 | +1.30 | +2.15 | +1.29 | 0.43 | -1.78 | 0.62 | 0.96 | 0.24 | -64% | -55% | 218 | 0.21 |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | NONE | +1.94 | +1.72 | +2.59 | +1.64 | 0.43 | -1.95 | 0.62 | 1.00 | 0.18 | -61% | -55% | 216 | 0.20 |
| B1 country rotation C20+SPY 6m top1 + T-bill test -> VFITX | CA | -3.36 | -0.40 | -2.57 | -3.43 | 0.28 | -14.18 | 0.38 | 0.07 | 0.56 | -58% | -55% | 285 | 5.01 |
| B1 country rotation C20+SPY 6m top1 + T-bill test -> VFITX | FED | -3.01 | +0.41 | -2.11 | -3.12 | 0.30 | -15.14 | 0.38 | 0.15 | 0.50 | -58% | -55% | 285 | 5.02 |
| B1 country rotation C20+SPY 6m top1 + T-bill test -> VFITX | NONE | -0.78 | +3.19 | +0.61 | -1.00 | 0.39 | -15.84 | 0.45 | 0.48 | 0.33 | -58% | -55% | 273 | 5.04 |
| E1 cheap-country reversal C20 5y top3 annual | CA | -2.53 | -0.63 | -1.70 | -2.75 | 0.28 | -8.91 | 0.23 | 0.07 | 0.59 | -65% | -55% | 104 | 0.43 |
| E1 cheap-country reversal C20 5y top3 annual | FED | -2.45 | -0.09 | -1.59 | -2.70 | 0.28 | -9.62 | 0.26 | 0.11 | 0.53 | -61% | -55% | 104 | 0.43 |
| E1 cheap-country reversal C20 5y top3 annual | NONE | -1.94 | +0.93 | -0.96 | -2.26 | 0.30 | -10.21 | 0.32 | 0.15 | 0.41 | -56% | -55% | 104 | 0.43 |
| S1 buy-hold SPY 80 / VEIEX 20 | CA | -0.08 | -0.25 | +0.19 | -0.09 | 0.31 | -1.42 | 0.32 | 0.30 | 0.63 | -59% | -55% | 2 | 0.00 |
| S1 buy-hold SPY 80 / VEIEX 20 | FED | -0.07 | -0.25 | +0.20 | -0.07 | 0.31 | -1.51 | 0.32 | 0.30 | 0.62 | -59% | -55% | 2 | 0.00 |
| S1 buy-hold SPY 80 / VEIEX 20 | NONE | -0.06 | -0.26 | +0.22 | -0.05 | 0.31 | -1.59 | 0.32 | 0.30 | 0.61 | -59% | -55% | 2 | 0.00 |
| S2 buy-hold SPY 70 / VGTSX 30 | CA | -0.79 | -0.67 | -0.62 | -0.84 | 0.24 | -1.89 | 0.00 | 0.00 | 0.89 | -57% | -55% | 2 | 0.00 |
| S2 buy-hold SPY 70 / VGTSX 30 | FED | -0.86 | -0.70 | -0.70 | -0.90 | 0.24 | -2.03 | 0.00 | 0.00 | 0.88 | -57% | -55% | 2 | 0.00 |
| S2 buy-hold SPY 70 / VGTSX 30 | NONE | -0.92 | -0.72 | -0.78 | -0.96 | 0.24 | -2.16 | 0.00 | 0.00 | 0.87 | -57% | -55% | 2 | 0.00 |
| S3 global equal weight C20+SPY annual | CA | -2.36 | -1.35 | -1.43 | -2.59 | 0.30 | -8.41 | 0.30 | 0.00 | 0.75 | -63% | -55% | 564 | 0.05 |
| S3 global equal weight C20+SPY annual | FED | -2.54 | -1.25 | -1.62 | -2.79 | 0.30 | -9.22 | 0.30 | 0.00 | 0.71 | -62% | -55% | 564 | 0.05 |
| S3 global equal weight C20+SPY annual | NONE | -2.68 | -1.11 | -1.77 | -2.95 | 0.30 | -10.03 | 0.30 | 0.00 | 0.69 | -62% | -55% | 564 | 0.05 |
| F1b ratio SPY vs VGTSX 24m momentum band5% (F1 without VEIEX) | CA | +0.03 | +0.15 | +0.55 | -0.15 | 0.30 | -2.31 | 0.40 | 0.56 | 0.46 | -64% | -55% | 15 | 0.19 |
| F1b ratio SPY vs VGTSX 24m momentum band5% (F1 without VEIEX) | FED | +0.14 | +0.28 | +0.67 | -0.07 | 0.30 | -2.55 | 0.43 | 0.74 | 0.41 | -64% | -55% | 15 | 0.19 |
| F1b ratio SPY vs VGTSX 24m momentum band5% (F1 without VEIEX) | NONE | +0.38 | +0.53 | +0.88 | +0.14 | 0.33 | -2.80 | 0.47 | 0.81 | 0.34 | -64% | -55% | 11 | 0.18 |
| F2b ratio SPY vs VGTSX SMA400 band3% (F2 without VEIEX) | CA | +0.31 | +0.27 | +0.76 | +0.15 | 0.36 | -2.11 | 0.49 | 0.74 | 0.42 | -63% | -55% | 15 | 0.20 |
| F2b ratio SPY vs VGTSX SMA400 band3% (F2 without VEIEX) | FED | +0.51 | +0.46 | +0.98 | +0.32 | 0.36 | -1.93 | 0.51 | 0.85 | 0.37 | -62% | -55% | 15 | 0.20 |
| F2b ratio SPY vs VGTSX SMA400 band3% (F2 without VEIEX) | NONE | +0.77 | +0.75 | +1.27 | +0.54 | 0.39 | -2.09 | 0.55 | 0.89 | 0.30 | -60% | -55% | 13 | 0.20 |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | CA | +2.67 | +3.63 | +3.51 | +2.43 | 0.46 | -2.92 | 0.66 | 1.00 | 0.04 | -67% | -55% | 12 | 0.03 |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | FED | +3.01 | +4.04 | +3.93 | +2.72 | 0.46 | -3.03 | 0.66 | 1.00 | 0.04 | -67% | -55% | 11 | 0.03 |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | NONE | +3.38 | +4.46 | +4.40 | +3.04 | 0.49 | -2.88 | 0.70 | 1.00 | 0.04 | -67% | -55% | 5 | 0.02 |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | CA | +0.82 | +1.12 | +1.09 | +0.70 | 0.42 | -1.29 | 0.60 | 1.00 | 0.09 | -61% | -55% | 10 | 0.03 |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | FED | +0.95 | +1.21 | +1.24 | +0.82 | 0.42 | -1.17 | 0.60 | 1.00 | 0.11 | -61% | -55% | 9 | 0.02 |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | NONE | +1.14 | +1.30 | +1.46 | +1.00 | 0.42 | -1.06 | 0.60 | 1.00 | 0.11 | -61% | -55% | 5 | 0.02 |
| N1e ratio SPY vs EEM 30m momentum band5% quarterly (ETF twin, 2005-10+) | CA | -2.06 | -1.08 | -1.42 | -2.26 | 0.18 | -5.04 | 0.00 | 0.00 | 0.70 | -66% | -55% | 23 | 0.29 |
| N1e ratio SPY vs EEM 30m momentum band5% quarterly (ETF twin, 2005-10+) | FED | -2.02 | -0.64 | -1.53 | -2.24 | 0.18 | -5.26 | 0.00 | 0.00 | 0.62 | -66% | -55% | 22 | 0.28 |
| N1e ratio SPY vs EEM 30m momentum band5% quarterly (ETF twin, 2005-10+) | NONE | -1.92 | -0.08 | -1.62 | -2.15 | 0.18 | -5.41 | 0.00 | 0.00 | 0.53 | -66% | -55% | 11 | 0.28 |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | CA | +1.69 | +1.35 | +2.42 | +1.45 | 0.46 | -4.21 | 0.53 | 0.81 | 0.30 | -68% | -55% | 35 | 0.44 |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | FED | +2.30 | +2.19 | +2.96 | +2.06 | 0.46 | -4.23 | 0.57 | 0.85 | 0.22 | -64% | -55% | 35 | 0.43 |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | NONE | +3.12 | +3.32 | +3.72 | +2.86 | 0.49 | -4.18 | 0.60 | 1.00 | 0.11 | -58% | -55% | 22 | 0.41 |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | CA | +1.28 | +1.37 | +2.11 | +1.07 | 0.51 | -7.50 | 0.49 | 0.67 | 0.35 | -40% | -55% | 51 | 0.78 |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | FED | +1.63 | +1.95 | +2.44 | +1.39 | 0.51 | -7.93 | 0.51 | 0.74 | 0.31 | -39% | -55% | 52 | 0.77 |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | NONE | +2.18 | +2.79 | +3.02 | +1.90 | 0.51 | -8.20 | 0.53 | 0.85 | 0.26 | -37% | -55% | 42 | 0.77 |
| H1 site TaxManagedCombo 12-1 mom top5 Q, incumbent 22 ETFs + 20 country funds | CA | +0.34 | +0.41 | +0.71 | +0.32 | 0.34 | -4.57 | 0.49 | 0.85 | 0.46 | -67% | -55% | 290 | 0.12 |
| H1 site TaxManagedCombo 12-1 mom top5 Q, incumbent 22 ETFs + 20 country funds | FED | +0.40 | +0.42 | +0.81 | +0.41 | 0.36 | -5.06 | 0.49 | 0.81 | 0.46 | -67% | -55% | 290 | 0.12 |
| H1 site TaxManagedCombo 12-1 mom top5 Q, incumbent 22 ETFs + 20 country funds | NONE | -1.88 | -0.76 | -0.44 | -2.48 | 0.28 | -9.51 | 0.19 | 0.11 | 0.64 | -61% | -55% | 770 | 1.81 |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | CA | -0.06 | -0.37 | +0.33 | -0.09 | 0.45 | -4.67 | 0.51 | 0.48 | 0.61 | -62% | -55% | 117 | 1.71 |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | FED | +0.57 | +0.38 | +0.90 | +0.51 | 0.46 | -4.33 | 0.53 | 0.74 | 0.44 | -60% | -55% | 117 | 1.71 |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | NONE | +2.52 | +2.20 | +2.98 | +2.38 | 0.48 | -2.89 | 0.66 | 1.00 | 0.16 | -58% | -55% | 90 | 1.70 |

Average holdings, first-start run (2000-2026): A1 holds VEIEX 41% of the time, F1 41%,
N1 40%; the GEM-type rules with a T-bill test on SPY hold the bond fund (VBMFX) 24% of the
time (PROTOCOL 5.5: the engine taxes bond interest as deferred gains, which flatters them in CA/FED).

## Long history (151 quarterly starts 1986-2026, VFINX benchmark)

Long twins translate SPY -> VFINX, VGTSX/EFA -> PRITX, EEM -> VEIEX, VBMFX -> VBMFX (VFIIX before
1986-12). `ho5`/`ho10` = windows that **end before 2000**, a true holdout for ideas designed on
2000-2026 data. VEIEX starts in 1994, so rules that need 2-2.5 years of VEIEX history are simply
VFINX before 1996-1997 (their holdout excess is exactly 0: no information).

| finalist | regime | score | full_excess | ex10_beat | ex15_beat | boot_p | ho5_mean | ho5_beat | ho10_mean | ho10_beat | max_dd | bench_max_dd |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | CA | +1.55 | +0.02 | 0.50 | 0.66 | 0.46 | -1.05 | 0.35 | -1.54 | 0.18 | -72% | -55% |
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | FED | +2.03 | +1.09 | 0.50 | 0.72 | 0.26 | -0.95 | 0.38 | -1.14 | 0.18 | -69% | -55% |
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | NONE | +2.73 | +2.42 | 0.54 | 0.76 | 0.10 | -0.30 | 0.46 | -0.24 | 0.29 | -65% | -55% |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | CA | +1.99 | -0.13 | 0.53 | 0.69 | 0.53 | -1.62 | 0.19 | -2.26 | 0.00 | -41% | -55% |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | FED | +2.54 | +0.96 | 0.55 | 0.72 | 0.37 | -1.39 | 0.41 | -1.70 | 0.18 | -40% | -55% |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | NONE | +3.71 | +2.76 | 0.64 | 0.78 | 0.16 | +0.22 | 0.57 | +0.22 | 0.59 | -38% | -55% |
| A3 rot SPY/VGTSX/VEIEX 1-3-6-12m blend top1 hyst3% | CA | +1.38 | -0.05 | 0.50 | 0.66 | 0.51 | -0.82 | 0.43 | -1.35 | 0.18 | -72% | -55% |
| A3 rot SPY/VGTSX/VEIEX 1-3-6-12m blend top1 hyst3% | FED | +1.94 | +1.05 | 0.55 | 0.71 | 0.29 | -0.81 | 0.43 | -1.07 | 0.18 | -68% | -55% |
| A3 rot SPY/VGTSX/VEIEX 1-3-6-12m blend top1 hyst3% | NONE | +2.92 | +2.51 | 0.59 | 0.75 | 0.11 | -0.55 | 0.46 | -0.62 | 0.24 | -63% | -55% |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | CA | -0.55 | -2.03 | 0.49 | 0.52 | 0.83 | -2.47 | 0.08 | -3.10 | 0.00 | -36% | -55% |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | FED | -0.22 | -1.04 | 0.50 | 0.61 | 0.69 | -2.34 | 0.14 | -2.63 | 0.00 | -35% | -55% |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | NONE | +0.96 | +0.88 | 0.54 | 0.74 | 0.35 | -0.68 | 0.35 | -0.64 | 0.18 | -34% | -55% |
| A5 classic GEM ETF SPY/EFA + T-bill test -> VBMFX (2003+) | all | (same config as A4's twin) | | | | | | | | | | |
| F1 ratio SPY vs VEIEX 24m momentum band5% | CA | +1.30 | -0.18 | 0.44 | 0.65 | 0.52 | 0.00 | 0.00 | 0.00 | 0.00 | -68% | -55% |
| F1 ratio SPY vs VEIEX 24m momentum band5% | FED | +1.70 | +0.59 | 0.45 | 0.67 | 0.36 | 0.00 | 0.00 | 0.00 | 0.00 | -67% | -55% |
| F1 ratio SPY vs VEIEX 24m momentum band5% | NONE | +2.19 | +1.46 | 0.45 | 0.69 | 0.20 | 0.00 | 0.00 | 0.00 | 0.00 | -67% | -55% |
| F2 ratio SPY vs VEIEX SMA400 band3% | CA | +1.78 | +0.15 | 0.49 | 0.72 | 0.45 | +0.03 | 0.03 | +0.03 | 0.06 | -72% | -55% |
| F2 ratio SPY vs VEIEX SMA400 band3% | FED | +2.27 | +0.98 | 0.50 | 0.73 | 0.25 | +0.03 | 0.03 | +0.03 | 0.06 | -68% | -55% |
| F2 ratio SPY vs VEIEX SMA400 band3% | NONE | +2.97 | +2.01 | 0.52 | 0.75 | 0.11 | +0.07 | 0.03 | +0.07 | 0.06 | -63% | -55% |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | CA | -1.30 | -1.95 | 0.27 | 0.25 | 0.92 | -2.70 | 0.00 | -3.25 | 0.00 | -66% | -55% |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | FED | -1.13 | -1.23 | 0.30 | 0.32 | 0.80 | -2.90 | 0.00 | -3.17 | 0.00 | -63% | -55% |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | NONE | -0.82 | -0.37 | 0.32 | 0.37 | 0.59 | -2.72 | 0.30 | -2.76 | 0.00 | -61% | -55% |
| S2 buy-hold SPY 70 / VGTSX 30 | CA | -0.87 | -0.67 | 0.19 | 0.00 | 0.94 | -1.15 | 0.14 | -1.16 | 0.06 | -57% | -55% |
| S2 buy-hold SPY 70 / VGTSX 30 | FED | -0.94 | -0.67 | 0.19 | 0.00 | 0.93 | -1.27 | 0.14 | -1.23 | 0.06 | -57% | -55% |
| S2 buy-hold SPY 70 / VGTSX 30 | NONE | -1.01 | -0.68 | 0.19 | 0.00 | 0.91 | -1.39 | 0.14 | -1.30 | 0.06 | -57% | -55% |
| F1b ratio SPY vs VGTSX 24m momentum band5% (F1 without VEIEX) | CA | -1.92 | -2.47 | 0.04 | 0.00 | 0.99 | -3.16 | 0.03 | -3.82 | 0.00 | -64% | -55% |
| F1b ratio SPY vs VGTSX 24m momentum band5% (F1 without VEIEX) | FED | -1.93 | -1.99 | 0.06 | 0.00 | 0.97 | -3.42 | 0.03 | -3.75 | 0.00 | -64% | -55% |
| F1b ratio SPY vs VGTSX 24m momentum band5% (F1 without VEIEX) | NONE | -1.84 | -1.39 | 0.07 | 0.00 | 0.89 | -3.50 | 0.03 | -3.49 | 0.00 | -64% | -55% |
| F2b ratio SPY vs VGTSX SMA400 band3% (F2 without VEIEX) | CA | -1.67 | -2.14 | 0.03 | 0.00 | 0.97 | -2.22 | 0.24 | -2.78 | 0.00 | -66% | -55% |
| F2b ratio SPY vs VGTSX SMA400 band3% (F2 without VEIEX) | FED | -1.59 | -1.52 | 0.11 | 0.00 | 0.91 | -2.41 | 0.27 | -2.68 | 0.00 | -62% | -55% |
| F2b ratio SPY vs VGTSX SMA400 band3% (F2 without VEIEX) | NONE | -1.40 | -0.81 | 0.14 | 0.03 | 0.73 | -2.40 | 0.30 | -2.46 | 0.06 | -58% | -55% |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | CA | +3.08 | +1.78 | 0.52 | 0.82 | 0.13 | 0.00 | 0.00 | 0.00 | 0.00 | -67% | -55% |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | FED | +3.46 | +2.39 | 0.52 | 0.82 | 0.07 | 0.00 | 0.00 | 0.00 | 0.00 | -67% | -55% |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | NONE | +3.88 | +3.00 | 0.54 | 0.83 | 0.04 | 0.00 | 0.00 | 0.00 | 0.00 | -67% | -55% |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | CA | -1.08 | -1.39 | 0.20 | 0.04 | 0.91 | -2.79 | 0.11 | -3.30 | 0.00 | -64% | -55% |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | FED | -1.05 | -0.80 | 0.20 | 0.04 | 0.76 | -2.95 | 0.11 | -3.13 | 0.00 | -62% | -55% |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | NONE | -0.91 | -0.15 | 0.20 | 0.05 | 0.56 | -2.90 | 0.14 | -2.77 | 0.00 | -61% | -55% |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | CA | +2.02 | +0.25 | 0.50 | 0.68 | 0.44 | -1.37 | 0.35 | -2.00 | 0.00 | -69% | -55% |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | FED | +2.63 | +1.40 | 0.51 | 0.71 | 0.20 | -1.38 | 0.38 | -1.73 | 0.00 | -64% | -55% |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | NONE | +3.50 | +2.87 | 0.60 | 0.79 | 0.06 | -1.00 | 0.49 | -1.16 | 0.24 | -58% | -55% |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | CA | +1.38 | -0.83 | 0.50 | 0.62 | 0.61 | -3.78 | 0.00 | -4.41 | 0.00 | -37% | -55% |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | FED | +1.80 | +0.08 | 0.50 | 0.65 | 0.49 | -4.01 | 0.00 | -4.33 | 0.00 | -37% | -55% |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | NONE | +2.56 | +1.31 | 0.53 | 0.67 | 0.33 | -3.56 | 0.30 | -3.60 | 0.00 | -37% | -55% |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | CA | -0.48 | -2.31 | 0.40 | 0.60 | 0.94 | -3.01 | 0.05 | -3.79 | 0.00 | -62% | -55% |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | FED | +0.02 | -1.29 | 0.40 | 0.60 | 0.79 | -2.96 | 0.08 | -3.46 | 0.00 | -60% | -55% |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | NONE | +1.48 | +0.73 | 0.50 | 0.71 | 0.35 | -2.04 | 0.11 | -2.26 | 0.06 | -58% | -55% |

Reading: the rules whose pre-2000 holdout can be tested (anything using PRITX, the oldest
international fund) lose to VFINX in windows ending before 2000: CA holdout 5-year means
-0.82 to -3.78 pp/yr, FED -0.81 to -4.01, NONE +0.22
to -3.56 (1 of 12 positive in NONE). The positive
long-protocol scores of the VEIEX rules come from windows that overlap 2001-2011.

## Pre-2010 vs 2010-2026

Full protocol. Sub-period columns are the after-tax excess of the window from the first to the last
date (e.g. 2000-01 to 2010-01).

| finalist | regime | 2000-10 | 2010-20 | 2020-26 | 5y windows ending <= 2010 (n) | 5y windows starting >= 2010: mean (beat) |
|---|---|---|---|---|---|---|
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | CA | +6.77 | -2.41 | -3.21 | +12.69 (21) | -2.80 (0.00 of 47) |
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | NONE | +8.43 | -1.93 | -2.39 | +16.32 (21) | -2.85 (0.00 of 47) |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | CA | +12.84 | -5.45 | -6.00 | +16.23 (21) | -6.05 (0.00 of 47) |
| A2 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test on SPY -> VBMFX, hyst3% | NONE | +16.72 | -5.51 | -6.27 | +21.15 (21) | -6.86 (0.00 of 47) |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | CA | +9.69 | -5.48 | -5.83 | +10.38 (21) | -5.28 (0.00 of 47) |
| A4 classic GEM SPY/VGTSX + T-bill test -> VBMFX | NONE | +12.27 | -5.32 | -5.45 | +13.40 (21) | -5.29 (0.02 of 47) |
| A5 classic GEM ETF SPY/EFA + T-bill test -> VBMFX (2003+) | CA | n/a | -6.29 | -6.12 | +8.97 (10) | -5.30 (0.00 of 47) |
| A5 classic GEM ETF SPY/EFA + T-bill test -> VBMFX (2003+) | NONE | n/a | -6.06 | -5.96 | +11.59 (10) | -5.48 (0.00 of 47) |
| F1 ratio SPY vs VEIEX 24m momentum band5% | CA | +7.70 | -3.26 | -1.01 | +12.55 (21) | -1.52 (0.02 of 47) |
| F1 ratio SPY vs VEIEX 24m momentum band5% | NONE | +9.64 | -3.34 | -0.78 | +15.47 (21) | -1.71 (0.02 of 47) |
| F2 ratio SPY vs VEIEX SMA400 band3% | CA | +6.25 | -1.77 | -2.58 | +12.99 (21) | -1.93 (0.00 of 47) |
| F2 ratio SPY vs VEIEX SMA400 band3% | NONE | +8.85 | -1.36 | -2.63 | +16.75 (21) | -1.85 (0.04 of 47) |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | CA | +3.32 | -0.76 | -0.43 | +8.29 (21) | -0.03 (0.02 of 47) |
| F3 ratio SPY vs VGTSX+VEIEX SMA400 band3% | NONE | +4.98 | -0.87 | -0.08 | +11.01 (21) | -0.02 (0.02 of 47) |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | CA | +10.87 | -1.91 | 0.00 | +14.24 (21) | -0.59 (0.00 of 47) |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | NONE | +13.26 | -2.19 | 0.00 | +17.59 (21) | -0.73 (0.00 of 47) |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | CA | +3.00 | 0.00 | 0.00 | +4.79 (21) | 0.00 (0.00 of 47) |
| N1b ratio SPY vs VGTSX 30m momentum band5% quarterly (N1 without VEIEX) | NONE | +3.72 | 0.00 | 0.00 | +6.10 (21) | 0.00 (0.00 of 47) |
| N1e ratio SPY vs EEM 30m momentum band5% quarterly (ETF twin, 2005-10+) | CA | n/a | -4.59 | -0.04 | n/a (0) | -2.32 (0.00 of 47) |
| N1e ratio SPY vs EEM 30m momentum band5% quarterly (ETF twin, 2005-10+) | NONE | n/a | -4.93 | -0.04 | n/a (0) | -2.78 (0.00 of 47) |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | CA | +7.81 | -1.69 | -3.24 | +13.58 (21) | -2.56 (0.00 of 47) |
| N2 rot SPY/VGTSX/VEIEX 9m top1 hyst6% monthly | NONE | +10.75 | -0.99 | -2.65 | +17.58 (21) | -2.58 (0.04 of 47) |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | CA | +13.26 | -4.58 | -6.19 | +17.34 (21) | -5.23 (0.00 of 47) |
| N3 GEM-3 SPY/VGTSX/VEIEX 12m + T-bill test -> VBMFX hyst3% quarterly | NONE | +16.11 | -4.84 | -6.51 | +21.54 (21) | -6.15 (0.02 of 47) |
| B1 country rotation C20+SPY 6m top1 + T-bill test -> VFITX | CA | +10.33 | -9.24 | -2.00 | +12.98 (21) | -10.70 (0.02 of 47) |
| B1 country rotation C20+SPY 6m top1 + T-bill test -> VFITX | NONE | +17.88 | -10.43 | +0.99 | +24.47 (21) | -11.74 (0.04 of 47) |
| E1 cheap-country reversal C20 5y top3 annual | CA | +7.33 | -7.08 | -2.39 | +7.88 (21) | -5.50 (0.09 of 47) |
| E1 cheap-country reversal C20 5y top3 annual | NONE | +10.45 | -8.04 | -1.01 | +11.64 (21) | -5.97 (0.13 of 47) |
| S1 buy-hold SPY 80 / VEIEX 20 | CA | +2.57 | -1.29 | -1.18 | +3.74 (21) | -1.39 (0.00 of 47) |
| S1 buy-hold SPY 80 / VEIEX 20 | NONE | +3.16 | -1.47 | -1.41 | +4.59 (21) | -1.74 (0.00 of 47) |
| S2 buy-hold SPY 70 / VGTSX 30 | CA | +1.05 | -1.73 | -1.31 | +1.97 (21) | -1.76 (0.00 of 47) |
| S2 buy-hold SPY 70 / VGTSX 30 | NONE | +1.09 | -1.99 | -1.57 | +2.41 (21) | -2.20 (0.00 of 47) |
| S3 global equal weight C20+SPY annual | CA | +5.53 | -6.97 | -3.32 | +8.65 (21) | -6.15 (0.00 of 47) |
| S3 global equal weight C20+SPY annual | NONE | +7.05 | -8.19 | -3.91 | +10.85 (21) | -7.78 (0.00 of 47) |
| H1 site TaxManagedCombo 12-1 mom top5 Q, incumbent 22 ETFs + 20 country funds | CA | +5.88 | -1.78 | -0.26 | +10.77 (21) | -3.00 (0.04 of 47) |
| H1 site TaxManagedCombo 12-1 mom top5 Q, incumbent 22 ETFs + 20 country funds | NONE | +2.63 | -7.31 | +3.95 | +11.62 (21) | -3.72 (0.19 of 47) |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | CA | +5.63 | -3.57 | -4.23 | +6.39 (21) | -3.21 (0.00 of 47) |
| J1 SPY unless VGTSX/VEIEX beats SPY by 5% (6m), monthly | NONE | +9.04 | -2.02 | -2.97 | +12.85 (21) | -2.46 (0.00 of 47) |

Long history, 5-year windows by era (CA): A1 twin ends<=2000 -1.05 / 2000-2010 +13.42 / starts>=2010 -2.90;
A4 (classic GEM, PRITX) -2.47 / +7.18 / -5.06; N1b (PRITX) -2.79 / +1.60 / -0.41.

## Robustness

### Parameter neighbourhood and cadence (block N, screen protocol)

| subset | regime | configs | median score | share > 0 | best score | max 10y beat | boot p <= 0.10 | pass bar |
|---|---|---|---|---|---|---|---|---|
| rotation SPY/VGTSX/VEIEX (lookback 9/12/15m x hysteresis 0-10% x M/Q/A x T-bill gate) | CA | 72 | +0.20 | 0.58 | +1.67 | 0.53 | 0 | 0 |
| rotation SPY/VGTSX/VEIEX (lookback 9/12/15m x hysteresis 0-10% x M/Q/A x T-bill gate) | NONE | 72 | +1.02 | 0.81 | +3.07 | 0.53 | 0 | 0 |
| ratio SPY vs VEIEX (momentum 18/24/30m, SMA 300-500, bands, M/Q) + SPY vs VGTSX/VEIEX basket | CA | 42 | +1.24 | 0.98 | +2.77 | 0.53 | 3 | 0 |
| ratio SPY vs VEIEX (momentum 18/24/30m, SMA 300-500, bands, M/Q) + SPY vs VGTSX/VEIEX basket | NONE | 42 | +1.96 | 1.00 | +3.49 | 0.53 | 4 | 0 |

The neighbourhood is positive on average (it was built around the winners), but **no neighbour
reaches a 10-year beat rate of 0.75** and none passes the bar. Within the ratio switches, the score
rises as trading falls (correlation of CA score with log(trades): -0.45): the best
neighbours are the ones that switched into VEIEX once around 2001-2002 and out once around
2011-2012. Slower cadences and wider bands help in CA only by removing switches, i.e. by turning
the rule into a static EM bet held through 2001-2011.

### Tax-managed execution (block T: the top 3 CA configs of every block, CA, screen)

| execution variant (vs the same signal, standard execution) | configs | mean change in CA score | share improved | best CA score | mean change in 10y beat | max 10y beat | median trades (parent) |
|---|---|---|---|---|---|---|---|
| drift band 50% | 7 | -3.71 | 0.14 | -5.53 | -0.17 | 0.08 | 0 (510) |
| tax 1% | 27 | +0.10 | 0.52 | +1.37 | -0.08 | 0.41 | 63 (104) |
| tax 10%, no short-term gains | 27 | -0.14 | 0.59 | +2.25 | -0.01 | 0.53 | 89 (104) |

The best tax-managed config (ratio[SPY v VEIEX] mom630s0 band0.05 tilt1.0 ; tax0.1noST/Q) scores
+2.25; 0 of 61 pass the bar. Tax-managed execution is a wash on
average: a 1% gain budget mostly freezes the switches (a rotation that cannot sell its winner stops
rotating), and allowing only long-term gains keeps most of the score; neither lifts a 10-year beat
rate anywhere near 0.75. The "drift band 50%" rows are degenerate and should be ignored as a test:
with target weights of 1/N <= 50%, a 50% band blocks every trade, so those configs never invest
(median 0 trades) and sit in 0%-yield cash. They are reported only because they were run
(the design came from the first researcher's stage-2 script and was not caught before running).

### Rebalance-date offsets and execution lag (full protocol, `weights_x`)

| finalist | regime | score at each boundary offset (days: score) | score mean [min, max] | full excess mean [min, max] | 10y beat range | 1-day lag: score, 10y beat, boot p |
|---|---|---|---|---|---|---|
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | CA | 0: +0.91, 7: +0.71, 14: +0.81, 21: +0.38 | +0.70 [+0.38, +0.91] | +0.38 [-0.11, +0.74] | 0.42-0.43 | +0.79, 0.40, 0.37 |
| A1 rot SPY/VGTSX/VEIEX 12m top1 hyst3% | NONE | 0: +1.87, 7: +1.80, 14: +1.81, 21: +1.37 | +1.71 [+1.37, +1.87] | +1.83 [+1.27, +2.14] | 0.42-0.43 | +1.69, 0.42, 0.20 |
| F1 ratio SPY vs VEIEX 24m momentum band5% | CA | 0: +1.37, 7: +0.66, 14: +1.80, 21: +0.73 | +1.14 [+0.66, +1.80] | +0.91 [+0.46, +1.51] | 0.36-0.45 | +1.32, 0.45, 0.33 |
| F1 ratio SPY vs VEIEX 24m momentum band5% | NONE | 0: +2.14, 7: +1.39, 14: +2.57, 21: +1.29 | +1.85 [+1.29, +2.57] | +1.95 [+1.50, +2.60] | 0.37-0.45 | +2.07, 0.45, 0.20 |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | CA | 0: +2.67, 14: +2.70, 28: +1.06, 42: +0.98, 56: +2.55, 70: +2.50, 84: +2.42 | +2.13 [+0.98, +2.70] | +2.90 [+1.56, +3.63] | 0.34-0.49 | +2.62, 0.60, 0.03 |
| N1 ratio SPY vs VEIEX 30m momentum band5% quarterly (2 switches) | NONE | 0: +3.38, 14: +3.43, 28: +1.84, 42: +1.73, 56: +3.31, 70: +3.25, 84: +3.11 | +2.86 [+1.73, +3.43] | +3.77 [+2.56, +4.47] | 0.34-0.51 | +3.33, 0.60, 0.02 |

Every offset keeps a positive score and the one-day lag changes little, so the scores are not
rebalance-date luck. What none of the variants fixes is the 10-year beat rate: the edge sits in one
decade, whatever the rebalance day.

### Hindsight (PROTOCOL 5.3): the same rules on menus nobody chose

24 random draws per rule from the pre-registered `common.BROAD_EQUITY_POOL_2003` (fixed seeds),
screen protocol. The winners' star is VEIEX: emerging markets were the best asset class of
2002-2007, and every positive CA config in the family holds it.

| control | regime | VEIEX version's score | random: mean | median | [p25, p75] | max | share > 0 | random draws scoring >= the VEIEX version | pass bar |
|---|---|---|---|---|---|---|---|---|---|
| A1 rule (12m momentum, top 1, 3% hysteresis) on [SPY + 2 random funds] | CA | +0.97 | -1.65 | -1.59 | [-2.67, -0.42] | +2.36 | 0.21 | 2 of 24 | 0 |
| A1 rule (12m momentum, top 1, 3% hysteresis) on [SPY + 2 random funds] | NONE | +1.90 | -0.78 | -0.69 | [-1.96, +0.62] | +3.84 | 0.33 | 3 of 24 | 0 |
| A2 rule (same + T-bill test on SPY -> VBMFX) on the same 24 menus | CA | +0.92 | -1.31 | -1.39 | [-2.31, -0.47] | +2.03 | 0.21 | 2 of 24 | 0 |
| A2 rule (same + T-bill test on SPY -> VBMFX) on the same 24 menus | NONE | +2.38 | -0.05 | -0.14 | [-1.36, +1.11] | +4.28 | 0.42 | 2 of 24 | 0 |
| F1 rule (SPY vs X, 24m ratio momentum, 5% band, monthly), X random | CA | +1.44 | -0.67 | -0.43 | [-1.23, +0.07] | +0.99 | 0.25 | 0 of 24 | 0 |
| F1 rule (SPY vs X, 24m ratio momentum, 5% band, monthly), X random | NONE | +2.18 | -0.26 | -0.14 | [-0.89, +0.60] | +1.84 | 0.42 | 0 of 24 | 0 |
| N1 rule (SPY vs X, 30m ratio momentum, 5% band, quarterly), X random | CA | +2.77 | -0.29 | -0.13 | [-0.74, +0.23] | +1.87 | 0.46 | 0 of 24 | 0 |
| N1 rule (SPY vs X, 30m ratio momentum, 5% band, quarterly), X random | NONE | +3.49 | +0.03 | +0.05 | [-0.41, +0.53] | +2.49 | 0.50 | 0 of 24 | 0 |

On random menus the same rules lose to SPY on average in CA. The best random draws are themselves
hindsight-flavoured (SPY/QQQ/IBB for H1; Singapore and Canada, the same 2000s commodity/EM boom,
for H4).

### Star removed and ETF-only twins

| config | protocol | first start | CA score | CA 10y beat | CA boot p | NONE score |
|---|---|---|---|---|---|---|
| A1 (SPY/VGTSX/VEIEX) | full | 2000-01-01 | +0.91 | 0.42 | 0.39 | +1.87 |
| A1 without VEIEX (SPY/VGTSX) | screen | 2000-01-01 | -0.88 | 0.29 | 0.82 | -0.23 |
| A1 on ETFs (SPY/EFA/EEM, 2005+) | screen | 2005-01-01 | -3.69 | 0.00 | 0.91 | -3.26 |
| F1 (SPY vs VEIEX) | full | 2000-01-01 | +1.37 | 0.45 | 0.36 | +2.14 |
| F1b without VEIEX (SPY vs VGTSX) | full | 2000-01-01 | +0.03 | 0.30 | 0.46 | +0.38 |
| F2 (SPY vs VEIEX) | full | 2000-01-01 | +1.36 | 0.45 | 0.36 | +2.56 |
| F2b without VEIEX | full | 2000-01-01 | +0.31 | 0.36 | 0.42 | +0.77 |
| N1 (SPY vs VEIEX) | full | 2000-01-01 | +2.67 | 0.46 | 0.04 | +3.38 |
| N1b without VEIEX (SPY vs VGTSX) | full | 2000-01-01 | +0.82 | 0.42 | 0.09 | +1.14 |
| N1e on ETFs (SPY vs EEM, 2005-10+) | full | 2005-10-01 | -2.06 | 0.18 | 0.70 | -1.92 |
| A4 GEM on VGTSX (2000+) | full | 2000-01-01 | -0.79 | 0.43 | 0.55 | +0.34 |
| A5 GEM on EFA (2003+) | full | 2002-10-01 | -3.04 | 0.23 | 0.88 | -2.36 |

Without VEIEX the scores fall to about zero or below; on ETFs that a buyer could actually have used
(EFA/EEM from 2003, VEA/VWO/VEU from 2005-2009) every version loses, because those funds' histories
start after most of the emerging-markets run.

## Diagnostics (`report.diagnostics` on the screened grids)

Configs whose first window start is later than the protocol's (EFA/EEM/VEU/VXUS menus) are left out
of PBO and the deflated Sharpe, because `metrics.monthly_matrix` keeps only months common to every
config (see lab notes); the walk-forward rows use the same set (the walk-forward over all configs
gives the same choices). Hindsight controls are excluded.

| grid | regime | configs used (first start = protocol start) | walk-forward 10y->5y: OOS mean (beat) | its in-sample mean | average config OOS | walk-forward 5y->3y: OOS mean (beat) | PBO | OOS of the IS-best (CSCV) | deflated Sharpe of best |
|---|---|---|---|---|---|---|---|---|---|
| ETF era 2000-2026 | CA | 895 of 1277 | -3.41 (0.00) | +7.47 | -6.76 | -6.35 (0.25) | 0.64 | -2.83 | 0.39 |
| ETF era 2000-2026 | NONE | 843 of 1277 | -7.76 (0.00) | +9.42 | -7.88 | -5.50 (0.00) | 0.59 | -1.26 | 0.13 |
| long history 1986-2026 | CA | 54 of 67 | +1.23 (0.33) | +5.97 | -0.10 | +1.37 (0.25) | 0.56 | -2.09 | 0.03 |
| long history 1986-2026 | NONE | 54 of 67 | +1.21 (0.50) | +8.53 | +0.73 | +2.48 (0.38) | 0.55 | -0.31 | 0.10 |

Walk-forward choices (decision date, config chosen on the trailing 10 years, its in-sample and next-5-year excess):

| grid | regime | T | chosen | IS excess | OOS excess |
|---|---|---|---|---|---|
| screen | CA | 2012-01-01 | `rot[C20+SPY] 126s0 top1 abs=tbill:each safe=VFITX ; tax0.01/M` | +18.27 | -2.26 |
| screen | CA | 2016-01-01 | `rot[SPY/VGTSX/VEIEX] 252s0 top1 abs=tbill:SPY safe=VBMFX hyst0.06 ; std/M` | +4.14 | -7.96 |
| screen | CA | 2020-01-01 | `ratio[SPY v VGTSX+VEIEX] sma300 band0.06 tilt1.0 ; std/M` | 0.00 | 0.00 |
| screen | NONE | 2012-01-01 | `rot[SPY/VGTSX/VEIEX] 21-63-126s0 top1 abs=zero:each safe=VUSTX ; std/M` | +21.33 | -9.39 |
| screen | NONE | 2016-01-01 | `rot[SPY/VGTSX/VEIEX] 21-63-126s0 top1 abs=zero:each safe=VUSTX ; std/M` | +6.94 | -13.88 |
| screen | NONE | 2020-01-01 | `ratio[SPY v VGTSX+VEIEX] sma300 band0.06 tilt1.0 ; std/M` | 0.00 | 0.00 |
| long_screen | CA | 1998-01-01 | `bh[VFINX1.0]` | 0.00 | 0.00 |
| long_screen | CA | 2002-01-01 | `rot[VFINX/PRITX/VEIEX] 21-63-126-252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; st` | +1.32 | +18.13 |
| long_screen | CA | 2006-01-01 | `rot[VFINX/PRITX/VEIEX] 21-63-126-252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; st` | +9.70 | +9.62 |
| long_screen | CA | 2010-01-01 | `rot[VFINX/PRITX/VEIEX] 21-63-126-252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; st` | +16.18 | -7.37 |
| long_screen | CA | 2014-01-01 | `rot[VFINX/PRITX/VEIEX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; std/M` | +8.16 | -3.56 |
| long_screen | CA | 2018-01-01 | `rot[VFINX/PRITX/VEIEX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; std/M` | +0.47 | -9.47 |
| long_screen | NONE | 1998-01-01 | `ratio[VFINX v VEIEX] sma400 band0.03 tilt1.0 ; std/M` | 0.00 | +1.94 |
| long_screen | NONE | 2002-01-01 | `rot[VFINX/PRITX] 21-63-126-252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; std/M` | +4.05 | +9.47 |
| long_screen | NONE | 2006-01-01 | `rot[VFINX/PRITX/VEIEX] 21-63-126-252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; st` | +14.00 | +14.28 |
| long_screen | NONE | 2010-01-01 | `rot[VFINX/PRITX/VEIEX] 21-63-126-252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; st` | +20.90 | -8.68 |
| long_screen | NONE | 2014-01-01 | `rot[VFINX/PRITX/VEIEX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX hyst0.03 ; std/M` | +10.62 | -3.32 |
| long_screen | NONE | 2018-01-01 | `rot[VFINX/VWIGX] 252s0 top1 abs=tbill:VFINX safe=VBMFX/VFIIX ; std/M` | +1.64 | -6.44 |

Selecting from this family with only past information never beat SPY after 2010 on the ETF-era
grid (CA out-of-sample excess -2.26, -7.96, 0.00; NONE -9.39, -13.88, 0.00).
On the long-history grid it won at the decision dates whose next five years fall in 1998-2011 and
lost at 2010, 2014 and 2018 in both regimes. PBO is above 0.5 in every grid: the in-sample best is
more likely than not below the median out of sample.

## Concerns and caveats

* **Two-trade "significance".** N1's boot_p (0.04) treats 26 years of months as
  the sample, but the strategy made two decisions. A 12-month-block bootstrap cannot see that the
  whole excess comes from one 2001-2011 holding; its 10-year beat rate (0.46), walk-forward and
  hindsight results are the honest summary.
* **Mutual-fund proxies.** The ETF-era winners trade VGTSX/VEIEX (Vanguard index mutual funds, not
  on the site) because they reach back before EFA (2001) and EEM (2003). Their historical purchase
  and redemption fees, if any applied, are not modelled (the engine charges 5 + 5 bps), and fund
  capital-gain distributions are taxed as deferred gains like every total-return series. Both
  flatter switching strategies in CA. The ETF-only versions lose anyway.
* **Early country ETFs.** 1996-2005 iShares country funds had wide spreads and high fees; 5 bps
  slippage is optimistic for them, so country rotation is, if anything, overstated, and it still loses.
* **Foreign tax credit** on international dividends is not modelled. For a taxable holder it is a
  small benefit (order of a few tenths of a percent a year on the international holding; an estimate,
  not computed). It could lift near-zero results such as SPY 80 / VEIEX 20 (-0.08 pp/yr) to
  about zero; it cannot rescue the beat rates or the post-2010 record.
* **Bond fallback.** GEM-type rules hold the aggregate-bond fund about a quarter of the time; the
  engine taxes bond interest as deferred gains, which flatters them in CA/FED (PROTOCOL 5.5).
* **Long-history proxies.** PRITX, VWIGX, VTRIX and FOSFX are active funds, not indexes. VEIEX starts
  in 1994, so the EM-based winners have no pre-2000 holdout at all (their long twins equal VFINX
  before 1996-97).
* **Search size.** 1459 distinct configs, with a dense neighbourhood around the winners
  (block N). The diagnostics above already account for it and are negative.

## Lab notes (suspected issues, not fixed: lab core is read-only)

* `metrics.monthly_matrix` ends with `.dropna()`, so PBO and the deflated Sharpe in
  `report.diagnostics` silently use only the months common to every config. One late-starting
  config (e.g. a VXUS menu, 2013+) shrinks the whole family's PBO sample to 2013-2026. This report
  passes only configs whose first start is the protocol's first start.
* `metrics.walk_forward(step_quarters=4)` steps over protocol *starts*, not quarters. On `screen`
  (yearly starts) that is every 4 years, so the 10y->5y walk-forward has only 3 decision dates
  (2012, 2016, 2020) and its `oos_beat` is very coarse.
* `WeightStrategy(band=...)` applies the band to opening new positions too: a name not yet held,
  with target weight below the band, is never bought. The stage-2 "band 0.5" variants of top-2/3
  rotations therefore never invested (all cash, median 0 trades). This matches the docstring, but it
  is an easy trap (no warning).
* Mutual-fund proxies (VGTSX, VEIEX, ...) are tradable in the lab but not on the site, so the
  ETF-era winners here cannot be reproduced on the website as configured (their ETF twins can, and lose).

## Not tested

* Valuation-based country/region selection (CAPE, P/B, dividend yield): no valuation data in the
  lab; long-term price reversal was the only proxy (blocks E, K).
* Currency-hedged international (HEFA/DBEF, 2011-2014+), international small-cap and value (SCZ, EFV,
  DLS, 2005-2008+): histories too short for the 10- and 15-year tests.
* Foreign tax credit and qualified-dividend treatment of foreign funds (see caveats).
* A slow US/international switch inside the incumbent's sector-momentum menu (e.g. replacing its
  EFA/EEM slots), and US/international switching on a total-market (VTI) home asset instead of SPY.

## Conclusion

Going global did not beat SPY after tax with good confidence. Three things were tested:
static diversification, rotation between the US and the rest of the world (or among regions or
countries), and contrarian country selection. Static international exposure lost over 2000-2026.
Country and regional rotation lost even before tax. US-vs-international switching produced
after-tax scores above +1 pp/yr only when it could hold emerging markets through the 2000s. That
result is one regime call. Without VEIEX it shrinks below +1 pp/yr (N1b: +0.82 on the full
protocol, 10-year beat 0.42); on the ETFs that existed at the time it is negative, and on
random menus it is negative on average; the best version never beat SPY in a 5-year window starting in 2010 or later, and the other
US/international switchers did so in at most 2 of 47 such windows; and the 1986-1999 holdout
(where it can be tested with PRITX) went against it. The pre-2010 and 2010-2026 evidence point in opposite
directions, and the longer history agrees with 2010-2026.

Representative failures, CA full-protocol scores: classic GEM on ETFs -3.04; country
rotation -3.36; cheap-country reversal -2.53; global equal
weight -2.36; incumbent menu plus countries +0.34 (vs +0.66 for
the incumbent).

