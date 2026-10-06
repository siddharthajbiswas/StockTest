/**
 * The 11 timing strategies. Port of `strategies/timers.py`.
 *
 * A timer answers one question per name per day: given price history so far, do
 * we want to be long *right now*? Several use hysteresis (different entry vs
 * exit thresholds), which is why `wantLong` is told whether the name is `held`.
 *
 * PARITY NOTE — the `null` fallbacks differ per timer and are load-bearing.
 * Some return `false` when an indicator can't be computed (ma_cross, macd,
 * momentum12, dual_momentum), others return `held` so a warm-up gap doesn't
 * force a trade (rsi, bollinger, turtle, vol_reversion, trend_stop). Mixing
 * those up changes the trade sequence during every warm-up window.
 */
import {
  bollinger,
  macd,
  realizedVol,
  sma,
  totalReturn,
  wilderRsi,
} from "./indicators.js";

/**
 * History pulled for EWMA-warm-up indicators (MACD). 150 bars is far more than
 * a 26-day EMA needs; timers wanting a longer window ask explicitly.
 */
export const MAX_WINDOW = 150;
function closes(ctx, ticker, window) {
  return ctx.history(ticker, "Close", window);
}

/** Always long. The timing baseline. */
export class BuyHoldTimer {
  name = "buy_hold";
  initialize(_ctx) {}
  wantLong(ctx, ticker, _held, _entry) {
    return ctx.price(ticker) !== null;
  }
}

/** Classic 50/200 trend filter: long while the fast SMA is above the slow. */
export class MaCrossTimer {
  fast;
  slow;
  name = "ma_cross";
  constructor(fast = 50, slow = 200) {
    this.fast = fast;
    this.slow = slow;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, _held, _entry) {
    const c = closes(ctx, ticker, this.slow);
    const fastMa = sma(c, this.fast);
    const slowMa = sma(c, this.slow);
    if (fastMa === null || slowMa === null) return false;
    return fastMa > slowMa;
  }
}

/** RSI mean reversion: enter when oversold, hold until it recovers. */
export class RsiTimer {
  period;
  oversold;
  exitLevel;
  name = "rsi";
  constructor(period = 14, oversold = 30.0, exitLevel = 70.0) {
    this.period = period;
    this.oversold = oversold;
    this.exitLevel = exitLevel;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, held, _entry) {
    const rsi = wilderRsi(closes(ctx, ticker, this.period * 5), this.period);
    if (rsi === null) return held; // not enough data: don't force a change
    if (held) return rsi < this.exitLevel;
    return rsi <= this.oversold;
  }
}

/** Momentum confirmation: long while the MACD line is above its signal. */
export class MacdTimer {
  fast;
  slow;
  signal;
  name = "macd";
  constructor(fast = 12, slow = 26, signal = 9) {
    this.fast = fast;
    this.slow = slow;
    this.signal = signal;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, _held, _entry) {
    const out = macd(
      closes(ctx, ticker, MAX_WINDOW),
      this.fast,
      this.slow,
      this.signal,
    );
    if (out === null) return false;
    return out[0] > out[1];
  }
}

/** Volatility band reversion: buy at the lower band, sell at the upper. */
export class BollingerTimer {
  window;
  k;
  name = "bollinger";
  constructor(window = 20, k = 2.0) {
    this.window = window;
    this.k = k;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, held, _entry) {
    const bands = bollinger(
      closes(ctx, ticker, this.window),
      this.window,
      this.k,
    );
    const px = ctx.price(ticker);
    if (bands === null || px === null) return held;
    const [lower, , upper] = bands;
    if (held) return px < upper; // exit once we ride back to the top band
    return px <= lower; // enter at the lower band
  }
}

/** Absolute 12-month momentum gate: only long names in a real uptrend. */
export class MomentumTimer {
  lookback;
  threshold;
  name = "momentum12";
  constructor(lookback = 252, threshold = 0.0) {
    this.lookback = lookback;
    this.threshold = threshold;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, _held, _entry) {
    const ret = totalReturn(
      closes(ctx, ticker, this.lookback + 1),
      this.lookback,
    );
    if (ret === null) return false;
    return ret > this.threshold;
  }
}

