# Tax-managed rotation: refining the "Beat the S&P (CA)" preset

Family `tax_rotation`, module `research/lab/families/tax_rotation.py`, scripts and logs in
`research/lab/scratch/tax_rotation/`. Every number comes from the lab engine, which matches the
website exactly. "Excess" means after-tax CAGR minus SPY buy-and-hold in the same regime
(0.01 = 1 percentage point a year). Primary regime: CA (48.1% / 28.1%). FED (35% / 15%) is
secondary. NONE is a diagnostic only.

## Verdict

**No tax-managed rotation clears the full "good confidence" bar (PROTOCOL section 3) in CA or in FED.**

The best refinement found is **KX3**:
- 378-day momentum with no skip, top 5, semiannual rebalance, 1%/yr gain budget, proportional buys.
- A "frozen-winner" execution on top:
  - keep a held fund while it ranks in the top 2N (10);
  - never trim a fund the signal still wants;
  - spend the gain budget on the worst-ranked holdings first.

KX3 beats the incumbent preset on every criterion-1-3 metric on the full protocol in CA:

| metric | KX3 | incumbent |
|---|---|---|
| score | +0.0099 | +0.0066 |
| full_excess | +0.0184 | +0.0154 |
| ex10_beat | 0.90 | 0.70 |
| ex15_beat | 0.85 | 0.83 |
| boot_p | 0.011 | 0.025 |
| max drawdown | −0.537 | −0.566 (SPY −0.552) |

It passes criteria 1-3 in CA and FED. Its sibling **KX1** (the incumbent's 12-1 / top-5 / quarterly
signal with the same execution, long-term gains only, 2% budget) does too.

Both fail the rest of the bar:
- **Criterion 4 (overfitting checks across the whole family):**
  - Across all 997 screened CA configs, PBO is 0.60.
  - Picking the best past config does not beat SPY afterwards. Walk-forward out-of-sample excess is
    +0.0004 (10-year in-sample / 5-year out-of-sample) and −0.0116 (5y / 3y).
  - Inside the K-execution sub-family, PBO is 0.63-0.77.
- **Criterion 6 (hindsight):**
  - With QQQ or XLK removed from the menu, every finalist fails the beat-rate tests.
  - On 30 random menus from the pre-registered pool, 1 in 30 passes criteria 1-3.
- **Criterion 7 (long history):** the pre-2000 holdout on mutual-fund proxies is flat to negative
  (KX3 ho5 −0.0012, ho10 −0.0023; KX1 −0.0030 / −0.0028).
- **Criterion 5 (neighbourhood):** only partly met.
  - Every one of the 25 full-protocol neighbours of KX1/KX3 has a positive score.
  - Only 27-29% of them clear criteria 1-3.
  - The default rebalance months are among the best of the possible schedules.

What is real, and what is not:
- **The momentum signal adds value regardless of menu.** On the same 30 random menus, momentum
  beats random ranking with the identical tax rule by +0.008/yr of score (t ≈ 7, better on 90%
  of menus).
- **The lead over SPY is not robust.** It needs a menu that contains the 2010-2026 winners
  (QQQ, XLK) or a US equal-weight tilt starting in 2000. Every rule lost 2.8-3.9 pp/yr in 5-year
  windows starting 2020-2023.
- **Most of the lead comes from 2000-2010.** In CA, the fresh-start excess is:

  | rule | 2000-10 | 2010-20 | 2020-26 |
  |---|---|---|---|
  | KX3 | +2.9 pp | +0.9 pp | −0.4 pp |
  | KX1 | +3.6 pp | +0.7 pp | −0.6 pp |

- **The "frozen winners" problem is not solved.** The K-execution lets winners run even more.
  By 2026, KX1/KX3 are 56-60% QQQ/XLK-type growth/tech, and 80-87% of the portfolio is
  unrealized gain. The incumbent is 74.5% growth/tech.

The user should treat KX3/KX1 as a better-engineered version of the same regime bet the incumbent
makes, not as a strategy that beats SPY with good confidence.

## What was tested (the multiple-testing count)

- **Total:** 1,794 distinct configs and 2,238 config × regime × protocol backtests.
- **By protocol:** 2,096 on screen (CA 1,422, NONE 674), 86 on full, 44 on long_screen, 12 on
  long.
- **Searched configs:** about 1,100 configs were searched for performance. The CA screen grid used
  for the diagnostics has 997 configs.
