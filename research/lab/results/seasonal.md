# Family `seasonal`: calendar and seasonality strategies

Module: `research/lab/families/seasonal.py` (signals `seasonal.cal`, `seasonal.samemonth`). The module
was not edited in the resumed session, so every cached result stays valid.
Scripts, logs and label maps are in `research/lab/scratch/seasonal/`. `grids.py` defines every config.
`run_grid.py`, `finalists.py`, `lowcost.py` and `queue3.sh`/`queue4.sh` ran them. `build_md.py`
regenerates every table below from the cache (`seasonal_template.md` holds the text). `holdings.py`
replays one run to show its holdings, `diag.py` computes the diagnostics and `assemble.py` writes the CSV.
The full table of every run is `research/lab/results/seasonal_table.csv`: one row per config x regime x
protocol x cost setting, with columns `protocol`, `comm`, `slip`, `group`, `era`, `dup_labels`, `cfg`.

This family was started by a researcher who was cut off, then finished by a successor using the same
code and cache. The successor completed the pending runs: G19 controls and basket placebo, G21 random
menus, long-protocol twins and cost sensitivity. It also added G22, a set of checks on the one
California config that clears bar items 1-3, and revised the verdict to match.

## Verdict

**For the user's taxable account (CA primary, FED secondary), no calendar or seasonality strategy beats
buying and holding SPY with good confidence.**

* **After tax, calendar timing loses almost without exception.** We screened the 262 pre-registered
  calendar rules (G1-G18) on 2000-2026 ETF data. Only 6 have a positive CA score:
  * four January / first-five-days / Santa barometers, which trade about once a year (+0.21 to
    +0.70 pp/yr score, 10-year beat rate 0.53, boot_p 0.44-0.68);
  * two constant-leverage controls, which are not seasonal.

  The median CA score is -3.47 pp/yr. Over 1986-2026 (235 rules on mutual-fund proxies) the median is
  -3.18 pp/yr, 3 rules are positive and the best is +0.27. A rule that switches twice a year realizes gains on
  positions held less than a year (taxed at 48.1% in CA) and gives up tax deferral. Buy-and-hold pays nothing until the end.
* **The only CA configs that clear bar items 1-3 are calendar strategies in name only.** The
  sector-season rule holds the cyclical SPDRs XLY/XLI/XLB/XLK in Nov-Apr and SPY in May-Oct. Run with
  tax-managed execution (gains realized only up to 1% of the portfolio per year), it scores **+0.64 pp/yr in CA on the full
  protocol**: full_excess +1.18, ex10_beat 0.84, ex15_beat 0.91, boot_p 0.025. Its Oct 1-May 1
  neighbour gets score +0.85, ex10_beat 0.91, ex15_beat 0.94, boot_p 0.035. These are roughly the
  incumbent preset's numbers (+0.66, 0.70, 0.83, 0.025) with better beat rates.

  But the gain budget blocks the switch whenever the holdings show gains. After the 2000-02 bear
  market it holds about 85-90% cyclical sectors (XLK 23-33%) and 10-20% SPY all year (see the holdings
  replay below). A gain budget of zero does as well (+0.53 on the screen). Its edge comes mostly from 2000-10
  (+1.90 pp; 2010-20 -0.04, 2020-26 -0.55). **It fails the bar:**
  * (4) the family's walk-forward selection loses out of sample in the ETF era (CA -2.97 pp/yr with
    yearly decisions, and -0.57 even inside the sector-season sub-family). Over 1986-2026 it is
    about zero (CA -0.43);
  * (5) is mixed: the score holds across the neighbourhood, but confidence does not (see below);
  * (6) it depends on the menu. Without XLK it fails (+0.46, ex10_beat 0.66, boot_p 0.30). The same
    rule on 24 random 4-fund menus from `BROAD_EQUITY_POOL_2003` is positive in only 8 of 24 (median
    -0.11 pp, none clears items 1-3), and the best of those menus hold tech funds;
  * (7) the pre-2000 holdout does not contradict it, but it does not confirm it either. The
    1986-2026 Fidelity twin scores +1.50 in CA with boot_p 0.135, and only half of its pre-2000
    5-year windows beat VFINX (mean +1.09 pp).

  Its neighbourhood (season boundaries, gain budgets 0-3%) is positive throughout (+0.39 to +0.77 on the
  screen), but confidence fades above a 1% budget (boot_p 0.14-0.27).

  What actually beat SPY in CA is the static tilt. Buying the four cyclical SPDRs once and never
  trading scores +1.21, with every 10- and 15-year window and all three sub-periods positive, but
  boot_p is 0.29. Without XLK the static basket fails (+0.46, boot_p 0.35). That is a sector bet that
  includes technology (a quarter of the basket at purchase), for the sector and factor families to
  judge, and not a calendar effect.
* **In tax-deferred accounts (NONE, diagnostic only), sector seasonality is the one calendar idea
  with a persistent edge, and it still fails the bar.** All of these lose to SPY over 2000-2026:
  Halloween / Sell-in-May into T-bills, Sy Harding's MACD version, turn-of-month, pre-holiday,
  day-of-week, Santa rally, barometers, the presidential cycle, options-expiry weeks, quarter-end
  rebalancing and same-calendar-month rotation. Several looked good only in windows starting in
  1986-87 or 2000-02, which contain the big crashes, and lose in recent windows. Even at
  near-zero costs the turn-of-month, pre-holiday, Monday and T-bill Halloween rules lose.

  Sector seasonality (cyclicals Nov-Apr, SPY May-Oct) does clear items 1-3:
  * on the full protocol: +0.98 pp/yr, 10-year beat rate 1.00, boot_p 0.071. The Oct 1-May 1
    version scores +1.21 (boot_p 0.048) and the no-tech version +1.46 (boot_p 0.035);
  * on the 1986-2026 Fidelity version: +2.69, boot_p 0.008, pre-2000 5-year windows +2.49 pp.

  It fails item 4. The family's walk-forward is negative in the ETF era (NONE -3.90 pp/yr) and about
  zero over 1986-2026. Inside the sector-season sub-family it is negative in 2000-2026 (-1.22) and
  positive over 1986-2026 (+3.73), but only for decisions made before 2009. It is also fragile on
  item 6. On 24 random menus
  the same rule beats SPY only 7 times (median -0.22 pp). Among all 126 four-SPDR baskets the cyclical
  one ranks 11th: 58% of the other baskets are positive, with a median of +0.07 pp. On the 1986-2026
  Fidelity funds it ranks 1st, but 120 of the other 125 baskets also beat VFINX (median +1.10 pp).
  Much of the long-history "sector seasonality" is therefore Fidelity sector funds beating the index
  fund. The seasonal switch does add
  something over holding the same basket all year: it is better for 19 of 24 random menus (median
  +1.35 pp), and reverse-season placebos lose. But over 2000-2026, holding the cyclical basket all
  year did as well (+1.22). After tax it loses (CA -2.17 pp/yr).
* **Leverage is not seasonality.** Holding SSO (2x) in Nov-Apr and SPY in May-Oct gains +4.32 pp/yr
  score in NONE, but holding the same average leverage all year gains +3.68 pp/yr. Both have -73 to
  -75% drawdowns (SPY -55%) and neither passes boot_p (0.162, 0.117). In CA the seasonal leverage loses
  (-1.33).

### Addendum (resumed session)

The predecessor's draft verdict said that no calendar rule beats SPY after California taxes. The
predecessor also wrote that tax-managed execution only helps by suppressing trades. That second point
holds: tax management turns the rule back into buy-and-hold of whatever it happened to own. But the cache already contained a
tax-managed sector-season config that clears items 1-3 in CA (finalist tier 2). The successor checked it
against items 4-7 and found the following:
* **Holdings replay:** after 2002 it barely trades. It made one more full switch, in late 2008.
* **Neighbourhood (G22):** 5 more season boundaries and 4 more gain budgets. All are positive in CA,
  and confidence holds only for budgets of 1% or less.
* **Static controls (G22):** buy-and-hold of the same baskets with no rebalancing.
* **PROTOCOL 5.3 random menus with the same tax-managed rule (G22):** none clears items 1-3.
* **Long-protocol twins.**

The family's walk-forward is negative in both regimes in the ETF era and about zero over 1986-2026
(table below), so item 4 fails for every member, including this config.

The resumed session also:
* completed the interrupted G19 (controls, 125-basket placebo), G21 (random menus) and long-protocol
  runs;
* corrected some details: barometer boot_p is 0.44-0.68 rather than 0.6-0.9, and the config counts
  are updated. "Same-season ranking" was drafted in `sameseason_draft.py` but never added to the
  module or run, so it is not counted.

## What was tested (all of it)

Calendar rules decide at today's close what to hold for the **next** trading day. Day positions
(k-th trading day of the month or quarter, pre-holiday, options-expiry week and so on) come from a
**scheduled NYSE calendar built from the exchange's holiday rules**, never from the realized data
calendar. The successor re-checked it against SPY, VFINX and ^GSPC from 1980 to 2026. It matches the
data exactly except on 12 unscheduled closures: Hurricane Gloria 1985, Nixon's funeral 1994, four
days after 9/11, Reagan 2004, Ford 2007, Hurricane Sandy (2 days), G.H.W. Bush 2018 and Carter 2025.
A trader could not have known those closures in advance either.

Price-dependent rules (MACD, trend, barometers, the quarter-to-date pension signal) use closes up to
today. Learned rules (learned months, same-month ranking) use only years before the current one. All
trades pay the site's 5 bps commission + 5 bps slippage per side.

Safe assets are funds that exist for the whole window: VFISX (short Treasury, from 1991; VWSTX
short muni before that), VFITX (intermediate), VUSTX (long Treasury), VBMFX (total bond), or cash at 0%.

