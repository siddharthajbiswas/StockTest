# StockTest

A backtesting studio for one honest question: **can a stock-picking strategy beat
just buying and holding the S&P 500 — after taxes and trading costs?**

StockTest is built around a composable engine: you pair a **Picker** (which stocks
to hold — momentum, value, quality, …) with a **Timer** (when to be in or out —
buy & hold, moving-average cross, RSI, …). From 10 pickers and 10 timers that's up
to 100 strategies, each scored net of commission, slippage, and capital-gains tax,
and always benchmarked against SPY.

**[Try it live →](https://siddharthajbiswas.github.io/StockTest/)** — it runs entirely in your
browser. No signup, no backend, nothing leaves your machine.

The **web app is the primary way to use StockTest** — no code or command line
required. The original CLI tools are still here for power users and researchers who
want the full sweep (see [For power users](#for-power-users)).

---

## The web app (start here)

A React UI over the engine ported to JavaScript and run in a Web Worker — no
server, no API, nothing leaves your machine. It walks you through one decision at
a time and surfaces the honest caveats instead of burying them.

### Run it

There is no server. The engine is a JavaScript port of `backtester/` that runs
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

## What the research found

StockTest asks whether a strategy can beat buy-and-hold after tax. A search of about
15,000 strategy configurations covered:
- timing and trend rules;
- tactical asset allocation and risk parity;
- leverage;
- seasonality and mean reversion;
- macro signals;
- factor tilts;
- sector and global rotation;
- individual stocks;
- pure tax structures.

**None beats buying and holding an S&P 500 fund after California tax with good
confidence.** The full report is [research/STRATEGY_SEARCH.md](research/STRATEGY_SEARCH.md).

The reason is mostly tax. Buy-and-hold defers every gain to the end. A strategy that
realizes gains along the way has to out-earn the index before tax by more than the
tax it pays. No signal tested did that reliably.

Two strategies are included as presets in the web app, as ordinary strategies to
explore:

- **Tax-managed ETF momentum (CA).** 12-1 momentum over 22 index ETFs, top 5, rebalanced
  quarterly, traded under a yearly realized-gain budget (`strategies/tax_managed.py`).
  Its historical lead depends on QQQ/XLK being in the menu and on the 2000s.
- **2× S&P trend switch (CA).** Holds SSO (2× S&P 500) while SPY is more than 3% above
  its 175-day average, and IEF (intermediate Treasuries) once it is more than 3% below.
  It is checked every trading day at the close (the `trend_switch` timer). It is leveraged,
  so it loses more in fast crashes, and its after-tax edge since 2010 has been about zero.

The original write-up of the tax-managed preset is kept in
[research/README.md](research/README.md).

---

## How it's kept correct

StockTest is implemented twice. `backtester/` and `reference/` are the Python
original; `web/engine/` is a JavaScript port of it that runs in the browser. Python
is the source of truth, and the port is pinned to it by a golden-oracle suite rather
than by hand-checking.

The Python side freezes 25 cases — 23 backtests and 2 out-of-sample validations —
chosen to cover every picker, every timer, and the awkward windows (2008, COVID,
point-in-time index membership). The JavaScript engine reruns all of them and
compares **300,508 values at 1e-9 relative tolerance**, with trade counts, dates,
tickers and sides required to match exactly. `web/frontend/verify.html` runs that
same suite through the shipped path — a real Web Worker, decoding the real price
bundle over HTTP — so the thing being verified is the thing that ships.

Two places where the languages genuinely disagree, and what it took to reconcile them:

- **Seeded randomness.** `RandomPicker` draws from Python's `random.sample`, which
  is CPython's Mersenne Twister. Reproducing the stream meant reimplementing
  MT19937, `getrandbits`, `_randbelow` and `sample` in JavaScript
  (`web/engine/src/mt19937.js`) — rejection sampling and all.
- **Rounding.** Python's `round()` is half-to-even on the float's exact value;
  JavaScript's `toFixed` rounds half away from zero, and scaling by 10ⁿ first
  destroys the tie. Hence `pyRound` in `web/engine/src/serialize.js`.

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
| `research/tax_managed_report.py` | Reproduces the whole tax-managed evidence table: fixed windows, rolling 5/10/15/20-year windows, random-ranking controls, tax-bracket and cost sensitivity. |
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
web/engine/      # JavaScript port of the engine (runs in a Web Worker)
reference/       # Python reference implementation — generates the golden oracle
web/frontend/    # React + Vite UI (plain JavaScript + JSX)
data/            # per-ticker price CSVs + fundamentals snapshot
*.py             # CLI tools (see "For power users")
```

## Tests

Needs the dev deps: `.venv/bin/pip install -r requirements-dev.txt`.

```bash
# Python: reference implementation + the golden oracle it generates
.venv/bin/python -m pytest reference golden -q

# JavaScript engine (parity against the oracle, worker, RNG, units)
cd web/engine && npm test

# frontend (production build)
cd web/frontend && npm run build
```

For the parity suite in a real browser rather than Node, run the frontend dev
server and open `/verify.html` — it reruns every golden case through an actual Web
Worker and prints a per-case pass/fail table.
