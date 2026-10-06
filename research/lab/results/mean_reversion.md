# Family `mean_reversion` — mean reversion, dip-buying and volatility signals

Module: `research/lab/families/mean_reversion.py` (signals `mean_reversion.timer`, `.basket`,
`.xs`, `.volscale`; kind `mean_reversion.ladder`; unchanged in session 2, so every session-1
result stayed valid). Scripts, logs and grids: `research/lab/scratch/mean_reversion/`
(`grid.py`, `extra_grid.py`, `finalists.py`, `controls.py` from session 1; `grid2.py`, `grid3.py`,
`grid4.py`, `finalists2.py`, `long2.py`, `analyze2.py`, `diag2.py` from session 2). Full table of
every run: `research/lab/results/mean_reversion_table.csv` (one row per config x regime x
protocol; `protocol` and `source` columns).

Where numbers come from (always labelled):
* **engine**: `backtester.Backtest` through the lab = the website's numbers (0.0 difference).
* **SYNTHETIC**: the same engine on a synthetic daily-reset 2x/3x S&P series
  (`r = L*r_index - (L-1)*(T-bill + 0.6%)/252 - 0.9%/252`, calibrated to SSO/UPRO within
  ~0.2 pp/yr), because real SSO/UPRO only exist since 2006/2009 and every real-ETF window of a
  leveraged rule is a 2006/2009-2026 bull market. Index = SPY for 2000+ protocols, VFINX (S&P
  500 fund, the long protocols' benchmark) for 1986+ protocols. Synthetic runs are stress tests,
  never candidates on their own.
* **FAST-SIM**: a NONE-regime replica of the engine for whole-book SPY <-> leveraged overlays
  (`fastsim.py`). Verified: 0.0 difference vs engine records at every checkpoint (12 sampled
  real-ETF configs, identical trades) and <= 6e-6 relative difference vs engine SYNTHETIC runs
  (2 configs x 38 starts x 88 checkpoints). Used for the 624-config overlay neighbourhoods and
  permutation tests.

## Verdict

**No mean-reversion, dip-buying or volatility rule beats buying and holding SPY after
California tax with good confidence. Nothing passes the protocol bar in FED either.**

1. **Every unlevered rule loses or ties after tax** — and the long history (1986-2026 on real
   mutual-fund proxies) agrees. Short-term dip timers (Connors RSI(2), ConnorsRSI, down
   streaks, N-day lows, % below moving averages, Bollinger %b, VIX spikes) are out of the market
   most of the time and realize every gain short-term: 0 of 260 standalone timers have a positive
   CA score (best -4.3 pp/yr); 0 of 31 "tax-aware" timers that may not sell a winner before 366
   days. Keeping a T-bill reserve to buy 10-30% drawdowns or VIX spikes and hold them is at best
   a wash (best CA full-protocol score -0.15 pp/yr; 1986+ twin -1.5 pp/yr). VIX risk-off rules,
   volatility targeting, sector/22-ETF dip baskets, pairs and cross-sectional reversal all lose;
   the website's own RSI / Bollinger / volatility-reversion timers lose 3-11 pp/yr (tax-managed
   Bollinger: +1.4 pp/yr on 2000+ but 10-year beat 0.63, boot_p 0.18, and +0.3 pp/yr with a
   negative pre-2000 holdout on 1986+).
2. **Every leveraged rule that looks good on real ETFs is first of all leverage in a bull
   market.** Real UPRO/SSO windows start in mid-2009/2006, and plain buy-and-hold leverage clears
   the mechanical part of the bar (criteria 1-3) over exactly those windows: 90% SPY + 10% UPRO
   bought once: CA score +2.4 pp/yr, boot_p 0.015. With SYNTHETIC leverage back to 2000 and 1986
   almost all of them fail (drawdown ladders, VIX "lever up on fear", tax-managed overlays,
   leveraged-trend controls: 0 of 26 tax-aware overlay variants pass in CA on 1986+ data).
3. **The closest call is a reserve-funded, trend-filtered, tax-aware leveraged dip sleeve**
   ("RH": 80% SPY never traded + 20% T-bill reserve; when SPY is oversold — Bollinger %b(20,2) < 0
   or RSI(2) < 10 — while above its 200-day average, the whole reserve buys UPRO; the tranche is
   held >= 366 days (long-term gains), then sold back to T-bills on the next RSI(2) > 65 day).
   Its %b version clears criteria 1-3 in CA on real ETFs (full protocol from 2009-07: score
   +3.44 pp/yr, full +4.73, 10/15-year beat 1.00/1.00, boot_p 0.009), on SYNTHETIC 2000+ (+2.79,
   boot_p 0.016) and on SYNTHETIC 1986+ (long protocol: +1.75, boot_p 0.029, pre-2000 10-year
   windows +0.90 pp/yr). It is robust to costs (+2.67 at 35 bps/side) and to stricter
   distribution taxes (-0.05 pp). It still **fails the bar**:
   * criterion 4: the family's walk-forward selection is negative out of sample in CA
     (-4.1 pp/yr lab default; -6.9 pp/yr with yearly decisions), and on the leveraged
     SYNTHETIC records PBO is 0.54 (2000+);
   * the deflated Sharpe of its after-tax excess, given ~2,000 configurations tried, is 0.06
     (RSI(2) version: 0.006);
   * it is leverage: average exposure 1.6x on real data and rising, because the UPRO sleeve is
     never rebalanced (1.5x in 2009, 2.7x in 2026; RSI(2) version 1.7x); max drawdown -54% (real,
     from 2009-07) and -63% to -77% (SYNTHETIC 1986+) vs -55% for SPY;
   * on the same 1986+ path its after-tax return is **not distinguishable from risk-matched
     leverage**: vs constant 1.5x/2x or buy-and-hold 30-50% UPRO the monthly difference is
     +0.6 to +2.7 pp/yr with bootstrap p 0.10-0.41, and vs a plain "UPRO when SPY is above its
     200-day average, else SPY" rule it is -1.1 to +3.0 pp/yr (p 0.20-0.67);
   * its parameter neighbourhood is positive everywhere but passes only about half the time
     (2 of 9 %b neighbours pass on 1986+; the RSI(2) version misses boot_p on real data, 0.11).
4. **Tax-deferred account (NONE, diagnostic only): one genuine timing edge, fragile.** Switch the
   whole S&P 500 position into 3x (UPRO) when ConnorsRSI(3,2,100) < 15 while SPY is above its
   200-day average, back to SPY after 5-7 days. Engine, full protocol (2009-07+): score +5.07
   pp/yr, full +8.56, 10/15-year beat 1.00/1.00, boot_p 0.005. It beats random entries with the
   same filter, exit and exposure by about +5 pp/yr (permutation p 0.05 on real UPRO, 0.00 on
   SYNTHETIC 2000+ and 1986+), holds on SYNTHETIC 1986+ data (+7.6 pp/yr; 10-year windows ending
   before 2000: +7.6, beaten 100%), and works on 73% of 84 other equity ETFs. But it needs 3x
   leverage and low costs (gone at 30 bps per side), the family walk-forward is negative
   (selection by trailing performance keeps picking unfiltered variants that crash), and in CA
   it loses (-1.13 pp/yr; +0.9 pp/yr with boot_p 0.59 on SYNTHETIC 1986+).