| group | idea | ETF-era configs | long-era configs | runs |
|---|---|---|---|---|
| G1 | Halloween / Sell-in-May windows: entry Oct 1/Oct 15/Nov 1/Nov 15/Dec 1 x exit Apr 1/Apr 15/May 1/May 15/Jun 1/Jul 1 x safe short/long, + cash/inter/agg | 63 | 63 | screen CA+NONE |
| G2 | placebo: all 12 six-month windows; avoid each single month; avoid each pair of months | 35 | 35 | screen CA+NONE |
| G3 | folklore exclusions (Jun-Sep, May-Sep, Jul-Sep, Jun+Aug+Sep) | 4 | 4 | screen CA+NONE |
| G4 | turn of month: last 1/2/4 + first 2/3/5 days x cash/short | 18 | 18 | screen CA+NONE |
| G5 | first half of month, mid-month exclusions, pre-holiday, Santa only, Mondays, OpEx weeks, quarter-end | 14 | 14 | screen CA+NONE |
| G6 | presidential cycle (5 variants x short/long) | 10 | 10 | screen CA+NONE |
| G7 | January / first-five-days / Santa barometers (+ as Halloween vetoes) | 8 | 8 | screen CA+NONE |
| G8 | Sy Harding seasonal + MACD (entry x exit x safe, MACD 12-26-9 and 8-17-9) | 20 | 20 | screen CA+NONE |
| G9 | season x trend hybrids + trend-only controls | 10 | 10 | screen CA+NONE |
| G10 | seasonal leverage (SSO/UPRO in season, TOM swaps, core+satellite) + constant-leverage controls | 13 | - | screen CA+NONE |
| G11 | January effect: small caps (IWM/NAESX) Dec 1/15/24 to Jan 15/Feb 1/Mar 1; small-cap Halloween | 11 | 11 | screen CA+NONE |
| G12 | sector seasons (cyclicals vs defensives vs index) | 5 | 5 | screen CA+NONE |
| G13 | same-calendar-month seasonality (Heston-Sadka) on sectors / countries | 22 | 9 | screen CA+NONE |
| G14 | learned month selection from ^GSPC (1928+) / VFINX history | 16 | 16 | screen CA+NONE |
| G15 | quarter-end pension-rebalancing rule | 6 | 6 | screen CA+NONE |
| G16 | composites (Halloween + TOM / pre-holiday / pre-election year) | 4 | 4 | screen CA+NONE |
| G17 | tax-managed Halloween (gain budget, no short-term gains) | 3 | 3 | screen CA+NONE |
| G18 | Halloween on international / small caps | 2 | 2 | screen CA+NONE |
| G19 | sector-season controls (23 ETF / 8 long): same baskets all year, swapped seasons, single sectors, basket definitions, boundary neighbours, tax-managed versions | 23 | 8 | screen CA+NONE |
| G19 | basket placebo: **every other 4-sector basket** in Nov-Apr, index otherwise (ETF: SPDRs; long: Fidelity Select funds) | 125 | 125 | screen NONE (ETF: 44 also in CA, from the interrupted run) |
| G21 | PROTOCOL 5.3 hindsight check: 24 random 4-fund menus from `BROAD_EQUITY_POOL_2003`, in Nov-Apr (SPY otherwise) and all year | 48 | - | screen NONE |
| G22 | checks on the CA candidate (successor): the same 24 random menus through the tax-managed season rule; 5 season boundaries x TAX; gain budgets 0/0.5/2/3%; never-rebalanced buy-and-hold of the cyclical baskets | 35 | 1 | screen CA (+ buy-and-hold on full / long) |
| **total** | (2 ETF and 3 long labels are byte-identical duplicates of another group's config) | **495 labels / 493 configs** | **372 / 369** | |

Finalists: 23 ETF configs on `full` (95 quarterly starts) x CA/FED/NONE, and 8 long-history twins on `long`
(151 quarterly starts, VFINX benchmark) x CA/FED/NONE. Cost sensitivity: 8 configs on `screen` NONE at
0 commission + 1 bp slippage. Counting every regime, protocol and cost setting, the CSV holds
1,536 records of 862 configs.

## Raw effects (descriptive, not a backtest)

This is the S&P 500 price index (^GSPC), log returns by era. TOM = the last trading day of each month
plus the first three of the next.

| era | Nov-Apr %/yr | May-Oct %/yr | TOM bp/day | other bp/day | TOM share of return | pre-holiday bp/day | Monday bp/day | September %/yr |
|---|---|---|---|---|---|---|---|---|
| 1928-1949 | -2.11 | +1.88 | 16.58 | -4.06 | n/a | 41.92 | -14.10 | -3.29 |
| 1950-1969 | +7.10 | +1.41 | 16.48 | 0.30 | 0.93 | 26.86 | -14.61 | -0.14 |
| 1970-1987 | +5.93 | -0.45 | 10.04 | 0.32 | 0.88 | 26.36 | -14.14 | -1.41 |
| 1988-1999 | +10.07 | +4.79 | 14.11 | 3.95 | 0.46 | 10.62 | +10.52 | +0.90 |
| 2000-2009 | -0.07 | -2.69 | 2.77 | -2.01 | n/a | 8.26 | -3.14 | -2.53 |
| 2010-2026 | +6.70 | +4.50 | 5.86 | 4.29 | 0.24 | 11.24 | +4.05 | -0.72 |

The Halloween spread (Nov-Apr minus May-Oct, per season-year) by era:

| era | spread %/yr | t-stat |
|---|---|---|
| 1950-69 | +5.95 | 3.25 |
| 1970-87 | +6.48 | 1.90 |
| 1988-99 | +4.66 | 1.78 |
| 2000-09 | +1.89 | 0.41 |
| 2010-26 | +2.20 | 0.87 |

The successor re-ran `raw_effects.py` and got the same numbers. The patterns are real and well known,
but they weakened after publication (turn of month 1987-88, Monday effect 1980, Halloween 2002). More
importantly, summer returns are positive: SPY's May-Oct return beat short Treasuries (VFISX) in 19 of
26 years from 2000 to 2025, so stepping out costs more than it saves. Holding only turn-of-month days
kept 88-93% of the index's return before 1988 but only 24-46% after.

## Screen results

### Best config per group (score = mean of 5/10/15-year average excess, pp/yr)

`n_pos` counts configs with score > 0. Groups that ran in only one regime appear only in that regime.

#### ETF era (2000-2026), `screen`

| regime | group | n | n_pos | median | best | best_score |
|---|---|---|---|---|---|---|
| NONE | G1 | 61 | 8 | -1.65 | G1 win Oct1-May15 safe=long | +2.43 |
| NONE | G2 | 37 | 5 | -2.49 | G2 avoid Aug+Sep safe=short | +0.71 |
| NONE | G3 | 4 | 1 | -0.82 | G3 avoid Jun+Aug+Sep safe=short | +0.72 |
| NONE | G4 | 18 | 0 | -8.82 | G4 TOM last4+first5 safe=cash | -3.95 |
| NONE | G5 | 14 | 0 | -8.72 | G5 avoid last3 days of quarter safe=short | -0.70 |
| NONE | G6 | 10 | 2 | -4.82 | G6 pres off midterm Jan-Sep only safe=long | +0.86 |
| NONE | G7 | 8 | 4 | -0.55 | G7 barometer santa bearish->short until yearend | +1.30 |
| NONE | G8 | 20 | 4 | -1.07 | G8 harding Oct1/May1 macd12-26-9 safe=long | +2.37 |
| NONE | G9 | 10 | 0 | -2.21 | G9 Halloween, summer in if >SMA200 safe=short | -0.93 |
| NONE | G10 | 13 | 9 | +0.32 | G10 LEV SSO Nov-Apr / SPY May-Oct | +4.46 |
| NONE | G11 | 11 | 6 | +0.06 | G11 small Dec15-Mar1 else SPY | +0.60 |
| NONE | G12 | 5 | 4 | +0.19 | G12 cyclicals Nov-Apr / defensives May-Oct | +1.60 |
| NONE | G13 | 22 | 0 | -2.35 | G13 samemonth sectors(Fid proxies) yrs=all top1 | -0.01 |
| NONE | G14 | 16 | 1 | -1.02 | G14 learned VFINX yrs=all thr=zero safe=short | +0.36 |
| NONE | G15 | 6 | 0 | -0.37 | G15 pension last8 eq-bond>0.05 -> short | -0.01 |
| NONE | G16 | 4 | 0 | -3.82 | G16 Halloween + whole pre-election year safe=short | -1.88 |
| NONE | G17 | 3 | 0 | -2.07 | G17 Halloween short TAX no-ST-gains gb=1.0 | -2.07 |
| NONE | G18 | 2 | 0 | -3.42 | G18 Halloween VGTSX / short | -2.68 |
| NONE | G19 | 148 | 93 | +0.21 | G19 XLB only Nov-Apr / SPY May-Oct | +1.70 |
| NONE | G21 | 48 | 11 | -0.72 | G21 rand03 EWO+IEV+SOXX+XLE Nov-Apr / SPY | +1.12 |
| CA | G1 | 61 | 0 | -3.53 | G1 win Oct1-May15 safe=long | -1.17 |
| CA | G2 | 37 | 0 | -3.93 | G2 avoid Aug+Sep safe=short | -2.11 |
| CA | G3 | 4 | 0 | -2.97 | G3 avoid Jun+Aug+Sep safe=short | -2.08 |
| CA | G4 | 18 | 0 | -7.54 | G4 TOM last4+first5 safe=cash | -4.66 |
| CA | G5 | 14 | 0 | -7.21 | G5 avoid last3 days of quarter safe=short | -3.04 |
| CA | G6 | 10 | 0 | -4.34 | G6 pres off midterm Jan-Sep only safe=long | -0.30 |
| CA | G7 | 8 | 4 | -1.13 | G7 barometer santa bearish->short until yearend | +0.70 |
| CA | G8 | 20 | 0 | -3.18 | G8 harding Oct1/May1 macd12-26-9 safe=long | -1.14 |
| CA | G9 | 10 | 0 | -2.73 | G9 Halloween, summer in if >SMA200 safe=short | -1.56 |
| CA | G10 | 13 | 2 | -1.22 | G10 LEV control const 50SSO+50SPY (1.5x) | +2.85 |
| CA | G11 | 11 | 0 | -2.70 | G11 small Dec15-Mar1 else SPY | -2.34 |
| CA | G12 | 5 | 0 | -2.50 | G12 cyclicals Nov-Apr / defensives May-Oct | -1.67 |
| CA | G13 | 22 | 0 | -4.03 | G13 samemonth sectors(Fid proxies) yrs=all top1 | -2.80 |
| CA | G14 | 16 | 0 | -3.10 | G14 learned VFINX yrs=all thr=zero safe=short | -2.33 |
| CA | G15 | 6 | 0 | -2.85 | G15 pension last8 eq-bond>0.05 -> short | -2.52 |
| CA | G16 | 4 | 0 | -4.65 | G16 Halloween + whole pre-election year safe=short | -2.86 |
| CA | G17 | 3 | 0 | -1.53 | G17 Halloween short TAX gb=0.01 | -0.27 |
| CA | G18 | 2 | 0 | -4.53 | G18 Halloween VGTSX / short | -3.97 |
| CA | G19 | 67 | 6 | -2.49 | G19 control cyclicals(4) all year | +0.87 |
| CA | G22 | 35 | 19 | +0.04 | G22 buyhold cyclicals(4) never rebalanced | +1.13 |


#### Long history (1986-2026), `long_screen`

| regime | group | n | n_pos | median | best | best_score |
|---|---|---|---|---|---|---|
| NONE | G1 | 61 | 31 | +0.00 | G1 win Oct1-May15 safe=long | +3.94 |
| NONE | G2 | 37 | 3 | -1.68 | G2 avoid Aug+Sep safe=short | +1.63 |
| NONE | G3 | 4 | 4 | +0.77 | G3 avoid Jun+Aug+Sep safe=short | +1.46 |
| NONE | G4 | 18 | 0 | -8.36 | G4 TOM last4+first5 safe=cash | -4.39 |
| NONE | G5 | 14 | 0 | -9.21 | G5 avoid last3 days of quarter safe=short | -0.50 |
| NONE | G6 | 10 | 2 | -2.04 | G6 pres off midterm Jan-Sep only safe=long | +1.68 |
| NONE | G7 | 8 | 4 | -0.26 | G7 barometer santa bearish->short until yearend | +0.69 |
| NONE | G8 | 20 | 12 | +0.32 | G8 harding Oct1/May1 macd12-26-9 safe=long | +3.15 |
| NONE | G9 | 10 | 3 | -0.98 | G9 Halloween AND >SMA200 safe=long | +0.87 |
| NONE | G11 | 10 | 10 | +0.95 | G11 small Dec15-Mar1 else VFINX | +1.94 |
| NONE | G12 | 5 | 5 | +1.84 | G12 cyclicals Nov-Apr / defensives May-Oct | +4.52 |
| NONE | G13 | 9 | 7 | +1.39 | G13 samemonth Fid sectors yrs=all top1 | +3.91 |
| NONE | G14 | 16 | 0 | -1.90 | G14 learned VFINX yrs=all thr=zero safe=short | -0.05 |
| NONE | G15 | 6 | 2 | -0.23 | G15 pension last8 eq-bond>0.0 -> short | +0.03 |
| NONE | G16 | 4 | 0 | -2.89 | G16 Halloween + whole pre-election year safe=short | -0.34 |
| NONE | G17 | 3 | 0 | -1.04 | G17 Halloween short TAX gb=0.05 | -1.04 |
| NONE | G18 | 3 | 2 | +0.91 | G18 Halloween NAESX(small) / short | +0.91 |
| NONE | G19 | 133 | 126 | +1.13 | G19 FSRPX+FSDAX+FSDPX Nov-Apr / VFINX TAX gb=0.01 | +2.86 |
| NONE | G22 | 1 | 1 | +2.91 | G22 buyhold cyclicals(4 Fid) never rebalanced | +2.91 |
| CA | G1 | 61 | 0 | -2.80 | G1 win Oct1-May15 safe=long | -0.57 |
| CA | G2 | 37 | 0 | -3.85 | G2 avoid Aug+Sep safe=short | -1.87 |
| CA | G3 | 4 | 0 | -2.37 | G3 avoid Jun+Aug+Sep safe=short | -1.93 |
| CA | G4 | 18 | 0 | -7.56 | G4 TOM last4+first5 safe=cash | -5.23 |
| CA | G5 | 14 | 0 | -8.13 | G5 avoid last3 days of quarter safe=short | -3.32 |
| CA | G6 | 10 | 2 | -2.24 | G6 pres off midterm Jan-Sep only safe=long | +0.27 |
| CA | G7 | 8 | 1 | -0.83 | G7 barometer santa bearish->short until yearend | +0.04 |
| CA | G8 | 20 | 0 | -2.56 | G8 harding Oct1/May1 macd12-26-9 safe=long | -0.96 |
| CA | G9 | 10 | 0 | -2.15 | G9 Halloween, summer in if >SMA200 safe=short | -0.94 |
| CA | G11 | 10 | 0 | -2.45 | G11 small Dec15-Mar1 else VFINX | -1.88 |
| CA | G12 | 5 | 0 | -1.87 | G12 cyclicals Nov-Apr / defensives May-Oct | -0.33 |
| CA | G13 | 9 | 0 | -2.42 | G13 samemonth Fid sectors yrs=all top1 | -1.51 |
| CA | G14 | 16 | 0 | -3.92 | G14 learned VFINX yrs=all thr=zero safe=short | -2.58 |
| CA | G15 | 6 | 0 | -3.08 | G15 pension last8 eq-bond>0.05 -> short | -2.89 |
| CA | G16 | 4 | 0 | -4.40 | G16 Halloween + whole pre-election year safe=short | -1.85 |
| CA | G17 | 3 | 0 | -1.57 | G17 Halloween short TAX gb=0.01 | -0.22 |
| CA | G18 | 3 | 0 | -2.29 | G18 Halloween NAESX(small) / short | -2.29 |
| CA | G19 | 8 | 5 | +1.14 | G19 control cyclicals(4 Fid) all year | +2.09 |
| CA | G22 | 1 | 1 | +2.47 | G22 buyhold cyclicals(4 Fid) never rebalanced | +2.47 |


### ETF era (2000-2026), screen: best and worst of the pre-registered grid

#### screen, CA: top 15 of G1-G18

| label | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | trades |
|---|---|---|---|---|---|---|---|
| G10 LEV control const 50SSO+50SPY (1.5x) | +2.85 | +1.60 | 1.00 | 1.00 | 0.229 | -73 | 470 |
| G10 LEV control const 25SSO+75SPY (1.25x) | +1.40 | +0.75 | 1.00 | 1.00 | 0.230 | -65 | 470 |
| G7 barometer santa bearish->short until yearend | +0.70 | -0.52 | 0.53 | 0.75 | 0.620 | -43 | 33 |
| G7 barometer santa bearish->short until Nov1 | +0.69 | -0.79 | 0.53 | 0.75 | 0.684 | -45 | 31 |
| G7 barometer first5 bearish->short until Nov1 | +0.26 | +0.43 | 0.53 | 0.33 | 0.439 | -39 | 37 |
| G7 barometer first5 bearish->short until yearend | +0.21 | +0.44 | 0.53 | 0.67 | 0.456 | -35 | 37 |
| G17 Halloween short TAX gb=0.01 | -0.27 | +0.29 | 0.29 | 0.42 | 0.470 | -34 | 70 |
| G6 pres off midterm Jan-Sep only safe=long | -0.30 | -0.30 | 0.53 | 0.25 | 0.597 | -55 | 27 |
| G6 pres off midterm Jan-Sep only safe=short | -0.51 | -0.10 | 0.24 | 0.25 | 0.569 | -56 | 27 |
| G10 LEV core75 SPY + sat SSO Nov-Apr / short | -0.68 | -0.80 | 0.20 | 0.00 | 0.904 | -58 | 80 |
| G10 core75 SPY + sat VFINX Nov-Apr / short (no lev) | -0.74 | -0.66 | 0.18 | 0.08 | 0.844 | -51 | 108 |
| G10 LEV 50SSO+50SPY Nov-Apr / SPY May-Oct | -0.76 | -1.29 | 0.30 | 0.00 | 0.830 | -68 | 80 |
| G8 harding Oct1/May1 macd12-26-9 safe=long | -1.14 | -1.42 | 0.53 | 0.25 | 0.692 | -39 | 107 |
| G1 win Oct1-May15 safe=long | -1.17 | -1.11 | 0.53 | 0.25 | 0.672 | -49 | 107 |
| G10 LEV SSO Nov-Apr / SPY May-Oct | -1.19 | -2.31 | 0.20 | 0.00 | 0.789 | -77 | 79 |


#### screen, CA: bottom 8

| label | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | trades |
|---|---|---|---|---|---|---|---|
| G4 TOM last2+first5 safe=short | -9.08 | -7.98 | 0.00 | 0.00 | 0.999 | -49 | 1273 |
| G5 avoid Mondays safe=cash | -9.26 | -10.37 | 0.00 | 0.00 | 1.000 | -77 | 2497 |
| G4 TOM last2+first2 safe=short | -9.61 | -8.74 | 0.00 | 0.00 | 0.996 | -44 | 1273 |
| G4 TOM last1+first5 safe=short | -9.72 | -8.96 | 0.00 | 0.00 | 1.000 | -52 | 1273 |
| G4 TOM last1+first3 safe=short | -9.79 | -9.37 | 0.00 | 0.00 | 1.000 | -52 | 1273 |
| G5 first-half (d-1..+8) safe=short | -10.04 | -9.28 | 0.00 | 0.00 | 1.000 | -68 | 1273 |
| G4 TOM last1+first2 safe=short | -10.31 | -9.62 | 0.00 | 0.00 | 0.998 | -54 | 1273 |
| G5 avoid Mondays safe=short | -17.13 | -18.87 | 0.00 | 0.00 | 1.000 | -97 | 4993 |


#### screen, NONE: top 15 of G1-G18

| label | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | trades |
|---|---|---|---|---|---|---|---|
| G10 LEV SSO Nov-Apr / SPY May-Oct | +4.46 | +2.49 | 1.00 | 1.00 | 0.191 | -75 | 79 |
| G10 LEV control const 50SSO+50SPY (1.5x) | +3.77 | +2.40 | 1.00 | 1.00 | 0.157 | -73 | 470 |
| G10 LEV UPRO Nov-Apr / short May-Oct | +3.00 | +2.85 | 0.57 | 1.00 | 0.319 | -77 | 67 |
| G10 LEV SSO Nov-Apr / 50SPY+50short May-Oct | +2.49 | +0.87 | 0.80 | 1.00 | 0.372 | -70 | 118 |
| G1 win Oct1-May15 safe=long | +2.43 | +2.78 | 0.71 | 0.75 | 0.178 | -45 | 107 |
| G10 LEV 50SSO+50SPY Nov-Apr / SPY May-Oct | +2.38 | +1.43 | 1.00 | 1.00 | 0.154 | -66 | 80 |
| G8 harding Oct1/May1 macd12-26-9 safe=long | +2.37 | +2.14 | 0.71 | 0.75 | 0.259 | -34 | 107 |
| G1 win Oct1-May1 safe=long | +2.29 | +1.92 | 0.71 | 0.83 | 0.277 | -46 | 107 |
| G8 harding Oct1/Apr20 macd12-26-9 safe=long | +2.03 | +1.50 | 0.71 | 0.75 | 0.330 | -34 | 107 |
| G1 win Oct1-Jun1 safe=long | +1.97 | +2.41 | 0.65 | 0.75 | 0.205 | -44 | 107 |
| G10 LEV control const 25SSO+75SPY (1.25x) | +1.97 | +1.31 | 1.00 | 1.00 | 0.132 | -65 | 470 |
| G8 harding Oct1/Apr1 macd12-26-9 safe=long | +1.70 | +0.64 | 0.71 | 0.75 | 0.429 | -38 | 107 |
| G12 cyclicals Nov-Apr / defensives May-Oct | +1.60 | +0.83 | 0.71 | 0.83 | 0.314 | -47 | 375 |
| G7 barometer santa bearish->short until yearend | +1.30 | +0.20 | 0.53 | 0.75 | 0.495 | -42 | 33 |
| G7 barometer santa bearish->short until Nov1 | +1.25 | -0.13 | 0.53 | 0.75 | 0.550 | -44 | 31 |


#### screen, NONE: bottom 8

| label | score | full_excess | ex10_beat | ex15_beat | boot_p | max_dd | trades |
|---|---|---|---|---|---|---|---|
| G4 TOM last2+first5 safe=short | -10.38 | -8.96 | 0.00 | 0.00 | 1.000 | -47 | 1273 |
| G4 TOM last2+first3 safe=short | -10.70 | -9.42 | 0.00 | 0.00 | 0.999 | -40 | 1273 |
| G4 TOM last1+first5 safe=short | -11.22 | -9.90 | 0.00 | 0.00 | 1.000 | -49 | 1273 |
| G4 TOM last2+first2 safe=short | -11.30 | -9.75 | 0.00 | 0.00 | 0.998 | -44 | 1273 |
| G5 first-half (d-1..+8) safe=short | -11.33 | -10.44 | 0.00 | 0.00 | 1.000 | -68 | 1273 |
| G4 TOM last1+first3 safe=short | -11.51 | -10.35 | 0.00 | 0.00 | 0.999 | -52 | 1273 |
| G4 TOM last1+first2 safe=short | -12.11 | -10.69 | 0.00 | 0.00 | 0.998 | -54 | 1273 |
| G5 avoid Mondays safe=short | -18.96 | -20.02 | 0.00 | 0.00 | 1.000 | -97 | 4993 |


### Long history (1986-2026, VFINX benchmark), long_screen: best

#### long_screen NONE: top 15 (G1-G19, baskets excluded)

| config | score | full_excess | ex10_beat | ex15_beat | ex20_beat | ho5_mean | ho5_beat | boot_p | max_dd |
|---|---|---|---|---|---|---|---|---|---|
| G12 cyclicals Nov-Apr / defensives May-Oct | +4.52 | +3.84 | 0.84 | 0.92 | 1.00 | +6.53 | 0.90 | 0.014 | -52 |
| G1 win Oct1-May15 safe=long | +3.94 | +2.26 | 0.77 | 0.88 | 0.95 | +1.11 | 0.60 | 0.133 | -45 |
| G13 samemonth Fid sectors yrs=all top1 | +3.91 | +2.71 | 0.81 | 0.92 | 0.95 | +6.27 | 0.80 | 0.178 | -66 |
| G1 win Oct1-Jun1 safe=long | +3.48 | +2.15 | 0.81 | 0.88 | 0.90 | +1.95 | 0.80 | 0.123 | -45 |
| G1 win Oct1-May1 safe=long | +3.32 | +1.19 | 0.74 | 0.92 | 0.95 | +0.10 | 0.50 | 0.283 | -46 |
| G8 harding Oct1/May1 macd12-26-9 safe=long | +3.15 | +1.14 | 0.74 | 0.85 | 0.95 | -0.59 | 0.40 | 0.320 | -38 |
| G8 harding Oct1/Apr20 macd12-26-9 safe=long | +2.92 | +0.70 | 0.74 | 0.85 | 0.90 | -0.29 | 0.40 | 0.392 | -39 |
| G19 FSRPX+FSDAX+FSDPX Nov-Apr / VFINX TAX gb=0.01 | +2.86 | +2.79 | 0.97 | 1.00 | 1.00 | +1.22 | 0.70 | 0.006 | -53 |
| G19 FSRPX+FSDAX+FSDPX (no tech) Nov-Apr / VFINX | +2.86 | +2.78 | 0.97 | 1.00 | 1.00 | +1.30 | 0.70 | 0.006 | -53 |
| G19 control cyclicals(4 Fid) all year | +2.71 | +1.74 | 0.87 | 0.92 | 1.00 | -0.40 | 0.40 | 0.105 | -58 |
| G12 cyclicals Nov-Apr / VFINX May-Oct | +2.70 | +2.78 | 1.00 | 1.00 | 1.00 | +2.41 | 0.80 | 0.008 | -55 |
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +2.70 | +2.78 | 1.00 | 1.00 | 1.00 | +2.36 | 0.80 | 0.008 | -54 |
| G1 win Oct15-May15 safe=long | +2.69 | +1.24 | 0.77 | 0.88 | 0.81 | +1.91 | 0.70 | 0.275 | -39 |
| G1 win Oct1-Jul1 safe=long | +2.56 | +1.37 | 0.71 | 0.88 | 0.81 | +0.18 | 0.50 | 0.219 | -50 |
| G8 harding Oct1/Apr1 macd12-26-9 safe=long | +2.45 | -0.45 | 0.71 | 0.85 | 0.81 | -1.84 | 0.40 | 0.574 | -40 |


#### long_screen CA: top 15 (G1-G19, baskets excluded)

| config | score | full_excess | ex10_beat | ex15_beat | ex20_beat | ho5_mean | ho5_beat | boot_p | max_dd |
|---|---|---|---|---|---|---|---|---|---|
| G19 control cyclicals(4 Fid) all year | +2.09 | +0.67 | 0.87 | 0.88 | 1.00 | -0.44 | 0.40 | 0.290 | -58 |
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +1.48 | +0.93 | 0.74 | 0.88 | 0.95 | +0.98 | 0.50 | 0.135 | -56 |
| G19 control FSRPX+FSDAX+FSDPX all year | +1.41 | -0.14 | 0.58 | 0.85 | 1.00 | -2.24 | 0.40 | 0.555 | -57 |
| G19 control equal-weight 9 Fid sectors all year | +1.24 | -0.02 | 0.74 | 0.85 | 0.95 | +0.18 | 0.50 | 0.512 | -56 |
| G19 FSRPX+FSDAX+FSDPX Nov-Apr / VFINX TAX gb=0.01 | +1.04 | +0.31 | 0.65 | 0.88 | 0.90 | -0.54 | 0.50 | 0.341 | -54 |
| G6 pres off midterm Jan-Sep only safe=long | +0.27 | -1.50 | 0.52 | 0.58 | 0.81 | -0.88 | 0.40 | 0.841 | -56 |
| G6 pres off midterm Jan-Sep only safe=short | +0.21 | -1.18 | 0.42 | 0.58 | 0.71 | +0.29 | 0.50 | 0.818 | -56 |
| G7 barometer santa bearish->short until yearend | +0.04 | -2.13 | 0.48 | 0.58 | 0.76 | -2.69 | 0.00 | 0.902 | -62 |
| G7 barometer santa bearish->short until Nov1 | -0.21 | -2.40 | 0.32 | 0.58 | 0.76 | -2.37 | 0.00 | 0.938 | -66 |
| G17 Halloween short TAX gb=0.01 | -0.22 | -0.04 | 0.23 | 0.27 | 0.19 | -0.63 | 0.10 | 0.931 | -55 |
| G7 barometer first5 bearish->short until Nov1 | -0.23 | -2.18 | 0.55 | 0.42 | 0.71 | -3.79 | 0.00 | 0.924 | -39 |
| G12 cyclicals Nov-Apr / defensives May-Oct | -0.33 | -2.09 | 0.52 | 0.50 | 0.57 | -0.44 | 0.50 | 0.905 | -56 |
| G1 win Oct1-May15 safe=long | -0.57 | -2.95 | 0.52 | 0.58 | 0.62 | -3.36 | 0.10 | 0.911 | -49 |
| G7 barometer first5 bearish->short until yearend | -0.59 | -2.42 | 0.39 | 0.54 | 0.71 | -4.63 | 0.00 | 0.918 | -37 |
| G1 win Oct1-Jun1 safe=long | -0.79 | -2.99 | 0.48 | 0.50 | 0.62 | -2.84 | 0.20 | 0.921 | -50 |


## Finalists on the full protocol (95 quarterly starts, 2000-2026)

Figures are pp/yr, except beat rates, boot_p and trades. `max_dd` is that of the first start
(2000-01), and SPY's is -55%.

#### full, CA (23 configs)

| label | score | full_excess | ex5_mean | ex10_mean | ex10_beat | ex10_min | ex15_beat | ex20_beat | boot_p | max_dd | bench_max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G10 LEV control const 50SSO+50SPY (1.5x) | +2.77 | +1.67 | +2.72 | +2.97 | 1.00 | +0.47 | 1.00 | 1.00 | 0.174 | -73 | -55 | 482 | 0.12 |
| G22 buyhold cyclicals(4) never rebalanced | +1.21 | +0.46 | +1.08 | +1.27 | 1.00 | +0.53 | 1.00 | 1.00 | 0.287 | -58 | -55 | 4 | 0.00 |
| G19 control cyclicals(4) all year | +0.93 | +0.63 | +0.87 | +0.98 | 0.97 | -0.04 | 0.91 | 1.00 | 0.187 | -56 | -55 | 216 | 0.05 |
| G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 | +0.85 | +1.44 | +0.76 | +0.94 | 0.91 | -0.85 | 0.94 | 0.96 | 0.035 | -57 | -55 | 416 | 0.08 |
| G7 barometer santa bearish->short until yearend | +0.67 | -0.52 | +0.58 | +0.81 | 0.54 | -5.00 | 0.77 | 0.70 | 0.620 | -43 | -55 | 33 | 0.76 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.01 | +0.64 | +1.18 | +0.50 | +0.71 | 0.84 | -0.79 | 0.91 | 1.00 | 0.025 | -57 | -55 | 423 | 0.10 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.01 | +0.46 | +0.59 | +0.20 | +0.51 | 0.66 | -2.26 | 0.83 | 0.96 | 0.304 | -57 | -55 | 325 | 0.10 |
| G22 buyhold XLY+XLI+XLB never rebalanced | +0.46 | +0.49 | +0.44 | +0.46 | 0.61 | -2.37 | 0.74 | 0.56 | 0.350 | -59 | -55 | 3 | 0.00 |
| G19 control XLY+XLI+XLB all year | +0.36 | +0.42 | +0.39 | +0.36 | 0.60 | -2.41 | 0.66 | 0.56 | 0.379 | -59 | -55 | 162 | 0.04 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.05 | +0.13 | +0.41 | -0.17 | +0.21 | 0.58 | -1.64 | 0.77 | 0.70 | 0.268 | -55 | -55 | 521 | 0.43 |
| G1 win Oct1-May15 safe=long | -1.32 | -1.11 | -1.36 | -1.25 | 0.51 | -7.59 | 0.23 | 0.26 | 0.672 | -49 | -55 | 107 | 2.05 |
| G10 LEV SSO Nov-Apr / SPY May-Oct | -1.33 | -2.47 | -1.02 | -1.34 | 0.27 | -4.02 | 0.00 | 0.00 | 0.772 | -78 | -55 | 81 | 2.07 |
| G12 cyclicals Nov-Apr / defensives May-Oct | -1.80 | -2.24 | -1.91 | -1.62 | 0.43 | -6.87 | 0.15 | 0.11 | 0.888 | -50 | -55 | 375 | 2.05 |
| G19 XLY+XLI+XLB (no XLK) Nov-Apr / SPY May-Oct | -1.90 | -1.70 | -1.86 | -1.79 | 0.15 | -4.96 | 0.11 | 0.00 | 0.876 | -59 | -55 | 215 | 2.06 |
| G19 cyclicals Oct1-May1 / SPY | -1.93 | -1.91 | -1.86 | -1.85 | 0.15 | -4.62 | 0.09 | 0.00 | 0.937 | -60 | -55 | 269 | 2.04 |
| G19 cyclicals Nov1-Jun1 / SPY | -2.14 | -2.15 | -2.11 | -2.03 | 0.12 | -4.58 | 0.04 | 0.00 | 0.974 | -58 | -55 | 269 | 2.07 |
| G12 cyclicals Nov-Apr / SPY May-Oct | -2.17 | -2.17 | -2.15 | -2.06 | 0.10 | -4.73 | 0.00 | 0.00 | 0.982 | -58 | -55 | 269 | 2.05 |
| G2 avoid Aug+Sep safe=short | -2.19 | -1.81 | -1.99 | -2.22 | 0.10 | -5.24 | 0.04 | 0.00 | 0.890 | -55 | -55 | 105 | 2.00 |
| G11 small Dec15-Mar1 else SPY | -2.52 | -2.01 | -2.41 | -2.48 | 0.06 | -5.35 | 0.02 | 0.00 | 0.956 | -56 | -55 | 107 | 2.06 |
| G11 small Dec15-Jan15 else SPY | -2.53 | -2.42 | -2.46 | -2.47 | 0.00 | -4.68 | 0.00 | 0.00 | 1.000 | -57 | -55 | 107 | 2.07 |
| G1 win Nov1-May1 safe=long | -3.04 | -3.18 | -3.19 | -2.88 | 0.33 | -10.95 | 0.15 | 0.11 | 0.857 | -45 | -55 | 107 | 2.04 |
| G1 win Nov1-May1 safe=short | -3.80 | -3.64 | -3.62 | -3.75 | 0.15 | -9.27 | 0.09 | 0.00 | 0.921 | -39 | -55 | 107 | 2.04 |
| G8 harding Oct16/Apr20 macd12-26-9 safe=short | -3.83 | -3.74 | -3.64 | -3.81 | 0.15 | -9.86 | 0.09 | 0.00 | 0.911 | -38 | -55 | 107 | 2.03 |


#### full, FED (23 configs)

| label | score | full_excess | ex5_mean | ex10_mean | ex10_beat | ex10_min | ex15_beat | ex20_beat | boot_p | max_dd | bench_max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G10 LEV control const 50SSO+50SPY (1.5x) | +3.18 | +2.09 | +3.12 | +3.37 | 1.00 | +0.53 | 1.00 | 1.00 | 0.142 | -73 | -55 | 482 | 0.11 |
| G22 buyhold cyclicals(4) never rebalanced | +1.32 | +0.48 | +1.21 | +1.39 | 1.00 | +0.56 | 1.00 | 1.00 | 0.294 | -58 | -55 | 4 | 0.00 |
| G19 control cyclicals(4) all year | +1.06 | +0.73 | +1.00 | +1.12 | 1.00 | +0.03 | 0.96 | 1.00 | 0.161 | -56 | -55 | 216 | 0.05 |
| G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 | +0.96 | +1.49 | +0.88 | +1.06 | 0.93 | -0.86 | 0.98 | 1.00 | 0.027 | -57 | -55 | 416 | 0.08 |
| G7 barometer santa bearish->short until yearend | +0.90 | -0.25 | +0.71 | +1.04 | 0.54 | -5.32 | 0.77 | 0.81 | 0.574 | -43 | -55 | 33 | 0.78 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.01 | +0.73 | +1.22 | +0.58 | +0.81 | 0.85 | -0.76 | 0.94 | 1.00 | 0.027 | -57 | -55 | 427 | 0.10 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.01 | +0.54 | +0.63 | +0.25 | +0.60 | 0.67 | -2.35 | 0.83 | 0.96 | 0.303 | -57 | -55 | 325 | 0.10 |
| G22 buyhold XLY+XLI+XLB never rebalanced | +0.51 | +0.51 | +0.49 | +0.52 | 0.61 | -2.53 | 0.74 | 0.56 | 0.351 | -59 | -55 | 3 | 0.00 |
| G19 control XLY+XLI+XLB all year | +0.45 | +0.54 | +0.45 | +0.46 | 0.60 | -2.51 | 0.66 | 0.59 | 0.347 | -59 | -55 | 162 | 0.04 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.05 | +0.35 | +0.72 | -0.02 | +0.45 | 0.64 | -1.10 | 0.81 | 1.00 | 0.108 | -55 | -55 | 537 | 0.41 |
| G10 LEV SSO Nov-Apr / SPY May-Oct | -0.23 | -1.44 | -0.06 | -0.26 | 0.51 | -3.08 | 0.24 | 0.00 | 0.673 | -77 | -55 | 81 | 2.05 |
| G1 win Oct1-May15 safe=long | -0.71 | -0.27 | -0.89 | -0.64 | 0.54 | -7.70 | 0.26 | 0.30 | 0.545 | -48 | -55 | 107 | 2.04 |
| G12 cyclicals Nov-Apr / defensives May-Oct | -1.27 | -1.64 | -1.54 | -1.07 | 0.51 | -6.79 | 0.21 | 0.15 | 0.804 | -49 | -55 | 375 | 2.04 |
| G19 XLY+XLI+XLB (no XLK) Nov-Apr / SPY May-Oct | -1.36 | -0.98 | -1.42 | -1.26 | 0.25 | -4.22 | 0.17 | 0.15 | 0.777 | -58 | -55 | 215 | 2.04 |
| G19 cyclicals Oct1-May1 / SPY | -1.45 | -1.26 | -1.47 | -1.37 | 0.16 | -3.94 | 0.15 | 0.04 | 0.867 | -59 | -55 | 269 | 2.03 |
| G19 cyclicals Nov1-Jun1 / SPY | -1.67 | -1.54 | -1.73 | -1.56 | 0.13 | -3.82 | 0.09 | 0.00 | 0.929 | -57 | -55 | 269 | 2.06 |
| G12 cyclicals Nov-Apr / SPY May-Oct | -1.69 | -1.56 | -1.77 | -1.58 | 0.12 | -3.93 | 0.06 | 0.00 | 0.938 | -57 | -55 | 269 | 2.04 |
| G2 avoid Aug+Sep safe=short | -1.78 | -1.16 | -1.64 | -1.83 | 0.15 | -4.65 | 0.15 | 0.00 | 0.805 | -54 | -55 | 105 | 1.98 |
| G11 small Dec15-Mar1 else SPY | -2.10 | -1.34 | -2.05 | -2.08 | 0.07 | -4.87 | 0.06 | 0.00 | 0.880 | -56 | -55 | 107 | 2.05 |
| G11 small Dec15-Jan15 else SPY | -2.12 | -1.86 | -2.13 | -2.07 | 0.01 | -4.10 | 0.00 | 0.00 | 0.999 | -56 | -55 | 107 | 2.05 |
| G1 win Nov1-May1 safe=long | -2.70 | -2.71 | -3.00 | -2.53 | 0.46 | -11.45 | 0.21 | 0.15 | 0.807 | -43 | -55 | 107 | 2.03 |
| G1 win Nov1-May1 safe=short | -3.76 | -3.36 | -3.71 | -3.71 | 0.16 | -9.54 | 0.11 | 0.00 | 0.906 | -38 | -55 | 107 | 2.03 |
| G8 harding Oct16/Apr20 macd12-26-9 safe=short | -3.80 | -3.48 | -3.74 | -3.78 | 0.15 | -10.27 | 0.11 | 0.00 | 0.889 | -36 | -55 | 107 | 2.02 |


#### full, NONE (23 configs)

| label | score | full_excess | ex5_mean | ex10_mean | ex10_beat | ex10_min | ex15_beat | ex20_beat | boot_p | max_dd | bench_max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G10 LEV SSO Nov-Apr / SPY May-Oct | +4.32 | +2.54 | +4.40 | +4.25 | 1.00 | +1.57 | 1.00 | 1.00 | 0.162 | -75 | -55 | 81 | 2.00 |
| G10 LEV control const 50SSO+50SPY (1.5x) | +3.68 | +2.56 | +3.65 | +3.85 | 1.00 | +0.59 | 1.00 | 1.00 | 0.117 | -73 | -55 | 482 | 0.11 |
| G1 win Oct1-May15 safe=long | +2.26 | +2.78 | +1.92 | +2.31 | 0.70 | -5.82 | 0.74 | 0.96 | 0.178 | -45 | -55 | 107 | 2.00 |
| G12 cyclicals Nov-Apr / defensives May-Oct | +1.54 | +0.83 | +1.03 | +1.78 | 0.70 | -4.39 | 0.83 | 1.00 | 0.314 | -47 | -55 | 375 | 2.01 |
| G19 XLY+XLI+XLB (no XLK) Nov-Apr / SPY May-Oct | +1.46 | +1.81 | +1.34 | +1.55 | 0.78 | -0.53 | 0.89 | 1.00 | 0.035 | -56 | -55 | 215 | 2.00 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.01 | +1.46 | +1.81 | +1.33 | +1.54 | 0.78 | -0.53 | 0.89 | 1.00 | 0.034 | -56 | -55 | 691 | 2.05 |
| G22 buyhold cyclicals(4) never rebalanced | +1.42 | +0.49 | +1.35 | +1.50 | 1.00 | +0.60 | 1.00 | 1.00 | 0.301 | -58 | -55 | 4 | 0.00 |
| G7 barometer santa bearish->short until yearend | +1.26 | +0.20 | +1.02 | +1.41 | 0.54 | -5.45 | 0.77 | 0.96 | 0.495 | -42 | -55 | 33 | 0.80 |
| G19 control cyclicals(4) all year | +1.22 | +0.84 | +1.16 | +1.28 | 1.00 | +0.11 | 0.98 | 1.00 | 0.133 | -56 | -55 | 216 | 0.04 |
| G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 | +1.22 | +1.31 | +1.15 | +1.26 | 0.90 | -0.32 | 0.96 | 1.00 | 0.042 | -56 | -55 | 1009 | 2.06 |
| G19 cyclicals Oct1-May1 / SPY | +1.21 | +1.31 | +1.15 | +1.26 | 0.91 | -0.35 | 0.96 | 1.00 | 0.048 | -56 | -55 | 269 | 1.99 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.01 | +0.98 | +0.96 | +0.85 | +1.07 | 1.00 | +0.05 | 0.94 | 1.00 | 0.070 | -55 | -55 | 903 | 2.06 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.05 | +0.98 | +0.96 | +0.85 | +1.07 | 1.00 | +0.05 | 0.94 | 1.00 | 0.070 | -55 | -55 | 903 | 2.06 |
| G12 cyclicals Nov-Apr / SPY May-Oct | +0.98 | +0.94 | +0.85 | +1.06 | 1.00 | +0.05 | 0.94 | 1.00 | 0.071 | -55 | -55 | 269 | 2.00 |
| G19 cyclicals Nov1-Jun1 / SPY | +0.97 | +0.91 | +0.87 | +1.04 | 0.94 | -0.23 | 0.91 | 1.00 | 0.080 | -54 | -55 | 269 | 2.02 |
| G2 avoid Aug+Sep safe=short | +0.68 | +1.34 | +0.84 | +0.56 | 0.70 | -1.00 | 0.57 | 1.00 | 0.147 | -52 | -55 | 105 | 1.91 |
| G22 buyhold XLY+XLI+XLB never rebalanced | +0.57 | +0.52 | +0.55 | +0.59 | 0.61 | -2.69 | 0.74 | 0.56 | 0.357 | -59 | -55 | 3 | 0.00 |
| G19 control XLY+XLI+XLB all year | +0.56 | +0.69 | +0.54 | +0.57 | 0.60 | -2.57 | 0.68 | 0.67 | 0.321 | -59 | -55 | 162 | 0.04 |
| G11 small Dec15-Mar1 else SPY | +0.47 | +1.35 | +0.53 | +0.43 | 0.72 | -1.44 | 0.87 | 1.00 | 0.119 | -55 | -55 | 107 | 2.02 |
| G11 small Dec15-Jan15 else SPY | +0.41 | +0.48 | +0.40 | +0.39 | 0.82 | -0.47 | 0.85 | 1.00 | 0.207 | -56 | -55 | 107 | 2.02 |
| G1 win Nov1-May1 safe=long | -0.42 | -0.62 | -0.90 | -0.24 | 0.57 | -10.77 | 0.64 | 0.41 | 0.567 | -38 | -55 | 107 | 2.00 |
| G1 win Nov1-May1 safe=short | -2.22 | -1.71 | -2.31 | -2.17 | 0.39 | -8.53 | 0.19 | 0.11 | 0.760 | -35 | -55 | 107 | 2.01 |
| G8 harding Oct16/Apr20 macd12-26-9 safe=short | -2.29 | -1.90 | -2.38 | -2.28 | 0.24 | -9.25 | 0.21 | 0.11 | 0.759 | -34 | -55 | 107 | 2.00 |


## Long-history twins on the long protocol (151 quarterly starts 1986-2026; ho = windows ending before 2000)

#### long, CA (8 configs)

| label | score | full_excess | ex10_beat | ex15_beat | ex20_beat | ho5_mean | ho5_beat | ho10_mean | boot_p | max_dd | bench_max_dd | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G22 buyhold cyclicals(4 Fid) never rebalanced | +2.44 | +2.14 | 0.93 | 0.97 | 1.00 | +0.75 | 0.56 | +0.24 | 0.048 | -61 | -55 | 4 |
| G19 control cyclicals(4 Fid) all year | +2.15 | +0.67 | 0.88 | 0.93 | 1.00 | -0.16 | 0.43 | -0.80 | 0.290 | -58 | -55 | 326 |
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +1.50 | +0.93 | 0.80 | 0.92 | 0.98 | +1.09 | 0.51 | +0.38 | 0.135 | -56 | -55 | 460 |
| G1 win Oct1-May15 safe=long | -0.52 | -2.95 | 0.52 | 0.58 | 0.63 | -3.20 | 0.08 | -4.01 | 0.911 | -49 | -55 | 163 |
| G19 FSRPX+FSDAX+FSDPX (no tech) Nov-Apr / VFINX | -1.25 | -2.73 | 0.35 | 0.28 | 0.17 | -3.01 | 0.19 | -3.83 | 0.976 | -57 | -55 | 325 |
| G12 cyclicals Nov-Apr / VFINX May-Oct | -1.38 | -2.71 | 0.28 | 0.25 | 0.08 | -2.48 | 0.32 | -3.31 | 0.990 | -58 | -55 | 407 |
| G2 avoid Aug+Sep safe=short | -1.83 | -3.33 | 0.19 | 0.14 | 0.00 | -3.11 | 0.05 | -3.86 | 0.990 | -56 | -55 | 161 |
| G11 small Dec15-Mar1 else VFINX | -1.91 | -3.32 | 0.12 | 0.13 | 0.00 | -2.80 | 0.16 | -3.64 | 0.997 | -56 | -55 | 163 |


#### long, FED (8 configs)

| label | score | full_excess | ex10_beat | ex15_beat | ex20_beat | ho5_mean | ho5_beat | ho10_mean | boot_p | max_dd | bench_max_dd | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G22 buyhold cyclicals(4 Fid) never rebalanced | +2.66 | +2.16 | 0.93 | 0.97 | 1.00 | +0.84 | 0.56 | +0.24 | 0.051 | -61 | -55 | 4 |
| G19 control cyclicals(4 Fid) all year | +2.43 | +1.19 | 0.89 | 0.95 | 1.00 | -0.15 | 0.43 | -0.76 | 0.166 | -58 | -55 | 326 |
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +1.68 | +1.08 | 0.80 | 0.93 | 0.98 | +1.26 | 0.54 | +0.45 | 0.106 | -56 | -55 | 435 |
| G1 win Oct1-May15 safe=long | +0.32 | -1.68 | 0.56 | 0.60 | 0.78 | -2.74 | 0.27 | -3.23 | 0.792 | -48 | -55 | 163 |
| G19 FSRPX+FSDAX+FSDPX (no tech) Nov-Apr / VFINX | -0.53 | -1.38 | 0.40 | 0.40 | 0.54 | -2.47 | 0.30 | -2.96 | 0.864 | -56 | -55 | 325 |
| G12 cyclicals Nov-Apr / VFINX May-Oct | -0.66 | -1.37 | 0.41 | 0.30 | 0.47 | -1.81 | 0.38 | -2.32 | 0.891 | -57 | -55 | 407 |
| G2 avoid Aug+Sep safe=short | -1.27 | -2.17 | 0.32 | 0.25 | 0.10 | -2.66 | 0.11 | -3.07 | 0.957 | -55 | -55 | 161 |
| G11 small Dec15-Mar1 else VFINX | -1.28 | -2.09 | 0.15 | 0.17 | 0.05 | -2.17 | 0.30 | -2.70 | 0.979 | -56 | -55 | 163 |


#### long, NONE (8 configs)

| label | score | full_excess | ex10_beat | ex15_beat | ex20_beat | ho5_mean | ho5_beat | ho10_mean | boot_p | max_dd | bench_max_dd | trades |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| G1 win Oct1-May15 safe=long | +3.95 | +2.26 | 0.79 | 0.88 | 0.95 | +1.00 | 0.57 | +0.86 | 0.133 | -45 | -55 | 163 |
| G22 buyhold cyclicals(4 Fid) never rebalanced | +2.88 | +2.17 | 0.93 | 0.97 | 1.00 | +0.93 | 0.56 | +0.24 | 0.062 | -61 | -55 | 4 |
| G19 FSRPX+FSDAX+FSDPX (no tech) Nov-Apr / VFINX | +2.83 | +2.78 | 0.93 | 1.00 | 1.00 | +1.55 | 0.70 | +1.44 | 0.006 | -53 | -55 | 325 |
| G19 control cyclicals(4 Fid) all year | +2.76 | +1.74 | 0.89 | 0.95 | 1.00 | -0.08 | 0.43 | -0.67 | 0.105 | -58 | -55 | 326 |
| G12 cyclicals Nov-Apr / VFINX May-Oct | +2.69 | +2.78 | 1.00 | 1.00 | 1.00 | +2.49 | 0.78 | +2.36 | 0.008 | -55 | -55 | 407 |
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +2.68 | +2.78 | 1.00 | 1.00 | 1.00 | +2.44 | 0.78 | +2.30 | 0.008 | -54 | -55 | 1404 |
| G11 small Dec15-Mar1 else VFINX | +1.88 | +1.83 | 0.97 | 1.00 | 1.00 | +2.08 | 0.68 | +1.88 | 0.018 | -55 | -55 | 163 |
| G2 avoid Aug+Sep safe=short | +1.62 | +1.44 | 0.80 | 0.81 | 1.00 | +1.02 | 0.68 | +1.00 | 0.090 | -52 | -55 | 161 |


## Post-publication decay (long history, NONE and CA)

Mean excess of 5-year windows by window start, pp/yr, shown as "mean (beat rate, n)". These come from
the same records as `long_screen`.

**NONE** (5-year windows grouped by start year; 2013-2023 = starts 2013-2021)

| config | start 1986-1987 | start 1988-1999 | start 2000-2002 | start 2003-2012 | start 2013-2023 |
|---|---|---|---|---|---|
| G1 win Nov1-May1 safe=short | +1.5 (1.00, 2) | -0.9 (0.25, 12) | +3.9 (0.67, 3) | -0.2 (0.50, 10) | -6.6 (0.00, 9) |
| G8 harding Oct16/Apr20 macd12-26-9 safe=short | +2.4 (1.00, 2) | -0.4 (0.42, 12) | +4.7 (1.00, 3) | +0.4 (0.50, 10) | -6.5 (0.00, 9) |
| G2 avoid Sep safe=short | +1.9 (1.00, 2) | +0.4 (0.50, 12) | +4.0 (1.00, 3) | -0.7 (0.40, 10) | +1.3 (0.56, 9) |
| G7 barometer jan bearish->short until yearend | +0.5 (1.00, 2) | +1.3 (0.33, 12) | +1.0 (0.33, 3) | -3.0 (0.20, 10) | -6.8 (0.00, 9) |
| G4 TOM last1+first3 safe=cash | -2.9 (0.00, 2) | -11.0 (0.08, 12) | -0.4 (0.67, 3) | -7.5 (0.10, 10) | -13.5 (0.00, 9) |
| G5 preholiday only safe=cash | -12.1 (0.00, 2) | -15.2 (0.08, 12) | -3.3 (0.00, 3) | -7.7 (0.10, 10) | -13.9 (0.00, 9) |
| G11 small Dec15-Jan15 else VFINX | +0.8 (1.00, 2) | +1.8 (0.92, 12) | +0.1 (0.33, 3) | +0.4 (0.70, 10) | +0.6 (0.67, 9) |
| G13 samemonth Fid sectors yrs=all top1 | -1.0 (0.00, 2) | +9.1 (1.00, 12) | +5.8 (1.00, 3) | +0.1 (0.30, 10) | +2.0 (0.89, 9) |
| G12 cyclicals Nov-Apr / VFINX May-Oct | +4.5 (1.00, 2) | +3.0 (0.83, 12) | +2.9 (1.00, 3) | +3.2 (0.80, 10) | +0.9 (0.89, 9) |
| G19 control cyclicals(4 Fid) all year | -5.9 (0.00, 2) | +2.0 (0.58, 12) | +6.4 (1.00, 3) | +4.4 (0.90, 10) | +0.6 (0.67, 9) |
| G1 win Oct1-May15 safe=long | -0.8 (0.00, 2) | +5.4 (0.83, 12) | +12.1 (1.00, 3) | +4.5 (0.80, 10) | -3.8 (0.11, 9) |


**CA** (5-year windows grouped by start year; 2013-2023 = starts 2013-2021)

| config | start 1986-1987 | start 1988-1999 | start 2000-2002 | start 2003-2012 | start 2013-2023 |
|---|---|---|---|---|---|
| G1 win Nov1-May1 safe=short | -2.2 (0.00, 2) | -3.9 (0.25, 12) | +1.9 (0.67, 3) | -2.0 (0.40, 10) | -7.0 (0.00, 9) |
| G8 harding Oct16/Apr20 macd12-26-9 safe=short | -1.7 (0.00, 2) | -3.6 (0.25, 12) | +2.3 (0.67, 3) | -1.5 (0.40, 10) | -6.9 (0.00, 9) |
| G2 avoid Sep safe=short | -2.2 (0.00, 2) | -3.5 (0.17, 12) | +2.0 (0.67, 3) | -2.8 (0.00, 10) | -2.5 (0.00, 9) |
| G7 barometer jan bearish->short until yearend | -0.5 (0.50, 2) | +0.5 (0.33, 12) | +0.6 (0.33, 3) | -2.7 (0.20, 10) | -5.6 (0.00, 9) |
| G4 TOM last1+first3 safe=cash | -4.6 (0.00, 2) | -9.8 (0.08, 12) | -0.4 (0.33, 3) | -6.3 (0.00, 10) | -11.0 (0.00, 9) |
| G5 preholiday only safe=cash | -9.5 (0.00, 2) | -12.3 (0.00, 12) | -2.7 (0.00, 3) | -6.0 (0.10, 10) | -10.8 (0.00, 9) |
| G11 small Dec15-Jan15 else VFINX | -2.7 (0.00, 2) | -2.9 (0.08, 12) | -0.3 (0.33, 3) | -2.1 (0.00, 10) | -3.2 (0.00, 9) |
| G13 samemonth Fid sectors yrs=all top1 | -3.9 (0.00, 2) | -0.3 (0.33, 12) | +2.2 (1.00, 3) | -3.5 (0.10, 10) | -2.5 (0.11, 9) |
| G12 cyclicals Nov-Apr / VFINX May-Oct | -0.4 (0.00, 2) | -2.0 (0.25, 12) | +1.4 (1.00, 3) | -0.5 (0.40, 10) | -3.1 (0.00, 9) |
| G19 control cyclicals(4 Fid) all year | -4.7 (0.00, 2) | +1.4 (0.58, 12) | +5.0 (1.00, 3) | +3.4 (0.90, 10) | +0.4 (0.56, 9) |
| G1 win Oct1-May15 safe=long | -3.5 (0.00, 2) | -0.4 (0.33, 12) | +6.4 (1.00, 3) | +0.5 (0.60, 10) | -5.6 (0.00, 9) |


In NONE the Halloween, Harding and January-barometer rules are roughly flat for 1988-1999 starts.
They are positive only for starts in 1986-87 and 2000-02, the windows that contain the 1987 and
2000-02 crashes, and they lose 6-7 pp/yr for starts in 2013-2021. Turn-of-month and pre-holiday never
paid as strategies, even before 2000, because they leave the market (cash at 0%) most of the time.
Two rules in the table stay positive for every start era in NONE: sector seasonality and the
small-cap January switch (the latter by less than 2 pp). In CA sector seasonality is negative for
every start era except 2000-02.

## Robustness and hindsight checks

### A. The CA candidate: tax-managed cyclical season (`G19 cyclicals Nov-Apr / SPY TAX gb=0.01`)

**Holdings replay** (`holdings.py`, start 2000-01-01, CA). The weights shown are on the first trading
day of the month, in %.

| date | XLK | XLI | XLB | XLY | SPY |
|---|---|---|---|---|---|
| 2000-01-03 | 25.0 | 25.0 | 25.0 | 25.0 | 0.0 |
| 2000-05-01 | 0.0 | 0.0 | 0.0 | 0.0 | 100.0 |
| 2002-05-01 | 0.0 | 0.0 | 10.1 | 26.3 | 63.6 |
| 2003-05-01 | 24.8 | 24.8 | 24.7 | 5.4 | 20.3 |
| 2005-05-02 | 22.7 | 25.6 | 25.6 | 12.2 | 14.0 |
| 2008-11-03 | 25.0 | 25.0 | 25.0 | 25.0 | 0.0 |
| 2009-05-01 | 23.3 | 25.6 | 24.9 | 4.2 | 21.9 |
| 2015-05-01 | 24.5 | 23.9 | 22.1 | 16.8 | 12.7 |
| 2020-05-01 | 30.1 | 19.9 | 18.6 | 21.4 | 10.0 |
| 2026-05-01 | 31.8 | 23.0 | 17.1 | 18.4 | 9.8 |

It switches fully only while the holdings show losses: the 2000-02 bear market, and again in 2008
when it moved back to cyclicals. Otherwise the 1% gain budget freezes it. The average weights from
2010 on are XLK 26.6%, XLI 23.4%, XLB 20.6%, XLY 17.1% and SPY 12.3%. Taxes paid during the run were
$10.7k, against $272k deferred to liquidation, with turnover of 0.10/yr. The 1986-2026 Fidelity twin
does the same. After the 1987 crash it is a slowly drifting mix in which VFINX falls from about 50%
(1988) to 17% (2020s) and the tech fund (FSPTX) grows to 30-35%.

**Neighbours, static controls and long twins:**

Tax-managed cyclical season: neighbours and static controls -- `full`, CA

| config | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals Nov-Apr / SPY TAX gb=0.01 | +0.64 | +1.18 | 0.84 | -0.79 | 0.91 | 0.025 | -57 | 423 | 0.10 |
| G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 | +0.85 | +1.44 | 0.91 | -0.85 | 0.94 | 0.035 | -57 | 416 | 0.08 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.05 | +0.13 | +0.41 | 0.58 | -1.64 | 0.77 | 0.268 | -55 | 521 | 0.43 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.01 | +0.46 | +0.59 | 0.66 | -2.26 | 0.83 | 0.304 | -57 | 325 | 0.10 |
| G12 cyclicals Nov-Apr / SPY May-Oct | -2.17 | -2.17 | 0.10 | -4.73 | 0.00 | 0.982 | -58 | 269 | 2.05 |
| G19 control cyclicals(4) all year | +0.93 | +0.63 | 0.97 | -0.04 | 0.91 | 0.187 | -56 | 216 | 0.05 |
| G22 buyhold cyclicals(4) never rebalanced | +1.21 | +0.46 | 1.00 | +0.53 | 1.00 | 0.287 | -58 | 4 | 0.00 |
| G22 buyhold XLY+XLI+XLB never rebalanced | +0.46 | +0.49 | 0.61 | -2.37 | 0.74 | 0.350 | -59 | 3 | 0.00 |
| G19 control XLY+XLI+XLB all year | +0.36 | +0.42 | 0.60 | -2.41 | 0.66 | 0.379 | -59 | 162 | 0.04 |


Tax-managed cyclical season: neighbours and static controls -- `full`, FED

| config | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals Nov-Apr / SPY TAX gb=0.01 | +0.73 | +1.22 | 0.85 | -0.76 | 0.94 | 0.027 | -57 | 427 | 0.10 |
| G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 | +0.96 | +1.49 | 0.93 | -0.86 | 0.98 | 0.027 | -57 | 416 | 0.08 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.05 | +0.35 | +0.72 | 0.64 | -1.10 | 0.81 | 0.108 | -55 | 537 | 0.41 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.01 | +0.54 | +0.63 | 0.67 | -2.35 | 0.83 | 0.303 | -57 | 325 | 0.10 |
| G12 cyclicals Nov-Apr / SPY May-Oct | -1.69 | -1.56 | 0.12 | -3.93 | 0.06 | 0.938 | -57 | 269 | 2.04 |
| G19 control cyclicals(4) all year | +1.06 | +0.73 | 1.00 | +0.03 | 0.96 | 0.161 | -56 | 216 | 0.05 |
| G22 buyhold cyclicals(4) never rebalanced | +1.32 | +0.48 | 1.00 | +0.56 | 1.00 | 0.294 | -58 | 4 | 0.00 |
| G22 buyhold XLY+XLI+XLB never rebalanced | +0.51 | +0.51 | 0.61 | -2.53 | 0.74 | 0.351 | -59 | 3 | 0.00 |
| G19 control XLY+XLI+XLB all year | +0.45 | +0.54 | 0.60 | -2.51 | 0.66 | 0.347 | -59 | 162 | 0.04 |


Tax-managed cyclical season: neighbours and static controls -- `full`, NONE

| config | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals Nov-Apr / SPY TAX gb=0.01 | +0.98 | +0.96 | 1.00 | +0.05 | 0.94 | 0.070 | -55 | 903 | 2.06 |
| G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 | +1.22 | +1.31 | 0.90 | -0.32 | 0.96 | 0.042 | -56 | 1009 | 2.06 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.05 | +0.98 | +0.96 | 1.00 | +0.05 | 0.94 | 0.070 | -55 | 903 | 2.06 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.01 | +1.46 | +1.81 | 0.78 | -0.53 | 0.89 | 0.034 | -56 | 691 | 2.05 |
| G12 cyclicals Nov-Apr / SPY May-Oct | +0.98 | +0.94 | 1.00 | +0.05 | 0.94 | 0.071 | -55 | 269 | 2.00 |
| G19 control cyclicals(4) all year | +1.22 | +0.84 | 1.00 | +0.11 | 0.98 | 0.133 | -56 | 216 | 0.04 |
| G22 buyhold cyclicals(4) never rebalanced | +1.42 | +0.49 | 1.00 | +0.60 | 1.00 | 0.301 | -58 | 4 | 0.00 |
| G22 buyhold XLY+XLI+XLB never rebalanced | +0.57 | +0.52 | 0.61 | -2.69 | 0.74 | 0.357 | -59 | 3 | 0.00 |
| G19 control XLY+XLI+XLB all year | +0.56 | +0.69 | 0.60 | -2.57 | 0.68 | 0.321 | -59 | 162 | 0.04 |


Tax-managed variants on the screen -- `screen`, CA

| config | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals Nov-Apr / SPY TAX gb=0.01 | +0.54 | +1.18 | 0.76 | -0.79 | 0.83 | 0.025 | -57 | 423 | 0.10 |
| G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 | +0.77 | +1.44 | 0.88 | -0.78 | 0.92 | 0.035 | -57 | 416 | 0.08 |
| G22 cyclicals Oct15-May15 / SPY TAX gb=0.01 | +0.50 | +1.25 | 0.88 | -0.82 | 1.00 | 0.050 | -56 | 414 | 0.10 |
| G22 cyclicals Nov1-Jun1 / SPY TAX gb=0.01 | +0.44 | +0.85 | 0.88 | -0.11 | 0.92 | 0.071 | -56 | 427 | 0.11 |
| G22 cyclicals Nov1-Apr1 / SPY TAX gb=0.01 | +0.47 | +0.42 | 0.82 | -0.46 | 0.92 | 0.148 | -55 | 252 | 0.12 |
| G22 cyclicals Nov15-May1 / SPY TAX gb=0.01 | +0.75 | +1.33 | 0.82 | -0.79 | 0.83 | 0.012 | -55 | 376 | 0.10 |
| G22 cyclicals Dec1-May1 / SPY TAX gb=0.01 | +0.62 | +0.31 | 0.82 | -0.79 | 0.83 | 0.284 | -55 | 429 | 0.13 |
| G22 cyclicals Nov-Apr / SPY TAX gb=0.0 | +0.53 | +1.31 | 0.88 | -1.70 | 1.00 | 0.022 | -56 | 106 | 0.07 |
| G22 cyclicals Nov-Apr / SPY TAX gb=0.005 | +0.50 | +1.42 | 0.76 | -1.13 | 0.92 | 0.011 | -57 | 380 | 0.08 |
| G22 cyclicals Nov-Apr / SPY TAX gb=0.02 | +0.46 | +0.60 | 0.82 | -0.64 | 0.92 | 0.166 | -56 | 364 | 0.14 |
| G22 cyclicals Nov-Apr / SPY TAX gb=0.03 | +0.39 | +0.63 | 0.82 | -0.78 | 0.92 | 0.143 | -56 | 346 | 0.17 |
| G19 cyclicals Nov-Apr / SPY TAX gb=0.05 | +0.16 | +0.41 | 0.59 | -1.16 | 0.83 | 0.268 | -55 | 521 | 0.43 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.01 | +0.41 | +0.59 | 0.71 | -2.14 | 0.92 | 0.304 | -57 | 325 | 0.10 |
| G19 XLY+XLI+XLB Nov-Apr / SPY TAX gb=0.05 | -0.31 | -0.21 | 0.59 | -3.14 | 0.25 | 0.597 | -58 | 473 | 0.50 |
| G19 control cyclicals(4) all year | +0.87 | +0.63 | 0.94 | -0.04 | 0.92 | 0.187 | -56 | 216 | 0.05 |
| G17 Halloween short TAX gb=0.01 | -0.27 | +0.29 | 0.29 | -2.92 | 0.42 | 0.470 | -34 | 70 | 0.14 |
| G17 Halloween short TAX gb=0.05 | -1.53 | -0.70 | 0.18 | -4.35 | 0.17 | 0.647 | -35 | 153 | 0.69 |
| G17 Halloween short TAX no-ST-gains gb=1.0 | -2.30 | -0.83 | 0.24 | -8.19 | 0.17 | 0.637 | -22 | 75 | 0.78 |
| G22 buyhold cyclicals(4) never rebalanced | +1.13 | +0.46 | 1.00 | +0.59 | 1.00 | 0.287 | -58 | 4 | 0.00 |
| G22 buyhold XLY+XLI+XLB never rebalanced | +0.48 | +0.49 | 0.65 | -2.25 | 0.83 | 0.350 | -59 | 3 | 0.00 |


Long-history twins -- `long`, CA

| config | score | full_excess | ex10_beat | ex15_beat | ho5_mean | ho5_beat | ho10_mean | boot_p | max_dd |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +1.50 | +0.93 | 0.80 | 0.92 | +1.09 | 0.51 | +0.38 | 0.135 | -56 |
| G19 FSRPX+FSDAX+FSDPX Nov-Apr / VFINX TAX gb=0.01 | (not run) |  |  |  |  |  |  |  |  |
| G12 cyclicals Nov-Apr / VFINX May-Oct | -1.38 | -2.71 | 0.28 | 0.25 | -2.48 | 0.32 | -3.31 | 0.990 | -58 |
| G19 control cyclicals(4 Fid) all year | +2.15 | +0.67 | 0.88 | 0.93 | -0.16 | 0.43 | -0.80 | 0.290 | -58 |
| G22 buyhold cyclicals(4 Fid) never rebalanced | +2.44 | +2.14 | 0.93 | 0.97 | +0.75 | 0.56 | +0.24 | 0.048 | -61 |


Long-history twins -- `long`, NONE

| config | score | full_excess | ex10_beat | ex15_beat | ho5_mean | ho5_beat | ho10_mean | boot_p | max_dd |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +2.68 | +2.78 | 1.00 | 1.00 | +2.44 | 0.78 | +2.30 | 0.008 | -54 |
| G19 FSRPX+FSDAX+FSDPX Nov-Apr / VFINX TAX gb=0.01 | (not run) |  |  |  |  |  |  |  |  |
| G12 cyclicals Nov-Apr / VFINX May-Oct | +2.69 | +2.78 | 1.00 | 1.00 | +2.49 | 0.78 | +2.36 | 0.008 | -55 |
| G19 control cyclicals(4 Fid) all year | +2.76 | +1.74 | 0.89 | 0.95 | -0.08 | 0.43 | -0.67 | 0.105 | -58 |
| G22 buyhold cyclicals(4 Fid) never rebalanced | +2.88 | +2.17 | 0.93 | 0.97 | +0.93 | 0.56 | +0.24 | 0.062 | -61 |


Long-history twins -- `long_screen`, CA

| config | score | full_excess | ex10_beat | ex15_beat | ho5_mean | ho5_beat | ho10_mean | boot_p | max_dd |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +1.48 | +0.93 | 0.74 | 0.88 | +0.98 | 0.50 | +0.29 | 0.135 | -56 |
| G19 FSRPX+FSDAX+FSDPX Nov-Apr / VFINX TAX gb=0.01 | +1.04 | +0.31 | 0.65 | 0.88 | -0.54 | 0.50 | -1.37 | 0.341 | -54 |
| G12 cyclicals Nov-Apr / VFINX May-Oct | -1.40 | -2.71 | 0.29 | 0.23 | -2.73 | 0.10 | -3.39 | 0.990 | -58 |
| G19 control cyclicals(4 Fid) all year | +2.09 | +0.67 | 0.87 | 0.88 | -0.44 | 0.40 | -0.62 | 0.290 | -58 |
| G22 buyhold cyclicals(4 Fid) never rebalanced | +2.47 | +1.96 | 0.93 | 0.96 | +0.92 | 0.67 | +0.98 | 0.086 | -61 |


Long-history twins -- `long_screen`, NONE

| config | score | full_excess | ex10_beat | ex15_beat | ho5_mean | ho5_beat | ho10_mean | boot_p | max_dd |
|---|---|---|---|---|---|---|---|---|---|
| G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 | +2.70 | +2.78 | 1.00 | 1.00 | +2.36 | 0.80 | +2.41 | 0.008 | -54 |
| G19 FSRPX+FSDAX+FSDPX Nov-Apr / VFINX TAX gb=0.01 | +2.86 | +2.79 | 0.97 | 1.00 | +1.22 | 0.70 | +1.28 | 0.006 | -53 |
| G12 cyclicals Nov-Apr / VFINX May-Oct | +2.70 | +2.78 | 1.00 | 1.00 | +2.41 | 0.80 | +2.47 | 0.008 | -55 |
| G19 control cyclicals(4 Fid) all year | +2.71 | +1.74 | 0.87 | 0.92 | -0.40 | 0.40 | -0.41 | 0.105 | -58 |
| G22 buyhold cyclicals(4 Fid) never rebalanced | +2.91 | +1.98 | 0.93 | 0.96 | +1.13 | 0.67 | +1.05 | 0.102 | -61 |


All 11 neighbours on the screen are positive in CA, and their 10-year beat rates are 0.76-0.88
(0.59 at a 5% budget). Their
boot_p is at or below 0.071 for gain budgets of 1% or less and for four of the six boundary pairs, and
0.14-0.28 otherwise. So the score is not a lone spike, but the confidence is. A gain budget of 0
(never realize a gain, switch only through losses) does as well as 1%. That confirms the edge comes
from the frozen cyclical tilt plus loss harvesting, not from the calendar. The never-rebalanced
buy-and-hold of the same four SPDRs has the best CA score (+1.21), and every 10- and 15-year window and
all three sub-periods are positive (+1.43 / +0.95 / +0.65 pp). Its boot_p is 0.287, because the
2000-01 path starts at the tech peak. Without XLK, both the static and the seasonal versions fail.

**Same tax-managed rule on 24 random menus (PROTOCOL 5.3)**: see the "CA TAX season" columns of the
random-menu table in section B. 8 of 24 menus are positive (median -0.11 pp, best +0.25) and none
clears items 1-3. The cyclical basket (+0.54 on the screen) beats all 24. The six menus with positive
full-period excess and boot_p of 0.11 or less all hold a tech fund (XLK, IYW, IGV, QQQ or SOXX).

### B. Sector seasons (NONE): boundaries, baskets, placebos, random menus

Sector seasons: boundaries, baskets, controls, placebos -- `screen`, NONE

| config | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|
| G12 cyclicals Nov-Apr / SPY May-Oct | +0.96 | +0.94 | 1.00 | +0.10 | 0.92 | 0.071 | -55 | 269 | 2.00 |
| G19 cyclicals Oct1-May1 / SPY | +1.18 | +1.31 | 0.94 | -0.35 | 0.92 | 0.048 | -56 | 269 | 1.99 |
| G19 cyclicals Oct15-May15 / SPY | +0.87 | +1.23 | 0.76 | -0.24 | 0.83 | 0.043 | -54 | 269 | 2.01 |
| G19 cyclicals Nov1-Jun1 / SPY | +0.95 | +0.91 | 0.94 | -0.04 | 0.92 | 0.080 | -54 | 269 | 2.02 |
| G19 cyclicals Nov1-Apr1 / SPY | +0.74 | +0.86 | 0.94 | -0.12 | 0.92 | 0.047 | -55 | 269 | 1.99 |
| G19 cyclicals Nov15-May1 / SPY | +0.58 | +0.50 | 0.71 | -0.52 | 0.83 | 0.219 | -53 | 269 | 2.02 |
| G19 cyclicals Dec1-May1 / SPY | +0.31 | +0.14 | 0.65 | -0.60 | 0.83 | 0.432 | -53 | 269 | 2.04 |
| G19 XLY+XLI+XLB (no XLK) Nov-Apr / SPY May-Oct | +1.49 | +1.81 | 0.71 | -0.50 | 0.92 | 0.035 | -56 | 215 | 2.00 |
| G19 XLY+XLI+XLB+XLK+XLF Nov-Apr / SPY May-Oct | +0.36 | +0.52 | 0.82 | -0.10 | 0.92 | 0.194 | -60 | 323 | 2.00 |
| G19 XLY+XLI+XLB+XLF+XLE Nov-Apr / SPY May-Oct | +0.86 | +1.73 | 0.76 | -1.41 | 0.75 | 0.065 | -58 | 323 | 2.00 |
| G19 XLK only Nov-Apr / SPY May-Oct | -0.88 | -2.21 | 0.35 | -5.36 | 0.50 | 0.916 | -74 | 107 | 2.00 |
| G19 XLY only Nov-Apr / SPY May-Oct | +1.38 | +1.07 | 0.82 | -1.04 | 0.92 | 0.255 | -57 | 107 | 2.00 |
| G19 XLI only Nov-Apr / SPY May-Oct | +1.09 | +1.49 | 0.65 | -1.19 | 0.92 | 0.071 | -59 | 107 | 2.00 |
| G19 XLB only Nov-Apr / SPY May-Oct | +1.70 | +2.46 | 0.76 | -1.95 | 0.83 | 0.070 | -53 | 107 | 2.00 |
| G12 cyclicals Nov-Apr / defensives May-Oct | +1.60 | +0.83 | 0.71 | -3.84 | 0.83 | 0.314 | -47 | 375 | 2.01 |
| G19 control cyclicals(4) all year | +1.16 | +0.84 | 1.00 | +0.17 | 0.92 | 0.133 | -56 | 216 | 0.04 |
| G19 control XLY+XLI+XLB all year | +0.60 | +0.69 | 0.59 | -2.45 | 0.83 | 0.321 | -59 | 162 | 0.04 |
| G22 buyhold cyclicals(4) never rebalanced | (not run) |  |  |  |  |  |  |  |  |
| G19 control equal-weight 9 sectors all year | +0.18 | +0.54 | 0.53 | -2.09 | 0.58 | 0.305 | -53 | 485 | 0.06 |
| G19 placebo SPY Nov-Apr / cyclicals May-Oct | -0.66 | -0.95 | 0.00 | -1.29 | 0.00 | 0.946 | -57 | 266 | 2.00 |
| G19 placebo defensives Nov-Apr / SPY May-Oct | -0.96 | -0.35 | 0.18 | -2.99 | 0.17 | 0.614 | -48 | 215 | 2.01 |


Sector seasons: boundaries, baskets, controls, placebos -- `screen`, CA

| config | score | full_excess | ex10_beat | ex10_min | ex15_beat | boot_p | max_dd | trades | turnover |
|---|---|---|---|---|---|---|---|---|---|
| G12 cyclicals Nov-Apr / SPY May-Oct | -2.08 | -2.17 | 0.12 | -4.33 | 0.00 | 0.982 | -58 | 269 | 2.05 |
| G19 cyclicals Oct1-May1 / SPY | -1.90 | -1.91 | 0.18 | -4.44 | 0.08 | 0.937 | -60 | 269 | 2.04 |
| G19 cyclicals Oct15-May15 / SPY | -2.10 | -1.95 | 0.12 | -4.39 | 0.08 | 0.947 | -58 | 269 | 2.05 |
| G19 cyclicals Nov1-Jun1 / SPY | -2.05 | -2.15 | 0.18 | -4.21 | 0.00 | 0.974 | -58 | 269 | 2.07 |
| G19 cyclicals Nov1-Apr1 / SPY | -2.27 | -2.25 | 0.12 | -4.54 | 0.00 | 0.992 | -58 | 269 | 2.04 |
| G19 cyclicals Nov15-May1 / SPY | -2.29 | -2.42 | 0.12 | -4.79 | 0.00 | 0.996 | -55 | 269 | 2.07 |
| G19 cyclicals Dec1-May1 / SPY | -2.48 | -2.64 | 0.12 | -4.87 | 0.00 | 0.995 | -55 | 269 | 2.08 |
| G19 XLY+XLI+XLB (no XLK) Nov-Apr / SPY May-Oct | -1.77 | -1.70 | 0.18 | -4.66 | 0.17 | 0.876 | -59 | 215 | 2.06 |
| G19 XLY+XLI+XLB+XLK+XLF Nov-Apr / SPY May-Oct | -2.49 | -2.41 | 0.00 | -4.39 | 0.00 | 0.988 | -63 | 323 | 2.05 |
| G19 XLY+XLI+XLB+XLF+XLE Nov-Apr / SPY May-Oct | -2.13 | -1.71 | 0.18 | -5.19 | 0.08 | 0.899 | -61 | 323 | 2.06 |
| G19 XLK only Nov-Apr / SPY May-Oct | -3.35 | -3.81 | 0.00 | -5.36 | 0.00 | 0.998 | -74 | 107 | 2.05 |
| G19 XLY only Nov-Apr / SPY May-Oct | -1.97 | -2.12 | 0.18 | -5.87 | 0.08 | 0.866 | -60 | 107 | 2.05 |
| G19 XLI only Nov-Apr / SPY May-Oct | -1.99 | -1.87 | 0.18 | -5.39 | 0.08 | 0.949 | -62 | 107 | 2.05 |
| G19 XLB only Nov-Apr / SPY May-Oct | -1.59 | -1.31 | 0.24 | -5.17 | 0.25 | 0.786 | -57 | 107 | 2.06 |
| G12 cyclicals Nov-Apr / defensives May-Oct | -1.67 | -2.24 | 0.53 | -6.37 | 0.17 | 0.888 | -50 | 375 | 2.05 |
| G19 control cyclicals(4) all year | +0.87 | +0.63 | 0.94 | -0.04 | 0.92 | 0.187 | -56 | 216 | 0.05 |
| G19 control XLY+XLI+XLB all year | +0.39 | +0.42 | 0.59 | -2.28 | 0.75 | 0.379 | -59 | 162 | 0.04 |
| G22 buyhold cyclicals(4) never rebalanced | +1.13 | +0.46 | 1.00 | +0.59 | 1.00 | 0.287 | -58 | 4 | 0.00 |
| G19 control equal-weight 9 sectors all year | -0.01 | +0.18 | 0.47 | -2.05 | 0.50 | 0.444 | -54 | 485 | 0.07 |
| G19 placebo SPY Nov-Apr / cyclicals May-Oct | -3.12 | -3.18 | 0.00 | -4.80 | 0.00 | 0.999 | -60 | 266 | 2.05 |
| G19 placebo defensives Nov-Apr / SPY May-Oct | -3.14 | -2.84 | 0.06 | -5.95 | 0.00 | 0.988 | -52 | 215 | 2.05 |


**All 126 four-sector baskets held Nov-Apr (index otherwise)**:

etf `screen` NONE: 125 other 4-sector baskets (+ the cyclical one = 126). Cyclicals score +0.96 ranks 11/126. Baskets with score > 0: 73/125; median +0.07; boot_p <= 0.10: 23. Top 5: XLE+XLY+XLI+XLB +1.60 (p 0.027); XLE+XLV+XLY+XLB +1.33 (p 0.041); XLE+XLV+XLI+XLB +1.20 (p 0.044); XLE+XLV+XLY+XLI +1.18 (p 0.031); XLK+XLE+XLY+XLB +1.17 (p 0.025)
  mean score of baskets containing each sector: XLE +0.39, XLB +0.36, XLY +0.34, XLI +0.26, XLV +0.10, XLK -0.02, XLU -0.10, XLP -0.12, XLF -0.23

etf `screen` CA: 44 other 4-sector baskets (+ the cyclical one = 45). Cyclicals score -2.08 ranks 4/45. Baskets with score > 0: 0/44; median -2.68; boot_p <= 0.10: 0. Top 5: XLK+XLE+XLY+XLB -1.90 (p 0.934); XLK+XLE+XLI+XLB -1.95 (p 0.941); XLK+XLE+XLY+XLI -2.01 (p 0.978); XLK+XLE+XLV+XLB -2.10 (p 0.953); XLK+XLE+XLV+XLY -2.16 (p 0.972)
  mean score of baskets containing each sector: XLE -2.40, XLB -2.47, XLY -2.55, XLI -2.57, XLK -2.67, XLV -2.69, XLU -2.82, XLP -2.83, XLF -2.93

long `long_screen` NONE: 125 other 4-sector baskets (+ the cyclical one = 126). Cyclicals score +2.70 ranks 1/126. Baskets with score > 0: 120/125; median +1.10; boot_p <= 0.10: 72. Top 5: FSENX+FSRPX+FSDAX+FSDPX +2.64 (p 0.019); FSPTX+FSENX+FSRPX+FSDAX +2.54 (p 0.004); FSPTX+FSENX+FSRPX+FSDPX +2.52 (p 0.009); FSPTX+FSENX+FSDAX+FSDPX +2.41 (p 0.020); FSPHX+FSRPX+FSDAX+FSDPX +2.23 (p 0.010)
  mean score of baskets containing each sector: FSRPX +1.45, FSDAX +1.38, FSDPX +1.37, FSPTX +1.28, FSENX +1.28, FSPHX +1.00, FIDSX +0.96, FDFAX +0.79, FSUTX +0.75

long `long_screen` CA: not run (the long-era basket placebo ran in NONE only).


**Random 4-fund menus from `BROAD_EQUITY_POOL_2003`** (G21 NONE; G22 CA tax-managed). Each window
starts once all four funds exist:

| seed | menu | NONE season score | NONE season boot_p | NONE all-year score | season minus all-year | CA TAX season score | CA ex10_beat | CA ex15_beat | CA boot_p | first start |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | EWA+IJR+IWR+IYE | +0.41 | 0.168 | -1.53 | +1.94 | -0.10 | 0.53 | 0.70 | 0.733 | 2002-01-01 |
| 1 | EWG+EWP+IJH+VTI | -0.57 | 0.241 | -2.46 | +1.89 | -0.35 | 0.47 | 0.60 | 0.700 | 2002-01-01 |
| 2 | EWD+EWI+EWJ+IWN | -0.71 | 0.341 | -3.85 | +3.14 | -0.92 | 0.31 | 0.27 | 0.889 | 2001-01-01 |
| 3 | EWO+IEV+SOXX+XLE | +1.12 | 0.016 | -1.87 | +2.99 | +0.01 | 0.67 | 0.70 | 0.112 | 2002-01-01 |
| 4 | EWL+IEV+IUSV+IWS | -0.24 | 0.209 | -2.27 | +2.03 | -0.95 | 0.13 | 0.10 | 0.621 | 2002-01-01 |
| 5 | IJH+IWM+RWR+XLP | -0.26 | 0.472 | -0.84 | +0.57 | -0.72 | 0.53 | 0.30 | 0.595 | 2002-01-01 |
| 6 | EWI+IJR+MDY+VXF | -0.21 | 0.398 | -2.33 | +2.12 | -0.83 | 0.50 | 0.11 | 0.841 | 2003-01-01 |
| 7 | EWC+EWS+IVW+IWS | -0.09 | 0.241 | -1.51 | +1.42 | -0.09 | 0.53 | 0.60 | 0.666 | 2002-01-01 |
| 8 | EWO+IDU+IWO+IWP | +0.11 | 0.125 | -1.17 | +1.28 | +0.04 | 0.53 | 0.80 | 0.489 | 2002-01-01 |
| 9 | IJS+IWO+IYR+XLK | -0.11 | 0.513 | +0.39 | -0.50 | +0.16 | 0.62 | 0.45 | 0.041 | 2001-01-01 |
| 10 | EPP+IYF+IYZ+VXF | -1.30 | 0.827 | -3.42 | +2.12 | -0.83 | 0.43 | 0.33 | 0.985 | 2003-01-01 |
| 11 | IYK+IYR+QQQ+SPYV | -0.45 | 0.713 | +0.41 | -0.86 | -0.02 | 0.56 | 0.73 | 0.011 | 2001-01-01 |
| 12 | IJS+IWF+IYW+RWR | -0.12 | 0.662 | +0.85 | -0.98 | +0.25 | 0.67 | 0.50 | 0.010 | 2002-01-01 |
| 13 | EWY+IDU+IJR+IUSG | +0.34 | 0.097 | -0.14 | +0.48 | +0.05 | 0.56 | 0.82 | 0.371 | 2001-01-01 |
| 14 | EWL+IGV+RWR+XLK | -0.39 | 0.846 | +0.91 | -1.30 | +0.25 | 0.67 | 0.70 | 0.042 | 2002-01-01 |
| 15 | DVY+EPP+FVD+RSP | -0.53 | 0.587 | -1.81 | +1.28 | -0.90 | 0.38 | 0.25 | 0.329 | 2004-01-01 |
| 16 | ILF+IWN+IYW+IYZ | -1.20 | 0.609 | -1.75 | +0.55 | +0.20 | 0.47 | 0.70 | 0.265 | 2002-01-01 |
| 17 | IUSV+IWN+IYE+RSP | -0.21 | 0.369 | -2.62 | +2.41 | -0.77 | 0.31 | 0.12 | 0.136 | 2004-01-01 |
| 18 | EWN+EWY+IWB+IYK | +0.39 | 0.054 | -0.89 | +1.28 | -0.17 | 0.56 | 0.73 | 0.555 | 2001-01-01 |
| 19 | EWA+EWN+QQQ+RSP | +0.03 | 0.228 | -0.74 | +0.77 | -0.04 | 0.54 | 0.88 | 0.316 | 2004-01-01 |
| 20 | EWK+EWS+IJR+XLV | +0.37 | 0.189 | -1.09 | +1.46 | -0.44 | 0.50 | 0.55 | 0.764 | 2001-01-01 |
| 21 | EWU+ILF+IYE+XLV | -0.74 | 0.254 | -3.08 | +2.34 | -0.12 | 0.47 | 0.60 | 0.661 | 2002-01-01 |
| 22 | EFA+EWP+IGV+XLK | -1.38 | 0.758 | -0.80 | -0.59 | +0.20 | 0.67 | 0.80 | 0.077 | 2002-01-01 |
| 23 | EEM+EWI+IUSG+XLE | -1.15 | 0.305 | -4.41 | +3.27 | -0.41 | 0.46 | 0.62 | 0.355 | 2004-01-01 |

NONE season: n=24, >0: 7, median -0.22, mean -0.29
NONE all-year: n=24, >0: 4, median -1.52, mean -1.50
season minus all-year: n=24, >0: 19, median +1.35, mean +1.21
CA TAX season: n=24, >0: 8, median -0.11, mean -0.27
CA TAX random menus clearing bar items 1-3 on the screen: 0/24


Taken together:
* The rule "risky basket in winter, index in summer" does not beat the index on menus nobody chose.
  The cyclical result depends on the basket.
* Seasonality does exist in a weaker sense. For 19 of 24 random menus, holding the basket only in
  Nov-Apr beats holding it all year. The basket underperforms the index mostly in May-Oct, and
  reverse-season placebos lose in both eras.
* Among the SPDR sectors, energy, materials, discretionary and industrials help a winter basket. Tech
  is neutral and staples, utilities and financials hurt.
* In the long history almost every Fidelity basket wins (120/125, median +1.10 pp). An equal-weight
  basket of all nine Fidelity sector funds held all year also beats VFINX (+1.74 on `long_screen`
  NONE). So the long-history sector results mix fund and sector selection with seasonality, and
  should not be read as pure calendar evidence.

### C. Trading costs: do the high-turnover effects exist before costs?

| config (NONE, screen) | score at site costs (5+5 bp) | score at 0+1 bp | full_excess at 0+1 bp | ex10_beat at 0+1 bp | boot_p at 0+1 bp | trades |
|---|---|---|---|---|---|---|
| G4 TOM last1+first3 safe=cash | -9.15 | -6.97 | -5.72 | 0.12 | 0.949 | 637 |
| G4 TOM last4+first5 safe=cash | -3.95 | -1.65 | -1.27 | 0.24 | 0.686 | 637 |
| G10 LEV TOM(1,3) 50% SSO swap / SPY | -1.79 | +0.63 | +0.37 | 0.90 | 0.298 | 938 |
| G1 win Nov1-May1 safe=short | -2.07 | -1.69 | -1.33 | 0.47 | 0.711 | 107 |
| G5 avoid Mondays safe=cash | -10.36 | -1.59 | -2.96 | 0.12 | 0.963 | 2497 |
| G5 preholiday only safe=cash | -9.97 | -8.37 | -7.45 | 0.06 | 0.983 | 481 |
| G2 avoid Sep safe=short | +0.40 | +0.79 | +1.62 | 0.65 | 0.068 | 105 |
| G12 cyclicals Nov-Apr / SPY May-Oct | +0.96 | +1.35 | +1.34 | 1.00 | 0.021 | 269 |


At almost zero cost (0 commission, 1 bp slippage), turn-of-month, pre-holiday, avoid-Mondays and
T-bill Halloween still lose to SPY in 2000-2026. Their problem is time out of the market, not costs.
Sector seasonality and avoid-September gain about 0.4 pp/yr from the lower costs. The leveraged TOM
swap turns positive, but that is leverage.

### D. Leverage

G10 compares seasonal leverage with constant leverage at the same average exposure. SSO Nov-Apr / SPY
May-Oct (NONE full +4.32, boot_p 0.162) does not beat a constant 50% SSO + 50% SPY (+3.68,
boot_p 0.117) by more than noise. Both have about -75% drawdowns. In CA the constant version scores
+2.77 (boot_p 0.174) and the seasonal one -1.33. Either way the gain is leverage, and leverage belongs
to the leverage family.

## Diagnostics (report.diagnostics on the screened grids)

The sets are:
* `core`: G1-G18, the pre-registered grid;
* `family`: everything screened in the regime;
* `sector`: G12 + G19 without placebos.

The variant `full_hist` keeps only configs whose first window starts at the protocol's first start.
`report.diagnostics` drops months missing for any config (`monthly_matrix(...).dropna()`), so a single
late-starting config truncates PBO and DSR for the whole set (see the lab bug note).
Walk-forward: choose the best trailing-10-year config each year, then score the next 5 years (WF5/3:
5-year in-sample, 3-year out-of-sample).

| era | set | regime | variant | n | WF10/5 OOS mean | WF OOS beat | WF IS mean | avg config OOS | WF5/3 OOS mean | PBO | PBO sample (months) | OOS of IS-best | DSR best | best by monthly mean |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| etf | core | CA | all | 262 | -6.07 | 0.00 | +5.14 | -6.71 | -3.79 | 0.15 | 199 from 2010-01 | +1.07 | 0.138 | G10 LEV control const 50SSO+50SPY (1.5x) |
| etf | core | CA | full_hist | 249 | -6.46 | 0.00 | +3.49 | -6.77 | -3.93 | 0.26 | 319 from 2000-01 | -2.79 | 0.001 | G7 barometer first5 bearish->short until yearend |
| etf | core | NONE | all | 262 | -4.40 | 0.00 | +9.97 | -6.15 | -8.00 | 0.25 | 199 from 2010-01 | -0.21 | 0.014 | G10 LEV SSO Nov-Apr / SPY May-Oct |
| etf | core | NONE | full_hist | 249 | -5.19 | 0.00 | +7.33 | -6.22 | -4.92 | 0.45 | 319 from 2000-01 | -1.67 | 0.002 | G1 win Oct1-May15 safe=long |
| etf | family | CA | all | 364 | -6.07 | 0.00 | +5.14 | -5.62 | -3.57 | 0.16 | 199 from 2010-01 | -0.75 | 0.032 | G10 LEV control const 50SSO+50SPY (1.5x) |
| etf | family | CA | full_hist | 327 | -3.87 | 0.00 | +3.97 | -5.85 | -3.69 | 0.24 | 319 from 2000-01 | -1.88 | 0.017 | G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 |
| etf | family | NONE | all | 458 | -4.40 | 0.00 | +9.97 | -4.06 | -7.87 | 0.41 | 199 from 2010-01 | -0.71 | 0.009 | G10 LEV SSO Nov-Apr / SPY May-Oct |
| etf | family | NONE | full_hist | 397 | -5.19 | 0.00 | +7.33 | -4.20 | -6.03 | 0.65 | 319 from 2000-01 | -1.44 | 0.001 | G1 win Oct1-May15 safe=long |
| etf | sector | CA | all | 70 | -0.52 | 0.33 | +1.21 | -3.41 | -1.44 | 0.05 | 319 from 2000-01 | +0.32 | 0.078 | G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 |
| etf | sector | NONE | all | 151 | -0.72 | 0.67 | +4.14 | -0.84 | -1.87 | 0.48 | 319 from 2000-01 | +0.30 | 0.267 | G19 XLB only Nov-Apr / SPY May-Oct |
| long | core | CA | all | 235 | -0.10 | 0.33 | +3.84 | -2.42 | -0.13 | 0.25 | 487 from 1986-01 | -2.95 | 0.000 | G17 Halloween short TAX gb=0.01 |
| long | core | NONE | all | 235 | -1.04 | 0.33 | +8.52 | -0.67 | -2.36 | 0.16 | 487 from 1986-01 | +0.68 | 0.010 | G12 cyclicals Nov-Apr / defensives May-Oct |
| long | family | CA | all | 244 | +0.86 | 0.50 | +4.24 | -2.30 | +0.78 | 0.03 | 475 from 1987-01 | +0.93 | 0.001 | G22 buyhold cyclicals(4 Fid) never rebalanced |
| long | family | CA | full_hist | 243 | +0.93 | 0.50 | +4.21 | -2.32 | +0.64 | 0.12 | 487 from 1986-01 | -1.36 | 0.000 | G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 |
| long | family | NONE | all | 369 | -1.00 | 0.33 | +8.52 | +0.31 | -1.12 | 0.34 | 475 from 1987-01 | +0.63 | 0.002 | G12 cyclicals Nov-Apr / defensives May-Oct |
| long | family | NONE | full_hist | 368 | -1.00 | 0.33 | +8.52 | +0.30 | -1.26 | 0.32 | 487 from 1986-01 | +0.44 | 0.001 | G12 cyclicals Nov-Apr / defensives May-Oct |
| long | sector | CA | all | 11 | +2.33 | 0.67 | +3.36 | +0.52 | +0.21 | 0.03 | 487 from 1986-01 | +0.01 | 0.020 | G19 cyclicals(Fid) Nov-Apr / VFINX TAX gb=0.01 |
| long | sector | NONE | all | 136 | +4.78 | 0.67 | +5.95 | +2.07 | +1.74 | 0.18 | 487 from 1986-01 | +2.22 | 0.814 | G12 cyclicals Nov-Apr / defensives May-Oct |


`report.diagnostics` passes `step_quarters=4` to the walk-forward, which steps four entries of the
protocol's start list. On the yearly `screen` and `long_screen` protocols that means one decision
every 4 years, only 3-4 in total (see the lab bug note). The table below re-runs the same
walk-forward with a decision every year (`metrics.walk_forward(..., step_quarters=1)`, script
`wf_yearly.py`):

| era | set | regime | n | WF10/5 decisions | OOS mean | OOS beat | IS mean | avg config OOS | WF5/3 decisions | OOS mean | OOS beat |
|---|---|---|---|---|---|---|---|---|---|---|---|
| etf | core | CA | 262 | 12 | -2.97 | 0.17 | +4.81 | -6.16 | 19 | -1.51 | 0.42 |
| etf | core | NONE | 262 | 12 | -3.41 | 0.25 | +7.88 | -5.32 | 19 | -2.66 | 0.37 |
| etf | family | CA | 364 | 12 | -2.97 | 0.17 | +4.81 | -5.15 | 19 | -0.28 | 0.47 |
| etf | family | NONE | 458 | 12 | -3.90 | 0.25 | +7.92 | -3.40 | 19 | -2.52 | 0.32 |
| etf | sector | CA | 70 | 12 | -0.57 | 0.50 | +1.71 | -3.17 | 19 | -0.93 | 0.37 |
| etf | sector | NONE | 151 | 12 | -1.22 | 0.42 | +4.11 | -0.41 | 19 | -0.39 | 0.42 |
| long | core | CA | 235 | 26 | -1.62 | 0.27 | +3.70 | -3.26 | 33 | -2.89 | 0.12 |
| long | core | NONE | 235 | 26 | -0.32 | 0.42 | +8.39 | -1.73 | 33 | -1.26 | 0.33 |
| long | family | CA | 244 | 26 | -0.43 | 0.42 | +4.43 | -3.13 | 33 | -1.13 | 0.27 |
| long | family | NONE | 369 | 26 | -0.02 | 0.50 | +8.48 | -0.60 | 33 | -1.29 | 0.33 |
| long | sector | CA | 11 | 26 | +1.86 | 0.69 | +3.12 | -0.12 | 33 | +1.10 | 0.64 |
| long | sector | NONE | 136 | 26 | +3.73 | 0.81 | +6.01 | +1.39 | 33 | +1.33 | 0.61 |


Chosen each year, `etf/sector/CA` (10/5): 2010: G19 XLB only Nov-Apr / SPY May-Oct (OOS -4.89); 2011: G19 control XLY+XLI+XLB all year (OOS -1.00); 2012: G19 XLB only Nov-Apr / SPY May-Oct (OOS -3.20); 2013: G19 control XLY+XLI+XLB all year (OOS +0.04); 2014: G19 control XLY+XLI+XLB all year (OOS -1.24); 2015: G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 (OOS +0.88); 2016: G19 control cyclicals(4) all year (OOS +1.95); 2017: G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 (OOS +1.23); 2018: G19 cyclicals Oct1-May1 / SPY TAX gb=0.01 (OOS +0.63); 2019: G19 control cyclicals(4) all year (OOS +1.13); 2020: G19 control cyclicals(4) all year (OOS -0.30); 2021: G19 cyclicals Nov-Apr / SPY TAX gb=0.01 (OOS -2.01)


Chosen each year, `etf/sector/NONE` (10/5): 2010: G19 XLB only Nov-Apr / SPY May-Oct (OOS -2.72); 2011: G19 XLB only Nov-Apr / SPY May-Oct (OOS -2.39); 2012: G19 XLB only Nov-Apr / SPY May-Oct (OOS +0.13); 2013: G12 cyclicals Nov-Apr / defensives May-Oct (OOS -2.30); 2014: G12 cyclicals Nov-Apr / defensives May-Oct (OOS +0.80); 2015: G12 cyclicals Nov-Apr / defensives May-Oct (OOS +1.99); 2016: G12 cyclicals Nov-Apr / defensives May-Oct (OOS +0.39); 2017: G12 cyclicals Nov-Apr / defensives May-Oct (OOS -0.31); 2018: G12 cyclicals Nov-Apr / defensives May-Oct (OOS +0.41); 2019: G19 XLY only Nov-Apr / SPY May-Oct (OOS -3.25); 2020: G19 XLY only Nov-Apr / SPY May-Oct (OOS -2.68); 2021: G19 XLY only Nov-Apr / SPY May-Oct (OOS -4.69)


**Reading the diagnostics:**
* **ETF era (2000-2026): item 4 fails for the whole family and for the sector sub-family.** Choosing
  the config with the best trailing 10 years and holding it for 5 loses to SPY in every set and regime.
  With yearly decisions (12) the whole family loses 2.97 pp/yr in CA (beat 0.17) and 3.90 in NONE.
  Inside the sector-season sub-family it loses 0.57 (CA) and 1.22 (NONE).
  * The trailing winners are configs that fitted the previous decade and then mean-reverted: the
    presidential cycle with long Treasuries (chosen 2010-12, -6.6 to -9.2 pp out of sample), the Santa
    barometer (2013-18) and leveraged UPRO/SSO (2019-21).
  * In the CA sector sub-family, the selection picked the tax-managed cyclical season or the static
    cyclical basket from 2015 on. Those choices made +0.6 to +2.0 pp for 2015-19 starts, but the
    2020 start lost 0.3 pp/yr and the 2021 start lost 2.0 pp/yr.
* **Long history (1986-2026): the family's selection is about zero, and the sector sub-family's is
  positive.** With 26 yearly decisions the family gets NONE -0.02 and CA -0.43 pp/yr, and the sector
  sub-family NONE +3.73 and CA +1.86.
  * The sub-family's gains come from 1996-2008 decisions: cyclicals in winter, plus the Fidelity
    health / staples / utilities funds in summer, at +0.7 to +15 pp/yr.
  * Decisions from 2009 on are flat to negative (-1.7 to +1.8 pp/yr), the post-publication pattern
    again.
  * In CA almost all its choices are static all-year baskets.
* **PBO and DSR.** PBO is below 0.5 in most sets (0.03-0.48), but 0.65 for the full-history ETF-era
  NONE family. The deflated Sharpe ratio of each set's best config is at most 0.27 (0.81 for the
  long-era NONE sector sub-family), all below the 0.95 a robust edge would show. The `all` rows for the
  ETF-era core and family sets use only months from 2010-01, because the UPRO configs start then (199
  of 319 months; see lab bugs). The `full_hist` rows use all 319.

