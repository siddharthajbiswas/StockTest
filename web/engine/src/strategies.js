/**
 * Standalone strategies that aren't a Picker/Timer pair.
 *
 * The 10 pickers live in `pickers.js` and the 10 timers in `timers.js`; this
 * file holds only `BuyAndHold`, which the SPY benchmark runs directly as a
 * `Strategy` rather than through a `Combo`.
 */

/** Buy an equal-weight basket on day one and hold it. */
export class BuyAndHold {
  invested = false;
  initialize(_ctx) {
    this.invested = false;
  }
  onDay(ctx) {
    if (this.invested) return;
    const universe = ctx.universe;
    if (universe.length === 0) return;
    const weight = 1.0 / universe.length;
    for (const ticker of universe) ctx.orderTargetPercent(ticker, weight);
    this.invested = true;
  }
}
