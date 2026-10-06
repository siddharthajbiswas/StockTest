# Family `tax_structures` — pure tax structures (no return forecasting)

Module: `research/lab/families/tax_structures.py` (kind `tax_structures.slots`). Scripts, logs
and intermediate tables: `research/lab/scratch/tax_structures/` (`grid.py`, `grid2.py`,
`grid3.py`, `fin.py`, `fin_long.py`, `battery.py`, `harvest_value.py`, `hv_run.py`, `an*.py`).
Every run, every regime and protocol: `research/lab/results/tax_structures_table.csv`
(`report.table` columns + `protocol`, `group`, the decomposition below, and the exact config).

All numbers are the engine's (= the site's) unless explicitly labelled **OUTSIDE-ENGINE
ARITHMETIC**. Excess is after-tax CAGR minus SPY buy-and-hold's in the same regime
(0.0100 = 1 pp/yr). Bootstrap p-values use `metrics.summary`'s default 1,000 resamples, as
`report.table` does.

## Verdict

**No pure tax structure beats buying and holding SPY after California tax (or federal tax) with
good confidence, and in this engine none can.** SPY buy-and-hold already defers 100% of its gain
to the end and pays the long-term rate once. The engine pools losses, has no $3,000 offset and
taxes everything at the final liquidation, so any strategy's total tax is at least the long-term
rate on its total gain. **A tax structure can only lose tax efficiency relative to SPY, never gain
it.** We measure that directly. For every window we split the CA excess into

* **mapped**: the pre-tax excess of the very same trades (ZERO regime: tax accounting on, 0%
  rates), taxed as if perfectly deferred, the way SPY is; and
* **gap**: the real after-tax result minus that perfectly-deferred value. Gap ≤ 0 by construction.

Across 511 decomposed records (every config with a ZERO twin, CA and FED), no harvesting or tax-aware
structure has a gap above +0.00004. The only larger positive gaps (largest +0.0001 score / +0.0012 on
the full window) are tax-blind band rules, whose CA and ZERO runs trade differently. So **the
after-tax "alpha" of tax management alone, holding market-like exposure, is 0.00 pp/yr in the
engine**. What remains is tracking noise of the substitute funds:

| structure (CA, full protocol 2000-2026, 95 start dates) | score | full excess | gap (score) | 10-yr beat | boot p |
|---|---|---|---|---|---|
| SPY + harvest 10% (daily checks) into IWB/VTI/VV/... | +0.0002 | +0.0010 | -0.0000 | 0.33 | 0.33 |
| SPY + harvest 15% (monthly checks): best of 102 harvest configs | +0.0015 | +0.0020 | -0.0000 | 0.46 | 0.21 |
| SPY replica from 11 sector SPDRs + harvest 5% (weekly) | +0.0019 | -0.0022 | -0.0000 | 0.81 | 0.67 |
| 9 sector SPDRs equal weight, rebalanced only through losses | +0.0023 | +0.0060 | -0.0000 | 0.49 | 0.30 |
| same + harvest 10% into iShares/Vanguard sectors (best pure structure) | +0.0026 | +0.0051 | -0.0000 | 0.49 | 0.29 |
| incumbent's 22-ETF menu, equal weight, rebalanced only through losses | +0.0010 | +0.0053 | -0.0000 | 0.49 | 0.26 |

None passes PROTOCOL §3 criteria 1-3, in CA or FED. The family's walk-forward selection is
negative out of sample (−1.17 pp/yr on the screen, −0.93 on the finalists) and PBO is 0.61 / 0.78.

What tax management *is* worth is defensive. It removes drag that trading creates, and that drag is large:

* **Static allocations**: tax-blind quarterly rebalancing costs 0.05–0.22 pp/yr of gap. Rebalancing
  only through losses costs 0.00. On 30 random 15–25-ETF menus it beat tax-blind rebalancing **in
  30 of 30** (+0.45 pp/yr including trading costs). It still lost to SPY on every menu (mean
  −1.35 pp/yr): the allocation decides, the structure only stops the leak.
* **The incumbent's rule** (site TaxManagedCombo, 1% budget), applied to **random** rankings of
  the same 22 ETFs: −0.22 pp/yr vs SPY (screen, 20 seeds; −0.28 on the full protocol, 8 seeds,
  all negative). The same random picks rotated with the site's standard rule lose −2.96 pp/yr
  (gap −2.33). So **the structure is worth +2.7 pp/yr against tax-blind rotation and nothing
  against SPY.** The incumbent's +0.66 is momentum's pre-tax edge (+0.77 mapped) carried through
  a nearly tax-free structure (gap −0.11). Momentum ranks above all 20 random seeds (z = 4.1).

