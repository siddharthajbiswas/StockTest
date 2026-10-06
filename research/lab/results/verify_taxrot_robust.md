# Verifying KX3 / KX1 (tax-managed rotation): robustness, hindsight, structure vs signal

Adversarial verification of the two round-1 finalists of family `tax_rotation`. Family key
`verify_taxrot_robust`; module `research/lab/families/verify_taxrot_robust.py` (adds only a
rebalance-boundary offset and a 1-day execution lag to the unchanged `tax_rotation` code); scripts,
logs and CSVs in `research/lab/scratch/verify_taxrot_robust/`. All numbers are lab-engine numbers
(website-identical). "Excess" = after-tax CAGR minus SPY buy-and-hold in the same regime
(0.01 = 1 pp/yr); "pp" = percentage points per year. Primary regime CA (48.1% / 28.1%).

- **KX3**: 378-day momentum (no skip), top 5 of the 22-ETF incumbent menu, semiannual; tax
  execution with a 1% gain budget; keep held funds while they rank in the top 10; never trim a fund
  the signal still wants; spend the gain budget on the worst-ranked holdings first.
- **KX1**: the incumbent signal (252-21 momentum, top 5, quarterly) with the same execution,
  long-term gains only, 2% budget.

## Verdict

**Both fail. Neither KX3 nor KX1 beats SPY after tax with good confidence, in CA or in FED.** KX1 is
the more robust of the two, but it fails the same decisive tests.

| CA | score | full_excess | ex10_beat | ex15_beat | ex20_beat | boot_p | max DD (SPY) | DSR (12k trials) |
|---|---|---|---|---|---|---|---|---|
| KX3, as reported | +0.99 | +1.84 | 0.90 | 0.85 | 0.96 | 0.011 | −53.7% (−55.2%) | 0.038 |
| KX3, starts ≥ 2002 | +0.81 | +0.83 | 0.88 | 0.82 | 0.95 | 0.173 | −58.2% (−55.2%) | |
| KX1, as reported | +0.93 | +1.82 | 0.91 | 0.89 | 0.96 | 0.011 | −56.6% (−55.2%) | 0.051 |
| KX1, starts ≥ 2002 | +0.80 | +1.55 | 0.90 | 0.87 | 0.95 | 0.051 | −58.9% (−55.2%) | |

(score and excess in pp/yr.)

**What holds:**
- The numbers reproduce exactly.
- There is no look-ahead and no code bug.
- Stricter distribution-tax accounting, a 1-day execution lag and costs up to 35 bps barely move the
  score.
- On the incumbent menu a positive score is a broad plateau (61 of 62 neighbours).
- The momentum ranking genuinely beats random picks under the same execution:
  - +0.7-0.8 pp of score on 30 menus nobody chose (t 5.8-6.9);
  - +0.8-0.9 on the incumbent menu;
  - +0.6-0.9 on the pre-ETF analog menu.

**What breaks:**
1. **Hindsight (criterion 6).**
   - Without QQQ the score falls 46-70% and both rules fail criteria 1-3.
   - Without QQQ and XLK it is −0.26 (KX3) / +0.12 (KX1), with 10-year beat rates of 0.46-0.49.
   - On 30 random menus: 1 in 30 passes. The mean score is +0.3 to +0.4, and zero or below from 2002 on.
   - The score rises with the number of tech funds in the menu: from −0.9 with none to +1.2 with
     three.
2. **Pre-2000 holdout (criterion 7).**
   - On the pre-ETF analog of the incumbent menu (PRE20, VFINX benchmark, 1-day lag) the true holdout
     is flat: KX3 ho5 +0.5 / ho10 +0.1, KX1 ho5 0.0 / ho10 0.0, boot_p 0.42-0.58.
   - On sector-fund menus the signal does not beat equal weight, and KX3's 10-year holdout on FSEL32
     is −1.9 pp/yr.
3. **Start-date artifact.**
   - On 2000-01-03 only SPY, MDY and DIA have the 274/379 days of history the rules need, so both
     start as a 1/3-each MDY/DIA/SPY portfolio. KX3 keeps MDY at about 40% for nine years; KX1 keeps
     it for three.
   - Scored from 2002 on, KX3 fails criteria 1-3 (ex15_beat 0.82, boot_p 0.17). KX1 still passes
     (boot_p 0.051).
4. **Timing and path chaos.**
   - Shifting rebalance dates by 4-8 weeks drops KX1's score to +0.70 / +0.38 (boot_p ~0.3). Only 1
     of 3 schedules passes, for each rule.
   - Moving costs from 5 to 15 bps per side (immaterial at 5-7% turnover) cuts the full-period excess
     to +0.46 (KX3) / +0.91 (KX1).
   - The headline full_excess and boot_p are one draw from a chaotic path.
5. **Multiple testing (criterion 4).** The deflated Sharpe is 0.04 / 0.05 given ~12,000
   configurations tried; round 1's PBO is 0.60-0.68. The neighbourhood plateau is real, but only
   25-37% of neighbours clear criteria 1-3.
