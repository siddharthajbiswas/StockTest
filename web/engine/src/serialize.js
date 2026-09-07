/**
 * Turn a `Result` into the JSON shapes the Phase 0 goldens use.
 * Ports `reference/serialize.py` and `reference/analytics.py`.
 *
 * Kept faithful to the Python field-by-field so the golden comparison is a real
 * test of the engine rather than of the serializer.
 */
import { nsum } from "./numeric.js";
import { isoOfDay } from "./result.js";

/** JSON has no NaN/Infinity — coerce to null, as `_finite` does. */
function finite(x) {
  if (x === null) return null;
  return Number.isFinite(x) ? x : null;
}

export function metricsDict(res) {
  const out = {
    starting_cash: finite(res.startingCash),
    final_value: finite(res.finalValue),
    total_return: finite(res.totalReturn),
    cagr: finite(res.cagr),
    sharpe: finite(res.sharpe),
    max_drawdown: finite(res.maxDrawdown),
    n_trades: res.trades.length,
    commission_paid: finite(res.trades.length === 0 ? 0.0 : res.commissionPaid),
    taxes_paid: null,
    terminal_tax: null,
    total_tax: null,
    after_tax_final_value: null,
    after_tax_total_return: null,
    after_tax_cagr: null,
  };
  if (res.taxesPaid !== null) {
    out.taxes_paid = finite(res.taxesPaid);
    out.terminal_tax = finite(res.terminalTax);
    out.total_tax = finite(res.totalTax);
    out.after_tax_final_value = finite(res.afterTaxFinalValue);
    out.after_tax_total_return = finite(res.afterTaxTotalReturn);
    out.after_tax_cagr = finite(res.afterTaxCagr);
  }
  return out;
}

export function tradesList(res) {
  return res.trades.map((t) => ({
    date: isoOfDay(t.day),
    ticker: t.ticker,
    side: t.side,
    shares: t.shares,
    price: t.price,
    value: t.value,
    commission: t.commission,
  }));
}

export function totals(res) {
  return Array.from(res.equity.total);
}

/** Decompose a finite double into exact integers m, e with x === m * 2^e. */
function decompose(x) {
  const view = new DataView(new ArrayBuffer(8));
  view.setFloat64(0, x);
  const hi = view.getUint32(0);
  const lo = view.getUint32(4);
  const negative = hi >>> 31 === 1;
  let exp = (hi >>> 20) & 0x7ff;
  let mant = (BigInt(hi & 0xfffff) << 32n) | BigInt(lo);
  if (exp === 0)
    exp = 1; // subnormal
  else mant |= 1n << 52n; // implicit leading bit
  return { m: negative ? -mant : mant, e: exp - 1075 };
}

/**
 * Python's `round(x, digits)`, exactly.
 *
 * Python rounds half-to-even against the float's *exact* binary value, then
 * returns the nearest double to that decimal. Neither JS primitive does this:
 * `Math.round` rounds halves up, and `toFixed` is specified to pick the larger
 * n on a tie (half away from zero). Scaling by 10^d first — the obvious
 * approach, and what an earlier draft of this function did — is also wrong,
 * because the multiplication introduces its own rounding and destroys the very
 * tie you are trying to detect. That produced 1e-4 discrepancies on 15 round
 * trips across the golden cases.
 *
 * So do it in exact arithmetic: x*10^d = (m * 10^d) / 2^-e as a rational,
 * divide with remainder, and compare 2*remainder against the denominator to
 * resolve the tie half-to-even.
 */
function pyRound(x, digits) {
  if (!Number.isFinite(x) || x === 0) return x;
  const { m, e } = decompose(x);
  // e >= 0 means x is already an integer, so rounding to >= 0 decimals is a
  // no-op — and avoids overflowing Number on huge magnitudes.
  if (e >= 0) return x;
  const negative = m < 0n;
  const am = negative ? -m : m;
  const p10 = 10n ** BigInt(digits);
  const den = 1n << BigInt(-e);
  const num = am * p10;
  const q = num / den;
  const r = num % den;
  const twice = r * 2n;
  let n;
  if (twice > den) n = q + 1n;
  else if (twice < den) n = q;
  else n = q % 2n === 0n ? q : q + 1n; // exact tie -> half to even
  const out = Number(n) / Number(p10);
  return negative ? -out : out;
}

/**
 * Pair BUY fills to SELL fills FIFO per ticker. Mirrors the engine's own FIFO
 * tax-lot accounting so per-trade P&L is consistent with how gains are
 * realized. Open positions at the end are not round trips.
 */
export function roundTrips(trades) {
  if (trades.length === 0) return { rt: [], winRate: null };
  const openLots = new Map();
  const out = [];
  for (const t of trades) {
    const cps = t.shares ? t.commission / t.shares : 0.0;
    if (t.side === "BUY") {
      let lots = openLots.get(t.ticker);
      if (lots === undefined) {
        lots = [];
        openLots.set(t.ticker, lots);
      }
      lots.push({ day: t.day, shares: t.shares, price: t.price, cps });
      continue;
    }
    let remaining = t.shares;
    const lots = openLots.get(t.ticker);
    if (lots === undefined) continue;
    while (remaining > 1e-9 && lots.length > 0) {
      const lot = lots[0];
      const take = Math.min(remaining, lot.shares);
      const buyComm = lot.cps * take;
      const sellComm = cps * take;
      const pnl = (t.price - lot.price) * take - buyComm - sellComm;
      const cost = lot.price * take + buyComm;
      out.push({
        ticker: t.ticker,
        entry_date: isoOfDay(lot.day),
        exit_date: isoOfDay(t.day),
        shares: pyRound(take, 4),
        entry_price: pyRound(lot.price, 4),
        exit_price: pyRound(t.price, 4),
        pnl: pyRound(pnl, 2),
        return_pct: cost > 0 ? pnl / cost : 0.0,
        holding_days: t.day - lot.day,
      });
      lot.shares -= take;
      remaining -= take;
      if (lot.shares <= 1e-9) lots.shift();
    }
  }
  const wins = out.reduce((acc, r) => acc + (r.pnl > 0 ? 1 : 0), 0);
  return { rt: out, winRate: out.length ? wins / out.length : null };
}

/** Reindex an equity curve onto `days`, forward- then back-filled. */
export function alignTotals(res, days) {
  const src = res.equity.days;
  const val = res.equity.total;
  const out = new Array(days.length);
  let k = 0;
  let last = NaN;
  for (let i = 0; i < days.length; i++) {
    while (k < src.length && src[k] <= days[i]) {
      last = val[k];
      k++;
    }
    out[i] = last;
  }
  // bfill for leading positions before the source series starts.
  const firstVal = val.length ? val[0] : NaN;
  for (let i = 0; i < out.length && Number.isNaN(out[i]); i++)
    out[i] = firstVal;
  return out;
}

export { nsum };