**Harvesting losses on SPY itself buys exactly nothing in this engine.** Across the 33 SPY-core
harvesting configs without swap-back (of 102 harvesting configs), the gap is −0.000014 on average
(max |gap| 0.00004). The harvested losses (on average 15–23% of starting capital per window) sit in
the carryforward until the final liquidation. There they offset exactly the extra gain the lower basis created. Outside
the engine they would be worth something. OUTSIDE-ENGINE ARITHMETIC on the same trades (CA, 5–10%
thresholds):

* about **+0.2 pp/yr** if each year's net loss offsets other long-term gains (+0.4 over 10-year
  windows, +0.5 to +0.9 if the other gains are short-term);
* **+0.2 pp/yr** (+0.35 over 10-year windows) from the $3,000 ordinary-income offset on a $100k
  account, **≈0 on $1M**;
* **+0.3 to +0.8 pp/yr** if the deferred gain is never taxed (stepped-up basis or donation).

The value comes almost entirely from windows that start just before a bear market (2000–2009).
Of the SPY 10-year windows starting 2010–2016, at a 10% threshold only the 2011 start harvested
anything (11% of capital); at 5%, 0–11% of capital.

**Best pure-structure strategy:** the 9 original Select Sector SPDRs, equal weight, rebalanced
quarterly only through losses. On the site this is manual mode with the 9 tickers, trade rule
tax-managed, gain budget 0. CA full protocol: score +0.0023, full excess +0.0060, 10/15-year beat
0.49/0.57, boot p 0.30; FED +0.0026, boot p 0.30. **It does not pass.** Its edge is not tax (gap
0.0000). It is an equal-weight-sector tilt, and all of it was earned in windows that start between
2000 and 2004 (the tech crash and its aftermath):

* restricted to windows from late 2004 it loses −0.38 pp/yr;
* dropping XLK turns it negative (−0.14);
* the same structure on iShares or Vanguard sector funds loses (−0.06 / −0.26).

A long-history proxy built from Fidelity Select sector funds (actively managed) *does* clear
criteria 1–3 from 1986: CA +0.0149, boot p 0.052, pre-2000 10-year holdout +0.60 pp, 79% of
windows beaten. That is conflicting evidence on different instruments, not confirmation.

## 1. The mechanism, quantified

Engine facts (`backtester/engine.py`, `backtester/tax.py`):

1. Realized losses are pooled with the carryforward and applied against short-term gains first,
   then long-term.
2. There is no $3,000 ordinary-income offset and no outside gains.
3. Every window ends with a full liquidation that taxes all unrealized gains net of the
   carryforward.
4. Prices are total-return, so dividends are deferred for everyone, SPY included.

So total tax ≥ t_LT × max(total gain, 0), with equality only if no gain is ever taxed at the
short-term rate, no loss is wasted and nothing is taxed before the end. Paying earlier also loses
compounding. SPY buy-and-hold attains the bound, so after-tax excess = mapped + gap with gap ≤ 0.
`scratch/tax_structures/an.py::decompose` computes both terms window by window from each config's
CA (or FED) record and its ZERO twin (same decisions, 0% rates).

Measured gaps (screen, CA, mean over 5/10/15-year windows, pp/yr):