- **Controls and hindsight menus:** the rest.

| stage | what | backtests |
|---|---|---|
| A (previous researcher) | site combo: lookback {63..504} × skip {0,21} × top_n 2..10 × M/Q/S/A at 1% budget (CA, NONE) | 672 |
| A | site combo budgets {0..5%} × M/Q/S/A × n {3,5,8} × (12-1, 6-0) (CA) | 144 |
| B (previous) | WS signal grid: 12 return signals + blended ranks, risk-adjusted, 52w-high, residual momentum × n {3,5,8} × M/M2/Q/S/A (CA) | 375 |
| B | same grid, shadow lots in NONE (the same tax-managed trades, untaxed) | 286 |
| p1 (previous) | random-rank controls (20 seeds combo CA/NONE; 20 WS CA; 18 WS shadow); 30 random menus + QQQ/XLK removals | 144 |
| s2 K | "frozen winners" (item k) and concentration-cap variants on two bases | 28 |
| s2 C | gain budget × st_gains for WS on two bases | 26 |
| s2 J | buy order alpha (= site) / rank vs proportional | 4 |
| s2 D | features: inverse-vol, hold buffers, sell-losers, TLH (with or without substitutes, monthly/weekly), SPY core 25/50/75%, strict wash, band, absolute filter to SHY/IEF | 46 |
| s2 F, RM | random-rank control for B378 (25 seeds); the 30 random menus finished for B378 | 25 + 9 |
| s2 E | 15 named menus × combo INC (CA, NONE), WS B378, WS INC (CA) | 52 |
| s3 KH, KR, KHR, KG | K-execution: 30 random menus + removals; random-rank control (20 + 20); paired random-rank on the 30 random menus (60); local grid (40) | 204 |
| s3 KUS | sensitivity, not pre-registered: 30 US-only random menus × (KX1, B378, random-rank) | 90 |
| f1 | full protocol: core finalists CA/FED/NONE (12), K finalists (6), neighbourhoods and rebalance offsets of B378 WS (14), B378 combo (9), KX1/KX3 (25), random-rank on full (20) | 86 |
| g2 | long history (1986-2026, VFINX, LONG_MENU): long_screen rules, shadow, random-rank (12 + 12), K rules; quarterly long protocol for 6 finalists × CA/NONE | 56 |

Abbreviations used below:
- **INC**: the incumbent's knobs, 252-21 momentum, top 5, quarterly.
- **B378**: 378-day momentum, no skip, top 5, semiannual.
- **WS**: the lab's tax execution with proportional buys.
- **combo**: the site's TaxManagedCombo, which fills buys alphabetically.

## 1. The grid: signals, top_n, cadence (screen protocol, CA)

- **Stage A (site combo, 336 configs, 1% budget):**
  - Mean score +0.0007; 64% of configs have a positive score.
  - The incumbent ranks 29th of 336.
  - Mean score by signal, from worst to best:

    | signal | mean score |
    |---|---|
    | 63-day | −0.0054 / −0.0037 |
    | 126-189 day | about 0 |
    | 252-21 | +0.0032 |
    | 378-0 | +0.0038 |
    | 504-0 | +0.0048 |

  - By top_n: n = 2 loses (−0.0041); n = 5-8 is the plateau (+0.0022 to +0.0024).
  - By cadence: Q is best (+0.0020); M is worst (−0.0002).
- **Stage B (WS, 375 configs):**
  - Mean score +0.0032; 82% positive.
  - The best signal families are:
    - riskadj126-0 with vol window 63 (+0.0064);
    - ret252+504 blended rank (+0.0058);
    - long single lookbacks 378-504 (+0.0053 to +0.0057);
    - resid126 (+0.0057).
  - 52-week-high proximity is about 0. Short lookbacks (63) lose.
- **Criteria 1-3 on screen are rare and scattered:**
  - 5 of 336 combos and 13 of 375 WS configs pass.
  - The only cluster is lookback 378-504, skip 0, n 5-6, cadence S/Q.
  - None of 40 random-rank seeds passes.
  - This is not a broad plateau. Mean boot_p is 0.2-0.5 nearly everywhere.

## 2. Site TaxManagedCombo vs WS execution (item j)

