import sys, json; sys.path.insert(0, '/Users/siddhartha/dev/StockTest')
import pandas as pd
from research.lab import sweep, report
base = {"kind": "weights", "signal": "verify_lev_robust.trend", "rebalance": "M"}
def cfg(risk, safe, n=175, band=0.03, req=None):
    return dict(base, params={"sig": "SPY", "n": n, "band": band, "check": "D", "risk": risk, "safe": safe,
                              "lag": 0, "ma": "sma", "mdrift": 0.05}, requires=req or [])
cfgs = {
  "REAL 2x: SSO on / IEF off, SMA175 3%": cfg({"SSO": 1}, ["IEF"], req=["SSO", "IEF"]),
  "SYN 2x same windows (SYN_SPY2XC / IEF)": cfg({"SYN_SPY2XC": 1}, ["IEF"], req=["SSO", "IEF"]),
  "REAL 2x: SSO / IEF, SMA200 4%": cfg({"SSO": 1}, ["IEF"], 200, 0.04, req=["SSO", "IEF"]),
  "REAL 1.5x: 50% SPY + 50% SSO on / IEF off": cfg({"SPY": 0.5, "SSO": 0.5}, ["IEF"], req=["SSO", "IEF"]),
  "SPY buy & hold (same windows)": {"kind": "buyhold", "weights": {"SPY": 1.0}, "requires": ["SSO", "IEF"]},
}
recs = sweep.run(list(cfgs.values()), protocol="full", regimes=("CA", "FED", "NONE"), workers=3)
inv = {sweep.cfg_id(c): k for k, c in cfgs.items()}
t = report.table(recs, label=lambda c: inv[sweep.cfg_id(c)])
cols = ["label", "regime", "first_start", "score", "full_excess", "full_cagr", "bench_full_cagr", "ex5_beat", "ex10_beat",
        "ex15_beat", "ex10_min", "boot_p", "max_dd", "bench_max_dd", "trades", "turnover"]
with pd.option_context("display.width", 250, "display.max_columns", 30):
    print(t[cols].round(4).to_string(index=False))
t.to_csv("/Users/siddhartha/dev/StockTest/research/lab/scratch/final_check/real_sso.csv", index=False)
