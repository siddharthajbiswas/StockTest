# verify_tilts: adversarial check of the style switch and the tax-managed cyclical season

Module: `research/lab/families/verify_tilts.py`. It adds a random-path placebo signal, `verify_tilts.randpath`, and two
start-shifted protocols, `full_m1` and `full_m2`. Their windows start in Feb/May/Aug/Nov and Mar/Jun/Sep/Dec, so together
with `full` every month from 2000 to 2023 is a start date. They are registered with `setdefault`, so no existing cache
key changes.

Scripts are in `research/lab/scratch/verify_tilts/`:
* `cfgs.py` defines every config, by group.
* `run.py` runs a group and writes `res_<group>_<protocol>.json`.
* `battery.py` runs `verify.battery` with `n_trials=12000` and writes `battery_{vgh,cyc}.json`.
* `replay.py` replays holdings, `bystart.py` and `an_long.py` give per-start and per-era excess, and `signal_ic.py`
  measures the pre-tax information in each signal straight from prices.

The logs are `log_*.txt`.

All figures are after-tax excess CAGR versus SPY bought and held (VFINX on `long`), in pp/yr. CA = 48.1% short-term /
28.1% long-term. "Bar 1-3" means PROTOCOL §3 items 1-3: score > 0, full > 0, ex10_beat >= 0.75, ex15_beat >= 0.85 and
boot_p <= 0.10.

## Verdict

**Both candidates FAIL. Each is a static tilt that the tax-managed execution freezes in place: growth for N5_vgh, the
XLK-heavy cyclical basket for the season rule. Each beats its own static tilt only through one episode, the 2000-02 bear
market, when the holdings were at a loss and could be switched without tax.** The mechanical checks all pass: rebalance
offsets, 1-day lag, costs, distribution-tax realism, `cover_tax`, and start dates shifted by 1 or 2 months. That is
expected, because the candidates hardly trade. The hindsight and regime tests break both.