6. **Regime.**
   - 2000-2008's lead is the forced mid-cap position.
   - 2009-2026's lead is entirely frozen growth/tech (+2.0 pp/yr; the rest of the portfolio −1.2 to
     −1.3 pp/yr).
   - Five-year windows starting 2019 or later lose 2.7-2.8 pp/yr and beat SPY 9-18% of the time.
   - By 2026 the portfolio is 54-57% growth/tech and 81-87% unrealized gain.

**Signal, structure or regime luck?**
- **Signal:** real, but modest and menu-dependent: it works best when the menu holds the era's winners.
- **Structure:** the tax-managed, no-trim execution is necessary for any rotation to survive CA
  taxes, and worth about zero on its own.
- **Regime luck:** the lead over SPY. Most of the 2000-2026 excess comes from two regime bets the
  rule fell into: mid caps at the 2000 peak, forced by ETF launch dates, and US mega-cap growth since
  2009.

**Most robust design:** KX1 unchanged, used as a tax-efficient momentum tilt rather than an
S&P-beater. No variant fixes the menu and regime dependence (section 9).

## Config count

- **Records and configs:** 492 config × regime × protocol records over 314 distinct configs:
  - `screen` 180;
  - `full` 270;
  - `long_screen` 30;
  - `long` 12.
- **Reused from round 1 (cache hits):** 90 screen random-menu records (KX3, KX1, RR1) and 11
  neighbours.
- **Run new here:** about 380 records.
- **Extra engine runs:** 16 realism runs and 4 holdings traces.
- **Selection:** none of these configs was searched for performance. They are controls, menus,
  perturbations and neighbourhood checks, so they add little to the ~12,000-config multiple-testing
  count. The deflated Sharpe above uses 12,000.

## 1. Reproduction and code checks

- The round-1 numbers reproduce exactly. KX3 CA: score +0.99 pp, full +1.84 pp, ex10_beat 0.90,
  ex15_beat 0.85, ex20_beat 0.96, boot_p 0.011, max DD −53.7% (SPY −55.2%). KX1 CA: +0.93,
  +1.82, 0.91, 0.89, 0.96, 0.011, −56.6%.
- The new kind (`verify_taxrot_robust.ws`, offset 0 / lag 0) reproduces `tax_rotation.ws` to the
  cent at every checkpoint of every start (`v0_identity.py`: max |liquidation-value difference| = 0.0).
- Code read line by line (`Rank.weights`, `TRStrategy._tax_sells`, `_buys`, the hold buffer, the
  rank-ordered gain spending, the wash guard). No look-ahead, no bug that changes KX3/KX1. Rebalances
  are 3-6 months apart, so the wash-sale look-back side never binds (round 1's strict-wash variant was
  identical).
- **Evaluation artifact found (not a code bug): fund-history eligibility at the 2000 start.** The
  rules need 274 (KX1) or 379 (KX3) trading days of history. On 2000-01-03 only SPY, MDY and DIA
  have it (sector SPDRs launched 1998-12-22, QQQ 1999-03-10, IWM/IJR/IWD/IWF 2000-05-26, EFA 2001,
  EEM/RSP 2003). Both rules therefore start as a 1/3 each MDY/DIA/SPY portfolio; because still-wanted
  funds are never trimmed and MDY stays in the top 10, **MDY is 39-45% of KX3 from 2000 to 2008 and
  ~30% until 2017**. A real investor in 2000 would have faced the same constraint, but the result is
  produced by ETF launch dates, not by momentum. It also means the 2000-01 start, which supplies
  `full_excess` and the bootstrap series, is the most favourable start:

  | statistic (CA) | KX3 all starts | KX3 starts ≥ 2002-01 | KX1 all starts | KX1 starts ≥ 2002-01 |
  |---|---|---|---|---|
  | score | +0.99 | +0.81 | +0.93 | +0.80 |
  | ex10_beat / ex15_beat | 0.90 / 0.85 | 0.88 / **0.82** | 0.91 / 0.89 | 0.90 / 0.87 |
  | full-period excess from the first start | +1.84 (2000-01) | +0.83 (2002-01) | +1.82 | +1.55 |
  | starts 2000-01..2001-12 only: score | +2.34 | | +1.94 | |

  Full-period excess by start date (CA) swings with what the rule happens to buy first and then
  freezes: KX3 +1.84 (2000-01), +1.06 (2001-07), +0.83 (2002-01), **−0.75 (2003-01)**, +0.90
  (2005-01), +1.23 (2009-01); KX1 +1.82, +1.57, +1.55, +0.05, +1.24, +0.11.

## 2. (a) 30 random menus: signal is real, the lead over SPY is not