- On 144 identical-knob pairs, proportional buys (WS) beat the site's alphabetical buys on 84% of
  pairs: +0.0011 score and +0.0019 full_excess on average. The correlation of scores is 0.955.
- WS with `buy_order="alpha"` reproduces the site combo exactly:
  - INC: 0.0064 / 0.0154;
  - B378: 0.0094 / 0.0105.
- So the only difference is the fill order. Filling in rank order adds nothing over proportional
  fills.

## 3. Gain budget and short-term gains (item d)

- **Site combo:**
  - 12-1 rule: mean score over cadence and n is flat from 0 to 1% (0.0034-0.0037). It falls to
    0.0029 at 2% and 0.0014 at 5%.
  - 6-0 rule: the decline is monotone, from about +0.0033 at 0% to −0.0066 at 5%. Turnover rises
    5-10×.
- **WS:**
  - B378: flat at 0.009-0.011 for budgets of 0-2%; 0.0029 at 5%.
  - INC: 0.006-0.0074 up to 2%; 0.0034 at 5%.
- **`st_gains=False`:**
  - On INC it raises the score (+0.0114 to +0.0125 for budgets 0-2%) but lowers full_excess
    (−0.001 to +0.008 for budgets 0-3%) and worsens boot_p (0.23-0.56).
  - On B378 it is neutral.
- The working region is a budget of 0.5-2% a year.

## 4. The incumbent's "frozen winners" (item k)

- **Holdings, one 2000-01 run in CA:**
  - Incumbent: by 2010 it is frozen in QQQ, IJR, XLV, XLK and IWF. Growth/tech weight goes from
    39% (2010) to 51% (2016), 69% (2022) and 74.5% (2026). Unrealized gains reach 88% of portfolio
    value.
  - B378 WS: about 50% growth/tech by 2026, with 86% unrealized gains.
- **Variants (screen, CA):**

  | rule | base | with K-execution | change |
  |---|---|---|---|
  | INC | 0.0073 | 0.0121-0.0133 | large gain |
  | B378 | 0.0106 | 0.0105-0.0125 | neutral |

  - The K-execution here means: keep held names in the top 2N (`hold_buffer=N`), `trim=False`,
    `gain_order="rank"`, optionally long-term only, budget 1-3%.
  - On INC, the long-term-only K-execution passes criteria 1-3 for budgets 1-5%.
  - `trim=False` alone and `gain_order="rank"` alone each add about +0.0005 to +0.0009 on INC.
  - A concentration cap (`max_weight` 0.3 / 0.4) does nothing.
  - Forcing exits with larger budgets (3-5%) does not help.
- **Local grid around the K-execution (40 configs, screen CA):**
  - All 40 have a positive score (mean 0.0085, versus 0.0032 for the plain WS grid); 23% pass
    criteria 1-3.
  - Lookback 189-21 is weak (about 0.004); 252-21, 378-0 and 504-0 give about 0.009-0.012.
  - n = 5 is best.
- **The execution does not unfreeze the portfolio.** It lets winners run without trims:
  - KX3 in 2026: QQQ 33%, XLK 23%, MDY 18%; growth/tech 56%; unrealized gains 87%.
  - KX1 in 2026: XLK 32%, QQQ 25%; growth/tech 60%.
- **It is momentum on this menu that benefits.** Random ranking with the same K-execution on the
  incumbent menu:

  | control | mean score (sd) | full_excess | rule's score | z |
  |---|---|---|---|---|
  | KX1 control, 20 seeds | +0.0012 (0.0024) | +0.0029 | 0.0133 | 5.2 |
  | KX3 control, 20 seeds | +0.0006 (0.0032) | +0.0064 | 0.0117 | 3.5 |

## 5. Features (items e, h, i): screen, CA, on the INC and B378 bases

