# Round 2 / rotation_final: is there an honest unlevered alternative to SPY? (fixed tax-managed momentum vs SPY)

Family key `r2_rotation_final`. Module `research/lab/families/r2_rotation_final.py`; scripts, logs,
tables (`an_*.md`, `an_*.json`, `an_rm.csv`) and the multi-start run cache in
`research/lab/scratch/r2_rotation_final/`. Every number comes from the lab engine, which is the
website's engine: the bootstrap paths also run through `backtester.Backtest`, not a replica.
"Excess" = after-tax CAGR (liquidated at the window end) minus SPY bought and held, same regime and
costs, in pp/yr. CA = 48.1% short-term / 28.1% long-term (primary), FED = 35% / 15% (secondary;
the engine's FED regime has no 3.8% NIIT). Costs 5 + 5 bps per side.

## Verdict

**No unlevered rule tested here can honestly be recommended over SPY for a taxable California
investor. SPY bought and held is the unlevered answer.**

{{VERDICT_BULLETS}}

## What was tested, and how many configurations

{{COUNTS}}

## 1. The two evaluation fixes, and checks that the code does what it says

**Eligibility (`min_start`).** A window may start only once at least 10 menu funds have the
history the rule needs (`lookback + skip + 1` bars; for a menu that changes each year, 10 funds of
that year's menu). The first valid start replaces the old 2000-01 start, on which only SPY, MDY
and DIA were rankable:

| menu | rules needing 274 bars (INC, KX1, CORE*_KX1) | rules needing 379 bars (KX3, ANC*, CORE*_KX3) |
|---|---|---|
| incumbent 22 ETFs | 2000-01-24 -> first start 2000-04-01 (full) | 2000-06-22 -> 2000-07-01 |
| rule-built US menus | 2000-01-24 -> 2000-04-01 | 2000-06-22 -> 2000-07-01 |
| rule-built ALL menus (8 country funds + SPY, MDY, DIA rankable in Jan 2000) | 2000-01-01 | 2000-01-01 |
| 60 random menus (screen) | first yearly start 2001 (43 menus), 2002 (11), 2000-01 (6) | same |
| PRE20 / FSEL32 / FSEL11 (long_r_screen) | 1986 / 1986 / 1988 | 1986 / 1986 / 1989 |

**FIFO-exact gain budget.** Every lab-execution rule (`r2_rotation_final.ws`) sizes a
budget-limited partial sale on the FIFO lots it will actually sell
(`verify_taxrot_mech.ws_x exact_budget=True`), so no calendar year's net realized gain exceeds
`gain_budget x portfolio value`. The site preset is reported as the site runs it (average-gain
sizing, alphabetical buys) and, as `INCX`, with the exact budget.

**Start-averaged statistics.** `full_excess` and `boot_p` describe one path (the first start), and
for these frozen-book rules one path is close to a lottery ticket. Every record here keeps the
month-end after-tax value of every start (`h.run_multi`), so each table also reports the excess
from every start with at least 10 years to 2026-07 ("start-avg full_excess", share of starts > 0)
and the median of those starts' bootstrap p-values (share <= 0.10). "Bar 1-3 averaged" applies
PROTOCOL criteria 1-3 with these two in place of the first-start values.

**Validation** (`v0_identity.py`, `v1_incw.py`, `v2_bootval.py`, `a1_audit.py`):
- The new kind with none of its new options reproduces `verify_taxrot_mech.ws_x` (exact budget) for
  KX1 and KX3 exactly: 95 starts, 5,605 checkpoints, max |difference| 0.
- The multi-start runner reproduces the sweep record of the site preset exactly (every checkpoint,
  every summary statistic). `INCW` (lab execution, alphabetical buys, average-gain sizing)
  reproduces the site's TaxManagedCombo exactly on `full` and `screen`.
- A menu given year by year (the same 22 funds every year) reproduces the static-menu run exactly.
  The anchored rule with an unreachable margin is SPY buy-and-hold (excess -3e-8, one trade).
- Trade-log audit of 13 runs (anchored, SPY core, 0% budget, KX1, KX3; starts 2000 and 2010):
  - **no wash sale on either side** of the IRS rule: no purchase of the same fund or a substantially
    identical one within 30 days before or after any loss sale (loss lots audited: 13-91 per run);
  - the anchored rule's targets re-derived independently from 378-day returns at every rebalance:
    0 mismatches;
  - the SPY core of the CORE designs is never sold;
  - no calendar year's net realized gain exceeds the budget times the year's largest rebalance-day
    portfolio value (the exact budget works);
  - cash goes negative only on the January tax-payment day, at most -$2.2k on a ~$450k book.
- The bootstrap's in-memory market reproduces the lab engine exactly when fed the real price files
  (KX1, KX3, INC from their first starts, with and without the volume column: difference 0).

## 2. The incumbent 22-ETF menu (full protocol: quarterly starts 2000-2023)

Pre-registered rule designs (no parameter was searched in this round):

| rule | what it is |
|---|---|
| INC | the site preset "Beat the S&P (CA)": 252-21 momentum, top 5, quarterly, 1% budget, alphabetical buys, average-gain partial sales |
| INCW / INCX | INC in the lab execution, average-gain (= site, identical numbers) / FIFO-exact budget |
| KX1 | 252-21, top 5, Q, 2% budget, long-term gains only, keep held funds in the top 10, never trim, spend the budget on the worst-ranked first, proportional buys |
| KX3 | 378-0, top 5, S, 1% budget, same K-execution (short-term gains allowed) |
| KX1_0 / KX3_0 | the same with a 0% budget: gains are realized only against losses of the same year (critic gap iii) |
| ANC{m}_{b} | anchored to SPY (critic gap ii): 5 slots hold SPY by default; a fund (378-0 return) takes a slot only if it beats SPY's 378-day return by m = 5 / 10 / 20 pp, keeps it while in the top 10 and still ahead of SPY; S cadence, K-execution, budget b = 0% / 1%; SPY may be sold down to pay for an entry |
| CORE{c}_{KX1/KX3} | c = 50 / 70 / 80% SPY never sold + KX1 or KX3 sleeve on the menu without SPY, budget scaled to the sleeve (KX1 2% x (1-c), KX3 1% x (1-c)) |
| RR1 / RR3, EWBH | controls: random ranking under the KX1 / KX3 execution (5 seeds); equal weight of the menu, never sold |

{{INC_TABLE}}

Reading the table:
- **Fixing the start barely moves the site preset and KX1.** KX1 still clears criteria 1-3 from its
  first valid start (2000-04: score +0.87, full +1.73, boot_p 0.011, 10/15-year beat 0.89/0.91). KX3
  with both fixes fails (15-year beat 0.84). KX3's exact-budget path is chaotic: from 2000-01 its
  full-period excess is +0.31, from 2000-07 +1.12.
- **Averaged over start dates, nothing passes.** KX1's excess from the 66 starts with 10+ years of
  history averages +0.64 pp/yr (positive from 85% of starts), but the median bootstrap p-value of
  those paths is 0.25; only 18% of start dates would have shown p <= 0.10. The other rules are
  similar (median 0.16-0.89).
- **The new designs do not change the picture.** ANC5_1 is the best by default (score +0.94, beat
  rates 0.92 / 0.91 / 0.92, boot_p 0.075) but its neighbours ANC10_1 (start-avg excess +0.00) and
  ANC20_1 (+0.25) are much weaker: a lone spike, not a plateau. A 0% budget freezes the book bought on
  day one (KX3_0's 2026 book is the five funds it bought in July 2000); full-period excess -0.2 to
  -1.2. The SPY core scales the rotation down: CORE70_KX1 has 30% of KX1's score (+0.28) at 39% of
  its tracking error (1.7% vs 4.3% a year) and fails criterion 2 by a single 15-year window in CA.
- **Controls.** Random picks under the same execution score +0.10 (RR1) / -0.02 (RR3) and equal
  weight +0.01: on this menu the momentum signal adds +0.8-0.9 of score.

{{INC_EXTRA}}

## 3. Rebalance-boundary offsets (incumbent menu, CA)

{{OFF_TABLE}}

## 4. Menus built by a fixed rule as of each date (critic gap i)

Rule (pre-registered in `menus.py` before any run): each Jan 1, rank the equity ETFs in a fixed
pool that have at least 252 trading days of history by their mean daily **dollar volume** over the
previous 252 days (unadjusted close x volume; the dividend-adjusted close would scale old prices by
future dividends), keep one fund per index (SPY/IVV/VOO, MDY/IJH, ...), and take the top 20 or 30.
Pools: **US** = the site's US-equity ETFs + the lab's 104 `us_equity` funds (127 funds: broad, size,
style, sector, industry, factor, REIT); **ALL** = US + 46 US-listed international equity ETFs.
The menu grows as funds launch: RB_US20 has 12 funds in 2000 (SPY, MDY, DIA, 9 sector SPDRs), 13 in
2001 (+QQQ) and 20 from 2002. Nobody chose QQQ or XLK: QQQ is on every rule-built menu from 2001 by
volume alone, XLK in 16-27 of 27 years, and semiconductors (SMH, SOXX), biotech, oil, banks, ARKK and
the iShares style boxes come and go. Held funds that leave the menu become exit candidates. The
pool is the set of ETFs the lab downloaded in 2026, so ETFs that were heavily traded and later
closed (HOLDRs such as HHH, OIH, RTH) are missing; that flatters every rule slightly in 2000-02.

Full protocol, CA (FED in `an_rb.md`; it changes no conclusion). Scores in pp/yr:

{{RB_TABLE}}

{{RB_NOTES}}

## 5. Random menus (60 menus, screen protocol, CA)

Menus: seeds 1-60, 15-25 funds drawn from `common.BROAD_EQUITY_POOL_2003` (seeds 1-30 are the
menus round 1 and verify_taxrot_robust used), wash guard over identical-index groups, first valid
start by the 10-eligible-fund rule.

{{RM_TABLE}}

{{RM_NOTES}}

## 6. Pre-2000 analog menus (long_r_screen, VFINXR benchmark, CA, 1-day lag)

PRE20 (sector_deep's mutual-fund analog of the incumbent menu, with VFINX replaced by the repaired
VFINXR), FSEL11 (its 11 sector funds) and FSEL32 (28 Fidelity Select + 4 Vanguard sector funds).
Yearly starts 1986-2023; `ho5` / `ho10` are windows that end before 2000, the true holdout for
rules designed on ETF data. Anchor / core = VFINXR. Mutual funds trade at a NAV the order cannot
know, hence the 1-day lag. Not modelled, and flattering every rule on the Fidelity menus: the 3%
front loads and short-term redemption fees of the 1980s-90s Select funds, and survivorship (merged
Select funds are missing).

{{PRE_TABLE}}

{{PRE_NOTES}}

## 7. Resampled market histories (critic gap iv)

{{BOOT}}

## 8. Criteria 1-7 for the leading candidates (CA)

{{CRITERIA}}

## 9. Decision: expected excess and confidence

{{DECISION}}

## Notes for the lab

{{LABNOTES}}

## Files

{{FILES}}
