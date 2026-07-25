"""Out-of-sample validation — tell a real edge from an overfit one.

Sweeping 100 combos and crowning the highest number is p-hacking: with that many
tries, the "winner" is partly luck. This harness runs the honest checks.

It runs every combo once over the full span (net of commission + slippage +
tax, survivorship-corrected by default), records each one's daily equity, then
slices those curves two ways:

  holdout      Split at --split. Rank combos by their TRAIN-window return, then
               look at how those same combos do on the UNTOUCHED TEST window.
               Reports the rank-decay (does in-sample skill persist?) and the
               single "pick the train winner, test once" out-of-sample result —
               the number that isn't cherry-picked.

  walkforward  Roll through time: each step, pick the combo with the best return
               over the trailing --train-years, then earn the NEXT --step-years
               with it (out-of-sample). Chain those OOS chunks into one track
               record and compare it to SPY. This simulates actually running the
               thing: every decision uses only past data.

Both modes read the same run-once equity curves. That treats a strategy as a
single continuous portfolio (taxes accrue along the path); the walk-forward
"switch to this year's pick" approximation ignores the tax cost of switching
baskets between windows, so it slightly flatters the adaptive strategy — noted,
not fatal. Fundamental pickers stay snapshot-biased regardless; --price-only
restricts to the trustworthy momentum/relative_strength/random pickers.

Examples:
    python walkforward.py holdout --split 2016-01-01
    python walkforward.py walkforward --train-years 5 --step-years 1 --price-only
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import pandas as pd

from backtester import Backtest, Combo, MarketData, TaxPolicy, load_prices
from strategies.buy_and_hold import BuyAndHold
from strategies.pickers import PICKERS, PRICE_ONLY_PICKERS
from strategies.timers import TIMERS
from grid_combos import build_market

# ---- shared run config, set once, reused by every worker -----------------
_W: dict = {}


def _init_worker(tickers, start, end, universe, cash, commission_pct, slippage_pct,
                 st_rate, lt_rate):
    prices = load_prices(tickers, start=start, end=end)
    _W.update(
        market=build_market(prices, universe),
        cash=cash,
        commission_pct=commission_pct,
        slippage_pct=slippage_pct,
        policy=TaxPolicy(short_term_rate=st_rate, long_term_rate=lt_rate),
        top_n=15,
        rebalance="M",
    )


def _run_curve(combo) -> tuple[str, str, np.ndarray]:
    """Run one combo over the full span; return its daily total-equity curve."""
    pname, tname = combo
    res = Backtest(
        Combo(PICKERS[pname](), TIMERS[tname](), top_n=_W["top_n"], rebalance=_W["rebalance"]),
        cash=_W["cash"], commission_pct=_W["commission_pct"],
        slippage_pct=_W["slippage_pct"], market=_W["market"], tax_policy=_W["policy"],
    ).run()
    return pname, tname, res.equity["total"].to_numpy()


# ---- window metrics ------------------------------------------------------
def _slice_bounds(dates: pd.DatetimeIndex, start, end) -> tuple[int, int] | None:
    lo = dates.searchsorted(pd.Timestamp(start), side="left")
    hi = dates.searchsorted(pd.Timestamp(end), side="right") - 1
    if hi <= lo:
        return None
    return lo, hi


def window_cagr(dates, totals, start, end) -> float:
    b = _slice_bounds(dates, start, end)
    if b is None:
        return float("nan")
    lo, hi = b
    yrs = (dates[hi] - dates[lo]).days / 365.25
    if yrs <= 0 or totals[lo] <= 0:
        return float("nan")
    return (totals[hi] / totals[lo]) ** (1 / yrs) - 1.0


def window_return(dates, totals, start, end) -> float:
    b = _slice_bounds(dates, start, end)
    if b is None:
        return float("nan")
    lo, hi = b
    return totals[hi] / totals[lo] - 1.0 if totals[lo] > 0 else float("nan")


# ---- run all combos once, capture curves ---------------------------------
def run_all_curves(args):
    prices = load_prices(args.tickers, start=args.start, end=args.end)
    dates = None
    combos = list(itertools.product(
        [p for p in PICKERS if not args.price_only or p in PRICE_ONLY_PICKERS],
        list(TIMERS),
    ))
    print(f"Loaded {len(prices)} tickers; running {len(combos)} combos once "
          f"(net-of-everything, universe={args.universe}) on {args.jobs} core(s)...")

    curves: dict[tuple[str, str], np.ndarray] = {}
    init = (args.tickers, args.start, args.end, args.universe, args.cash,
            args.commission_pct, args.slippage_pct, args.st_rate, args.lt_rate)
    t0 = time.time()
    if args.jobs == 1:
        _init_worker(*init)
        dates = _W["market"].calendar
        for c in combos:
            pn, tn, tot = _run_curve(c)
            curves[(pn, tn)] = tot
    else:
        with ProcessPoolExecutor(max_workers=args.jobs, initializer=_init_worker,
                                 initargs=init) as ex:
            for pn, tn, tot in ex.map(_run_curve, combos, chunksize=1):
                curves[(pn, tn)] = tot
        # Rebuild the calendar in the parent (cheap) for slicing.
        dates = build_market(load_prices(args.tickers, start=args.start, end=args.end),
                             args.universe).calendar

    # SPY buy&hold on the same calendar, net-of-everything.
    spy_market = MarketData({"SPY": prices["SPY"]})
    spy = Backtest(BuyAndHold(), cash=args.cash, commission_pct=args.commission_pct,
                   slippage_pct=args.slippage_pct, market=spy_market,
                   tax_policy=TaxPolicy(args.st_rate, args.lt_rate)).run()
    spy_curve = spy.equity["total"].reindex(dates).ffill().to_numpy()
    print(f"Ran {len(curves)} combos in {time.time()-t0:.1f}s.\n")
    return dates, curves, spy_curve


# ---- mode: holdout -------------------------------------------------------
def holdout(args):
    dates, curves, spy = run_all_curves(args)
    split = pd.Timestamp(args.split)
    tr = (dates[0], split)
    te = (split, dates[-1])

    rows = []
    for (pn, tn), tot in curves.items():
        rows.append({
            "picker": pn, "timer": tn,
            "train_cagr": window_cagr(dates, tot, *tr),
            "test_cagr": window_cagr(dates, tot, *te),
        })
    df = pd.DataFrame(rows).dropna()
    spy_train = window_cagr(dates, spy, *tr)
    spy_test = window_cagr(dates, spy, *te)

    print("=" * 74)
    print(f"HOLDOUT — train {tr[0].date()}..{split.date()}  |  "
          f"test {split.date()}..{te[1].date()}   (after-tax CAGR)")
    print("=" * 74)
    print(f"SPY: train {spy_train*100:5.1f}%   test {spy_test*100:5.1f}%\n")

    df = df.sort_values("train_cagr", ascending=False)
    print(f"{'rank':>4}  {'picker':<18}{'timer':<14}{'TRAIN':>8}{'TEST':>8}"
          f"{'testVsSPY':>10}")
    for i, (_, r) in enumerate(df.head(10).iterrows(), 1):
        print(f"{i:>4}  {r['picker']:<18}{r['timer']:<14}"
              f"{r['train_cagr']*100:>7.1f}%{r['test_cagr']*100:>7.1f}%"
              f"{(r['test_cagr']-spy_test)*100:>+9.1f}%")

    # Overfitting diagnostics.
    spearman = df["train_cagr"].corr(df["test_cagr"], method="spearman")
    best = df.iloc[0]
    top10 = df.head(10)
    print("\n" + "-" * 74)
    print(f"Rank persistence (Spearman train vs test): {spearman:+.2f}   "
          "(≈0 ⇒ in-sample rank is ~noise out-of-sample)")
    print(f"Top-10-on-train that beat SPY out-of-sample: "
          f"{int((top10['test_cagr'] > spy_test).sum())}/10")
    print(f"All combos that beat SPY out-of-sample:      "
          f"{int((df['test_cagr'] > spy_test).sum())}/{len(df)}")
    print("\nTHE HONEST TEST — pick the train winner, judge once on test:")
    print(f"  {best['picker']} x {best['timer']}:  "
          f"test {best['test_cagr']*100:.1f}%  vs SPY {spy_test*100:.1f}%  "
          f"({'BEATS' if best['test_cagr']>spy_test else 'LOSES TO'} SPY by "
          f"{abs(best['test_cagr']-spy_test)*100:.1f}%/yr)")


# ---- mode: walkforward ---------------------------------------------------
def walkforward(args):
    dates, curves, spy = run_all_curves(args)
    start_y = dates[0].year + args.train_years
    end_y = dates[-1].year
    combos = list(curves)

    print("=" * 74)
    print(f"WALK-FORWARD — train {args.train_years}y, step {args.step_years}y, "
          f"pick best trailing after-tax return each step")
    print("=" * 74)
    print(f"{'OOS window':<24}{'picked combo':<32}{'combo':>8}{'SPY':>8}")

    oos_growth = 1.0
    spy_growth = 1.0
    picks = []
    y = start_y
    while y < end_y:
        tr_start = pd.Timestamp(f"{y-args.train_years}-01-01")
        tr_end = pd.Timestamp(f"{y}-01-01")
        te_end = pd.Timestamp(f"{min(y+args.step_years, end_y+1)}-01-01")
        # Rank combos on the trailing train window.
        scored = [(window_cagr(dates, curves[c], tr_start, tr_end), c) for c in combos]
        scored = [(v, c) for v, c in scored if v == v]  # drop NaN
        if not scored:
            y += args.step_years
            continue
        _, best = max(scored, key=lambda x: x[0])
        r = window_return(dates, curves[best], tr_end, te_end)
        sr = window_return(dates, spy, tr_end, te_end)
        if r == r and sr == sr:
            oos_growth *= 1 + r
            spy_growth *= 1 + sr
            picks.append(best)
            print(f"{tr_end.date()}..{te_end.date():}  "
                  f"{best[0]+' x '+best[1]:<32}{r*100:>+7.1f}%{sr*100:>+7.1f}%")
        y += args.step_years

    n_years = (dates[-1] - pd.Timestamp(f"{start_y}-01-01")).days / 365.25
    oos_cagr = oos_growth ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    spy_cagr = spy_growth ** (1 / n_years) - 1 if n_years > 0 else float("nan")
    print("\n" + "-" * 74)
    print(f"Chained OUT-OF-SAMPLE ({start_y}..{end_y}, {n_years:.0f}y):")
    print(f"  Adaptive (pick trailing winner): CAGR {oos_cagr*100:5.1f}%  "
          f"(grew {oos_growth:.2f}x)")
    print(f"  SPY buy & hold:                  CAGR {spy_cagr*100:5.1f}%  "
          f"(grew {spy_growth:.2f}x)")
    verdict = "BEATS" if oos_cagr > spy_cagr else "LOSES TO"
    print(f"  => Adaptive {verdict} SPY out-of-sample by "
          f"{abs(oos_cagr-spy_cagr)*100:.1f}%/yr")
    from collections import Counter
    print(f"\nMost-picked combos: "
          f"{', '.join(f'{p[0]}x{p[1]}({n})' for p,n in Counter(picks).most_common(5))}")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["holdout", "walkforward"])
    ap.add_argument("--tickers", nargs="+")
    ap.add_argument("--start", default="2000-01-01")
    ap.add_argument("--end", default="2026-12-31")
    ap.add_argument("--universe", default="sp500-pit", choices=["all", "sp500-pit"])
    ap.add_argument("--price-only", action="store_true",
                    help="Only trustworthy price pickers (momentum/rel-strength/random).")
    ap.add_argument("--split", default="2016-01-01", help="Holdout train/test boundary.")
    ap.add_argument("--train-years", type=int, default=5)
    ap.add_argument("--step-years", type=int, default=1)
    ap.add_argument("--cash", type=float, default=100_000.0)
    ap.add_argument("--commission-pct", type=float, default=0.0005)
    ap.add_argument("--slippage-pct", type=float, default=0.0005)
    ap.add_argument("--st-rate", type=float, default=0.35)
    ap.add_argument("--lt-rate", type=float, default=0.15)
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()

    if args.mode == "holdout":
        holdout(args)
    else:
        walkforward(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
