# StockTest Frontend

A React + Vite + TypeScript UI for the backtest API, designed for **non-experts**:
one clear decision at a time, generous whitespace, and the honest caveats
surfaced (not buried).

## Run

The frontend proxies API calls to the FastAPI backend, so start the backend first:

```bash
# terminal 1 — backend (from web/backend)
../../.venv/bin/python -m uvicorn app:app --port 8000

# terminal 2 — frontend (from web/frontend)
npm install
npm run dev            # http://localhost:5173
```

Vite proxies `/pickers`, `/timers`, `/universe`, `/tickers`, `/backtest`,
`/strategies`, `/validate`, `/health` to `http://localhost:8000` (override with
`VITE_BACKEND`). Production build: `npm run build` (runs `tsc` then `vite build`
into `dist/`).

## Flow (progressive disclosure — each step reveals the next)

1. **Mode** — the first decision, in plain language: *Pick stocks myself* vs
   *Let a strategy pick for me*, one line each.
2. **Stocks**
   - *Manual:* a searchable, debounced multi-select backed by `/tickers/search`,
     showing company names when available, with a banner that this is a **fixed
     set of ~530 well-known US stocks**, not any ticker.
   - *AI:* a card grid of the 10 pickers from `/pickers`. Each card carries a
     visual badge — green **“Reliable for full-history backtests”** (price-only)
     vs amber **“Best for recent-period analysis”** (fundamentals) — and the
     look-ahead caveat is printed right on the risky cards. A **“Customize
     parameters”** disclosure under the grid exposes the selected picker's params
     (from `/pickers`) as pre-filled form fields, with reset-to-defaults.
3. **Timer** — same card-grid pattern for the 10 timers, with a one-line
   explanation of what a timer is, and the same **“Customize parameters”**
   disclosure for the selected timer.

Customized params flow through to `/backtest` (`picker_params` / `timer_params`);
the results/caveat panel keys off the returned `picker_id`, so look-ahead-risk
status always reflects the picker actually run, not preset defaults.

## Saving & reusing strategies

The run bar has a **★ Save strategy** action that names the current
picker+params+timer+params (plus window/universe/tax) and POSTs it to
`/strategies/mine` (a JSON-file store on the backend; validated as runnable
before saving). Saved combos appear in a **My strategies** panel at the top of
the screen, each with **Re-run** (loads + runs immediately), **Edit** (loads
into the wizard to tweak), and delete.
4. **When & taxes** — a date-range picker and a tax section (“use sensible
   defaults” vs custom short/long-term rates) with a one-line note on why taxes
   change the verdict. Universe, stocks-held, rebalance cadence, and trading
   costs live under a collapsed **Advanced options** disclosure.
5. **Run** — a sticky bar runs the backtest and opens the results sheet.

## Results view

- **Equity chart** — three labeled lines: strategy pre-tax (dashed grey),
  strategy after-tax (indigo), and the S&P 500 (green), sharing one date axis.
- **Drawdown chart** beneath it (underwater plot from the after-tax line).
- **Metrics panel** — pre-tax & after-tax CAGR, total return, Sharpe, max
  drawdown, tax drag (\$ and %/yr), win rate, and trade count. Every tile has an
  info icon whose text explains what it measures, what's good, and why pre/post-tax
  differ.
- **“How much should you trust this result?”** — caveats chosen from the picker's
  `look_ahead_risk` flag and the universe's `bias_caveat` metadata (not hardcoded
  per result): a fundamentals picker over a long window flags look-ahead bias;
  `sp500-pit` flags missing delisted companies; the full dataset flags the stronger
  membership look-ahead; manual mode flags survivorship in the fixed universe.
- **Trade log** — round-trip trades (entry/exit date, ticker, buy/sell price,
  P&L \$ and %, holding period), reconstructed FIFO by the backend.

All results copy — metric explanations and the trust/caveat logic — lives in one
reviewable file, `src/content.ts`.

## Onboarding

A dependency-free 5-step tour (`components/Onboarding.tsx`) explains what the
tool does, the two modes, what a timer is, and that results are judged against
the S&P net of tax. It shows once (tracked in `localStorage`), is reopenable via
**Take a tour**, and its final step launches **Try an example** — which pre-fills
momentum + Buy & Hold over a 10-year window and runs immediately. The same
button lives in the header.

## Structure

```
src/
  api.ts, types.ts        # typed client + backend shapes
  App.tsx                 # flow orchestration, state, run, tour
  components/
    ModeCards, PickerGrid, TimerGrid, TickerPicker
    SettingsPanel         # dates, taxes, collapsed advanced
    Results, EquityChart  # results sheet + inline SVG chart
    Onboarding, InfoTip   # tour + hover tooltips (no libraries)
  styles.css              # design system (one accent, light theme)
```

No charting or component libraries — the equity chart, tour, and tooltips are
hand-rolled inline SVG/DOM to keep the bundle small.