Bottom line for the user's taxable account: within this family, nothing is better than the
incumbent preset or plain SPY with good confidence. The only CA-positive structure is "add a
leveraged S&P sleeve, mostly in uptrends, and hold it for a year" — a leverage decision with
deeper drawdowns, not a mean-reversion edge, and not statistically better than taking the same
leverage without the dip timing.

## What was tested

Every config is a JSON dict runnable by `research.lab.sweep.run`; its label (`group|details`)
is part of it. Screen = protocol `screen` (24 yearly starts 2000-2023) in CA and NONE unless
stated. Leveraged-ETF configs carry `requires` (SSO 2006-06, UPRO 2009-06), so their windows
start at the fund's launch. Counts below are distinct engine configs per regime (the full list,
with every statistic, is in the CSV).

| group | idea | engine screen | other evidence |
|---|---|---|---|
| T | standalone dip timers SPY <-> short Treasuries: RSI(2) <5/10/15/25, RSI(3), ConnorsRSI <10/15/20, cumulative RSI(2), 2-4 down days, 5/7/10/20-day lows, % below 10/20/50-day SMA, Bollinger %b, 5-day return; +/- 200-day filter; 7 exits | 260 CA / 261 NONE (of 364 planned) | 15 long-history twins (1986+) |
| K | the same timers made tax-aware: a winner may not be sold before 366 days (losers exit at once), or tax execution with no short-term gains | 31 | 3 long twins |
| O | whole-book SPY <-> 2x/3x overlays (SSO, UPRO, 50% UPRO) on dips, +/- 200-day filter | 216 | 624 FAST-SIM overlays (real, SYNTHETIC 2000+ and 1986+) |
| N, NL | O-neighbourhood: 22 entries x 5 filters x 10 exits x 3 leverages; one-day execution lag | 11 (NONE) | FAST-SIM 342 + 54 |
| R | T-bill reserve -> SSO/UPRO on dips, sold on rebound (min hold 0) | 144 | |
| L | drawdown ladders: reserve (20-100%) or swap into SPY/SSO/UPRO at 5-45% drawdowns (from the high or 252-day high), hold >= 366 days, release never / at the high / near the high | 240 | 96 SYNTHETIC 2000+, 19 SYNTHETIC 1986+, 3 long twins |
| E | "recovery-confirmed" leveraged dip buying (still >= 10-30% below the high but back above the 50/100/200-day SMA) | 104 CA / 104 NONE (of 104 planned) | 4 SYNTHETIC |
| V | VIX regimes (lag 1 day): risk-off on high VIX; contrarian "lever up on fear"; VIX/VIX3M term structure (both directions); VIX spike vs 10-day mean; VIX percentile calm/stress; volatility risk premium (VIX - realized); VIX RSI(2); realized-vol spike | 93 | 13 SYNTHETIC (2000+, 1986+), 4 long twins |
| S | volatility-scaled exposure (21/63-day realized vol or VIX; target 10-20%; cap 1x or up to 2x via SSO) | 90 CA / 90 NONE (of 90 planned) | 3 long twins |
| B | the dip rule run on every sector SPDR / the incumbent's 22-ETF menu; base SPY or T-bills | 80 CA / 80 NONE (of 80 planned) | |
| X | cross-sectional reversal: short-term losers (1 week-3 months) and long-term losers (3-5 years; standard or tax execution) of sectors / 22 ETFs / 16 countries | 138 CA / 138 NONE (of 138 planned) | 3 corrected twins (see lab notes) |
| P | pair/ratio reversion (IWM, QQQ, RSP, EFA, MDY, EEM vs SPY; IWD vs IWF) | 21 | |
| CTRL, BHC | leverage controls: monthly-rebalanced 1.1-3x and buy-and-hold 5-100% SSO/UPRO mixes | 17 + 10 | 13 SYNTHETIC (2000+, 1986+) |
| VL | VIX ladders for taxable accounts: reserve -> SPY/SSO/UPRO when VIX > 30/40/50, hold >= 366 days | 36 | 2 SYNTHETIC, 3 long twins |
| VF | VIX "fear" neighbourhood (VIX > 30-45 -> SSO or 50% SSO until VIX < 12-17; min hold 366) | 23 | 3 SYNTHETIC |
| TX, TXN, TXC | tax-aware leveraged overlays: whole book -> UPRO on a dip in an uptrend; losers cut at once, winners held >= 366 days (or tax execution with no short-term gains); 23-config neighbourhood (10 entries, filters, exits, min hold 183-400, SSO/UPRO50, lag, no stop) and 3 leveraged-trend controls | 12 + 23 + 3 | all 26 TXN/TXC SYNTHETIC 2000+ and 1986+ |
| RH, RHN, RHN2, RHP | reserve-funded leveraged dip sleeve held >= 366 days (see verdict): entries, filters, reserve 10-50%, min hold 183-548, release rule, lag, SSO, no-timing controls; %b parameter neighbourhood | 8 + 15 + 7 + 9 | 37 SYNTHETIC 2000+ and 1986+, 3 on full and long |
| SITE, XFIX | the website's own RSI / Bollinger / volatility-reversion timers on SPY (plain and tax-managed) and on the incumbent preset; corrected long-horizon reversal twins | 15 + 3 | 1 long twin |

The planned grid was run in full except 104 standalone T timers with secondary exits (RSI(2) > 50/80, close >
5-day SMA, 7-day high, 10-day hold): that last batch was stopped when the shared machine slowed to
~0.05 runs/s. Every T entry signal is covered (both filters, 2+ exits each) and every T config
run is negative in both regimes.

Finalists on protocol `full` (95 quarterly starts, CA/FED/NONE): 32 strategies + 5 leverage /
no-timing controls (two over the protocol's 30-finalist guideline, because the RH family emerged
late in the session). Total engine configs screened: 1620 (CA: 1608) (a few rule-identical configs
appear under two labels); plus FAST-SIM for 683 overlay/timer configs (385 of them, the N/NL
neighbourhoods, only in FAST-SIM) and 301 SYNTHETIC-leverage stress configs (614 engine runs).

## Screen results by group (best and median score, pp/yr after tax vs SPY)

Engine, protocol `screen`, pp/yr. `pass 1-3` = score > 0, full > 0, 10y beat >= 0.75, 15y beat >= 0.85, boot_p <= 0.10 (on screen windows).

