# r2_gap5: specific-lot (HIFO / min-tax) sales, exact budget sizing and IRS netting

Round 2, key `gap5`. Module `research/lab/families/r2_gap5.py` (kind `r2_gap5.x`, its own
engine subclass and runner); scripts, logs, CSV/JSON in `research/lab/scratch/r2_gap5/`.
Every number is the lab engine's (the website's engine, reproduced exactly), unless marked
"sim" (the lev_robust simulator, validated against the engine to 1e-6 of CAGR). "Excess" =
after-tax CAGR minus SPY buy-and-hold in the same regime and costs, in pp/yr. CA = 48.1% /
28.1% (primary), FED = 35% / 15%.

## Verdict

**Correcting the engine's tax accounting changes no verdict. Specific-lot (HIFO) sales do not
make any tax-managed rotation pass the bar.**

**Specific-lot sales (HIFO / min-tax).**
- They let the rotations sell 5-17% more dollars per dollar of realized gain.
- Most sales are full exits, where lot order cannot matter, so the effect is small.
- Averaged over 7 rebalance schedules, every finalist's score moves by −0.04 to +0.02 pp:
  KX3 +0.02, KX1 +0.01, the site preset −0.04.
- On the default dates:
  - the no-trim rules gain slightly: KX3 +0.99 → +1.02, KX1 +0.93 → +0.94;
  - the trimming rules lose: preset +0.66 → +0.38, INC-WS −0.11, B378-WS −0.06. That is path
    divergence (one changed rotation decision cascades), not a mechanism. Averaged over
    schedules it is −0.04 pp.
- Min-tax ≈ HIFO.

**No rotation passes with HIFO.**
- **Default dates:** the same rules clear criteria 1-3 as before (KX3, KX1, the B378 combo).
  B378-WS drops out (p 0.101).
- **Across schedules:** no rule clears them on a majority of schedules. The best is KX3, 3 of 7.
- **Pre-registered 50-rule HIFO grid:** it finds nothing new.
  - 15/50 rules clear 1-3, vs 14/50 under FIFO.
  - Walk-forward out of sample −0.83 pp; PBO 0.56.
  - Deflated Sharpe ≤ 0.03 at 12,050 trials.
  - Larger budgets do not start paying.
- **Hindsight and holdout tests** are unchanged to within 0.06 pp of score:
  - without QQQ/XLK: KX3 −0.26, KX1 +0.12;
  - 30 random menus: +0.39 / +0.42, 1/30 pass;
  - the pre-2000 holdout: KX3 10-year −0.06, KX1 −0.19.

**Exact budget sizing.**
- It removes the overshoot completely: 0 of 344 path-years over budget, vs 108 with the
  average-gain sizing (KX3 35 of 54, up to 1.33×).
- It has no systematic effect on the score (−0.04 to +0.00 pp).
- It reshuffles single paths: KX3's 2000 path goes +1.84 → +0.31 pp under FIFO, and back to
  +1.84 under HIFO.

**IRS character-preserving netting.**
- It gives identical yearly taxes on all 48 finalist histories: long-term loss carryforwards
  never meet taxable short-term gains.
- The engine's pooling is never less generous (proven, and checked on 200,000 cases), but the
  difference never binds here.
- What remains is the terminal liquidation, ≤ +0.02 pp.

**Wash sales.**
- Impossible for the rotations: zero exposure in every audit.
- The daily trend rules whipsaw into about one per 2000-2026 path (12-14 in 1930-2026),
  costing 0.02-0.04 pp.

**The trend rules.**
- The 2x SMA175/3% rule, the program's only surviving (CONDITIONAL) candidate, is unchanged in
  every history under IRS netting plus the wash rule:
  - CA +4.95, p 0.073 on 2000-26;
  - +4.64, p 0.068 on 1986-26;
  - +2.92, p 0.275 on the 1930-85 holdout.
- Lot choice cannot affect it.
- The 3x rule stays a FAIL (−88% drawdown in 1929-35).

**For an investor who runs a tax-managed rotation anyway:** specific-lot identification plus
exact sizing is free and makes the gain budget mean what it says. It does not change the
expected after-tax result.

## 1. What was built

The engine sells FIFO, sizes nothing, and nets losses in one pool. I added four research-only
options. None of them edits `backtester/` or the lab core. They are subclasses (`LotPortfolio`,
`XBacktest`, `XGate`) driven by the module's own runner, which is `sweep.run`'s twin: same
record format, so `metrics.summary`, `report.score` and the battery statistics apply unchanged.

| option | values | what it does |
|---|---|---|
| `lot` | `fifo` (engine), `hifo`, `mintax` | Which lots a sale consumes. `hifo` takes the highest cost basis first. `mintax` takes the lowest tax per share first: (net price − basis) × the lot's own ST/LT rate, so losses come first. |
| `size` | `avg` (engine and site), `exact` | The budget-limited partial gain sale. `avg` sells qty × room / gain, which assumes the average gain per share. `exact` counts shares lot by lot in the order the engine will really sell them, so the year lands on the budget. |
| `net` | `pooled` (engine), `irs`, `irs3k` | `pooled` is `compute_year_tax`, with the terminal tax in two steps. `irs` is Schedule D netting: ST with ST, LT with LT, then cross-netting. Carryforwards keep their character, and the terminal liquidation is one tax year. `irs3k` adds the $3,000/yr deduction of a net capital loss against ordinary income, at 44.3% (CA: 35% + 9.3%, no NIIT on wages) or 35% (FED). |
| `wash` | `none` (engine), `irs` | The IRS wash-sale rule. A loss lot is disallowed when replacement shares of the same ticker were bought within 30 days before (and are still held) or are bought within 30 days after. The loss moves into the replacement basis and the holding period is tacked on. A disallowance that reaches into a settled year is paid at once, as an amended return. |

Every strategy's own planner ("what would this sale realize?") reads lots in the engine's sale
order. That covers the gain/loss classification, the long-term-only test and the budget room.
The strategy and the engine therefore always agree. Wrapped kinds:
- `tax_rotation.ws` (KX3, KX1, B378-WS, INC-WS), with offsets and a 1-day lag;
- the site's `TaxManagedCombo` (the preset and B378-combo), with offsets;
- `weights` (the trend rules, the value/growth switch, the seasonal tilt).

