"""Vectorized picker x timing grid backtest, 2000-2026.

Only price/volume-derived factors are used — the dataset has no fundamentals,
so pickers like Value/ROE/Revenue are deliberately absent (building them from
made-up numbers would produce fake results). See the pickers below for the six
honest, price-based selectors.

Design: every picker becomes a monthly top-quintile selection mask (dates x
tickers), every timing rule becomes a daily "hold" mask. A combo's daily
positions = selected & hold, lagged one day (decide at close t, earn t+1),
equal-weighted, net of turnover commission. Everything is matrix algebra, so
the full grid runs in seconds rather than the per-day-loop engine's hours.
"""

from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from backtester.data import load_prices

MEAS_START = "2000-01-01"     # measurement window start
BUFFER_START = "1998-01-01"   # load earlier so 252-day indicators are warm at 2000
END = "2026-07-01"
COMMISSION = 0.001            # 10 bps charged on |weight change| (both sides)
TRADING_DAYS = 252
SEED = 42

# ---------------------------------------------------------------- data loading
def load_matrices():
    prices = load_prices(None, start=BUFFER_START, end=END)
    close = pd.DataFrame({t: df["Close"] for t, df in prices.items()}).sort_index()
    high = pd.DataFrame({t: df["High"] for t, df in prices.items()}).reindex_like(close)
    low = pd.DataFrame({t: df["Low"] for t, df in prices.items()}).reindex_like(close)
    # Drop SPY from the tradable universe; keep it as the benchmark/relative ref.
    spy = close["SPY"] if "SPY" in close else None
    universe = [c for c in close.columns if c != "SPY"]
    close_u = close[universe]
    return close_u, high[universe], low[universe], spy, close


def rolling_return(close, w):
    return close / close.shift(w) - 1.0


# ------------------------------------------------------------------- pickers
def build_pickers(close, spy):
    """Each picker -> daily bool selection mask (top quintile, monthly rebalance)."""
    dates = close.index
    reb_dates = pd.Series(dates, index=dates).groupby([dates.year, dates.month]).first().values
    reb_dates = pd.DatetimeIndex(reb_dates)

    ret_126 = rolling_return(close, 126)                 # 6-month momentum
    ret_21 = rolling_return(close, 21)                   # 1-month (reversal)
    vol_63 = close.pct_change().rolling(63).std()        # 3-month volatility
    high_252 = close.rolling(252).max()
    prox_high = close / high_252                         # nearness to 52wk high
    spy_126 = (spy / spy.shift(126) - 1.0) if spy is not None else None
    rel_strength = ret_126.sub(spy_126, axis=0) if spy_126 is not None else ret_126

    def quintile_mask(factor, top=True):
        """At each rebalance date, pick the top (or bottom) 20% by factor."""
        fr = factor.loc[factor.index.isin(reb_dates)]
        valid = close.loc[fr.index].notna() & fr.notna()
        pr = fr.where(valid).rank(axis=1, pct=True)
        sel = (pr >= 0.8) if top else (pr <= 0.2)
        sel = sel.where(valid, False)
        return sel.reindex(close.index).ffill().fillna(False).astype(bool)

    rng = np.random.default_rng(SEED)

    def random_mask():
        out = pd.DataFrame(False, index=reb_dates, columns=close.columns)
        for r in reb_dates:
            avail = close.loc[r].notna()
            names = close.columns[avail.values]
            if len(names):
                k = max(1, int(round(0.20 * len(names))))  # size-matched to quintile
                pick = rng.choice(names, size=k, replace=False)
                out.loc[r, pick] = True
        return out.reindex(close.index).ffill().fillna(False).astype(bool)

    return {
        "Momentum": quintile_mask(ret_126, top=True),
        "RelStrength": quintile_mask(rel_strength, top=True),
        "LowVol": quintile_mask(vol_63, top=False),
        "NearHigh": quintile_mask(prox_high, top=True),
        "ShortRevers": quintile_mask(ret_21, top=False),
        "Random": random_mask(),
    }


# --------------------------------------------------------------- timing rules
def ema(df, span):
    return df.ewm(span=span, adjust=False).mean()


def wilder_rsi(close, period=14):
    d = close.diff()
    gain = d.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-d.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100)


