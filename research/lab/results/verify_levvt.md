# verify_levvt: adversarial check of tax-aware levered vol targeting (risk_alloc.taxvt)

**Verdict: FAIL as a strategy that beats SPY with good confidence.** The SSO-era numbers reproduce
exactly. They survive a one-day lag, a wash-sale fix, the stricter tax accounting and costs up
to 15 bps. But the excess is plain leverage (beta 1.57, alpha about 0). In a CA taxable account
the 1% gain budget switches the vol targeting off after about 2009: exposure freezes at
1.6-1.9x, and the frozen level depends on the price path. The long-history test fails the
confidence bar. Holding a constant mix with the same average leverage does as well or better.

Candidate (round 1, runnable as-is):
`{"kind":"risk_alloc.taxvt","signal":{"est":"simple","window":21,"target":0.25,"cap":2},"vehicles":["SPY","IWB","VTI"],"band":0.1,"cash":["SHY","VFISX"],"lever":[["SSO",2],["DDM",2]],"gain_budget":0.01,"requires":["SSO"]}`

Code: `research/lab/families/verify_levvt.py` contains kind `verify_levvt.taxvt`. It is the same
TaxVT logic plus two switches: `lag` (vol read from N bars earlier) and `wash_pre` (enforces
both sides of the wash-sale rule). Scripts and raw outputs are in
`research/lab/scratch/verify_levvt/` (`phase_{A,B,C,D}.json`, `diag.json`, `dd.json`,
`realism.json`, `beta.json`, `dsr.json`). About 75 new configs were run.

## 1. Reproduction and code audit

| regime | score | full | 10y beat | 15y beat | 20y beat | boot p | maxDD (SPY) | Sharpe (SPY) |
|---|---|---|---|---|---|---|---|---|
| CA | +3.40 | +4.85 | 98% (n=41) | 100% (n=21) | 100% (**n=1**) | 0.011 | -61% (-55%) | 0.65 (0.51) |
| FED | +3.64 | +6.32 | 98% | 100% | 100% | 0.001 | -59% (-55%) | 0.68 (0.51) |
| NONE | +4.01 | +3.40 | 100% | 100% | 100% | 0.024 | -54% (-55%) | 0.70 (0.51) |

These are identical to the round-1 figures. My kind with `lag=0` reproduces them exactly.
Round 1's cached results did not match only because `"cap": 2` and `2.0` give different
cache keys. The SSO-era sample starts in 2006-07, so only one 20-year window exists.

- **Look-ahead: none found.** `_vol_arr` is a rolling standard deviation of log returns up to
  today's bar, and `_bar` uses `rows_upto(today) - 1`. The engine's convention is to trade at
  the same close the signal reads. A one-day lag (vol from yesterday's close, traded at today's
  close) gives CA score +3.34, full +6.18, boot p 0.001; NONE +3.89 / +3.17. `requires: SSO`
  is honored: the first start is 2006-07-01.
- **Wash sales: real but not material.** The original blocks a re-buy only after a sale whose
  combined result was a loss. It never checks purchases in the 30 days before a loss sale.
  Replaying the first-start CA path lot by lot, 84 of 140 loss lots (25% of realized-loss
  dollars) had a purchase of the same fund within 30 days. In NONE the share is 75%, but
  without tax it does not matter. The `wash_pre=True` fix never sells a lot at a loss while a
  younger lot of the same fund bought in the last 30 days is held, and it blocks any loss lot
  from being re-bought for 31 days. It leaves 0.4% of loss dollars. Results with the fix:
  CA +3.26 / full +5.62 / boot p 0.001, FED +3.46 / +5.80; with lag 1 as well, CA +3.62 / +7.04.
- **Substitutes.** SPY, IWB and VTI track the S&P 500, the Russell 1000 and the CRSP US Total
  Market index. SSO and DDM are 2x the S&P 500 and 2x the Dow. These are different indexes, so
  the usual reading is that they are not substantially identical. The IRS has never ruled, and
  S&P 500 against Russell 1000 is about 0.99 correlated, so a small residual risk remains.
  **DDM as an SSO substitute is legal, but it changes the exposure.** On the CA path the
  levered sleeve ends up mostly in DDM: on average 78% of the portfolio is DDM and 5% is SSO.
  The strategy is therefore mostly a 2x Dow bet. Over 2006-2026 DDM returned 14.2%/yr against
  15.5% for SSO, so DDM held the result back rather than flattering it. With SSO only, CA
  scores +4.58 (full +5.99); with SSO only and the wash fix, +4.29 (+5.86). Removing DDM after
  seeing that result would itself be hindsight.
- **Negative cash.** Tax is paid in cash on the first trading day of each year, which can
  leave a small unfunded balance. It averages -0.02% of portfolio value, the minimum is -0.31%
  and it occurs on 8% of days. Immaterial.