| group | regime | configs | score > 0 | pass 1-3 | median | best | best config |
|---|---|---|---|---|---|---|---|
| T | CA | 260 | 0 | 0 | -6.16 | -4.33 | `T|low10|x:hold10` |
| T | NONE | 261 | 0 | 0 | -6.78 | -3.32 | `T|low10|x:hold10` |
| K | CA | 31 | 0 | 0 | -2.99 | -1.26 | `K|low10&F200|x:c>sma5|minhold366` |
| K | NONE | 31 | 0 | 0 | -3.33 | -0.68 | `K|low10&F200|x:c>sma5|minhold366` |
| O | CA | 216 | 0 | 0 | -3.60 | -0.19 | `O|sma20<-4%&F200|x:rsi2>65|on:UPRO` |
| O | NONE | 216 | 110 | 31 | +0.06 | +4.75 | `O|low10&F200|x:hold5|on:UPRO` |
| N | CA | 10 | 0 | 0 | -2.13 | -0.70 | `N|crsi<5&F200|x:hold3|on:UPRO` |
| N | NONE | 11 | 10 | 3 | +1.15 | +2.58 | `N|crsi<10&F200|x:hold5|on:UPRO` |
| R | CA | 144 | 0 | 0 | -1.25 | -0.51 | `R|res10|low10&F200|x:rsi2>65|dip:SSO` |
| R | NONE | 144 | 0 | 0 | -1.26 | -0.39 | `R|res10|low10&F200|x:rsi2>65|dip:UPRO` |
| L | CA | 240 | 88 | 43 | -0.13 | +7.84 | `L|swap100|ddATH:30|dip:UPRO|rel:ath` |
| L | NONE | 240 | 94 | 47 | -0.10 | +10.48 | `L|swap100|ddATH:10/20/30|dip:UPRO|rel:ath` |
| E | CA | 104 | 85 | 15 | +0.78 | +6.09 | `E|swap100|dd>15&sma50up|dip:UPRO|rel:ath` |
| E | NONE | 104 | 86 | 23 | +1.16 | +7.92 | `E|swap100|dd>15&sma50up|dip:UPRO|rel:ath` |
| V | CA | 93 | 13 | 0 | -2.72 | +1.84 | `V|fear|vix>35->SSO|vix<15->spy` |
| V | NONE | 93 | 39 | 5 | -1.51 | +4.33 | `V|fear|vix>35->SSO|vix<15->spy` |
| S | CA | 90 | 0 | 0 | -3.08 | -0.22 | `S|rv21|tgt20|cap1.0|M` |
| S | NONE | 90 | 17 | 2 | -1.62 | +2.43 | `S|rv21|tgt20|cap2.0|M` |
| B | CA | 80 | 0 | 0 | -6.49 | -3.55 | `B|sect|base:SPY|rsi2<5&F200|x:c>sma5` |
| B | NONE | 80 | 0 | 0 | -7.09 | -1.64 | `B|sect|base:SPY|rsi2<5&F200|x:c>sma5` |
| X | CA | 138 | 7 | 0 | -4.14 | +0.44 | `X|sect|ret1260|bot3|S|tax` |
| X | NONE | 138 | 14 | 0 | -3.41 | +0.82 | `X|ctry|ret10|bot1|W` |
| P | CA | 21 | 1 | 0 | -3.03 | +1.36 | `P|QQQ/SPY|z20<-4%->QQQ|>0->half` |
| P | NONE | 21 | 4 | 0 | -1.24 | +1.82 | `P|QQQ/SPY|z20<-4%->QQQ|>0->half` |
| CTRL | CA | 17 | 13 | 7 | +1.68 | +13.53 | `CTRL|SPY+UPRO|3.0x|M` |
| CTRL | NONE | 17 | 13 | 7 | +2.35 | +14.94 | `CTRL|SPY+UPRO|3.0x|M` |
| BHC | CA | 9 | 9 | 5 | +3.48 | +8.52 | `BHC|SPY+UPRO|upro0.5` |
| BHC | NONE | 10 | 10 | 5 | +3.29 | +9.47 | `BHC|SPY+UPRO|upro0.5` |
| VL | CA | 36 | 14 | 9 | -0.24 | +4.85 | `VL|res30|vix>30|dip:UPRO|rel:never` |
| VL | NONE | 36 | 14 | 10 | -0.17 | +5.36 | `VL|res30|vix>30|dip:UPRO|rel:never` |
| VF | CA | 23 | 23 | 0 | +1.17 | +3.14 | `VF|vix>35->SSO|vix<15->spy|minhold366` |
| VF | NONE | 23 | 23 | 1 | +2.96 | +5.69 | `VF|vix>35->SSO|vix<12->spy` |
| TX | CA | 12 | 10 | 4 | +4.47 | +9.65 | `TX|pctb<0&F200|x:rsi2>65|on:UPRO|minhold366` |
| TX | NONE | 12 | 12 | 8 | +3.69 | +13.98 | `TX|pctb<0&F200|x:rsi2>65|on:UPRO|minhold366` |
| TXN | CA | 23 | 21 | 10 | +5.75 | +8.52 | `TXN|crsi<15&F250|x:hold5|on:UPRO|mh366` |
| TXN | NONE | 23 | 23 | 16 | +10.62 | +13.17 | `TXN|crsi<15&F250|x:hold5|on:UPRO|mh366` |
| TXC | CA | 3 | 3 | 1 | +7.76 | +8.57 | `TXC|trend200|UPRO-above|SPY-below` |
| TXC | NONE | 3 | 3 | 2 | +11.71 | +12.81 | `TXC|trend200|UPRO-above|SPY-below` |
| RH | CA | 8 | 8 | 4 | +0.97 | +2.14 | `RH|res20|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` |
| RH | NONE | 8 | 8 | 8 | +1.63 | +3.37 | `RH|res20|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` |
| RHN | CA | 15 | 15 | 7 | +2.55 | +4.34 | `RHN|res50|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` |
| RHN | NONE | 15 | 15 | 12 | +3.93 | +6.99 | `RHN|res50|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` |
| RHN2 | CA | 7 | 7 | 5 | +2.25 | +3.52 | `RHN2|res20|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold450` |
| RHN2 | NONE | 7 | 7 | 7 | +3.51 | +4.92 | `RHN2|res20|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold450` |
| RHP | CA | 9 | 9 | 4 | +2.86 | +5.45 | `RHP|res30|pctb<0&F200|x:rsi2>65|dip:UPRO|hold366` |
| RHP | NONE | 9 | 9 | 6 | +4.38 | +7.50 | `RHP|res30|pctb<0&F200|x:rsi2>65|dip:UPRO|hold366` |
| SITE | CA | 15 | 4 | 0 | -4.85 | +1.57 | `SITE|SPY|boll20-1.5|taxmanaged-M` |
| SITE | NONE | 15 | 0 | 0 | -6.17 | -2.19 | `SITE|SPY|boll20-2|taxmanaged-M` |
| XFIX | CA | 3 | 2 | 0 | +0.08 | +0.25 | `X|sect|ret1260|bot3|S|tax|req1830d` |
| XFIX | NONE | 3 | 2 | 0 | +0.21 | +0.21 | `X|sect|ret1260|bot3|S|tax|req1830d` |
| FIN | CA | 1 | 1 | 0 | +1.00 | +1.00 | `F|low10&F200|x:hold10|on:UPRO` |

## 1. Unlevered mean reversion: a clean negative, now and since 1986

* **Standalone dip timers (T)**: the textbook rules (RSI(2) < 10 above the 200-day average, exit
  RSI(2) > 65; ConnorsRSI < 15; 3 down days; 10-day low; %b < 0) are in the market 10-30% of the
  time. Over 2000-2026 every one of them loses to SPY even in an IRA (best NONE score -3.3 pp/yr);
  in CA it is worse. On 1986-2026 mutual-fund twins (VFINX / short-Treasury fund, VFINX
  benchmark) they lose 5.3-5.6 pp/yr and also lose in the pre-2000 holdout (-8.6 to -9.9 pp/yr on
  10-year windows ending before 2000). Short-horizon reversal on the S&P is real (see section 4),
  but it is too small and too rare to pay for sitting in T-bills the rest of the time.
