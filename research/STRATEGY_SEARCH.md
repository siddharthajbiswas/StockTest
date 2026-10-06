# Strategy search: what beats buying and holding the S&P 500 after tax?

*Status, 2026-10-05: complete. Round 1 (13 strategy families), adversarial verification, round 2 and
three independent final reviews are done. Round-2 completeness items that finished last are summarized in
the addendum at the end.*

**The question.** Which investing strategy beats buying and holding the S&P 500 (SPY) after tax
and trading costs, with good confidence, in an ordinary taxable brokerage account? The primary
tax case is a California single filer earning about $300k: 48.1% on short-term gains and 28.1% on
long-term gains. The secondary case is federal rates only, 35% / 15%. Every number comes from the
StockTest website's own backtesting engine, unless it is marked as research-only.

**How to read the numbers.** "Excess" means the strategy's after-tax CAGR minus SPY's after-tax
CAGR over the same window, in the same tax regime and with the same costs. It is given in
percentage points per year (pp/yr), and a positive excess means the strategy won. "Score" is the
pre-registered ranking statistic: the average excess over every 5-, 10- and 15-year window.
"Full" is the excess from the first start date to mid-2026.

---

## 1. Bottom line

### Final recommendation (2026-10-05)

**For a California taxable brokerage account: buy and hold a low-cost S&P 500 index fund (VOO or
IVV; SPY is equivalent) and sell as little as possible.** Roughly 15,000+ configurations were
tested: 13,778 in 13 strategy families in round 1, plus thousands more in adversarial verification
and round 2, across 95 start dates, 3- to 20-year windows, and histories back to 1930. **No
strategy beats buy-and-hold after California tax and costs with good confidence.** Three
independent final reviews (statistics, risk, implementation/tax) reached the same pick, each with
high confidence.

**Why it is so hard to beat.** In a taxable account, buy-and-hold never realizes a gain until the
end and then pays only the long-term rate once. If the shares are held until death (step-up in
basis) or donated, that last tax disappears too. Every other strategy realizes gains along the way.
In this engine, any after-tax win therefore has to come from pre-tax return, and every rule with a
real pre-tax edge lost most or all of it to California's 48.1% short-term rate.

**If you deliberately want a bet** (expected-value upside, not a confident edge):
- Keep at least **75-80% in a never-sold S&P 500 fund**.
- Run **at most a 20-25% satellite** with the website's **"2× S&P trend, leveraged (CA)"** preset:
  hold SSO (2× S&P 500) while SPY closes more than 3% above its 175-day average, and IEF
  (intermediate Treasuries) once it closes more than 3% below.
- Check it every trading day and trade with market-on-close orders on the day the signal flips.

What to expect from the satellite:

| | |
|---|---|
| Realistic after-tax edge (CA) | **about +1 pp/yr** (plausible range −1 to +2.5); about +0.2-0.3 pp/yr for the whole account at 20-25% |
| Chance of trailing SPY over 20 years | 25-50% |
| Bad years | it can fall harder than the index in fast sell-offs (2022: about −37% vs −25%) |
| Execution | one day late in Oct 1987 turned a clean escape into a −59% drawdown |

**Do not use the older "Beat the S&P (CA)" tax-managed momentum preset as a way to beat the S&P.**
Its expected edge is about zero:
- its lead over SPY needs QQQ/XLK in the menu, which is hindsight;
- the lead comes mostly from 2000-2010;
- its holdings freeze into a 50-60% growth/tech book that cannot be sold without a large tax bill.

| Best of each class (CA, after tax, vs SPY) | Result | Verdict |
|---|---|---|
| Buy & hold an S&P 500 fund | 0 by construction (VOO/IVV +0.03-0.04 on fees) | **the pick** |
| 2× trend (SSO/IEF, SMA175, 3% band), real ETFs 2006-2026 (the website preset) | full +3.67 pp/yr, score +4.48, 100% of 10/15-yr windows, boot p 0.116, max DD −48% vs −55% | conditional: the setting is the luckiest of 34 neighbours, and SMA200 scores only +1.6 to +2.4 on the same data |
| 2× trend, 2000-2026 / 1986-2026 / 1930-1985 holdout | score +4.9 (p 0.077) / +4.6 (p 0.067) / +3.0 (p 0.27) | positive everywhere, but not significant out of sample; about 0 since 2010 |
| 2× trend applied to 33 other stock markets | median +0.24, pooled −0.53 (p 0.60) | fails: the S&P result was partly luck |
| 3× trend (UPRO) | score up to +9.7 | rejected: −88% to −93% in 1929-35; a 17-24% chance of an 80%+ drawdown in 20 years |
| Tax-managed momentum (site preset / refined KX3) | score +0.66 / +0.99 | fails hindsight, holdout and regime tests; expected about 0 |
| Every other family (timing, TAA, risk parity, vol targeting, seasonality, mean reversion, VIX, macro, factor, global, sector, stocks, pure tax structures, combinations) | negative or about 0 after CA tax | fail |

**What would change this answer:**
- **The 2× trend rule keeps working:** it keeps beating SPY after tax through the next bear market,
  since its edge has been dormant since 2010.
- **You also have tax-advantaged money:** in an IRA or Roth the leveraged trend rule's numbers are
  stronger (no-tax 2006-26: +7.2 pp/yr, p 0.016). That is an asset-location question, not a
  reason to run it in a taxable account.
- **Different tax vehicles or cheaper leverage:** the Section 1256 futures and options-overlay
  research was still finishing as this was written (see the round-2 addendum at the end).

### What round 1 and verification have already settled

1. **Nothing cleared the bar.** The search tried 13,778 configurations in 13 families. None passes
   all seven items of the pre-registered "good confidence" bar in the California regime, or in the
   federal one. For a taxable account the default is still to buy and hold an S&P 500 fund. Which
   fund does not matter: in this data IVV and VOO beat SPY by only +0.03 to +0.04 pp/yr.
2. **The only unlevered survivor is tax-managed momentum rotation, and it is a modest tilt rather
   than a way to beat the S&P 500.** Its best versions (KX3, KX1) score about +0.9 to +1.0 pp/yr
   after CA tax. The website's existing "Beat the S&P (CA)" preset scores +0.66. The momentum
   signal is real: under identical execution it beats random picks by +0.7 to +0.9 pp/yr. But the
   lead over SPY is fragile:
   * It depends on QQQ or XLK being in the menu. Without both, KX3 scores -0.26 and KX1 +0.12.
   * It comes mostly from the 2000-2010 decade.
   * Its headline significance comes from the January 2000 start, when only 3 of the 22 menu ETFs
     had enough history. Scored only from 2002 on, KX3 fails items 1-3.

   The deflated Sharpe is 0.04-0.05, and KX3 is not detectably better than the website preset
   (+0.28 pp/yr, p 0.38). See section 4.1.
