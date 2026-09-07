/**
 * Capital-gains tax accounting. Port of `backtester/tax.py`.
 *
 * Deliberately NOT modeled (same as Python): the wash-sale rule, the $3,000/yr
 * capital-loss offset against ordinary income, state taxes / NIIT, and dividend
 * taxes. See the Python module docstring for why each is excluded.
 */
export function makeTaxPolicy(
  shortTermRate = 0.35,
  longTermRate = 0.15,
  longTermDays = 365,
) {
  return { shortTermRate, longTermRate, longTermDays };
}

/** Strictly greater than the threshold, matching Python's `holding_days > long_term_days`. */
export function isLongTerm(policy, holdingDays) {
  return holdingDays > policy.longTermDays;
}

/**
 * Tax owed for a year plus the loss carried into the next one.
 *
 * `netSt`/`netLt` are the year's net short/long-term realized gains (negative =
 * loss). `carryforwardLoss` is the accumulated unused loss as a non-negative
 * magnitude. Losses are pooled and applied against short-term gains first,
 * which is taxpayer-optimal because they are taxed higher.
 *
 * The arithmetic order here mirrors Python exactly — pool, then consume against
 * short-term, then long-term — because subtracting in a different order changes
 * the low bits of the residual pool.
 */
export function computeYearTax(netSt, netLt, carryforwardLoss, policy) {
  let pool = carryforwardLoss + Math.max(0.0, -netSt) + Math.max(0.0, -netLt);
  let gainSt = Math.max(0.0, netSt);
  let gainLt = Math.max(0.0, netLt);
  let used = Math.min(pool, gainSt);
  gainSt -= used;
  pool -= used;
  used = Math.min(pool, gainLt);
  gainLt -= used;
  pool -= used;
  const tax = gainSt * policy.shortTermRate + gainLt * policy.longTermRate;
  return { tax, carryforward: pool };
}
