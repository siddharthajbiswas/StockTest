"""Prove the lab measures exactly what the site reports.

For a handful of windows, run the site's own request path (reference/service.py
EngineService.run_backtest -- the oracle the browser engine is pinned to at
1e-9) and compare its after-tax CAGR and its SPY benchmark's after-tax CAGR
with the lab's checkpoint numbers for the same window.

    .venv/bin/python -m research.lab.validate_lab
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "reference")):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd  # noqa: E402

from research.lab import core, metrics, sweep  # noqa: E402

MENU = ["SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP",
        "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY"]

CFGS = {
    "shipped tax-managed momentum": {
        "kind": "combo", "picker": "momentum", "picker_params": {"lookback": 252, "skip": 21},
        "timer": "buy_hold", "timer_params": {}, "top_n": 5, "rebalance": "Q", "menu": MENU,
        "trade_rule": "tax_managed", "gain_budget": 0.01, "wash_days": 31},
    "standard sector momentum M": {
        "kind": "combo", "picker": "momentum", "picker_params": {"lookback": 126},
        "timer": "ma_cross", "timer_params": {}, "top_n": 3, "rebalance": "M", "menu": MENU,
        "trade_rule": "standard"},
    "manual QQQ+SPY trend_stop": {
        "kind": "combo", "tickers": ["QQQ", "SPY"], "timer": "trend_stop",
        "timer_params": {"ma_window": 200, "stop": 0.1}, "rebalance": "M"},
}
WINDOWS = [("2000-01-01", "2026-07-01"), ("2003-04-01", "2013-04-01"),
           ("2010-01-01", "2020-01-01"), ("2016-07-01", "2021-07-01")]
REGIMES = ["CA", "FED", "NONE"]


def site_run(engine, cfg, regime, start, end):
    from models import BacktestRequest, TaxSettings
    rates = core.REGIMES[regime]
    tax = TaxSettings(enabled=rates is not None,
                      short_term_rate=rates[0] if rates else 0.35,
                      long_term_rate=rates[1] if rates else 0.15)
    kw = dict(timer_id=cfg.get("timer", "buy_hold"), timer_params=cfg.get("timer_params", {}),
              rebalance=cfg.get("rebalance", "M"), start=start, end=end, warmup_days=2000,
              commission_pct=core.COMMISSION, slippage_pct=core.SLIPPAGE, tax=tax,
              trade_rule=cfg.get("trade_rule", "standard"),
              gain_budget=cfg.get("gain_budget", 0.01), wash_days=cfg.get("wash_days", 31))
    if cfg.get("tickers"):
        req = BacktestRequest(tickers=cfg["tickers"], **kw)
    else:
        req = BacktestRequest(picker_id=cfg["picker"], picker_params=cfg.get("picker_params", {}),
                              top_n=cfg.get("top_n", 15), menu=cfg.get("menu"), **kw)
    out = engine.run_backtest(req)
    m = out["metrics"]
    b = out["benchmark"]["metrics"]
    key = "after_tax_cagr" if rates else "cagr"
    return m[key], b[key]


def main():
    from service import EngineService
    engine = EngineService(tickers=sorted(set(MENU) | {"SPY"}))
    worst = 0.0
    for name, cfg in CFGS.items():
        for rg in REGIMES:
            rec = sweep.run_one(cfg, rg, "full", use_cache=False)
            bench = metrics.bench_for(rec)
            for s, e in WINDOWS:
                lab_s = metrics.window(rec, s, e)
                lab_b = metrics.window(bench, s, e)
                site_s, site_b = site_run(engine, cfg, rg, s, e)
                d = max(abs(lab_s - site_s), abs(lab_b - site_b))
                worst = max(worst, d)
                flag = "OK " if d < 1e-9 else "BAD"
                print(f"{flag} {name:32s} {rg:4s} {s}->{e}  lab {lab_s*100:7.3f}% / {lab_b*100:7.3f}%"
                      f"   site {site_s*100:7.3f}% / {site_b*100:7.3f}%   diff {d:.2e}")
    print(f"\nworst abs difference in CAGR: {worst:.3e}")


if __name__ == "__main__":
    main()