**"REAL"** below means `lot=hifo, size=exact, net=irs`. That is what a taxable account at a
broker with specific-lot identification would actually get.

### Validation (all passed)

| check | result |
|---|---|
| **V1 identity.** All options at their defaults vs the lab's cached records. 8 finalists × CA/FED: every checkpoint of all 95 starts (5,605 per record, 89,680 values), the monthly series and the run stats. | max abs difference **0.0** (bit-identical) |
| **T1 netting.** `year_tax_irs` vs an independent transcription of Schedule D lines 7/15/16 and the IRS Capital Loss Carryover Worksheet (lines 1-13), on 200,000 random cases, with and without the $3k deduction. | max diff 7e-12. Pooled tax ≤ IRS tax in every case: the engine's pooling is never less generous. |
| **T1/T2 wash sales.** Scripted engine runs: after-side, before-side partial (400 + 200 replacement shares, basis +8.14/share, holding period tacked 61 days), an old lot (> 30 days) that is not a replacement, and a December loss rebought in January. | All as specified. The amended 2008 return pays exactly the LT gain × 28.1% that the disallowed loss had sheltered ($4,560.28). |
| **V2 exact sizing.** `fifo/exact` vs the round-1 verifier's independent `exact_budget` implementation (`verify_taxrot_mech.ws_x`). | Identical (max diff 0.0). KX3 +0.95 / +0.31 / p 0.40; KX1 +0.92 / +1.76 / 0.015. |
| **A1 planner = engine.** 120 instrumented runs: 6 tax-managed finalists × 3 lot methods × 2 sizings × starts 2000-01, 2007-07, 2015-04, plus the trend rules. | Predicted gain = booked gain for every planned sale, partial sales included (max error 7e-12). |
| **V3 simulator.** `simx` (lev_robust `sim.simulate` + netting / wash options) vs `sim.simulate` and vs the engine, for 2x/3x, 4 accounting variants, 2 checkpoints × every 12th start. | Defaults identical (0.0). vs the engine: max abs CAGR diff 9e-7 under every variant. |
| **V4 offsets.** My `offset_days` vs the lab's cached `ws_x` / `combo_x` offset records. | Identical (0.0). The lab's baseline offset records are reused as the FIFO baseline. |

## 2. Mechanics: when can lot choice matter at all?

Lot order matters only when a sale leaves part of a position:
- trims of names still wanted (the site preset, B378-WS, INC-WS);
- the budget-limited last exit of a rebalance;
- the January tax sale of the trend rules.

A full exit realizes every lot whatever the order. That bounds the whole effect. From the
instrumented runs (3 starts each, CA):

| finalist | budget years over 1% (2%) with fifo/avg (max ratio) | with exact sizing (any lot method) | $ sold per $ of gross realized gain, fifo/avg → hifo/exact | wash-exposed loss lots |
|---|---|---|---|---|
| KX3 | **35 of 54** (1.33×) | 0 of 54 | 4.1 → 4.8 (+17%) | 0 |
| KX1 | 28 of 56 (1.21×) | 0 | 3.5 → 4.0 (+15%) | 0 |
| site preset (INC) | 10 of 59 (1.18×) | 0 | 7.1 → 7.8 (+9%) | 0 |
| B378 combo | 2 of 58 (1.44×) | 0 | 5.8 → 6.2 (+6%) | 0 |
| B378-WS | 15 of 58 (1.12×) | 0 | 5.6 → 5.9 (+6%) | 0 |
| INC-WS | 18 of 59 (1.24×) | 0 | 7.5 → 7.9 (+5%) | 0 |

- **Exact sizing fixes the overshoot completely.** The round-1 finding (KX3 over budget in
  18 of 25 years from 2000) reproduces exactly under `fifo/avg`. HIFO with `avg` sizing
  undershoots instead: the first shares sold have the highest basis.
- **Specific-lot sales let a rotation sell 5-17% more dollars per dollar of realized gain.**
  That is the "turns over more for the same tax" effect. It is modest because most sales
  are full exits.
- **`mintax` ≈ `hifo`.** In these portfolios the highest-basis lots are almost always also the
  lowest-tax lots: long-term lots are the old low-basis ones. The two orders differ in a
  handful of sales.
- **No tax-managed rotation can trigger a wash sale under any lot method.** It trades only on
  quarterly or semiannual rebalance days and carries a 31-day forward guard. Zero loss lots
  had a same-ticker purchase within ±30 days. The guard's missing look-back side never binds.
- **The trend rules do trigger wash sales.** A whipsaw re-entry within 30 days does it. The
  engine's IRS rule disallows:
  - one material loss on the 2x path from 2000 (VFITX sold at a $40.2k loss on 2022-03-29,
    rebought 2022-04-22: $34.7k deferred);
  - two on the 3x path ($67.7k VFITX 2022; $39.2k of the 3x fund 2023-10-27 → 11-10).
  - In 1930-2026 (sim) it is 12-14 events per path.
- **The lot method cannot matter for the trend rules.** Each state holds one material lot.
  Results under `hifo` are identical to `fifo` (2x) or within 1e-9 (3x).

## 3. IRS netting: the gap does not bind for any finalist

**The rule difference.** Within a year, pooled and IRS netting are identical: a net loss of one
character offsets the other character's net gain under both. They differ only when a
**long-term** carryforward meets a year with **both** short- and long-term gains:
- the engine applies the LT carry to ST gains (saving 48.1%);
- the IRS applies it to LT gains first (28.1%);
- example: a $10k LT carry followed by $10k ST + $10k LT gains costs $2,000 more under IRS
  rules in CA.

**On the finalists' actual histories it never happens** (`n1_netting_static.csv`). I held each
finalist's realized gains fixed (starts 2000, 2007, 2015; CA and FED) and re-taxed them under
both rules:
- the settled taxes are **identical** for all 8 finalists in all 48 cases, with zero years
  differing;
- the rotations carry long-term losses for up to 14 years, but they realize almost no taxable
  short-term gains: net ST is negative on every path;
- the trend rules never carry a long-term loss: their losses come from whipsaws inside a year.

