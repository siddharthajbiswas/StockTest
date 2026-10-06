"""Full evidence run for strategies/tax_managed.py, in the project's own engine.

Everything here is the real Backtest loop with real tax lots -- no research
shortcuts. Writes a JSON summary next to itself and prints the tables.

    .venv/bin/python research/tax_managed_report.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backtester import Backtest, MarketData, Strategy, TaxManagedCombo, TaxPolicy, load_prices
from strategies.tax_managed import DEFAULT_MENU, TaxManagedMomentum

WARM = "1997-01-01"          # load this far back so the 12-1 signal is warm
DATA_END = "2026-07-01"
CASH = 100_000.0
COMM, SLIP = 0.0005, 0.0005  # 5bps commission + 5bps slippage, each side

# California single filer, ~$300k taxable income, 2025 schedule:
#   short: 35% federal + 3.8% NIIT + 9.3% CA  = 48.1%
#   long:  15% federal + 3.8% NIIT + 9.3% CA  = 28.1%
CA_300K = (0.481, 0.281)
BRACKETS = {
    "CA ~$120k": (0.333, 0.243),
    "CA ~$300k": CA_300K,
    "CA ~$700k": (0.521, 0.351),
    "CA ~$1.5M": (0.541, 0.371),
}

_markets: dict[str, MarketData] = {}


def market_to(end: str) -> MarketData:
    if end not in _markets:
        prices = load_prices(sorted(set(DEFAULT_MENU) | {"SPY"}), start=WARM, end=end)
        _markets[end] = MarketData(prices)
    return _markets[end]


def gated(start, **kw):
    """The shipped strategy, held in cash until `start`, so a window can begin
    anywhere while the signal still sees the warm-up history before it."""
    combo = TaxManagedMomentum(**kw)
    combo.__class__ = type("Gated", (TaxManagedCombo,), {
        "start": pd.Timestamp(start),
        "on_day": lambda self, ctx: (
            None if ctx.date < self.start else TaxManagedCombo.on_day(self, ctx)
        ),
    })
    return combo


def random_pick(start, seed=0, **kw):
    """Control: identical machinery, random ranking. Isolates how much of the
    result is the momentum signal rather than the tax rule."""
    from backtester import Picker

    class RandomRank(Picker):
        name = "random_rank"

        def initialize(self, ctx):
            self._rng = np.random.default_rng(seed)

        def select(self, ctx, universe, n):
            pool = [t for t in universe if ctx.price(t) is not None]
            if not pool:
                return []
            order = self._rng.permutation(len(pool))
            return [pool[i] for i in order[:n]]

    combo = gated(start, **kw)
    combo.picker = RandomRank()
    return combo


class BuyHold(Strategy):
    def __init__(self, ticker, start):
        self.ticker, self.start = ticker, pd.Timestamp(start)

    def initialize(self, ctx):
        self.done = False

    def on_day(self, ctx):
        if not self.done and ctx.date >= self.start and ctx.price(self.ticker):
            ctx.order_target_percent(self.ticker, 1.0)
            self.done = True


def run_one(strategy, start, end, rates=CA_300K, comm=COMM, slip=SLIP):
    market = market_to(end)
    policy = TaxPolicy(short_term_rate=rates[0], long_term_rate=rates[1]) if rates else None
    res = Backtest(strategy, market=market, cash=CASH, commission_pct=comm,
                   slippage_pct=slip, tax_policy=policy).run()
    eq = res.equity["total"]
    i0 = eq.index.searchsorted(pd.Timestamp(start))
    sub = eq.iloc[i0:]
    years = (eq.index[-1] - eq.index[i0]).days / 365.25
    final = res.final_value - (res.terminal_tax or 0.0)
    r = sub.pct_change().dropna()
    return dict(
        # Base on the cash actually committed, not the first day's CLOSE — that
        # close is already net of the entry's commission and slippage, and using
        # it would quietly credit a strategy for its own trading costs.
        cagr=(final / CASH) ** (1 / years) - 1,
        final=final,
        maxdd=float((sub / sub.cummax() - 1).min()),
        sharpe=float(np.sqrt(252) * r.mean() / r.std()) if r.std() else 0.0,
        tax=res.total_tax, trades=len(res.trades), years=years,
    )


def pair(start, end, rates=CA_300K, comm=COMM, slip=SLIP, **kw):
    s = run_one(gated(start, **kw), start, end, rates, comm, slip)
    b = run_one(BuyHold("SPY", start), start, end, rates, comm, slip)
    return s, b


def hdr(title):
    print(f"\n{title}\n" + "-" * len(title))


def main():
    out: dict = {}

    hdr("1. HEADLINE  (California ~$300k bracket, 5bps commission + 5bps slippage each side)")
    print(f"{'window':<24}{'years':>6}{'strategy':>10}{'SPY':>9}{'excess':>9}"
          f"{'str.DD':>9}{'SPY DD':>9}{'str.Sh':>8}{'SPY Sh':>8}{'trades':>8}")
    FIXED = [("1998-04-01", DATA_END), ("1998-04-01", "2008-04-01"), ("2000-03-01", "2010-03-01"),
             ("2003-01-01", "2013-01-01"), ("2007-10-01", "2017-10-01"), ("2010-01-01", "2020-01-01"),
             ("2013-01-01", "2023-01-01"), ("2016-01-01", DATA_END), ("2020-01-01", DATA_END)]
    rows = []
    for a, b_ in FIXED:
        s, b = pair(a, b_)
        rows.append(dict(start=a, end=b_, strat=s, spy=b))
        print(f"{a[:7]+' -> '+b_[:7]:<24}{s['years']:6.1f}{s['cagr']*100:9.2f}%{b['cagr']*100:8.2f}%"
              f"{(s['cagr']-b['cagr'])*100:+9.2f}{s['maxdd']*100:8.1f}%{b['maxdd']*100:8.1f}%"
              f"{s['sharpe']:8.2f}{b['sharpe']:8.2f}{s['trades']:8d}")
    out["fixed_windows"] = rows

    hdr("2. ROLLING WINDOWS  (every window of this length, stepped 1 year)")
    print(f"{'length':<10}{'windows':>9}{'beat SPY':>10}{'median':>9}{'mean':>9}{'worst':>9}{'best':>9}")
    roll = {}
    for years in (5, 10, 15, 20):
        ex = []
        t = pd.Timestamp("1998-04-01")
        while t + pd.DateOffset(years=years) <= pd.Timestamp(DATA_END):
            e = (t + pd.DateOffset(years=years)).strftime("%Y-%m-%d")
            s, b = pair(t.strftime("%Y-%m-%d"), e)
            ex.append(s["cagr"] - b["cagr"])
            t += pd.DateOffset(years=1)
        a = np.array(ex)
        roll[years] = dict(n=len(a), beat=float((a > 0).mean()), median=float(np.median(a)),
                           mean=float(a.mean()), worst=float(a.min()), best=float(a.max()))
        print(f"{str(years)+'-year':<10}{len(a):9d}{(a>0).mean()*100:9.0f}%{np.median(a)*100:+9.2f}"
              f"{a.mean()*100:+9.2f}{a.min()*100:+9.2f}{a.max()*100:+9.2f}")
    out["rolling"] = roll

    hdr("3. CONTROLS  (1998-04 -> 2026-07)")
    A, B = "1998-04-01", DATA_END
    s, b = pair(A, B)
    print(f"{'momentum ranking + tax rule':<38}{s['cagr']*100:8.2f}%   excess {(s['cagr']-b['cagr'])*100:+.2f}")
    rnd = [run_one(random_pick(A, seed=k), A, B)["cagr"] for k in range(25)]
    rnd = np.array(rnd)
    print(f"{'RANDOM ranking + tax rule (25 seeds)':<38}{rnd.mean()*100:8.2f}%   excess {(rnd.mean()-b['cagr'])*100:+.2f}"
          f"    (p10 {np.percentile(rnd,10)*100:.2f}%  p90 {np.percentile(rnd,90)*100:.2f}%)")
    print(f"{'  -> the real strategy beats':<38}{(rnd < s['cagr']).mean()*100:7.0f}% of random rankings")
    nb = run_one(gated(A, gain_budget=1e9), A, B)
    print(f"{'momentum ranking, NO tax rule':<38}{nb['cagr']*100:8.2f}%   excess {(nb['cagr']-b['cagr'])*100:+.2f}"
          f"    ({nb['trades']} trades vs {s['trades']})")
    print(f"{'SPY buy & hold':<38}{b['cagr']*100:8.2f}%")
    out["controls"] = dict(strategy=s["cagr"], random_mean=float(rnd.mean()),
                           random_beat_pct=float((rnd < s["cagr"]).mean()),
                           no_tax_rule=nb["cagr"], spy=b["cagr"])

    hdr("4. TAX BRACKET SENSITIVITY  (1998-04 -> 2026-07)")
    print(f"{'bracket':<14}{'short/long':>14}{'strategy':>11}{'SPY':>9}{'excess':>9}")
    br = {}
    for name, rates in BRACKETS.items():
        s, b = pair(A, B, rates=rates)
        br[name] = dict(strat=s["cagr"], spy=b["cagr"])
        print(f"{name:<14}{f'{rates[0]*100:.1f}/{rates[1]*100:.1f}%':>14}{s['cagr']*100:10.2f}%"
              f"{b['cagr']*100:8.2f}%{(s['cagr']-b['cagr'])*100:+9.2f}")
    s0 = run_one(gated(A), A, B, rates=None)
    b0 = run_one(BuyHold("SPY", A), A, B, rates=None)
    br["no tax"] = dict(strat=s0["cagr"], spy=b0["cagr"])
    print(f"{'no tax at all':<14}{'-':>14}{s0['cagr']*100:10.2f}%{b0['cagr']*100:8.2f}%{(s0['cagr']-b0['cagr'])*100:+9.2f}"
          "     <- the edge is structural, not a return forecast")
    out["brackets"] = br

    hdr("5. TRADING-COST SENSITIVITY  (1998-04 -> 2026-07, CA ~$300k)")
    print(f"{'cost per side':<18}{'strategy':>11}{'SPY':>9}{'excess':>9}")
    cost = {}
    for c in (0.0, 0.0005, 0.0015, 0.0035):
        s, b = pair(A, B, comm=c, slip=c)
        cost[c] = dict(strat=s["cagr"], spy=b["cagr"])
        print(f"{f'{c*10000:.0f}bps + {c*10000:.0f}bps':<18}{s['cagr']*100:10.2f}%{b['cagr']*100:8.2f}%"
              f"{(s['cagr']-b['cagr'])*100:+9.2f}")
    out["costs"] = {str(k): v for k, v in cost.items()}

    hdr("6. PARAMETER SENSITIVITY  (1998-04 -> 2026-07, CA ~$300k)")
    print(f"{'variant':<30}{'strategy':>11}{'excess':>9}{'trades':>9}")
    s, b = pair(A, B)
    grid = [("top_n=3", dict(top_n=3)), ("top_n=4", dict(top_n=4)), ("top_n=5 (default)", {}),
            ("top_n=6", dict(top_n=6)), ("top_n=8", dict(top_n=8)),
            ("monthly", dict(rebalance="M")), ("quarterly (default)", {}),
            ("semi-annual", dict(rebalance="S")), ("annual", dict(rebalance="A")),
            ("6-1 momentum", dict(lookback=126)), ("12-0 momentum", dict(skip=0)),
            ("12-1 (default)", {}), ("24-1 momentum", dict(lookback=504)),
            ("gain budget 0%", dict(gain_budget=0.0)), ("gain budget 1% (default)", {}),
            ("gain budget 2%", dict(gain_budget=0.02)), ("gain budget 4%", dict(gain_budget=0.04)),
            ("no wash-sale guard", dict(wash_days=0))]
    psens = []
    for name, kw in grid:
        r = run_one(gated(A, **kw), A, B)
        psens.append(dict(variant=name, cagr=r["cagr"], excess=r["cagr"] - b["cagr"]))
        print(f"{name:<30}{r['cagr']*100:10.2f}%{(r['cagr']-b['cagr'])*100:+9.2f}{r['trades']:9d}")
    out["param_sensitivity"] = psens

    Path(__file__).with_name("tax_managed_report.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {Path(__file__).with_name('tax_managed_report.json')}")


if __name__ == "__main__":
    main()
