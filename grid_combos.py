"""Sweep every picker x timer combo and rank them against the S&P 500.

This is the payoff of the composable design: from 10 pickers and 10 timers it
backtests up to 100 strategies over one date range, then reports which picker
wins, which timer wins, and which *pairing* wins on a risk-adjusted basis —
always benchmarked against just buying and holding SPY.

Examples:
    # Price-only pickers over the full liquid universe (no fundamentals needed):
    python grid_combos.py --price-only --start 2010-01-01

    # All 100 combos on a recent window (needs data/fundamentals.csv):
    python grid_combos.py --start 2022-01-01 --top-n 15

    # A focused pairing study:
    python grid_combos.py --pickers momentum value_pe --timers turtle rsi

Fundamental pickers rely on a *current* snapshot (fetch_fundamentals.py) and are
only meaningful over a recent window — see that script's header. Use
--price-only to exclude them for honest long-history runs.
"""

from __future__ import annotations

import argparse
import itertools
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

from backtester import Backtest, Combo, MarketData, TaxPolicy, load_prices
from backtester.data import universe_tickers
from strategies.buy_and_hold import BuyAndHold
from strategies.pickers import PICKERS, PRICE_ONLY_PICKERS
from strategies.timers import SWEEP_TIMERS, TIMERS

RESULTS_DIR = Path(__file__).parent / "results"


# ---- parallel worker plumbing -------------------------------------------
# Each worker process builds the shared market once (from disk, to avoid
# pickling hundreds of DataFrames across the process boundary) and then runs
# whatever combos the pool hands it against that one market.
_W: dict = {}


def build_market(prices, universe: str) -> MarketData:
    """Build a MarketData, optionally with a point-in-time membership filter."""
    members = None
    if universe == "sp500-pit":
        from backtester.data import trading_calendar
        from backtester.universe import load_membership, members_by_calendar

        cal = trading_calendar(prices)
        members = members_by_calendar(
            load_membership(), cal, restrict_to=set(prices)
        )
    return MarketData(prices, members_by_day=members)


def _init_worker(tickers, start, end, cash, commission_pct, top_n, rebalance,
                 universe, slippage_pct, tax_policy):
    prices = load_prices(tickers, start=start, end=end)
    _W.update(
        market=build_market(prices, universe),
        cash=cash,
        commission_pct=commission_pct,
        top_n=top_n,
        rebalance=rebalance,
        slippage_pct=slippage_pct,
        tax_policy=tax_policy,
    )


def _metrics(pname, tname, res) -> dict:
    row = {
        "picker": pname,
        "timer": tname,
        "cagr": res.cagr,
        "sharpe": res.sharpe,
        "max_drawdown": res.max_drawdown,
        "total_return": res.total_return,
        "trades": len(res.trades),
        "final_value": res.final_value,
    }
    if res.taxes_paid is not None:
        row["after_tax_cagr"] = res.after_tax_cagr
        row["after_tax_total_return"] = res.after_tax_total_return
        row["total_tax"] = res.total_tax
    return row


def _make_backtest(pname, tname, market, cash, commission_pct, top_n, rebalance,
                   slippage_pct, tax_policy):
    strat = Combo(PICKERS[pname](), TIMERS[tname](), top_n=top_n, rebalance=rebalance)
    return Backtest(strat, cash=cash, commission_pct=commission_pct, market=market,
                    slippage_pct=slippage_pct, tax_policy=tax_policy)


def _run_one(combo) -> dict:
    pname, tname = combo
    res = _make_backtest(
        pname, tname, _W["market"], _W["cash"], _W["commission_pct"],
        _W["top_n"], _W["rebalance"], _W["slippage_pct"], _W["tax_policy"],
    ).run()
    return _metrics(pname, tname, res)


def benchmark_spy(prices, cash, commission_pct, slippage_pct, tax_policy):
    """Buy-and-hold SPY through the same engine, as the yardstick.

    Uses a SPY-only market so BuyAndHold holds just SPY (not the whole
    universe), while still pricing it on the same trading calendar. With taxes
    on, this is the after-tax bar to beat — SPY defers its gains and pays
    long-term rates only at terminal liquidation.
    """
    if "SPY" not in prices:
        return None
    spy_market = MarketData({"SPY": prices["SPY"]})
    return Backtest(
        BuyAndHold(), cash=cash, commission_pct=commission_pct, market=spy_market,
        slippage_pct=slippage_pct, tax_policy=tax_policy,
    ).run()