## Concerns and caveats

* **Multiple testing.** The family ran 493 ETF-era and 369 long-era configs. The best of that many
  will look good by chance. The deflated Sharpe ratio of each set's best config is at most 0.27, except
  0.81 for the long-era NONE sector sub-family. Walk-forward selection, which simulates "pick the best
  config so far", loses out of sample in both regimes in the ETF era and is about zero over 1986-2026.
* **The CA pass is a disguised static tilt.** Tax-managed execution turns the season switch into
  buy-and-hold of the cyclical basket after the first gains. Its boot_p (0.025) is computed on one path,
  the 2000-01 start, which happened to sell XLK in May 2000 and harvest losses through 2000-02. The
  never-rebalanced basket, whose 2000-01 path rode XLK down, has a higher score but boot_p 0.287. The
  candidate's edge is 2000-10 (+1.90 pp), with nothing since 2010. It needs XLK, which averages 27% of
  the portfolio since 2010. The same concentration in growth and tech is the incumbent preset's main risk.
* **The long-history proxies are narrow, actively managed funds.** The Fidelity Select funds standing
  in for the cyclical sectors are Retailing (FSRPX), Defense & Aerospace (FSDAX), Materials (FSDPX) and
  Technology (FSPTX). They are not broad sector indexes: they carry fees, and their historical sales
  loads or short-term redemption fees (where they applied) are not modelled. So costs before 2000 are
  understated for switching rules. Their buy-and-hold beats VFINX by 2-3 pp/yr in 1986-2026, so part of
  every long-history sector result is fund selection. FSDPX starts in 1986-09, so in 1986 the cyclical
  basket is only 75% invested (CalSignal configs) or the window starts late (buy-and-hold).
