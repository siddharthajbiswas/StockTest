"""Multi-window head-to-head: plain vs selective RSI reversion across regimes.

Loads all tickers once, then for each window runs both strategies with a
lookback buffer (so indicators are warm at the window start) and measures only
the in-window equity. Prints a per-window comparison plus a market benchmark.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from backtester import Backtest, load_prices

BUFFER_DAYS = 400          # calendar-day lookback before each window (warms SMA200/RSI)
CASH = 100_000.0
COMM = 0.001               # 10 bps
TRADING_DAYS = 252

WINDOWS = [
    ("2005-01-01", "2006-12-31", "Bull '05-06"),
    ("2008-01-01", "2009-12-31", "Crisis '08-09"),
    ("2012-01-01", "2013-12-31", "Recovery '12-13"),
    ("2015-01-01", "2016-12-31", "Choppy '15-16"),
    ("2018-01-01", "2019-12-31", "Correction '18-19"),
    ("2020-01-01", "2021-12-31", "COVID '20-21"),
    ("2022-01-01", "2023-12-31", "Bear '22-23"),
    ("2025-01-01", "2026-07-01", "Recent '25-26"),
]

STRATS = {
    "plain": "strategies/rsi_reversion.py",
    "selective": "strategies/rsi_reversion_selective.py",
}


def fresh_strategy(path: str):
    """Load the module and return a brand-new instance of its strategy class."""
    p = Path(path).resolve()
    spec = importlib.util.spec_from_file_location(p.stem, p)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return type(m.strategy)()  # fresh, default params


def window_metrics(equity: pd.DataFrame, w_start: str) -> dict:
    """Metrics computed only over the in-window slice of the equity curve."""
    eq = equity[equity.index >= pd.Timestamp(w_start)]
    tot = eq["total"]
    ret = tot.iloc[-1] / tot.iloc[0] - 1.0
    daily = tot.pct_change().dropna()
    sharpe = 0.0 if daily.std() == 0 or daily.empty else np.sqrt(TRADING_DAYS) * daily.mean() / daily.std()
    peak = tot.cummax()
    mdd = (tot / peak - 1.0).min()
    return {"ret": ret, "sharpe": float(sharpe), "mdd": float(mdd)}


def main() -> int:
    print("Loading all tickers once...", flush=True)
    prices_full = load_prices(None)  # everything, full history
    print(f"Loaded {len(prices_full)} tickers.\n", flush=True)

    rows = []
    for w_start, w_end, label in WINDOWS:
        buf_start = pd.Timestamp(w_start) - pd.Timedelta(days=BUFFER_DAYS)
        sliced = {}
        for t, df in prices_full.items():
            d = df[(df.index >= buf_start) & (df.index <= pd.Timestamp(w_end))]
            if not d.empty:
                sliced[t] = d

        # Market benchmark: SPY buy & hold over the measurement window.
        spy_ret = float("nan")
        if "SPY" in sliced:
            spy = sliced["SPY"]["Close"]
            spy = spy[spy.index >= pd.Timestamp(w_start)]
            if len(spy) > 1:
                spy_ret = spy.iloc[-1] / spy.iloc[0] - 1.0

        res_by_strat = {}
        for name, path in STRATS.items():
            bt = Backtest(fresh_strategy(path), sliced, cash=CASH, commission_pct=COMM)
            res = bt.run()
            m = window_metrics(res.equity, w_start)
            m["trades"] = 0 if res.trades.empty else len(res.trades)
            res_by_strat[name] = m
            print(f"  [{label}] {name:<10} ret={m['ret']*100:7.2f}%  "
                  f"sharpe={m['sharpe']:5.2f}  mdd={m['mdd']*100:7.2f}%  trades={m['trades']}",
                  flush=True)

        rows.append((label, spy_ret, res_by_strat))
        print(flush=True)

    # ---- summary table ----
    print("=" * 96)
    print(f"{'Window':<20}{'SPY B&H':>10}{'Plain ret':>12}{'Plain Shp':>11}"
          f"{'Selec ret':>12}{'Selec Shp':>11}{'Winner':>12}")
    print("-" * 96)
    p_rets, s_rets = [], []
    for label, spy_ret, r in rows:
        p, s = r["plain"], r["selective"]
        p_rets.append(p["ret"]); s_rets.append(s["ret"])
        winner = "selective" if s["ret"] > p["ret"] else "plain"
        print(f"{label:<20}{spy_ret*100:>9.1f}%{p['ret']*100:>11.1f}%{p['sharpe']:>11.2f}"
              f"{s['ret']*100:>11.1f}%{s['sharpe']:>11.2f}{winner:>12}")
    print("-" * 96)
    n = len(rows)
    sel_wins = sum(1 for _, _, r in rows if r["selective"]["ret"] > r["plain"]["ret"])
    print(f"{'MEAN':<20}{'':>10}{np.mean(p_rets)*100:>11.1f}%{'':>11}"
          f"{np.mean(s_rets)*100:>11.1f}%{'':>11}")
    print(f"\nSelective beat plain in {sel_wins} of {n} windows.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