**What remains is the terminal liquidation.** The engine taxes this year's realized gains and
then the unrealized ones, in two steps. That is *less* generous than one combined tax year
when realized gains meet unrealized losses: the opposite direction from the critic's concern.
It moves the finalists by 0.00 to +0.02 pp.

## 4. The finalists under every option (protocol `full`, CA)

Score / full-period excess / mean to-the-end excess over all 95 starts (less path-dependent
than `full_excess`) / beat rates / bootstrap p / max drawdown. Bar 1-3 = PROTOCOL criteria 1-3.
Change vs the engine in brackets.

| finalist | accounting | score | full_excess | end_mean | ex10 / ex15 / ex20 beat | boot_p | max DD (SPY −55.2%) | trades | bar 1-3 |
|---|---|---|---|---|---|---|---|---|---|
| KX3 | engine (fifo/avg/pooled) | +0.99 | +1.84 | +0.20 | 0.90 / 0.85 / 0.96 | 0.011 | -53.7% | 224 | yes |
| KX3 | exact sizing only (fifo/exact/pooled) | +0.95 (-0.04) | +0.31 (-1.54) | +0.13 | 0.90 / 0.85 / 0.81 | 0.400 | -54.3% | 276 | no |
| KX3 | IRS netting only (fifo/avg/irs) | +0.99 (-0.00) | +1.84 (+0.00) | +0.20 | 0.90 / 0.85 / 0.96 | 0.013 | -53.7% | 224 | yes |
| KX3 | HIFO + exact (pooled) | +1.02 (+0.03) | +1.84 (-0.00) | +0.23 | 0.90 / 0.87 / 1.00 | 0.012 | -54.9% | 265 | yes |
| KX3 | REAL = HIFO + exact + IRS | +1.02 (+0.03) | +1.84 (-0.00) | +0.23 | 0.90 / 0.87 / 1.00 | 0.013 | -54.9% | 265 | yes |
| KX3 | min-tax + exact + IRS | +1.02 (+0.03) | +1.84 (-0.00) | +0.24 | 0.90 / 0.87 / 1.00 | 0.013 | -54.9% | 265 | yes |
| KX3 | REAL + IRS wash rule | +1.02 (+0.03) | +1.84 (-0.00) | +0.23 | 0.90 / 0.87 / 1.00 | 0.013 | -54.9% | 265 | yes |
| KX1 | engine (fifo/avg/pooled) | +0.93 | +1.82 | +0.14 | 0.91 / 0.89 / 0.96 | 0.011 | -56.6% | 279 | yes |
| KX1 | exact sizing only (fifo/exact/pooled) | +0.92 (-0.02) | +1.76 (-0.06) | +0.10 | 0.90 / 0.91 / 0.96 | 0.015 | -56.6% | 351 | yes |
| KX1 | IRS netting only (fifo/avg/irs) | +0.93 (-0.01) | +1.82 (+0.00) | +0.14 | 0.91 / 0.89 / 0.96 | 0.012 | -56.6% | 279 | yes |
| KX1 | HIFO + exact (pooled) | +0.95 (+0.01) | +1.89 (+0.07) | +0.18 | 0.90 / 0.91 / 1.00 | 0.009 | -56.5% | 347 | yes |
| KX1 | REAL = HIFO + exact + IRS | +0.94 (+0.01) | +1.89 (+0.07) | +0.18 | 0.90 / 0.91 / 1.00 | 0.008 | -56.5% | 347 | yes |
| KX1 | min-tax + exact + IRS | +0.94 (+0.01) | +1.89 (+0.07) | +0.18 | 0.90 / 0.91 / 1.00 | 0.008 | -56.5% | 347 | yes |
| KX1 | REAL + IRS wash rule | +0.94 (+0.01) | +1.89 (+0.07) | +0.18 | 0.90 / 0.91 / 1.00 | 0.008 | -56.5% | 347 | yes |
| site preset (INC) | engine (fifo/avg/pooled) | +0.66 | +1.54 | +0.03 | 0.70 / 0.83 / 1.00 | 0.025 | -56.6% | 295 | no |
| site preset (INC) | exact sizing only (fifo/exact/pooled) | +0.65 (-0.01) | +1.54 (-0.00) | +0.02 | 0.70 / 0.83 / 1.00 | 0.025 | -56.6% | 302 | no |
| site preset (INC) | IRS netting only (fifo/avg/irs) | +0.66 (-0.00) | +1.54 (+0.00) | +0.03 | 0.70 / 0.83 / 1.00 | 0.026 | -56.6% | 295 | no |
| site preset (INC) | HIFO + exact (pooled) | +0.38 (-0.28) | +0.93 (-0.62) | -0.13 | 0.55 / 0.68 / 0.96 | 0.109 | -56.6% | 324 | no |
| site preset (INC) | REAL = HIFO + exact + IRS | +0.38 (-0.28) | +0.93 (-0.62) | -0.13 | 0.55 / 0.68 / 0.96 | 0.109 | -56.6% | 324 | no |
| site preset (INC) | min-tax + exact + IRS | +0.37 (-0.28) | +0.93 (-0.62) | -0.14 | 0.55 / 0.68 / 0.96 | 0.109 | -56.6% | 324 | no |
| site preset (INC) | REAL + IRS wash rule | +0.38 (-0.28) | +0.93 (-0.62) | -0.13 | 0.55 / 0.68 / 0.96 | 0.109 | -56.6% | 324 | no |
| B378 site combo | engine (fifo/avg/pooled) | +0.79 | +1.05 | +0.03 | 0.82 / 0.91 / 1.00 | 0.073 | -56.7% | 184 | yes |
| B378 site combo | exact sizing only (fifo/exact/pooled) | +0.79 (+0.00) | +1.04 (-0.00) | +0.04 | 0.84 / 0.91 / 1.00 | 0.073 | -56.7% | 185 | yes |
| B378 site combo | IRS netting only (fifo/avg/irs) | +0.79 (-0.00) | +1.05 (+0.00) | +0.03 | 0.82 / 0.91 / 1.00 | 0.073 | -56.7% | 184 | yes |
| B378 site combo | HIFO + exact (pooled) | +0.79 (-0.00) | +1.11 (+0.07) | +0.06 | 0.79 / 0.89 / 1.00 | 0.070 | -56.7% | 186 | yes |
| B378 site combo | REAL = HIFO + exact + IRS | +0.79 (-0.00) | +1.11 (+0.07) | +0.06 | 0.79 / 0.89 / 1.00 | 0.069 | -56.7% | 186 | yes |
| B378 site combo | min-tax + exact + IRS | +0.79 (-0.00) | +1.11 (+0.07) | +0.07 | 0.82 / 0.89 / 1.00 | 0.069 | -56.7% | 186 | yes |
| B378 site combo | REAL + IRS wash rule | +0.79 (-0.00) | +1.11 (+0.07) | +0.06 | 0.79 / 0.89 / 1.00 | 0.069 | -56.7% | 186 | yes |
| B378-WS | engine (fifo/avg/pooled) | +0.91 | +1.15 | -0.11 | 0.82 / 0.89 / 1.00 | 0.054 | -54.9% | 331 | yes |
| B378-WS | exact sizing only (fifo/exact/pooled) | +0.92 (+0.00) | +1.14 (-0.01) | -0.10 | 0.82 / 0.89 / 1.00 | 0.055 | -54.9% | 335 | yes |
| B378-WS | IRS netting only (fifo/avg/irs) | +0.91 (-0.00) | +1.15 (+0.00) | -0.11 | 0.82 / 0.89 / 1.00 | 0.055 | -54.9% | 331 | yes |
| B378-WS | HIFO + exact (pooled) | +0.85 (-0.06) | +0.88 (-0.27) | -0.15 | 0.79 / 0.87 / 1.00 | 0.098 | -55.5% | 333 | yes |
| B378-WS | REAL = HIFO + exact + IRS | +0.85 (-0.06) | +0.88 (-0.27) | -0.15 | 0.79 / 0.87 / 1.00 | 0.101 | -55.5% | 333 | no |
| B378-WS | min-tax + exact + IRS | +0.85 (-0.06) | +0.88 (-0.27) | -0.14 | 0.82 / 0.87 / 1.00 | 0.101 | -55.5% | 333 | no |
| B378-WS | REAL + IRS wash rule | +0.85 (-0.06) | +0.88 (-0.27) | -0.15 | 0.79 / 0.87 / 1.00 | 0.101 | -55.5% | 333 | no |
| INC-WS | engine (fifo/avg/pooled) | +0.72 | +1.29 | -0.03 | 0.84 / 0.83 / 1.00 | 0.044 | -55.1% | 581 | no |
| INC-WS | exact sizing only (fifo/exact/pooled) | +0.70 (-0.02) | +1.26 (-0.03) | -0.07 | 0.84 / 0.83 / 1.00 | 0.042 | -55.2% | 584 | no |
| INC-WS | IRS netting only (fifo/avg/irs) | +0.72 (-0.00) | +1.29 (+0.00) | -0.03 | 0.84 / 0.83 / 1.00 | 0.044 | -55.1% | 581 | no |
| INC-WS | HIFO + exact (pooled) | +0.60 (-0.11) | +1.16 (-0.13) | -0.10 | 0.82 / 0.83 / 0.93 | 0.060 | -55.1% | 575 | no |
| INC-WS | REAL = HIFO + exact + IRS | +0.60 (-0.11) | +1.16 (-0.13) | -0.10 | 0.82 / 0.83 / 0.93 | 0.063 | -55.1% | 575 | no |
| INC-WS | min-tax + exact + IRS | +0.61 (-0.11) | +1.16 (-0.13) | -0.09 | 0.82 / 0.83 / 0.93 | 0.063 | -55.1% | 575 | no |
| INC-WS | REAL + IRS wash rule | +0.60 (-0.11) | +1.16 (-0.13) | -0.10 | 0.82 / 0.83 / 0.93 | 0.063 | -55.1% | 575 | no |

