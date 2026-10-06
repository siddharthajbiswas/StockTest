# Strategy lab — evaluation protocol (v1)

The question: **which investing strategy beats buying and holding the S&P 500
(SPY), after tax and trading costs, with good confidence?** Everything below
exists so that every number is the website's number and every claim survives
the obvious ways backtests lie.

## 1. The numbers are the site's numbers

* Every run is `backtester.Backtest` — the engine the website's JavaScript port
  is pinned to by the golden suite. `research/lab/validate_lab.py` re-runs
  windows through the site's own request path (`reference/service.py`) and
  matches the lab to **0.0** difference in after-tax CAGR.
* Costs: **5 bps commission + 5 bps slippage per side** (site default).
* Tax regimes (`core.REGIMES`):
  * `CA`   — California ~$300k: 48.1% short-term / 28.1% long-term (the site's
    "Beat the S&P (CA)" preset). **Primary taxable regime.**
  * `FED`  — site default 35% / 15%.
  * `NONE` — no tax: an IRA / 401(k). **Primary tax-deferred regime.**
* Benchmark: SPY bought on the window's first day and held, same engine, same
  tax regime and costs (the site's benchmark). Long-history protocol: VFINX.
* "After-tax CAGR" = value if everything were sold on the window's last day,
  net of all taxes (the site's after-tax number). "Excess" = strategy minus
  benchmark, in CAGR percentage points (0.01 = 1 pp/yr).

## 2. Protocols (`core.PROTOCOLS`)

| name | window starts | benchmark | use |
|---|---|---|---|
| `screen` | Jan 1 of 2000 … 2023 (24) | SPY | fast screening |
| `full` | every quarter 2000-01 … 2023-07 (95) | SPY | finalists |
| `long_screen` | Jan 1 of 1986 … 2023 | VFINX | long history, screening |
| `long` | every quarter 1986-01 … 2023-07 | VFINX | long history, finalists |

Each start is one engine run to 2026-07-01; after-tax liquidation values are
recorded at every quarter end, so windows of **3, 5, 10, 15, 20 years** and
"to the end" all come from the same runs. Signals see all history before the
start (warm), but nothing trades before it. The `long*` protocols also report
`ho5_*` / `ho10_*`: windows that **end before 2000** — a true holdout for any
idea designed on ETF-era data.

## 3. Ranking and the confidence bar

`report.score` (pre-registered): **mean of the average excess over 5-, 10- and
15-year windows.** Report alongside: `full_excess` (from the first valid
start to 2026-07), beat rates (`exL_beat` = share of L-year windows where the
strategy beat SPY), worst windows (`exL_min`), the stationary-bootstrap
confidence interval of the after-tax monthly excess (`boot_lo` = 5th
percentile of annualized excess, `boot_p` = one-sided p-value), max drawdown vs
SPY's, trades, turnover.

A strategy clears the **"good confidence" bar** only if, in the regime it is
for, all hold:
1. score > 0 and full_excess > 0;
2. ex10_beat ≥ 0.75 and ex15_beat ≥ 0.85 (when those windows exist);
3. boot_p ≤ 0.10;
4. its family's walk-forward selection is positive out of sample (see
   `report.diagnostics`) and PBO < 0.5;
5. a parameter neighborhood also passes (it is not a lone spike);
6. it does not depend on one instrument chosen with hindsight (see §5.3);
7. where long-history proxies exist, the pre-2000 holdout does not contradict it.

## 4. How to build and run strategies

```python
from research.lab import sweep, report
from research.lab.registry import register_signal, register_kind
from research.lab.blocks import Signal, WeightStrategy, np_closes, asof, normalize
```

* Put your code in **`research/lab/families/<family>.py`** (auto-imported).
  Register signals with `register_signal("<family>.<name>", factory, tickers_fn)`
  and use config `{"kind": "weights", "signal": "<family>.<name>", "params": {...},
  "rebalance": "M", "execution": "standard"|"tax", ...}`. For logic that is not
  "target weights", subclass `backtester.Strategy` and `register_kind(...)`.
* Reuse `families/common.py`: `common.momentum` (rotation), `common.trend`
  (trend switch), `common.mix` (static mix). Site-expressible strategies use
  kind `"combo"` (exactly the site's classes); `"buyhold"` is a never-rebalanced
  fixed mix.
* `WeightStrategy` execution: `"standard"` (trade to targets, optional `band`)
  or `"tax"` (losses always sold, gains only within `gain_budget` × portfolio
  per year, `st_gains=False` forbids short-term gains, 31-day wash-sale guard,
  optional `harvest` threshold + `substitutes` for tax-loss harvesting).
  Cadences: D, W, M, Q, S, A, or `"M2"`/`"M4"`… (every k months).
* Data: `np_closes(ctx, t, n)` (fast numpy closes up to today);
  `asof(ctx, "^VIX", lag_days=1)` for index series (signals only — `^` tickers
  are never tradable). Instruments: site tickers + `research/lab/INSTRUMENTS.md`.
* Run: `recs = sweep.run(configs, protocol="screen", regimes=("CA", "NONE"),
  workers=6)`; `print(report.family(recs, label=fn, regime="CA"))`.
  Results are cached on disk by config + code hash; re-running is free.
* Fixed allocations that include late-launch funds must set
  `"requires": [...]` (and `"require_days"` if a signal needs history) so no
  window starts before the fund existed (otherwise "waiting in cash for VUG to
  launch" dodges the 2000-02 crash and looks like skill).

## 5. Rules of honesty (non-negotiable)

1. **No look-ahead.** Signals read only `ctx` history up to today (orders fill
   at today's close) and side-channel series lagged ≥ 1 day.
2. **Survivorship.** The per-stock data covers only ~39% of the S&P 500's 2000
   membership (the rest were delisted or acquired), so stock-picking results
   are inflated. Only the `stocks` family may trade individual stocks, always
   next to a random-pick control on the same universe, and its results are
   upper bounds. ETFs/funds have no such bias.
3. **Hindsight.** Choosing an instrument *because* it won (QQQ, XLK, VUG,
   TQQQ, NVDA…) is hindsight. If a result depends on such a choice, also run
   (a) the same rule on ≥ 20 random menus drawn from a broad pre-defined pool
   and (b) the rule with the star removed. Report both.
4. **Wash sales.** The engine does not enforce the wash-sale rule. Any rule
   that deliberately harvests losses must use `execution="tax"` (31-day guard)
   and substitutes that track a *different* index (SPY→VTI is fine; SPY→IVV or
   VOO is not).
5. **Distributions.** Prices are total-return, so the engine taxes dividends
   and bond interest as deferred capital gains. Reality taxes them yearly
   (bond interest at ordinary rates). This flatters bond-heavy and high-yield
   allocations in the taxable regimes — report average bond/cash-proxy weight
   for finalists.
6. **Cash earns 0%** in the engine. To hold T-bills use BIL / SHV / SGOV / SHY
   (VFISX in the long protocol).
7. **Leverage** only via leveraged ETFs (the engine forbids margin). Report
   drawdown and volatility next to return; more risk is not skill.
8. **Report everything you tried** — the number of configs is part of the
   result (it sets the multiple-testing penalty). Never report only winners.

## 6. Compute etiquette (shared machine, many agents)

* At most 12 backtest tasks run machine-wide (file-lock slots), 4 of them
  heavy (whole stock universe). Use `workers=6` (ETF) or `workers=3` (stocks).
* Screen first (`screen`, regimes `CA` + `NONE`), then run ≤ 30 finalists on
  `full` × (`CA`, `FED`, `NONE`) and, where proxies exist, `long`.
* Keep foreground commands under ~9 minutes; run longer sweeps in the
  background (`nohup ... > log 2>&1 &`) and poll.
* Do **not** edit the lab core (`core.py`, `blocks.py`, `registry.py`,
  `data.py`, `sweep.py`, `metrics.py`, `report.py`, `families/common.py`) or
  anything outside `research/lab/families/` and your own scratch files. Report
  suspected lab bugs in your output instead.