| feature | INC (base 0.0073) | B378 (base 0.0106) | reading |
|---|---|---|---|
| inverse-vol weights (63 / 252) | 0.0068 / 0.0069 | 0.0082 / 0.0086 | slightly worse |
| hold buffer 1 / 2 / 4 (with trims) | 0.0074 / 0.0071 / 0.0066 | 0.0086 / 0.0108 / 0.0098 | neutral; full_excess falls on B378 |
| sell losers 0 / 5 / 10 / 20% | 0.0055 / 0.0066 / 0.0089 / 0.0061 | 0.0114 / 0.0117 / 0.0096 / 0.0107 | noise |
| TLH 5 / 10 / 15%, monthly, different-index substitutes | 0.0003 / 0.0005 / 0.0055 | 0.0048 / 0.0067 / 0.0078 | **hurts** |
| TLH without substitutes (cash) | 0.0057 / −0.0013 / −0.0003 | 0.0015 / 0.0028 / 0.0036 | hurts more |
| TLH 10% weekly with substitutes | −0.0017 | 0.0005 | hurts |
| SPY core 25 / 50 / 75% | 0.0058 / 0.0038 / 0.0014 | 0.0072 / 0.0044 / 0.0018 | dilutes about proportionally; B378 + 25-50% core still passes 1-3 on screen |
| strict wash guard | 0.0073 | 0.0106 | identical |
| 2% drift band | 0.0069 | 0.0101 | neutral |
| absolute filter to SHY / IEF | −0.0037 / −0.0080 | −0.0088 / −0.0078 | **strongly negative** |

TLH hurts for three reasons:
- Losses are already sold at every rebalance.
- The substitutes VEA, VWO and ONEQ did not exist before 2003-2007, so harvests left cash idle
  (average cash 1.5-6.5%).
- Swapping back to the original fund costs trades.

## 6. Menus and hindsight (items f, g; PROTOCOL 5.3)

**Named menus**, screen score in CA:

| menu | combo INC | WS B378 | WS INC |
|---|---|---|---|
| incumbent 22 | +0.0064 | **+0.0106** | +0.0073 |
| broad/style 11 | +0.0040 | +0.0096 (ex15_beat 0.75) | +0.0041 |
| SPDR sectors 11 | −0.0001 | +0.0033 | +0.0001 |
| iShares sectors 11 (gated from 2002) | −0.0095 | −0.0064 | −0.0087 |
| + bonds (IEF, TLT, SHY) | −0.0055 | +0.0006 | −0.0031 |
| + gold | +0.0013 | +0.0101 | +0.0052 |
| + bonds + gold | −0.0058 | −0.0007 | −0.0038 |
| 20 country funds + SPY | −0.0258 | −0.0224 | −0.0224 |
| incumbent 22 + countries | +0.0044 | −0.0021 | +0.0013 |
| factor ETFs | −0.0100 | −0.0045 | −0.0094 |
| equity pool, 84 funds | +0.0036 (full −0.0204) | +0.0067 (full −0.0132) | +0.0084 (full −0.0090) |
| full pool, 90 funds | +0.0026 (full −0.0263) | −0.0082 | +0.0046 |

The incumbent's menu is the best of the 15 for every rule.

**QQQ / XLK removed** (screen, CA; score, with ex10_beat / ex15_beat / boot_p):

| rule | incumbent menu | − QQQ | − XLK | − both |
|---|---|---|---|---|
| combo INC (site preset) | 0.0064 | 0.0004 | 0.0017 | −0.0030 |
| WS B378 | 0.0106 | 0.0044 (0.76/0.67/0.44) | 0.0075 (0.82/0.83/0.10) | 0.0006 |
| KX1 | 0.0133 | 0.0075 (0.59/0.75/0.071) | 0.0095 (0.65/0.83/0.095) | 0.0042 |
| KX3 | 0.0117 | 0.0044 (0.59/0.58/0.33) | 0.0056 (0.76/0.75/0.16) | −0.0010 |

Every finalist fails criteria 1-3 once QQQ or XLK is removed.

**30 random menus** of 15-25 funds from `common.BROAD_EQUITY_POOL_2003` (screen, CA):

| rule | score mean (share > 0) | full_excess mean (share > 0) | ex10_beat mean | max_dd mean | pass 1-3 |
|---|---|---|---|---|---|
| combo INC | −0.0013 (40%) | −0.0028 (37%) | 0.39 | −0.635 | 0/30 |
| WS B378 | +0.0048 (73%) | −0.0018 (40%) | 0.54 | −0.635 | 0/30 |
| KX1 | +0.0042 (70%) | +0.0070 (87%) | 0.48 | −0.638 | 1/30 |
| KX3 | +0.0039 (77%) | +0.0016 (60%) | 0.52 | −0.642 | 1/30 |

**Paired control on the same 30 random menus** (random ranking, same execution; screen, CA):

