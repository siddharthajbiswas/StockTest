/**
 * The 10 timing strategies. Port of `strategies/timers.py`.
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

import { bollinger, macd, realizedVol, sma, totalReturn, wilderRsi } from "./indicators.js";
import type { Timer } from "./composite.js";
import type { Context } from "./strategy.js";

/**
 * History pulled for EWMA-warm-up indicators (MACD). 150 bars is far more than
 * a 26-day EMA needs; timers wanting a longer window ask explicitly.
 */
export const MAX_WINDOW = 150;

function closes(ctx: Context, ticker: string, window: number): Float64Array {
  return ctx.history(ticker, "Close", window);
}

/** Always long. The timing baseline. */
export class BuyHoldTimer implements Timer {
  readonly name = "buy_hold";
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, _held: boolean, _entry: number | null): boolean {
    return ctx.price(ticker) !== null;
  }
}

/** Classic 50/200 trend filter: long while the fast SMA is above the slow. */
export class MaCrossTimer implements Timer {
  readonly name = "ma_cross";
  constructor(private readonly fast = 50, private readonly slow = 200) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, _held: boolean, _entry: number | null): boolean {
    const c = closes(ctx, ticker, this.slow);
    const fastMa = sma(c, this.fast);
    const slowMa = sma(c, this.slow);
    if (fastMa === null || slowMa === null) return false;
    return fastMa > slowMa;
  }
}

/** RSI mean reversion: enter when oversold, hold until it recovers. */
export class RsiTimer implements Timer {
  readonly name = "rsi";
  constructor(
    private readonly period = 14,
    private readonly oversold = 30.0,
    private readonly exitLevel = 70.0,
  ) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, held: boolean, _entry: number | null): boolean {
    const rsi = wilderRsi(closes(ctx, ticker, this.period * 5), this.period);
    if (rsi === null) return held; // not enough data: don't force a change
    if (held) return rsi < this.exitLevel;
    return rsi <= this.oversold;
  }
}

/** Momentum confirmation: long while the MACD line is above its signal. */
export class MacdTimer implements Timer {
  readonly name = "macd";
  constructor(
    private readonly fast = 12,
    private readonly slow = 26,
    private readonly signal = 9,
  ) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, _held: boolean, _entry: number | null): boolean {
    const out = macd(closes(ctx, ticker, MAX_WINDOW), this.fast, this.slow, this.signal);
    if (out === null) return false;
    return out[0] > out[1];
  }
}

/** Volatility band reversion: buy at the lower band, sell at the upper. */
export class BollingerTimer implements Timer {
  readonly name = "bollinger";
  constructor(private readonly window = 20, private readonly k = 2.0) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, held: boolean, _entry: number | null): boolean {
    const bands = bollinger(closes(ctx, ticker, this.window), this.window, this.k);
    const px = ctx.price(ticker);
    if (bands === null || px === null) return held;
    const [lower, , upper] = bands;
    if (held) return px < upper; // exit once we ride back to the top band
    return px <= lower;          // enter at the lower band
  }
}

/** Absolute 12-month momentum gate: only long names in a real uptrend. */
export class MomentumTimer implements Timer {
  readonly name = "momentum12";
  constructor(private readonly lookback = 252, private readonly threshold = 0.0) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, _held: boolean, _entry: number | null): boolean {
    const ret = totalReturn(closes(ctx, ticker, this.lookback + 1), this.lookback);
    if (ret === null) return false;
    return ret > this.threshold;
  }
}

/** Absolute momentum AND relative strength versus the benchmark. */
export class DualMomentumTimer implements Timer {
  readonly name = "dual_momentum";
  constructor(private readonly lookback = 252, private readonly benchmark = "SPY") {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, _held: boolean, _entry: number | null): boolean {
    const ret = totalReturn(closes(ctx, ticker, this.lookback + 1), this.lookback);
    const bench = totalReturn(closes(ctx, this.benchmark, this.lookback + 1), this.lookback);
    if (ret === null || bench === null) return false;
    return ret > 0.0 && ret > bench;
  }
}

/** Donchian channel breakout: buy new highs, exit on the lower channel. */
export class TurtleBreakoutTimer implements Timer {
  readonly name = "turtle";
  constructor(private readonly entryWindow = 252, private readonly exitWindow = 100) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, held: boolean, _entry: number | null): boolean {
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
    for (let i = 0; i < highs.length - 1; i++) if (highs[i] > max) max = highs[i];
    return px >= max;
  }
}

/** Volatility mean reversion: buy after a vol spike, flat once vol calms. */
export class VolReversionTimer implements Timer {
  readonly name = "vol_reversion";
  constructor(
    private readonly short = 20,
    private readonly long = 100,
    private readonly spike = 1.5,
  ) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, held: boolean, _entry: number | null): boolean {
    const c = closes(ctx, ticker, this.long + 1);
    const shortVol = realizedVol(c, this.short);
    const longVol = realizedVol(c, this.long);
    if (shortVol === null || longVol === null || longVol === 0) return held;
    const ratio = shortVol / longVol;
    if (held) return ratio > 1.0;   // stay until vol reverts to baseline
    return ratio >= this.spike;     // enter on a genuine spike
  }
}

/** Trend following with a hard stop from the entry price. */
export class TrendStopTimer implements Timer {
  readonly name = "trend_stop";
  constructor(private readonly maWindow = 200, private readonly stop = 0.08) {}
  initialize(_ctx: Context): void {}
  wantLong(ctx: Context, ticker: string, held: boolean, entry: number | null): boolean {
    const px = ctx.price(ticker);
    if (px === null) return held;
    if (held && entry !== null && px <= entry * (1.0 - this.stop)) return false;
    const ma = sma(closes(ctx, ticker, this.maWindow), this.maWindow);
    if (ma === null) return held;
    return px > ma;
  }
}

export type TimerParams = Record<string, number | string>;

/** Registry mirroring `strategies/timers.py::TIMERS`. */
export function makeTimer(id: string, p: TimerParams = {}): Timer {
  const num = (k: string, d: number) => (p[k] === undefined ? d : Number(p[k]));
  switch (id) {
    case "buy_hold": return new BuyHoldTimer();
    case "ma_cross": return new MaCrossTimer(num("fast", 50), num("slow", 200));
    case "rsi": return new RsiTimer(num("period", 14), num("oversold", 30), num("exit_level", 70));
    case "macd": return new MacdTimer(num("fast", 12), num("slow", 26), num("signal", 9));
    case "bollinger": return new BollingerTimer(num("window", 20), num("k", 2));
    case "momentum12": return new MomentumTimer(num("lookback", 252), num("threshold", 0));
    case "dual_momentum":
      return new DualMomentumTimer(num("lookback", 252), String(p.benchmark ?? "SPY"));
    case "turtle":
      return new TurtleBreakoutTimer(num("entry_window", 252), num("exit_window", 100));
    case "vol_reversion":
      return new VolReversionTimer(num("short", 20), num("long", 100), num("spike", 1.5));
    case "trend_stop": return new TrendStopTimer(num("ma_window", 200), num("stop", 0.08));
    default: throw new Error(`Unknown timer_id ${id}`);
  }
}