* **Tax-aware timers (K)**: forbidding the sale of winners before 366 days does not rescue them
  (CA -1.3 to -4.7 pp/yr; 1986+ CA -0.6 pp/yr).
* **Buying drawdowns from a reserve (L, VL unlevered)**: holding 20-100% in short Treasuries
  and deploying it at 10/20/30% drawdowns or VIX 30/40/50 spikes, then holding >= 366 days:
  best CA score +0.12 pp/yr on screen (median -0.6); on the full protocol -0.15 (100% reserve,
  buy everything after a 30% drawdown) and -0.05 (30% reserve); 1986+ twins -0.1 to -1.5 pp/yr.
  The occasional great entry (2002, 2009) does not pay for the years of cash drag.
* **VIX risk-off and volatility targeting (V, S)**: fleeing to T-bills when VIX > 25-40, its
  252-day percentile > 0.8, or VIX/VIX3M > 1 loses 0.3-7.5 pp/yr in CA; volatility targeting loses in
  every CA variant (best -0.2 pp/yr; 1986+ twins -0.5).
* **Baskets, cross-sectional and pairs (B, X, P)**: per-asset dip rules on sectors and on the
  22-ETF menu lose 1.6-10.2 pp/yr in both regimes (CA: 3.6-9.3); buying last week's/month's/quarter's
  losers loses 2.1-9.1 pp/yr in CA (0 of 90 positive);
  3-5-year losers (DeBondt-Thaler) with tax execution are about zero (+0.25 pp/yr after the
  look-ahead-free correction, boot_p 0.54); the only positive pair (QQQ/SPY) is a QQQ tilt
  (+1.4, boot_p 0.47 — hindsight instrument).
* **The website's own mean-reversion timers (SITE)**: plain RSI(14) 30/70, RSI(2), Bollinger and
  volatility-reversion timers on SPY lose 2.8-10.7 pp/yr (cash earns 0% while out). Tax-managed
  monthly Bollinger is +1.4 pp/yr in CA on the full protocol (10-year beat 0.63, boot_p 0.18): it
  waits in cash for a monthly close below the lower band and then almost never sells (the gain
  budget blocks it), so it is a lucky entry delay — 1986+ twin +0.3 pp/yr, pre-2000 holdout
  -0.6 pp/yr. Swapping these timers into the incumbent momentum preset does not help (Bollinger +0.0,
  volatility reversion -5.2, RSI -7.3 pp/yr; with RSI it never buys anything).

## 2. Leveraged rules: real ETFs vs SYNTHETIC history

Real leveraged ETFs only cover 2006/2009-2026. Over those windows buying leverage and holding
it beats SPY with "good confidence" by the mechanical criteria (90% SPY + 10% UPRO, never traded:
CA +2.38 pp/yr, boot_p 0.015; 20% UPRO +4.28, boot_p 0.011; constant 1.3x rebalanced monthly
+1.97, boot_p 0.002). Any leveraged rule therefore has to be judged against (a) the same
leverage without the rule and (b) SYNTHETIC history that includes 1987, 2000-02 and 2008.

Real = engine on real SSO/UPRO (windows from 2006/2009); SYNTHETIC = engine on synthetic 2x/3x of SPY (2000+, screen protocol) or VFINX (1986+, long_screen protocol). pp/yr.

| config | real score / boot_p | SYN 2000+ score / 10y beat / boot_p / max DD | SYN 1986+ score / 10y beat / boot_p / ho10 / max DD |
|---|---|---|---|
| `L|swap100|ddATH:30|dip:UPRO|rel:ath` | +7.85 / 0.02 | +2.91 / 0.53 / 0.31 / -0.88 | +1.01 / 0.39 / 0.36 / +0.97 / -0.91 |
| `L|swap100|ddATH:10/20/30|dip:UPRO|rel:ath` | +7.22 / 0.00 | +1.00 / 0.47 / 0.50 / -0.92 | -1.92 / 0.39 / 0.64 / +1.08 / -0.95 |
| `L|res30|ddATH:5/10/15/20|dip:UPRO|rel:never` | +5.64 / 0.01 | +1.84 / 0.53 / 0.56 / -0.65 | +1.37 / 0.52 / 0.29 / +5.71 / -0.79 |
| `L|swap100|ddATH:30|dip:SSO|rel:ath` | +3.23 / 0.25 | +1.90 / 0.82 / 0.26 / -0.75 | +0.88 / 0.61 / 0.36 / +0.48 / -0.79 |
| `E|swap100|dd>10&sma50up|dip:UPRO|rel:ath` | +5.91 / 0.02 | -1.88 / 0.47 / 0.65 / -0.96 | -1.74 / 0.45 / 0.54 / +5.37 / -0.97 |
| `E|swap100|dd>10&sma200up|dip:UPRO|rel:ath` | +5.08 / 0.08 | +4.67 / 1.00 / 0.18 / -0.81 | +2.72 / 0.84 / 0.37 / +0.35 / -0.81 |
| `V|fear|vix>35->SSO|vix<15->spy` | +1.66 / 0.45 | +0.70 / 0.65 / 0.42 / -0.78 | -0.29 / 0.48 / 0.70 / +1.07 / -0.89 |
| `VF|vix>35->SSO|vix<12->spy` | +2.62 / 0.25 | +1.22 / 0.59 / 0.27 / -0.78 | +0.24 / 0.48 / 0.51 / +2.20 / -0.88 |
| `V|vrp21>5&F200->SSO|vrp<0|<sma200->spy` | +0.58 / 0.53 | -0.21 / 0.41 / 0.69 / -0.66 | -0.70 / 0.32 / 0.95 / -2.32 / -0.62 |
| `VL|res30|vix>30|dip:UPRO|rel:never` | +4.85 / 0.01 | +1.50 / 0.53 / 0.54 / -0.65 | +0.80 / 0.48 / 0.24 / +5.91 / -0.83 |
| `F|crsi<15&F200|x:hold7|on:UPRO` | -1.13 / 0.55 | +0.77 / 0.59 / 0.42 / -0.66 | +0.93 / 0.71 / 0.59 / -0.84 / -0.67 |
| `F|low10&F200|x:hold10|on:UPRO` | +0.82 / 0.29 | +2.06 / 0.88 / 0.17 / -0.62 | +0.65 / 0.68 / 0.64 / -3.23 / -0.75 |
| `TX|crsi<15&F200|x:hold5|on:UPRO|minhold366` | +7.16 / 0.03 | +5.25 / 1.00 / 0.04 / -0.61 | +4.18 / 0.71 / 0.24 / +4.08 / -0.78 |
| `TX|pctb<0&F200|x:rsi2>65|on:UPRO|minhold366` | +9.20 / 0.02 | +7.18 / 1.00 / 0.10 / -0.70 | +3.52 / 0.74 / 0.32 / +2.20 / -0.74 |
| `TXC|trend200|UPRO-above|SPY-below` | +8.57 / 0.10 | +3.90 / 0.76 / 0.40 / -0.81 | +4.44 / 0.81 / 0.12 / +8.54 / -0.83 |
| `TXC|always&F200|x:hold5|on:UPRO|mh366` | +5.59 / 0.23 | +3.88 / 0.88 / 0.34 / -0.71 | +4.17 / 0.84 / 0.26 / +5.23 / -0.78 |
| `RH|res20|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` | +1.59 / 0.11 | +2.40 / 1.00 / 0.09 / -0.73 | +2.71 / 0.94 / 0.08 / +2.44 / -0.77 |
| `RHN|res20|pctb<0&F200|x:rsi2>65|dip:UPRO|hold366` | +3.44 / 0.01 | +3.20 / 1.00 / 0.02 / -0.66 | +1.97 / 0.87 / 0.03 / +1.48 / -0.63 |
| `RHN|res30|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` | +2.25 / 0.15 | +3.34 / 1.00 / 0.08 / -0.77 | +3.70 / 0.94 / 0.07 / +3.39 / -0.77 |
| `RHN|res20|always|x:rsi2>65|dip:UPRO|hold366` | +3.07 / 0.06 | +0.81 / 0.47 / 0.71 / -0.59 | +0.59 / 0.48 / 0.52 / +3.13 / -0.79 |
| `RHN|res20|F200only|x:rsi2>65|dip:UPRO|hold366` | +1.67 / 0.18 | +0.51 / 0.53 / 0.55 / -0.62 | +0.70 / 0.61 / 0.77 / +2.77 / -0.75 |
| `RHN|res20|rsi2<10&nofilt|x:rsi2>65|dip:UPRO|hold366` | +2.61 / 0.06 | +0.71 / 0.53 / 0.67 / -0.60 | +0.71 / 0.55 / 0.65 / +3.42 / -0.77 |
| `CTRL|SPY+UPRO|1.3x|M` | +1.97 / 0.00 | +0.79 / 0.76 / 0.39 / -0.67 | +0.70 / 0.77 / 0.50 / +1.78 / -0.71 |
| `CTRL|SPY+UPRO|1.5x|M` | +3.30 / 0.00 | +1.23 / 0.76 / 0.41 / -0.75 | +1.08 / 0.74 / 0.34 / +2.97 / -0.77 |
| `CTRL|SPY+UPRO|2.0x|M` | +6.66 / 0.00 | +2.09 / 0.71 / 0.44 / -0.88 | +1.76 / 0.68 / 0.30 / +6.05 / -0.90 |
| `BHC|SPY+UPRO|upro0.1` | +2.38 / 0.01 | +0.79 / 0.53 / 0.63 / -0.57 | +0.73 / 0.58 / 0.27 / +2.30 / -0.64 |
| `BHC|SPY+UPRO|upro0.2` | +4.28 / 0.01 | +1.40 / 0.53 / 0.63 / -0.59 | +1.30 / 0.58 / 0.27 / +4.15 / -0.73 |
| `BHC|SPY+UPRO|upro0.3` | +5.84 / 0.01 | +1.87 / 0.53 / 0.63 / -0.64 | +1.76 / 0.58 / 0.28 / +5.72 / -0.80 |
| `BHC|SPY+UPRO|upro0.5` | +8.52 / 0.01 | +2.53 / 0.53 / 0.62 / -0.74 | +2.41 / 0.58 / 0.28 / +8.30 / -0.88 |