| execution | momentum score | random score | paired difference | full_excess difference |
|---|---|---|---|---|
| B378 | +0.0048 | −0.0032 | +0.0079 (t = 6.96; momentum better on 90%) | +0.0019 (t = 1.11) |
| KX1 | +0.0042 | −0.0038 | +0.0080 (t = 7.22; 90%) | +0.0089 (t = 5.10; 87%) |

The momentum ranking is a real, menu-independent improvement over picking at random. The average
fund in the pre-registered pool, which is about 30% international, trails SPY by enough that
momentum lifts these menus only to about +0.004 of score, with beat rates near a coin flip.

**Sensitivity (not pre-registered): 30 US-only random menus** (58-fund US part of the pool):

| rule | score mean (share > 0) | full_excess mean (share > 0) | pass 1-3 |
|---|---|---|---|
| B378 | +0.0087 (97%) | +0.0117 (97%) | 6/30 |
| KX1 | +0.0062 (87%) | +0.0136 (87%) | 6/30 |
| random ranking, KX1 execution | +0.0040 (87%) | +0.0103 (80%) | 0/30 |

- Paired differences: B378 − random is +0.0048 score (t = 6.5); KX1 − random is +0.0022
  (t = 2.3).
- On US menus, even random picks held tax-efficiently beat SPY from the 2000 start. That is an
  equal-weight / size tilt that paid from the 2000 peak of mega-cap concentration, not
  selection skill.

## 7. Random-ranking controls (mandatory; same tax rule)

| control (CA, incumbent menu) | seeds | score mean (sd) | full_excess mean | rule's score (percentile) |
|---|---|---|---|---|
| site combo + RandomPicker, INC knobs | 20 | −0.0022 (0.0021) | +0.0043 | 0.0064 (100%) |
| WS random score, INC eligibility | 20 | +0.0006 (0.0019) | +0.0058 | 0.0073 (100%) |
| WS random score, B378 eligibility, n5 S | 25 | +0.0004 (0.0026) | +0.0064 | 0.0106 (100%; full_excess only 72nd percentile) |
| full protocol, INC / B378 | 10 + 10 | −0.0001 / −0.0001 | +0.0037 / +0.0096 | — |
| long_screen, INC / B378 | 12 + 12 | +0.0040 / +0.0030 | −0.0022 / −0.0014 | rules 0.0056-0.0083 |

- Random selection under the same tax rule ties SPY on score but earns +0.4 to +1.0 pp of
  full-period excess on the incumbent menu. That part of every headline "full_excess" is a menu
  effect, not a signal effect.
- On long history, momentum beats random by only about 0.001-0.004.

## 8. Finalists on the full protocol (quarterly starts 2000-2023)

Bar 1-3 means PROTOCOL criteria 1-3 only. Criteria 4-7 are assessed in section 11.

**CA**

| rule | score | full_excess | ex5_mean | ex10_mean | ex10_beat | ex10_min | ex15_beat | ex20_beat | boot_p | max_dd (SPY) | trades | turnover | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KX3 = 378-0 n5 S + buffer/no-trim/rank exits (WS) | +0.0099 | +0.0184 | +0.0078 | +0.0117 | 0.90 | −0.0038 | 0.85 | 0.96 | 0.011 | −0.537 (−0.552) | 224 | 0.047 | pass |
| KX1 = 252-21 n5 Q + buffer/no-trim/rank, LT-only, 2% (WS) | +0.0093 | +0.0182 | +0.0072 | +0.0107 | 0.91 | −0.0047 | 0.89 | 0.96 | 0.011 | −0.566 (−0.552) | 279 | 0.071 | pass |
| B378 WS = 378-0 n5 S, 1% (WS, prop buys) | +0.0091 | +0.0115 | +0.0059 | +0.0097 | 0.82 | −0.0114 | 0.89 | 1.00 | 0.054 | −0.549 (−0.552) | 331 | 0.070 | pass |
| B378 site combo = 378-0 top5 S, 1% | +0.0079 | +0.0105 | +0.0057 | +0.0076 | 0.82 | −0.0112 | 0.91 | 1.00 | 0.073 | −0.567 (−0.552) | 184 | 0.077 | pass |
| INC WS = 252-21 n5 Q, 1% (prop buys) | +0.0072 | +0.0129 | +0.0051 | +0.0075 | 0.84 | −0.0154 | 0.83 | 1.00 | 0.044 | −0.551 (−0.552) | 581 | 0.106 | fail: ex15_beat |
| Incumbent site preset (combo 252-21 top5 Q, 1%) | +0.0066 | +0.0154 | +0.0056 | +0.0055 | 0.70 | −0.0148 | 0.83 | 1.00 | 0.025 | −0.566 (−0.552) | 295 | 0.105 | fail: ex10_beat, ex15_beat |