3. **The leveraged survivor is a 2x S&P 500 fund with a daily trend filter** (175-day average, 3%
   band, intermediate Treasuries when out). It earned about +3 to +5 pp/yr after CA tax in every
   history tested: 2000-2026, 1986-2026 and 1930-1985. Trading at the close, its drawdowns were at
   or below the index's.
   Confidence is only moderate (p 0.07-0.27, deflated Sharpe 0.0035), and most of the excess is
   paid-for leverage. It is **conditional**, not a pass. The 3x version, which had the biggest
   numbers, was rejected for ruin-level tail risk: -88% to -93% in 1929-35, and a 17-24% chance
   of an 80%+ drawdown within 20 years. See section 4.2.
4. **Taxes decide almost everything.** Most rules with a real pre-tax edge lose after California
   tax. In this engine, buying SPY and holding it is already the most tax-efficient thing you can
   do (section 5).

---

## 2. How the search worked

Full methods: [`lab/REPORT_METHODS.md`](lab/REPORT_METHODS.md). Rules: [`lab/PROTOCOL.md`](lab/PROTOCOL.md).

| | |
|---|---|
| Strategy families | 13, each searched by its own research agent |
| Configurations tested | **13,778**. Every one counts toward the multiple-testing penalty. |
| Verification | 7 adversarial agents re-tested the 13 round-1 finalists: about 3,000 more variants (robustness checks, not new search) and about 11,000 permutation placements |
| Start dates | **95** quarterly starts, 2000-01 to 2023-07, each run to 2026-07 |
| Windows | every **3-, 5-, 10-, 15- and 20-year** window, plus "to mid-2026" (67 ten-year windows, for example). Each is compared with SPY bought and held over the same dates. |
| Tax regimes | **CA** 48.1% / 28.1% (primary), **FED** 35% / 15% (secondary), **NONE** = IRA / 401(k) (diagnostic only) |
| Longer histories | **1986-2026** using index, sector and bond mutual funds (VFINX benchmark). Windows that end before 2000 are a true holdout for ideas found on ETF-era data. **1930-2026** for the leverage finalists: S&P 500 index data run through a simulator that matches the engine to the 4th decimal. |
| Costs and accounting | $100,000 start; 5 bps commission + 5 bps slippage per side; FIFO tax lots; short- vs long-term at 365 days; tax settled each January; losses carried forward; everything sold and taxed at the end of every window, so churning strategies and SPY are compared fully after tax |
| Parity with the website | `research/lab/validate_lab.py` re-ran 36 windows through the site's own request path (3 strategies x 3 regimes x 4 windows). **Worst difference in after-tax CAGR: 0.0.** The site's JavaScript engine is pinned to the same Python engine by the golden-oracle test suite. |

**Research-only numbers.** These are clearly marked where they appear, because the website cannot
reproduce them:
* synthetic leveraged funds before SSO (2006) and UPRO (2009) existed;
* the 1930-1985 simulator;
* the "realism" replays that tax distributions every year;
* off-engine proxies.

**The "good confidence" bar** (PROTOCOL section 3). A strategy must pass all seven items in its
own regime:
1. Score > 0 and full-period excess > 0.
2. It beats SPY in at least 75% of 10-year windows and at least 85% of 15-year windows.
3. Bootstrap p <= 0.10.
4. Its family's walk-forward selection is positive out of sample, and PBO < 0.5.
5. Its parameter neighbourhood also passes.
6. It does not depend on one instrument chosen with hindsight.
7. The pre-2000 holdout does not contradict it.

**Statistics used.**
* **Beat rate:** the share of windows in which the strategy beat SPY.
* **Boot p:** a stationary block-bootstrap p-value for "true excess <= 0", from the first start's
  monthly path.
* **Walk-forward:** pick the family's best config on the trailing 10 years, then score it on the
  next 5. This is the honest estimate of what running the search would have earned.
* **PBO:** the probability that the backtest is overfitted.
* **DSR:** the deflated Sharpe ratio. It discounts a result by the number of configurations tried;
  0.95 is the usual pass mark.

**Stages.**
1. **Round 1.** Each family screened its ideas on 24 yearly starts in CA and NONE. It then ran up to
   about 30 finalists on all 95 starts in all three regimes, and on 1986-2026 where proxies exist.
   Every family also ran:
   * hindsight controls: random menus from a fixed pool of 90 ETFs that existed by 2003, and the
     rule with its "star" fund removed;
   * rebalance-date offsets;
   * a one-day execution lag;
   * cost stress;
   * a yearly distribution-tax replay.
2. **Critic.** A cross-family review of coverage gaps, suspicious results and lab bugs
   (`critic.json`).
3. **Verification.** Seven agents attacked the 13 finalists: code and trade-log audits, rebalance
   timing, start dates, menus, long history, crash injection and the deflated Sharpe.
4. **Round 2, still running.** Twelve agents cover:
   * Section 1256 futures;
   * valuation (CAPE) allocation;
   * crash protection that never sells the core;
   * ways a position ends other than a sale (step-up at death, gifts, slow retirement sales);
   * HIFO lots and IRS netting;
   * the trend rule on other markets;
   * cross-family combinations held in one account;
   * a pre-registered 2x leverage + trend grid;
   * a final rotation test on menus rebuilt by a fixed rule each year.

---

## 3. What failed and why

One row per family. "Items" refers to the 7-item bar above. Numbers are CA, after tax, versus SPY
bought and held.