/** Absolute momentum AND relative strength versus the benchmark. */
export class DualMomentumTimer {
  lookback;
  benchmark;
  name = "dual_momentum";
  constructor(lookback = 252, benchmark = "SPY") {
    this.lookback = lookback;
    this.benchmark = benchmark;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, _held, _entry) {
    const ret = totalReturn(
      closes(ctx, ticker, this.lookback + 1),
      this.lookback,
    );
    const bench = totalReturn(
      closes(ctx, this.benchmark, this.lookback + 1),
      this.lookback,
    );
    if (ret === null || bench === null) return false;
    return ret > 0.0 && ret > bench;
  }
}

/** Donchian channel breakout: buy new highs, exit on the lower channel. */
export class TurtleBreakoutTimer {
  entryWindow;
  exitWindow;
  name = "turtle";
  constructor(entryWindow = 252, exitWindow = 100) {
    this.entryWindow = entryWindow;
    this.exitWindow = exitWindow;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, held, _entry) {
    const px = ctx.price(ticker);
    if (px === null) return held;
    if (held) {
      const lows = closes(ctx, ticker, this.exitWindow);
      if (lows.length < this.exitWindow) return true;
      let min = Infinity;
      for (let i = 0; i < lows.length; i++) if (lows[i] < min) min = lows[i];
      return px > min; // stay long above the channel low
    }
    const highs = closes(ctx, ticker, this.entryWindow);
    if (highs.length < this.entryWindow) return false;
    // Break out on a new high vs the prior window — Python slices `[:-1]`,
    // excluding today's bar.
    let max = -Infinity;
    for (let i = 0; i < highs.length - 1; i++)
      if (highs[i] > max) max = highs[i];
    return px >= max;
  }
}

/** Volatility mean reversion: buy after a vol spike, flat once vol calms. */
export class VolReversionTimer {
  short;
  long;
  spike;
  name = "vol_reversion";
  constructor(short = 20, long = 100, spike = 1.5) {
    this.short = short;
    this.long = long;
    this.spike = spike;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, held, _entry) {
    const c = closes(ctx, ticker, this.long + 1);
    const shortVol = realizedVol(c, this.short);
    const longVol = realizedVol(c, this.long);
    if (shortVol === null || longVol === null || longVol === 0) return held;
    const ratio = shortVol / longVol;
    if (held) return ratio > 1.0; // stay until vol reverts to baseline
    return ratio >= this.spike; // enter on a genuine spike
  }
}

/** Trend following with a hard stop from the entry price. */
export class TrendStopTimer {
  maWindow;
  stop;
  name = "trend_stop";
  constructor(maWindow = 200, stop = 0.08) {
    this.maWindow = maWindow;
    this.stop = stop;
  }
  initialize(_ctx) {}
  wantLong(ctx, ticker, held, entry) {
    const px = ctx.price(ticker);
    if (px === null) return held;
    if (held && entry !== null && px <= entry * (1.0 - this.stop)) return false;
    const ma = sma(closes(ctx, ticker, this.maWindow), this.maWindow);
    if (ma === null) return held;
    return px > ma;
  }
}

/**
 * `"SSO, qld"` (or an array) -> `["SSO", "QLD"]`: trimmed, upper-cased,
 * de-duplicated, in order. Port of `_ticker_list` in `strategies/timers.py`.
 */
function tickerList(value) {
  const parts =
    value === null || value === undefined
      ? []
      : Array.isArray(value)
        ? value
        : String(value).split(",");
  const out = [];
  for (const p of parts) {
    const t = String(p).trim().toUpperCase();
    if (t && !out.includes(t)) out.push(t);
  }
  return out;
}