What each option does on its own (default rebalance dates):

- **Exact sizing alone changes the score by −0.04 to +0.00 pp, but moves single paths a lot.**
  KX3's 2000-start path falls from +1.84 to +0.31 pp (p 0.40). This is exactly the round-1
  verifier's result: the budget-overshooting path was the lucky one.
- **IRS netting alone changes the score by ±0.00 pp.** Yearly taxes are identical (§3); only
  the terminal liquidation differs, so boot_p moves by ≤ 0.002.
- **HIFO + exact.** Default dates only (§5 has the schedule averages):
  - the no-trim K-execution rises slightly (KX3 +0.03, KX1 +0.01);
  - the trimming rules fall (B378-WS −0.06, INC-WS −0.11, the site preset −0.28).
- **min-tax ≈ HIFO** (±0.01 pp).
- **The IRS wash rule changes nothing.** These rules cannot wash-sale (§2).
- **Bar 1-3 on the default dates:**
  - KX3, KX1 and the B378 combo pass under both accountings;
  - the preset and INC-WS fail under both;
  - B378-WS slips from pass (p 0.054) to fail (p 0.101).
- **Why the preset fell on the default dates: path divergence, not a systematic mechanism.**
  - The loss is concentrated in windows starting 2005-2008 (−0.6 to −1.6 pp/yr over 5-10 years).
  - The 2007-07 path is identical through 2009. It diverges on one rotation decision in
    2010-2011 and is 7-11% lower by 2012-2013.
  - Growth/tech weight is *not* lower under HIFO (2000 start: 43% vs 41% on average).
  - Averaged over 7 schedules the preset loses only 0.04 pp (§5).

## 5. Rebalance-timing luck: averages over 7 schedules (CA)

The tax-managed rules are frozen-portfolio rules. Their single-path statistics
(`full_excess`, `boot_p`) are chaotic: one partial sale in 2004 or 2010 sends a 2000-start path
somewhere else. So I re-ran every finalist on 7 rebalance-boundary offsets:
- S cadence: 0-168 days, step 28;
- Q cadence: 0-84 days, step 14.

Each was run under the engine and under REAL. The engine's offset records for KX3, KX1 and the
preset are the lab's own cached runs (V4).