| Group | Family (configs) | Verdict | The most telling number | Why |
|---|---|---|---|---|
| Timing / trend | `trend_timing` (875) | Fail | **0 of 662** screened SPY timing rules beat SPY in any 10-year window starting 2009 or later | The whole edge is sidestepping the 2000-02 and 2008 bears. The best rule (EMA100/200 cross into Treasuries) scores +1.01 but beats SPY in only 57% of 10-year windows (p 0.29, family PBO 0.69), and the 1986-99 holdout is -2.78 pp/yr (0% beat). Exits realize gains, and the Treasury leg supplies 0.6-1.1 pp/yr of every result. Timing does halve drawdowns, but a never-rebalanced 70/30 SPY/Treasury mix buys the same cut with a better Sharpe, and more cheaply over 1986-2026. |
| Tactical asset allocation | `taa_models` (925) | Fail | **47** configs positive before tax, **0** positive after CA tax (median drag 2.6 pp/yr) | Tax drag is about 0.75 + 0.23 x turnover pp/yr. The published models (GEM, ADM, VAA, DAA, HAA, GTAA...) score -1.4 to -7.6. The best scores +0.03, with a 10-year beat rate of 0.49. Every finalist led by +4.6 to +13.6 in 2000-10 and then trailed by 4.6-8.9 in 2010-20. |
| Risk / volatility | `risk_alloc` (558) | Fail | Unlevered vol targeting: median **-1.06** pp/yr (best +0.14, p 0.77) | Lower risk brought lower return, and de-risking sales realize gains. Risk parity scores -1.4 to -7.7. The levered vol target (+3.40) is matched by a never-rebalanced 50/50 SPY/SSO (+3.39). Verification failed it (see below). |
| Seasonality | `seasonal` (862) | Fail | Median of 262 pre-registered calendar rules: **-3.47** pp/yr; none clears items 1-3 | Switching twice a year turns deferred gains into 48.1% short-term gains. The only CA pass (tax-managed cyclicals Oct-May, +0.85) is really a frozen, XLK-heavy sector tilt: the same basket with no season does as well (+0.99). |
| Mean reversion / VIX | `mean_reversion` (2,039) | Fail | **0 of 260** unlevered dip timers have a positive CA score (best -4.3) | They spend time out of the market and realize short-term gains. Only leveraged structures come out positive: the UPRO dip sleeve scores +3.44, but its DSR is 0.06 and it cannot be told apart from constant leverage. |
| Macro / regime | `macro_regime` (750) | Fail | Two recessions (2001, 2007) supply **120-146%** of the leaders' CA excess | The leading yield-curve un-inversion rules score +3.1 to +3.9, but beat SPY in only 57-64% of 10-year windows. On the standard curve the leader drops to +2.67 (p 0.23). The family's walk-forward is -3.38 pp/yr. |
| Factor / style | `factor_style` (1,661) | Fail | The value/growth switch scores **+1.16**; just holding IWF over the same windows scores **+1.21** | Every pass is the 2007-2026 growth era, held in place by tax-managed execution. The 1994-2026 index-fund twin fails (p 0.22), and 4 of 40 random switching paths also pass. |
| Global | `global` (1,459) | Fail | The best rule (SPY vs VEIEX) **traded twice in 26 years**; 0 of 47 five-year windows starting 2010 or later beat SPY | Nearly every positive result (133 of 140) is an emerging-markets bet, mainly VEIEX held from 2001 to 2011. The ETF twin scores -2.06, and the 1986-99 holdout is negative. |
| Sector rotation | `sector_deep` (1,170) | Fail | Under the same tax-managed execution, **random picks score +1.11** vs momentum's **+1.28** (medians, 32 Fidelity/Vanguard sector funds, 1986-2023) | The gain comes from the execution, not the selection. The website preset's rule scores -0.06 / -0.10 on the 9 / 11 SPDR sector funds. Fidelity Select proxies paid out 4-5% a year; taxing that yearly removes 0.2-1.2 pp/yr. |
| Individual stocks | `stocks` (280) | Fail (cannot be measured) | **20 random stocks** "beat" SPY by +3.24 pp/yr; 9 of 10 random seeds pass items 1-3 | Survivorship: only 37% of the S&P 500's 2000 members are in the data. Signals versus random picks: -0.43 pp/yr. 69% of the best finalist's profit is AAPL. |
| Pure tax structures | `tax_structures` (475) | Fail (by construction) | No harvesting or tax-aware structure improved on SPY's tax efficiency by more than **0.004 pp/yr** (511 decomposed runs) | Holding SPY forever already pays the least tax the engine allows (section 5). Tax-loss harvesting on an SPY core (102 configs) averages -0.04 pp/yr. Harvesting is worth about +0.2 pp/yr, and only outside the engine. |
| *Survivor* | `tax_rotation` (1,794) | Fails the full bar; survives as a modest tilt (section 4.1) | KX3 / KX1 score **+0.99 / +0.93** vs the preset's +0.66. Without QQQ and XLK: **-0.26 / +0.12** | Real momentum signal, but the lead over SPY depends on the menu, the era and the start date. |
| *Survivor* | `leverage` (930) | 3x fails; 2x is conditional (section 4.2) | 3x SMA175/3%: **+9.65** (p 0.029), but picked after the fact (DSR 0.013) | The excess is mostly paid-for leverage. Static leverage, HFEA, vol targeting, monthly-check and QQQ-based rules all failed clearly (below). |

### Promoted to verification, then failed

| Candidate (family) | Round-1 CA headline | What verification found | Report |
|---|---|---|---|
| Tax-aware levered vol target, TVT (`risk_alloc`) | +3.40, full +4.85, p 0.011 (2006+) | After 2009 the 1% gain budget froze exposure at 1.6-1.9x, so vol targeting was effectively off (beta 1.57, alpha about 0). A constant 1.8x scores higher (+5.06). Fails on 1986-2026 (p 0.26). 25% of loss dollars broke the wash-sale rule. | `verify_levvt.md` |
| Curve un-inversion 540 days, min_len 90 (`macro_regime`) | +3.87, p 0.064 | The edge is two events. The min_len 90 filter only works on the lab's discount-yield curve; on the standard curve the score is +2.67 (p 0.23). DSR 0.022. | `verify_curve.md` |
| GATED curve + SPY 200-day (`macro_regime`) | +3.12, p 0.101 | The headline is the luckiest of 28 equivalent monthly check days (median +1.63). DSR 0.004. | `verify_curve.md` |
| Value/growth 12-1 switch, N5_vgh (`factor_style`) | +1.16, p 0.040 | Static IWF scores higher on the same windows. 13 trades in 26 years. The long twin fails. DSR 0.012. | `verify_tilts.md` |
| Tax-managed cyclical season (`seasonal`) | +0.85, p 0.035 | A frozen basket: the same basket with no season scores +0.99, and a zero gain budget +1.00 (p 0.013). Without XLK: +0.40 (fails). DSR 0.015. | `verify_tilts.md` |
| 3x SMA200 / 2% band, the pre-registered rule (`leverage`) | +6.07, p 0.117 | Misses item 3 in CA. DSR 0.003. 2020-26: -0.29 pp/yr. -91% drawdown in 1930-85. | `verify_lev_mech.md`, `verify_lev_robust.md` |
| Low-vol 3x / 1x (`leverage`) | +5.14, p 0.039 | No edge in the 1930-85 holdout (full -0.3, p 0.51). Lost 19 pp to the index in 1987. Drawdowns of -65% to -84%. | `verify_lev_robust.md` |
| SSO EMA100/200 cross (`trend_timing`) | +6.34, p 0.034 (2006+) | 4 switches since 2006, and a Sharpe equal to SPY's (0.65), so the excess is leverage. No edge in 1930-85 (+0.4, p 0.54). | `verify_lev_robust.md` |
| 3x SMA175 / 3% band, picked after the fact (`leverage`) | +9.65, p 0.029 | Mechanically sound, but tail risk is unacceptable (section 4.2) | `verify_lev_mech.md`, `verify_lev_robust.md` |
| Unlevered EMA100/200 cross (`trend_timing`) | +1.01, p 0.29 | Carried as the unlevered reference. It had already failed in round 1 (10-year beat 0.57, holdout -2.78). | `trend_timing.md` |

**Other failures inside the two surviving families.**
* 3x S&P bought and held from 2000: -1.32 pp/yr, a -98% drawdown, and 47% of starts lost more
  than half their value after tax.
* HFEA (55% UPRO / 45% TMF): +6.72 but p 0.18; 2022 was -61.6% vs SPY's -16.8%.
* Monthly-check leverage rules are check-day luck. Shifting the month boundary gives +6.59 / +1.11
  / +3.50 / +1.47.