| execution rule | 22-ETF menu EW | 9 sectors EW | US size mix 80/12/8 | global 60/30/10 |
|---|---|---|---|---|
| never sell (drift) | 0.000 | 0.000 | 0.000 | 0.000 |
| rebalance quarterly only through losses (tax rule, budget 0) | -0.001 | -0.001 | 0.000 | 0.000 |
| same + harvest 10% into different-index twins | -0.001 | -0.002 | 0.000 | -0.007 |
| tax rule, budget 0.5%/yr | -0.048 | -0.031 | -0.033 | -0.035 |
| tax rule, budget 1%/yr (the site's default) | -0.083 | -0.063 | -0.048 | -0.067 |
| tax rule 1% + harvest 10% | -0.020 | -0.024 | -0.021 | -0.029 |
| tax rule 1%, no short-term gains | -0.065 | -0.045 | -0.045 | -0.057 |
| tax rule, budget 2% | -0.131 | -0.122 | -0.053 | -0.094 |
| tax rule, budget 5% | -0.176 | -0.152 | -0.054 | -0.101 |
| tax-blind quarterly | -0.181 | -0.158 | -0.054 | -0.101 |
| tax-blind annual | -0.145 | -0.185 | -0.028 | -0.083 |
| tax-blind, 5-pt band checked monthly | +0.011 | -0.014 | -0.001 | -0.028 |
| tax-blind, 2-pt band checked monthly | -0.020 | -0.087 | -0.012 | -0.064 |

(Long history, 1986+: 21-fund long menu tax-blind quarterly −0.29 pp/yr, losses-only 0.00; Fidelity
sector proxy tax-blind quarterly −0.32 / −0.33, losses-only 0.00.) Harvesting has genuine
in-engine value only in the row where it offsets gains the strategy realizes anyway (budget 1% →
gap cut from −0.05…−0.10 to −0.02…−0.03).

**Caveat on the two band rows:** my band rule skips in-band slots for buys as well as sells. Sale
proceeds can therefore sit idle: average cash is 1–8% for the band configs, versus about 0% for every
other rule. Treat those two rows (and their CA scores) as unreliable. They are a side variant; fixing
them would have invalidated every cached result of this family.

## 2. What was tested (461 designed configurations + 14 battery timing variants = 475; 1,421 backtest records)

| group | what | configs | protocol × regimes |
|---|---|---|---|
| A0 | controls: SPY slot (= benchmark, excess exactly 0) and buy-and-hold of each substitute (VTI, IWB, IWV, VV, VTSMX) | 6 | screen × CA/NONE/ZERO |
| A1 | SPY core + harvest, chain SPY→IWB→VTI→VV→SCHX→IWV→SCHB: threshold 3/5/8/10/15/20% × check D/W/M × swap-back none/any/loss/lt | 72 | screen × CA/NONE/ZERO |
| A2 | other chains (large-cap only, total-market only, SPY↔IWB, SPY↔VTI, SPY→VTSMX→IWB) × 5/10/20% × swap-back none/loss | 30 | screen × CA/NONE/ZERO |
| B | sector direct indexing: 11 SPDR sector chains (→ iShares IY* → Vanguard V*) at SPY-replica (NNLS fit) or equal weights; drift, yearly re-fit within a gain budget, losses-only or budgeted rebalancing; harvest 5–20% D/W, swap-back | 33 | screen × CA/NONE/ZERO |
| C | static allocations (22-ETF menu EW with/without requiring EEM+RSP, 9 sectors EW, SPY/MDY/IJR 80/12/8, SPY/EFA/EEM 60/30/10) × 15 execution rules; plus the site's manual-mode combos | 81 | screen × CA/NONE/ZERO |
| F | site TaxManagedCombo 1% and 0% and standard Combo on random rankings (20 seeds) vs momentum 12-1 (incumbent menu, top 5, Q) | 63 | screen × CA/NONE/ZERO |
| H | hindsight: 30 random 15–25-fund menus from `BROAD_EQUITY_POOL_2003` × drift / tax-blind Q / losses-only / 1% budget | 120 | screen × CA/ZERO |
| L, L2 | long-history proxies (VFINX↔VTSMX harvesting, VFINX/VEXMX 80/20, 21-fund long menu, Fidelity Select sector proxy) | 21 | long_screen × CA/NONE/ZERO |
| N, O, I | robustness of the best structure: cadence, threshold, leave-one-sector-out, iShares/Vanguard sector families, later windows | 23 | screen × CA/NONE/ZERO |
| FIN | 21 finalists | 21 | full × CA/FED/NONE/ZERO |
| FIN-ctrl | random-ranking controls (8 seeds site rule, 2 seeds standard) | 10 | full × CA/ZERO |
| FIN-long | long proxies of the candidates | 5 | long × CA/FED/NONE/ZERO |
| X | rebalance-date offsets of the best structure (6 offsets × 2 configs) | 12 | full × CA/NONE |

ZERO is the lab regime registered in `families/variants.py`: tax accounting on, 0% rates, so
tax-aware rules make the same decisions as in CA. In NONE the engine keeps no lots, so harvesting
never fires and tax-aware rebalancing behaves like tax-blind rebalancing (what one would do in an
IRA). NONE results for the harvesting groups are therefore SPY buy-and-hold (excess 0); they are
a check, not a finding.

## 3. Results by question

### (a) SPY core + tax-loss harvesting into different-index substitutes

* **102 configs, CA screen score −0.0036 … +0.0015 (mean −0.0004; 34% positive; lowest boot p
  0.127; none passes).**
* Without swap-back the gap is −0.000014 on average. The excess is the pre-tax tracking of
  whatever substitute the portfolio ends up in. Compare holding the substitute outright (screen
  CA score):

  | buy-and-hold | score |
  |---|---|
  | VTI | +0.0014 |
  | VV | +0.0014 |
  | VTSMX | +0.0013 |
  | IWB | +0.0007 |
  | IWV | −0.0003 |

  The "best" harvesting configs (15–20% thresholds, +0.0012 to +0.0015) harvested twice or
  three times in 2001–02 or 2008 and then sat in VTI or IWB. For example, the 15% monthly config
  from 2000: SPY → IWB (2001-04) → VTI (2002-08), then held to 2026; from 2005: SPY → IWB
  (2008-12).
* Thresholds: lower thresholds trade more and score slightly worse (mix chain, mean of D/W/M):

  | threshold | score | turnover/yr |
  |---|---|---|
  | 3% | +0.0003 | 0.135 |
  | 5% | 0.0000 | 0.105 |
  | 10% | +0.0007 | 0.051 |
  | 20% | +0.0013 | 0.022 |

  All of this is noise around zero.
* Check cadence (no swap-back): daily +0.0002 (21), weekly +0.0007 (6), monthly +0.0009 (6).
* (d) Swap back to SPY after 31 days:
  * "loss" (only when that is another loss): gap −0.00001, score −0.0002;
  * "any" (realizes short-term gains): gap −0.00017, score −0.0015;
  * "lt": gap −0.00056, score −0.0010.

  Swapping back only adds trades.
* Full protocol (finalists): score / full excess, CA:

  | config | score | full excess |
  |---|---|---|
  | 10% daily | +0.0002 | +0.0010 |
  | 15% monthly | +0.0015 | +0.0020 |
  | 5% daily | −0.0001 | −0.0009 |
  | 5% daily + swap back on loss | −0.0002 | +0.0012 |
  | large-cap chain 10% | −0.0003 | −0.0003 |
  | VTSMX chain 20% | +0.0010 | +0.0017 |

  FED is identical to ±0.0001; gap −0.0000 in all.
* Long history (1986+, benchmark VFINX), VFINX↔VTSMX at 10%: score +0.0005, full −0.0000,
  pre-2000 holdout 0.0000. VTSMX exists only from 1992, and from most starts no 10% loss below
  basis ever occurred.

**OUTSIDE-ENGINE ARITHMETIC: what the harvested losses would be worth**
(`harvest_value.py`). The exact engine run is replayed and its taxes are re-settled under
alternative rules. Differences go to a side account invested in SPY, taxed long-term at the end.
Means over the 24 yearly starts to 2026-07 / over the 17 ten-year windows; CA:

| config | net losses harvested (× start capital) | engine | B: offsets other LT gains | B_st: other ST gains | C: $3k/yr, $100k acct | C: $3k/yr, $1M acct | D: stepped-up basis |
|---|---|---|---|---|---|---|---|
| SPY 5% daily | 0.19 / 0.23 | −0.0012 / +0.0002 | +0.0020 / +0.0038 | +0.0049 / +0.0090 | +0.0019 / +0.0036 | −0.0007 / +0.0006 | +0.0032 / +0.0081 |
| SPY 10% daily | 0.18 / 0.21 | −0.0007 / +0.0005 | +0.0022 / +0.0038 | +0.0049 / +0.0086 | +0.0020 / +0.0035 | −0.0004 / +0.0009 | +0.0033 / +0.0079 |
| SPY 20% daily | 0.15 / 0.18 | −0.0002 / +0.0013 | +0.0021 / +0.0041 | +0.0043 / +0.0081 | +0.0020 / +0.0039 | +0.0001 / +0.0016 | +0.0031 / +0.0077 |
| sector replica 10% daily | 0.23 / 0.26 | +0.0012 / +0.0010 | +0.0045 / +0.0045 | +0.0077 / +0.0100 | +0.0048 / +0.0048 | +0.0017 / +0.0015 | +0.0060 / +0.0094 |

(Per-start rows: `scratch/tax_structures/hv_*_CA_*.csv`.) FED: SPY 10% daily B +0.0009 /
+0.0025, C100k +0.0016 / +0.0036, D +0.0014 / +0.0046. Scenario B assumes enough outside gains to
absorb every year's loss — including 2001–02 and 2008, when an investor's other holdings were
probably losing too — so it is an upper bound. The per-start detail (`hv_spy_mix_h10D_CA_10y.csv`)
shows the value comes from windows that begin before a bear market. At a 10% threshold, 10-year
windows starting 2010 and 2012–2016 harvested nothing.

### (b) Sector "direct indexing"

* 33 configs, CA screen −0.0004 … +0.0022 (94% positive, lowest boot p 0.106, none passes).
  Gap −0.0000 for drift and losses-only versions.
* The SPY replica (non-negative least squares of SPY's trailing 252-day returns on the live SPDR
  sectors, bought once and left to drift) tracks SPY with ~4.4%/yr tracking error. It lags badly
  after 2018: XLC took GOOGL/META out of XLK/XLY, the drift portfolio never owned XLC, and the
  sector funds' capping rules matter. Full protocol CA: score +0.0017, full −0.0021, 10/15-year
  beat 0.72/0.79, boot p 0.62.
* Harvesting into iShares/Vanguard sector twins harvests more than SPY-level harvesting (23–27% of
  start capital) and is worth nothing in the engine. Fit-drift without harvest +0.0013 vs mean
  +0.0009 over 16 harvest variants on the screen. Full: 10% daily +0.0013, 5% weekly +0.0019.
  OUTSIDE-ENGINE (B) about +0.45 pp/yr.
* Yearly re-fit within a 1% budget + 10% harvest: full CA score +0.0009, full +0.0060, 10/15-year
  beat 0.78/0.68, boot p 0.106 (FED boot p 0.090). It passes criterion 3 in FED but fails criterion 2
  (15-year beat 0.70), and its score is small.

### (c)/(e) Static allocations: never-sell, losses-only, gain budgets, bands

The gap table in §1 is the answer. In CA:

| allocation | best CA score | under which rule | standard quarterly |
|---|---|---|---|
| 22-ETF menu EW | +0.0015 | losses-only | −0.0017 |
| same, windows from 2004 (requires EEM+RSP) | −0.0045 | drift | −0.0088 |
| 9 sectors EW | +0.0030 | losses-only + harvest | +0.0011 |
| US size mix | +0.0007 | drift | +0.0001 |
| global 60/30/10 | −0.0173 | drift | −0.0217 |

The rule moves results by 0.1–0.3 pp/yr; the allocation by 2 pp/yr. Larger gain budgets
monotonically cost more. A 1%/yr budget costs 0.05–0.10 pp/yr of gap, a 5% budget as much as
tax-blind rebalancing. Forbidding short-term gains helps a little (−0.065 vs −0.083 on the 22-ETF
menu). The band rows are unreliable; see the caveat in §1.

Site-expressible versions (manual mode, tax-managed) match the research kind:

| config | CA score | full excess |
|---|---|---|
| site manual, 9 sectors, budget 0 | +0.0023 | +0.0060 |
| research kind, 9 sectors, budget 0 | +0.0023 | +0.0060 |
| site manual, 22-ETF menu, budget 0 | +0.0009 | +0.0058 |

The site's manual standard mode never rebalances unless a fund launches, so it is effectively
"drift".

### (f) The incumbent's tax rule on random rankings vs momentum (what pure structure is worth)

Screen, 22-ETF menu, top 5, quarterly (20 random seeds):

| rule | random: CA score (sd, share > 0) | random: ZERO | momentum: CA | momentum: ZERO | CA gap random / momentum |
|---|---|---|---|---|---|
| site TaxManagedCombo 1% | −0.0022 (0.0021, 15%) | −0.0010 | +0.0064 (z = 4.1) | +0.0089 | −0.0012 / −0.0010 |
| site TaxManagedCombo 0% | −0.0003 (0.0030, 40%) | +0.0001 | +0.0067 | +0.0079 | −0.0002 / −0.0001 |
| site standard Combo | −0.0296 (0.0014, 0%) | −0.0072 | −0.0109 | +0.0026 | −0.0233 / −0.0126 |

Full protocol:

* random + site rule 1% (8 seeds): CA score mean −0.0028 (−0.0067 … −0.0008), full +0.0079;
* random + standard: −0.0303 / −0.0287.

Pure structure is worth +2.7 pp/yr against standard rotation of the same picks:

* the tax gap shrinks from −2.33 to −0.12;
* trading costs fall from ~305% to ~15% turnover per year;
* letting winners run adds a little.

It is worth −0.2 to −0.3 pp/yr against SPY. The incumbent's edge is momentum (+0.86 pp/yr over
random under the same rule) preserved by the structure.

