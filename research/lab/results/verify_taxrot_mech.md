# Verification: tax-managed rotation KX3 / KX1 (mechanics, bugs, execution realism)

Verifier key `taxrot_mech`. Module `research/lab/families/verify_taxrot_mech.py` (kind
`verify_taxrot_mech.ws_x`). Scripts, logs and JSON in `research/lab/scratch/verify_taxrot_mech/`.
All numbers are lab-engine numbers (the website's engine). "Excess" = after-tax CAGR minus SPY
buy-and-hold, same regime and costs (0.01 = 1 pp/yr). CA = 48.1% / 28.1% (primary), FED = 35% / 15%.

Candidates (exact configs from `scratch/_lead/r1/verify_candidates.json`):

- **KX3**: 378-0 momentum, top 5, semiannual (S), 1% gain budget, keep-in-top-2N (`hold_buffer=5`),
  `trim=false`, `gain_order="rank"`, proportional buys.
- **KX1**: 252-21 momentum, top 5, quarterly (Q), 2% budget, long-term gains only, same K-execution.
- Comparator **INC**: the site preset (combo TaxManagedCombo momentum 252/21, top 5, Q, 1% budget,
  the 22-ETF menu).

## Verdict

**KX3: fail. KX1: fail.** Neither is recommendable as "beats SPY after tax with good
confidence". The mechanics are clean. The headline numbers are not.

**What held:**
- **The code does what the label says.**
  - keep-in-top-2N, no trims, worst-ranked-first gain spending and long-term-only (KX1) all
    re-derive exactly from the trade log.
  - It trades only through `ctx.order` and never buys with cash it does not have.
  - The gains it predicts equal the gains the engine books (to 1e-12).
  - A wash sale is impossible at an S/Q cadence: 0 of 99 loss lots were rebought within 30 days.
  - **No look-ahead:** clipping all data at three dates reproduces every earlier order exactly.
- **The 95-window statistics are robust to execution details.**
  - KX3's score stays +0.88 to +1.09 under a 1-day lag, costs 0-35 bps, skipping small trades
    and the budget fix.
  - Every one of 26 weekly rebalance offsets has a positive score (mean +0.94, min +0.65) and a
    positive full-period excess.
  - Stricter tax accounting (annual dividend tax) helps slightly (+0.03 to +0.06 pp).

**What broke:**
1. **The full-period result and its significance are path luck.**
   - The partial gain sale is sized on the average gain, so the 1% budget is overshot in 18 of 25
     years. The site's TaxManagedCombo has the same approximation.
   - Sizing it exactly on FIFO lots leaves KX3's score unchanged (+0.95). But at the default
     date, full_excess falls from **+1.84 to +0.31** and boot_p rises from **0.011 to 0.40**.
   - One 2004 partial sale sends the 2000-start path to a QQQ-light book worth 31% less in 2026.
   - Across 26 weekly offsets, the default date ranks 3rd on full_excess (median +1.00). boot_p is
     <= 0.10 at only 12 of 26 offsets, and criteria 1-3 hold at only **9 of 26** (KX1: 4 of 13).
2. **Multiple testing.** Deflated Sharpe at 12,000 trials:
   - KX3 **0.038** (CA) / 0.048 (FED);
   - KX1 0.051 / 0.065;
   - below 0.5 even if the search were only 100 independent trials.
3. **Not detectably better than the site preset.**
   - Paired monthly difference from 2000: KX3 - INC +0.28 pp/yr, p = 0.38.
   - Averaged over offsets, the full-period excess is identical (+1.18 vs +1.18).
   - KX3 loses to INC in 78% of 20-year windows.
   - KX3's real gain is the 5-15-year beat rate (10y beat 0.88 vs 0.68 across offsets).
4. **Era and holdout.**
   - 2020-26 fresh-start excess is -0.40 pp (KX3) and -0.64 pp (KX1).
   - 5-year windows starting 2020/2021 lose 3.2 / 4.8 pp/yr.
   - The pre-2000 mutual-fund holdout is negative (reproduced from round 1).
   - Round 1's hindsight test (no QQQ/XLK, random menus) already fails.
5. **Untested concentration.**
   - The frozen 2026 books are 56-82% growth/tech, with 76-87% of value as unrealized gain.
   - Replaying the 2000-02 bust on those books loses 56-71% vs SPY -47.5%.
   - A 1% budget cannot de-risk them.

Fixed variant (label-faithful budget):
`{"kind": "verify_taxrot_mech.ws_x", ..., "exact_budget": true}` (section 6). It is not better:
its average over offsets equals the original's, and it removes KX3's lucky default-date path.

## 1. Code audit (`families/tax_rotation.py`, kind `tax_rotation.ws`, signal `tax_rotation.rank`)

Read line by line against `blocks.WeightStrategy`, the engine (`backtester/engine.py`,
`portfolio.py`) and the site's `TaxManagedCombo`.

| question | finding |
|---|---|
| Trades only through `ctx.order`? | Yes. `_tax_sells`, `_buys` (and the unused `_harvest`, `max_weight` trim) all call `ctx.order`; lots, realized gains, cash, the annual tax settlement and the terminal tax are the engine's own. The `_ShadowCtx` proxy is only active with `shadow` in an untaxed run (not used by KX1/KX3). |
| Look-ahead? | None found. Scores read `np_closes` (rows up to and including today via `rows_upto(..., side="right")`); orders fill at today's close. Same-close signal-and-fill is the engine convention; the 1-day-lag test (section 4) removes it. |
| keep-in-top-2N | `keep = [held names ranked in the top N+buffer][:N]`, then fill with the best-ranked non-kept names. Matches the label. Note: "held" includes residual positions left by a budget-limited partial exit, so such a name is kept (and topped back up to 1/N) while it ranks 6-10. |
| no-trim | `trim=False` skips any sell of a name whose target is > 0. Only exits are sold. |
| worst-ranked-first gain spending | Sort key `(is_gain, is_short, -rank if gain else 0, gain, ticker)`: losses first (largest first), then long-term before short-term gains, then the worst-ranked name first; unranked = worst. Matches the label. |
| LT-only (KX1) | `st_gains=False` skips a candidate if any lot sold would be short-term **and** the sale is a net gain. A net-loss exit is always sold, so a short-term-gain lot can be realized inside a net-loss sale (2 lots in the 2000 run, 1 in the 2007 run, all inside net-loss exits; the yearly short-term net is <= 0 except +$13 in one year). Not a violation. |
| Wash sales | Buys are blocked for 31 days after a loss sale of the same name (or an identical-index group). Because trading happens only on S/Q rebalance days (>= 3 months apart) and a name is never both sold and bought on one day, a wash sale cannot occur in either direction. The 22-ETF menu has no substantially identical pair. |
| Buys exceeding cash | Proportional buys are scaled to `ctx.cash / need * 0.999999`; the engine never had to cap a KX buy. |
| Partial-sale sizing | **Deviation from the label (shared with the site's TaxManagedCombo):** the last, budget-limited gain sale sells `qty * room / gain`, i.e. it assumes the position's *average* gain per share, but the engine sells FIFO (oldest, lowest-basis lots first). The realized gain therefore overshoots the budget. Quantified in sections 2 and 6 (variant `exact_budget`). |
| Tax paid from cash | The engine deducts last year's tax from cash on the first trading day of January, before the strategy runs; with no sale that day cash goes negative (an interest-free loan). Measured in section 2: absent for KX3, rare and tiny for KX1. |

## 2. Instrumented trade-log audit (`a1_audit.py`, `a2_stlots.py`, `a3_keep.py`)

Each order, each FIFO lot closed and each rebalance (targets, ranking, held set, budget room) was
logged for single runs starting 2000-01, 2007-07 and 2015-04 (CA; 2000-01 also FED), and every
rebalance was re-derived independently.

| check | KX3 (2000-01 start, CA) | KX1 (2000-01 start, CA) |
|---|---|---|
| rebalances / trades / trade dates | 54 / 224 / 42 | 107 / 279 / 52 |
| target set != independent keep-in-top-2N rule | 0 | 0 |
| sells of a name still wanted (trim) | 0 | 0 |
| sell sequence out of order (loss, LT, ST, worst rank first) | 0 | 0 |
| buys of unwanted names / sell and buy same name same day | 0 / 0 | 0 / 0 |
| buys capped by the engine (requested > filled) | 0 | 0 |
| predicted gain vs engine-booked gain, full exits | max abs diff 4e-12 | 4e-12 |
| loss lots / buys of that name within +-30 days (wash sales) | 39 / **0** | 60 / **0** |
| short-term-gain lots in an LT-only rule | n/a | 2 (both inside net-loss exits) |
| days with negative cash | 0 (min cash +1.6e-9 of PV) | 0 (2015-04 start: 371 of 2,829 days, min -0.54% of PV) |
| years whose net realized gain exceeds the budget | **18 of 25** (max 1.32x, 2017) | **16 of 26** (max 1.21x) |
| cumulative realized gain above budget, 2000-2026 | 1.6% of PV in total (~0.06% of PV a year) | 1.8% of PV |
| largest partial-sale overshoot | room $1,358, realized $2,445 (2010-01-04) | room $4,957, realized $6,499 (2014-01-02) |
| trades < $100 / < 0.1% of PV / < 0.5% of PV | 6 / 24 / 95 (proportional top-ups) | 12 / 39 / 104 |
| orders below the engine's $1 minimum (dropped) | 42, all buys worth <= $0.05 | 221, all buys worth <= $0.05 |
| largest single trade | 33% of PV: the 2000-01-03 start buys SPY, DIA, MDY at 1/3 each (the only menu funds with 379 days of history) | 33% (same) |
| max names held / rebalances with an unsellable (frozen) exit | 10 / 45 of 54 (mean 2.8 frozen names) | 10 / 93 of 107 |
| held names kept while ranked 6-10 | 75 times | 153 times |
| 2026 book | QQQ 33%, XLK 23%, MDY 18%, XLY 13%; unrealized gain 87% of value | XLK 32%, QQQ 25%, XLY 15%; 81% |

Same pattern for the 2007-07 and 2015-04 starts and in FED (`a1_audit.json`). The incumbent
expressed as WS with alphabetical buys (`buy_order="alpha"`) behaves like the site: engine-capped
buys and dropped orders once cash runs out, by design.

**Look-ahead (truncation) test.** Re-running with every price file clipped at 2003-02-14,
2012-01-04 and 2020-03-20 reproduces every order up to the cut exactly (KX3 22 / 122 / 200 orders,
KX1 38 / 229 / 392, incumbent-as-WS 76 / 298 / 462). Nothing reads data after the trade's close.

**Data sanity** (22 menu files): no duplicate dates, no non-positive or missing closes; largest
daily move 22.8% (EEM, 2008); six zero-volume bars (XLRE 5, XLI 1) that the engine treats as
untradable.

**What the audit found:**

- **No bug that inflates the result.** The execution does what the label says. It trades only
  through `ctx.order`, never buys with cash it does not have, cannot wash-sale, and uses no
  future data.
- **One accounting deviation: the "1% budget" is really about 1.06% on average.** The
  budget-limited partial sale is sized on the average gain per share, but FIFO realizes the
  oldest, lowest-basis lots first. KX3 overshot its 1% budget in 18 of 25 years, by up to 32%.
  The site's TaxManagedCombo has the same approximation. The `exact_budget` variant (section 6)
  sizes the sale on the actual FIFO lots. On average over rebalance offsets the fix is neutral.
  On the default dates, though, it moves KX3's 2000-start full-period excess from +1.84 to +0.31
  pp/yr: the overshooting path happens to be the lucky one.
- **Negative cash is not a factor.** It never occurs in KX3. In KX1 it is rare and below 0.6% of
  PV: an interest-free loan worth under 0.01 pp/yr.
- **Dust trades are harmless.** 40% of KX3's trades are top-ups below 0.5% of PV. Costs are
  proportional in the engine, so they cost nothing extra. A real investor would skip them; the
  `min_trade_frac` variants (section 6) show the effect.

## 3. Reproduction

`sweep.run` of the exact round-1 configs on `full` reproduces every reported statistic to the 4th
decimal in CA, FED and NONE (score, full_excess, beat rates, boot_p, max_dd, trades, turnover). An
independent fresh run of KX3 through my kind with no shift (`ws_x`, offset 0, lag 0) reproduces
it exactly: score 0.0099, full 0.0184, 224 trades. Fresh KX1 runs at offset 0 match as well
(CA 0.0093 / 0.0182). So the cached records are not affected by the cache-poisoning issue that
round 1 reported. The instrumented single runs (section 2) also reproduce the trade counts (224 /
279).

The cached long-protocol records (LONG_MENU proxies, VFINX benchmark, CA) still give round 1's
numbers:

| | full | ho5 mean | ho10 mean | ho10 beat |
|---|---|---|---|---|
| KX3 | -0.34 | -0.12 | -0.23 | 0.24 |
| KX1 | -0.54 | -0.30 | -0.28 | 0.47 |

## 4. Battery

`verify.battery(cfg, n_trials=12000)` for the full protocol, costs, stricter tax accounting,
sub-periods and the deflated Sharpe ratio (DSR). The battery cannot shift or lag a custom kind, so
rebalance offsets and the 1-day lag ran through `verify_taxrot_mech.ws_x`. Offsets use the
battery's definition: every period boundary is shifted by N calendar days, and N steps through
every week of the period (KX3: 26 offsets 0-175 days; KX1 and the incumbent: 13 offsets 0-84 days;
CA). NONE uses the battery's own grid.

**Headline (full protocol, quarterly starts 2000-2023).** In CA, the KX3 boot_p is 0.016 with the
battery's 500 resamples and 0.011 with 1,000.

| | regime | score | full | 10y mean | 10y beat | 15y beat | 20y beat | boot p | max DD (SPY -55.2%) | after-tax IR |
|---|---|---|---|---|---|---|---|---|---|---|
| KX3 | CA | +0.99 | +1.84 | +1.17 | 90% | 85% | 96% | 0.011 | -53.7% | 0.42 |
| KX3 | FED | +1.10 | +1.94 | +1.30 | 90% | 87% | 100% | 0.006 | -53.7% | 0.44 |
| KX1 | CA | +0.93 | +1.82 | +1.07 | 91% | 89% | 96% | 0.011 | -56.6% | 0.45 |
| KX1 | FED | +1.05 | +1.96 | +1.20 | 93% | 91% | 100% | 0.009 | -56.3% | 0.47 |
| INC | CA | +0.66 | +1.54 | +0.55 | 70% | 83% | 100% | 0.026 | -56.6% | 0.28 |
| INC | FED | +0.74 | +1.60 | +0.63 | 69% | 85% | 100% | 0.020 | -56.6% | 0.29 |

(pp/yr; score = mean of the 5/10/15-year average excess.)

**Rebalance-timing luck (CA, every weekly boundary shift).** "Pass" means criteria 1-3.

| | offsets | score mean (median) [min, max] | full_excess mean (median) [min, max] | 10y beat mean [min] | 15y beat mean [min] | boot_p mean [max]; share <= 0.10 | pass 1-3 | default date's rank (score / full) |
|---|---|---|---|---|---|---|---|---|
| KX3 | 26 | **+0.94** (0.95) [+0.65, +1.27] | +1.18 (1.00) [+0.48, +2.42] | 0.88 [0.79] | 0.88 [0.74] | 0.12 [0.31]; 46% | **9 / 26** | 9th / **3rd** |
| KX1 | 13 | +0.76 (0.74) [+0.38, +1.13] | +1.14 (0.97) [+0.23, +2.85] | 0.82 [0.63] | 0.82 [0.66] | 0.16 [0.41]; 31% | **4 / 13** | 4th / 3rd |
| INC | 13 | +0.61 (0.63) [+0.35, +0.88] | +1.18 (1.38) [+0.50, +1.89] | 0.68 [0.57] | 0.84 [0.79] | 0.10 [0.27]; 69% | 0 / 13 | 5th / 4th |

- Every offset of every rule has a positive score and a positive full_excess.
- KX3's score is not a timing artefact. The default ranks 9th of 26, and KX3's worst offset
  (+0.65) is about the incumbent's average.
- KX3's **full-period excess and its bootstrap significance are timing-lucky:**
  - the default is the 3rd-best of 26 offsets;
  - the median offset gives +1.00 against the headline +1.84;
  - boot_p is above 0.10 at 14 of the 26 offsets;
  - only 35% of offsets clear criteria 1-3.
- KX1 is worse on every count.
- NONE (battery grid, 7 offsets; a diagnostic only, because untaxed runs keep no lots and the
  rules become plain rotations):

  | | score mean [min, max] | full mean | 10y beat | pass 1-3 |
  |---|---|---|---|---|
  | KX3 | +1.06 [+0.62, +1.47] | +1.62 | 0.71 | 2 / 7 |
  | KX1 | +0.94 [+0.71, +1.33] | +1.77 | 0.56 | 0 / 7 |
  | INC | +0.42 [-0.38, +0.88] | +0.88 | 0.42 | 0 / 7 |

**One-day execution lag** (targets from today's close, traded at tomorrow's close; full protocol):

| | regime | score | full | 10y beat | 15y beat | boot_p | pass 1-3 |
|---|---|---|---|---|---|---|---|
| KX3 lag 1 | CA | +1.09 | +1.53 | 0.91 | 0.87 | 0.053 | yes |
| KX1 lag 1 | CA | +1.02 | +1.83 | 0.88 | 0.94 | 0.020 | yes |
| INC (as WS, alphabetical buys) lag 1 | CA | +0.70 | +1.85 | 0.70 | 0.87 | 0.017 | no |
| KX3 lag 1 | FED | +1.22 | +1.64 | 0.93 | 0.87 | 0.040 | yes |
| KX1 lag 1 | FED | +1.15 | +1.96 | 0.88 | 0.94 | 0.018 | yes |
| KX3 / KX1 / INC lag 1 | NONE | +1.04 / +0.78 / +0.12 | +1.75 / +1.81 / +0.99 | 0.69 / 0.48 / 0.42 | | | no |

A same-close signal-and-trade is not the source of the edge. A one-day delay is noise of the same
size as the offsets. As a WS config with alphabetical buys, the incumbent reproduces the site combo
exactly (0.0066 / 0.0154 / 295 trades).

**Costs per side** (commission and slippage each; site default 5 bps). Score in CA, with
full_excess in brackets:

| | 0 bps | 5 bps | 15 bps | 35 bps |
|---|---|---|---|---|
| KX3 | +1.02 (+1.82) | +0.99 (+1.84) | +0.96 (+0.46) | +0.88 (+0.97) |
| KX1 | +0.97 (+1.85) | +0.93 (+1.82) | +0.86 (+0.91) | +0.74 (+0.79) |
| INC | +0.70 (+1.57) | +0.66 (+1.54) | +0.39 (+1.04) | +0.37 (+1.10) |

- The score is robust to costs because turnover is only 0.05-0.07 a year.
- The single-path full_excess is not monotone in cost. KX3 drops from +1.84 to +0.46 at 15 bps
  and recovers to +0.97 at 35 bps. A threshold flip, such as a near-zero position classed as a
  loss instead of a gain, sends the 2000-start path elsewhere.
- **Path sensitivity:** nudging costs to 4, 4.5, 5.5 or 6 bps leaves every number unchanged
  (KX3 full 1.843-1.844, score 0.985-0.986).
- **Skipping small trades** (`min_trade_frac` 0.5% / 1% of PV) moves KX1's full_excess from
  +1.82 to +2.50 / +2.57.
- So any one full-period number carries about ±1 pp/yr of path luck. The 95-window averages
  (score, beat rates) are the stable statistics.

**Stricter tax accounting** (`realism`: annual tax on distributions, basis credit). Engine ->
stricter excess, CA:

| start | KX3 | KX1 | INC |
|---|---|---|---|
| 2000 | +1.84 -> +1.90 | +1.82 -> +1.86 | +1.54 -> +1.60 |
| 2005 | +0.90 -> +0.93 | +1.24 -> +1.27 | +2.30 -> +2.32 |
| 2010 | +0.95 -> +1.00 | +1.12 -> +1.18 | +0.04 -> +0.10 |
| 2015 | +1.99 -> +2.00 | -0.13 -> -0.12 | -0.10 -> -0.06 |

The rotations hold lower-yield funds than SPY, so the engine's deferred taxation of dividends
slightly understates them. There is no bond or gold sleeve.

**Sub-periods** (fresh start at each boundary, pp/yr):

| | regime | 2000-10 | 2010-20 | 2020-26 |
|---|---|---|---|---|
| KX3 | CA | +2.93 | +0.89 | **-0.40** |
| KX3 | FED | +3.30 | +0.98 | -0.42 |
| KX1 | CA | +3.57 | +0.74 | **-0.64** |
| INC | CA | +1.20 | -0.55 | +0.19 |

Five-year windows starting in 2020 and 2021 average:

| | 2020 starts | 2021 starts |
|---|---|---|
| KX3 | -3.2 pp/yr | -4.8 pp/yr |
| KX1 | -3.4 pp/yr | -3.2 pp/yr |
| INC | -2.9 pp/yr | -2.8 pp/yr |

**Deflated Sharpe** of the monthly after-tax excess from the 2000 start (319 months; Bailey-Lopez de
Prado with trial variance 1/T):

| | after-tax excess Sharpe (annual) | PSR (1 trial) | DSR 100 trials | DSR 1,800 (round-1 family size) | DSR 12,000 (whole search) |
|---|---|---|---|---|---|
| KX3 CA | 0.42 | 0.988 | 0.36 | 0.10 | **0.038** |
| KX3 FED | 0.44 | 0.990 | 0.40 | 0.12 | 0.048 |
| KX1 CA | 0.45 | 0.990 | 0.41 | 0.13 | **0.051** |
| KX1 FED | 0.47 | 0.992 | 0.45 | 0.15 | 0.065 |
| INC CA | 0.28 | 0.925 | 0.15 | 0.03 | 0.009 |

An after-tax information ratio of about 0.43 over 26.6 years is significant on its own (PSR
0.99). It is nowhere near significant once the search is accounted for: the DSR is below 0.5 even
if the 12,000 correlated configs amounted to only 100 independent trials.

## 5. KX3 / KX1 versus the incumbent preset

**Is KX3 better on average across rebalance offsets, or only on the default date?** It depends
on the statistic. Mean over all weekly offsets, CA:

| | score | full_excess | 10y beat | 15y beat | boot_p | pass 1-3 |
|---|---|---|---|---|---|---|
| KX3 | +0.94 | +1.18 | 0.88 | 0.88 | 0.12 | 35% |
| INC | +0.61 | +1.18 | 0.68 | 0.84 | 0.10 | 0% |
| KX3 - INC | **+0.33** | **0.00** | +0.20 | +0.04 | worse | |

- **Genuinely better, in every offset:** the 5-15-year window statistics. The 10y beat rate is
  0.79-0.96 against the incumbent's 0.57-0.85. This is the K-execution: winners are not trimmed,
  and held funds are kept while they rank 6-10.
- **Not better on average:** the full-period after-tax excess and its significance. KX3's
  default-date lead in full_excess (+1.84 vs +1.54) is offset luck.

**Paired, window by window** (default dates, same 95 starts; `c2_paired.json`). KX3 minus INC, CA:

| windows | mean | share of windows KX3 is better |
|---|---|---|
| 5-year | +0.22 pp | 54% |
| 10-year | +0.62 pp | 70% |
| 15-year | +0.15 pp | 55% |
| 20-year | **-0.32 pp** | **22%** |
| to 2026 | +0.17 pp | 53% |

- KX1 minus INC: +0.17 / +0.52 / +0.14 / -0.11 / +0.11 pp, better in 48% / 67% / 64% / 52% / 51%
  of windows.
- Stationary bootstrap of the monthly difference from the 2000 start: KX3 - INC +0.28 pp/yr,
  **p = 0.38**; KX1 - INC +0.25 pp/yr, p = 0.39.
- On the 2010-2026 part of that path, KX3 trails the incumbent (-0.59 pp/yr, p(> 0) = 0.95), and
  so does KX1 (-1.00, 0.99).
- **There is no statistically detectable improvement over the site preset.**

**Concentration risk the backtest never tested.**
- The K-execution freezes winners. By 2026 the books are 56-82% QQQ / XLK / IWF / XLY, with 76-87%
  of value as unrealized gain:

  | start | QQQ | XLK | other large holdings |
  |---|---|---|---|
  | 2000 | 33% | 23% | MDY 18% |
  | 2015 | 27% | 39% | IWF 16% |

- The 1% budget cannot de-risk such a book. Exiting QQQ alone would realize about 29% of PV in
  gains, or decades of budget.
- Replaying past crashes on the 2026 books (fund total returns over each crash; `a5_stress.py`):

  | crash | SPY | 2000-start book | 2015-start book |
  |---|---|---|---|
  | 2000-03 to 2002-10 | -47.5% | -56% | -71% |
  | 2007-10 to 2009-03 | -55% | -52% | -54% |
  | 2021-11 to 2022-10 | -23% | -29% | -32% |

- The backtest's max drawdown (-54%, versus SPY -55%) comes from 2008, when the book was
  diversified. It says nothing about a tech bust hitting a frozen growth book.

## 6. Variants tried (all reported)

### Exact budget: the label-faithful fix

`exact_budget=True` sizes the budget-limited partial sale on the FIFO lots that will actually be
sold, so the year never exceeds 1% (or 2%) of PV. Everything else is unchanged.

| | regime | score | full | 10y beat | 15y beat | 20y beat | boot_p | max DD | pass 1-3 |
|---|---|---|---|---|---|---|---|---|---|
| KX3 (as reported) | CA | +0.99 | +1.84 | 0.90 | 0.85 | 0.96 | 0.011 | -53.7% | yes |
| **KX3 exact budget** | CA | **+0.95** | **+0.31** | 0.90 | 0.85 | 0.81 | **0.40** | -54.3% | **no** |
| KX3 exact budget | FED | +1.07 | +0.38 | 0.90 | 0.85 | 0.89 | 0.37 | -54.3% | no |
| KX3 exact, 7 offsets (0-168 d) | CA | mean +0.93 [+0.74, +1.16] | mean +0.83 [+0.29, +1.79] | | | | 0.02-0.40 | | 1 / 7 |
| KX3, the same 7 offsets | CA | mean +0.94 | mean +1.15 | | | | | | 2 / 7 |
| KX3 exact, lag 1 | CA | +1.06 | +1.54 | 0.90 | 0.87 | 0.78 | 0.053 | -56.2% | yes |
| KX1 (as reported) | CA | +0.93 | +1.82 | 0.91 | 0.89 | 0.96 | 0.011 | -56.6% | yes |
| KX1 exact budget | CA | +0.92 | +1.76 | 0.90 | 0.91 | 0.96 | 0.015 | -56.6% | yes |
| KX1 exact budget | FED | +1.04 | +1.90 | 0.91 | 0.91 | 0.96 | 0.011 | -56.3% | yes |
| KX1 exact, 7 offsets (0-84 d) | CA | mean +0.78 [+0.38, +1.02] | mean +0.94 [-0.07, +1.77] | | | | 0.015-0.55 | | 2 / 7 |
| KX1, the same 7 offsets | CA | mean +0.78 | mean +0.95 | | | | | | 2 / 7 |
| KX1 exact, lag 1 | CA | +0.99 | +1.85 | 0.88 | 0.94 | 1.00 | 0.016 | -56.7% | yes |

- **On average the fix changes nothing.** Over the offsets, the score is identical and the full
  excess is within noise.
- **For KX3 it moves the headline path a lot** (`a4_exact_path.py`):
  - The two runs first differ on 2004-07-01, by one partial XLF sale.
  - That cascades through which funds are "held" and therefore kept.
  - In 2009, the reported path rotates into QQQ; the exact path does not.
  - The reported path ends 2026 holding 33% QQQ; the exact path holds 14% QQQ and 29% MDY.
  - The reported path's terminal after-tax wealth is 46% higher ($968k vs $664k on $100k).
- **The +1.84 / p = 0.011 headline is one lucky trajectory of a chaotic, path-dependent rule.**
  It is not a property of the rule. The 95-window averages are the meaningful statistics: score
  about +0.93 to +0.99, 10y beat about 0.9.

### Other variants

| variant | regime | score | full | 10y beat | 15y beat | boot_p | pass 1-3 |
|---|---|---|---|---|---|---|---|
| KX3, skip trades < 0.5% of PV | CA | +1.01 | +1.84 | 0.91 | 0.89 | 0.011 | yes |
| KX3, skip trades < 1% of PV | CA | +1.01 | +1.92 | 0.90 | 0.89 | 0.009 | yes |
| KX1, skip trades < 0.5% of PV | CA | +0.98 | +2.50 | 0.93 | 0.89 | 0.001 | yes |
| KX1, skip trades < 1% of PV | CA | +1.01 | +2.57 | 0.93 | 0.89 | 0.000 | yes |
| KX3, skip < 0.5% / < 1% | FED | +1.13 / +1.13 | +1.94 / +2.01 | 0.91 / 0.90 | 0.91 / 0.91 | 0.006 / 0.003 | yes |
| KX1, skip < 0.5% / < 1% | FED | +1.10 / +1.14 | +2.00 / +2.42 | 0.94 / 0.96 | 0.94 / 0.94 | 0.007 / 0.003 | yes |
| KX3 / KX1 / INC, costs 4.0-6.0 bps | CA | 0.985-0.986 / 0.919-0.938 / 0.642-0.664 | 1.84 / 1.81-1.82 / 1.53-1.55 | | | 0.011-0.012 / 0.011 / 0.025 | |

- Skipping dust top-ups is what a real investor would do, and it costs nothing.
- KX1's jump to +2.5 full_excess is the same path chaos in the other direction. Do not read it
  as an improvement.

**Configs added by this verification (none selected on performance):**
- 52 offset / lag / exact / sanity configs (`b2`);
- 14 exact-budget offset and lag configs (`b5`);
- 4 min-trade configs (`b3`);
- 12 cost-nudged runs (`b4`);
- the standard battery's 18 cost runs and 24 realism runs (`b1`).

They count as robustness checks of two finalists, not as additional search.

## Files

- `research/lab/families/verify_taxrot_mech.py`: kind `verify_taxrot_mech.ws_x` (`offset_days`,
  `lag`, `exact_budget`).
- `research/lab/scratch/verify_taxrot_mech/`: `a1_audit.py` (+ `.json`, `.log`), `a2_stlots.py`,
  `a3_keep.py`, `a4_exact_path.py`, `a5_stress.py`, `b5_exact_offsets.py` (+ `.json`, `.log`), `b1_battery.py` (+ `battery_{KX3,KX1,INC}.json`), `b2_xruns.py` (+ `b2_runs.json`),
  `b3_extra.py` (+ `b3_extra.json`), `b4_pathsens.py` (+ `b4_pathsens.json`), `c1_analyze.py`
  (+ `c1_summary.json`), `c2_paired.py` (+ `c2_paired.json`), `c3_dsr_paired.py`
  (+ `c3_dsr_paired.json`).