* QQQ-based leverage is hindsight. On 20 random funds the median is -4.07, and 13 of 20 had
  drawdowns worse than -80%.
* Tax-loss harvesting, absolute-momentum filters and adding bond, country or factor ETFs to the
  rotation menu all hurt the rotation.

---

## 4. What survived verification

### 4.1 Tax-managed momentum rotation: the website preset, KX1 and KX3

**The rules.** All three hold the top 5 of the same 22-ETF menu: SPY, QQQ, DIA, MDY, IWM, IJR, EFA,
EEM, IWD, IWF, RSP and the 11 sector SPDRs. They sell at a gain only within a yearly realized-gain
budget, always sell losses, and wait 31 days before buying back after a loss.

| | Signal | Rebalance | Gain budget | Execution |
|---|---|---|---|---|
| **INC**, the website preset "Beat the S&P (CA)" (`TaxManagedCombo`) | 12-1 month momentum | quarterly | 1% of portfolio/yr | sells the smallest gains first; buys in alphabetical order |
| **KX1** (lab only) | 12-1 month momentum | quarterly | 2%, long-term gains only | "K-execution": keeps a holding while it ranks in the top 10, never trims a fund the signal still wants, spends the budget on the worst-ranked holding first, buys proportionally |
| **KX3** (lab only) | 18-month (378-day) momentum, no skip | semiannual | 1% | K-execution |
| **B378 combo** (runs on the site today) | 378-day momentum | semiannual | 1% | the site's `TaxManagedCombo` |

**Headline numbers** (95 starts, 2000-2026; `verify_taxrot_mech.md`):

| | Regime | Score | Full | 10y beat | 15y beat | 20y beat | Boot p | Max DD (SPY -55.2%) | After-tax IR |
|---|---|---|---|---|---|---|---|---|---|
| KX3 | CA | +0.99 | +1.84 | 90% | 85% | 96% | 0.011 | -53.7% | 0.42 |
| KX3 | FED | +1.10 | +1.94 | 90% | 87% | 100% | 0.006 | -53.7% | 0.44 |
| KX1 | CA | +0.93 | +1.82 | 91% | 89% | 96% | 0.011 | -56.6% | 0.45 |
| KX1 | FED | +1.05 | +1.96 | 93% | 91% | 100% | 0.009 | -56.3% | 0.47 |
| INC (site preset) | CA | +0.66 | +1.54 | 70% | 83% | 100% | 0.026 | -56.6% | 0.28 |
| INC (site preset) | FED | +0.74 | +1.60 | 69% | 85% | 100% | 0.020 | -56.6% | 0.29 |
| B378 combo (site) | CA | +0.79 | +1.05 | 82% | 91% | | 0.073 | -56.7% | |

KX3 and KX1 pass items 1-3 in CA and FED. The preset fails item 2. The KX3, KX1 and preset
numbers reproduced exactly in verification. The code does what its label says, and there is no
look-ahead: re-running with all data clipped at three different dates reproduces every earlier
order exactly.

**What holds.**
* The 95-window score is robust to execution details:
  * a one-day lag gives KX3 +1.09 and KX1 +1.02;
  * at 35 bps per side, KX3 scores +0.88 and KX1 +0.74;
  * yearly distribution tax helps slightly (+0.03 to +0.06);
  * all 26 weekly rebalance offsets of KX3 have a positive score.
* On the incumbent menu, positive scores form a broad plateau: 61 of 62 neighbouring parameter sets
  are positive.
* **The momentum signal is real.** Under the identical execution, ranking by momentum beats
  ranking at random:
  * by +0.72 (t 5.7) and +0.80 (t 7.2) on 30 random menus that nobody chose;
  * on 80-90% of those menus;
  * also from starts after 2001;
  * on the pre-ETF mutual-fund copy of the menu (+0.6 to +0.9).

**What breaks.**

| Test (CA, pp/yr) | KX3 | KX1 | INC (site preset) |
|---|---|---|---|
| Score across weekly rebalance-date offsets, mean [min, max] | +0.94 [+0.65, +1.27] (26 offsets) | +0.76 [+0.38, +1.13] (13) | +0.61 [+0.35, +0.88] (13) |
| Full-period excess across offsets, mean (median) | +1.18 (+1.00); the default date ranks 3rd | +1.14 (+0.97) | +1.18 (+1.38) |
| Offsets that pass items 1-3 | 9 of 26 | 4 of 13 | 0 of 13 |
| Scored only from starts in 2002 or later | +0.81, 15y beat 0.82, p 0.173: **fails** | +0.80, full +1.55, p 0.051: passes | |
| Gain budget sized exactly on the FIFO lots (see below) | score +0.95, full **+0.31**, p **0.40** | +0.92, +1.76, p 0.015 | |
| QQQ removed from the menu | +0.30 (p 0.36) | +0.50 (p 0.080) | +0.04 (screen) |
| QQQ and XLK removed | **-0.26** | **+0.12** | -0.30 (screen) |
| 30 random menus: mean score; menus passing 1-3 | +0.42; 1 of 30 | +0.34; 1 of 30 | -0.13 (screen) |
| Pre-2000 holdout, pre-ETF copy of the menu (10-year windows vs VFINX) | +0.1 | 0.0 | +0.52 in the engine; -0.37 to -1.14 for 1986-2000 once fund distributions are taxed yearly |
| Sub-periods, fresh starts: 2000-10 / 2010-20 / 2020-26 | +2.93 / +0.89 / **-0.40** | +3.57 / +0.74 / **-0.64** | +1.20 / -0.55 / +0.19 |
| 5-year windows starting in 2020 / 2021 | -3.2 / -4.8 | -3.4 / -3.2 | -2.9 / -2.8 |
| Deflated Sharpe (about 12,000 trials) | **0.038** | **0.051** | 0.009 |
| Paired with INC, monthly, from 2000 | +0.28 pp/yr, p 0.38; behind INC in 78% of 20-year windows and over 2010-2026 (-0.59) | +0.25 pp/yr, p 0.39 | |

**Where the excess comes from** (full protocol, CA, score):

| Component | Incumbent menu | Menu without QQQ and XLK |
|---|---|---|
| Hold the menu in equal weights, never trade | +0.05 | -0.40 |
| + K-execution with random picks (the structure alone) | +0.08 / +0.13 | -0.35 |
| + momentum ranking (KX3 / KX1) | **+0.99 / +0.93** | -0.26 / +0.12 |

* **The structure alone is worth about nothing against simply holding the menu.** It is necessary,
  though: without it no rotation survives California tax.
* **Selection adds +0.8 to +0.9, mostly by picking growth/tech.** On random menus, KX3's score
  rises with the number of tech funds the menu happens to contain: no tech fund -0.91, one +0.19,
  two +0.44, three +1.21.