## 2. Costs, realism, deflated Sharpe

- **Costs per side.** CA score: 0 bps +3.62, 5 bps +3.40, 15 bps +3.11, 35 bps +2.24.
  NONE: +4.94, +4.01, +2.21, -1.41; turnover in NONE is 4.1x per year.
- **Stricter tax accounting** (annual tax on distributions), CA excess before -> after:
  from 2006-07 +4.85 -> +4.59; from 2010 +1.40 -> +1.39; from 2015 +0.95 -> +0.92.
  FED from 2006-07: +6.32 -> +6.07. Starts after 2009 earn only about +1 to +1.4 pp/yr after
  tax despite about 1.9x leverage.
- **Deflated Sharpe** (12,000 trials): CA 0.012, FED 0.041, NONE 0.008. Far from 0.95.

## 3. Path dependence: the gain budget freezes leverage at a level set by the path (main fragility)

Daily exposure on the first-start path (CA): average 1.82x, at or above 1.8x on 85% of days.
Yearly averages: 2008 1.12, 2009 1.18, 2010 1.77, then 1.84 to 1.94 in every year 2011-2026.
That includes 2020 at 1.90 and 2022 at 1.89. In NONE, where the targeting trades freely, the
same years average 1.31 (2020) and 1.14 (2022). So **in CA the vol targeting worked once, in
2008, while the lots were young. After that, the embedded gains plus the 1% budget lock the
exposure in place.**

The frozen level depends on the path through 2009-10. Small, irrelevant perturbations move it,
and the full-period result with it:

| perturbation (CA, 2006-07 start) | average exposure | exposure 2015 / 2020 | ending equity | full excess |
|---|---|---|---|---|
| base (5 bps) | 1.82 | 1.91 / 1.90 | $2.03M | +4.85 |
| 0 bps | 1.83 | 1.89 / 1.89 | $2.57M | +6.19 |
| 15 bps | 1.63 | 1.60 / 1.71 | $1.16M | +1.79 |
| lag 1 | 1.83 | 1.89 / 1.88 | $2.56M | +6.18 |

Across lag, costs and the wash fix, the full excess ranges from +1.6 to +7.0 pp/yr. Scores
range from +2.2 to +3.6.

**Drawdowns after the freeze look like constant leverage.** CA maximum drawdowns by start date:

| start | candidate | constant 1.8x | SPY |
|---|---|---|---|
| 2006-07 | -61% (in COVID 2020, not 2008) | -80% | -55% |
| 2010-01 | -52% (COVID) | -56% | -34% |
| 2013-01 | -58% (COVID) | -57% | -34% |
| 2016-01 | -53% (COVID) | -56% | -34% |
| 2019-01 | -33% | -55% | -34% |

A 2008-sized crash that arrives after the freeze should cost about 80%. The long-history run
shows -79%.

## 4. Does vol targeting add anything beyond average leverage? No in return, yes in risk only without tax

Constant-exposure controls use the same TaxVT execution, budget and band (`signal.const_e`);
buy-and-hold controls are bought once and never rebalanced.

| config (SSO era, full protocol) | CA score | CA full | NONE score | NONE full | maxDD | Sharpe |
|---|---|---|---|---|---|---|
| candidate (average exposure 1.82 CA / 1.65 NONE) | +3.40 | +4.85 | +4.01 | +3.40 | -61% / -54% | 0.65 / 0.70 |
| constant 1.65 | +4.24 | +2.81 | +4.75 | +3.12 | -77% | 0.58 |
| constant 1.8 | +5.06 | +3.59 | +5.67 | +3.61 | -80% | 0.58 |
| constant 1.9 | +5.53 | +4.02 | +6.25 | +4.21 | -82% | 0.58 |
| SPY/SSO 18/82, bought once | +5.03 | +3.47 | +5.69 | +3.64 | -80% | 0.58 |
| SPY/SSO 50/50, bought once | +3.39 | +2.35 | +3.84 | +2.47 | -71% | 0.60 |

- **Regression of monthly returns on SPY** (first start): CA beta 1.57, alpha -0.09%/yr
  (t = -0.04); NONE beta 1.29, alpha +0.69%/yr (t = 0.37). In excess-return terms, CA alpha
  is about +0.6%/yr and not significant.
- **Parameter neighborhood** (screen protocol, CA; 32 configs: target 15/20/25/30%, window
  10/21/42/63, cap 1.5/2.0). Cap 2.5 is identical to 2.0 with a 2x sleeve.
  - The score rises steadily with the target, that is, with average leverage: at 15% it is
    -0.6 to +0.04 (the strategy fails), at 20% +0.5 to +2.7, at 25% +1.8 to +3.9, at 30%
    +2.6 to +4.8.
  - The window hardly matters: at 25% target and cap 2, windows 10/21/42/63 score
    +3.9 / +3.6 / +3.2 / +3.5.
  - The dial is leverage, not timing.