**FED**

| rule | score | full_excess | ex5_mean | ex10_mean | ex10_beat | ex10_min | ex15_beat | ex20_beat | boot_p | max_dd (SPY) | trades | turnover | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| KX3 | +0.0110 | +0.0194 | +0.0088 | +0.0130 | 0.90 | −0.0038 | 0.87 | 1.00 | 0.006 | −0.537 (−0.552) | 224 | 0.047 | pass |
| KX1 | +0.0105 | +0.0196 | +0.0082 | +0.0120 | 0.93 | −0.0046 | 0.91 | 1.00 | 0.009 | −0.563 (−0.552) | 281 | 0.071 | pass |
| B378 WS | +0.0102 | +0.0123 | +0.0068 | +0.0110 | 0.82 | −0.0121 | 0.89 | 1.00 | 0.046 | −0.549 (−0.552) | 331 | 0.070 | pass |
| B378 site combo | +0.0088 | +0.0109 | +0.0066 | +0.0086 | 0.82 | −0.0114 | 0.94 | 1.00 | 0.075 | −0.567 (−0.552) | 185 | 0.078 | pass |
| INC WS | +0.0081 | +0.0134 | +0.0060 | +0.0085 | 0.85 | −0.0159 | 0.85 | 1.00 | 0.044 | −0.551 (−0.552) | 587 | 0.107 | pass |
| Incumbent preset | +0.0074 | +0.0160 | +0.0065 | +0.0063 | 0.69 | −0.0133 | 0.85 | 1.00 | 0.025 | −0.566 (−0.552) | 297 | 0.106 | fail: ex10_beat |

**NONE** (diagnostic). Without a tax policy the engine keeps no lots, so the tax rule, TLH and
sell-losers do nothing: these are plain untaxed rotations.

| rule | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | turnover | bar 1-3 |
|---|---|---|---|---|---|---|---|---|
| KX3 | +0.0091 | +0.0148 | 0.66 | 0.70 | 0.135 | −0.540 | 0.450 | fail |
| KX1 | +0.0071 | +0.0162 | 0.48 | 0.60 | 0.124 | −0.547 | 0.747 | fail |
| B378 WS / combo (identical) | +0.0100 | +0.0147 | 0.57 | 0.70 | 0.131 | −0.539 | 0.788 | fail |
| INC WS / incumbent (identical) | +0.0014 | +0.0055 | 0.40 | 0.43 | 0.341 | −0.518 | 1.45 | fail |

**Robustness on full, CA**

- **Neighbourhoods** (one step in lookback, skip, n, cadence and budget, plus rebalance-month
  offsets):

  | finalist | neighbours with score > 0 | median score | pass 1-3 |
  |---|---|---|---|
  | WS B378 | 14/14 | 0.0072 | 4/14 |
  | combo B378 | 9/9 (all with full_excess > 0) | 0.0068 | 2/9 |
  | KX1 | 11/11 (all with full_excess > 0) | 0.0076 | 3/11 |
  | KX3 | 14/14 | 0.0092 | 4/14 |

  Most failures are on boot_p (above 0.10) or ex15_beat (below 0.85). The effect is broad;
  clearing the whole bar is fragile.
- **Rebalance timing.** Averages over all rebalance-month schedules:

  | finalist | schedules | score mean (range) | full_excess mean (range) | boot_p mean | pass 1-3 |
  |---|---|---|---|---|---|
  | KX3 | 6 | 0.0089 (0.0068 to 0.0109) | 0.0124 (0.0075 to 0.0184) | 0.093 | 3/6 |
  | KX1 | 3 | 0.0071 (0.0057 to 0.0093) | 0.0124 (0.0090 to 0.0182) | 0.085 | 1/3 |
  | WS B378 | 6 | 0.0073 (0.0052 to 0.0091) | 0.0074 (−0.0017 to 0.0144) | 0.237 | 2/6 |

  The default schedule has the best full_excess of the schedules for KX1 and KX3, so the headline
  numbers contain some timing luck.