* **Attribution before tax, pp/yr.** For KX3 from 2000:
  * 2000-2008: +4.56 of active return, of which +2.80 came from small/mid caps (mostly MDY);
  * 2009-2026: +0.87, with growth/tech contributing +2.05 and every other holding together -1.2 to
    -1.3.
* **The book freezes.** By 2026 KX3 is 54% growth/tech with 87% of its value in unrealized gains;
  KX1 is 57% and 81%. A 1% budget cannot de-risk that.
* **Untested crash risk.** Replaying the 2000-02 tech bust on the 2026 books loses -56% (2000-start
  book) and -71% (2015-start book), against SPY's -47.5%.

**The start-date artifact.** KX3 needs 379 trading days of history and KX1 needs 274. On
2000-01-03 only SPY, MDY and DIA have it: sector SPDRs launched in December 1998, QQQ in March
1999, IWM, IJR, IWD and IWF in May 2000, EFA in 2001, and EEM and RSP in 2003. Both rules therefore start one-third
each in MDY, DIA and SPY. Because they never trim, KX3 holds MDY at 39-45% until 2008. That first
start also supplies the headline "full" excess and the bootstrap p-value. KX3's full-period excess
depends on its start date:

| Start | 2000-01 | 2001-07 | 2002-01 | 2003-01 | 2005-01 | 2009-01 |
|---|---|---|---|---|---|---|
| KX3 | +1.84 | +1.06 | +0.83 | **-0.75** | +0.90 | +1.23 |
| KX1 | +1.82 | +1.57 | +1.55 | +0.05 | +1.24 | +0.11 |

**The budget-sizing quirk in the website's `TaxManagedCombo`.** The site's description says the
last gain sale is part-filled so the year "lands exactly on the budget". In fact the code sells
`qty x room / gain`, sizing the sale on the position's *average* gain per share (in
`backtester/composite.py`, the sell loop of `TaxManagedCombo`). The engine then sells FIFO, oldest
and lowest-basis lots first, so the realized gain overshoots. The lab's KX rules have the same
behaviour.
* KX3 exceeded its 1% budget in **18 of 25 years**, by up to **1.32x** (2017); on average the
  budget was about 1.06%. KX1 exceeded its budget in 16 of 26 years.
* Sizing the sale on the actual FIFO lots barely moves the score (KX3 +0.99 -> +0.95). It does
  change the single 2000-start path a lot:
  * one partial XLF sale in July 2004 sends the path to a book with less QQQ;
  * full excess falls from +1.84 to **+0.31** and boot p rises from 0.011 to **0.40**;
  * terminal after-tax wealth falls from $968k to $664k on $100k.
* Averaged over rebalance offsets the fix is neutral: score +0.93 vs +0.94, full +0.83 vs +1.15,
  both within noise.

**Lesson:** for these frozen-book rules, any single-path statistic carries about ±1 pp/yr of path
luck. Raising costs from 5 to 15 bps per side adds only about 0.01 pp/yr of direct cost, yet it
moves KX3's full excess from +1.84 to +0.46. Only the 95-window averages are stable.

**Changes to the website suggested by this work** (facts measured, not recommendations):
* Buying proportionally instead of alphabetically beat the site's order in 84% of 144
  identical-knob pairs, by +0.11 of score. The preset with proportional buys scores +0.72 / full
  +1.29 / 10y beat 0.84 / p 0.044.
* A 0% gain budget gives +0.64, 10/15y beat 0.79/0.81, p 0.047.
* Exact FIFO budget sizing removes path luck without changing the average.
* KX1 and KX3 need knobs the site does not have yet: a hold buffer, no-trim, and rank-ordered gain
  spending.

**Verdict.**
* **Signal:** real but modest, and largest when the menu contains the era's winners.
* **Structure:** necessary for any rotation in a taxable account, and worth about zero on its own.
* **Lead over SPY:** regime luck. It came from mid-caps forced on it at the 2000 peak, then US
  mega-cap growth after 2009.
* **KX1** is the more robust of the two, but neither has good confidence.

Treat it as a tax-efficient momentum tilt with a growth bet built in and an expected edge near
zero. It brings 50-60% growth/tech concentration that cannot be unwound without a large tax bill,
and five-year stretches of 2-3 pp/yr underperformance. Round 2 (`r2_rotation_final`) re-tests it
on menus rebuilt each year by a fixed rule.

### 4.2 Moderate leverage plus a trend filter: 2x S&P 500, daily SMA175 with a 3% band

**The rule.** Each day at the close:
* hold a 2x daily-reset S&P 500 fund (SSO in practice; the tests use a cost-calibrated synthetic
  2x series, which matches SSO where the two overlap);
* switch to intermediate Treasuries (VFITX / IEF) when the S&P 500 closes more than 3% below its
  175-day average;
* switch back when it closes more than 3% above it.

This is the lower-leverage version of the round-1 3x leader. Verification (`verify_lev_robust.md`)
named it the highest leverage whose risk is acceptable.

**Numbers in every history** (CA, after tax, versus S&P 500 buy-and-hold):

| History | Score, pp/yr | Boot p | Max drawdown (index) |
|---|---|---|---|
| 2000-2026, engine (full excess +3.80; beat SPY in 100% of 10/15/20-year windows) | **+4.94** | 0.077 | **-47%** (-55%) |
| 1986-2026, VFINX repaired | **+4.62** | 0.067 | -47% (-55%) |
| 1986-2026, executed one day late | +3.85 | 0.264 | -59% (-55%) |
| 1930-1985 holdout (never seen in round 1; research simulator) | **+2.95** | 0.27 | -67% (-81%) |
| 1930-2026 | +3.48 | 0.13 | -67% (-81%) |
| FED / NONE, 2000-2026 | +6.00 / +7.74 | 0.041 / 0.011 | |

**Crashes, peak to trough, before tax** (1986-2026, repaired data):

| Episode | S&P 500 (VFINX) | 2x SMA175/3% | 3x SMA175/3% |
|---|---|---|---|
| 1987 crash | -34% | -24% | -38% (exited at the 10-16 close); **-76%** one day late |
| 1990 | -19% | -21% | -31% |
| 1998 | -19% | -24% | -35% |
| 2000-02 | -47% | **-16%** | -35% |
| 2007-09 | -55% | **-7%** | -16% |
| 2011 | -19% | -21% | -32% |
| 2015-16 | -13% | -12% | -19% |
| 2018 Q4 | -19% | -17% | -25% |
| 2020 | -34% | -23% | -33% |
| 2022 | -25% | **-37%** | -49% |
| 2025 | -19% | -18% | -26% |

The pattern is clear: it sits out slow bear markets but loses about as much as the index, or more,
in fast corrections. It exits after the index is down about 10% and then misses part of the
rebound.

**Risk simulations** (`verify_lev_robust.md` sections 6-7):