* **Drawdown ladders (L, E)**: the CA winners on real data (+7.9 pp/yr: swap all of SPY into UPRO
  after a 30% drawdown from the high) are two trades — all-in UPRO in July 2010 and on 20 March
  2020. On SYNTHETIC history the same rule went all-in during 2001-02 and 2008: 10-year beat 0.53
  (2000+) and 0.39 (1986+), max drawdown -88% / -91%.
* **VIX "lever up on fear" (V, VF)**: hold SSO from VIX > 35 until VIX < 15: +1.7 pp/yr CA on real
  data (boot_p 0.45, -79% drawdown), +0.7 on SYNTHETIC 2000+, -0.3 on 1986+. Part of its CA score is
  an engine artefact (lab notes: tax bills paid from cash leave it 3-6% "short cash" at 0%).
* **Tax-aware whole-book overlays (TX/TXN)**: switch the whole book to UPRO on a dip in an uptrend,
  cut losers immediately, hold winners >= 366 days. In UPRO 69% of days (2.4x average exposure):
  CA +7.2 pp/yr on real full (boot_p 0.033) and +5.3 on SYNTHETIC 2000+ (boot_p 0.045), but on
  SYNTHETIC 1986+ 0 of 26 variants pass (main config +4.2, 10-year beat 0.71, boot_p 0.25), and
  the same structure with no dip entry, or plain "UPRO above the 200-day average, else SPY", does
  as well (+4.2 to +4.4 pp/yr on 1986+). It is leveraged trend following, not mean reversion.
* **Reserve-funded leveraged dip sleeve (RH family)** — the closest call; section 3.

## 3. The closest call: the reserve-funded, tax-aware leveraged dip sleeve (RH)

Rule (kind `mean_reversion.ladder`, existing code): 80% SPY (never traded) + 20% short
Treasuries (`SHY`, `VFISX` before 2002). When SPY closes below its lower Bollinger band
(%b(20, 2) < 0) — or RSI(2) < 10 — while above its 200-day average, the whole reserve buys UPRO.
The tranche is held at least 366 days (gains are long-term), then sold back into T-bills on the
next RSI(2) > 65 day, and the rule re-arms. The ladder kind pays each January's tax bill by
selling the reserve, then the core (no negative cash).

| evidence (CA) | %b version | RSI(2) version | no-timing twin ("always") |
|---|---|---|---|
| real full 2009-07+: score / full / 10y beat / 15y beat / boot_p | +3.44 / +4.73 / 1.00 / 1.00 / 0.009 | +1.59 / +2.32 / 0.83 / 1.00 / 0.114 | +3.07 / +5.40 / 1.00 / 1.00 / 0.060 |
| SYNTHETIC full 2000+ (95 starts) | +2.79 / +4.75 / 0.99 / 1.00 / 0.016 | +2.02 / +3.43 / 0.88 / 0.96 / 0.085 | (screen) +0.81, beat 0.47, p 0.71 |
| SYNTHETIC long 1986+ (151 starts) | +1.75 / +2.33 / 0.85 / 0.92 / 0.029 | +2.52 / +3.48 / 0.89 / 0.97 / 0.080 | (long_screen) +0.59, beat 0.48, p 0.52 |
| pre-2000 holdout (SYNTHETIC, 10-year windows) | +0.90 (beaten 59%) | +2.01 (76%) | +3.13 (100%) |
| average exposure / T-bill weight (real) | 1.57x (1.5x -> 2.7x) / 12% | 1.73x / 4% | |
| max drawdown real / SYNTHETIC 1986+ (SPY -55%) | -54% / -63% | -58% / -77% | -69% / -79% |
| costs 35 bps/side; stricter distribution tax | +2.67; -0.03 to -0.07 | +0.93; -0.01 to -0.03 | |
| deflated Sharpe (2,000 trials) | 0.062 | 0.006 | |

