# StockTest

A backtesting studio for one honest question: **can a stock-picking strategy beat
just buying and holding the S&P 500 — after taxes and trading costs?**

StockTest is built around a composable engine: you pair a **Picker** (which stocks
to hold — momentum, value, quality, …) with a **Timer** (when to be in or out —
buy & hold, moving-average cross, RSI, …). From 10 pickers and 10 timers that's up
to 100 strategies, each scored net of commission, slippage, and capital-gains tax,
and always benchmarked against SPY.

The **web app is the primary way to use StockTest** — no code or command line
required. The original CLI tools are still here for power users and researchers who
want the full sweep (see [For power users](#for-power-users)).

---

## The web app (start here)

A React UI over the engine compiled to TypeScript and run in a Web Worker — no
server, no API, nothing leaves your machine. It walks you through one decision at
a time and surfaces the honest caveats instead of burying them.

### Run it

There is no server. The engine is a TypeScript port of `backtester/` that runs
in a Web Worker in the browser, so you only need the data bundle and Vite.

```bash
# 1. Python deps + price data (once)
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python download_data.py
.venv/bin/python fetch_fundamentals.py

# 2. Build the browser data bundle (after any data refresh)
.venv/bin/python tools/build_web_data.py
.venv/bin/python tools/gen_web_metadata.py

# 3. Run the app
cd web/frontend
npm install
npm run dev            # open http://localhost:5173
```

The dev server streams the bundle from `build/webdata/` at `/data`. The worker
loads the ~13 MB universe only when you use strategy mode; picking your own
stocks fetches ~190 kB per ticker.

### What you can do, entirely in the UI

- **Pick stocks yourself** (a searchable basket of the ~530 local tickers) **or let
  a strategy pick** (a card grid of the 10 pickers).
- Choose a **timing rule**, tweak any strategy's parameters, and set the date range,
  tax rates, and trading costs.
- See the result net of tax vs the S&P 500: equity curve, drawdown, full metrics,
  and a plain-language trust panel.
- **Save a strategy** to re-run or edit later — no reconfiguring from scratch.
- **Validate a strategy out-of-sample** — re-test the exact combo on data it wasn't
  chosen on (holdout rank persistence + a walk-forward track record), so you can
  tell a real edge from an overfit one.

---

## Honesty & known limits

The app's credibility depends on **not overstating what free data can tell you**.
These limits are documented in the engine and surfaced in the UI (they are not hidden):

- **Look-ahead bias (fundamental pickers).** The 7 fundamentals-based pickers (value,
  quality, growth, …) rank stocks using a *current* fundamentals snapshot, not
  point-in-time data. Over long windows that flatters historical results. The UI
  badges these as *"Best for recent-period analysis"*; the 3 price-only pickers
  (momentum, relative strength, random) are marked *"Reliable for full-history
  backtests."* Enforced in `backtester`/`catalog.py` via `look_ahead_risk`.
- **Survivorship bias.** The full local dataset is essentially *today's* survivors —
  delisted/bankrupt companies are missing because free sources lack their prices. The
  **S&P 500 point-in-time** universe corrects *membership* look-ahead (real index
  members on each date, back to 1996) but still can't resurrect delisted names. See
  `backtester/universe.py`.
- **Tax engine simplifications.** Short- vs long-term capital gains are modeled
  (annual settlement, loss carryforward), but **deliberately not**: the wash-sale
  rule, the $3,000/yr capital-loss offset, state taxes / NIIT, and dividend taxes
  (prices are total-return adjusted, so dividends are taxed as capital gains — a
  break that also applies to SPY, so it largely cancels in the comparison). See the
  docstring in `backtester/tax.py`.

---

## For power users

The engine and its CLI tools run without the web app — useful for full sweeps,
research, and reproducible batch runs.

| Tool | What it does |
|------|--------------|
| `grid_combos.py` | **The full sweep:** backtests every picker × timer combo (up to 100) over a date range and ranks them against SPY on a risk-adjusted basis. |
| `walkforward.py` | Out-of-sample validation — runs the honest holdout / walk-forward checks that the web app's "Validate" button is built on. |
| `grid_backtest.py` | Vectorized price-only picker × timer grid over the long history. |
| `run_backtest.py` | Run a single strategy module and report per-day trades. |

Data setup (needed before the tools or app have anything to test):

| Tool | What it does |
|------|--------------|
| `download_data.py` | Downloads split/dividend-adjusted daily OHLCV CSVs into `data/` (via yfinance). |
| `fetch_fundamentals.py` | Writes a current fundamentals snapshot (`data/fundamentals.csv`) used by the fundamental pickers. |

Example:

```bash
.venv/bin/python grid_combos.py --start 2016-01-01 --end 2021-12-31 --universe sp500-pit
```

See `STRATEGY_CATALOG.md` for the full picker/timer reference and `STRATEGIES.md`
for the strategy design notes.

---

## Layout

```
backtester/      # the engine: data, portfolio, tax, indicators, universe
strategies/      # picker & timer implementations (the composable pieces)
web/engine/      # TypeScript port of the engine (runs in a Web Worker)
reference/       # Python reference implementation — generates the golden oracle
web/frontend/    # React + Vite + TypeScript UI
data/            # per-ticker price CSVs + fundamentals snapshot
*.py             # CLI tools (see "For power users")
```

## Tests

Needs the dev deps: `.venv/bin/pip install -r requirements-dev.txt`.

```bash
# Python: reference implementation + the golden oracle it generates
.venv/bin/python -m pytest reference golden -q

# TypeScript engine (parity against the oracle, worker, RNG, units)
cd web/engine && npm test

# frontend (typecheck + production build)
cd web/frontend && npm run build
```