| Simulation | 2x | 3x | 1.5x |
|---|---|---|---|
| Chance of a drawdown over 80% within 20 years (block bootstrap of 1930-2026) | **0.7%** | **17%** | 0.0% |
| Chance of a drawdown over 70% within 20 years, same | 5.4% | 41% | 0.4% |
| Chance of trailing SPY after tax at 20 years: 1986-2026 data / 1930-2026 data | 16% / 32% | 5% / 21% | — / 51% |
| Resampled market paths with about 3 months of trend persistence: chance of trailing at 20 years | 64% | 52% | |
| Same, about 1 month of persistence: chance of a drawdown over 80% | 9% | 51% | |
| One -20% day while invested (1987 pattern), 10-year excess (share of windows ahead) | +0.8 (60%) | +0.8 (54%) | +0.2 (51%) |

For reference, SPY's own chance of a drawdown over 60% within 20 years is 20% on 1930-2026 data
and 5.7% on 1986-2026 data.

**Is it skill or leverage?**
* **At equal volatility, the trend filter is a much better way to hold leverage than constant
  leverage.** At about 24% volatility, 2x-with-trend scores +4.9 / +4.6 / +3.5 (2000-26 / 1986-26 /
  1930-2026) against +1.0 / +0.8 / +0.9 for constant 1.25x.
* **But most of the excess is the leverage itself.** At SPY-like volatility (1.5x with the trend
  filter) the gain is only +1.5 to +2.6 pp/yr, and it is not significant anywhere (p 0.22-0.46).
* **Selection.** Walk-forward picking of the best trailing parameter set inside the 2x daily grid
  is positive out of sample: +1.4 (2000-26, 58% of decisions win), +4.1 (1986-26, 85%), +3.2
  (1930-2026, 82%).
* **Parameter choice is close to a coin flip.** PBO inside the 2x grid is 0.47-0.60. Of 486
  neighbourhood configs, only 13 pass items 1-3 on both 2000-26 and 1986-26: two are 2x daily
  (SMA175/3%, SMA200/4%) and the rest are 3x. No 2x config passes on 1930-85. The deflated Sharpe
  is **0.0035**.
* **Mechanics are sound** (`verify_lev_mech.md`):
  * the synthetic 2x matches real SSO on the same windows (+6.24 vs +6.34 for the SSO EMA rule);
  * wash sales cost 0.03-0.10 pp/yr;
  * yearly distribution tax costs 0.2-0.65 pp/yr;
  * rate-dependent financing costs the 3x rule at most 0.23 of score;
  * 35 bps per side still leaves the 3x rule at +8.60;
  * pre-2010 noise in SPY's closes *hurts* these rules (3x on index data: +10.10).

**Conditions for using it** (all from verification):
1. **Trade at the same day's close** with a market-on-close order. With a one-day lag the
   1986-2026 result falls to +3.85 (p 0.26) and the drawdown to -59%.
2. **Hold a 2x daily-reset fund and pay its distribution tax.** SSO paid out 4-5% in 2006-07; a
   fund-level short-term distribution could cost about 2 pp in such a year.
3. **Accept that the edge needs trends lasting months.** In resampled markets with only 1-3 months
   of persistence, it trails SPY over 20 years 64-73% of the time.
4. **Accept losing more than the index in fast drops** (2022: -37% vs -25%), and that much of the
   excess is paid-for risk.
5. **Know what has and has not been tested.** The rule has run only in the lab's research
   strategy kinds. These reports do not establish whether the website can express it as-is. Round
   2 (`r2_lev2x`, `r2_gap1`, `r2_gap6`) re-tests a pre-registered 2x grid, a Section 1256 futures
   version and other markets.

**Why 3x was rejected, despite the largest numbers in the search** (3x: CA +9.65, every 10-year
window beat SPY, p 0.029):

| | 3x SMA175/3% | 2x SMA175/3% |
|---|---|---|
| Worst drawdown before 1986 | **-88%** in the 1930-1985 windows; -93% peak to trough from 1929-09 to 1935-05 (it re-entered bear-market rallies at 3x) | -67% in the 1930-1985 windows (index -81%) |
| Chance of a drawdown over 80% within 20 years (1930-2026 bootstrap) | **17%** (24% for the pre-registered SMA200/2%) | 0.7% |
| 1987 | Avoided Black Monday only by selling at the 1987-10-16 close. With a one-day lag: -76% in the crash and a -78% drawdown, p 0.13-0.21. 37% of daily neighbours, and 98-100% of weekly and monthly ones, held 3x into the -61% day. | -24% |
| One -20% day while invested (about 7% odds over 20 years) | Removes about 60% of the account at that close; cuts the 10-year excess by about 7-8 pp/yr | Cuts the 10-year excess by about 3-4 pp/yr |
| Fast corrections | Loses more than the index in 1990, 1998, 2011, 2015-16, 2018, 2022 (-49% vs -25%) and 2025 | Roughly index-like, except 2022 (-37% vs -25%) |
| How it was chosen | After the fact. The pre-registered SMA200/2% has p 0.100-0.117. DSR 0.013. PBO inside the 3x daily grid 0.47-0.71. | Named by verification as the acceptable-risk level |
| 1930-1985 holdout | +6.81, p 0.19, worst 10-year window -14.6 pp/yr | +2.95, p 0.27 |

**Verdict.** An after-tax excess shows up in every history, and the trend filter beats holding
constant leverage at the same risk. It is still mostly a leverage premium bought with fatter tails.
Confidence is moderate at best (p 0.07-0.27, DSR 0.0035), and it was found by searching about
14,000 configurations. **2x is conditional, not a pass. 3x is rejected.**

---

## 5. Key lessons

1. **Taxes dominate.**
   * SPY's own tax drag is about 1.15 pp/yr (2000-2026), paid once, at the end, at the long-term
     rate.
   * Active rules lose much more. The 3x trend rule's tax drag is 4.76 pp/yr (7.89 for the real-UPRO
     version). TAA pays about 0.75 + 0.23 x turnover pp/yr. The median calendar rule loses 3.47
     pp/yr in CA.
   * Many rules have real pre-tax edges that vanish in CA:
     * sector seasonality: +0.98 untaxed, -2.17 in CA;
     * credit-spread rules: work untaxed, median -1.01 in CA;
     * a ConnorsRSI 3x dip overlay: +5.07 untaxed, -1.13 in CA;
     * 47 TAA configs, none still positive after tax.
   * In practice, a taxable strategy must realize almost nothing.
2. **Buying and holding SPY is already the most tax-efficient strategy in this engine.**
   * The engine pools losses, has no $3k ordinary-income offset and taxes everything at the final
     sale. So any strategy's total tax is at least the long-term rate times its total gain, and SPY
     held forever pays exactly that minimum.
   * No harvesting or tax-aware structure improved on it by more than 0.004 pp/yr.
   * Tax-loss harvesting has value only outside the engine:
     * about +0.2 to +0.4 pp/yr if the losses offset other long-term gains;
     * +0.20 to +0.35 pp/yr from the $3k offset on a $100k account, about 0 on $1M.