* **Long-Treasury safe asset.** The `safe=long` Halloween variants (the best G1/G8 configs in NONE) hold
  VUSTX half the year through a 1986-2020 bond bull market, so they are partly a duration bet. Bond
  interest is taxed as deferred capital gains in the engine (PROTOCOL 5.5), which flatters them in CA,
  and they lose in CA anyway.
* **The engine lends the annual tax bill at 0%.** It pays each January's tax from cash even when fully
  invested, so cash goes negative until the next sale (avg cash -1.3% for the standard sector-season
  rule in CA). This flatters taxable switching rules slightly and does not change any negative CA
  verdict. The CA candidate is unaffected (avg cash +0.02%). `CalSignal(cover_tax=True)` implements the
  stricter version but was not needed.
* **Hindsight in the sector-season literature.** The cyclical/defensive split is textbook. But the
  "Halloween effect is strongest in cyclical sectors" finding (e.g. Jacobsen & Visaltanachoti 2009)
  used US data through the mid-2000s. So the pre-2000 holdout is not out of sample for the published
  idea, only for ideas designed on ETF-era data. Only windows after roughly 2009 are post-publication,
  and there the rule is weaker: 2010-20 +0.77, 2020-26 -0.22 pp in NONE.
* **Screen granularity.** `screen` has only 12 fifteen-year windows, so its ex15_beat is coarse. Verdicts
  rest on `full` and `long`.