Menus: seeds 1-30, 15-25 funds drawn from the pre-registered `common.BROAD_EQUITY_POOL_2003`
(identical to round 1's menus), wash guard over identical-index groups. Same menus, six rules:
- **KX3**, **KX1**;
- **RR3 / RR1**: random ranking with exactly the same execution and history rule (seed = menu
  seed), the structure without the signal;
- **EWBH**: equal weight of every fund live at the start, never sold (no selection, no trading);
- **EWTAX**: equal weight rebalanced quarterly with the site's tax rule (1% budget, trims).

Protocol `screen` (24 yearly starts), CA. Round 1's KX3/KX1/RR1 records are reused (cache hits);
RR3, EWBH and EWTAX are new.

| rule | score mean (share > 0) | full_excess mean (share > 0) | ex10_beat | ex15_beat | max DD | pass 1-3 | score, starts ≥ 2002 | full from 2002 (share > 0) |
|---|---|---|---|---|---|---|---|---|
| KX3 | +0.39 (77%) | +0.16 (60%) | 0.52 | 0.53 | −64% | 1/30 | +0.00 | −0.24 (37%) |
| KX1 | +0.42 (70%) | +0.70 (87%) | 0.48 | 0.56 | −64% | 1/30 | −0.02 | +0.67 (73%) |
| RR3 | −0.32 (23%) | −0.54 (23%) | 0.44 | 0.43 | −60% | 0/30 | −0.70 | −0.54 (30%) |
| RR1 | −0.38 (23%) | −0.20 (33%) | 0.43 | 0.39 | −59% | 0/30 | −0.77 | −0.51 (27%) |
| EWBH | −0.38 (13%) | −1.01 (3%) | 0.35 | 0.34 | −61% | 0/30 | −0.81 | −0.45 (13%) |
| EWTAX | −0.59 (10%) | +0.24 (57%) | 0.35 | 0.38 | −58% | 0/30 | −1.06 | −0.01 (47%) |

Paired differences on the same 30 menus (pp/yr; t-statistic; share of menus where the first is better):

| comparison | score | full_excess | score, starts ≥ 2002 |
|---|---|---|---|
| KX3 − RR3 (signal, same execution) | +0.72 (t 5.7, 80%) | +0.70 (t 4.0, 73%) | +0.71 (t 5.1) |
| KX1 − RR1 | +0.80 (t 7.2, 90%) | +0.89 (t 5.1, 87%) | +0.75 (t 6.4) |
| RR3 − EWBH (execution/concentration, no signal) | +0.06 (t 0.7, 53%) | +0.47 (t 3.1, 70%) | +0.11 (t 1.1) |
| RR1 − EWBH | +0.00 (t 0.0, 43%) | +0.81 (t 4.3, 70%) | +0.05 (t 0.6) |
| EWBH − EWTAX | +0.21 (t 8.6, 93%) | −1.25 (t −9.6, 3%) | +0.25 (t 16.6) |

The same 30 menus on the `full` protocol (95 quarterly starts; EWTAX omitted) give the same picture:

| rule | score mean (share > 0) | full mean (share > 0) | ex10_beat | ex15_beat | pass 1-3 | score, starts ≥ 2002 |
|---|---|---|---|---|---|---|
| KX3 | +0.42 (73%) | +0.16 (60%) | 0.51 | 0.50 | 1/30 | −0.04 |
| KX1 | +0.34 (63%) | +0.70 (87%) | 0.48 | 0.53 | 1/30 | −0.17 |
| RR3 | −0.38 (17%) | −0.54 (23%) | 0.42 | 0.40 | 0/30 | −0.85 |
| RR1 | −0.38 (20%) | −0.20 (33%) | 0.42 | 0.40 | 0/30 | −0.86 |
| EWBH | −0.41 (13%) | −1.01 (3%) | 0.34 | 0.34 | 0/30 | −0.90 |

Paired on `full`: KX3 − RR3 +0.80 (t 5.8, 83% of menus), KX1 − RR1 +0.73 (t 6.9, 87%),
RR3 − EWBH +0.03 (t 0.3), RR1 − EWBH +0.03 (t 0.4). KX3 score by tech funds in the menu: none −0.91,
one +0.19, two +0.44, three +1.21.

- **The momentum signal is real and menu-independent.** It beats random ranking under the identical
  execution by about +0.7-0.8 pp of score on 80-90% of menus nobody chose, including from starts
  after the 2000-2001 artifact.
- **The execution alone (random picks) is worth nothing on score** versus simply buying the menu
  equally and holding it (RR − EWBH ≈ 0); its +0.5-0.8 pp of full_excess is a 2000-start effect.
- **But the lead over SPY is not robust.** On random menus the rules average only +0.4 pp of score,
  beat SPY in about half of 10- and 15-year windows, and 1 menu in 30 passes criteria 1-3. From starts
  after 2001 the average score is zero or below (−0.17 to +0.00).
- **The lead tracks how much tech the menu happens to contain.** KX3 score by the number of
  QQQ/XLK/IYW/IGV/SMH/SOXX/ONEQ funds in the menu: none −0.79 (3 menus), one +0.20 (11), two +0.40
  (8), three +1.10 (8). The signal's lift over random (KX3 − RR3) grows the same way: +0.18, +0.60,
  +0.76, +1.04.

## 3. (b) The incumbent menu without QQQ / XLK (full protocol)

Round 1 ran these removals on `screen` only; here they are on `full` (quarterly starts), CA and FED.

| menu | rule | regime | score | full | ex10_beat | ex15_beat | ex20_beat | boot_p | pass 1-3 | score / full, starts ≥ 2002 |
|---|---|---|---|---|---|---|---|---|---|---|
| incumbent 22 | KX3 | CA | +0.99 | +1.84 | 0.90 | 0.85 | 0.96 | 0.016 | yes | +0.81 / +0.83 |
| − QQQ | KX3 | CA | +0.30 | +0.46 | 0.58 | 0.62 | 0.52 | 0.36 | no | +0.03 / −0.86 |
| − XLK | KX3 | CA | +0.39 | +0.83 | 0.70 | 0.79 | 0.89 | 0.20 | no | +0.15 / +0.49 |
| − QQQ − XLK | KX3 | CA | −0.26 | +0.15 | 0.46 | 0.51 | 0.41 | 0.46 | no | −0.60 / −0.61 |
| incumbent 22 | KX1 | CA | +0.93 | +1.82 | 0.91 | 0.89 | 0.96 | 0.014 | yes | +0.80 / +1.55 |
| − QQQ | KX1 | CA | +0.50 | +1.29 | 0.61 | 0.75 | 0.96 | 0.080 | no | +0.19 / +0.68 |
| − XLK | KX1 | CA | +0.60 | +1.06 | 0.69 | 0.77 | 0.96 | 0.11 | no | +0.27 / +0.26 |
| − QQQ − XLK | KX1 | CA | +0.12 | +0.14 | 0.49 | 0.64 | 0.56 | 0.48 | no | −0.34 / −0.99 |
| − QQQ | KX3 | FED | +0.36 | +0.56 | 0.58 | 0.64 | 0.63 | 0.32 | no | |
| − XLK | KX3 | FED | +0.45 | +0.88 | 0.70 | 0.79 | 0.93 | 0.18 | no | |
| − QQQ − XLK | KX3 | FED | −0.26 | +0.17 | 0.48 | 0.51 | 0.41 | 0.44 | no | |
| − QQQ | KX1 | FED | +0.59 | +1.41 | 0.64 | 0.77 | 1.00 | 0.058 | no | |
| − XLK | KX1 | FED | +0.68 | +1.18 | 0.67 | 0.81 | 0.96 | 0.090 | no | |
| − QQQ − XLK | KX1 | FED | +0.16 | +0.24 | 0.49 | 0.64 | 0.70 | 0.44 | no | |

(boot_p here from 500 bootstrap draws; the headline rows use 1,000 in the verdict table.)

- **Removing one fund that was chosen with hindsight removes most of the edge.** Without QQQ the
  score falls by 46-70% and the 10-year beat rate drops to about 0.6. Without both QQQ and XLK the
  score is −0.26 (KX3) / +0.12 (KX1) and the rules beat SPY in about half of 10-year windows: a coin
  flip.
- From starts after the 2000-2001 eligibility artifact, the menus without QQQ/XLK have scores of
  −0.6 to +0.3.
- Criterion 6 (no dependence on one instrument chosen with hindsight) fails for both, in CA and FED.

Controls on the same menus (full, CA; RR = random ranking with the KX execution, mean of 5 seeds on
the incumbent menu and 2 seeds without QQQ/XLK):

| menu | KX3 | KX1 | RR3 | RR1 | EWBH | EWTAX |
|---|---|---|---|---|---|---|
| incumbent 22: score / full | +0.99 / +1.84 | +0.93 / +1.82 | +0.08 / +1.24 | +0.13 / +0.04 | +0.05 / +0.13 | −0.07 / +0.47 |
| incumbent 22: ex10 / ex15 beat | 0.90 / 0.85 | 0.91 / 0.89 | 0.56 / 0.57 | 0.55 / 0.56 | 0.51 / 0.45 | 0.48 / 0.45 |
| − QQQ − XLK: score / full | −0.26 / +0.15 | +0.12 / +0.14 | −0.35 / −0.01 | −0.36 / +0.51 | −0.40 / +0.08 | −0.45 / +0.08 |

- On the incumbent menu the structure alone is worth about nothing on score: random picks under the
  identical execution, or simply holding the menu equally, score +0.05 to +0.13 with beat rates near
  0.5. The ~+0.8-0.9 lift of KX3/KX1 is the momentum signal.
- Without QQQ and XLK that lift shrinks to +0.09 (KX3) and +0.48 (KX1), and every rule, signal or not,
  loses to SPY on score. The signal's value on this menu runs largely through picking QQQ/XLK.
- RR3's +1.24 full-period excess (versus its +0.08 score) shows how much the single 2000-01 start is
  worth to any rule with a 379-day history requirement: the MDY/DIA/SPY portfolio it is forced into.

## 4. (c) Parameter neighbourhood (full protocol, CA, incumbent menu)

Execution knobs fixed (no trim, rank-ordered gain spending, proportional buys). Two sets:
- **one-at-a-time**: 19 variants each around KX3 and KX1: lookback 252/315/378/441/504, skip 0↔21,
  top_n 3/4/6/8 (buffer = N), cadence Q/S/A, budget 0.5/1/2%, hold buffer none/2/3/8/10, short-term
  gains on↔off;
- **random box**: 24 seeded random draws of all knobs at once: lookback 252-504, skip 0/21, top_n
  3-8, Q/S/A, budget 0.5-2%, buffer 0..2N, ST on/off.

`nb_full_CA.csv` has all 62.

| set | n | score mean (median) | score > 0 | full mean | full > 0 | pass 1-3 |
|---|---|---|---|---|---|---|
| around KX3 | 19 | +0.87 (+0.95) | 100% | +0.97 | 95% | 6 (32%) |
| around KX1 | 19 | +0.81 (+0.89) | 100% | +1.21 | 100% | 7 (37%) |
| random box | 24 | +0.68 (+0.70) | 96% | +0.80 | 88% | 6 (25%) |

- On this menu the positive score is a broad plateau. No knob matters much except annual rebalancing
  (box mean +0.36) and very large hold buffers (box, buffer 8-12: +0.34 to +0.59; one-at-a-time,
  buffer 10: +0.66 to +0.71).
- Clearing the confidence bar is not a plateau: only a quarter to a third of neighbours pass criteria
  1-3. The failures are on boot_p and ex15_beat, the two statistics tied to the chaotic 2000-01 path.
- Every neighbour shares the menu, so the plateau inherits everything in sections 2, 3 and 5.

## 5. (d) Pre-2000 holdout on pre-ETF analog menus

Menus reused unchanged from the sector_deep agent (pre-registered there before any run):
- **PRE20**: a category-for-category mutual-fund analog of the incumbent's 22 ETFs (VFINX, PRGFX,
  DODGX, VEXMX, NAESX, PRITX, VEIEX, VWNDX, VWUSX + 11 Fidelity Select / Vanguard REIT funds);