def state_machine(enter, exit_):
    """Hold=1 from an enter signal until an exit signal (vectorized ffill)."""
    s = pd.DataFrame(np.nan, index=enter.index, columns=enter.columns)
    s = s.mask(enter, 1.0).mask(exit_ & ~enter, 0.0)
    return s.ffill().fillna(0.0).astype(bool)


def build_timing(close, high, low, spy):
    rets = close.pct_change()
    ma50, ma200 = close.rolling(50).mean(), close.rolling(200).mean()
    rsi = wilder_rsi(close)
    macd = ema(close, 12) - ema(close, 26)
    signal = ema(macd, 9)
    m20, s20 = close.rolling(20).mean(), close.rolling(20).std()
    upper, lower = m20 + 2 * s20, m20 - 2 * s20
    ret_252 = rolling_return(close, 252)
    spy_252 = (spy / spy.shift(252) - 1.0) if spy is not None else None
    hi252, lo50 = close.rolling(252).max(), close.rolling(50).min()
    vol20 = rets.rolling(20).std()
    vol_med = vol20.rolling(252).median()

    always = pd.DataFrame(True, index=close.index, columns=close.columns)

    # Trend + 8% stop-loss needs entry tracking -> one vectorized pass over days.
    trend = close > ma200
    tv, cv = trend.values, close.values
    hold = np.zeros_like(cv, dtype=bool)
    entry = np.full(cv.shape[1], np.nan)
    for i in range(cv.shape[0]):
        px = cv[i]
        in_pos = ~np.isnan(entry)
        stopped = in_pos & (px < 0.92 * entry)          # down 8% from entry
        exit_now = stopped | (~tv[i] & in_pos)
        entry[exit_now] = np.nan
        enter_now = (~in_pos) & tv[i] & ~np.isnan(px)
        entry[enter_now] = px[enter_now]
        hold[i] = ~np.isnan(entry)
    trend_stop = pd.DataFrame(hold, index=close.index, columns=close.columns)

    return {
        "BuyHold": always,
        "MACross": (ma50 > ma200).fillna(False),
        "RSIrevert": state_machine(rsi < 30, rsi > 70),
        "MACD": (macd > signal).fillna(False),
        "Bollinger": state_machine(close < lower, close > upper),
        "Mom12": (ret_252 > 0).fillna(False),
        "DualMom": ((ret_252 > 0) & (ret_252.sub(spy_252, axis=0) > 0)).fillna(False)
                   if spy_252 is not None else (ret_252 > 0).fillna(False),
        "Turtle": state_machine(close >= hi252, close <= lo50),
        "VolRevert": (vol20 > 1.5 * vol_med).fillna(False),
        "TrendStop": trend_stop,
    }


# ------------------------------------------------------------------- metrics
def stats(daily_ret, spy_cagr):
    eq = (1 + daily_ret).cumprod()
    n = len(daily_ret)
    years = n / TRADING_DAYS
    total = eq.iloc[-1] - 1
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else 0
    sd = daily_ret.std()
    sharpe = np.sqrt(TRADING_DAYS) * daily_ret.mean() / sd if sd > 0 else 0
    mdd = (eq / eq.cummax() - 1).min()
    return {"ret": total, "cagr": cagr, "sharpe": sharpe, "mdd": mdd,
            "vs_spy": cagr - spy_cagr}


def run_combo(sel, hold, rets_np, comm):
    pos = (sel.values & hold.values)
    pos = np.vstack([np.zeros((1, pos.shape[1]), bool), pos[:-1]])  # lag 1 day
    rowsum = pos.sum(axis=1, keepdims=True)
    w = np.where(rowsum > 0, pos / np.maximum(rowsum, 1), 0.0)
    r = np.nan_to_num(rets_np)
    port = (w * r).sum(axis=1)
    turnover = np.abs(np.diff(w, axis=0, prepend=np.zeros((1, w.shape[1])))).sum(axis=1)
    return pd.Series(port - turnover * comm, index=sel.index)