## Conclusion

Calendar and seasonality strategies do not answer the user's question. We built 493 ETF-era and 369
long-history configs, including tax-managed versions. In a taxable California account each of them
falls into one of two cases:
* it loses to SPY: the median CA score is -3.5 pp/yr, and turn-of-month-style rules lose 7-10 pp/yr;
* tax management stops it trading, and it becomes a static sector tilt whose CA edge depends on
  technology and on the 2000-10 decade.

None clears the protocol's good-confidence bar. The family-level selection test (item 4) fails in
both regimes in the ETF era. Over 1986-2026 it is about zero: CA -0.43 and NONE -0.02 pp/yr with
yearly decisions, or +0.86 and -1.00 with `report.diagnostics`' 4-year steps.

What to take away:
1. **In a taxable account, do not time the market by the calendar.** That covers Sell-in-May /
   Halloween, turn-of-month, holiday, Monday, barometer, presidential-cycle and options-expiry rules.
   They turn deferred long-term gains into yearly short-term gains, and most of them also lose before
   tax since 2000.
2. **The one calendar pattern with lasting evidence is not a reliable way to beat SPY.** That pattern
   is that cyclical sectors beat the index in Nov-Apr and lag in May-Oct. It holds over 1986-2026, and
   on random menus the winter-only basket beats the same basket held all year. But it fails the
   walk-forward test, depends on which basket is chosen, has weakened since publication (2020-26
   negative) and only works in a tax-deferred account.
3. **The best CA config from this family is really a buy-and-hold sector tilt.** That config is
   `G19 cyclicals Nov-Apr / SPY TAX gb=0.01`: score +0.64, full_excess +1.18, ex10_beat 0.84,
   ex15_beat 0.91, boot_p 0.025. It fails items 4 and 6, and its fresh-start 2021-26 window lost
   2.0 pp/yr. In substance it holds the cyclical sectors, about a quarter in tech, and rarely trades.
   If the lead wants that bet, the never-rebalanced four-SPDR basket expresses it more simply (CA
   score +1.21, every 10-year window positive, boot_p 0.29). It should be judged with the sector and
   factor families, not credited to seasonality.

**Recommendation: carry nothing from this family forward as a "beat SPY with confidence" strategy.**