- **FSEL11**: the 11 sector funds of PRE20 (analog of the SPDR sectors);
- **FSEL32**: 28 Fidelity Select + 4 Vanguard sector funds.

Exact KX3/KX1 rules; benchmark VFINX; CA. Mutual funds cannot be traded at a NAV the order already
knows, so the primary runs use the 1-day lag (lag 0 shown for reference; it changes little).
`ho5`/`ho10` = windows ending before 2000 (the true holdout for an ETF-era design).

| menu | rule | protocol | score | full | ho5 (beat) | ho10 (beat) | ex10_beat | ex15_beat | boot_p | max DD (VFINX) |
|---|---|---|---|---|---|---|---|---|---|---|
| PRE20 | KX3 lag 1 | long | +1.12 | −0.22 | +0.52 (0.65) | +0.09 (0.59) | 0.69 | 0.84 | 0.58 | −52% (−55%) |
| PRE20 | KX3 lag 0 | long | +1.03 | −0.19 | +0.55 (0.65) | +0.12 (0.65) | 0.70 | 0.84 | 0.58 | −52% |
| PRE20 | KX1 lag 1 | long | +0.99 | +0.17 | +0.01 (0.51) | −0.03 (0.41) | 0.66 | 0.81 | 0.42 | −58% |
| PRE20 | KX1 lag 0 | long | +0.86 | +0.13 | +0.19 (0.57) | +0.12 (0.53) | 0.68 | 0.81 | 0.44 | −59% |
| FSEL11 | KX3 lag 1 | long | +1.18 | +0.02 | +0.63 (0.62) | −0.06 (0.41) | 0.76 | 0.87 | 0.45 | −56% |
| FSEL11 | KX1 lag 1 | long | +0.98 | +0.20 | +0.79 (0.62) | +0.24 (0.59) | 0.76 | 0.86 | 0.37 | −57% |
| FSEL32 | KX3 lag 1 | long | +1.27 | +0.39 | +0.32 (0.51) | **−1.91 (0.06)** | 0.69 | 0.77 | 0.33 | −48% |
| FSEL32 | KX1 lag 1 | long | +1.10 | −0.02 | +0.80 (0.57) | −0.39 (0.29) | 0.56 | 0.71 | 0.52 | −52% |