- **Calendar sub-periods** (CA, fresh start at each period start; pp/yr):

  | rule | 2000-10 | 2010-20 | 2020-26 | 2010-26 |
  |---|---|---|---|---|
  | incumbent | +1.20 | −0.55 | +0.19 | +0.04 |
  | WS B378 | +1.88 | +0.53 | −1.01 | +0.09 |
  | KX1 | +3.57 | +0.74 | −0.64 | +1.12 |
  | KX3 | +2.93 | +0.89 | −0.40 | +0.95 |

  All rules lose 2.8-3.9 pp/yr in 5-year windows starting 2020-2023
  (`scratch/tax_rotation/subperiods.csv`).

## 9. Long history: 1986-2026 on mutual-fund proxies (pre-2000 holdout)

`LONG_MENU` was pre-registered by the previous researcher before any long run:
- VFINX, NAESX, VEXMX, VIVAX, VIGRX, PRITX, VWIGX, VEIEX;
- 12 Fidelity Select / Vanguard REIT funds standing in for the sector SPDRs.

The benchmark is VFINX. ho5 and ho10 are windows that end before 2000.

| rule (quarterly `long` protocol) | regime | score | full_excess | ex10_beat | ex15_beat | boot_p | ho5_mean | ho5_beat | ho10_mean | ho10_beat |
|---|---|---|---|---|---|---|---|---|---|---|
| KX3 | CA | +0.0096 | −0.0034 | 0.66 | 0.75 | 0.600 | −0.0012 | 0.57 | −0.0023 | 0.24 |
| KX1 | CA | +0.0068 | −0.0054 | 0.64 | 0.80 | 0.675 | −0.0030 | 0.59 | −0.0028 | 0.47 |
| B378 WS | CA | +0.0087 | −0.0046 | 0.61 | 0.73 | 0.615 | −0.0101 | 0.65 | −0.0010 | 0.41 |
| B378 combo | CA | +0.0075 | −0.0020 | 0.59 | 0.66 | 0.534 | −0.0117 | 0.65 | −0.0045 | 0.29 |
| INC WS | CA | +0.0075 | −0.0052 | 0.56 | 0.72 | 0.670 | +0.0030 | 0.62 | +0.0019 | 0.47 |
| incumbent preset | CA | +0.0065 | −0.0002 | 0.59 | 0.78 | 0.480 | +0.0002 | 0.51 | +0.0008 | 0.47 |
| B378 (plain rotation) | NONE | +0.0225 | +0.0207 | 0.88 | 0.98 | 0.058 | +0.0110 | 0.68 | +0.0101 | 0.94 |
| incumbent (plain rotation) | NONE | +0.0049 | +0.0051 | 0.60 | 0.64 | 0.338 | +0.0201 | 0.70 | +0.0179 | 1.00 |

- **CA:** nothing passes criteria 1-3 over 1986-2026. The pre-2000 holdout is flat to negative
  (the plain 378-day rules −1.0 to −1.2 pp in 5-year windows).
- **NONE (diagnostic, for the IRA family):** the untaxed 378-0 n5 S rotation passes criteria 1-3
  on the long protocol, but not on the ETF-era full protocol (ex10_beat 0.57).
- The long_screen results (in the CSV) say the same.

## 10. Overfitting diagnostics (`report.diagnostics`, screen grid)

| set | configs | walk-forward 10y/5y OOS | walk-forward 5y/3y OOS | PBO | DSR of best |
|---|---|---|---|---|---|
| CA (stages A, B, K, C, J, D, KG) | 997 | +0.0004 (beat 0.33; average config −0.0076) | −0.0116 (beat 0.50) | 0.605 | 0.157 |
| NONE (A plain rotations + B shadow) | 622 | −0.0056 | −0.0439 | 0.516 | 0.241 |
| K-execution sub-family (KG + K) | 68 | +0.0002 | −0.0152 | 0.684 | 0.754 |

- In CA, the best config by monthly mean is `C|inc22|mom126-0|n2|Q`, a full-period fluke:
  full_excess +0.035 but score −0.0016.
- Within the K-execution sub-family (KG + K, 68 configs), the yearly walk-forward OOS is −0.0075
  (10y/5y), −0.0066 (5y/3y) and +0.0023 (5y/5y).
