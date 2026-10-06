# Family `risk_alloc` — risk-based allocation and volatility management

Module: `research/lab/families/risk_alloc.py` (signals `risk_alloc.voltarget`, `.riskpar`, `.cppi`,
`.ddtier`, `.volmom`, `.overlay`; custom kind `risk_alloc.taxvt`). Scripts, logs and job sets:
`research/lab/scratch/risk_alloc/` — `grids.py` (the first researcher's grids) and `resume_sets.py`
(the resumed work) define every config; `run_queue.py` / `run_extra.py` ran them;
`final_table.py`, `write_md.py`, `render_md.py` build this file and the CSV. Every result is in
`research/lab/results/risk_alloc_table.csv` (one row per config x regime x protocol, with
`protocol`, `set`, `group`, matched-volatility columns and `uses_leverage` / `uses_synthetic`).

All numbers are the lab's (= the website engine's): after-tax CAGR, fully liquidated at each
window's end, minus SPY bought and held over the same window in the same tax regime (VFINX in the
1986+ protocols), 5 bps commission + 5 bps slippage per side. pp = percentage points per year.
*score* = mean of the average 5-, 10- and 15-year window excess (the pre-registered ranking).
*matched-vol* = the strategy's annual return over T-bills rescaled to SPY's volatility, minus SPY's
(from the first start's monthly after-tax values) — what it would have earned at SPY's risk.
Configs that hold SSO/DDM can only start once SSO exists (first window 2006-07 on the full
protocol, 2007-01 on the screen protocol), so their numbers cover 2006-2026, not 2000-2026.

## Verdict

**No risk-based allocation or volatility-management rule beats buying and holding SPY after
California taxes with good confidence. Without leverage nothing in this family beats SPY at all —
in CA, FED or NONE. With leverage (2x S&P 500 funds) the excess return is the leverage, not risk
management, and in a taxable account it does not survive the longer-history tests.**

* **Unlevered (258 configs; 246 screened in CA): nothing beats SPY.** Vol targeting of SPY, risk parity
  (equal / inverse-vol / ERC / min-variance / max-diversification / HRP / risk budgets) over
  stock-bond-gold-commodity-REIT menus, equity-only min-variance, CPPI, drawdown tiers,
  vol-scaled momentum and a vol-target overlay on the incumbent: the best CA score is +0.14 pp/yr
  (a tax-aware 25%-target vol target, boot_p 0.77) and no config clears even items 1-3 of the bar
  in any regime. Vol targeting does what it promises before tax — lower drawdowns (median max
  drawdown -40% vs SPY's -55%) and a higher Sharpe in NONE (86% of the 146 configs, median +0.03)
  — but it costs return (median score -1.06 pp/yr in CA, -0.76 in NONE), and in CA most of the
  Sharpe gain is gone (median -0.005) because de-risking sales realize gains. Risk parity with bonds and
  gold has the best risk-adjusted numbers in NONE (SPY/TLT/GLD min-variance: Sharpe 0.86 vs 0.66)
  but returns 1-9 pp/yr less than SPY; turning it into return needs leverage, and levered risk
  parity (SSO/UBT/UGL) lost 1.1-3.6 pp/yr over 2010-2026.
* **Levered vol targeting of SPY (SPY + SSO, exposure = 25% / 21-day realized vol, capped at 2x)
  beats SPY over 2006-2026 — because it is ~1.7-1.8x leveraged on average.**
  * NONE (diagnostic regime): full protocol score +4.64 pp/yr, 10-year beat 100%, boot_p 0.010,
    max drawdown -55% (SPY -55%), Sharpe 0.71 vs 0.67. With a synthetic 2x S&P fund it still beats
    VFINX over 1986-2026 (score +2.75, 10y beat 81%, 15y beat 92%, boot_p 0.057; pre-2000 holdout
    +5.3 pp), but its 40-year Sharpe is *below* buy-and-hold (0.55 vs 0.57) and its drawdown is
    -65%: the excess is the equity premium earned on ~1.7x exposure, not timing skill. From 2000
    (synthetic) its boot_p is 0.15.
  * CA with normal execution: the de-/re-leveraging trades are taxed away (full score +0.83 pp,
    boot_p 0.40; 1986-2026 synthetic -0.13 pp, 2000-2026 synthetic +0.73 pp, boot_p 0.57).
  * CA with tax-aware execution (lots chosen across SPY/IWB/VTI + SSO/DDM, net realized gains
    capped at 1% of the portfolio per year): full score +3.40 pp/yr, full-period excess +4.85 pp,
    10-year beat 98%, boot_p 0.011 — it formally clears items 1-3 of the bar on the 2006-2026
    sample. It is not a pass: (i) the gain budget freezes the exposure (~1.9x every year since
    2010 for the 2006 start): it is a path-dependent constant-leverage portfolio, and a never-
    rebalanced 50% SPY + 50% SSO scores the same (+3.39 pp, beat SPY from every one of 69 starts
    to 2026); (ii) at SPY's volatility it earns +0.12 pp/yr; (iii) the family's walk-forward
    selection is negative out of sample in CA (10y->5y: -0.53 pp with the lab's default steps,
    -1.42 pp and 25% of decisions with yearly steps); (iv) with
    synthetic leverage the same rule fails the bar from 2000 (boot_p 0.35, Sharpe 0.36 vs 0.42)
    and over 1986-2026 (quarterly long protocol: 10y beat 74%, 15y beat 72%, boot_p 0.26, max
    drawdown -79%).
* **For a taxable account:** the only way this family beats SPY is to hold roughly 1.5-2x
  S&P 500 exposure through leveraged ETFs, with 1.6-1.9x SPY's volatility and drawdowns of -57% to
  -85%. That is a bet on the equity premium (and on 2009-2026-like markets), not a better
  portfolio, and its confidence evaporates on longer history. Nothing here should replace SPY on
  the strength of these backtests.

## What was tested (all of it)

| group | full / CA | full / FED | full / NONE | long_screen / CA | long_screen / NONE | screen / CA | screen / NONE | long / CA | long / NONE |
|---|---|---|---|---|---|---|---|---|---|
| BH | 1 | 1 | 1 | 1 | 1 | 4 | 4 | 0 | 0 |
| CPPI | 0 | 0 | 0 | 1 | 1 | 4 | 4 | 0 | 0 |
| DD | 1 | 1 | 1 | 1 | 1 | 5 | 5 | 0 | 0 |
| OV | 1 | 1 | 1 | 0 | 0 | 2 | 2 | 0 | 0 |
| RP | 2 | 2 | 2 | 4 | 4 | 27 | 27 | 0 | 0 |
| RP-eq | 0 | 0 | 0 | 0 | 0 | 8 | 8 | 0 | 0 |
| RP-lev | 0 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 0 |
| TVT-1x | 1 | 1 | 1 | 0 | 0 | 48 | 15 | 0 | 0 |
| TVT-const | 3 | 2 | 2 | 2 | 0 | 12 | 4 | 0 | 0 |
| TVT-lev | 8 | 6 | 6 | 5 | 0 | 72 | 18 | 1 | 0 |
| VM | 0 | 0 | 0 | 0 | 0 | 5 | 5 | 0 | 0 |
| VT-1x | 2 | 2 | 2 | 6 | 6 | 146 | 146 | 0 | 0 |
| VT-const | 2 | 1 | 2 | 2 | 2 | 10 | 10 | 0 | 0 |
| VT-lev | 4 | 2 | 4 | 2 | 2 | 71 | 73 | 1 | 1 |
| VT-taxexec | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0 | 0 |
| hindsight: BH | 0 | 0 | 0 | 0 | 0 | 6 | 26 | 0 | 0 |
| hindsight: RP | 0 | 0 | 0 | 0 | 0 | 29 | 29 | 0 | 0 |
| hindsight: RP-eq | 0 | 0 | 0 | 0 | 0 | 17 | 17 | 0 | 0 |
| hindsight: TVT-lev | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0 | 0 |
| hindsight: VT-1x | 0 | 0 | 0 | 0 | 0 | 0 | 20 | 0 | 0 |
| hindsight: VT-lev | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 |
| reference: combo | 1 | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 |

Unique configs: 559 — 454 family configs (the search; they set the multiple-testing count), 104 hindsight-check configs, 1 reference (the site's incumbent preset, already cached). (config, regime, protocol) results: 1022.

Group key: `VT-1x` vol targeting of SPY (exposure = target / forecast vol, capped at 100%, rest in
SHY); `TVT-1x` the same with the tax-aware execution kind; `VT-lev` / `TVT-lev` the same capped at
150-300% via SSO (2x) or UPRO (3x) (SPY + SSO, fully invested); `VT-const` / `TVT-const` / `BH`
constant-leverage controls (same execution, fixed exposure; `BH` = SPY + SSO bought once and never
rebalanced); `VT-taxexec` the plain signal under the lab's generic tax execution; `RP` risk parity
on multi-asset menus (equal / inverse-vol / ERC / min-variance / max-diversification / HRP, risk
budgets, a fixed 60/40 with a portfolio vol target); `RP-eq` the same on equity-only menus (the 9
sector SPDRs; the incumbent's 22 ETFs); `RP-lev` levered risk parity (SSO/UBT/UGL); `CPPI`
constant-proportion portfolio insurance; `DD` exposure set by SPY's drawdown tiers; `VM`
vol-scaled time-series / cross-sectional momentum; `OV` vol-target overlay on the incumbent's
momentum rotation.

Vol forecasts tried: rolling std over 10/21/42/63/126 days, EWMA (half-life 10/20/40), max(21d,
126d), downside semi-deviation, VIX (lagged one day), VIX/realized blend; power 1 and 2
(Moreira-Muir variance scaling); 200-day trend filter; VIX/VIX3M term-structure filter; exposure
floors; cash leg in SHY, IEF, TLT or real cash; monthly / weekly / quarterly rebalancing and
daily-checked no-trade bands (5-30%); tax-aware execution with gain budgets 0 / 0.5 / 1 / 2% of
the portfolio per year, no short-term gains, tax-loss harvesting across different-index funds.
Multi-asset menus: SPY+TLT, SPY+IEF, SPY+TLT+GLD, an all-weather 5 (SPY/TLT/IEF/GLD/DBC), a global
8 (SPY/EFA/EEM/TLT/IEF/GLD/DBC/VNQ), SPY+VUSTX (from 2000) and 1986+ mutual-fund menus.

Coverage note: the first researcher's planned 753-config screening grid was cut short by the
battery throttle (the machine went to sleep). 213 of its configs ran (all 144 unlevered VT, 69
levered VT); the other groups (RP, CPPI, DD, VM, OV, VT filters) ran as a 56-config representative
subset, plus the targeted resume sets below. Everything that ran is in the CSV and in the counts.

Screening summary (screen protocol: yearly starts 2000-2023; SSO-based configs from 2007):

| group | regime | n | best score | median score | share score>0 | share full>0 | median Sharpe - SPY | median matched-vol | best config (score) |
|---|---|---|---|---|---|---|---|---|---|
| BH | CA | 4 | +3.48 | +1.90 | 75% | 75% | -0.033 | -0.46 | BH SPY:0.5,SSO:0.5 |
| BH | NONE | 4 | +3.95 | +2.17 | 75% | 75% | -0.040 | -0.62 | BH SPY:0.5,SSO:0.5 |
| CPPI | CA | 4 | -3.03 | -3.74 | 0% | 0% | -0.053 | -0.74 | CPPI m2 f0.7 rNone c1.0 /M |
| CPPI | NONE | 4 | -3.46 | -4.16 | 0% | 0% | +0.014 | +0.21 | CPPI m2 f0.7 rNone c1.0 /M |
| DD | CA | 5 | -0.05 | -0.44 | 0% | 0% | +0.041 | +0.58 | DD 0.2:1.0,1.0:0.5 hw252 /M |
| DD | NONE | 5 | +0.55 | +0.09 | 60% | 40% | +0.058 | +0.88 | DD 0.1:1.0,0.2:1.5,1.0:2.0 hw252 SSO /M |
| OV | CA | 2 | -0.08 | -1.17 | 0% | 50% | +0.024 | +0.33 | OV momentum t0.15 lb63 c1.0 /tax0.01 Q |
| OV | NONE | 2 | -1.33 | -1.33 | 0% | 0% | +0.005 | +0.07 | OV momentum t0.15 lb63 c1.0 /Q |
| RP | CA | 27 | -1.42 | -2.51 | 0% | 0% | -0.012 | -0.16 | RP MF2 invvol lb63 /M |
| RP | NONE | 27 | -1.05 | -2.43 | 0% | 0% | +0.080 | +1.17 | RP MF2 minvar lb63 /M |
| RP-eq | CA | 8 | -0.21 | -2.06 | 0% | 0% | -0.115 | -1.61 | RP SECT9 invvol lb126 /M |
| RP-eq | NONE | 8 | +0.25 | -0.63 | 25% | 50% | +0.006 | +0.10 | RP SECT9 invvol lb126 /M |
| RP-lev | CA | 3 | -2.96 | -3.14 | 0% | 0% | -0.239 | -2.98 | RP SB erc lb63 t0.15 c3.0 LSSOUBT /M |
| RP-lev | NONE | 3 | -1.09 | -1.63 | 0% | 0% | -0.141 | -1.99 | RP SB equal lb63 t0.15 c3.0 LSSOUBT fixedSPY0.6/TLT0.4 /M |
| TVT-1x | CA | 48 | +0.14 | -0.31 | 17% | 6% | +0.005 | +0.07 | TVT s21 t0.25 c1.0 v3 b0.1 gb0.0 |
| TVT-1x | NONE | 15 | +0.18 | -0.47 | 13% | 0% | +0.038 | +0.58 | TVT s21 t0.2 c1.0 v3 b0.1 |
| TVT-const | CA | 12 | +6.00 | +2.21 | 100% | 100% | -0.044 | -0.62 | TVT const2.0 v3 LSSO/DDM b0.1 gb0.0 |
| TVT-const | NONE | 4 | +3.93 | +2.06 | 100% | 100% | -0.046 | -0.70 | TVT const1.5 v3 LSSO/DDM b0.1 |
| TVT-lev | CA | 72 | +4.97 | +0.41 | 64% | 75% | +0.010 | +0.15 | TVT s21 t0.3 c2.0 v3 LSSO/DDM b0.1 gb0.0 |
| TVT-lev | NONE | 18 | +4.00 | +0.29 | 61% | 61% | -0.012 | -0.18 | TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 |
| VM | CA | 5 | -0.36 | -3.49 | 0% | 0% | -0.214 | -2.98 | VM xs INC22 lb252 top5 /tax0.01 Q |
| VM | NONE | 5 | -1.04 | -3.13 | 0% | 0% | -0.102 | -1.54 | VM xs INC22 lb252 top5 /tax0.01 Q |
| VT-1x | CA | 146 | +0.03 | -1.06 | 1% | 0% | -0.005 | -0.07 | VT SPY s21 t0.25 c1.0 /M |
| VT-1x | NONE | 146 | +0.50 | -0.76 | 11% | 1% | +0.034 | +0.51 | VT SPY s10 t0.25 c1.0 b0.1d /M |
| VT-const | CA | 10 | +3.41 | +1.87 | 100% | 100% | -0.033 | -0.47 | VT SPY const1.5 c1.5 SSO b0.1d /M |
| VT-const | NONE | 10 | +4.01 | +2.38 | 100% | 100% | -0.040 | -0.62 | VT SPY const1.5 c1.5 SSO b0.1d /M |
| VT-lev | CA | 71 | +1.04 | -2.58 | 14% | 13% | -0.116 | -1.64 | VT SPY s63 t0.25 c2.0 SSO b0.1d /M |
| VT-lev | NONE | 73 | +4.65 | +0.13 | 51% | 53% | +0.008 | +0.13 | VT SPY s21 t0.25 c2.0 SSO /M |
| VT-taxexec | CA | 4 | +0.09 | -0.65 | 25% | 25% | +0.002 | +0.03 | VT SPY e20 t0.18 c2.0 SSO b0.1d /tax0.01 M |

## 1. Without leverage nothing beats SPY

**Vol targeting of SPY (146 screened configs, 2000-2026; 48 more with tax-aware execution).**
Scaling SPY exposure by 10-25% / forecast vol, with the rest in SHY, behaves exactly as the
literature says *before tax*: drawdowns shrink (median max drawdown -40% vs SPY's -55%; about
-23% to -29% at a 10-12% target) and in NONE the Sharpe ratio rises for 86% of configs (median +0.03;
return at SPY's volatility +0.5 pp/yr). But exposure averages well below 100% while the equity
premium is large, so return falls: median score -0.76 pp/yr in NONE and -1.06 in CA, best NONE
+0.50 (10-day vol, 25% target, boot_p 0.46), best CA +0.03. In CA most of the Sharpe gain is
gone (median -0.005 across the 146; the low-turnover versions keep +0.02-0.03): de-risking sells
appreciated SPY lots and re-risking rebuys them, so gains are realized early and often short-term. The tax-aware execution kind (lots chosen across
SPY/IWB/VTI, gain budget 0-1%/yr, harvesting) gets it back to about zero (best CA score +0.14,
boot_p 0.77) by suppressing the de-risking trades — i.e. by turning it back into buy-and-hold.
On the full protocol: 25%-target / 21-day VT CA score +0.01, full -0.47 pp, boot_p 0.73; the
tax-aware version +0.05 / +0.12 pp, boot_p 0.47; the textbook 15% EWMA target -1.11 pp (NONE
-0.81). Moreira-Muir variance scaling (power 2) and a 200-day trend filter raised the NONE Sharpe
a little but lowered the score further (CA -1.63 / -1.68 vs -1.04 / -0.74 for the same configs
without them; NONE -1.29 / -1.17 vs -0.72 / -0.51); a VIX/VIX3M term-structure cap on the levered
version cut its NONE score from +0.43 to -0.15.

**Risk parity, minimum variance, maximum diversification, HRP, risk budgets (38 configs).** Every
multi-asset version loses to SPY in every regime: SPY+long Treasuries (2000-) -1.4 to -1.7 pp/yr
in CA, -1.0 to -1.5 in NONE; SPY+TLT -2.3 to -2.5 (CA); with gold -3.3 to -3.9 (CA); the global
8-asset menu -5.6 to -7.7 (CA) and -6.4 to -8.7 (NONE). The risk-adjusted side is where risk
parity shines — in NONE SPY/TLT/GLD min-variance has a Sharpe of 0.86 vs SPY's 0.66 and would
have earned +3.1 pp/yr at SPY's volatility; SPY+VUSTX ERC 0.67 vs 0.47 (+2.9 pp) — but that
needs leverage, which is where it broke: levered risk parity (SPY/TLT[/GLD] with SSO/UBT/UGL,
10-15% portfolio vol target, from 2010) lost 1.1-2.1 pp/yr in NONE and 3.0-3.6 in CA (2022's
stock-bond crash; Sharpe 0.60-0.80 vs SPY's 0.85-0.90 over 2010-2026). The tailwind behind the
good Sharpe numbers is also a hindsight issue: 2000-2020 was a secular bond bull market and a
gold bull market. Equity-only risk parity (inverse-vol / ERC / min-var / max-div / HRP over the
9 sectors or the incumbent's 22 ETFs) is -0.2 to -2.7 pp in CA (best: sector inverse-vol, -0.21,
boot_p 0.63; +0.25 in NONE, boot_p 0.34). A vol-targeted fixed 60/40 lost 2.5 pp in both regimes.

**CPPI, drawdown tiers, vol-scaled momentum, overlay (14 configs).** CPPI -3.0 to -5.0 pp/yr in
CA (insurance is paid for in every recovery); drawdown-tier de-risking -0.05 to -0.8 in CA
(unlevered best +0.14 in NONE, boot_p 0.37; it does cut the drawdown to -34% to -43%); vol-scaled momentum
-3.5 to -8.6 (CA); the vol-target overlay on the incumbent rotation -2.25 (CA) / -1.33 (NONE),
far below the incumbent itself (+0.66 CA). The tax-managed versions of the last two are in
section 5.

## 2. Levered vol targeting: the excess is the leverage

The levered vol target holds SPY + SSO (2x) so that exposure = 25% / 21-day realized vol, capped
at 2x (monthly rebalance), or runs the same signal through the tax-aware kind `risk_alloc.taxvt`
(daily check with a 10% no-trade band; 1x exposure spread over SPY / IWB / VTI — three different
indexes — and 2x over SSO / DDM; de-risking sells the lots with the least tax per dollar; net
realized gains capped at 0-2% of the portfolio per year; no re-buy within 31 days of a loss sale).
On the full protocol (69 quarterly starts, 2006-07 to 2023-07, windows to 2026-07):

* **NONE.** Plain VT 25% / 2x: score +4.64 pp/yr, full-period +4.33, every 10-year window ahead
  (worst +2.92), boot_p 0.010, max drawdown -55% (SPY -55%), Sharpe 0.71 vs 0.67, matched-vol
  +0.55 pp. Capped at 1.5x: +3.18, boot_p 0.012, Sharpe 0.72, matched-vol +0.79. These are the
  family's best numbers, and they come from ~1.4-1.7x average exposure (volatility 19-22% vs SPY's
  15%), not from avoiding risk.
* **CA, plain execution.** +0.83 / +0.38 pp, boot_p 0.40, Sharpe 0.54 vs 0.62: re-leveraging
  every month (turnover 2.5x a year) realizes gains, and the tax takes almost all of the edge.
* **CA, tax-aware execution.** 1%/yr budget: +3.40 / +4.85 pp, 10-year beat 98%, 15-year beat
  100%, boot_p 0.011, max drawdown -61%, Sharpe 0.63 vs 0.62, matched-vol +0.12 pp. Zero budget:
  +3.17 / +5.54, boot_p 0.002. Full-protocol neighbours: EWMA vol +2.09 (boot_p 0.022),
  max(21d, 126d) +1.46 (0.021), 20% target +1.13 (0.125), EWMA 20% capped at 1.5x +0.88 (0.027).
  All 18 screened vol-targeted neighbours (targets 22-30%, vol windows 10-63 days, bands 5-20%,
  budgets 0-2%, caps 1.5-2x, a single SPY/SSO pair, never realizing short-term gains) score +2.2
  to +5.0 with boot_p 0.002-0.039. A smooth, positive neighbourhood — of a leverage effect.
* **Constant-leverage controls do as well on the pre-registered score.** Same execution, fixed
  exposure: 1.5x +3.59 (tax-aware) / +3.36 (plain, daily band), SPY + SSO 50/50 bought once and
  never rebalanced +3.39 (ahead of SPY from all 69 starts to 2026), 1.8x +5.08, 2x (screen) +6.00.
  Their boot_p is 0.10-0.21 against 0.002-0.03 for most of the vol-targeted versions because the
  bootstrap uses the first start's path, and the 2006-07 start is exactly the one for which vol targeting dodged
  2008. Their drawdowns are -71% to -85%.

So in a taxable account the family's "winners" are leverage. Vol targeting changes when the
leverage is held, and only in one episode (2008, for investors who started before it) did that
matter much; at SPY's volatility the tax-aware lead earns +0.12 pp/yr (zero budget +0.57).

### Full protocol (quarterly starts; SSO-based configs from 2006-07)

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +3.40 | +4.85 | +3.92 | 98% | -2.32 | 100% | 100% | 0.011 | -61% (-55%) | 0.63 (0.62) | +0.12 | 992 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | FED | +3.64 | +6.32 | +4.19 | 98% | -2.82 | 100% | 100% | 0.001 | -59% (-55%) | 0.69 (0.65) | +0.57 | 1069 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | NONE | +4.01 | +3.40 | +4.14 | 100% | +2.67 | 100% | 100% | 0.024 | -54% (-55%) | 0.67 (0.67) | +0.02 | 1167 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +3.17 | +5.54 | +3.71 | 98% | -2.67 | 100% | 100% | 0.002 | -57% (-55%) | 0.67 (0.62) | +0.57 | 120 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | FED | +3.37 | +5.67 | +3.96 | 98% | -2.85 | 100% | 100% | 0.002 | -57% (-55%) | 0.68 (0.65) | +0.42 | 120 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | NONE | +4.01 | +3.40 | +4.14 | 100% | +2.67 | 100% | 100% | 0.024 | -54% (-55%) | 0.67 (0.67) | +0.02 | 1167 |
| VT SPY s21 t0.25 c2.0 SSO /M | CA | +0.83 | +0.38 | +0.91 | 93% | -0.39 | 90% | 100% | 0.404 | -59% (-55%) | 0.54 (0.62) | -1.10 | 362 |
| VT SPY s21 t0.25 c2.0 SSO /M | FED | +1.78 | +1.51 | +1.87 | 100% | +0.39 | 100% | 100% | 0.193 | -58% (-55%) | 0.62 (0.65) | -0.47 | 362 |
| VT SPY s21 t0.25 c2.0 SSO /M | NONE | +4.64 | +4.33 | +4.59 | 100% | +2.92 | 100% | 100% | 0.010 | -55% (-55%) | 0.71 (0.67) | +0.55 | 355 |
| TVT const1.5 v3 LSSO/DDM b0.1 gb0.0 | CA | +3.59 | +2.54 | +3.84 | 100% | +0.70 | 100% | 100% | 0.109 | -72% (-55%) | 0.55 (0.62) | -0.95 | 8 |
| TVT const1.5 v3 LSSO/DDM b0.1 gb0.0 | FED | +3.83 | +2.61 | +4.07 | 100% | +0.77 | 100% | 100% | 0.109 | -72% (-55%) | 0.58 (0.65) | -1.07 | 8 |
| TVT const1.5 v3 LSSO/DDM b0.1 gb0.0 | NONE | +3.80 | +2.73 | +4.00 | 100% | +0.96 | 100% | 100% | 0.104 | -72% (-55%) | 0.61 (0.67) | -0.87 | 16 |
| VT SPY const1.5 c1.5 SSO b0.1d /M | CA | +3.36 | +2.57 | +3.57 | 100% | +0.85 | 100% | 100% | 0.103 | -73% (-55%) | 0.58 (0.62) | -0.61 | 30 |
| VT SPY const1.5 c1.5 SSO b0.1d /M | FED | +3.63 | +2.84 | +3.83 | 100% | +0.94 | 100% | 100% | 0.093 | -73% (-55%) | 0.60 (0.65) | -0.69 | 20 |
| VT SPY const1.5 c1.5 SSO b0.1d /M | NONE | +3.89 | +3.02 | +4.09 | 100% | +1.03 | 100% | 100% | 0.089 | -73% (-55%) | 0.62 (0.67) | -0.76 | 16 |
| BH SPY:0.5,SSO:0.5 | CA | +3.39 | +2.35 | +3.63 | 100% | +0.09 | 100% | 100% | 0.111 | -71% (-55%) | 0.56 (0.62) | -0.85 | 2 |
| BH SPY:0.5,SSO:0.5 | FED | +3.62 | +2.41 | +3.84 | 100% | +0.10 | 100% | 100% | 0.105 | -71% (-55%) | 0.58 (0.65) | -0.96 | 2 |
| BH SPY:0.5,SSO:0.5 | NONE | +3.84 | +2.47 | +4.05 | 100% | +0.11 | 100% | 100% | 0.113 | -71% (-55%) | 0.60 (0.67) | -1.05 | 2 |
| TVT e20 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +2.09 | +3.25 | +2.88 | 93% | -0.75 | 86% | 100% | 0.022 | -55% (-55%) | 0.62 (0.62) | -0.10 | 72 |
| TVT e20 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | FED | +2.27 | +3.34 | +3.11 | 93% | -0.80 | 86% | 100% | 0.029 | -55% (-55%) | 0.63 (0.65) | -0.24 | 72 |
| TVT e20 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | NONE | +3.29 | +2.94 | +3.45 | 100% | +1.21 | 100% | 100% | 0.049 | -51% (-55%) | 0.67 (0.67) | -0.06 | 641 |
| TVT mx21/126 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +1.46 | +2.30 | +2.30 | 88% | -2.86 | 86% | 100% | 0.021 | -51% (-55%) | 0.65 (0.62) | +0.37 | 72 |
| TVT mx21/126 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | FED | +1.55 | +2.36 | +2.45 | 88% | -3.06 | 86% | 100% | 0.021 | -51% (-55%) | 0.67 (0.65) | +0.25 | 72 |
| TVT mx21/126 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | NONE | +2.31 | +1.96 | +2.56 | 100% | +0.87 | 100% | 100% | 0.134 | -45% (-55%) | 0.65 (0.67) | -0.34 | 813 |
| TVT s21 t0.2 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +1.13 | +1.40 | +1.29 | 83% | -4.01 | 100% | 100% | 0.125 | -54% (-55%) | 0.61 (0.62) | -0.23 | 1616 |
| TVT s21 t0.2 c2.0 v3 LSSO/DDM b0.1 gb0.01 | FED | +1.31 | +1.31 | +1.46 | 83% | -4.30 | 100% | 100% | 0.133 | -54% (-55%) | 0.63 (0.65) | -0.30 | 1612 |
| TVT s21 t0.2 c2.0 v3 LSSO/DDM b0.1 gb0.01 | NONE | +1.98 | +1.94 | +2.04 | 100% | +0.92 | 100% | 100% | 0.087 | -46% (-55%) | 0.67 (0.67) | +0.07 | 1480 |
| TVT e20 t0.2 c1.5 v3 LSSO/DDM b0.1 gb0.01 | CA | +0.88 | +2.40 | +1.31 | 78% | -1.82 | 90% | 100% | 0.027 | -47% (-55%) | 0.66 (0.62) | +0.55 | 912 |
| TVT e20 t0.2 c1.5 v3 LSSO/DDM b0.1 gb0.01 | FED | +0.86 | +1.88 | +1.30 | 76% | -2.73 | 90% | 100% | 0.065 | -47% (-55%) | 0.66 (0.65) | +0.13 | 985 |
| TVT e20 t0.2 c1.5 v3 LSSO/DDM b0.1 gb0.01 | NONE | +0.82 | +1.12 | +0.90 | 80% | -1.04 | 81% | 100% | 0.221 | -40% (-55%) | 0.70 (0.67) | +0.49 | 415 |
| VT SPY s21 t0.25 c1.5 SSO /M | CA | +0.92 | +0.69 | +0.91 | 61% | -0.62 | 90% | 100% | 0.329 | -54% (-55%) | 0.62 (0.62) | -0.03 | 504 |
| VT SPY s21 t0.25 c1.5 SSO /M | FED | +1.62 | +1.58 | +1.62 | 98% | -0.03 | 100% | 100% | 0.120 | -53% (-55%) | 0.68 (0.65) | +0.51 | 504 |
| VT SPY s21 t0.25 c1.5 SSO /M | NONE | +3.18 | +3.01 | +3.17 | 100% | +1.41 | 100% | 100% | 0.012 | -52% (-55%) | 0.72 (0.67) | +0.79 | 506 |
| VT SPY s21 t0.25 c1.0 /M | CA | +0.01 | -0.47 | +0.08 | 58% | -2.00 | 72% | 11% | 0.726 | -48% (-55%) | 0.44 (0.42) | +0.18 | 137 |
| VT SPY s21 t0.25 c1.0 /M | FED | +0.12 | -0.28 | +0.21 | 60% | -1.87 | 74% | 19% | 0.655 | -48% (-55%) | 0.47 (0.45) | +0.34 | 137 |
| VT SPY s21 t0.25 c1.0 /M | NONE | +0.31 | -0.05 | +0.40 | 61% | -1.54 | 77% | 100% | 0.555 | -48% (-55%) | 0.50 (0.47) | +0.39 | 123 |
| VT SPY e20 t0.15 c1.0 /M | CA | -1.11 | -1.35 | -1.10 | 43% | -4.41 | 17% | 4% | 0.834 | -38% (-55%) | 0.45 (0.42) | +0.42 | 342 |
| VT SPY e20 t0.15 c1.0 /M | FED | -1.03 | -1.04 | -1.00 | 48% | -4.34 | 21% | 7% | 0.786 | -38% (-55%) | 0.51 (0.45) | +0.81 | 341 |
| VT SPY e20 t0.15 c1.0 /M | NONE | -0.81 | -0.57 | -0.77 | 51% | -3.98 | 34% | 7% | 0.687 | -38% (-55%) | 0.54 (0.47) | +0.98 | 328 |
| TVT e20 t0.25 c1.0 v3 b0.1 gb0.0 | CA | +0.05 | +0.12 | +0.19 | 48% | -1.15 | 66% | 67% | 0.469 | -48% (-55%) | 0.46 (0.42) | +0.48 | 49 |
| TVT e20 t0.25 c1.0 v3 b0.1 gb0.0 | FED | +0.05 | +0.13 | +0.21 | 48% | -1.23 | 66% | 67% | 0.459 | -48% (-55%) | 0.48 (0.45) | +0.48 | 49 |
| TVT e20 t0.25 c1.0 v3 b0.1 gb0.0 | NONE | -0.21 | -0.36 | -0.12 | 55% | -2.05 | 47% | 7% | 0.711 | -46% (-55%) | 0.49 (0.47) | +0.20 | 80 |
| TVT const1.8 v3 LSSO/DDM b0.1 gb0.0 | CA | +5.08 | +3.69 | +5.45 | 100% | +0.59 | 100% | 100% | 0.134 | -80% (-55%) | 0.55 (0.62) | -1.07 | 4 |
| TVT const1.8 v3 LSSO/DDM b0.1 gb0.0 | FED | +5.41 | +3.78 | +5.77 | 100% | +0.66 | 100% | 100% | 0.126 | -80% (-55%) | 0.57 (0.65) | -1.22 | 4 |
| TVT const1.8 v3 LSSO/DDM b0.1 gb0.0 | NONE | +5.67 | +3.61 | +6.05 | 100% | +0.72 | 100% | 100% | 0.133 | -80% (-55%) | 0.58 (0.67) | -1.34 | 6 |
| RP MF2 erc lb63 /M | CA | -1.62 | -1.53 | -1.50 | 49% | -8.11 | 23% | 19% | 0.704 | -31% (-55%) | 0.54 (0.42) | +1.63 | 638 |
| RP MF2 erc lb63 /M | FED | -1.54 | -1.19 | -1.40 | 51% | -8.68 | 28% | 19% | 0.651 | -30% (-55%) | 0.62 (0.45) | +2.41 | 638 |
| RP MF2 erc lb63 /M | NONE | -1.33 | -0.71 | -1.17 | 52% | -9.09 | 36% | 22% | 0.600 | -29% (-55%) | 0.67 (0.47) | +2.93 | 638 |
| RP SBG minvar lb63 /M | CA | -3.03 | -3.27 | -3.21 | 28% | -7.92 | 4% | 0% | 0.888 | -25% (-55%) | 0.68 (0.63) | +0.71 | 762 |
| RP SBG minvar lb63 /M | FED | -2.92 | -2.80 | -3.12 | 28% | -8.16 | 8% | 0% | 0.844 | -24% (-55%) | 0.78 (0.65) | +1.85 | 762 |
| RP SBG minvar lb63 /M | NONE | -2.05 | -1.44 | -2.33 | 33% | -7.69 | 19% | 0% | 0.699 | -23% (-55%) | 0.88 (0.66) | +3.17 | 762 |
| DD 0.1:1.0,0.2:0.5,1.0:0.0 hw252 /M | CA | -0.53 | -0.60 | -0.51 | 52% | -3.74 | 43% | 15% | 0.639 | -35% (-55%) | 0.53 (0.42) | +1.40 | 139 |
| DD 0.1:1.0,0.2:0.5,1.0:0.0 hw252 /M | FED | -0.43 | -0.29 | -0.40 | 52% | -3.88 | 47% | 19% | 0.576 | -34% (-55%) | 0.57 (0.45) | +1.68 | 136 |
| DD 0.1:1.0,0.2:0.5,1.0:0.0 hw252 /M | NONE | -0.14 | +0.16 | -0.08 | 54% | -3.76 | 49% | 37% | 0.485 | -34% (-55%) | 0.58 (0.47) | +1.64 | 119 |

### Sub-periods (consecutive 5-year windows from the first start; after-tax excess, pp/yr)

| config | regime | 2006-2011 | 2011-2016 | 2016-2021 | 2021-2026 |
|---|---|---|---|---|---|
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +5.4 | +1.3 | +0.5 | +1.0 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | NONE | +4.1 | +1.1 | +10.4 | +0.5 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +4.0 | +0.7 | -4.7 | -0.1 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | NONE | +4.1 | +1.1 | +10.4 | +0.5 |
| VT SPY s21 t0.25 c2.0 SSO /M | CA | +1.5 | +1.3 | +0.8 | +1.6 |
| VT SPY s21 t0.25 c2.0 SSO /M | NONE | +3.7 | +3.5 | +5.9 | +4.4 |
| TVT const1.5 v3 LSSO/DDM b0.1 gb0.0 | CA | -1.4 | +3.7 | +5.7 | +2.1 |
| TVT const1.5 v3 LSSO/DDM b0.1 gb0.0 | NONE | -2.0 | +4.5 | +6.5 | +2.6 |
| VT SPY const1.5 c1.5 SSO b0.1d /M | CA | -1.5 | +3.7 | +5.4 | +2.1 |
| VT SPY const1.5 c1.5 SSO b0.1d /M | NONE | -2.1 | +4.5 | +6.6 | +2.6 |
| BH SPY:0.5,SSO:0.5 | CA | -2.3 | +3.7 | +5.7 | +2.1 |
| BH SPY:0.5,SSO:0.5 | NONE | -3.1 | +4.5 | +6.8 | +2.6 |

### Why tax-aware vol targeting stops being vol targeting

A vol target must sell when volatility rises and buy back when it falls. In a taxable account
selling appreciated lots costs tax; under a realized-gain budget the strategy may de-risk only by
selling lots that are under water, and may re-lever (swap 1x funds for 2x funds) only within the
budget. The exposure therefore freezes wherever it was when gains piled up. Average exposure
(1x funds + 2 x the 2x funds), one start each:

* tax-aware lead, CA, start 2006-07: average exposure **1.82x**; yearly means 2006: 1.97, 2007: 1.93, 2008: 1.12, 2009: 1.18, 2010: 1.77, 2011: 1.84, 2012: 1.84, 2013: 1.89, 2014: 1.92, 2015: 1.91, 2016: 1.91, 2017: 1.94, 2018: 1.93, 2019: 1.92, 2020: 1.90, 2021: 1.90, 2022: 1.89, 2023: 1.88, 2024: 1.91, 2025: 1.90, 2026: 1.92
* tax-aware lead, CA, start 2019-01: average exposure **1.36x**; yearly means 2019: 1.30, 2020: 1.10, 2021: 1.35, 2022: 1.36, 2023: 1.39, 2024: 1.45, 2025: 1.48, 2026: 1.52
* standard lead, start 2006-07: average exposure **1.66x**; yearly means 2006: 1.95, 2007: 1.69, 2008: 1.11, 2009: 1.13, 2010: 1.54, 2011: 1.50, 2012: 1.82, 2013: 1.92, 2014: 1.94, 2015: 1.77, 2016: 1.75, 2017: 2.00, 2018: 1.69, 2019: 1.77, 2020: 1.30, 2021: 1.87, 2022: 1.12, 2023: 1.83, 2024: 1.90, 2025: 1.69, 2026: 1.89
* tax-aware, 1986+ synthetic (VFINX), CA: average exposure **1.61x**; yearly means 1986: 1.90, 1987: 1.63, 1988: 1.21, 1989: 1.34, 1990: 1.36, 1991: 1.40, 1992: 1.44, 1993: 1.48, 1994: 1.49, 1995: 1.54, 1996: 1.60, 1997: 1.66, 1998: 1.68, 1999: 1.70, 2000: 1.70, 2001: 1.63, 2002: 1.58, 2003: 1.55, 2004: 1.60, 2005: 1.62, 2006: 1.63, 2007: 1.66, 2008: 1.58, 2009: 1.47, 2010: 1.52, 2011: 1.55, 2012: 1.56, 2013: 1.61, 2014: 1.66, 2015: 1.66, 2016: 1.65, 2017: 1.70, 2018: 1.73, 2019: 1.73, 2020: 1.74, 2021: 1.79, 2022: 1.77, 2023: 1.76, 2024: 1.80, 2025: 1.80, 2026: 1.83
* same, gain budget 0: average exposure **1.13x**; yearly means 1986: 1.69, 1987: 1.52, 1988: 1.05, 1989: 1.07, 1990: 1.07, 1991: 1.07, 1992: 1.07, 1993: 1.08, 1994: 1.08, 1995: 1.09, 1996: 1.10, 1997: 1.12, 1998: 1.13, 1999: 1.14, 2000: 1.14, 2001: 1.11, 2002: 1.09, 2003: 1.08, 2004: 1.09, 2005: 1.09, 2006: 1.10, 2007: 1.10, 2008: 1.08, 2009: 1.05, 2010: 1.06, 2011: 1.07, 2012: 1.07, 2013: 1.08, 2014: 1.09, 2015: 1.10, 2016: 1.10, 2017: 1.11, 2018: 1.12, 2019: 1.12, 2020: 1.12, 2021: 1.15, 2022: 1.14, 2023: 1.13, 2024: 1.15, 2025: 1.16, 2026: 1.17

Started mid-2006, the 1%-budget lead de-risked through 2008 (its 2006-07 lots were losses, so
selling them was free), re-levered in 2009-10 while lots were still under water, and has sat at
~1.9x ever since — through 2011, 2015-16, 2018, 2020 and 2022. Started in January 2019, just after
the Q4-2018 volatility spike, it is stuck near 1.35x. Over 1986-2026 with a single 1x fund the
zero-budget version de-risked in the 1987 crash and then stayed at about 1.1x for 38 years.
"Tax-aware vol targeting" is therefore a path-dependent constant-leverage portfolio whose leverage
is set by the volatility regime at the start, which is why its sub-period results jump around (the
zero-budget twin lost 4.7 pp/yr over 2016-2021 while the 1%-budget version gained 0.5).

### Neighbourhood of the CA lead and constant-leverage controls (screen, CA, 2007+)

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TVT s21 t0.22 c2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +2.23 | +2.92 | +2.74 | 100% | +0.26 | 100% | n/a | 0.039 | -53% (-55%) | 0.60 (0.60) | +0.07 | 197 |
| TVT s21 t0.22 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +2.90 | +2.18 | +3.63 | 100% | +1.77 | 100% | n/a | 0.025 | -50% (-55%) | 0.61 (0.60) | +0.24 | 1652 |
| TVT s21 t0.28 c2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +4.29 | +5.52 | +5.06 | 100% | +2.10 | 100% | n/a | 0.004 | -57% (-55%) | 0.64 (0.60) | +0.58 | 216 |
| TVT s21 t0.28 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +3.94 | +4.25 | +4.46 | 90% | -2.03 | 100% | n/a | 0.007 | -57% (-55%) | 0.61 (0.60) | +0.14 | 1662 |
| TVT s21 t0.3 c2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +4.97 | +5.00 | +5.84 | 100% | +3.07 | 100% | n/a | 0.031 | -62% (-55%) | 0.59 (0.60) | -0.06 | 210 |
| TVT s21 t0.3 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +4.76 | +4.67 | +5.80 | 100% | +4.02 | 100% | n/a | 0.031 | -61% (-55%) | 0.59 (0.60) | -0.05 | 756 |
| TVT s10 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +3.88 | +4.76 | +4.24 | 80% | -0.83 | 100% | n/a | 0.016 | -60% (-55%) | 0.62 (0.60) | +0.33 | 1463 |
| TVT s42 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +3.22 | +2.90 | +4.09 | 100% | +2.06 | 100% | n/a | 0.019 | -53% (-55%) | 0.60 (0.60) | -0.01 | 1574 |
| TVT s63 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +3.51 | +4.08 | +4.43 | 100% | +1.25 | 100% | n/a | 0.028 | -60% (-55%) | 0.59 (0.60) | -0.05 | 1181 |
| TVT e10 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 | CA | +2.68 | +4.12 | +3.42 | 90% | -1.39 | 100% | n/a | 0.035 | -60% (-55%) | 0.59 (0.60) | -0.01 | 1355 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.05 gb0.01 | CA | +3.66 | +6.16 | +4.25 | 100% | +1.17 | 100% | n/a | 0.003 | -59% (-55%) | 0.64 (0.60) | +0.63 | 1191 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.2 gb0.01 | CA | +3.76 | +4.22 | +4.45 | 90% | -2.28 | 100% | n/a | 0.029 | -58% (-55%) | 0.60 (0.60) | +0.09 | 696 |
| TVT s21 t0.25 c1.75 v3 LSSO/DDM b0.1 gb0.01 | CA | +3.34 | +4.84 | +3.76 | 90% | -2.13 | 100% | n/a | 0.002 | -52% (-55%) | 0.65 (0.60) | +0.73 | 633 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.02 | CA | +3.80 | +5.59 | +4.31 | 100% | +0.11 | 100% | n/a | 0.004 | -60% (-55%) | 0.63 (0.60) | +0.47 | 1056 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.005 | CA | +3.21 | +4.47 | +3.98 | 100% | +0.24 | 100% | n/a | 0.026 | -60% (-55%) | 0.60 (0.60) | +0.02 | 1061 |
| TVT s21 t0.25 c2.0 vSPY LSSO b0.1 gb0.01 | CA | +4.50 | +5.98 | +5.35 | 100% | +3.25 | 100% | n/a | 0.002 | -57% (-55%) | 0.65 (0.60) | +0.77 | 1350 |
| TVT const1.7 v3 LSSO/DDM b0.1 gb0.0 | CA | +4.78 | +3.00 | +5.15 | 100% | +0.92 | 100% | n/a | 0.169 | -78% (-55%) | 0.53 (0.60) | -0.98 | 8 |
| TVT const1.8 v3 LSSO/DDM b0.1 gb0.0 | CA | +5.19 | +3.42 | +5.63 | 100% | +0.66 | 100% | n/a | 0.170 | -80% (-55%) | 0.53 (0.60) | -0.97 | 4 |
| TVT const2.0 v3 LSSO/DDM b0.1 gb0.0 | CA | +6.00 | +3.68 | +6.53 | 100% | +0.17 | 100% | n/a | 0.210 | -85% (-55%) | 0.52 (0.60) | -1.12 | 1 |
| TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.01 noST | CA | +2.40 | +2.41 | +3.21 | 100% | +0.25 | 100% | n/a | 0.030 | -50% (-55%) | 0.60 (0.60) | +0.09 | 1519 |
| TVT s21 t0.25 c1.5 v3 LSSO/DDM b0.1 gb0.01 | CA | +2.69 | +3.38 | +3.24 | 100% | +1.48 | 100% | n/a | 0.004 | -51% (-55%) | 0.64 (0.60) | +0.64 | 589 |

### Longer history with cost-calibrated synthetic 2x funds (research-only, not tradable)

`SYN_SPY2XC`, `SYN_DIA2XC`, `SYN_VFINX2XC` are daily-reset 2x series built by the leverage family:
2 x the underlying's total return, minus financing at the T-bill rate + 0.6%/yr, minus 0.9%/yr
expense — within 0.1 pp/yr of SSO over 2006-2026. They let the same rules run from 2000 (ETF era)
and from 1986 (VFINX benchmark; windows ending before 2000 are a holdout).

ETF era from 2000 (full protocol):

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VT SPY s21 t0.25 c2.0 SYN_SPY2XC /M | CA | +0.73 | -0.29 | +0.88 | 87% | -1.75 | 96% | 85% | 0.566 | -63% (-55%) | 0.35 (0.42) | -1.05 | 488 |
| VT SPY s21 t0.25 c2.0 SYN_SPY2XC /M | NONE | +3.65 | +2.09 | +3.72 | 93% | -1.75 | 100% | 100% | 0.151 | -63% (-55%) | 0.48 (0.47) | +0.13 | 480 |
| VT SPY s21 t0.2 c2.0 SYN_SPY2XC /M | CA | -0.91 | -1.46 | -0.74 | 36% | -2.99 | 6% | 4% | 0.877 | -54% (-55%) | 0.31 (0.42) | -1.63 | 608 |
| VT SPY s21 t0.2 c2.0 SYN_SPY2XC /M | NONE | +2.26 | +1.33 | +2.35 | 100% | +0.06 | 100% | 100% | 0.177 | -54% (-55%) | 0.49 (0.47) | +0.27 | 607 |
| VT SPY const1.3 c1.3 SYN_SPY2XC /M | CA | +0.84 | +0.20 | +0.87 | 82% | -2.70 | 87% | 89% | 0.400 | -67% (-55%) | 0.37 (0.42) | -0.70 | 636 |
| VT SPY const1.3 c1.3 SYN_SPY2XC /M | NONE | +1.27 | +0.60 | +1.27 | 84% | -2.70 | 87% | 93% | 0.292 | -67% (-55%) | 0.43 (0.47) | -0.63 | 636 |
| TVT s21 t0.25 c2.0 v3 LSYN_SPY2XC/SYN_DIA2XC b0.1 gb0.01 | CA | +2.31 | +0.70 | +2.45 | 79% | -4.97 | 85% | 93% | 0.347 | -70% (-55%) | 0.36 (0.42) | -0.88 | 1877 |
| TVT s21 t0.25 c2.0 v3 LSYN_SPY2XC/SYN_DIA2XC b0.1 gb0.0 | CA | +2.23 | +0.73 | +2.54 | 81% | -4.10 | 85% | 93% | 0.321 | -67% (-55%) | 0.37 (0.42) | -0.76 | 434 |
| TVT const1.5 v3 LSYN_SPY2XC/SYN_DIA2XC b0.1 gb0.0 | CA | +2.01 | +0.77 | +2.09 | 82% | -3.90 | 85% | 93% | 0.320 | -71% (-55%) | 0.37 (0.42) | -0.78 | 15 |

| config | regime | 2000-2005 | 2005-2010 | 2010-2015 | 2015-2020 | 2020-2025 |
|---|---|---|---|---|---|---|
| TVT s21 t0.25 c2.0 v3 LSYN_SPY2XC/SYN_DIA2XC b0.1 gb0.01 | CA | -3.6 | +0.8 | +1.5 | +1.6 | +2.6 |
| VT SPY s21 t0.25 c2.0 SYN_SPY2XC /M | CA | -4.1 | -0.1 | +3.0 | +0.7 | +1.3 |
| VT SPY s21 t0.25 c2.0 SYN_SPY2XC /M | NONE | -4.1 | +1.3 | +8.0 | +2.9 | +4.0 |

1986-2026 (long_screen protocol, VFINX benchmark; ho5 / ho10 = mean excess of the 5- / 10-year
windows that end before 2000):

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades | ho5 | ho10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VT VFINX s21 t0.25 c2.0 SYN_VFINX2XC cash=VFISX /M | CA | -0.13 | -1.20 | -0.02 | 65% | -3.48 | 42% | 33% | 0.817 | -68% (-55%) | 0.39 (0.55) | -2.21 | 720 | +1.54 | +0.98 |
| VT VFINX s21 t0.25 c2.0 SYN_VFINX2XC cash=VFISX /M | NONE | +2.75 | +2.57 | +2.88 | 81% | -2.24 | 92% | 100% | 0.057 | -65% (-55%) | 0.55 (0.57) | -0.32 | 717 | +5.30 | +4.97 |
| VT VFINX s21 t0.2 c2.0 SYN_VFINX2XC cash=VFISX /M | CA | -1.02 | -2.37 | -0.91 | 23% | -3.04 | 4% | 5% | 0.981 | -58% (-55%) | 0.36 (0.55) | -2.65 | 914 | +0.47 | -0.26 |
| VT VFINX s21 t0.2 c2.0 SYN_VFINX2XC cash=VFISX /M | NONE | +2.10 | +1.92 | +2.24 | 84% | -1.46 | 96% | 100% | 0.056 | -56% (-55%) | 0.58 (0.57) | +0.06 | 914 | +4.81 | +4.56 |
| VT VFINX const1.3 c1.3 SYN_VFINX2XC cash=VFISX /M | CA | +0.70 | -0.05 | +0.79 | 77% | -2.91 | 69% | 52% | 0.517 | -71% (-55%) | 0.48 (0.55) | -0.93 | 972 | +1.97 | +1.79 |
| VT VFINX const1.3 c1.3 SYN_VFINX2XC cash=VFISX /M | NONE | +1.08 | +1.20 | +1.15 | 84% | -2.81 | 69% | 86% | 0.095 | -67% (-55%) | 0.53 (0.57) | -0.57 | 972 | +2.60 | +2.49 |
| VT VFINX const1.5 c1.5 SYN_VFINX2XC cash=VFISX /M | CA | +1.15 | +0.47 | +1.30 | 74% | -4.88 | 69% | 57% | 0.320 | -79% (-55%) | 0.46 (0.55) | -1.23 | 972 | +3.34 | +3.11 |
| VT VFINX const1.5 c1.5 SYN_VFINX2XC cash=VFISX /M | NONE | +1.67 | +1.85 | +1.79 | 81% | -4.76 | 69% | 76% | 0.114 | -74% (-55%) | 0.52 (0.57) | -0.82 | 972 | +4.28 | +4.07 |
| BH VFINX:0.5,SYN_VFINX2XC:0.5 | CA | +1.45 | +1.80 | +1.70 | 68% | -3.83 | 65% | 62% | 0.138 | -77% (-55%) | 0.49 (0.55) | -0.90 | 2 | +3.89 | +4.08 |
| BH VFINX:0.5,SYN_VFINX2XC:0.5 | NONE | +1.69 | +1.82 | +1.88 | 68% | -3.83 | 65% | 62% | 0.146 | -77% (-55%) | 0.50 (0.57) | -1.04 | 2 | +4.57 | +4.46 |
| TVT s21 t0.25 c2.0 vVFINX LSYN_VFINX2XC b0.1 gb0.01 | CA | +2.52 | +1.19 | +3.00 | 71% | -4.71 | 73% | 43% | 0.260 | -79% (-55%) | 0.46 (0.55) | -1.28 | 2610 | +6.11 | +5.35 |
| TVT s21 t0.25 c2.0 vVFINX LSYN_VFINX2XC b0.1 gb0.0 | CA | +2.18 | -0.19 | +2.73 | 65% | -4.53 | 58% | 29% | 0.558 | -58% (-55%) | 0.48 (0.55) | -0.97 | 19 | +6.82 | +5.29 |
| TVT const1.5 vVFINX LSYN_VFINX2XC b0.1 gb0.0 | CA | +1.64 | +1.80 | +1.85 | 74% | -4.63 | 69% | 71% | 0.138 | -77% (-55%) | 0.49 (0.55) | -0.90 | 2 | +3.89 | +4.08 |
| TVT const1.8 vVFINX LSYN_VFINX2XC b0.1 gb0.0 | CA | +2.13 | +2.50 | +2.42 | 74% | -7.51 | 69% | 67% | 0.151 | -85% (-55%) | 0.48 (0.55) | -1.03 | 2 | +5.85 | +5.98 |
| TVT s21 t0.2 c1.5 vVFINX LSYN_VFINX2XC b0.1 gb0.01 | CA | +1.09 | +0.31 | +1.27 | 71% | -2.13 | 73% | 67% | 0.336 | -66% (-55%) | 0.48 (0.55) | -0.95 | 2384 | +2.80 | +2.37 |
| TVT s21 t0.3 c2.0 vVFINX LSYN_VFINX2XC b0.1 gb0.01 | CA | +2.43 | +1.21 | +2.88 | 74% | -7.51 | 69% | 48% | 0.250 | -78% (-55%) | 0.46 (0.55) | -1.26 | 2625 | +6.12 | +5.33 |
| TVT e20 t0.25 c2.0 vVFINX LSYN_VFINX2XC b0.1 gb0.01 | CA | +1.58 | +0.41 | +1.92 | 68% | -3.49 | 58% | 48% | 0.332 | -67% (-55%) | 0.47 (0.55) | -1.09 | 2627 | +5.83 | +4.36 |

| config | regime | 1986-1991 | 1991-1996 | 1996-2001 | 2001-2006 | 2006-2011 | 2011-2016 | 2016-2021 | 2021-2026 |
|---|---|---|---|---|---|---|---|---|---|
| TVT s21 t0.25 c2.0 vVFINX LSYN_VFINX2XC b0.1 gb0.01 | CA | -4.1 | +5.0 | +4.2 | -0.3 | +1.7 | +3.1 | +4.3 | +2.2 |
| VT VFINX s21 t0.25 c2.0 SYN_VFINX2XC cash=VFISX /M | CA | -3.6 | +4.6 | -3.0 | -3.5 | +1.9 | +1.6 | +0.2 | +2.7 |
| VT VFINX s21 t0.25 c2.0 SYN_VFINX2XC cash=VFISX /M | NONE | -2.0 | +8.2 | +2.8 | -3.7 | +2.6 | +4.3 | +3.7 | +6.9 |
| VT VFINX const1.3 c1.3 SYN_VFINX2XC cash=VFISX /M | CA | -0.3 | +2.3 | +2.1 | -1.3 | -1.4 | +2.2 | +2.2 | +1.6 |
| VT VFINX const1.3 c1.3 SYN_VFINX2XC cash=VFISX /M | NONE | -0.2 | +3.1 | +2.7 | -1.6 | -1.9 | +2.8 | +3.2 | +2.4 |
| VT VFINX const1.5 c1.5 SYN_VFINX2XC cash=VFISX /M | CA | -0.7 | +4.0 | +3.5 | -2.4 | -2.9 | +3.6 | +3.7 | +2.8 |
| VT VFINX const1.5 c1.5 SYN_VFINX2XC cash=VFISX /M | NONE | -0.6 | +5.2 | +4.3 | -2.7 | -3.3 | +4.6 | +5.2 | +3.8 |
| BH VFINX:0.5,SYN_VFINX2XC:0.5 | CA | -1.0 | +4.7 | +3.6 | -2.5 | -3.1 | +3.8 | +4.2 | +3.1 |
| BH VFINX:0.5,SYN_VFINX2XC:0.5 | NONE | -1.2 | +5.7 | +4.4 | -2.7 | -3.6 | +4.7 | +5.1 | +3.8 |

The two leads' synthetic analogues on the full `long` protocol (quarterly starts 1986-2023):

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades | ho5 | ho10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| TVT s21 t0.25 c2.0 vVFINX LSYN_VFINX2XC b0.1 gb0.01 | CA | +2.46 | +1.19 | +2.91 | 74% | -5.54 | 72% | 55% | 0.260 | -79% (-55%) | 0.46 (0.55) | -1.28 | 2610 | +5.83 | +5.37 |
| VT VFINX s21 t0.25 c2.0 SYN_VFINX2XC cash=VFISX /M | NONE | +2.68 | +2.57 | +2.81 | 81% | -4.27 | 92% | 100% | 0.057 | -65% (-55%) | 0.55 (0.57) | -0.32 | 717 | +5.19 | +4.97 |
| VT VFINX s21 t0.25 c2.0 SYN_VFINX2XC cash=VFISX /M | CA | -0.18 | -1.20 | -0.08 | 63% | -4.40 | 45% | 40% | 0.817 | -68% (-55%) | 0.39 (0.55) | -2.21 | 720 | +1.88 | +1.22 |

## 3. Hindsight checks (PROTOCOL 5.3)

The S&P 500 is the benchmark, not a hindsight pick, so "remove the star" does not apply to the SPY
vol target itself. The hindsight risk is the *decision to lever* an index after its best 17 years.
Two checks. (a) The same levered rule (25% target, 2x cap) on the other equity indexes that have a
synthetic 2x series — DIA, MDY, IWM, EFA, EEM and QQQ (a fixed, predefined set: synthetic 2x
series exist only for these, so this is the available cross-section, not a random draw) — each
against its own buy-and-hold, screen protocol from 2000-2004. (b) Unlevered vol targeting on 20
random funds from `BROAD_EQUITY_POOL_2003` against their own buy-and-hold. For risk parity, the
gold menus with GLD removed.

Result (a): the rule beats its own index only where that index had a high Sharpe ratio over the
sample. In NONE it wins on QQQ (+4.80 pp/yr — QQQ's 2000-02 crash was a slow, high-volatility
decline the vol target sidestepped) and DIA (+2.97), roughly ties MDY (+0.83, 10y beat 65%) and
loses on IWM (-0.81), EFA (-0.72) and EEM (-2.30); its Sharpe is *below* its own buy-and-hold's on
5 of 6 indexes. In CA with normal execution it loses on 5 of 6 (DIA +0.95). With tax-aware
execution in CA: QQQ +4.92, DIA +2.71, MDY +0.23, IWM -1.28, EFA -1.77, EEM -3.37, with max
drawdowns of -63% to -83% (the gain budget keeps it levered into crashes). A rule whose sign
depends on which market you apply it to is a leverage bet on that market's equity premium, not
a risk-management edge. Picking the US large-cap index *because* 2009-2026 rewarded leverage on
it is exactly the hindsight PROTOCOL 5.3 warns about.

Result (b): unlevered vol targeting generalizes the way the SPY version behaved — on the 20 random
funds it cut the maximum drawdown on 19 of 20 (e.g. semiconductors -42% vs -75%, REITs -36% vs
-75%), raised the Sharpe ratio on half of them (median +0.01), and lowered the return on 17 of 20
(median score -0.81 pp/yr vs the fund's own buy-and-hold, NONE). Lower risk, lower return; no
free lunch, and no special SPY effect.

standard execution, NONE:

| underlying | first start | score vs own B&H | full vs own B&H | 10y beat own B&H | Sharpe strat / B&H | maxDD strat / B&H |
|---|---|---|---|---|---|---|
| DIA | 2000-01 | +2.97 | +1.69 | 88% | 0.45 / 0.48 | -56% / -52% |
| MDY | 2000-01 | +0.83 | -0.41 | 65% | 0.42 / 0.51 | -54% / -55% |
| IWM | 2001-01 | -0.81 | -1.46 | 56% | 0.35 / 0.44 | -57% / -59% |
| EFA | 2002-01 | -0.72 | +0.11 | 27% | 0.33 / 0.38 | -59% / -61% |
| EEM | 2004-01 | -2.30 | -0.45 | 8% | 0.34 / 0.39 | -55% / -66% |
| QQQ | 2000-01 | +4.80 | +5.74 | 100% | 0.60 / 0.40 | -63% / -83% |

standard execution, CA:

| underlying | first start | score vs own B&H | full vs own B&H | 10y beat own B&H | Sharpe strat / B&H | maxDD strat / B&H |
|---|---|---|---|---|---|---|
| DIA | 2000-01 | +0.95 | -0.20 | 82% | 0.35 / 0.44 | -58% / -52% |
| MDY | 2000-01 | -1.79 | -3.01 | 35% | 0.27 / 0.49 | -59% / -55% |
| IWM | 2001-01 | -2.78 | -3.50 | 6% | 0.22 / 0.42 | -60% / -59% |
| EFA | 2002-01 | -1.97 | -1.44 | 13% | 0.22 / 0.35 | -64% / -61% |
| EEM | 2004-01 | -3.11 | -2.34 | 0% | 0.22 / 0.35 | -63% / -66% |
| QQQ | 2000-01 | -0.68 | +0.71 | 29% | 0.39 / 0.36 | -63% / -83% |

tax-aware execution (1%/yr gain budget), CA:

| underlying | first start | score vs own B&H | full vs own B&H | 10y beat own B&H | Sharpe strat / B&H | maxDD strat / B&H |
|---|---|---|---|---|---|---|
| DIA | 2000-01 | +2.71 | +2.01 | 82% | 0.41 / 0.44 | -67% / -52% |
| MDY | 2000-01 | +0.23 | -1.28 | 53% | 0.35 / 0.49 | -77% / -55% |
| IWM | 2001-01 | -1.28 | -1.70 | 31% | 0.30 / 0.42 | -74% / -59% |
| EFA | 2002-01 | -1.77 | -2.61 | 13% | 0.18 / 0.35 | -83% / -61% |
| EEM | 2004-01 | -3.37 | -2.62 | 8% | 0.22 / 0.35 | -81% / -66% |
| QQQ | 2000-01 | +4.92 | +4.21 | 94% | 0.52 / 0.36 | -63% / -83% |

Unlevered vol targeting (EWMA 20, 18% target) on 20 random equity funds drawn from
`BROAD_EQUITY_POOL_2003`, each against its own buy-and-hold (NONE):

| underlying | first start | score vs own B&H | full vs own B&H | 10y beat own B&H | Sharpe strat / B&H | maxDD strat / B&H |
|---|---|---|---|---|---|---|
| EWQ | 2000-01 | -0.83 | -0.79 | 53% | 0.21 / 0.24 | -40% / -61% |
| IYM | 2001-01 | -1.70 | -1.70 | 38% | 0.37 / 0.39 | -36% / -68% |
| XLV | 2000-01 | -0.79 | -0.76 | 24% | 0.47 / 0.48 | -32% / -39% |
| EWW | 2000-01 | -1.70 | -1.19 | 12% | 0.35 / 0.36 | -57% / -65% |
| IWS | 2002-01 | -0.93 | -0.84 | 47% | 0.59 / 0.55 | -40% / -62% |
| IWF | 2001-01 | -0.90 | -0.53 | 50% | 0.59 / 0.52 | -37% / -53% |
| IYH | 2001-01 | -0.67 | -0.54 | 50% | 0.47 / 0.48 | -35% / -41% |
| ONEQ | 2004-01 | -1.60 | -1.52 | 38% | 0.71 / 0.67 | -37% / -55% |
| EWM | 2000-01 | -1.10 | -0.13 | 6% | 0.20 / 0.20 | -52% / -52% |
| SMH | 2001-01 | -3.08 | -2.89 | 31% | 0.63 / 0.54 | -42% / -75% |
| EWN | 2000-01 | -0.73 | -0.69 | 53% | 0.30 / 0.30 | -46% / -65% |
| EWI | 2000-01 | -0.37 | -0.78 | 53% | 0.19 / 0.23 | -55% / -70% |
| XLU | 2000-01 | +0.10 | +0.07 | 59% | 0.51 / 0.47 | -42% / -52% |
| IJR | 2001-01 | -1.46 | -1.67 | 50% | 0.48 / 0.50 | -40% / -58% |
| EWC | 2000-01 | -1.07 | -0.92 | 41% | 0.38 / 0.38 | -43% / -61% |
| FVD | 2004-01 | -0.20 | -0.15 | 38% | 0.69 / 0.63 | -34% / -51% |
| IWB | 2001-01 | -0.72 | -0.79 | 50% | 0.56 / 0.53 | -38% / -55% |
| IDU | 2001-01 | +0.06 | +0.23 | 50% | 0.46 / 0.42 | -45% / -53% |
| IVE | 2001-01 | -0.03 | -0.24 | 50% | 0.47 / 0.43 | -42% / -61% |
| RWR | 2002-01 | +0.35 | +0.41 | 47% | 0.54 / 0.41 | -36% / -75% |

Summary over 20 random funds: score vs own B&H median -0.81, positive for 15%; Sharpe higher than own B&H for 50% (median difference +0.013).

Risk parity with the hindsight star (GLD) removed from the gold menus (SBG minus GLD = SB):

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RP SB invvol lb63 /M | CA | -2.29 | -3.98 | -2.34 | 43% | -7.16 | 11% | 0% | 0.941 | -31% (-55%) | 0.58 (0.68) | -1.24 | 566 |
| RP SB invvol lb63 /M | NONE | -2.09 | -3.27 | -2.15 | 43% | -7.92 | 22% | 0% | 0.855 | -30% (-55%) | 0.69 (0.70) | -0.17 | 566 |
| RP SB erc lb63 /M | CA | -2.29 | -3.98 | -2.34 | 43% | -7.16 | 11% | 0% | 0.941 | -31% (-55%) | 0.58 (0.68) | -1.24 | 566 |
| RP SB erc lb63 /M | NONE | -2.09 | -3.27 | -2.15 | 43% | -7.92 | 22% | 0% | 0.855 | -30% (-55%) | 0.69 (0.70) | -0.17 | 566 |
| RP SB minvar lb63 /M | CA | -2.34 | -4.11 | -2.38 | 43% | -7.28 | 11% | 0% | 0.937 | -32% (-55%) | 0.57 (0.68) | -1.35 | 566 |
| RP SB minvar lb63 /M | NONE | -1.99 | -3.29 | -2.04 | 43% | -7.96 | 33% | 0% | 0.852 | -30% (-55%) | 0.68 (0.70) | -0.26 | 566 |
| RP SPY+TLT+IEF+DBC invvol lb63 /M | CA | -6.97 | -5.98 | -7.18 | 0% | -10.49 | 0% | n/a | 0.946 | -21% (-55%) | 0.35 (0.60) | -3.43 | 940 |
| RP SPY+TLT+IEF+DBC invvol lb63 /M | NONE | -8.05 | -6.21 | -8.33 | 0% | -12.08 | 0% | n/a | 0.934 | -19% (-55%) | 0.49 (0.65) | -2.41 | 940 |
| RP SPY+TLT+IEF+DBC erc lb63 /M | CA | -6.78 | -5.94 | -6.97 | 0% | -10.13 | 0% | n/a | 0.953 | -20% (-55%) | 0.35 (0.60) | -3.40 | 940 |
| RP SPY+TLT+IEF+DBC erc lb63 /M | NONE | -7.74 | -6.11 | -7.98 | 0% | -11.53 | 0% | n/a | 0.946 | -18% (-55%) | 0.50 (0.65) | -2.26 | 940 |
| RP SPY+TLT+IEF+DBC minvar lb63 /M | CA | -7.44 | -6.61 | -7.61 | 0% | -11.01 | 0% | n/a | 0.959 | -19% (-55%) | 0.28 (0.60) | -4.50 | 697 |
| RP SPY+TLT+IEF+DBC minvar lb63 /M | NONE | -8.44 | -6.87 | -8.60 | 0% | -12.41 | 0% | n/a | 0.954 | -16% (-55%) | 0.47 (0.65) | -2.74 | 697 |
| RP SPY+EFA+EEM+TLT+IEF+DBC+VNQ invvol lb63 /M | CA | -6.48 | -5.54 | -6.67 | 0% | -9.66 | 0% | n/a | 0.959 | -24% (-55%) | 0.33 (0.60) | -3.72 | 1643 |
| RP SPY+EFA+EEM+TLT+IEF+DBC+VNQ invvol lb63 /M | NONE | -7.43 | -5.59 | -7.65 | 0% | -10.93 | 0% | n/a | 0.948 | -22% (-55%) | 0.46 (0.65) | -2.89 | 1644 |
| RP SPY+EFA+EEM+TLT+IEF+DBC+VNQ erc lb63 /M | CA | -6.96 | -6.00 | -7.15 | 0% | -10.37 | 0% | n/a | 0.953 | -23% (-55%) | 0.30 (0.60) | -4.12 | 1645 |
| RP SPY+EFA+EEM+TLT+IEF+DBC+VNQ erc lb63 /M | NONE | -7.97 | -6.17 | -8.20 | 0% | -11.82 | 0% | n/a | 0.945 | -21% (-55%) | 0.44 (0.65) | -3.25 | 1645 |
| RP SPY+EFA+EEM+TLT+IEF+DBC+VNQ minvar lb63 /M | CA | -7.84 | -6.93 | -8.00 | 0% | -11.41 | 0% | n/a | 0.963 | -20% (-55%) | 0.21 (0.60) | -5.49 | 891 |
| RP SPY+EFA+EEM+TLT+IEF+DBC+VNQ minvar lb63 /M | NONE | -8.90 | -7.24 | -9.06 | 0% | -12.93 | 0% | n/a | 0.958 | -18% (-55%) | 0.40 (0.65) | -3.86 | 891 |

Risk parity (ERC, 63-day) on random menus from `BROAD_POOL_2003` (screen protocol):

* CA, ERC on 20 random 6-fund menus: score median -3.11, best -0.70 (RP EWW+IJS+IYE+QQQ+RWR+XLK erc lb63), 0% positive; Sharpe above SPY's for 0% (median difference -0.131); median max drawdown -56%
* CA, ERC on 20 random 4 equity + 2 bond funds: score median -5.11, best -3.08 (RP EWN+IYC+RWR+SPYG+LQD+TLT erc lb63), 0% positive; Sharpe above SPY's for 0% (median difference -0.238); median max drawdown -25%
* NONE, ERC on 20 random 6-fund menus: score median -3.02, best +0.08 (RP EWW+IJS+IYE+QQQ+RWR+XLK erc lb63), 5% positive; Sharpe above SPY's for 25% (median difference -0.050); median max drawdown -54%
* NONE, ERC on 20 random 4 equity + 2 bond funds: score median -5.54, best -2.95 (RP EWN+IYC+RWR+SPYG+LQD+TLT erc lb63), 0% positive; Sharpe above SPY's for 0% (median difference -0.105); median max drawdown -23%

Risk parity's failure is not a menu-choice artifact: removing GLD leaves every gold menu losing by
2.0-8.9 pp/yr, and equal-risk-contribution portfolios of 20 random 6-fund menus and 20 random
"4 equity + 2 bond" menus lost to SPY in all 80 (menu x regime) cases but one (+0.08 in NONE),
by a median 3.0-5.5 pp/yr, with a Sharpe ratio above SPY's in only 0-25% of the menus. The hand-picked
menus (best CA -1.42) were, if anything, luckier than random ones.

## 4. Family diagnostics (overfitting)

`report.diagnostics` on every screened config (CA and NONE), overall and by evaluation era:

| regime | subset | configs | WF 10y->5y OOS (beat) | WF 5y->3y OOS (beat) | PBO | DSR of best | best by monthly mean |
|---|---|---|---|---|---|---|---|
| CA | all | 421 | -0.53 (33%) | -1.26 (50%) | 0.002 | 0.002 | TVT const2.0 v3 LSSO/DDM b0.1 gb0.0 |
| CA | from2000 | 225 | -2.23 (0%) | -2.68 (50%) | 0.299 | 0.424 | OV momentum t0.15 lb63 c1.0 /tax0.01 Q |
| CA | from_SSO_launch | 189 | +0.45 (50%) | -2.65 (33%) | 0.008 | 0.000 | TVT const2.0 v3 LSSO/DDM b0.1 gb0.0 |
| CA | unlevered_from2000 | 223 | -2.23 (0%) | -2.99 (50%) | 0.287 | 0.422 | OV momentum t0.15 lb63 c1.0 /tax0.01 Q |
| NONE | all | 324 | -2.89 (33%) | -1.59 (75%) | 0.145 | 0.013 | VT SPY s21 t0.25 c2.0 SSO /M |
| NONE | from2000 | 189 | -2.92 (0%) | -3.15 (25%) | 0.789 | 0.248 | TVT e20 t0.2 c2.0 v3 LSSO/DDM b0.1 hyb |
| NONE | from_SSO_launch | 128 | -0.44 (50%) | -3.20 (67%) | 0.208 | 0.010 | VT SPY s21 t0.25 c2.0 SSO /M |
| NONE | unlevered_from2000 | 187 | -4.94 (0%) | -3.12 (25%) | 0.838 | 0.263 | DD 0.1:1.0,1.0:0.5 hw252 /M |

How to read this. **PBO is near zero** in CA (0.002 overall, 0.008 for the SSO-era subset) not
because the search found a robust timing edge but because one dimension — leverage — dominated
every sub-sample of 2011-2026: the most-levered configs rank first in sample and stay first out
of sample. The **deflated Sharpe** of the best config (constant 2x leverage in CA) is 0.002 given
the number of configs tried: no evidence of a true after-tax excess Sharpe above zero once the
search is accounted for. The primary **walk-forward** (best trailing 10 years -> next 5 years) is
negative out of sample in CA with the lab's 4-yearly decisions (-0.53 pp; the 5y -> 3y variant
-1.26 pp) and with yearly decisions (-1.42 pp, ahead in 25% of 12 decisions): it chose unlevered
trend-filtered vol targets and risk parity until 2016 (all lost), the tax-aware levered vol target
in 2017 and 2018 (lost 3.0 and 4.1 pp/yr over the next 5 years), and only the constant-2x choices
of 2019-2021 won. The yearly 5y -> 3y variant is positive (+1.96 pp, 58% of 19 decisions) because
from 2012 on it kept picking leverage in a bull market. NONE: -2.89 / -1.59 pp (4-yearly), -0.78
/ -0.50 pp (yearly). The unlevered ETF-era sub-family has PBO 0.29 (CA) and 0.84 (NONE) with
negative walk-forwards (-2.2 / -4.9 pp): its in-sample winners do not persist. Lab caveat:
`report.diagnostics` keeps only the months covered by every config, so PBO and DSR here use
2011-01 to 2026-07 (the levered risk-parity configs start in 2011).

Walk-forward with yearly decision dates (the lab default steps 4 starts, i.e. 4 years, on the
yearly screen protocol — see lab notes):

CA walk-forward 10y -> 5y, yearly decisions: n=12, OOS mean -1.42, OOS beat 25%, in-sample +5.20, average config OOS -2.49

| decision date | chosen config | in-sample | out-of-sample |
|---|---|---|---|
| 2010-01-01 | VT SPY e20 t0.18 c1.0 tr200>0.0 /M | +7.23 | -3.34 |
| 2011-01-01 | VT SPY e20 t0.18 c1.0 tr200>0.0 /M | +5.12 | -3.33 |
| 2012-01-01 | RP MF2 hrp lb63 /M | +4.33 | -5.97 |
| 2013-01-01 | RP SB erc lb63 /M | +1.54 | -4.50 |
| 2014-01-01 | VT SPY e20 t0.18 c1.0 tr200>0.0 /M | +1.41 | -3.32 |
| 2015-01-01 | VT SPY e20 t0.18 c1.0 tr200>0.0 /M | +1.43 | -6.16 |
| 2016-01-01 | TVT e20 t0.18 c1.0 v3 b0.1 gb0.0 | +1.50 | -0.15 |
| 2017-01-01 | TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | +5.96 | -3.00 |
| 2018-01-01 | TVT s21 t0.25 c2.0 v3 LSSO/DDM b0.1 gb0.0 | +8.40 | -4.07 |
| 2019-01-01 | TVT const2.0 v3 LSSO/DDM b0.1 gb0.0 | +8.05 | +6.44 |
| 2020-01-01 | TVT const2.0 v3 LSSO/DDM b0.1 gb0.0 | +9.06 | +4.51 |
| 2021-01-01 | TVT const2.0 v3 LSSO/DDM b0.1 gb0.0 | +8.37 | +5.87 |

CA walk-forward 5y -> 3y, yearly decisions: n=19, OOS mean +1.96, OOS beat 58%, in-sample +7.38, average config OOS -0.88
NONE walk-forward 10y -> 5y, yearly decisions: n=12, OOS mean -0.78, OOS beat 58%, in-sample +5.01, average config OOS -2.63

| decision date | chosen config | in-sample | out-of-sample |
|---|---|---|---|
| 2010-01-01 | VT SPY e20 t0.18 c1.0 tr200>0.0 /M | +9.78 | -4.16 |
| 2011-01-01 | VT SPY e20 t0.18 c1.0 tr200>0.0 /M | +7.33 | -4.00 |
| 2012-01-01 | RP MF2 hrp lb63 /M | +6.43 | -7.06 |
| 2013-01-01 | RP SB hrp lb63 /M | +2.63 | -5.05 |
| 2014-01-01 | TVT e20 t0.2 c2.0 v3 LSSO/DDM b0.1 hyb | +2.96 | +1.17 |
| 2015-01-01 | TVT e20 t0.2 c2.0 v3 LSSO/DDM b0.1 hyb | +3.13 | +0.46 |
| 2016-01-01 | RP SB hrp lb63 /M | +2.18 | -4.50 |
| 2017-01-01 | VT SPY s21 t0.25 c1.5 SSO /M | +3.31 | +3.39 |
| 2018-01-01 | VT SPY s21 t0.25 c2.0 SSO /M | +5.58 | +0.09 |
| 2019-01-01 | VT SPY s21 t0.25 c2.0 SSO /M | +5.48 | +3.61 |
| 2020-01-01 | BH SPY:0.5,SSO:0.5 | +5.92 | +2.88 |
| 2021-01-01 | BH SPY:0.5,SSO:0.5 | +5.41 | +3.77 |

NONE walk-forward 5y -> 3y, yearly decisions: n=19, OOS mean -0.50, OOS beat 58%, in-sample +8.09, average config OOS -0.99

## 5. Long history without leverage (1986-2026, mutual-fund proxies)

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades | ho5 | ho10 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VT VFINX s21 t0.15 c1.0 cash=VFISX /M | CA | -1.23 | -2.62 | -1.26 | 32% | -3.23 | 19% | 0% | 0.991 | -45% (-55%) | 0.51 (0.55) | -0.56 | 497 | -1.71 | -2.11 |
| VT VFINX s21 t0.15 c1.0 cash=VFISX /M | NONE | -0.50 | -0.79 | -0.52 | 32% | -2.29 | 46% | 48% | 0.826 | -41% (-55%) | 0.61 (0.57) | +0.61 | 475 | -1.22 | -1.19 |
| VT VFINX s21 t0.2 c1.0 cash=VFISX /M | CA | -0.48 | -1.68 | -0.48 | 32% | -2.52 | 46% | 19% | 0.969 | -51% (-55%) | 0.53 (0.55) | -0.23 | 274 | -0.64 | -0.86 |
| VT VFINX s21 t0.2 c1.0 cash=VFISX /M | NONE | +0.01 | -0.20 | +0.01 | 35% | -1.71 | 58% | 86% | 0.656 | -47% (-55%) | 0.61 (0.57) | +0.51 | 246 | -0.41 | -0.40 |
| VT VFINX s21 t0.25 c1.0 cash=VFISX /M | CA | -0.11 | -1.14 | -0.10 | 45% | -1.95 | 54% | 33% | 0.937 | -54% (-55%) | 0.55 (0.55) | -0.00 | 181 | -0.22 | -0.28 |
| VT VFINX s21 t0.25 c1.0 cash=VFISX /M | NONE | +0.16 | +0.03 | +0.16 | 45% | -1.49 | 62% | 86% | 0.501 | -47% (-55%) | 0.60 (0.57) | +0.47 | 152 | -0.07 | -0.06 |
| VT VFINX e20 t0.15 c1.0 cash=VFISX /M | CA | -1.14 | -2.54 | -1.16 | 32% | -3.61 | 19% | 0% | 0.988 | -43% (-55%) | 0.52 (0.55) | -0.49 | 494 | -1.39 | -1.68 |
| VT VFINX e20 t0.15 c1.0 cash=VFISX /M | NONE | -0.72 | -0.99 | -0.73 | 32% | -3.26 | 46% | 29% | 0.858 | -39% (-55%) | 0.60 (0.57) | +0.41 | 472 | -1.15 | -1.10 |
| VT VFINX e20 t0.2 c1.0 cash=VFISX /M | CA | -0.59 | -1.72 | -0.57 | 32% | -2.65 | 31% | 14% | 0.978 | -53% (-55%) | 0.52 (0.55) | -0.45 | 282 | -0.51 | -0.59 |
| VT VFINX e20 t0.2 c1.0 cash=VFISX /M | NONE | -0.36 | -0.52 | -0.35 | 32% | -2.28 | 46% | 57% | 0.789 | -47% (-55%) | 0.58 (0.57) | +0.18 | 260 | -0.38 | -0.36 |
| VT VFINX e20 t0.25 c1.0 cash=VFISX /M | CA | -0.18 | -1.23 | -0.15 | 35% | -2.06 | 46% | 33% | 0.950 | -53% (-55%) | 0.53 (0.55) | -0.24 | 147 | -0.23 | -0.28 |
| VT VFINX e20 t0.25 c1.0 cash=VFISX /M | NONE | -0.03 | -0.19 | -0.02 | 42% | -1.92 | 46% | 57% | 0.636 | -46% (-55%) | 0.59 (0.57) | +0.22 | 119 | -0.14 | -0.13 |
| RP L-SB erc lb63 /M | CA | -1.42 | -3.70 | -1.54 | 40% | -7.20 | 36% | 40% | 0.954 | -31% (-55%) | 0.54 (0.56) | -0.24 | 950 | -4.03 | -4.80 |
| RP L-SB erc lb63 /M | NONE | -1.04 | -2.35 | -1.12 | 43% | -7.98 | 44% | 60% | 0.846 | -29% (-55%) | 0.69 (0.58) | +1.63 | 950 | -4.30 | -4.41 |
| RP L-SB minvar lb63 /M | CA | -2.01 | -4.35 | -2.17 | 37% | -8.05 | 32% | 15% | 0.965 | -32% (-55%) | 0.46 (0.56) | -1.36 | 924 | -5.92 | -6.79 |
| RP L-SB minvar lb63 /M | NONE | -1.25 | -2.64 | -1.35 | 40% | -8.24 | 44% | 60% | 0.849 | -29% (-55%) | 0.66 (0.58) | +1.27 | 924 | -5.09 | -5.28 |
| RP L-6 erc lb63 /M | CA | -2.54 | -4.82 | -2.73 | 23% | -9.33 | 28% | 15% | 0.984 | -23% (-55%) | 0.39 (0.56) | -2.36 | 2850 | -6.76 | -7.78 |
| RP L-6 erc lb63 /M | NONE | -2.15 | -3.45 | -2.30 | 33% | -9.48 | 36% | 45% | 0.927 | -22% (-55%) | 0.59 (0.58) | +0.19 | 2850 | -7.27 | -7.77 |
| RP L-6 minvar lb63 /M | CA | -3.34 | -5.66 | -3.53 | 17% | -9.45 | 20% | 0% | 0.993 | -22% (-55%) | 0.31 (0.56) | -3.43 | 1728 | -6.71 | -7.82 |
| RP L-6 minvar lb63 /M | NONE | -3.15 | -4.50 | -3.29 | 23% | -10.25 | 24% | 15% | 0.973 | -21% (-55%) | 0.56 (0.58) | -0.26 | 1727 | -7.20 | -7.78 |
| CPPI m3 f0.8 rA c1.0 /M | CA | -2.96 | -4.63 | -3.08 | 13% | -6.84 | 0% | 0% | 1.000 | -29% (-55%) | 0.45 (0.55) | -1.41 | 581 | -4.59 | -5.11 |
| CPPI m3 f0.8 rA c1.0 /M | NONE | -3.08 | -3.51 | -3.15 | 13% | -7.24 | 0% | 0% | 0.994 | -26% (-55%) | 0.59 (0.57) | +0.30 | 491 | -5.05 | -4.94 |
| DD 0.1:1.0,0.2:0.5,1.0:0.0 hw252 /M | CA | -0.21 | -1.82 | -0.18 | 52% | -3.55 | 69% | 57% | 0.907 | -35% (-55%) | 0.56 (0.55) | +0.19 | 197 | -1.21 | -1.44 |
| DD 0.1:1.0,0.2:0.5,1.0:0.0 hw252 /M | NONE | +0.19 | -0.43 | +0.23 | 52% | -3.38 | 69% | 71% | 0.637 | -34% (-55%) | 0.62 (0.57) | +0.81 | 164 | -1.19 | -1.18 |

The 1986-2026 record (VFINX = S&P 500 index fund as both the risky asset and the benchmark;
VFISX/VWSTX as cash; Vanguard long Treasury, high-yield and precious-metals funds plus small-cap
and international index funds for the risk-parity menus) repeats the ETF-era result without any
leverage: in CA every config loses (best: 25%-target vol target -0.11 pp/yr, boot_p 0.94;
drawdown tiers -0.21; stock/long-bond ERC -1.42; CPPI -2.96; six-asset min-variance -3.34), and
the pre-2000 holdout is negative too (unlevered vol targets -0.2 to -1.7 pp/yr over 5-year windows
ending before 2000). In NONE the best are +0.19 (drawdown tiers, boot_p 0.64) and +0.16 (vol
target, boot_p 0.50), with Sharpe ratios 0.60-0.62 vs VFINX's 0.57 and stock/bond ERC at 0.69 vs
0.58 — the familiar pattern: a little better risk-adjusted, not better in dollars.

Tax-executed vol-scaled momentum and the vol-target overlay on the incumbent (quarterly, 1%/yr gain
budget, same terms as the incumbent):

| config | regime | score | full | 10y mean | 10y beat | 10y min | 15y beat | 20y beat | boot p | maxDD (bench) | Sharpe (bench) | matched-vol | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| VM xs INC22 lb252 top5 /tax0.01 Q | CA | -0.36 | -0.02 | -0.37 | 29% | -2.82 | 50% | 57% | 0.492 | -52% (-55%) | 0.45 (0.42) | +0.41 | 501 |
| VM xs INC22 lb252 top5 /tax0.01 Q | NONE | -1.04 | -0.39 | -1.24 | 24% | -4.86 | 8% | 14% | 0.595 | -40% (-55%) | 0.48 (0.47) | +0.03 | 672 |
| VM xs INC22 lb252 top5 pt0.15 /tax0.01 Q | CA | -2.06 | -1.69 | -1.79 | 12% | -4.41 | 0% | 0% | 0.837 | -52% (-55%) | 0.34 (0.42) | -1.18 | 547 |
| VM xs INC22 lb252 top5 pt0.15 /tax0.01 Q | NONE | -3.13 | -2.34 | -3.24 | 12% | -6.45 | 0% | 0% | 0.862 | -37% (-55%) | 0.37 (0.47) | -1.54 | 723 |
| OV momentum t0.15 lb63 c1.0 /tax0.01 Q | CA | -0.08 | +1.53 | +0.06 | 65% | -2.77 | 67% | 71% | 0.056 | -55% (-55%) | 0.57 (0.42) | +2.04 | 611 |
| OV momentum t0.15 lb63 c1.0 /tax0.01 Q | NONE | -1.33 | -0.84 | -1.35 | 35% | -6.26 | 42% | 14% | 0.650 | -35% (-55%) | 0.48 (0.47) | +0.07 | 789 |

With the incumbent's tax terms, inverse-vol weighting of the top-5 momentum ETFs does not help
(CA score -0.36 pp, boot_p 0.49; with a 15% portfolio vol target -2.06). The vol-target overlay on
the incumbent's rotation (15% target, rest in SHY) is the one tax-aware variant with an
interesting risk profile: screen protocol CA score -0.08, full-period excess +1.53 pp, boot_p
0.056, Sharpe 0.57 vs SPY's 0.42, max drawdown -55% (= SPY) — but its 10-year beat rate is 65%
and its score is negative, so it is no better than the incumbent at the job the user asked for
(the incumbent on the same screen protocol: score +0.64, full +1.54 pp, 10-year beat 59%,
boot_p 0.025, Sharpe 0.51, matched-vol +1.23 pp vs the overlay's +2.04). Full-protocol check (95 quarterly starts): overlay CA score -0.18,
full +1.53 pp, 10-year beat 60%, 15-year beat 62%, boot_p 0.056, Sharpe 0.57, volatility 12.5%,
max drawdown -55%; incumbent CA +0.66 / +1.54 / 70% / 83% / 0.025, Sharpe 0.51, volatility 14.5%,
max drawdown -57%. The overlay buys a smoother ride (matched-vol +2.04 vs +1.23 pp) with fewer
winning windows; it fails items 1-2 of the bar.

## 6. Verification battery of the CA lead

`research.lab.verify.battery` on the CA lead (`battery.py`, output `battery_ca.json`; the
rebalance-offset and one-day-lag tests do not apply to the custom `risk_alloc.taxvt` kind, which
checks daily):

* Headline (full protocol): CA +3.40 / +4.85 pp, FED +3.64 / +6.32, NONE +4.01 / +3.40 (score /
  full-period excess); boot_p 0.014 / 0.002 / 0.024 with the battery's 500 bootstrap draws.
* Trading costs per side 0 / 5 / 15 / 35 bps: CA score +3.62 / +3.40 / +3.11 / +2.24 — robust,
  because the gain budget keeps trading low in taxable accounts (NONE, where the budget does not
  bind and it trades daily, falls to -1.41 at 35 bps).
* Stricter tax accounting (distributions taxed yearly at their real character; SSO/DDM income
  ordinary, SHY interest federal-only): CA excess from 2006 +4.85 -> +4.59, from 2010 +1.40 ->
  +1.39, from 2015 +0.95 -> +0.92, from 2020 +3.36 -> +3.32. Small.
* Sub-periods: CA 2010-2020 +2.50, 2020-2026 +3.36 (the 2006-07 start is needed for the 2008
  de-risking; none of these windows contains a crash that started after gains had built up).
* **Deflated Sharpe** (probability the true after-tax excess Sharpe is above zero, assuming 600
  trials; the family ran 454 configs, 559 with the hindsight checks): **CA 0.067**, FED 0.158, NONE 0.049. After accounting for the search,
  the evidence that this beats SPY on a risk-adjusted basis is weak.

## 7. Candidates and the confidence bar

Bar items (PROTOCOL 3): (1) score > 0 and full-period excess > 0; (2) 10-year beat >= 75% and
15-year beat >= 85%; (3) boot_p <= 0.10; (4) the family's walk-forward selection positive out of
sample and PBO < 0.5; (5) a parameter neighbourhood also passes; (6) no dependence on a hindsight
instrument; (7) the pre-2000 holdout does not contradict it. Full-protocol numbers, target regime.

| # | candidate | regime | score | full | 10y / 15y beat | boot_p | (1) | (2) | (3) | (4) | (5) | (6) | (7) | passes? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | tax-aware levered VT, 25% / 21d, cap 2x, 1%/yr gain budget (SPY/IWB/VTI + SSO/DDM) | CA | +3.40 | +4.85 | 98% / 100% | 0.011 | yes | yes | yes | **no** (WF -0.53 / -1.42 pp) | yes | **no** (works only on high-Sharpe indexes) | holdout yes (+6.1 pp); but 1986-2026 synthetic fails (2) and (3), 2000-2026 synthetic fails (3) | **no** — leverage |
| 2 | same, zero gain budget | CA | +3.17 | +5.54 | 98% / 100% | 0.002 | yes | yes | yes | **no** | yes | **no** | 1986-2026 synthetic: full -0.19, boot_p 0.56 | **no** — leverage |
| 3 | 50% SPY + 50% SSO, bought once (constant-leverage control) | CA | +3.39 | +2.35 | 100% / 100% | 0.111 | yes | yes | **no** | **no** | yes (1.5x-2x all positive) | **no** | 1986-2026 synthetic: boot_p 0.14, max DD -77% | **no** — leverage |
| 4 | plain levered VT, 25% / 21d, cap 2x, monthly (SPY + SSO) | NONE | +4.64 | +4.33 | 100% / 100% | 0.010 | yes | yes | yes | **no** (NONE WF -2.89 / -0.78 pp) | yes | **no** | holdout yes (+5.3 pp); 1986-2026 passes (1)-(3) but Sharpe 0.55 < 0.57; 2000-2026 boot_p 0.15 | **no** — leverage |
| 5 | plain levered VT, 25% / 21d, cap 1.5x | NONE | +3.18 | +3.01 | 100% / 100% | 0.012 | yes | yes | yes | **no** | yes | **no** | not run on synthetic | **no** — leverage |
| 6 | best unlevered: tax-aware VT, EWMA20, 25%, cap 1x, zero budget | CA | +0.05 | +0.12 | 48% / 66% | 0.469 | yes | **no** | **no** | **no** | no | yes | n/a | **no** |
| 7 | risk parity, SPY + long Treasuries (VUSTX), ERC 63d, monthly | NONE | -1.33 | -0.71 | 52% / 36% | 0.600 | **no** | **no** | **no** | **no** | no (all RP lose) | bonds' 2000-2020 bull market | 1986-2026: -1.04, holdout -4.3 pp | **no** |
| 8 | drawdown-tier de-risking of SPY (100% / 50% / 0% at 10% / 20% drawdown) | CA | -0.53 | -0.60 | 52% / 43% | 0.639 | **no** | **no** | **no** | **no** | no | yes | 1986-2026: -0.21, holdout -1.2 pp | **no** |

**Nothing passes.** Candidates 1-5 clear items 1-3 on the 2006-2026 sample only because they hold
1.5-1.9x the S&P 500; each fails the walk-forward item, each depends on applying leverage to the
one index that rewarded it, and in the user's regime (CA) the long synthetic histories fail items
2-3. Candidate 1 is the best answer this family can give to "beat SPY after CA tax", and the
honest description of it is "about 1.8x S&P 500 exposure, held through leveraged ETFs and kept
because selling it would trigger taxes": expected to beat SPY when stocks rise steadily, and to
lose far more than SPY (-61% on the record, -79% on 1986-2026 synthetic history) in a crash that
arrives after gains have built up.

## 8. Caveats and lab notes

* **Leverage is the risk, not a free lunch.** The engine has no margin, so leverage means daily-
  reset 2x funds (SSO, DDM, UPRO). They decay in choppy markets, carry ~0.9%/yr fees plus swap
  financing above T-bills, and can be closed or restructured. The 2006-2026 sample contains one
  slow crash where de-risking helped (2008), two fast ones where it could not (Q4-2018, Feb-Mar
  2020), the 2022 bear and a long low-volatility bull market in which 1.5-2x S&P exposure was the
  right bet. Max drawdowns of the levered configs: -47% to -61% (vol-targeted) and -71% to -85%
  (constant leverage), vs SPY's -55%.
* **Synthetic history is research-only.** `SYN_*2XC` series are model-built (calibrated to SSO
  within 0.1 pp/yr over 2006-2026) and not tradable; pre-2006 financing spreads and fund
  frictions may differ. They are used only to ask whether the 2006-2026 result generalizes.
* **Not runnable on the website today.** SSO, DDM, IWB and SHY are research-only tickers (VTI and
  SPY are site tickers) and `risk_alloc.taxvt` is a research strategy kind; the risk-parity menus
  use research-only bond/gold/commodity funds. An investor would have to implement these by hand.
* **Distributions.** The engine taxes dividends and interest only when a position is sold. SSO /
  DDM distribute 0.2-1%/yr (ordinary income), SPY ~1.3-2% (qualified), SHY interest is ordinary
  income: the verification battery's stricter accounting (section 6) quantifies the effect for
  the CA lead. Bond-heavy risk-parity configs are flattered by this simplification (PROTOCOL 5.5);
  they lose anyway. Average cash-proxy (SHY) weight of the CA lead ~1.5%.
* **Wash sales.** The engine does not enforce them. The tax-aware kind blocks re-buying a fund for
  31 days after selling it at a loss, but does not block a loss sale within 30 days *after* a
  purchase of the same fund. For the CA lead started 2007-01, 25 of 63 loss sales (21% of the
  realized losses, $10.3k of $49.1k on a $100k start) had a same-fund purchase within 30 days.
  Under the real rule those losses would be deferred into the new lots' basis, not lost; the
  effect on after-tax CAGR is a timing difference and small, but it flatters the strategy.
* **Path dependence.** Tax-aware results depend on the start date relative to volatility regimes
  and crashes (section 2): averages over 69 starts are the honest summary, single backtests are not.
* **Coverage.** The planned 753-config screen was not completed (battery throttle); unscreened
  RP/CPPI/VM grid points (other lookbacks and menus) are listed under untested ideas. Given that
  every one of the 56 representative configs of those groups lost to SPY in CA by 0.05-8.6 pp/yr,
  a different outcome on the rest of the grid is unlikely but not proven.


**Lab notes (suspected issues, reported, not edited):**

* `report.diagnostics` calls `metrics.walk_forward(..., step_quarters=4)` whatever the protocol;
  on the yearly `screen` protocol that steps 4 *starts* = 4 years, leaving only 3 (10y->5y) or 4
  (5y->3y) decision dates. Section 4 also reports yearly steps (`step_quarters=1`).
* `metrics.monthly_matrix` ends in `.dropna()`, so PBO and the deflated Sharpe silently use only
  the months that every config covers — here 2011-01 to 2026-07, because a few configs start in
  2011 — dropping 2000-2010 (including 2000-02 and 2008, the episodes that matter most for risk
  management) for all configs.
* The wash-sale guard (`blocks.WeightStrategy` "tax" execution, and this family's TaxVT) only
  blocks re-buying after a loss sale; a loss sale within 30 days after buying the same fund is not
  caught, and the engine does not enforce wash sales, so harvested losses are slightly
  front-loaded (quantified above for the CA lead).
* `registry.code_version` hashes the family file that registers a signal, not the files of signals
  it wraps: `risk_alloc.overlay` around `common.momentum` would keep stale cache entries if
  `families/common.py` changed.
* `metrics.summary`'s `bench_max_dd` / `bench_sharpe` come from the benchmark's run from the
  protocol's first start (2000-01), not from the config's first start (2006-07 for SSO configs).
  Harmless for max drawdown here (SPY's worst drawdown, 2007-09, is in both periods) but the
  engine-Sharpe comparison is misaligned; this file's Sharpe columns are computed on matched months
  instead (`analyze.matched_vol`).