The incumbent with a **0% budget** keeps the edge with almost no tax gap. Full CA: score +0.0064,
full +0.0146, 10/15-year beat 0.79/0.81, boot p 0.047; FED 0.0070, 0.79/0.81, 0.048. The incumbent
itself is at 0.70/0.83. It narrowly misses criterion 2 (15-year beat < 0.85). It uses a momentum
forecast, so it is not a pure structure and belongs to the tax_rotation family; it is reported
here because the budget is a structural knob.

### Hindsight checks (PROTOCOL 5.3)

* **Random menus** (30 menus of 15–25 ETFs from `BROAD_EQUITY_POOL_2003`, equal weight, windows
  once every fund exists, ≈2004+), CA screen:

  | rule | mean score | gap | menus with positive score |
  |---|---|---|---|
  | drift | −0.0134 | 0.000 | 0/30 |
  | tax-blind Q | −0.0180 | −0.0020 | 0/30 |
  | losses-only | −0.0135 | 0.000 | 0/30 |
  | 1% budget | −0.0162 | −0.0008 | 0/30 |

  Losses-only − tax-blind = +0.0045, positive in 30/30 menus. Losses-only − drift = −0.0001.
  None passes.
* **Remove the star** (9-sector structure, screen CA, base +0.0027):

  | dropped sector | score |
  |---|---|
  | XLB | +0.0038 |
  | XLE | +0.0040 |
  | XLF | +0.0056 |
  | XLI | +0.0028 |
  | XLK | **−0.0014** |
  | XLP | +0.0032 |
  | XLU | +0.0034 |
  | XLV | +0.0020 |
  | XLY | +0.0005 |