/**
 * Switch between a risk basket and a safe basket on ONE trend signal.
 * Port of `TrendSwitchTimer` — see its docstring for the full contract.
 *
 * Each trading day, on that day's close:
 *   margin = signal close today / mean(last n signal closes, today included) - 1
 * First successful evaluation: state = margin > 0. Afterwards: true once
 * margin > +band, false once margin < -band, otherwise unchanged. state true ->
 * the `risk` tickers are wanted, false -> the `safe` ones; anything else never.
 *
 * PARITY NOTES
 *  * The state is per signal, so it is evaluated at most once per trading day
 *    (the first wantLong call) and shared by every ticker asked that day.
 *  * Undecided (null) until the first evaluation succeeds — fewer than n closes
 *    or no signal close today — and wantLong is then false for EVERY ticker
 *    (the portfolio waits in cash). A later day without data keeps the state.
 *  * The mean goes through `sma` -> `nmean` (NumPy pairwise summation), and
 *    the margin is `px / ma - 1.0` in that order, exactly as Python computes it.
 */
export class TrendSwitchTimer {
  signal;
  n;
  band;
  risk;
  safe;
  state = null;
  lastDay = null;
  name = "trend_switch";
  constructor(signal = "SPY", n = 175, band = 0.03, risk = "SSO", safe = "IEF") {
    this.signal = String(signal ?? "SPY").trim().toUpperCase();
    this.n = Math.max(1, Math.trunc(Number(n)));
    this.band = Number(band);
    this.risk = tickerList(risk ?? "SSO");
    this.safe = tickerList(safe ?? "IEF");
  }
  initialize(_ctx) {
    this.state = null;
    this.lastDay = null;
  }
  /** Evaluate the rule on today's close — at most once per trading day. */
  update(ctx) {
    if (this.lastDay === ctx.day) return;
    this.lastDay = ctx.day;
    const px = ctx.price(this.signal);
    const ma = sma(closes(ctx, this.signal, this.n), this.n);
    // Not enough data: keep the previous state (null = undecided).
    if (px === null || ma === null || !(ma > 0)) return;
    const margin = px / ma - 1.0;
    if (this.state === null) this.state = margin > 0.0;
    else if (margin > this.band) this.state = true;
    else if (margin < -this.band) this.state = false;
  }
  wantLong(ctx, ticker, _held, _entry) {
    this.update(ctx);
    if (this.state === null) return false;
    return this.state ? this.risk.includes(ticker) : this.safe.includes(ticker);
  }
}

/** Registry mirroring `strategies/timers.py::TIMERS`. */
export function makeTimer(id, p = {}) {
  const num = (k, d) => (p[k] === undefined ? d : Number(p[k]));
  switch (id) {
    case "buy_hold":
      return new BuyHoldTimer();
    case "ma_cross":
      return new MaCrossTimer(num("fast", 50), num("slow", 200));
    case "rsi":
      return new RsiTimer(
        num("period", 14),
        num("oversold", 30),
        num("exit_level", 70),
      );
    case "macd":
      return new MacdTimer(num("fast", 12), num("slow", 26), num("signal", 9));
    case "bollinger":
      return new BollingerTimer(num("window", 20), num("k", 2));
    case "momentum12":
      return new MomentumTimer(num("lookback", 252), num("threshold", 0));
    case "dual_momentum":
      return new DualMomentumTimer(
        num("lookback", 252),
        String(p.benchmark ?? "SPY"),
      );
    case "turtle":
      return new TurtleBreakoutTimer(
        num("entry_window", 252),
        num("exit_window", 100),
      );
    case "vol_reversion":
      return new VolReversionTimer(
        num("short", 20),
        num("long", 100),
        num("spike", 1.5),
      );
    case "trend_stop":
      return new TrendStopTimer(num("ma_window", 200), num("stop", 0.08));
    case "trend_switch":
      return new TrendSwitchTimer(
        p.signal ?? "SPY",
        num("n", 175),
        num("band", 0.03),
        p.risk ?? "SSO",
        p.safe ?? "IEF",
      );
    default:
      throw new Error(`Unknown timer_id ${id}`);
  }
}