- **Supplementary walk-forward with a decision every year** (the pre-registered setting uses only
  3 decision dates on the annual-start screen protocol): choosing the trailing-best config gives
  OOS −0.0134 (10y/5y, 12 dates), −0.0057 (5y/3y) and +0.0038 (5y/5y), with an OOS rank
  percentile of about 0.5. Selecting within this family has no out-of-sample skill.

## 11. Criteria 1-7 per finalist (CA)

| | 1-3 (full) | 4 family WF/PBO | 5 neighbourhood | 6 hindsight | 7 pre-2000 | overall |
|---|---|---|---|---|---|---|
| KX3 | pass | fail (PBO 0.60) | partial (14/14 positive, 29% pass) | fail (−QQQ ex10_beat 0.59; random menus 1/30) | contradicts mildly (ho5 −0.0012, ho10 −0.0023) | **fail** |
| KX1 | pass | fail | partial (11/11 positive, 27% pass) | fail (−QQQ 0.59/0.75; 1/30) | contradicts mildly (−0.0030 / −0.0028) | **fail** |
| B378 WS | pass (boot_p 0.054) | fail | partial (29%; offsets range −0.0017 to +0.0144) | fail (−QQQ 0.44 boot_p; 0/30) | contradicts (ho5 −0.0101) | **fail** |
| B378 combo (site) | pass (boot_p 0.073) | fail | partial (22%) | fail | contradicts (ho5 −0.0117) | **fail** |
| incumbent preset | fail (ex10_beat 0.70) | fail | — | fail (−QQQ 0.0004; random menus 40% positive) | neutral (+0.0002 / +0.0008) | **fail** |

## Conclusion

- **The incumbent can be improved inside its own frame.** The cleanest fixes are:
  - proportional instead of alphabetical buys (+0.001);
  - a 378-day lookback with no skip and semiannual rebalance;
  - no trimming of winners, holding funds while they stay in the top 2N, and spending the gain
    budget on the worst-ranked holdings first.

  Together these lift the full-protocol CA score from 0.0066 to 0.0099, ex10_beat from 0.70 to
  0.90, and cut turnover by more than half (0.105 to 0.047).
- **None of it amounts to "beats SPY with good confidence."** The out-performance:
  - needs QQQ/XLK in the menu, or a US equal-weight tilt dated from 2000;
  - comes mainly from 2000-2010;
  - has been negative in every 5-year window starting 2020-2023;
  - did not appear before 2000 on mutual-fund proxies;
  - cannot be selected out of sample (PBO 0.60).
- The only robust positive finding is relative: momentum ranking beats random ranking under the
  same tax rule (+0.8 pp/yr of score, t ≈ 7, on random menus).
- For a CA taxable account, the honest recommendation from this family is still to hold SPY,
  unless the user knowingly takes the growth/tech regime bet. If they do, KX3 is the variant with
  the best risk and robustness profile.

## Notes, caveats, reproducibility

- **The module was edited once, additively.** New knobs `trim` and `gain_order` were added for
  item (k).
  - The pre-edit file is kept as `scratch/tax_rotation/tax_rotation_v1.py.bak`. Records computed
    before the edit are read through `tr.cached_v1()` under the old code hash.
  - `verify_v1.py` re-ran six old configs under the new code, covering plain WS, shadow-NONE,
    random score, wash groups with a removed-star menu, risk-adjusted momentum and blended ranks.
    Every checkpoint and monthly value was identical (max |diff| = 0) and the full-run stats were
    equal.
- **Distributions:** the engine taxes dividends as deferred capital gains, which flatters
  high-yield and bond holdings. The finalists hold no bonds; their average cash or bond weight is
  0.
- **Terminal tax:** after-tax values assume full liquidation at the window end. The
  frozen portfolios carry 80-88% unrealized gains, so an investor who never sells (step-up at
  death) would see the deferral differently. The engine does not model this.
- **Rebalance-month luck:** the default schedules are among the best (section 8).

**Files:**
- `research/lab/results/tax_rotation_table.csv`: every record, with protocol, stage and the exact
  config.
- `scratch/tax_rotation/`:
  - `cand.json`: candidate stats;
  - `diag_ALL.json`, `wf_supp.json`: diagnostics;
  - `subperiods.csv`, `khr_paired.csv`;
  - `RESUME_NOTES.txt`;
  - scripts `s2.py`, `s3.py`, `f1.py`, `g2.py`, `final.py`, `an_*.py`.