* **Other index families** for the same structure:

  | family (windows) | losses-only | drift | tax-blind |
  |---|---|---|---|
  | iShares IY* (from 2000-07) | −0.0006 | −0.0010 | −0.0027 |
  | Vanguard V* (from 2004-10) | −0.0026 | −0.0028 | −0.0053 |
  | the SPDRs on the same 2004-10+ windows | −0.0038 | −0.0041 | — |

* SPY-core harvesting: substitute chains varied (large-cap only, total market, single pairs,
  mutual fund); results stay within ±0.15 pp/yr of zero, gap 0.

### Long history (pre-2000 holdout, criterion 7)

Protocol `long` (quarterly starts 1986–2023, benchmark VFINX), CA:

| proxy | score | full | 10/15-year beat | boot p | ho5 (beat) | ho10 (beat) |
|---|---|---|---|---|---|---|
| VFINX↔VTSMX harvest 10% | +0.0005 | −0.0000 | 0.28 / 0.21 | 0.999 | 0.0000 (0.00) | 0.0000 (0.00) |
| Fidelity Select sector proxy (FSPTX, FIDSX, FSENX, FSPHX, FSUTX, FDFAX, FSRPX, FSDPX, FSDAX), EW, losses-only | +0.0149 | +0.0112 | 0.75 / 0.89 | 0.052 | +0.0078 (0.62) | +0.0060 (0.79) |
| same, never sold | +0.0149 | +0.0112 | 0.75 / 0.90 | 0.052 | +0.0079 (0.62) | +0.0057 (0.79) |
| same, tax-blind quarterly | +0.0132 | −0.0010 | 0.64 / 0.84 | 0.536 | +0.0043 | −0.0023 (0.14) |
| 21-fund long menu EW, losses-only | +0.0057 | +0.0028 | 0.58 / 0.75 | 0.338 | −0.0040 (0.46) | −0.0059 (0.29) |

