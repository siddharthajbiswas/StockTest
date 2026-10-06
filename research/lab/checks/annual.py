import sys; sys.path.insert(0, '/Users/siddhartha/dev/StockTest')
import pandas as pd
from research.lab import sweep, report
from research.lab.validate_lab import MENU
SECT = ["XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY"]
mom = lambda menu: {"menu": menu, "lookback": 252, "skip": 21, "top_n": 5}
C = {
 "Momentum rotation, 22 ETFs, rebalance once a year (Jan)":
   {"kind": "weights", "signal": "common.momentum", "params": mom(MENU), "rebalance": "A", "execution": "standard"},
 "Momentum rotation, 22 ETFs, every 13 months (every sale > 1 yr)":
   {"kind": "weights", "signal": "common.momentum", "params": mom(MENU), "rebalance": "M13", "execution": "standard"},
 "Momentum rotation, 22 ETFs, yearly, SELL ONLY LONG-TERM LOTS":
   {"kind": "weights", "signal": "common.momentum", "params": mom(MENU), "rebalance": "A", "execution": "tax",
    "gain_budget": 1.0, "st_gains": False},
 "Momentum rotation, 9 sector ETFs, yearly, long-term lots only":
   {"kind": "weights", "signal": "common.momentum", "params": mom(SECT), "rebalance": "A", "execution": "tax",
    "gain_budget": 1.0, "st_gains": False},
 "Equal-weight 9 sectors, rebalanced yearly":
   {"kind": "weights", "signal": "common.mix", "params": {"weights": {t: 1 / 9 for t in SECT}}, "rebalance": "A", "execution": "standard"},
 "Equal-weight SPY/QQQ/IWM/EFA, rebalanced yearly":
   {"kind": "weights", "signal": "common.mix", "params": {"weights": {"SPY": .25, "QQQ": .25, "IWM": .25, "EFA": .25}}, "rebalance": "A", "execution": "standard"},
 "Same 4 funds bought once, never rebalanced":
   {"kind": "buyhold", "weights": {"SPY": .25, "QQQ": .25, "IWM": .25, "EFA": .25}},
 "60/40 SPY/IEF, rebalanced yearly":
   {"kind": "weights", "signal": "common.mix", "params": {"weights": {"SPY": .6, "IEF": .4}}, "rebalance": "A", "execution": "standard"},
}
recs = sweep.run(list(C.values()), protocol="full", regimes=("CA", "NONE"), workers=12, verbose=False)
inv = {sweep.cfg_id(c): k for k, c in C.items()}
t = report.table(recs, label=lambda c: inv[sweep.cfg_id(c)])
rows = []
for lab in C:
    ca = t[(t.label == lab) & (t.regime == "CA")].iloc[0]
    no = t[(t.label == lab) & (t.regime == "NONE")].iloc[0]
    rows.append({"strategy": lab, "pre-tax score": no.score, "CA score": ca.score, "tax cost": no.score - ca.score,
                 "CA full": ca.full_excess, "CA 10y beat": ca.ex10_beat, "CA boot_p": ca.boot_p})
out = pd.DataFrame(rows)
with pd.option_context("display.width", 250, "display.max_colwidth", 70):
    print((out.set_index("strategy") * [100, 100, 100, 100, 100, 1]).round(2).to_string())