3. **Tax-managed execution lifts any picker, but it does not beat SPY by itself.**
   * Under the same tax-managed execution, random sector picks score +1.11 against momentum's +1.28.
   * The site's rule lifts a random-pick rotation from -2.96 to -0.22 pp/yr.
   * Losses-only rebalancing beat tax-blind rebalancing on 30 of 30 random menus (+0.45).
   * The same stocks under tax-managed execution beat standard execution by +0.65 pp/yr (p 0.004).
   * Against simply holding the menu, the structure adds about zero. Any lead over SPY has to come
     from selection, and here that meant growth/tech.
4. **Most "edges" are one or two events.**
   * Trend timing, TAA and the macro rules all live on the 2000-02 and 2008 bear markets. No
     screened timing rule beat SPY in any 10-year window starting 2009 or later.
   * The best global rule traded twice; the style switch traded 13 times in 26 years.
   * Every finalist lost 3-5 pp/yr in five-year windows starting 2020-2023.
5. **The large excess comes from leverage, and that is risk, not free alpha.**
   * The excess scales with leverage. At SPY-like volatility it shrinks to +1.5 to +2.6 pp/yr
     (p 0.22-0.46).
   * Leveraged Sharpe ratios are about SPY's (3x trend 0.58 vs 0.51; SSO cross 0.65 vs 0.65). On
     1986-2026 every leveraged finalist's Sharpe (0.55-0.61) was *below* VFINX's (0.67).
   * Levered vol targeting had beta 1.57 and alpha about 0.
   * Real leveraged ETFs only cover a bull market. Buying UPRO in 2009 and holding it "passes"
     (+17.12, p 0.004), and so does 10% UPRO + 90% SPY never traded (+2.38, p 0.015). Leveraged
     rules therefore had to be judged on synthetic 2000+, 1986+ and 1930+ histories and against
     constant leverage.
   * The 3x tails (-88% to -93%) are close to ruin.
6. **What "good confidence" means after 13,778 trials.**
   * Try 14,000 strategies and the best-looking one will impress even if none works. The deflated
     Sharpe corrects for this. With about 12,000 trials, a strategy needed an after-tax excess
     Sharpe of about **0.76 a year** to be significant. The best unlevered candidates had 0.32-0.47.
     The finalists' CA DSRs ranged from 0.003 to 0.06 against a pass mark of 0.95, and the final
     count of 13,778 makes them slightly lower still.
   * The 95 overlapping start dates hold only 2-3 independent decades, and most 10- and 15-year
     windows contain 2000-02 or 2008.
   * The bootstrap uses a single path, which can be an artifact, as with KX3's 2000 start.
   * Monthly rules carry check-day luck: the GATED macro rule scores anywhere from +0.88 to +3.12
     depending on which of 28 days it checks (median +1.63).
   * Good confidence would need one of two things:
     * an excess far larger and steadier than anything found;
     * a pre-registered rule confirmed on data not used to find it.
   * Only the 2x trend rule has partial out-of-sample support (positive in 1930-1985), and even
     there it is not significant (p 0.27). **Expect any backtested edge from this search to shrink
     out of sample.**
7. **Hindsight hides in menus.**
   * QQQ and XLK carry the rotation's lead.
   * Late-launching growth ETFs (VUG, MGK, SPMO...) pass only because of their launch windows: IWF
     scored on the same windows passes too.
   * Removing EEM drops VAA-G4's untaxed score from +1.78 to -0.11.

   Every menu-based result was re-run on random menus from a fixed 2003 pool, and those results are
   the ones to believe.

---

## 6. Caveats and engine limitations