FED, sector proxy losses-only: +0.0163, boot p 0.058.

The sector proxy passes criteria 1–3 in CA and FED from 1986. But:

* these are actively managed funds with narrower sector definitions (defense and aerospace for
  industrials, retailing for discretionary, food and agriculture for staples);
* the proxy list is the set of funds that survived to today;
* the real-ETF test of the same structure fails (10-year beat 0.49, boot p 0.30) and fails every
  robustness check above.

The pre-2000 holdout is positive, but the evidence disagrees with the ETF era, so it does not
rescue the candidate.

## 4. Finalists (protocol full, 95 quarterly starts 2000-01 … 2023-07)

CA / FED / NONE / ZERO; criteria 1–3 never all hold.

| finalist | CA score | CA full | CA 10y beat | CA 15y beat | CA boot p | CA gap | FED score | FED boot p | NONE score | ZERO score |
|---|---|---|---|---|---|---|---|---|---|---|
| A 10% daily | +0.0002 | +0.0010 | 0.33 | 0.34 | 0.329 | -0.0000 | +0.0002 | 0.346 | -0.0000 | +0.0003 |
| A 15% monthly | +0.0015 | +0.0020 | 0.46 | 0.60 | 0.214 | -0.0000 | +0.0016 | 0.208 | -0.0000 | +0.0018 |
| A 5% daily | -0.0001 | -0.0009 | 0.34 | 0.36 | 0.660 | -0.0000 | -0.0001 | 0.660 | -0.0000 | -0.0001 |
| A 5% daily, swap back on loss | -0.0002 | +0.0012 | 0.39 | 0.49 | 0.187 | -0.0000 | -0.0002 | 0.191 | -0.0000 | -0.0002 |
| A large-cap chain 10% | -0.0003 | -0.0003 | 0.25 | 0.34 | 0.716 | -0.0000 | -0.0003 | 0.733 | -0.0000 | -0.0003 |
| A VTSMX chain 20% | +0.0010 | +0.0017 | 0.37 | 0.47 | 0.193 | -0.0000 | +0.0011 | 0.186 | -0.0000 | +0.0012 |
| B replica, no harvest | +0.0017 | -0.0021 | 0.72 | 0.79 | 0.619 | -0.0000 | +0.0018 | 0.629 | +0.0019 | +0.0019 |
| B replica 10% daily | +0.0013 | -0.0023 | 0.64 | 0.74 | 0.662 | -0.0000 | +0.0014 | 0.660 | +0.0019 | +0.0015 |
| B replica 5% weekly | +0.0019 | -0.0022 | 0.81 | 0.81 | 0.668 | -0.0000 | +0.0021 | 0.671 | +0.0019 | +0.0022 |
| B replica, yearly re-fit 1% + 10% | +0.0009 | +0.0060 | 0.78 | 0.68 | 0.106 | -0.0002 | +0.0011 | 0.090 | -0.0005 | +0.0013 |
| C 9 sectors losses-only + 10% harvest | +0.0026 | +0.0051 | 0.49 | 0.57 | 0.288 | -0.0000 | +0.0030 | 0.267 | +0.0030 | +0.0034 |
| C 9 sectors losses-only | +0.0023 | +0.0060 | 0.49 | 0.57 | 0.301 | -0.0000 | +0.0026 | 0.296 | +0.0030 | +0.0030 |
| C 9 sectors never sold | +0.0019 | -0.0005 | 0.49 | 0.53 | 0.529 | -0.0000 | +0.0022 | 0.528 | +0.0025 | +0.0025 |
| C 9 sectors tax-blind Q | +0.0006 | +0.0027 | 0.49 | 0.51 | 0.418 | -0.0017 | +0.0016 | 0.324 | +0.0030 | +0.0030 |
| C 9 sectors budget 1% | +0.0011 | +0.0064 | 0.49 | 0.51 | 0.276 | -0.0006 | +0.0016 | 0.241 | +0.0030 | +0.0023 |
| C 22-ETF menu losses-only | +0.0010 | +0.0053 | 0.49 | 0.49 | 0.262 | -0.0000 | +0.0012 | 0.246 | -0.0001 | +0.0014 |
| C 22-ETF menu never sold | +0.0005 | +0.0013 | 0.51 | 0.45 | 0.459 | +0.0000 | +0.0006 | 0.459 | +0.0008 | +0.0008 |
| C site manual 9 sectors budget 0 | +0.0023 | +0.0060 | 0.49 | 0.55 | 0.299 | -0.0000 | +0.0026 | 0.295 | +0.0030 | +0.0030 |
| C site manual 22-ETF menu budget 0 | +0.0009 | +0.0058 | 0.49 | 0.51 | 0.249 | -0.0000 | +0.0011 | 0.233 | -0.0001 | +0.0014 |
| F incumbent (momentum, 1%) | +0.0066 | +0.0154 | 0.70 | 0.83 | 0.025 | -0.0011 | +0.0074 | 0.025 | +0.0014 | +0.0090 |
| F momentum, 0% budget | +0.0064 | +0.0146 | 0.79 | 0.81 | 0.047 | -0.0001 | +0.0070 | 0.048 | +0.0014 | +0.0076 |