def main():
    print("Loading matrices...", flush=True)
    close, high, low, spy, close_all = load_matrices()
    print(f"{close.shape[1]} tradable tickers, {close.shape[0]} days "
          f"({close.index[0].date()} -> {close.index[-1].date()})", flush=True)

    meas = close.index >= pd.Timestamp(MEAS_START)
    rets = close.pct_change()

    # --- benchmark: SPY buy & hold over the measurement window ---
    spy_meas = spy[meas]
    spy_ret = spy_meas.iloc[-1] / spy_meas.iloc[0] - 1
    spy_years = meas.sum() / TRADING_DAYS
    spy_cagr = (1 + spy_ret) ** (1 / spy_years) - 1
    spy_daily = spy.pct_change()[meas]
    spy_sharpe = np.sqrt(TRADING_DAYS) * spy_daily.mean() / spy_daily.std()
    spy_mdd = ((1 + spy_daily).cumprod() / (1 + spy_daily).cumprod().cummax() - 1).min()
    print(f"\nBENCHMARK  SPY buy&hold {MEAS_START}->{END}: "
          f"ret={spy_ret*100:.1f}%  cagr={spy_cagr*100:.2f}%  "
          f"sharpe={spy_sharpe:.2f}  mdd={spy_mdd*100:.1f}%", flush=True)

    print("\nBuilding pickers...", flush=True)
    pickers = build_pickers(close, spy)
    for name, m in pickers.items():
        avg = m[meas].sum(axis=1).mean()
        print(f"  {name:<12} avg names held/day: {avg:.0f}", flush=True)

    print("\nBuilding timing signals...", flush=True)
    timing = build_timing(close, high, low, spy)
    for name, m in timing.items():
        frac = m[meas].mean().mean()
        print(f"  {name:<12} avg fraction of days 'in': {frac*100:.0f}%", flush=True)

    # --- sanity combo: Random picker + BuyHold ~ equal-weight market ---
    rets_np = rets.values
    sanity = run_combo(pickers["Random"], timing["BuyHold"], rets_np, 0.0)[meas]
    s = stats(sanity, spy_cagr)
    print(f"\nSANITY  Random+BuyHold (no cost): cagr={s['cagr']*100:.2f}%  "
          f"sharpe={s['sharpe']:.2f}  (should roughly track a broad equal-weight index)",
          flush=True)

    # --- full grid ---
    print("\nRunning 6 x 10 = 60 combos...", flush=True)
    rows = []
    for pname, sel in pickers.items():
        for tname, hold in timing.items():
            daily = run_combo(sel, hold, rets_np, COMMISSION)[meas]
            st = stats(daily, spy_cagr)
            rows.append({"picker": pname, "timing": tname, **st})
    df = pd.DataFrame(rows)
    df.to_csv("results/grid_2000_2026.csv", index=False)

    beat = (df["cagr"] > spy_cagr).sum()
    print(f"\n{'='*82}")
    print(f"RESULTS — 60 combos, 2000-2026, net of {COMMISSION*1e4:.0f}bps costs, "
          f"vs SPY cagr {spy_cagr*100:.2f}%")
    print(f"{beat} of 60 combos beat SPY on CAGR.")
    print(f"{'='*82}")

    def show(sub, title):
        print(f"\n{title}")
        print(f"{'Picker':<13}{'Timing':<12}{'CAGR':>8}{'TotRet':>10}{'Sharpe':>8}{'MaxDD':>8}{'vsSPY':>8}")
        for _, r in sub.iterrows():
            print(f"{r['picker']:<13}{r['timing']:<12}{r['cagr']*100:>7.1f}%"
                  f"{r['ret']*100:>9.0f}%{r['sharpe']:>8.2f}{r['mdd']*100:>7.1f}%"
                  f"{r['vs_spy']*100:>+7.1f}%")

    show(df.sort_values("sharpe", ascending=False).head(15), "TOP 15 BY SHARPE:")
    show(df.sort_values("cagr", ascending=False).head(10), "TOP 10 BY CAGR:")
    show(df.sort_values("sharpe").head(5), "WORST 5 BY SHARPE:")

    # best timing per picker
    print("\nBEST TIMING PER PICKER (by Sharpe):")
    for pname in pickers:
        best = df[df["picker"] == pname].sort_values("sharpe", ascending=False).iloc[0]
        print(f"  {pname:<13} -> {best['timing']:<12} sharpe={best['sharpe']:.2f} "
              f"cagr={best['cagr']*100:.1f}%")
    print(f"\nFull table saved to results/grid_2000_2026.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