Controls on the same menus (protocol `long_screen`, yearly starts, lag 1, CA; KX rows repeated on the
same protocol for a like-for-like comparison; RR = mean of 3 seeds):

| menu | KX3 | KX1 | RR3 | RR1 | EWBH | EWTAX |
|---|---|---|---|---|---|---|
| PRE20 score / full / ho5 | +0.92 / −0.22 / +0.00 | +1.19 / +0.17 / +0.22 | +0.31 / −0.90 / −0.62 | +0.34 / −0.90 / −0.91 | +0.48 / +0.15 / −0.70 | +0.26 / −0.44 / −1.21 |
| FSEL11 score / full / ho5 | +1.17 / +0.02 / +0.64 | +1.08 / +0.20 / +0.57 | +0.72 / +0.79 / −0.62 | +0.70 / +0.74 / −0.52 | **+1.17 / +0.88 / +0.69** (boot_p 0.09) | +1.03 / +0.37 / +0.34 |
| FSEL32 score / full / ho5 | +1.37 / +0.39 / +1.43 | +1.16 / −0.02 / +1.50 | +1.36 / +0.61 / +1.22 | +1.53 / +0.32 / +1.34 | **+1.58 / +1.38 / +0.80** (boot_p 0.04) | +1.42 / +0.83 / +0.49 |