(Exact per-regime statistics for every finalist: `scratch/tax_structures/fin_stats.json`; all rows
in the CSV with `protocol=full`.)

### Verification battery (`research.lab.verify`, n_trials = 470 for the deflated Sharpe)

**9 sector SPDRs EW, site manual mode, tax-managed, budget 0** (`battery_C_site_sect9_tm0.json`):

* Rebalance-date offsets (7, CA): score +0.22 … +0.25, all positive.
* Costs per side 0 / 15 / 35 bps: CA score +0.23 / +0.22 / +0.21.
* Stricter distribution-tax accounting (CA, from 2000 / 2005 / 2010 / 2015): +0.60 → +0.60,
  −0.30 → −0.29, −0.99 → −0.99, −1.39 → −1.40. Sector dividends ≈ SPY's, so no effect.
* Sub-periods, CA: 2000–10 **+3.13**, 2010–20 **−0.59**, 2020–26 **−1.75** pp/yr.
* Deflated Sharpe: CA 0.009, FED 0.010.

**Same + 10% harvest into iShares/Vanguard twins** (research kind, `battery_C_sect9_tax0_h10D.json`):

* Its timing offsets were run separately (group X): CA score +0.22 … +0.28 over 7 offsets, all
  positive; boot p 0.14–0.29.
* Costs 0 / 15 / 35 bps: CA +0.29 / +0.20 / +0.01. The harvest trades make it cost-sensitive.
* Realism: +0.51 → +0.55 from 2000.
* Sub-periods, CA: +2.66 / −0.80 / −1.44.
* Deflated Sharpe: CA 0.008.

The structure is robust to timing and costs, and stricter tax accounting does not change it. It is
just not an edge: it is one decade of equal-weight-sector outperformance (2000–10), followed by
16 years of underperformance.

**Incumbent with a 0% gain budget** (momentum signal; a structure knob, not a pure structure;
`battery_F_mom_tm0.json`; verify's own bootstrap uses 500 resamples, hence boot p 0.042 here vs
0.047 above):