| test (CA) | N5_vgh (value/growth 12-1 switch) | cyclical season Oct 1-May 1 |
|---|---|---|
| headline (`full`) | +1.16 / full +1.83 / 10y 88% / 15y 100% / 20y 100% / boot_p 0.026 / maxDD -53% (SPY -55%) | +0.85 / +1.44 / 91% / 94% / 96% / 0.030 / -57% (-55%) |
| deflated Sharpe, 12,000 trials | 0.012 (single-test PSR 0.945) | 0.015 (PSR 0.965) |
| same tilt held static | IWF: score **+1.21** (higher), full -0.33, boot_p 0.53 | 4 SPDRs never rebalanced: **+1.21**, full +0.46, boot_p 0.29. Same basket, same tax-managed execution, no season: +0.99 / +0.97 / boot_p 0.077 |
| rule minus static, all windows | 5y -0.19 (rule ahead in 28%), 10y -0.25 (34%), to end -0.80 (23%) | 5y -0.33 (37%), 10y -0.33 (30%), to end -0.70 (16%); starts >= 2003: rule ahead in 7% |
| long history, pre-2000 data | VIVAX/VIGRX 1994-2026: +0.61 / full +0.79 / **10y beat 60%** / boot_p 0.224, **FAIL**. 10y windows starting 1994-96 beat VFINX 0 of 12. Static VIGRX scores higher (+0.67 / +0.92) | Fidelity twin 1986-2026: +1.89 / full +0.75 / 10y 78% / **boot_p 0.146**, **FAIL**. Static Fidelity basket +2.44 / +2.14 / boot_p 0.048 beats it (rule ahead in 16% of 10y windows) |
| other index families | 3 of 11 pairs clear bar 1-3 (S&P 500/900 large-cap). 6 of 11 have negative scores (all small/mid/pure-style pairs). In every large-cap pair the static growth leg scores higher | iShares IYC/IYJ/IYM/IYW: 10y beat 73%, fails. Vanguard VCR/VIS/VAW/VGT: boot_p 0.24, fails. Without XLK: +0.40, fails. Swapping XLK for IGV: boot_p 0.20, fails |
| random placebo, same execution | 40 random IWD/IWF switching paths: **4 of 40 clear bar 1-3**. The candidate's score ranks about 93rd percentile, its full excess about 72nd | 16 random season windows with the same basket: **14 of 16 positive** (median +0.42), 5 of 16 clear bar 1-3 |
| first-path dependence of boot_p | first start 2002/04/06/08/10/12/14: 0.012/0.024/0.032/0.047/0.085/**0.113**/**0.998** | 0.04/**0.459**/**0.125**/0.056/**0.177**/**0.135**/**0.979** |
| neighbourhood | 20 of 38 clear bar 1-3. No hysteresis: all 4 fail (score -0.31 to +0.31). Lookback 189 or 315 at the exact skip and hysteresis: fail. Quarterly and standard execution: fail. On the long protocol 0 of 15 pass, and 5 of 11 neighbours have **negative** full excess | 15 of 19 clear bar 1-3. The candidate is the best of 12 boundary pairs. A gain budget of **0** does better (+1.00, boot_p 0.013), which confirms the edge is "never sell a gain" |
| verdict | **FAIL** | **FAIL** |

## Candidate A: `N5_vgh|VG_R|lb252|sk21|M|h0.06|tax1`

```json
{"kind":"weights","signal":"factor_style.rotate","params":{"menu":["IWD","IWF"],"lookback":252,"skip":21,"top_n":1,"hyst":0.06,"proxies":{"IWD":"VIVAX","IWF":"VIGRX"}},"rebalance":"M","execution":"tax","gain_budget":0.01,"requires":["IWD","IWF"],"tag":"N5_vgh|VG_R|lb252|sk21|M|h0.06|tax1"}
```

**(e) Battery: holds.**
* Headline:

  | regime | score | full | 10y beat | 15y beat | boot_p |
  |---|---|---|---|---|---|
  | CA | +1.16 | +1.83 | 88% | 100% | 0.026 |
  | FED | +1.26 | +1.88 | 88% | 100% | 0.022 |
  | NONE | +1.23 | +1.30 | 78% | 100% | 0.092 |

  The round-1 boot_p was 0.040. The battery uses 500 resamples instead of 1,000, so boot_p carries about ±0.015 of
  Monte Carlo noise.
* Rebalance offsets 0/7/14/21 days: CA score +0.86 to +1.16, full +1.12 to +1.83.
* 1-day lag: CA +1.22 / +2.03.
* Costs of 0/15/35 bps per side: CA +1.16 / +1.14 / +1.10.
* Annual distribution-tax realism: +1.93 → +1.96 (from 2000) and +1.73 → +1.80 (from 2010).
* Start dates shifted by 1 and 2 months: +1.24 (boot_p 0.032) and +1.15 (0.020).
* Deflated Sharpe: CA **0.012**. The after-tax excess Sharpe is 0.32/yr; about 0.76/yr would be needed with 12,000
  configs tried.
* Sub-periods: CA 2010-20 +1.31 and 2020-26 +1.81. The battery's 2000-2010 sub-period is silently missing, because the
  first start is 2000-07 (see Lab issues).

**Mechanism (holdings replay, `replay.py`):**
* Start 2000-07: buys IWF, because growth led on 12-1 momentum after 1999. It switches at losses through 2001-03, holds
  IWD from 2004 to 2008 and moves to IWF in 2008-12, again at a loss. It then stays 100% IWF to 2026. That is 13 trades
  in 26 years, with no tax paid during the run.
* Start 2013: frozen in IWD, -3.04 pp/yr to the end.
* Start 2016: -1.21.
* Starts 2020-2023: -0.3 to -1.8.
* Starts 2000-2012 all end in growth after 2009, and they supply every 15- and 20-year window. The "100% of 15-year
  windows" is therefore one bet: hold growth from 2009 to 2026.

**(d) Static comparison: the timing adds nothing after 2005.**
* Static IWF, scored on the same windows: score +1.21, against the rule's +1.16.
* Rule minus IWF:

  | window | mean difference | rule ahead in |
  |---|---|---|
  | 5y | -0.19 | 28% |
  | 10y | -0.25 | 34% |
  | 15y | +0.30 | 49% |
  | to end | -0.80 | 23% |

* All of the rule's advantage comes from starts in 2000-05, which escaped the 2000-02 growth crash: 10y difference
  +5.08 for 2000 and +2.03 for 2001. Every start-year from 2006 on is behind static IWF.
* Later evaluation starts (`bootstarts`): from 2004 on, static IWF scores +1.80 to +2.66, above the rule's +1.01 to
  +1.16 in every case.

**(a) Long protocol, VIVAX/VIGRX vs VFINX, 119 quarterly starts 1994-01 to 2023-07: fails.**
* CA: +0.61 / +0.79 / 10y beat **60%** / 15y 94% / boot_p 0.224.
* FED: +0.67, boot_p 0.231.
* 10-year windows starting 1994-96 beat VFINX in 0 of 12 (mean -0.50). Starts in 1997-99 win 3 of 12. In those starts
  the rule bought growth on momentum in the 1990s and was frozen in it through 2000-02, because its 1990s gains could
  not be realized.
* Static VIGRX does better: +0.67 / +0.92 / boot_p 0.185. The rule beats it in 32% of 5-year, 41% of 10-year and 23%
  of to-end windows.
* Neighbours on `long` CA (lookback 189/252/315 × hysteresis 0.03/0.06/0.10, quarterly, gb0): 0 of 15 pass. Five have
  full excess between -0.96 and -1.18.
* The pre-2000 holdout ho5 is +2.37 for the exact rule, but its neighbours range from -2.13 to +2.99.
* NONE is a different story: +1.37, boot_p 0.059, and the hysteresis-3% neighbours reach +1.70 to +1.77. Pre-tax style
  momentum is weakly real, but the CA rule cannot harvest it.

**Pre-tax information (`signal_ic.py`).** Measured as next-month return of the chosen style minus the other:
* VIVAX/VIGRX signal traded as IWD/IWF: +2.97%/yr, t = 1.45 (2000-26), and -1.0%/yr over 2009-16.
* On VIVAX/VIGRX itself, 1993-2026: +3.62%/yr, t = 2.03.
* Own-history signals elsewhere: IJS/IJT t = -1.36, RPV/RPG -0.44, IWN/IWO +0.35, VTV/VUG +0.95, IVE/IVW +1.66.

**(b) Same rule on other style pairs (`full`, CA; ETF-only signals start 400 days after launch).**

| pair | rule: score / full / boot_p | static growth leg: score / full / boot_p |
|---|---|---|
| SPYV/SPYG | +1.04 / +1.86 / 0.013 (passes) | SPYG +1.22 / +0.64 / 0.268 |
| IUSV/IUSG | +0.45 / +1.61 / 0.014 (passes) | IUSG +1.01 / +0.96 / 0.089 |
| IVE/IVW, own signal | +0.53 / +1.15 / 0.063 (passes) | IVW +1.06 / +1.05 / 0.105 |
| IVE/IVW, VIVAX/VIGRX proxies | +0.66 / +0.94 / 0.112 | same |
| VTV/VUG | +0.71 / +1.57 / 0.082 (10y beat 70%) | VUG +1.68 / +1.68 / 0.069 |
| IWX/IWY (from 2011) | +2.00 / +2.55 / 0.028 (10y beat 74%) | IWY +3.11 / +2.73 / 0.025 |
| IJS/IJT | -0.37 | IJT +0.18 |
| IWS/IWP | -0.54 | IWP +0.16 |
| RPV/RPG | -0.83 | RPG +0.22 |
| VBR/VBK | -1.65 | VBK -0.92 |
| IWN/IWO | -1.72 | IWO -0.76 |
| RZV/RZG | -3.41 | RZG -2.26 |

The rule works only where large-cap growth won, and there the static growth fund scores higher.

**Placebo.** 40 date-determined random switching paths between IWD and IWF (switch probability 3% a month), with the
same tax-managed execution:
* median score -0.16, but 4 of 40 clear bar 1-3 in CA;
* 3 of 40 reach the candidate's score (+1.16), and 11 of 40 reach its full excess (+1.83).

The tax freeze alone turns a coin flip into a CA "pass" one time in ten.

**Inverted signal** (style reversal, same execution): -1.40. The sign matters only because the inverted rule is frozen
in value after 2009.

**(c) Neighbourhood (`full`, CA, 38 configs): 20 of 38 clear bar 1-3, with structured failures.**
* All four no-hysteresis versions fail.
* Lookback 189 and 315 at sk21 / h0.06 fail: 10y beat 65% / 69%, 15y beat 64% / 62%.
* Lookback 126: score -0.15.
* Quarterly (boot_p 0.20), every 2 months (0.235) and standard execution (+0.22): all fail.
* What survives needs hysteresis of at least 3% plus tax execution, which are exactly the ingredients that freeze the
  book.

**Verdict A: FAIL.** The CA result is static growth exposure since 2008-12 plus one escape from the 2000-02 crash for
starts in 2000-05. It loses to static IWF on most windows, fails its own pre-2000 regime test, fails on other style
pairs and on long-history neighbours, and has a deflated Sharpe of 0.012. Someone starting today inherits whichever
style leads now and stays frozen in it.

## Candidate B: tax-managed cyclical season, Oct 1-May 1

```json
{"kind":"weights","signal":"seasonal.cal","params":{"layers":[{"rule":{"type":"window","start":[10,1],"end":[5,1]},"w":{"XLY":0.25,"XLI":0.25,"XLB":0.25,"XLK":0.25}}],"default":{"SPY":1},"rebalance_states":true},"rebalance":"M","execution":"tax","gain_budget":0.01}
```

**(e) Battery: holds.**
* Headline:

  | regime | score | full | 10y beat | 15y beat | boot_p |
  |---|---|---|---|---|---|
  | CA | +0.85 | +1.44 | 91% | 94% | 0.030 |
  | FED | +0.96 | +1.49 | 93% | 98% | 0.024 |
  | NONE | +1.22 | +1.31 | 90% | 96% | 0.038 |

* Offsets: CA score +0.83 to +0.91.
* 1-day lag: CA +0.82 / +1.54.
* Costs of 0/15/35 bps per side: CA +0.92 / +0.74 / +0.44, against NONE +1.67 / +0.31 / -1.48.
* Realism: about +0.02.
* `cover_tax=True` (pay the January tax bill by selling instead of a 0% cash loan): identical, +0.85.
* Start dates shifted by 1 and 2 months: +0.84 (boot_p 0.017) and +0.90 (0.012).
* Sub-periods (CA): 2000-10 **+2.43**, 2010-20 +0.32, 2020-26 **-1.29**.
* Deflated Sharpe: CA **0.015**.

**Mechanism (holdings replay):** the starting state decides the book.

| start | holdings at the end |
|---|---|
| 2000-01 | about 80% cyclicals (XLK 31%) by 2026 |
| 2003-07 | 97% SPY by 2026, after selling the cyclicals at a loss in 2009 |
| 2009-07 | 100% SPY |
| 2013-01 | 82% cyclicals |
| 2013-07 | 54% SPY |
| 2020-07 | 75% SPY |

To-end excess by start year:
* 2000: +1.60
* 2001: +1.35
* 2002: +0.89
* 2003-08: +0.2 to +0.9
* 2009-2023: mean about **+0.03**, range -0.68 to +0.74

**(d) Static comparison: the season subtracts value except in 2000-01.**
* Never-rebalanced cyclical SPDRs score **+1.21** (every 10- and 15-year window positive), above the rule's +0.85.
* Rule minus static basket:

  | window | mean difference | rule ahead in |
  |---|---|---|
  | 10y | -0.33 | 30% |
  | to end | -0.70 | 16% |
  | to end, starts from 2003 on | -0.83 | 7% |

* The same basket held all year under the same tax-managed monthly execution, with no season, gives +0.99 / +0.97 /
  10y 100% / 15y 98% / boot_p 0.077, which nearly clears bar 1-3 by itself.
* Static XLK alone: +2.49 (boot_p 0.415).
* With later first starts (`bootstarts`, 2002-2014), static cyc4 scores +0.82 to +1.14 and beats the rule (+0.64 down
  to -0.04) every time. The rule's boot_p rises to 0.459 (2004), 0.177 (2010) and 0.979 (2014).

**(a) Long protocol: Fidelity Select twin with the Oct 1-May 1 boundary, 1986-2026 vs VFINX.** Round 1 never ran this
twin.
* Round-1 map (FSRPX/FSDAX/FSDPX/FSPTX), CA: +1.89 / full +0.75 / 10y 78% / 15y 95% / **boot_p 0.146**, which fails.
  * The static buy-and-hold of the same four funds does better: +2.44 / +2.14 / boot_p 0.048.
  * The rule beats the static basket in 36% of 5-year, 16% of 10-year and 21% of to-end windows (10y mean -0.67).
  * Pre-2000 holdout (ho5, 5-year windows ending by 2000): +1.30. For comparison, 5-year windows starting
    1986-93 average +1.61 and beat VFINX in 59%.
* Alternative Fidelity maps, season vs static, CA:

  | map | season: score / boot_p | static: score / boot_p |
  |---|---|---|
  | alt1 FDLSX/FSRFX/FSCHX/FSELX | +2.45 / 0.013 | +3.02 / 0.010 |
  | alt2 FSAVX/FSRFX/FSDPX/FDCPX | +1.24 / 0.43 | +1.12 / 0.20 |
  | alt3 FSHOX/FSDAX/FSCHX/FSCSX | +2.14 / 0.050 | +2.86 / 0.053 |
  | no tech | +1.39, full -0.13 | +1.76 |

  In CA the season overlay beats static in score only for alt2. In NONE the season beats static for alt1/alt2/alt3,
  which is the pre-tax effect.
* Reversed season: about 0.
* Fidelity Selects are survivors with historical loads, so their static excess over VFINX is itself inflated.

**Pre-tax seasonality (`signal_ic.py`).** Measured as the monthly return of the equal-weight basket minus SPY, in-season
vs out-of-season:
* 2000-26: +3.25 vs -1.39 %/yr, t = 2.32.
* **2017-26: +0.80 vs +0.86, t = -0.02.** The effect is gone in the last decade.
* Fidelity maps 1986-99: t = 1.2 to 2.2.

The CA rule does not harvest this effect anyway, because the gain budget freezes it.

**(b) Other sector sets (`full`, CA, same rule):**

| set | score | other stats | static |
|---|---|---|---|
| iShares IYC/IYJ/IYM/IYW (same sectors, other index provider) | +0.53 | full +1.38, **10y beat 73%**, boot_p 0.056: fails | +0.83 |
| Vanguard VCR/VIS/VAW/VGT (from 2004) | +0.67 | **boot_p 0.243**: fails | +1.24, boot_p 0.035 |
| no tech | +0.40 | boot_p 0.29 | |
| XLK swapped for IGV | +0.59 | boot_p 0.20 | |
| XLK swapped for SMH | +1.18 | boot_p 0.029: passes | +1.66 |
| XLK only | +2.02 | boot_p 0.106 | |
| cyclicals ex tech, with XLF/XLE | -0.08 | | |
| 6 cyclicals | +0.30 | | |
| defensives (placebo) | -0.46 | | |
| all 9 SPDRs | +0.08 | | |

It passes only where the basket holds XLK or semis.

**Placebos:**
* 16 random season windows of 4-8 months, same basket and execution: 14 of 16 positive (median +0.42), 5 of 16 clear
  bar 1-3.
* The Halloween-like windows rank highest: 9/1-5/1 +0.80 and 9/15-5/15 +0.63. Non-seasonal windows such as 6/15-2/15
  (+0.48, 10y 93%) and 7/15-3/15 (+0.53) are positive too.
* Reversed season (cyclicals May-Oct): -0.17 (and -0.16 on both shifted protocols). The ratchet goes into SPY instead
  of into the tilt.

**(c) Neighbourhood (`full`, CA, 19 configs): 15 of 19 clear bar 1-3.**
* 12 boundary pairs (start 9/15-11/1 × end 4/15-5/15): all positive, +0.45 to +0.85. The candidate is the best, so its
  number carries selection bias.
* Gain budgets: gb0 +1.00 (boot_p 0.013), gb0.005 +0.92, gb0.02 +0.71, gb0.05 +0.32 (fails).
* Quarterly +0.83, no short-term gains +0.84.
* The best "variant" is never realizing a gain at all. That is buy-and-hold plus loss-switching, not seasonality.

**Verdict B: FAIL.** In CA the rule is a ratchet into a static, XLK-heavy cyclical tilt, plus one lucky exit in May
2000.
* It loses to the same basket held static in 84% of to-end windows and 93% of those starting from 2003 on.
* Its long-history twin fails boot_p and loses to its own static basket.
* It fails with the same sectors from iShares or Vanguard, and without XLK.
* The pre-tax seasonal effect is zero over 2017-26.
* Deflated Sharpe 0.015. The 2020-26 sub-period is -1.29.

## Lab issues found (no core files edited)

1. **boot_p and max_dd come only from the first start's path** (`metrics.summary`). For tax-frozen strategies that
   path is the luckiest one: the 2000 start escaped the crash at a loss. Moving the first start changes boot_p:
   * N5_vgh: 0.026 → 0.113 (from 2012) and 0.998 (from 2014).
   * Cyclical season: 0.030 → 0.459 (from 2004) and 0.979 (from 2014).

   Suggest reporting the median boot_p over several first starts, or a bootstrap over start dates.
2. **`verify.battery` drops the 2000-2010 sub-period** when the first start is after 2000-01-01, because it looks for an
   exact window start of 2000-01-01. N5_vgh starts 2000-07, so its battery hides the one sub-period where its timing
   paid.
3. **The quarterly-start grid interacts with season boundaries.** For example, Oct 1 is "in season", so 3 of 4 quarterly
   starts buy cyclicals. The new `full_m1` / `full_m2` protocols check this. Here the shift did not change the
   numbers, but they are worth using for any calendar rule.
4. `cover_tax` (the engine pays the January tax from cash at 0%) has no effect on these candidates. The engine bias is
   immaterial here: N5_vgh paid no tax during the 2000-07 run.

## Configs run in this session

239 distinct configs and 355 config × regime × protocol runs, plus the two batteries (about 27 runs each).
By group:

| group | configs | protocol / regimes |
|---|---|---|
| vgh_controls | 6 | full ×3 |
| vgh_neigh_small | 38 | full CA |
| vgh_pairs | 34 | full CA/NONE |
| vgh_placebo | 40 | full CA |
| vgh_long | 15 | long ×3 |
| cyc_controls | 5 | full ×3 |
| cyc_long | 12 | long ×3 |
| shift_set | 6 | full_m1 and full_m2, CA |
| cyc_sets | 20 | full CA |
| cyc_neigh_small | 19 | full CA |
| cyc_placebo_small | 16 | full CA |
| bootstarts | 28 | full CA |

The larger planned grids `vgh_neigh` (88) and `cyc_neigh` / `cyc_placebo` (33 / 30) were trimmed for speed and were not
run. The whole-search trial count rises from about 12,000 to about 12,250.