Against the protocol bar (CA):
1-3. pass for the %b version on every dataset; the RSI(2) version misses boot_p on real data.
4. **fail**: the family's walk-forward selection (report.diagnostics) is negative out of sample
   in CA: -4.1 pp/yr (lab default, 3 decisions) and -6.9 pp/yr with yearly decisions
   (12, beat 0.17); only the shorter 5/3 split is positive (+4.6 lab, +2.3
   yearly). On the leveraged SYNTHETIC records (where every leveraged rule exists
   from 2000/1986) walk-forward is positive (+4.7 / +1.9 pp/yr) but beats only
   54-67% of the time and PBO is 0.54 (2000+) / 0.36 (1986+).
5. partial: all 9 %b neighbours (thresholds -0.1/0.1/0.2, window 15/25, width 1.5/2.5, 30%
   reserve, 450-day hold) are positive in CA on every dataset, but only 4/9 (real, screen), 5/9
   (2000+) and 2/9 (1986+) pass criteria 1-3; of the RSI(2)-family robustness variants 7/11 pass on
   2000+ and 3/11 on 1986+.
6. no hindsight instrument (S&P 500 and its 3x fund), but the real-ETF evidence is 2009-2026 only.
7. the pre-2000 holdout (SYNTHETIC) is positive, i.e. does not contradict.

What it is: the dip entry and overbought exit matter relative to the same sleeve without timing
(on SYNTHETIC 1986+ the timed sleeve beats its untimed twins by +2.2 to +3.8 pp/yr, p 0.01-0.08),
but the whole package is not better than taking the same risk without it: vs constant 1.5x/2x
leverage or buy-and-hold 30-50% UPRO the monthly after-tax difference on the 1986+ path is +0.6
to +2.7 pp/yr (p 0.10-0.41); vs "UPRO above the 200-day average, else SPY" it is -1.1 to +3.0 (p
0.20-0.67). And on real 2009-2026 data the untimed twin beats the RSI(2) version. Verdict:
**does not clear the bar** (criterion 4, deflated Sharpe, leverage-explained).

## 4. Tax-deferred account (NONE): a genuine short-term edge, leveraged

| ConnorsRSI(3,2,100) < 15 & SPY > SMA200 -> 3x for 7 days (`F|crsi<15&F200|x:hold7|on:UPRO`) | NONE |
|---|---|
| engine full 2009-07+: score / full / 10y beat / 15y beat / boot_p / max DD | +5.07 / +8.56 / 1.00 / 1.00 / 0.005 / -39% |
| SYNTHETIC 2000+ (FAST-SIM, full) / 1986+ (engine long_screen) | +6.49 (p 0.000) / +7.71 (p 0.000; ho10 +7.55, beaten 100%) |
| permutation vs random entries, same filter / exit / exposure | +5.2 (real, p 0.05), +7.1 (2000+, p 0.00), +8.7 (1986+, p 0.00) |
| exposure | in UPRO 19% of days, 1.38x average; constant 1.3x control +2.97 |
| same rule on 84 other equity ETFs (SYNTHETIC 3x each, 5-day hold) | positive on 73%, mean +2.0 pp/yr |
| costs: 20 / 30 bps per side (hold-5 version, 2000+ / 1986+) | +1.3 / +3.1; -1.4 / +0.2 |
| one-day execution lag (RSI(2) > 65 exit version) | +2.56 real (p 0.059); +6.35 SYNTHETIC 1986+ |
| CA / FED (engine full) | -1.13 / +0.08 |