| Limitation | What it means | Effect on this search |
|---|---|---|
| **Survivorship** | The stock panel has only 37% of the S&P 500's 2000 members (93% by 2025). The random-menu ETF pool and the Fidelity Select proxies hold only funds alive today, and the pool includes 7 tech winners. | Stock results cannot be measured (random stocks "beat" SPY by +3.24). Random-menu and pre-2000 sector results are upper bounds. |
| **Synthetic leverage history** | Before SSO (2006-06) and UPRO (2009-06), leveraged funds are synthetic, with a fixed 0.6%/yr spread on the borrowed amount. Real spreads rise with rates (UPRO is about 0.44% + 0.13 x T-bill). 1930-1985 uses approximate dividends and, before 1960, approximate T-bill yields. | The synthetic is about 0.55 pp/yr too cheap when T-bills are above 2%, and too expensive near zero. A conservative rebuild cost the 3x rule 0.23 of score. The synthetic matches real UPRO/SSO on the same windows. |
| **Distribution taxes** | Prices are total return, so dividends and bond interest are deferred and taxed as capital gains at the sale, for both the strategy and SPY. Leveraged ETFs actually pay ordinary income, and Fidelity Selects paid 4-5% a year, often short-term. | Yearly-tax replays moved the finalists by -0.65 to +0.06 pp/yr; Fidelity-menu results by -0.2 to -1.2. The replays ran on only 4 start dates and treat non-bond payouts as qualified. |
| **FIFO lots only** | No specific-lot (HIFO) sales. Budget-limited partial sales overshoot under FIFO (section 4.1). | Real brokers allow specific lots, which could help tax-managed rotation. Round 2 (`r2_gap5`) tests this. |
| **Loss netting** | The engine nets all losses, including long-term losses and carryforwards, against short-term gains first. | This is more generous than IRS netting for switching strategies. |
| **Wash sales** | The engine ignores them. The lab's 31-day guard blocks buying back after a loss sale, but not a purchase in the 30 days *before* the loss. | 0.03-0.10 pp/yr for the leverage rules. Impossible at the rotations' quarterly or semiannual cadence. TVT broke the rule on 25% of its loss dollars. |
| **Same-close execution** | Signals read the close they trade at. | Daily rules need market-on-close orders. A one-day lag is harmless on 2000-2026 but decides 1987 for the leveraged rules. |
| **No $3k offset, no other income** | Harvested losses offset only the account's own gains. | Harvesting is understated by about +0.2 pp/yr on a $100k account. |
| **Everything sold at window end** | No step-up at death, no gifts of appreciated shares, no slow retirement sales. | Mildly favours strategies that realize gains along the way (the EMA cross's full excess goes from +1.36 to +0.76 without the terminal sale). Frozen books barely move. Round 2 (`r2_gap4`) tests this. |
| **No cash flows** | No contributions or withdrawals. | A saver could rebalance a frozen book with new money. Not tested. |
| **Negative cash** | The January tax is taken from cash even when the account is fully invested, which acts as an interest-free loan. | Worth +0.5 to +1 pp/yr to some VIX timers. Never happens for KX3; worth under 0.01 pp/yr for KX1. |
| **Cash and Treasuries** | Cash earns 0%. Treasury interest is deferred and taxed at the long-term rate, whereas in reality it is taxed at ordinary federal rates plus NIIT (38.8%) and is CA-exempt. CA munis were not tested. | Slightly flatters Treasury off-legs, which supply 0.6-1.1 pp/yr of the timing results. |
| **FED regime** | 35/15 leaves out the 3.8% NIIT; the CA regime includes it. | Slightly flatters every gain-realizing strategy in FED. |
| **Fund frictions** | Mutual-fund loads, redemption fees and frequent-trading limits are not modelled. | Affects the Fidelity Select history and VFITX round trips (use IEF). |

**Data problems found and fixed.**

| Problem | Effect | Fix |
|---|---|---|
| **VFINX distributions.** Six 1980-86 capital-gain distribution days are unadjusted; on 1986-12-09 VFINX shows -7.0% vs the S&P's -0.75%. | Tripled in synthetic 3x VFINX (-20.9% that day). It penalized the leveraged rules and distorted the 1986+ benchmark: the 3x rule's 1986-2026 full excess was +6.06 before the fix and +6.88 after. | Repaired series `data/VFINXR.csv` (the S&P's return on those days) and protocols `long_r` / `long_r_screen` (`families/lab_extras.py`). Verification and round 2 use them. The original file is unchanged. |
| **Noisy SPY closes before about 2010** (6.4%/yr tracking error vs the index in 2000-02, reverting the next day) | Same-close trend rules sell into transient dips. | Re-tested on the S&P 500 total-return index. The round-1 numbers are kept as the conservative ones. |
| **Discount-yield curve.** The lab's ^TNX - ^IRX reads about 10 bp too high. | It split the 2019 inversion and missed 1989. | A bond-equivalent curve was used in verification (curve leader +3.87 -> +2.67). |
| **Small fund-data issues.** VFITX shows -3.2% on 1993-12-31; FGOVX/VUSTX have stale-NAV jumps in the 1980s; mutual-fund prices before mid-1985 are stale month-end values. | Small. | Noted. The long protocols start in 1986. |
| **Lab bugs** (critic triage). Cache poisoning by mid-sweep edits; walk-forward stepping over start indices rather than time (only 3-4 decisions on yearly screens); a degenerate offset test for monthly-check signals; benchmark drawdown always taken from the 2000 start (SPY's drawdown since 2009 is -34%, not -55%). | Mixed. The offset test was optimistic for monthly-check rules, and the benchmark-drawdown issue flattered 2009+ leveraged strategies. | Cache hashing fixed in `lab_extras.py`. Verification re-ran walk-forward with yearly decisions and used custom offset and lag kinds, which is how GATED's check-day luck was found. |

---

## 7. Appendix: where every result file lives

All paths are relative to the repository root.

| What | Where |
|---|---|
| This report | `research/STRATEGY_SEARCH.md` |
| Methods (keep with this report) | `research/lab/REPORT_METHODS.md` |
| Protocol and the 7-item bar | `research/lab/PROTOCOL.md` |
| Instruments, proxies and synthetic series | `research/lab/INSTRUMENTS.md` |
| Family reports (11) | `research/lab/results/{trend_timing,risk_alloc,seasonal,mean_reversion,macro_regime,factor_style,global,stocks,tax_rotation,tax_structures,leverage}.md` |
| Family reports for `taa_models` and `sector_deep` (never written as .md) | the `results_md` field of `research/lab/scratch/_lead/r1/{taa_models,sector_deep}.json` |
| Every run, one row per config x regime x protocol, with the exact config JSON (13 tables) | `research/lab/results/<family>_table.csv` |
| Structured round-1 output per family: headline, findings, candidates, diagnostics, hindsight checks, untested ideas, lab bugs | `research/lab/scratch/_lead/r1/<family>.json` |
| The 13 finalists sent to verification | `research/lab/scratch/_lead/r1/verify_candidates.json` |
| Critic review: coverage gaps, suspicious results, combinations, lab bug triage | `research/lab/scratch/_lead/r1/critic.json` |
| Re-verification of the website preset | `research/lab/scratch/_lead/verify_incumbent.json` |
| Verification reports (7) | `research/lab/results/verify_{taxrot_mech,taxrot_robust,lev_mech,lev_robust,levvt,curve,tilts}.md` |
| Strategy code: families, verification kinds, round 2 | `research/lab/families/*.py` |
| Per-family and per-verifier scripts, logs and grids | `research/lab/scratch/<family or verifier>/` |
| Lab core: engine wrapper, protocols, sweep, metrics, battery, distribution-tax replay | `research/lab/{core,blocks,registry,data,sweep,metrics,report,verify,realism}.py` |
| Parity check against the website | `research/lab/validate_lab.py` |
| Repaired VFINX and the `long_r` protocols | `research/lab/data/VFINXR.csv`, `research/lab/families/lab_extras.py` |
| Result cache (every run, keyed by config and code hash) | `research/lab/cache/` |
| Round 2 (running) | code `research/lab/families/r2_*.py`, work `research/lab/scratch/r2_*/`; reports will appear as `research/lab/results/r2_*.md` |
| Earlier write-up of the tax-managed preset (predates this search; its headline used a single window, so section 4.1 supersedes it) | `research/README.md`, `research/tax_managed_report.py`, `research/tax_managed_report.json` |

---

## Addendum: round 2 completeness items (stopped at the user's request, 2026-10-05)

The user stopped the search once the answer was clear. Items that had finished or written a verdict
by then:

- **Unlevered rotation, final pass** (`results/r2_rotation_final.md`). No unlevered rule tested can
  honestly be recommended over SPY for a taxable California investor. SPY bought and held is the
  unlevered answer.
- **Option overlays** (`results/r2_gap3.md`). Puts, put-spread collars and VIX calls, 104 configs,
  using CBOE strategy-index prices 1986-2026 plus a calibrated option model. None beats SPY after CA
  tax. Hedged structures lose 0.4 to 3.6 pp/yr; insurance costs more than it pays.
- **Specific-lot (HIFO) sales and IRS netting** (`results/r2_gap5.md`). They change no verdict:
  finalist scores move by -0.04 to +0.02 pp.
- **How the position ends** (`results/r2_gap4.md`). Under a step-up at death or a donation, the 2x
  trend rule loses its CA support (p about 0.20); buy-and-hold gains about 0.8-0.9 pp/yr against
  every strategy that realizes gains.
- **Cross-family combinations** (`results/r2_combos.md`). None beats its best component on
  robustness. The 75% never-sold SPY + 25% trend-sleeve form is the safest way to hold the bet.
- **Leverage + trend on 33 other stock markets** (reviewed by the final judges). Median +0.24 pp,
  pooled -0.53 pp (p 0.60): the S&P result does not generalize.

Not finished when stopped:
- the Section 1256 futures version of the trend rule (early results were preliminary and could not
  run on the website anyway);
- valuation (CAPE) allocation.

Neither is likely to change the bottom line, though neither was tested to completion.
- The futures version is still leverage. Its 60/40 tax treatment and cheaper financing might narrow
  the gap, but it cannot run on the website.
- Valuation tilts are slow changes to equity weight, the same kind of move every timing family
  failed with after CA tax.