| finalist | accounting | score mean [min, max] | full_excess mean [min, max] | end_mean | ex10 / ex15 beat | boot_p mean (≤ 0.10) | clears bar 1-3 |
|---|---|---|---|---|---|---|---|
| KX3 | engine | +0.94 [+0.74, +1.17] | +1.15 [+0.52, +1.90] | +0.20 | 0.87 / 0.87 | 0.130 (3/7) | 2/7 |
| KX3 | REAL | +0.95 [+0.74, +1.18] | +1.13 [+0.40, +1.94] | +0.23 | 0.88 / 0.88 | 0.139 (3/7) | 3/7 |
| KX1 | engine | +0.78 [+0.38, +1.01] | +0.95 [+0.23, +1.82] | +0.12 | 0.81 / 0.84 | 0.195 (2/7) | 2/7 |
| KX1 | REAL | +0.79 [+0.39, +1.02] | +1.12 [+0.50, +1.89] | +0.15 | 0.81 / 0.86 | 0.133 (2/7) | 1/7 |
| site preset (INC) | engine | +0.67 [+0.52, +0.88] | +1.11 [+0.50, +1.89] | +0.10 | 0.71 / 0.84 | 0.107 (5/7) | 0/7 |
| site preset (INC) | REAL | +0.63 [+0.38, +0.88] | +0.98 [+0.40, +1.88] | +0.08 | 0.70 / 0.82 | 0.127 (4/7) | 0/7 |
| B378 site combo | engine | +0.52 [+0.23, +0.82] | +0.71 [+0.14, +1.36] | -0.20 | 0.67 / 0.79 | 0.218 (3/7) | 2/7 |
| B378 site combo | REAL | +0.53 [+0.25, +0.88] | +0.74 [+0.14, +1.25] | -0.20 | 0.67 / 0.80 | 0.203 (3/7) | 2/7 |
| B378-WS | engine | +0.67 [+0.44, +0.93] | +0.72 [+0.08, +1.37] | -0.20 | 0.75 / 0.83 | 0.205 (2/7) | 1/7 |
| B378-WS | REAL | +0.66 [+0.45, +0.94] | +0.74 [+0.16, +1.34] | -0.21 | 0.75 / 0.83 | 0.182 (1/7) | 0/7 |
| INC-WS | engine | +0.67 [+0.44, +0.96] | +1.10 [+0.53, +1.87] | -0.02 | 0.75 / 0.83 | 0.097 (4/7) | 2/7 |
| INC-WS | REAL | +0.65 [+0.46, +0.96] | +1.00 [+0.58, +1.81] | -0.03 | 0.75 / 0.84 | 0.118 (4/7) | 1/7 |

Paired REAL − engine at the same schedule (pp/yr; share of the 7 schedules where REAL is higher):

| finalist | score | full_excess | end_mean |
|---|---|---|---|
| KX3 | +0.02 (7/7) | -0.02 (4/7) | +0.03 (6/7) |
| KX1 | +0.01 (5/7) | +0.17 (6/7) | +0.03 (5/7) |
| site preset (INC) | -0.04 (3/7) | -0.13 (1/7) | -0.03 (3/7) |
| B378 site combo | +0.01 (4/7) | +0.03 (4/7) | +0.00 (3/7) |
| B378-WS | -0.01 (3/7) | +0.02 (4/7) | -0.01 (4/7) |
| INC-WS | -0.01 (4/7) | -0.09 (2/7) | -0.01 (3/7) |

- **Averaged over schedules, specific-lot accounting moves no finalist's score by more than
  0.04 pp.** KX3 is higher on all 7 schedules, but by only +0.02 pp. The preset's −0.28 pp on
  the default dates becomes −0.04 pp.
- **Single-path statistics move both ways, within their usual chaos:**
  - KX1 full_excess +0.17 pp, higher on 6/7 schedules;
  - the preset −0.13 pp;
  - INC-WS −0.09 pp.
- **No finalist clears criteria 1-3 on a majority of schedules under either accounting.**

  | finalist | REAL | engine |
  |---|---|---|
  | KX3 | 3/7 | 2/7 |
  | B378 combo | 2/7 | 2/7 |
  | KX1 | 1/7 | 2/7 |
  | INC-WS | 1/7 | 2/7 |
  | B378-WS | 0/7 | 1/7 |
  | site preset | 0/7 | 0/7 |

  The failures are the same as in round 1: boot_p and the 15-year beat rate.
- **The S-cadence rules' default dates were lucky in round 1, and still are.**
  - B378 combo: mean +0.52 across schedules vs +0.79 on the default dates;
  - B378-WS: +0.66 vs +0.91.

## 6. Does specific-lot accounting enable a better rotation? (pre-registered grid, CA)