def run_grid(args) -> pd.DataFrame:
    # No explicit list = the stock-picking universe (UNIVERSE_EXCLUDE left out).
    tickers = args.tickers or universe_tickers()
    prices = load_prices(tickers, start=args.start, end=args.end)
    print(f"Loaded {len(prices)} tickers "
          f"({min(df.index.min() for df in prices.values()).date()} "
          f"-> {max(df.index.max() for df in prices.values()).date()})")

    if args.universe == "sp500-pit":
        print("Universe: point-in-time S&P 500 members (survivorship-aware; "
              "note delisted names' data is still unavailable).")
    else:
        print("Universe: all tickers with data (survivorship-biased).")

    tax_policy = None
    if args.tax:
        tax_policy = TaxPolicy(short_term_rate=args.st_rate, long_term_rate=args.lt_rate)
        print(f"Costs: commission {args.commission_pct*1e4:.0f}bps, "
              f"slippage {args.slippage_pct*1e4:.0f}bps, "
              f"tax ST {args.st_rate*100:.0f}%/LT {args.lt_rate*100:.0f}% "
              f"(ranking by AFTER-TAX CAGR).")
    else:
        print(f"Costs: commission {args.commission_pct*1e4:.0f}bps, "
              f"slippage {args.slippage_pct*1e4:.0f}bps, no tax (gross).")

    picker_names = args.pickers or list(PICKERS)
    if args.price_only:
        picker_names = [p for p in picker_names if p in PRICE_ONLY_PICKERS]
    timer_names = args.timers or list(SWEEP_TIMERS)

    spy = benchmark_spy(prices, args.cash, args.commission_pct, args.slippage_pct, tax_policy)
    # The bar to beat: after-tax CAGR when taxes are on, else gross CAGR.
    spy_cagr = (spy.after_tax_cagr if tax_policy else spy.cagr) if spy else float("nan")
    if spy:
        extra = (f"  ->  after-tax CAGR {spy.after_tax_cagr*100:5.1f}%"
                 if tax_policy else "")
        print(f"Benchmark  SPY buy&hold:  CAGR {spy.cagr*100:5.1f}%   "
              f"Sharpe {spy.sharpe:4.2f}   MaxDD {spy.max_drawdown*100:5.1f}%{extra}\n")

    combos = list(itertools.product(picker_names, timer_names))
    total = len(combos)
    jobs = max(1, args.jobs)
    print(f"Running {total} combos ({len(picker_names)} pickers x "
          f"{len(timer_names)} timers) on {jobs} core(s)...\n")

    rows = []
    t0 = time.time()
    if jobs == 1:
        # Serial: build the shared market once, reuse for every combo.
        market = build_market(prices, args.universe)
        for i, (pname, tname) in enumerate(combos, 1):
            res = _make_backtest(
                pname, tname, market, args.cash, args.commission_pct,
                args.top_n, args.rebalance, args.slippage_pct, tax_policy,
            ).run()
            rows.append(_metrics(pname, tname, res))
            eta = (time.time() - t0) / i * (total - i)
            print(f"  [{i:>3}/{total}] {pname:<18} x {tname:<14} "
                  f"CAGR {res.cagr*100:6.1f}%  Sharpe {res.sharpe:5.2f}  (ETA {eta:4.0f}s)")
    else:
        # Parallel: each worker builds its own market once, then runs a share
        # of the combos. Results can complete out of order.
        init = (tickers, args.start, args.end, args.cash,
                args.commission_pct, args.top_n, args.rebalance, args.universe,
                args.slippage_pct, tax_policy)
        with ProcessPoolExecutor(
            max_workers=jobs, initializer=_init_worker, initargs=init
        ) as ex:
            for i, row in enumerate(ex.map(_run_one, combos, chunksize=1), 1):
                rows.append(row)
                eta = (time.time() - t0) / i * (total - i)
                print(f"  [{i:>3}/{total}] {row['picker']:<18} x {row['timer']:<14} "
                      f"CAGR {row['cagr']*100:6.1f}%  Sharpe {row['sharpe']:5.2f}  "
                      f"(ETA {eta:4.0f}s)")

    df = pd.DataFrame(rows)
    # Score on the net metric: after-tax CAGR when taxes are on, else gross CAGR.
    df["net_cagr"] = df["after_tax_cagr"] if "after_tax_cagr" in df else df["cagr"]
    df["excess_cagr"] = df["net_cagr"] - spy_cagr
    df.attrs["spy_cagr"] = spy_cagr
    df.attrs["spy_sharpe"] = spy.sharpe if spy else float("nan")
    df.attrs["taxed"] = tax_policy is not None
    print(f"\nSwept {total} combos in {time.time()-t0:.1f}s.")
    return df


