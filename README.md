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

A React UI over a FastAPI backend that wraps the engine as a library. It walks you
through one decision at a time and surfaces the honest caveats instead of burying
them.

### Run it

The frontend proxies API calls to the backend, so start the backend first.

```bash
# 1. Install backend deps (once)
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# 2. Terminal A — backend API (from web/backend)
cd web/backend
../../.venv/bin/python -m uvicorn app:app --port 8000

# 3. Terminal B — frontend (from web/frontend)
cd web/frontend
npm install
npm run dev            # open http://localhost:5173
```

The backend loads every price CSV in `data/` once at startup and pre-warms the
market layout, so the first backtest is fast. Interactive API docs live at
`http://localhost:8000/docs`.

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
web/backend/     # FastAPI service wrapping the engine as a library
web/frontend/    # React + Vite + TypeScript UI
data/            # per-ticker price CSVs + fundamentals snapshot
*.py             # CLI tools (see "For power users")
```

## Tests

Needs the dev deps: `.venv/bin/pip install -r requirements-dev.txt`.

```bash
# backend
cd web/backend && ../../.venv/bin/python -m pytest -q

# frontend (typecheck + production build)
cd web/frontend && npm run build
```