Pre-registered before running: signal {INC = 252-21 momentum, top 5, Q; B378 = 378-0, top 5,
S} × execution {WS = trims, smallest gain first; K = keep in top 2N, no trims, worst-ranked
first; the site's TaxManagedCombo} × gain budget {0.5, 1, 2, 3, 5%} × short-term gains
{allowed, forbidden} (WS and K only). That is 50 rules, each run under REAL and under
`fifo/exact/irs`. The pair isolates the lot method: the sizing and the netting are the same.
Full protocol, CA. Every row is in `scratch/r2_gap5/e3_grid.csv`.

| execution | budget | rules | mean score REAL | mean score fifo | REAL − fifo score | REAL − fifo end_mean | clear bar 1-3: REAL / fifo |
|---|---|---|---|---|---|---|---|
| K | 0.5% | 4 | +0.95 | +0.93 | +0.03 | +0.05 | 2 / 2 |
| K | 1.0% | 4 | +1.00 | +0.96 | +0.04 | +0.07 | 4 / 1 |
| K | 2.0% | 4 | +0.96 | +0.93 | +0.02 | +0.07 | 3 / 3 |
| K | 3.0% | 4 | +0.89 | +0.89 | -0.00 | +0.03 | 2 / 1 |
| K | 5.0% | 4 | +0.66 | +0.69 | -0.03 | -0.04 | 0 / 0 |
| WS | 0.5% | 4 | +0.86 | +0.88 | -0.02 | +0.00 | 0 / 0 |
| WS | 1.0% | 4 | +0.82 | +0.86 | -0.03 | -0.02 | 1 / 2 |
| WS | 2.0% | 4 | +0.78 | +0.81 | -0.03 | +0.00 | 2 / 2 |
| WS | 3.0% | 4 | +0.79 | +0.79 | -0.00 | +0.03 | 0 / 1 |
| WS | 5.0% | 4 | +0.47 | +0.50 | -0.02 | -0.01 | 0 / 0 |
| combo | 0.5% | 2 | +0.67 | +0.74 | -0.07 | -0.01 | 0 / 1 |
| combo | 1.0% | 2 | +0.58 | +0.72 | -0.14 | -0.07 | 1 / 1 |
| combo | 2.0% | 2 | +0.51 | +0.61 | -0.11 | -0.07 | 0 / 0 |
| combo | 3.0% | 2 | +0.44 | +0.48 | -0.04 | -0.06 | 0 / 0 |
| combo | 5.0% | 2 | +0.22 | +0.19 | +0.03 | +0.01 | 0 / 0 |

- **Specific-lot sales do not open a new design space.** Across the 50 pairs, HIFO changes the
  score by −0.02 pp on average and is better in 48% of pairs:
  - **K-execution:** +0.02 to +0.04 pp at 0.5-2% budgets;
  - **trimming WS:** −0.00 to −0.03;
  - **site combo:** −0.04 to −0.14.
- **Larger budgets stay worse under HIFO.** At 5%, K +0.66, WS +0.47 and combo +0.22, vs
  +0.95-1.00 for K at 0.5-1%. Cheaper partial sales do not make more turnover pay.
- **The bar.** 15 of 50 rules clear criteria 1-3 on the default dates under REAL and
  14 under FIFO. They are the same K-execution cluster as round 1, and which members pass
  flips with the path. For example, KX3 fails under `fifo/exact` (p 0.40) and passes under
  REAL (p 0.013).
- **Family diagnostics of the REAL grid** (criterion 4):
  - walk-forward out of sample −0.83 pp (10y in / 5y out, beat 0.33);
  - −0.13 pp (5y / 3y);
  - PBO 0.56.
- **Deflated Sharpe of the five best REAL rules is 0.0003-0.032**, at the search-wide count of
  12,050 configurations.
- **Criterion 4 fails, exactly as in round 1.**

## 7. Hindsight and holdout under specific-lot accounting

(a) **The incumbent menu without QQQ and XLK** (full, CA):

| finalist | engine: score / full / ex10 / ex15 beat / boot_p | REAL: score / full / ex10 / ex15 beat / boot_p |
|---|---|---|
| KX3 | -0.26 / +0.15 / 0.46 / 0.51 / 0.45 | -0.26 / +0.19 / 0.46 / 0.51 / 0.43 |
| KX1 | +0.12 / +0.14 / 0.49 / 0.64 / 0.44 | +0.12 / +0.15 / 0.51 / 0.64 / 0.44 |
| site preset | -0.35 / +0.68 / 0.34 / 0.45 / 0.27 | -0.36 / +0.48 / 0.39 / 0.47 / 0.34 |
| B378 combo | -0.12 / -0.05 / 0.51 / 0.49 / 0.52 | -0.10 / -0.11 / 0.51 / 0.57 / 0.54 |
| B378-WS | -0.11 / -0.00 / 0.51 / 0.57 / 0.50 | -0.12 / -0.11 / 0.52 / 0.57 / 0.54 |
| INC-WS | -0.42 / +0.20 / 0.36 / 0.40 / 0.42 | -0.36 / +0.29 / 0.36 / 0.43 / 0.40 |

- Every finalist still fails without the two hindsight funds, under both accountings.
- Specific-lot accounting moves the scores by ≤ 0.06 pp. Single-path full excess moves by up to 0.20 pp (the preset).
- The 10-year beat rates of 0.34-0.52 are a coin flip.

(b) **30 random menus** (seeds 1-30, 15-25 funds from the pre-registered
`BROAD_EQUITY_POOL_2003`; screen protocol, CA). Baselines are round 1's own records.

| rule | engine: score (share > 0) / full / ex10 beat / pass 1-3 | REAL: score (share > 0) / full / ex10 beat / pass 1-3 | paired REAL − engine |
|---|---|---|---|
| KX3 | +0.39 (77%) / +0.16 / 0.52 / 1 of 30 | +0.39 (77%) / +0.17 / 0.52 / 1 of 30 | score +0.00 (t 0.2); end_mean +0.04 (t 3.6) |
| KX1 | +0.42 (70%) / +0.70 / 0.48 / 1 of 30 | +0.42 (70%) / +0.57 / 0.47 / 1 of 30 | score +0.00 (t 0.6); full -0.12 (t -1.6) |

- Menus nobody chose give the same answer under both accountings: about +0.4 pp of score and
  1 menu in 30 clearing criteria 1-3.
- The only consistent change is KX3's mean to-the-end excess, +0.04 pp (t 3.6): real but
  immaterial.

(c) **Pre-2000 holdout** (pre-ETF analog menu PRE20, `long_r`, 1-day lag): VFINXR benchmark, quarterly starts 1986-2023; `ho5` / `ho10` = windows ending before 2000.

| rule | engine: score / full / ex10 beat / boot_p / ho5 (beat) / ho10 (beat) | REAL: same |
|---|---|---|
| KX3 | +1.10 / -0.39 / 0.66 / 0.64 / +0.40 (0.59) / -0.06 (0.35) | +1.10 / -0.11 / 0.66 / 0.54 / +0.41 (0.59) / -0.06 (0.35) |
| KX1 | +0.97 / -0.01 / 0.66 / 0.48 / -0.12 (0.51) / -0.19 (0.41) | +0.98 / +0.48 / 0.66 / 0.26 / -0.11 (0.51) / -0.19 (0.41) |

- **The true holdout is identical under both accountings, to 0.01 pp.** It stays flat to
  negative:
  - KX3: 5-year windows +0.4, 10-year windows −0.1;
  - KX1: −0.1 and −0.2.
- Criteria 1-3 fail in both.
- These differ slightly from the round-1 verifier's PRE20 numbers. It used the `long` protocol,
  whose VFINX benchmark has the 1980-86 distribution bug. `long_r` repairs it.

## 8. The leveraged trend rules (SMA175 / 3% band, daily, → VFITX)

**Engine, protocol `full`, CA** (FED at the end of this section):

| rule | accounting | score | full_excess | end_mean | ex10 / ex15 / ex20 beat | ex10 min | boot_p | max DD (SPY −55.2%) |
|---|---|---|---|---|---|---|---|---|
| 2x SMA175/3% | engine | +4.94 | +3.80 | +1.01 | 1.00 / 1.00 / 1.00 | +0.64 | 0.077 | -47.1% |
| 2x SMA175/3% | IRS netting | +4.95 (+0.01) | +3.80 | +1.01 | 1.00 / 1.00 / 1.00 | +0.64 | 0.075 | -47.1% |
| 2x SMA175/3% | IRS wash rule | +4.93 (-0.00) | +3.78 | +0.98 | 1.00 / 1.00 / 1.00 | +0.60 | 0.075 | -47.7% |
| 2x SMA175/3% | IRS netting + wash | +4.95 (+0.01) | +3.78 | +0.98 | 1.00 / 1.00 / 1.00 | +0.60 | 0.073 | -47.7% |
| 2x SMA175/3% | + $3k ordinary deduction (irs3k) | +5.01 (+0.07) | +3.88 | +1.07 | 1.00 / 1.00 / 1.00 | +0.65 | 0.069 | -47.1% |
| 2x SMA175/3% | HIFO lots | +4.94 (+0.00) | +3.80 | +1.01 | 1.00 / 1.00 / 1.00 | +0.64 | 0.077 | -47.1% |
| 3x SMA175/3% | engine | +9.65 | +7.10 | +5.56 | 1.00 / 1.00 / 1.00 | +4.81 | 0.029 | -60.5% |
| 3x SMA175/3% | IRS netting | +9.67 (+0.02) | +7.10 | +5.56 | 1.00 / 1.00 / 1.00 | +4.87 | 0.029 | -60.5% |
| 3x SMA175/3% | IRS wash rule | +9.70 (+0.05) | +7.08 | +5.52 | 1.00 / 1.00 / 1.00 | +4.76 | 0.029 | -60.9% |
| 3x SMA175/3% | IRS netting + wash | +9.72 (+0.07) | +7.08 | +5.52 | 1.00 / 1.00 / 1.00 | +4.84 | 0.029 | -60.9% |
| 3x SMA175/3% | + $3k ordinary deduction (irs3k) | +9.77 (+0.12) | +7.23 | +5.66 | 1.00 / 1.00 / 1.00 | +5.09 | 0.027 | -60.5% |
| 3x SMA175/3% | HIFO lots | +9.65 (+0.00) | +7.10 | +5.56 | 1.00 / 1.00 / 1.00 | +4.81 | 0.029 | -60.5% |

**Long histories (sim, CA).** These are the lev_robust verifier's four worlds, run with the
simulator extended for IRS netting and wash sales and validated against the engine (V3):

| rule | history | engine accounting: score / full / ex10 beat / boot_p | IRS netting + wash rule: score / full / ex10 beat / boot_p | wash events (first path; mean per start) | max DD (benchmark) |
|---|---|---|---|---|---|
| 2x | 2000-2026 (= full) | +4.94 / +3.80 / 1.00 / 0.077 | +4.95 / +3.78 / 1.00 / 0.073 | 1; 1.0 | -48% (-55%) |
| 2x | 1986-2026 (repaired VFINX) | +4.62 / +2.79 / 1.00 / 0.067 | +4.64 / +2.78 / 1.00 / 0.068 | 1; 1.0 | -47% (-55%) |
| 2x | 1930-1985 holdout | +2.95 / +1.48 / 0.83 / 0.270 | +2.92 / +1.44 / 0.80 / 0.275 | 12; 1.9 | -67% (-81%) |
| 2x | 1930-2026 | +3.48 / +1.77 / 0.89 / 0.129 | +3.48 / +1.74 / 0.87 / 0.132 | 13; 1.9 | -67% (-81%) |
| 3x | 2000-2026 (= full) | +9.65 / +7.10 / 1.00 / 0.029 | +9.72 / +7.08 / 1.00 / 0.029 | 2; 1.9 | -61% (-55%) |
| 3x | 1986-2026 (repaired VFINX) | +8.64 / +6.88 / 1.00 / 0.007 | +8.69 / +6.87 / 1.00 / 0.007 | 2; 2.0 | -61% (-55%) |
| 3x | 1930-1985 holdout | +6.81 / +3.40 / 0.83 / 0.187 | +6.82 / +3.40 / 0.83 / 0.186 | 12; 1.9 | -88% (-81%) |
| 3x | 1930-2026 | +7.29 / +4.70 / 0.90 / 0.046 | +7.31 / +4.70 / 0.90 / 0.046 | 14; 2.9 | -88% (-81%) |

- **Lot choice cannot matter here.** Each state holds one lot.
- **IRS netting changes no yearly tax** (§3). The terminal liquidation as one tax year adds
  +0.00 to +0.02 pp.
- **The wash rule defers the loss of a whipsaw re-entry.**
  - It happens about once per 2000-2026 path (2022 for 2x; 2022 and 2023 for 3x).
  - It happens 12-14 times on the 1930 path.
  - The cost is 0.02-0.04 pp of full-period excess, and the max drawdown is 0.4-0.6 pp deeper.
- **The $3,000 ordinary-loss deduction is worth +0.07 (2x) / +0.12 (3x) pp** on a $100k account.
  It is scale-dependent and shrinks as the account grows.
- **Every verdict of `verify_lev_robust` stands unchanged:**
  - **2x** stays **CONDITIONAL**: CA p 0.073 on 2000-26 and 0.068 on 1986-26, but 0.275 on the
    1930-85 holdout and 0.132 on 1930-2026; deflated Sharpe 0.0037.
  - **3x** stays **FAIL**: −88% drawdown in 1929-35.
- **Context for the 2x rule, not new but worth knowing.** Its to-the-end excess is negative for
  every start from 2017 on (−0.3 to −3.7 pp/yr to 2026, CA). The average over all starts,
  +1.0 pp, is far below its window score of +4.9: the score is carried by windows that contain
  2000-02 or 2008.

## 9. Other tax-managed round-1 leads

Both are `weights` kinds with the lab's tax execution, so the same wrapper applies. The
critic also listed TVT (`risk_alloc.taxvt`), which was **not** re-run (§12).

| lead (round-1 verification verdict) | accounting | score / full / end_mean / ex10 beat / ex15 beat / boot_p / trades |
|---|---|---|
| value/growth 12-1 switch N5_vgh (verify_tilts: FAIL) | engine (identical to the lab record, max diff 0.0) | +1.16 / +1.83 / +0.91 / 0.88 / 1.00 / 0.040 / 13 |
| | REAL | +1.15 / +1.83 / +0.91 / 0.88 / 1.00 / 0.040 / 13 |
| | min-tax + exact + IRS | +1.15 / +1.83 / +0.91 / 0.88 / 1.00 / 0.040 / 13 |
| tax-managed cyclical season Oct-May (verify_tilts: FAIL) | engine (identical, 0.0) | +0.85 / +1.44 / +0.34 / 0.91 / 0.94 / 0.035 / 416 |
| | REAL | +0.88 / +1.67 / +0.41 / 0.91 / 0.96 / 0.014 / 475 |
| | min-tax + exact + IRS | +0.89 / +1.67 / +0.41 / 0.91 / 0.96 / 0.014 / 482 |

- **The value/growth switch does not change** (−0.01 pp). Its 13 trades are whole switches,
  where lot order cannot matter.
- **The monthly-trimming season tilt gains a little** (+0.03 pp of score). The single path
  moves more: full +1.44 → +1.67, boot_p 0.035 → 0.014, because cheaper trims keep it closer
  to its targets.
- **Neither verdict changes.** verify_tilts failed both on grounds accounting cannot touch:
  - the static basket scores higher than the rule;
  - the long-history twins fail;
  - first-path dependence of boot_p;
  - deflated Sharpe 0.012-0.015.

## 10. Against SPY and against the round-1 best

Every excess above is already *versus SPY bought and held* after the same tax and costs. Against
the round-1 best (`scratch/_lead/r1/verify_candidates.json`; CA, `full`):

| round-1 candidate | round-1 / verification status | engine score | under this gap's accounting | changes the status? |
|---|---|---|---|---|
| 2x SMA175/3% → VFITX (the verified best: CONDITIONAL) | p 0.077, DSR 0.004, 1930-85 p 0.27 | +4.94 | +4.95 (IRS + wash); 1986-26 +4.64 (p 0.068); 1930-85 +2.92 (p 0.275) | no |
| 3x SMA175/3% (C1) | FAIL: −88% to −93% in 1929-35 | +9.65 | +9.72; 1930-85 drawdown still −88% | no |
| KX3 tax-managed rotation | FAIL: hindsight, holdout, DSR 0.04 | +0.99 | +1.02 REAL; schedules +0.95; without QQQ/XLK −0.26; DSR 0.032 | no |
| KX1 | FAIL | +0.93 | +0.94; schedules +0.79; without QQQ/XLK +0.12; DSR 0.048 | no |
| site preset "Beat the S&P (CA)" | fails criteria 1-3 | +0.66 | +0.38 default dates; −0.04 averaged over schedules | no (still fails) |
| B378 site combo / B378-WS | fail 4-7 | +0.79 / +0.91 | +0.79 / +0.85 | no |
| value/growth switch / cyclical season | FAIL (verify_tilts) | +1.16 / +0.85 | +1.15 / +0.88 | no |

- The ranking of the program's candidates is unchanged.
- **The only candidate still standing is the conditional 2x trend rule.** IRS netting and the
  wash rule leave it within ±0.02 pp everywhere, and lot choice cannot affect it.

## 11. Configs and runs

__PENDING_COUNT__

## 12. Notes for the lab

1. **Pooled netting is never less generous than IRS netting.** I proved it and checked it on
   200,000 random cases. For the finalists the two give **identical** yearly taxes on every
   history. The engine docstring's "close approximation of the IRS netting" is accurate for
   these strategies. A strategy that harvests long-term losses while realizing short-term gains
   would be flattered; none of the finalists does.
2. **The engine's terminal tax is computed in two steps** (this year's realized gains, then the
   unrealized ones with the remaining carry). That is slightly *less* generous than one
   combined liquidation year, by ≤ 0.02 pp here. Not worth a site change.