Its 31-cell neighbourhood (ConnorsRSI < 10/15/20 x 150/200/250-day filter x 3-10 day exits) is
positive in 74-90% of cells but passes criteria 1-3 in only 35-58%; ConnorsRSI < 15 is a ridge.
The family's walk-forward is negative in NONE (-6.7 pp/yr lab default; -6.7 yearly) and the
overlay sub-family's 10/5 walk-forward is negative on real (-6.2) and SYNTHETIC 2000+ (-2.4)
data — selection by trailing performance keeps picking unfiltered variants that buy 3x into
crashes. Fails criterion 4; diagnostic only (the user's money is taxable).

Two VIX rules also pass criteria 1-3 in NONE on real data (vol-risk-premium > 5 & uptrend -> SSO:
+4.23, boot_p 0.041; VIX > 25 & uptrend -> SSO until VIX < 20: +2.78, boot_p 0.017; SYNTHETIC
1986+ +2.6/+2.7, boot_p 0.06/0.003) — both leveraged and both negative-to-zero in CA.

## 5. Family diagnostics (report.diagnostics, screen protocol)

| set | configs | walk-forward 10/5 OOS (lab, 3 dates) | 5/3 OOS (lab) | 10/5 yearly decisions | 5/3 yearly | PBO | deflated Sharpe of best |
|---|---|---|---|---|---|---|---|
| CA_all | 1581 | -4.11 (beat 0.33) | +4.60 (beat 0.75) | -6.90 (12 dates, beat 0.17) | +2.32 (19 dates, beat 0.47) | 0.00 | 0.000 |
| CA_from2000 | 761 | -7.64 (beat 0.33) | +0.66 (beat 0.50) | -9.25 (12 dates, beat 0.08) | -0.99 (19 dates, beat 0.42) | 0.29 | 0.010 |
| CA_unlev | 776 | -7.64 (beat 0.33) | +0.66 (beat 0.50) | -9.25 (12 dates, beat 0.08) | -0.99 (19 dates, beat 0.42) | 0.09 | 0.000 |
| NONE_all | 1583 | -6.73 (beat 0.33) | -1.88 (beat 0.50) | -6.68 (12 dates, beat 0.25) | +3.05 (19 dates, beat 0.53) | 0.12 | 0.000 |
| NONE_from2000 | 762 | -6.78 (beat 0.33) | -6.99 (beat 0.25) | -7.66 (12 dates, beat 0.33) | -1.44 (19 dates, beat 0.47) | 0.35 | 0.000 |
| NONE_unlev | 777 | -6.78 (beat 0.33) | -6.99 (beat 0.25) | -7.66 (12 dates, beat 0.33) | -1.44 (19 dates, beat 0.47) | 0.16 | 0.006 |
| SYNTHETIC leveraged long_screen/CA | 126 | | | +1.92 (26 dates, beat 0.54) | +0.65 (33 dates, beat 0.48) | 0.36 | |
| SYNTHETIC leveraged screen/CA | 217 | | | +4.74 (12 dates, beat 0.67) | +1.37 (19 dates, beat 0.58) | 0.54 | |

The lab-default walk-forward uses 3 decision dates on the yearly screen protocol (lab note 2); the yearly version uses every start. Leveraged-ETF configs only enter a 10-year in-sample window from 2019-2020 on real data, which is why the SYNTHETIC rows are shown. PBO on the full set is computed on months shared by all configs (2009+; lab note 4).

## 6. Hindsight and robustness checks

* Instruments: everything that matters runs on SPY (the benchmark) and its 2x/3x funds; no star
  instrument was chosen for having won. The one positive pair (QQQ/SPY) is a QQQ tilt and fails
  anyway. Menu rules (B, X) were negative or about zero (best CA +0.44 pp/yr, boot_p 0.75; none
  passes), so no random-menu test was needed (the script `hindsight.py` is ready).
* Leverage hindsight is the real issue — handled with SYNTHETIC leverage back to 1986 and with
  constant / buy-and-hold leverage controls on the same windows.
* Cross-index: the NONE overlay works on 73% of 84 equity ETFs from `BROAD_EQUITY_POOL_2003`.
* Execution lag, costs, stricter distribution taxes, parameter neighbourhoods: see sections 3-4.
* Determinism: an RH config re-run under a different label reproduced its numbers exactly.

## 7. Lab notes and suspected lab issues

* **Tax bills paid from cash create interest-free margin** (engine, so the site too): the engine
  deducts each January's tax from cash and lets cash go negative; a timer that realizes gains
  and then holds for a long time carries that negative cash (an interest-free loan) until its
  next trade. VIX "fear" timers average -3% to -6% cash in CA (worth roughly 0.5-1 pp/yr of their
  CA score), whole-book overlays about -1%. The ladder kind settles taxes explicitly.
* **`metrics.walk_forward` steps every 4 starts** (`step_quarters=4`). On the yearly `screen` /
  `long_screen` protocols that is one decision every 4 years: the 10/5 walk-forward in
  `report.diagnostics` uses 3 dates (2012, 2016, 2020). Session 2 also reports a yearly version.
* **`bench_max_dd` is always the benchmark's first-start (2000) drawdown**, so for configs whose
  windows start later (leveraged ETFs: 2006/2009) the strategy-vs-SPY drawdown comparison is not
  like for like (SPY's -55% is 2008; the strategy never saw 2008).
* **PBO with mixed start dates**: `monthly_matrix` drops months not shared by all configs, so a
  family that mixes 2000-start and 2009-start configs gets PBO computed on 2009+ only (CA PBO
  0.00 here just says "leverage won after 2009").
* **Engine is FIFO-only**: switching strategies sell their oldest (lowest-basis) lots first; real
  brokers allow specific-lot / HIFO relief, which would reduce the tax drag of overlays somewhat.
* **Family-code bug (`DipLadder._settle_cash`, this module)**: the ladder pays each January's
  tax bill by selling the funding asset, then the core — never the dip asset. In "swap" ladders
  (`L|swap100...`, `E|swap100...`, fund = core = SPY) the whole core may already be in the
  leveraged fund, so nothing is sold and cash stays negative (interest-free margin); on SYNTHETIC
  1986+ data `E|swap100|dd>15&sma50up|dip:UPRO|rel:ath` even shows equity below zero (max
  drawdown -103%). The RH family keeps an SPY core and is unaffected (average cash 0). These swap
  configs are rejected regardless; a fix (sell the dip asset as a last resort) needs a module
  edit, which would re-run every cached config of the family, so it was left for a later session.
* Session-1 grid flaw (fixed by twins, not a lab bug): 3-5-year-lookback reversal configs had no
  `require_days`, so 2000-2003 windows sat in T-bills until the history existed (dodging
  2000-02). Corrected twins (`XFIX`) are lower (+0.44 -> +0.25 pp/yr) and still fail.
* The engine taxes bond interest and leveraged-fund distributions as deferred capital gains; for
  the RH finalist `realism.adjusted` (annual tax at real character) changes the excess by only
  -0.01 to -0.07 pp/yr (average T-bill weight 4-12%).

## 8. Not tested / ideas for later

* S&P futures overlays (Section 1256: 60/40 long/short-term tax regardless of holding period)
  would cut the CA tax drag of short-term dip trades — the engine has no futures or margin.
* Specific-lot (HIFO) sales for switching strategies — engine is FIFO.
* Rebalancing the RH sleeve back to a fixed weight (needs new kind code; would make its leverage
  stable instead of drifting up) and a version with a stop or trend exit during the 366-day hold.
* New-money (contribution) timing on dips — the engine has no contributions.
* Running the NONE overlay in an IRA next to a taxable SPY core (asset location) — outside the
  lab's single-account model.
* Option-based dip buying (selling puts).

## Appendix: tables

### Finalists, protocol full (engine, real ETFs), CA

Excess in pp/yr. `pass` = criteria 1-3 (score > 0, full > 0, 10y beat >= 0.75, 15y beat >= 0.85, boot_p <= 0.10).

| config | first start | score | full | ex10 | 10y beat | 10y min | 15y beat | boot_p | max DD | trades | NONE score | FED score | pass CA |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `F|crsi<15&F200|x:hold7|on:UPRO` | 2009-07-01 | -1.13 | -0.16 | -1.49 | 0.14 | -3.62 | 0.00 | 0.55 | -0.44 | 465 | +5.07 | +0.08 | no |
| `F|crsi<15&F200|x:hold5|on:UPRO` | 2009-07-01 | -2.04 | -1.58 | -2.51 | 0.00 | -3.94 | 0.00 | 0.81 | -0.45 | 493 | +3.46 | -1.04 | no |
| `F|low10&F200|x:hold10|on:UPRO` | 2009-07-01 | +0.82 | +1.48 | +0.48 | 0.76 | -3.81 | 0.78 | 0.29 | -0.55 | 563 | +8.55 | +2.45 | no |
| `F|rsi3<20&F200|x:rsi2>65|on:UPRO` | 2009-07-01 | -1.66 | -1.58 | -1.81 | 0.00 | -2.89 | 0.00 | 0.78 | -0.42 | 569 | +4.32 | -0.53 | no |
| `F|sma10<-1%&F200|x:hold7|on:UPRO` | 2009-07-01 | -0.78 | -1.80 | -0.56 | 0.24 | -2.48 | 0.00 | 0.80 | -0.52 | 547 | +6.19 | +0.64 | no |
| `F|crsi<15&F200|x:hold5|on:SSO` | 2006-07-01 | -3.07 | -2.91 | -3.26 | 0.00 | -4.38 | 0.00 | 0.99 | -0.61 | 533 | +0.75 | -2.50 | no |
| `F|crsi<15&F200|x:hold7|on:UPRO50` | 2009-07-01 | -2.49 | -2.57 | -2.66 | 0.00 | -3.46 | 0.00 | 0.99 | -0.40 | 465 | +2.71 | -1.58 | no |
| `F|crsi<15&F200|x:rsi2>65|on:UPRO|lag1` | 2009-07-01 | -2.58 | -2.86 | -2.78 | 0.00 | -4.47 | 0.00 | 0.97 | -0.43 | 477 | +2.56 | -1.69 | no |
| `L|swap100|ddATH:30|dip:UPRO|rel:ath` | 2009-07-01 | +7.85 | +8.20 | +8.35 | 1.00 | +3.17 | 1.00 | 0.02 | -0.52 | 15 | +9.63 | +8.66 | yes |
| `L|swap100|ddATH:10/20/30|dip:UPRO|rel:ath` | 2009-07-01 | +7.22 | +8.21 | +7.39 | 1.00 | +2.41 | 1.00 | 0.00 | -0.53 | 70 | +10.65 | +8.68 | yes |
| `L|res30|ddATH:5/10/15/20|dip:UPRO|rel:never` | 2009-07-01 | +5.64 | +9.59 | +5.29 | 1.00 | +1.57 | 1.00 | 0.01 | -0.67 | 10 | +6.26 | +5.96 | yes |
| `L|swap100|ddATH:30|dip:SSO|rel:ath` | 2006-07-01 | +3.23 | +1.85 | +3.04 | 0.95 | -0.14 | 1.00 | 0.25 | -0.75 | 15 | +4.23 | +3.67 | no |
| `V|fear|vix>35->SSO|vix<15->spy` | 2006-07-01 | +1.66 | +0.42 | +1.57 | 0.93 | -0.97 | 1.00 | 0.45 | -0.79 | 33 | +4.15 | +2.35 | no |
| `V|fear|vix>40&F200->SSO|vix<15->spy` | 2006-07-01 | +0.76 | +0.59 | +0.62 | 0.90 | -4.44 | 1.00 | 0.37 | -0.55 | 9 | +1.30 | +0.94 | no |
| `L|res100|ddATH:30|dip:SPY|rel:never` | 2000-01-01 | -0.15 | +1.88 | -0.26 | 0.57 | -7.95 | 0.85 | 0.04 | -0.57 | 3 | -0.16 | -0.17 | no |
| `L|res30|ddATH:30|dip:SPY|rel:never` | 2000-01-01 | -0.05 | +0.62 | -0.08 | 0.57 | -1.89 | 0.79 | 0.13 | -0.54 | 10 | -0.03 | -0.05 | no |
| `CTRL|SPY+UPRO|1.3x|M` | 2009-07-01 | +1.97 | +1.86 | +1.98 | 1.00 | +1.52 | 1.00 | 0.00 | -0.41 | 410 | +2.97 | +2.40 | yes |
| `CTRL|SPY+SSO|1.3x|M` | 2006-07-01 | +1.63 | +0.91 | +1.75 | 1.00 | +0.35 | 1.00 | 0.22 | -0.67 | 482 | +2.29 | +1.93 | no |
| `BHC|SPY+UPRO|upro0.1` | 2009-07-01 | +2.38 | +4.70 | +2.24 | 1.00 | +0.86 | 1.00 | 0.01 | -0.53 | 2 | +2.66 | +2.52 | yes |
| `BHC|SPY+UPRO|upro0.2` | 2009-07-01 | +4.28 | +7.54 | +4.08 | 1.00 | +1.66 | 1.00 | 0.01 | -0.62 | 2 | +4.77 | +4.53 | yes |
| `V|vrp21>5&F200->SSO|vrp<0|<sma200->spy` | 2006-07-01 | +0.58 | -0.14 | +0.50 | 0.71 | -1.75 | 0.67 | 0.53 | -0.62 | 233 | +4.23 | +1.48 | no |
| `V|fear|vix>25&F200->SSO|vix<20->spy` | 2006-07-01 | +0.05 | -0.13 | -0.03 | 0.44 | -4.29 | 0.48 | 0.52 | -0.61 | 89 | +2.78 | +0.69 | no |
| `VF|vix>35->SSO|vix<12->spy` | 2006-07-01 | +2.62 | +2.10 | +2.48 | 0.90 | -0.32 | 1.00 | 0.25 | -0.79 | 23 | +5.52 | +3.48 | no |
| `E|swap100|dd>10&sma50up|dip:UPRO|rel:ath` | 2009-07-01 | +5.91 | +6.79 | +5.95 | 1.00 | +1.01 | 1.00 | 0.02 | -0.52 | 21 | +7.76 | +6.71 | yes |
| `S|rv21|tgt20|cap1.0|M` | 2000-01-01 | -0.24 | -0.73 | -0.17 | 0.55 | -2.51 | 0.53 | 0.78 | -0.46 | 163 | +0.22 | -0.09 | no |
| `K|crsi<15|x:c>sma5|minhold366` | 2000-01-01 | -1.57 | -1.82 | -1.47 | 0.49 | -6.99 | 0.23 | 0.86 | -0.40 | 247 | -1.11 | -1.46 | no |
| `SITE|SPY|boll20-1.5|taxmanaged-M` | 2000-01-01 | +1.43 | +2.00 | +1.79 | 0.63 | -2.78 | 0.85 | 0.18 | -0.34 | 21 | -4.20 | +1.57 | no |
| `SITE|SPY|boll20-2|taxmanaged-M` | 2000-01-01 | +1.33 | +2.01 | +1.93 | 0.67 | -3.58 | 0.89 | 0.18 | -0.34 | 11 | -2.51 | +1.44 | no |
| `TX|crsi<15&F200|x:hold5|on:UPRO|minhold366` | 2009-07-01 | +7.16 | +8.74 | +7.11 | 1.00 | +0.58 | 1.00 | 0.03 | -0.61 | 121 | +11.27 | +8.82 | yes |
| `TX|pctb<0&F200|x:rsi2>65|on:UPRO|minhold366` | 2009-07-01 | +9.20 | +8.42 | +9.59 | 1.00 | +3.25 | 1.00 | 0.02 | -0.50 | 91 | +13.48 | +10.87 | yes |
| `TX|rsi2<15&F200|x:rsi2>65|on:UPRO|minhold366` | 2009-07-01 | +3.66 | +3.92 | +2.74 | 0.90 | -2.47 | 1.00 | 0.22 | -0.79 | 103 | +7.20 | +4.95 | no |
| `TX|rsi2<10&F200|x:rsi2>65|on:UPRO|minhold366` | 2009-07-01 | +4.34 | +5.18 | +3.96 | 0.90 | -2.28 | 1.00 | 0.16 | -0.77 | 115 | +7.69 | +5.66 | no |
| `RH|res20|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` | 2009-07-01 | +1.59 | +2.32 | +1.41 | 0.83 | -0.58 | 1.00 | 0.11 | -0.58 | 75 | +2.60 | +2.02 | no |
| `RHN|res20|crsi<15&F200|x:rsi2>65|dip:UPRO|hold366` | 2009-07-01 | +1.79 | +2.32 | +1.84 | 0.97 | -0.19 | 1.00 | 0.11 | -0.57 | 70 | +2.79 | +2.20 | no |
| `RHN|res20|pctb<0&F200|x:rsi2>65|dip:UPRO|hold366` | 2009-07-01 | +3.44 | +4.73 | +3.29 | 1.00 | +0.10 | 1.00 | 0.01 | -0.54 | 67 | +4.98 | +4.12 | yes |
| `RHN|res30|rsi2<10&F200|x:rsi2>65|dip:UPRO|hold366` | 2009-07-01 | +2.25 | +3.24 | +1.94 | 0.83 | -0.88 | 1.00 | 0.15 | -0.67 | 75 | +3.67 | +2.86 | no |
| `RHN|res20|always|x:rsi2>65|dip:UPRO|hold366` | 2009-07-01 | +3.07 | +5.40 | +2.88 | 1.00 | +0.72 | 1.00 | 0.06 | -0.69 | 81 | +4.57 | +3.71 | yes |