- **What vol targeting really does.** In a tax-free account (NONE) it lowers risk at about the
  same leverage: Sharpe 0.70 against 0.58, drawdown -54% against -77%. Its return is no
  higher, and its score is lower than constant leverage at the same average exposure. In CA
  even that benefit vanishes once the budget freezes exposure.

## 5. Long history (synthetic 2x S&P 500 with financing and fees, SYN_VFINX2XC)

The financing cost is the T-bill rate plus a 0.6% spread on the borrowed half; the fee is
0.9%/yr. Benchmark: VFINX.

| config (1986-2026) | regime | score | full | 10y beat | 15y beat | 20y beat | boot p | maxDD (VFINX) | Sharpe (VFINX) |
|---|---|---|---|---|---|---|---|---|---|
| candidate analog, quarterly starts | CA | +2.46 | +1.19 | 74% | 72% | 55% | 0.26 | -79% (-55%) | 0.55 (0.67) |
| candidate analog, yearly starts | NONE | +1.89 | +2.29 | 68% | 50% | 71% | 0.095 | -69% | 0.65 |
| candidate analog | FED | +2.73 | +1.29 | 71% | 73% | 48% | 0.26 | -78% | 0.55 |
| + one-day lag | CA | +2.26 | +0.89 | 74% | 69% | 52% | 0.27 | -74% | 0.56 |
| + wash fix | CA | +2.05 | +1.19 | 71% | 65% | 33% | 0.26 | -79% | 0.55 |
| + 2nd vehicle VTSMX | CA | +2.23 | +1.31 | 71% | 69% | 43% | 0.25 | -80% | 0.55 |
| constant 1.8 | CA | +2.14 | +2.49 | 74% | 69% | 71% | 0.14 | -84% | 0.56 |
| VFINX/2x 50/50, bought once | CA | +1.45 | +1.80 | 68% | 65% | 62% | 0.14 | -77% | 0.57 |

- **2000-2026 with synthetic 2x SPY** (before SSO existed). CA score +3.11, full +1.72,
  10y beat 82%, 15y beat 89%, boot p 0.25, max drawdown -68%, Sharpe 0.47 against SPY 0.51.
  Constant 1.8: +2.59, +1.20, boot p 0.34, max drawdown -83%.
- **Pre-2000 holdout** (windows that end before 2000) is positive: 5-year +5.8 pp with an
  81% beat rate. Those windows sit inside the 1986-99 bull market, so leverage would win there
  whatever the timing.
- **10-year excess by start decade** (CA): 1980s +5.2, 1990s +1.3 (worst -5.5),
  2000s +2.5 (worst -4.7), 2010s +4.6.
- In CA the risk-adjusted return is **below** buying and holding the index: Sharpe 0.55
  against 0.67.

## 6. Scorecard against the protocol bar (CA)

1. Score and full-period excess above zero: **yes** in the SSO era, and yes in the long
   history.
2. Beat rates (10y at least 75%, 15y at least 85%): **yes** in the SSO era (98% / 100%).
   **No** in the long history (74% / 72%).
3. Bootstrap p at most 0.10: **yes** in the SSO era (0.011). **No** in the long history
   (0.26) and **no** for 2000-2026 synthetic (0.25).
4. Positive walk-forward: **no**. Round 1 found -0.53 pp.
5. A passing neighborhood: **yes**, but only because the dial is the leverage level; at a 15%
   target the strategy fails.
6. No hindsight instrument: **ok**. DDM is a drag, not a winner picked after the fact.
7. Long history does not contradict: **it contradicts.** Pre-2000 alone is positive but
   uninformative.

Deflated Sharpe is 0.01.

## Corrected config (if anyone still wants it as a leverage product)

The wash-sale-compliant version is
`{"kind":"verify_levvt.taxvt","signal":{"est":"simple","window":21,"target":0.25,"cap":2},"vehicles":["SPY","IWB","VTI"],"band":0.1,"cash":["SHY","VFISX"],"lever":[["SSO",2],["DDM",2]],"gain_budget":0.01,"requires":["SSO"],"wash_pre":true}`.

| regime | score | full | 10y beat | 15y beat | 20y beat | boot p | maxDD (SPY) |
|---|---|---|---|---|---|---|---|
| CA | +3.26 | +5.62 | 98% | 100% | 100% (n=1) | 0.001 | -59% (-55%) |
| FED | +3.46 | +5.80 | — | — | — | — | — |

Long-history CA: +2.05 / +1.19, boot p 0.26.

It is still a frozen-leverage bet. If the user wants 1.5-1.9x S&P exposure and accepts
drawdowns of about 80%, a once-bought SPY/SSO mix gets the same expected excess more simply.
That is more risk, not more skill.