3. **The site's TaxManagedCombo sizes its partial sale on the average gain.** Under FIFO it
   overshoots the gain budget: B378 combo up to 1.44× in a year, the preset 1.18×. Sizing on
   the actual lots is a one-function fix with no systematic performance effect (§4, §5),
   and it makes the budget mean what the UI says.
4. **Wash sales.**
   - The lab's tax execution has no look-back guard. At Q/S cadences it can never bind: zero
     exposure in every audit.
   - Daily trend rules do produce wash sales (about 1 per 2000-26 path), and standard
     execution ignores them. This module models them; the effect is ≤ 0.04 pp.
   - Two lenient readings in my implementation:
     - a partial loss sale of a lot bought within 30 days (the lot's own remaining shares are
       not treated as replacements);
     - the $1 dust lots the lab's WeightStrategy buys with residual cash on rebalance days,
       which do count as replacements (immaterial).
5. **Cache hygiene.** During this session other work edited `strategies/timers.py` and
   `backtester/data.py` (website presets).
   - That changed my first code hash: 29 early records under hash 660393389802 are superseded
     and unused.
   - The r2_gap5 runner now hashes only what a run executes: this module, the lab core, the
     wrapped family files, the engine files it subclasses, and the source of the momentum
     picker, `total_return` and the buy-hold timer.
   - The lab's own `registry.code_version` does **not** hash `strategies/pickers.py` or
     `timers.py` at all, so a picker edit would leave stale combo results in the sweep cache.
6. **Not covered:**
   - **TVT (`risk_alloc.taxvt`).** Its seller already walks lot fronts across three different-
     index vehicles cheapest-tax-first, though FIFO within a vehicle. Wrapping it needs a
     custom subclass. Its verdict (verify_levvt: the excess is leverage, beta 1.57, alpha ≈ 0)
     does not depend on lot order.
   - **The TAA "lt" configs** from the critic's list.
   - **Average-cost basis** (mutual funds only).
7. **The $3k ordinary-loss deduction (`irs3k`) is real tax law but scale-dependent.** It is
   worth +0.07 pp (2x) and +0.12 pp (3x) on the lab's $100k account and less on larger
   accounts. It is not part of REAL.