def report(df: pd.DataFrame, sort_by: str, top: int) -> None:
    spy_cagr = df.attrs.get("spy_cagr", float("nan"))
    spy_sharpe = df.attrs.get("spy_sharpe", float("nan"))
    taxed = df.attrs.get("taxed", False)
    # When taxes are on, rank and compare on after-tax CAGR by default.
    if taxed and sort_by in ("sharpe", "cagr"):
        sort_by = "net_cagr"

    print("\n" + "=" * 70)
    print(f"TOP {top} COMBOS BY {sort_by.upper()}" + ("  (after-tax)" if taxed else ""))
    print("=" * 70)
    best = df.sort_values(sort_by, ascending=False).head(top)
    net_label = "AftTaxCAGR" if taxed else "CAGR"
    print(f"{'picker':<18}{'timer':<15}{'GrossCAGR':>10}{net_label:>11}"
          f"{'Sharpe':>8}{'MaxDD':>8}{'vsSPY':>8}")
    for _, r in best.iterrows():
        print(f"{r['picker']:<18}{r['timer']:<15}{r['cagr']*100:>9.1f}%"
              f"{r['net_cagr']*100:>10.1f}%{r['sharpe']:>8.2f}"
              f"{r['max_drawdown']*100:>7.1f}%{r['excess_cagr']*100:>+7.1f}%")

    # Which picker / which timer wins on average?
    print("\n" + "-" * 70)
    print("AVERAGE SHARPE BY PICKER (across timers):")
    for name, v in df.groupby("picker")["sharpe"].mean().sort_values(ascending=False).items():
        print(f"  {name:<20}{v:>6.2f}")
    print("\nAVERAGE SHARPE BY TIMER (across pickers):")
    for name, v in df.groupby("timer")["sharpe"].mean().sort_values(ascending=False).items():
        print(f"  {name:<20}{v:>6.2f}")

    n_beat = int((df["net_cagr"] > spy_cagr).sum())
    print("\n" + "-" * 70)
    bar = "after-tax " if taxed else ""
    print(f"SPY buy&hold {bar}CAGR: {spy_cagr*100:.1f}%  (Sharpe {spy_sharpe:.2f})")
    print(f"{n_beat}/{len(df)} combos beat SPY on {bar}CAGR.")

    # Sharpe matrix (picker rows x timer cols) for a quick eyeball.
    print("\n" + "-" * 70)
    print("SHARPE MATRIX (rows=picker, cols=timer):")
    mat = df.pivot(index="picker", columns="timer", values="sharpe")
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(mat.round(2).to_string())


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--tickers", nargs="+",
                    help="Universe (default: all in data/ except UNIVERSE_EXCLUDE).")
    ap.add_argument("--start", help="Start date YYYY-MM-DD.")
    ap.add_argument("--end", help="End date YYYY-MM-DD.")
    ap.add_argument("--pickers", nargs="+", choices=list(PICKERS), help="Subset of pickers.")
    ap.add_argument("--timers", nargs="+", choices=list(TIMERS), help="Subset of timers.")
    ap.add_argument("--price-only", action="store_true",
                    help="Exclude fundamental pickers (honest for long history).")
    ap.add_argument("--top-n", type=int, default=15, help="Names held per combo.")
    ap.add_argument("--rebalance", default="M", choices=["D", "W", "M", "Q"],
                    help="Picker rebalance cadence.")
    ap.add_argument("--cash", type=float, default=100_000.0)
    ap.add_argument("--commission-pct", type=float, default=0.0005, help="Per-trade cost (5bps default).")
    ap.add_argument("--slippage-pct", type=float, default=0.0,
                    help="Per-trade slippage as a fraction (0.0005 = 5bps). Buys fill up, sells down.")
    ap.add_argument("--tax", action="store_true",
                    help="Model capital-gains tax (ST/LT lots, annual settlement, "
                         "terminal liquidation). Ranks by AFTER-TAX CAGR vs after-tax SPY.")
    ap.add_argument("--st-rate", type=float, default=0.35, help="Short-term cap-gains rate.")
    ap.add_argument("--lt-rate", type=float, default=0.15, help="Long-term cap-gains rate.")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 1),
                    help="Parallel worker processes (default: CPUs-1).")
    ap.add_argument("--universe", default="all", choices=["all", "sp500-pit"],
                    help="'all' = every ticker with data; 'sp500-pit' = only "
                         "actual S&P 500 members on each date (survivorship-aware).")
    ap.add_argument("--sort-by", default="sharpe",
                    choices=["sharpe", "cagr", "net_cagr", "excess_cagr", "total_return"])
    ap.add_argument("--top", type=int, default=15, help="How many top combos to print.")
    ap.add_argument("--out", default=str(RESULTS_DIR / "combo_grid.csv"),
                    help="Where to write the full results CSV.")
    args = ap.parse_args()

    df = run_grid(args)
    report(df, args.sort_by, args.top)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.sort_values(args.sort_by, ascending=False).to_csv(out, index=False)
    print(f"\nWrote full results to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