- **Nothing passes criteria 1-3 on any analog menu** (boot_p 0.33-0.58, ex10_beat 0.56-0.76). Against
  VFINX the true holdout is flat: on PRE20, KX3 ho5 +0.5 / ho10 +0.1, KX1 ho5 0.0 / ho10 0.0; on
  FSEL32, KX3's 10-year holdout windows lose 1.9 pp/yr and beat VFINX 6% of the time. This agrees with
  round 1's LONG_MENU result (KX3 ho5 −0.12, ho10 −0.23; KX1 −0.30 / −0.28).
- **The signal transfers to the broad analog menu, not to sector-only menus.** On PRE20 momentum beats
  random ranking by about +0.6-0.9 of score and +0.6-1.1 pp in the 5-year holdout. On FSEL11 and FSEL32
  it does not beat simply holding every sector fund equally: EWBH has the best score (tied on FSEL11),
  the best full-period excess and the best bootstrap p of every rule. On FSEL32 the rules' 5-year
  holdout is better than EWBH's, but their 10-year holdout is far worse (KX3 −1.04 on `long_screen`
  vs EWBH +1.09).
- Caveats that flatter every rule on the FSEL menus alike: the menus are survivors (merged Select
  funds are missing), and the 1980s-90s Fidelity Select 3% front loads and short-term redemption fees
  are not modelled.

## 6. (e) Concentration over time and where the excess comes from

One engine run from 2000-01-03 (CA), daily holdings recorded (`e_conc.py`, `e_conc_2000.json`).
Pre-tax arithmetic active return vs SPY is attributed to each holding as
w(t−1) × (r_fund − r_SPY); the groups add up to the portfolio's active return.

| year | KX3 names | KX3 top-3 share | KX3 eff. N | KX3 growth/tech weight | KX3 unrealized gain / value | KX1 top-3 share | KX1 growth/tech weight |
|---|---|---|---|---|---|---|---|
| 2000 | 3 | 1.00 | 3.0 | 0% | 2% | 1.00 | 0% |
| 2002 | 5 | 0.86 | 3.3 | 0% | −15% | 0.84 | 0% |
| 2005 | 8 | 0.74 | 3.8 | 20% | 28% | 0.55 | 16% |
| 2008 | 7 | 0.71 | 4.4 | 2% | 5% | 0.57 | 0% |
| 2010 | 7.5 | 0.62 | 5.3 | 22% | 35% | 0.57 | 22% |
| 2015 | 8 | 0.66 | 5.4 | 29% | 62% | 0.56 | 32% |
| 2020 | 8.5 | 0.65 | 5.4 | 43% | 80% | 0.61 | 42% |
| 2023 | 9 | 0.67 | 5.4 | 45% | 82% | 0.62 | 44% |
| 2026 | 9 | 0.71 | 4.9 | 54% | 87% | 0.70 | 57% |

(growth/tech = QQQ, XLK, IWF, XLC; full yearly table in `e_conc_2000.log`.) 2026 holdings: KX3 QQQ
33%, XLK 22%, MDY 18%, XLY 13%; KX1 XLK 32%, QQQ 25%, XLY 15%, XLV 9%.

Arithmetic active return vs SPY, pp/yr, by holding group:

| run | period | total | growth/tech | small/mid (MDY, IJR, IWM) | broad/value (SPY, DIA, RSP, IWD) | international | other sectors (incl. XLV) |
|---|---|---|---|---|---|---|---|
| KX3 from 2000 | 2000-2008 | +4.56 | −0.23 | **+2.80** | +0.64 | +0.48 | +0.87 |
| KX3 from 2000 | 2009-2026 | +0.87 | **+2.05** | −0.18 | −0.03 | −0.09 | −0.88 |
| KX1 from 2000 | 2000-2008 | +5.02 | −0.08 | **+2.29** | +0.78 | +1.02 | +1.01 |
| KX1 from 2000 | 2009-2026 | +0.74 | **+2.08** | −0.02 | −0.05 | −0.02 | −1.26 |
| KX3 from 2010 | 2010-2026 | +1.30 | **+1.94** | −0.06 | −0.22 | −0.28 | −0.08 |
| KX1 from 2010 | 2010-2026 | +1.61 | **+2.43** | −0.03 | +0.01 | −0.27 | −0.52 |

- The 2000-2008 lead is mostly the frozen MDY (and DIA) position bought because it was one of three
  eligible funds in January 2000, plus the 2003-2007 small/mid, materials, energy and emerging-market
  run.