* Offsets (7): CA score +0.47 … +0.79, all positive; full excess −0.42 … +1.67.
* Costs 0 / 15 / 35 bps: CA +0.70 / +0.38 / +0.51. The response is non-monotonic, i.e.
  path-dependent.
* Realism: from 2000 +1.46 → +1.51, from 2010 −0.15 → −0.08.
* Sub-periods, CA: +0.80 / −0.47 / +0.33.
* Deflated Sharpe (n = 470, this family's count only; the momentum search was larger): CA 0.049.

For comparison, the incumbent's own sub-periods are +1.20 / −0.55 / +0.19.


## 5. Diagnostics (`report.diagnostics`)

| set | regime | n | walk-forward 10y→5y OOS (beat; IS) | walk-forward 5y→3y OOS (beat) | PBO | DSR of best |
|---|---|---|---|---|---|---|
| screen, pure structures (A1+A2+B+C) | CA | 216 | −0.0117 (0.00; +0.0095) | +0.0018 (0.50) | 0.606 | 0.193 |
| same | NONE | 216 | −0.0133 (0.00; +0.0116) | +0.0034 (0.50) | 0.936 | 0.027 |
| screen, all incl. F controls | CA | 279 | −0.0223 (0.33; +0.0194) | −0.0212 (0.00) | 0.394 | 0.062 |
| same | NONE | 279 | −0.0148 (0.33; +0.0278) | +0.0100 (0.75) | 0.919 | 0.035 |
| screen, A only (harvesting) | CA | 102 | −0.0014 (0.00; +0.0031) | +0.0049 (0.50) | 0.636 | 0.276 |
| full, 19 pure-structure finalists | CA | 19 | −0.0093 (0.08; +0.0123) | −0.0005 (0.42) | 0.779 | 0.435 |
| same | FED | 19 | −0.0104 (0.08; +0.0138) | −0.0009 (0.42) | 0.782 | 0.456 |
| same | NONE | 19 | −0.0105 (0.25; +0.0139) | +0.0021 (0.47) | 0.554 | 0.228 |

Picking the best trailing structure reverses out of sample, as it should when the differences are
tilt and tracking noise. NONE diagnostics for the harvesting groups are degenerate: without lots
nothing is harvested, so every config is SPY.

## 6. Conclusion

1. **Tax management alone, holding market-like exposure, adds 0.00 pp/yr in the engine.** That is
   a structural fact, measured to four decimals: gap ≈ 0 for harvesting, ≤ 0 for everything.
   The best SPY-like structures are within ±0.2 pp/yr of SPY, with boot p ≥ 0.2.
2. Its real value is to stop tax leaks from trading. For a strategy that must trade, a
   losses-only or small-budget execution rule plus harvesting into different-index twins is
   worth +0.4 to +2.7 pp/yr versus tax-blind execution. The site's tax-managed rule already
   captures most of it; a 0% budget captures slightly more of the gap.
3. **Harvesting's value lives outside the engine.** About +0.2 to +0.4 pp/yr if losses can offset
   other gains, mostly in bear-market-starting windows. The $3k offset matters only for small
   accounts. Step-up/donation turns deferral into +0.3 to +0.8 pp/yr. The site cannot show any of
   this. If the user has other realized gains, harvesting the SPY core into VTI/IWB/VV is a cheap,
   low-risk addition, but it is not an engine-verifiable edge.
4. The best pure-structure strategy on the site (9 sector SPDRs, equal weight, losses-only) is a
   sector-breadth bet. It won in windows starting 2000–2004 and loses in windows starting from late
   2004 (−0.38 pp/yr). It is not a tax edge and not a confident winner.

## 7. Lab notes

* No lab bug found. Two engine simplifications matter for this family and are worth knowing:
  * Pooled losses offset short-term gains first. That is more generous than IRS netting when a
    long-term loss meets a short-term gain while long-term gains exist.
  * The January tax payment can drive cash negative (an interest-free loan) for strategies that
    realize gains without selling to raise cash. The site's TaxManagedCombo shows small negative
    cash; for example, the manual-mode standard combo on the 22-ETF menu reached −$4,533. My kind
    sells to cover (`cover_cash`, default on), so its `avg_cash` is ≥ 0.
* The ZERO regime (from `families/variants.py`) is what makes the decomposition possible. NONE
  cannot show a tax-aware rule's pre-tax behaviour because the engine keeps no lots there.
* FIFO-only lot relief means harvesting is position-level. Specific-lot identification, which real
  brokers offer, would harvest a little more, but the in-engine value would still be zero.
* The site's manual "standard" mode silently rebalances when a menu fund first launches (membership
  changes). Its drift portfolio is therefore not a pure buy-and-hold for menus with late launches.
