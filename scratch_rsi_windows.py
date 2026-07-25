"""Does RSI mean reversion earn its keep in choppy/bear regimes?

Reuses the vectorized grid framework: build picker + timing masks once over full
history (warm), then measure RSI-revert vs Buy&Hold (same stocks) vs SPY within
each bear/choppy sub-window.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from grid_backtest import (load_matrices, build_pickers, build_timing,
                           run_combo, stats, COMMISSION, TRADING_DAYS)

WINDOWS = [
    ("2000-01-01", "2002-12-31", "Dot-com bear '00-02"),
    ("2008-01-01", "2008-12-31", "Financial crisis '08"),
    ("2015-01-01", "2016-12-31", "Choppy '15-16"),
    ("2022-01-01", "2022-12-31", "Bear '22"),
]

def main():
    print("Loading + building signals...", flush=True)
    close, high, low, spy, _ = load_matrices()
    rets_np = close.pct_change().values
    pickers = build_pickers(close, spy)
    timing = build_timing(close, high, low, spy)

    # Precompute full daily-return series for each picker under RSI-revert and BuyHold.
    rsi_series = {p: run_combo(pickers[p], timing["RSIrevert"], rets_np, COMMISSION) for p in pickers}
    bh_series = {p: run_combo(pickers[p], timing["BuyHold"], rets_np, COMMISSION) for p in pickers}
    spy_daily = spy.pct_change()

    for w0, w1, label in WINDOWS:
        mask = (close.index >= pd.Timestamp(w0)) & (close.index <= pd.Timestamp(w1))
        sd = spy_daily[mask]
        spy_ret = (1 + sd).prod() - 1
        yrs = mask.sum() / TRADING_DAYS
        spy_cagr = (1 + spy_ret) ** (1 / yrs) - 1
        spy_sh = np.sqrt(TRADING_DAYS) * sd.mean() / sd.std()
        spy_mdd = ((1+sd).cumprod()/(1+sd).cumprod().cummax()-1).min()

        print(f"\n{'='*78}")
        print(f"{label}   |   SPY: ret={spy_ret*100:+.1f}%  cagr={spy_cagr*100:+.1f}%  "
              f"sharpe={spy_sh:.2f}  mdd={spy_mdd*100:.1f}%")
        print(f"{'-'*78}")
        print(f"{'Picker':<13}{'RSI ret':>9}{'RSI Shp':>9}{'RSI DD':>8}   "
              f"{'B&H ret':>9}{'B&H Shp':>9}   {'RSI wins?':>10}")
        rsi_beats_bh = rsi_beats_spy = 0
        for p in pickers:
            r = stats(rsi_series[p][mask], spy_cagr)
            b = stats(bh_series[p][mask], spy_cagr)
            win = r["sharpe"] > b["sharpe"]
            rsi_beats_bh += win
            rsi_beats_spy += r["ret"] > spy_ret
            print(f"{p:<13}{r['ret']*100:>+8.1f}%{r['sharpe']:>9.2f}{r['mdd']*100:>7.1f}%   "
                  f"{b['ret']*100:>+8.1f}%{b['sharpe']:>9.2f}   {'YES' if win else 'no':>10}")
        print(f"{'-'*78}")
        print(f"RSI beat Buy&Hold (Sharpe) in {rsi_beats_bh}/6 pickers | "
              f"RSI beat SPY (return) in {rsi_beats_spy}/6")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