- **From 2009 on, the growth/tech holdings supply more than all of the lead** (+2.0 to +2.4 pp/yr);
  every other holding together lags SPY by 0.6-1.3 pp/yr. Without QQQ/XLK-type winners the post-2009
  portfolio trails SPY.
- Concentration is high and rising: after 2009 the top three funds are 62-71% of KX3 and 53-70% of
  KX1, growth/tech reaches 54-57% by 2026, and 81-87% of the portfolio is unrealized gain. The rule cannot
  diversify out without a large tax bill: it is a frozen growth bet.

## 7. Battery (custom-kind versions of `verify.battery`)

`verify.battery` cannot shift boundaries or lag a custom kind, so `verify_taxrot_robust.ws` does it
(full protocol, CA unless noted; rows marked † use 500 bootstrap draws, the rest 1,000).

| test | KX3 | KX1 |
|---|---|---|
| headline (CA): score / full / ex10, ex15 beat / boot_p / max DD (SPY −55.2%) | +0.99 / +1.84 / 0.90, 0.85 / 0.011 / −53.7% | +0.93 / +1.82 / 0.91, 0.89 / 0.011 / −56.6% |
| headline (FED) | +1.10 / +1.94 / 0.90, 0.87 / 0.006 | +1.05 / +1.96 / 0.93, 0.91 / 0.009 |
| **scored from starts ≥ 2002-01** (`min_start`, CA) | +0.81 / +0.83 / 0.88, **0.82** / **0.173** / −58.2%: **fails 1-3** | +0.80 / +1.55 / 0.90, 0.87 / 0.051 / −58.9%: passes 1-3 |
| same, FED | +0.91 / +0.95 / 0.88, 0.85 / 0.151: fails | +0.91 / +1.72 / 0.92, 0.90 / 0.048: passes |
| boundary offset (days), score / full / boot_p † | 56: +0.74 / +1.10 / 0.104; 112: +0.95 / +0.87 / 0.192 (1 of 3 schedules passes) | 28: +0.70 / +0.54 / 0.29; 56: +0.38 / +0.41 / 0.32 (1 of 3 passes) |
| round 1's month offsets (`reb_offset`) | 6 schedules: score +0.68 to +1.09, 3/6 pass | 3 schedules: +0.57 to +0.93, 1/3 pass |
| 1-day execution lag, CA / FED † | +1.09 / +1.53, boot_p 0.056 / FED +1.22 / +1.64: pass | +1.02 / +1.83, 0.036 / FED +1.15 / +1.96: pass |
| costs per side 0 / 15 / 35 bps (score) † | +1.02 / +0.96 / +0.88 | +0.97 / +0.86 / +0.74 |
| costs 0 / 15 / 35 bps (full_excess, boot_p) † | +1.82 (0.022) / **+0.46 (0.34)** / +0.97 (0.17) | +1.85 (0.014) / **+0.91 (0.18)** / +0.79 (0.20) |
| annual distribution tax (realism), excess engine → real, CA, from 2000 / 2005 / 2010 / 2015 | +1.84 → +1.90 / +0.90 → +0.93 / +0.95 → +1.00 / +1.99 → +2.00 | +1.82 → +1.86 / +1.24 → +1.27 / +1.12 → +1.18 / −0.13 → −0.12 |
| sub-periods, CA (fresh start; pp/yr): 2000-10 / 2010-20 / 2020-26 | +2.93 / +0.89 / −0.40 | +3.57 / +0.74 / −0.64 |
| 5-year windows starting 2019 or later (11), CA | mean −2.74, beat 18% | mean −2.78, beat 9% |
| deflated Sharpe, ~12,000 configs tried (CA / FED) | **0.038** / 0.048 (PSR 0.988) | **0.051** / 0.065 (PSR 0.990) |

- **The single 2000-01 path is chaotic.** `full_excess` and `boot_p` both come from that one run, and
  immaterial perturbations move them a lot. Going from 5 to 15 bps per side costs about 0.01 pp/yr
  directly (turnover is 5-7% a year), yet it cuts KX3's full-period excess from +1.84 to +0.46 and
  KX1's from +1.82 to +0.91; a 4-8-week boundary shift does the same. A slightly different trade
  early on freezes a different portfolio for the next 20 years. The 95-start score is far more
  stable (+0.7 to +1.0).
- Distribution-tax realism, the 1-day lag and costs up to 35 bps barely move the score. The candidates
  are not fragile to execution realism; they are fragile to timing, start date, menu and multiple
  testing.
- **Deflated Sharpe 0.04-0.05**: after accounting for ~12,000 configurations tried, the after-tax
  monthly excess is not distinguishable from the best of many noise strategies.

## 8. Signal, structure or regime luck?

Decomposition on the incumbent menu (full protocol, CA, score):

| component | how measured | score |
|---|---|---|
| hold the menu, no selection, no trading | EWBH | +0.05 |
| + the KX execution with random picks (structure) | RR3 / RR1 | +0.08 / +0.13 |
| + momentum ranking (signal) | KX3 / KX1 | +0.99 / +0.93 |
| the same, menu without QQQ and XLK | EWBH, RR, KX3, KX1 | −0.40, −0.35, −0.26, +0.12 |

- **Signal: real, but narrow.** Momentum beats random selection under the same execution on the
  incumbent menu (+0.8-0.9), on 30 menus nobody chose (+0.7-0.8, t 5.7-7.2), and on the pre-ETF broad
  analog PRE20 (+0.6-0.9; 5-year holdout +0.6-1.1). It does not beat equal weight on sector-only
  menus (FSEL11/FSEL32). Its size scales with how much tech the menu contains (KX3 − RR3: +0.05 to
  +0.2 with no tech fund, +1.0 to +1.2 with three), and on the incumbent menu it runs largely through picking QQQ/XLK (lift +0.09 /
  +0.48 without them).
- **Structure: necessary, not sufficient.** The no-trim, rank-ordered, tax-budgeted execution is what
  lets a rotation survive 48%/28% taxes (round 1: plain rotations lose after tax), and it has very
  low turnover. On its own (random picks) it is worth about zero versus simply holding the menu.
- **Regime luck: the lead over SPY.** The +1.8 pp after-tax full-period excess comes from two
  regimes (pre-tax attribution, section 6):
  - +4.6-5.0 pp/yr of active return in 2000-2008: largely an MDY/DIA position forced by ETF launch
    dates at the dot-com peak, then never trimmed;
  - +0.7-0.9 pp/yr in 2009-2026: entirely frozen QQQ/XLK (growth/tech +2.0 pp/yr, everything else
    −1.2 to −1.3 pp/yr).

  Fresh starts since 2019 lose 2.7-2.8 pp/yr over five years. The pre-2000 holdout, a different
  regime, is flat against the index.
- **Bottom line.** The rule converts a real but modest selection signal into a concentrated,
  tax-locked bet on whatever led when it bought. From 2000 to 2026 that happened to be mid caps and
  then US mega-cap growth.

## 9. The most robust design

- Of the two, **KX1 is the more robust**:
  - it still passes criteria 1-3 when scored only from 2002 on (KX3 does not: ex15_beat 0.82,
    boot_p 0.17);
  - it loses less without QQQ (+0.50 vs +0.30) or without both (+0.12 vs −0.26);
  - it has the better full-period excess on random menus (+0.70, positive on 87% of menus, vs +0.16,
    60%).
- KX3 is less sensitive to the rebalance date (score +0.74 to +0.99 across offsets vs +0.38 to +0.93)
  and holds up slightly better on PRE20 (5-year holdout +0.5 vs 0.0).
- Neither survives the tests that matter for "good confidence": hindsight removal, random menus, the
  pre-2000 holdout, and deflated Sharpe.
- No neighbour or fix changes that. Every neighbour lives on the same menu, and the failures are
  menu and regime failures, not tuning failures.
- What to keep from this work:
  - The **execution** (keep winners within the top 2N, never trim, spend the gain budget on the
    worst-ranked first, long-term gains only) is a strict improvement over the site's incumbent
    preset on every test here and in round 1.
  - It should be presented as a tax-efficient momentum tilt with a growth-regime bet and an expected
    edge near zero, not as a way to beat the S&P 500 with confidence.
  - Anyone using it must accept 50-60% growth/tech concentration that cannot be unwound without a
    large tax bill, and five-year stretches of 2-3 pp/yr underperformance.

## 10. Notes for the lab (no lab file edited)

1. **Rotation rules need an eligibility guard like `requires`.** PROTOCOL 4 guards fixed mixes
   against late-launch funds. A rotation whose history requirement leaves 3 of 22 funds eligible at
   the first start gets an unearned first window, and that window supplies `full_excess` and the
   bootstrap. Suggest reporting statistics from the first start at which (say) 80% of the menu is
   eligible: `win_stats(rec, min_start)` in `scratch/verify_taxrot_robust/h.py`, or a `min_start`
   in the cfg.
2. **Single-path statistics are chaotic for frozen-portfolio rules.** `full_excess` and `boot_p` come
   from one path. 15 instead of 5 bps per side, or a 4-week boundary shift, moves them by up to
   1.4 pp and from p 0.01 to 0.34. For low-turnover tax-managed rules, average them over boundary
   offsets before applying the bar.
3. **Cache key gap.** `registry.code_version` hashes only the kind's own source file for custom
   kinds. A kind that subclasses another family's class or uses another family's signal (as this
   module does with `tax_rotation.TRStrategy` / `tax_rotation.rank`) would keep stale cached
   results if that other module changed. Harmless here (tax_rotation.py was not edited during these
   runs), but worth fixing by hashing `SIGNALS[cfg["signal"]][2]` for every kind.
4. `verify.battery` offsets and lag support only `weights`/`combo`; `verify_taxrot_robust.ws` adds
   both for `tax_rotation.ws` configs (identical results at offset 0 / lag 0).
