// ---------------------------------------------------------------------------
// SINGLE SOURCE OF TRUTH for user-facing explanations.
//
// Everything a non-expert reads about a metric or a caveat lives here, so the
// copy is easy to review and edit for accuracy in one place — nothing is
// scattered through the chart/panel components. The trust logic below CHOOSES
// which caveats apply from the picker/universe METADATA (Phase W2); it never
// hardcodes a verdict per strategy.
// ---------------------------------------------------------------------------
export const METRIC_INFO = {
  pretax_cagr: {
    label: "Pre-tax CAGR",
    help: "Compound annual growth rate before any taxes — the average yearly return, smoothed. Good is beating the S&P 500's ~10%/yr. This is the 'on paper' number; the after-tax figure is what you actually keep.",
  },
  aftertax_cagr: {
    label: "After-tax CAGR",
    help: "The same yearly return, but after capital-gains taxes. It's the number that matters for a taxable account. It's lower than pre-tax because selling winners triggers tax — and strategies that trade often are taxed more heavily than buy-and-hold.",
  },
  total_return: {
    label: "Total return",
    help: "The overall percentage gain across the whole period (after-tax). +100% means your money doubled. Useful for the headline, but CAGR is better for comparing across different time spans.",
  },
  sharpe: {
    label: "Sharpe ratio",
    help: "Return earned per unit of risk (volatility). Higher is better: under 0.5 is weak, ~1 is solid, above 2 is excellent. A high return with a wild, scary ride scores worse than a steadier one.",
  },
  max_drawdown: {
    label: "Max drawdown",
    help: "The worst peak-to-trough drop along the way — how much you'd have been down at the scariest moment. Closer to 0% is calmer; −50% means the portfolio halved before recovering. This is the pain you'd have to sit through.",
  },
  tax_drag: {
    label: "Tax drag",
    help: "How much taxes cost this strategy — in dollars, and as annual return lost (pre-tax CAGR minus after-tax CAGR). Frequent trading realizes gains early and is taxed at higher short-term rates, so high-turnover strategies have a bigger drag; buy-and-hold defers tax and keeps more.",
  },
  win_rate: {
    label: "Win rate",
    help: "The share of completed round-trip trades that made money. Higher feels nicer, but it isn't everything — a strategy can win often with small gains yet lose overall if its few losers are large. Judge it alongside total return.",
  },
  n_trades: {
    label: "Trades",
    help: "How many buy/sell fills the strategy made. More trades mean more commission, more slippage, and more taxable events — costs that all come out of your return. Fewer, larger trades are usually cheaper to run.",
  },
};
// --------------------------- what is a picker? -----------------------------
// The single most common confusion from testers: "I don't understand the
// difference between strategy and timing." The app asks for two separate
// choices and the words for them are not self-explanatory, so the explanation
// lives here and is reused by the step headers, the mode cards and the tour.
export const PICKER_VS_TIMER = {
  short: "A strategy chooses WHICH stocks. A timer chooses WHEN to hold them.",
  picker: {
    label: "Strategy — what to own",
    body: "Runs down the list of available companies and ranks them, then buys the top handful. “Momentum” buys whatever has been rising fastest; “Value” buys whatever looks cheapest. It re-ranks periodically, so the basket changes over time.",
  },
  timer: {
    label: "Timer — when to hold it",
    body: "Takes the basket it was handed and decides, day by day, whether to actually be holding each name or sitting in cash. “Buy & Hold” always holds. “RSI” only holds after a stock has dropped sharply, and sells once it recovers.",
  },
  example: {
    title: "A worked example",
    body: "Pair Momentum with Buy & Hold and you get: every month, buy the 15 fastest-rising stocks and hold them, no matter what. Swap the timer to Moving-Average Cross and you get: pick the same 15 stocks, but only hold each one while it's above its own long-run average — step aside when it turns down. Same stock picks, very different ride.",
  },
  why: "They are separate because they fail differently. A picker can choose good companies at bad moments; a timer can have perfect discipline about a basket of duds. Splitting them lets you see which half is doing the work — including whether either is doing anything at all beyond what buying the index would have done.",
};
const WIKI = (title, slug) => ({
  title,
  url: `https://en.wikipedia.org/wiki/${slug}`,
});
export const PICKER_DETAIL = {
  momentum: {
    summary:
      "Ranks every candidate by its return over a trailing window and buys the strongest.",
    rationale:
      "Winners have tended to keep winning over horizons of a few months to a year — one of the most persistently documented effects in markets, visible across countries and asset classes. The usual explanations are that investors under-react to good news at first, then pile in late.",
    weakness:
      "Momentum crashes. When a long rally turns, the stocks that ran hardest fall hardest, and the strategy is by construction holding exactly those. It also trades a lot, which in a taxable account is expensive — watch the tax drag figure on the results.",
    wiki: WIKI("Momentum investing", "Momentum_investing"),
  },
  relative_strength: {
    summary:
      "Momentum measured against the benchmark: keeps only names actually beating the index, ranked by how far.",
    rationale:
      "Filtering by relative rather than absolute return is meant to avoid buying a stock that is merely rising with the tide. In a broad rally almost everything is up; the question is what is leading.",
    weakness:
      "In a sharp downturn nothing beats the benchmark, so the filter can empty out and leave you holding little or nothing — which is either prudent or a missed recovery, depending on what happens next.",
    wiki: WIKI("Relative strength", "Relative_strength"),
  },
  random: {
    summary:
      "Picks names at random, reshuffled at every rebalance. This is the control group.",
    rationale:
      "Not a strategy — a yardstick. Any real picker should beat a coin flip over the same period, with the same costs and the same taxes. If it doesn't, its apparent skill was the market's return, not the picker's.",
    weakness:
      "It has none to speak of, which is the point. Run it a few times: the spread between runs shows you how much of any strategy's result could be luck.",
    wiki: WIKI("Random walk hypothesis", "Random_walk_hypothesis"),
  },
  value_pe: {
    summary:
      "Buys the cheapest stocks by price-to-earnings ratio. Loss-making companies are dropped.",
    rationale:
      "Paying less per dollar of earnings has historically been rewarded, the classic argument being that the market over-punishes dull or troubled businesses and their prices eventually revert.",
    weakness:
      "Value traps: a stock is often cheap because the business is genuinely deteriorating, and the ratio keeps looking attractive right up until earnings collapse. Value also underperformed for most of the 2010s, which is longer than most people's patience.",
    wiki: WIKI("Price–earnings ratio", "Price%E2%80%93earnings_ratio"),
  },
  price_to_book: {
    summary: "Buys stocks cheapest relative to the book value of their assets.",
    rationale:
      "The original academic value measure. Buying below the accounting value of what a company owns has a long history of outperformance in the data.",
    weakness:
      "Book value has aged badly as a measure. It captures factories and inventory well and software, brands and research spending barely at all, so it systematically flags asset-heavy old-economy firms as cheap and modern ones as expensive.",
    wiki: WIKI("P/B ratio", "P/B_ratio"),
  },
  small_cap: {
    summary:
      "Buys the smallest companies in the universe by market capitalization.",
    rationale:
      "Small companies have historically returned more than large ones, compensation for being riskier, less liquid and less researched.",
    weakness:
      "The premium is weak and unreliable — much of it disappeared after it was published, and much of what remains comes from tiny illiquid companies. Note also that this universe is ~500 large listed firms, so the “small” names here are not small in absolute terms.",
    wiki: WIKI("Size premium", "Size_premium"),
  },
  quality_roe: {
    summary:
      "Buys companies generating the most profit per dollar of shareholder equity.",
    rationale:
      "Profitable, efficiently run businesses have tended to beat unprofitable ones — an effect that survives even after controlling for how cheap they are, and one of the few factors that held up out of sample.",
    weakness:
      "High return-on-equity can be manufactured with debt, since borrowing shrinks the equity the ratio divides by. It also correlates with being expensive: quality is rarely on sale.",
    wiki: WIKI("Return on equity", "Return_on_equity"),
  },
  growth_revenue: {
    summary: "Buys the companies whose sales are growing fastest.",
    rationale:
      "Betting that rapid growth continues and that the market underestimates how long a fast-growing company can compound.",
    weakness:
      "Growth is the factor most exposed to paying too much. Fast growers are usually priced for it, so the strategy tends to buy high multiples and suffers badly when rates rise or growth merely slows.",
    wiki: WIKI("Growth investing", "Growth_investing"),
  },
  high_dividend: {
    summary:
      "Buys the highest dividend-yielding stocks. Zero-yield names are dropped.",
    rationale:
      "Income investing: a high yield suggests a mature, cash-generating business, and the dividend pays you while you wait.",
    weakness:
      "Yield rises when the price falls, so screening for the highest yields reliably surfaces companies in trouble shortly before they cut the dividend. And in a taxable account dividends are income — this backtest does not model dividend tax at all, so the real-world result would be worse than shown here.",
    wiki: WIKI("Dividend yield", "Dividend_yield"),
  },
  earnings_surprise: {
    summary:
      "Buys the companies that most recently beat their earnings estimates by the widest margin.",
    rationale:
      "Post-earnings-announcement drift: prices keep moving in the direction of an earnings surprise for weeks afterwards, as if the market digests the news slowly.",
    weakness:
      "The drift is measured in weeks, so capturing it means trading fast and often — the transaction costs and short-term tax rates modeled here eat much of it. This picker is also the most exposed to the snapshot problem below: it only knows the latest surprise, not the one that applied on a date in the past.",
    wiki: WIKI(
      "Post-earnings-announcement drift",
      "Post%E2%80%93earnings-announcement_drift",
    ),
  },
};
export const TIMER_DETAIL = {
  buy_hold: {
    summary: "Always holds. Never times anything.",
    rationale:
      "The baseline every timer must beat. It pays the least in commission, and by never selling it defers capital-gains tax indefinitely — a real, compounding advantage that shows up directly in the after-tax number.",
    weakness:
      "You sit through every drawdown in full. Check the drawdown chart: holding through a 50% fall is easy in a backtest and hard in life.",
    wiki: WIKI("Buy and hold", "Buy_and_hold"),
  },
  ma_cross: {
    summary: "Holds only while a fast moving average sits above a slow one.",
    rationale:
      "The classic trend filter. Its real appeal is not higher returns but a gentler ride: it tends to step aside during sustained declines, so drawdowns are usually shallower than buy-and-hold.",
    weakness:
      "Whipsaw. In a choppy, directionless market the averages cross back and forth and you buy high and sell low repeatedly, paying costs and short-term tax each time. It is also always late by construction — it cannot get out before a fall, only after one starts.",
    wiki: WIKI("Moving average crossover", "Moving_average_crossover"),
  },
  rsi: {
    summary:
      "Buys when the stock is oversold and holds until it recovers past an exit level.",
    rationale:
      "Buying the dip. Sharp short-term falls often overshoot and partially retrace, so entering after one and leaving on the bounce aims to harvest that.",
    weakness:
      "Mean reversion is the opposite bet to trend, and it fails catastrophically in exactly one scenario: a stock that keeps falling. “Oversold” has no floor — it will buy at −30% and again at −60%.",
    wiki: WIKI("Relative strength index", "Relative_strength_index"),
  },
  macd: {
    summary:
      "Holds while the MACD line is above its signal line — while upward momentum is building.",
    rationale:
      "A smoother, more responsive cousin of the moving-average cross, designed to signal a change in momentum slightly earlier than a raw price crossover would.",
    weakness:
      "Same whipsaw problem as any trend filter, and being more responsive means more false signals rather than fewer. Its parameters are also the most over-tuned in common use — worth running the out-of-sample validation on this one.",
    wiki: WIKI("MACD", "MACD"),
  },
  bollinger: {
    summary:
      "Buys at the lower volatility band and sells when price reaches the upper one.",
    rationale:
      "A statistical version of buying the dip: the bands are set a couple of standard deviations from a moving average, so touching the lower one means an unusually large move relative to the stock's own recent volatility.",
    weakness:
      "The bands widen as volatility rises, so in a genuine crash the lower band runs away downwards and the signal keeps firing all the way down.",
    wiki: WIKI("Bollinger Bands", "Bollinger_Bands"),
  },
  momentum12: {
    summary:
      "Holds a stock only while its trailing 12-month return is above a threshold.",
    rationale:
      "Absolute momentum, or time-series momentum: rather than comparing stocks to each other, it asks only whether this one is in an uptrend. Historically it has cut exposure ahead of prolonged bear markets.",
    weakness:
      "A twelve-month window is slow. It will hold through the first several months of a decline and stay out through the first several months of a recovery.",
    wiki: WIKI("Momentum investing", "Momentum_investing"),
  },
  dual_momentum: {
    summary:
      "Requires both: the stock must be up over the window AND beating the benchmark.",
    rationale:
      "Combining absolute and relative momentum is meant to filter out both the stock that is only rising with the market and the market-beater that is beating it by falling less.",
    weakness:
      "Two conditions means a stricter filter, which means long stretches in cash. Being out of the market is itself a bet, and an expensive one to get wrong.",
    wiki: WIKI("Momentum investing", "Momentum_investing"),
  },
  turtle: {
    summary:
      "Buys a breakout to a new high and exits when price drops below a recent low.",
    rationale:
      "The rule set from the famous 1980s Turtle Traders experiment, which set out to show that trading could be taught as a mechanical system. It rides large trends and cuts losers quickly.",
    weakness:
      "Built for futures markets with strong trends, and it needs them: most breakouts fail, so it strings together many small losses waiting for the occasional large win. That pattern is psychologically brutal and tax-inefficient.",
    wiki: WIKI("Turtle Traders", "Turtle_Traders"),
  },
  vol_reversion: {
    summary:
      "Enters when short-term volatility spikes well above its longer-run level, exits when it calms.",
    rationale:
      "A bet that panic reverts. Volatility clusters and then subsides, and the price damage done during a spike is often partly undone as it fades.",
    weakness:
      "A volatility spike is equally the signature of a company in real trouble. This timer cannot tell a panic from a repricing, and it buys both.",
    wiki: WIKI("Volatility (finance)", "Volatility_(finance)"),
  },
  trend_stop: {
    summary:
      "Holds while price is above its long moving average, but exits immediately on a set percentage loss.",
    rationale:
      "A trend filter with a seatbelt. The stop is there to bound the damage from a single position falling apart faster than the slow average can react.",
    weakness:
      "A fixed percentage stop ignores how volatile the stock actually is: too tight for a volatile name and you are stopped out by noise, too loose for a calm one and it never triggers. Stops also convert paper losses into realized ones, and lock in the sale at the worst moment.",
    wiki: WIKI("Stop-loss order", "Stop-loss_order"),
  },
  trend_switch: {
    summary:
      "Holds a leveraged S&P 500 fund while SPY is in an uptrend and switches to Treasury bonds when it isn't — checked every trading day at the close.",
    rationale:
      "Leveraged funds earn their keep in calm, rising markets and do their damage in long declines. A slow trend filter tries to keep the leverage only for the first kind: once SPY is more than the band above its 175-day average, hold the 2× fund; once it is more than the band below, hold intermediate Treasuries, which have often risen when stocks fell. The band stops the rule flip-flopping while SPY hovers near its average.",
    weakness:
      "Leverage magnifies losses, and the rule only reacts at the close — a sudden crash hits a 2× fund twice as hard before it can switch. In a choppy, sideways market it whipsaws, and every switch is a taxable sale. Bonds are not a guaranteed hedge: in 2022 stocks and Treasuries fell together, and this rule's deepest drawdown came then. And no leveraged ETF existed before mid-2006, so the test has seen only a few bear markets — and this exact setting was chosen from many tried on that same history.",
    wiki: WIKI("Trend following", "Trend_following"),
  },
};
const RANK = { good: 0, low: 1, moderate: 2, high: 3 };
export function overallTrust(items) {
  return items.reduce(
    (worst, it) => (RANK[it.level] > RANK[worst] ? it.level : worst),
    "good",
  );
}

export const TRUST_HEADLINE = {
  good: "This result is about as trustworthy as free data allows",
  low: "Trustworthy, with a couple of things to keep in mind",
  moderate: "Take this result with a pinch of salt",
  high: "Treat this result with real skepticism",
};
function yearsBetween(start, end) {
  return (
    (new Date(end).getTime() - new Date(start).getTime()) / (365.25 * 864e5)
  );
}

/**
 * Decide which honest caveats apply to THIS run, from metadata — not hardcoded
 * per result. Inputs are the picker that was used (with its `look_ahead_risk`
 * flag) and the universe option that was used (with its `bias_caveat` text),
 * both straight from the shipped strategy catalog (build/webdata/catalog.json).
 */
/**
 * Broad index ETFs — the corner of this dataset with no survivorship problem,
 * since each of these funds still trades. Mirrors DEFAULT_MENU in
 * strategies/tax_managed.py plus the other funds shipped in data/.
 */
const INDEX_FUNDS = new Set([
  "SPY", "QQQ", "DIA", "MDY", "IWM", "IJR", "EFA", "EEM", "IWD", "IWF", "RSP",
  "VTI", "VOO", "VEA", "VWO", "AGG", "TLT", "IEF", "GLD", "SLV", "USO", "ARKK",
  "XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY",
]);

/**
 * Daily-reset leveraged and inverse ETFs -> their daily multiple of the index.
 * Only SSO ships in data/ today; the others are listed so the warning still
 * fires if one is ever added. No leveraged ETF traded before June 2006.
 */
const LEVERAGED_ETFS = new Map(Object.entries({
  SSO: 2, QLD: 2, DDM: 2, MVV: 2, UWM: 2, UBT: 2,
  UPRO: 3, SPXL: 3, TQQQ: 3, UDOW: 3, TNA: 3, TMF: 3, TYD: 3,
  SDS: -2, QID: -2, SPXU: -3, SPXS: -3, SQQQ: -3, TZA: -3,
}));

/** The honest caveats for a leveraged fund in the basket, or null if none. */
function leverageCaveat(basket) {
  const lev = (basket ?? []).filter((t) => LEVERAGED_ETFS.has(t));
  if (lev.length === 0) return null;
  const maxX = Math.max(...lev.map((t) => Math.abs(LEVERAGED_ETFS.get(t))));
  const first = lev[0];
  const m = LEVERAGED_ETFS.get(first);
  const x = Math.abs(m);
  const names = lev.join(", ");
  const short =
    lev.includes("SSO")
      ? "SSO only began trading in June 2006, so no backtest can hold it earlier — a window that starts before then sits in cash or the safe asset until it exists — and the test has seen only a few bear markets."
      : "No leveraged ETF traded before mid-2006, so the test has seen only a few bear markets.";
  return {
    level: maxX >= 3 ? "high" : "moderate",
    title: `${names} ${lev.length === 1 ? "is a leveraged fund" : "are leveraged funds"} — losses are magnified too`,
    body:
      `${first} resets every day to ${m < 0 ? "−" : ""}${x}× the index's daily move. That magnifies losses as much as gains: on a day the index moves 10% the wrong way, a ${x}× fund loses about ${10 * x}%, and a rule checked at the close can only react afterwards. ` +
      "Daily-reset funds also decay in choppy, sideways markets — the index can end flat while the fund ends down. " +
      "This result assumes the rule was followed every single trading day at the close, with no exceptions or delays. " +
      short +
      (lev.includes("SSO")
        ? " In this project's research the SSO trend rule beat SPY after California tax over most past periods, but not with statistical confidence: almost all of its lead came from sidestepping 2000-02 and 2008, its after-tax edge since 2010 was about zero, and the same rule did no better than buy-and-hold on 33 other stock markets (research/STRATEGY_SEARCH.md)."
        : ""),
  };
}

export function assessTrust(args) {
  const { mode, picker, universeOption, period, tickersUsed, tradeRule, basket } =
    args;
  const items = [];
  const span = yearsBetween(period.start, period.end);
  // 1. Look-ahead risk from the picker's data source.
  if (mode === "ai" && picker) {
    if (picker.look_ahead_risk) {
      const longWindow = span > 3;
      items.push({
        level: longWindow ? "high" : "moderate",
        title: `“${picker.name}” uses present-day company data for past decisions`,
        body:
          `This picker ranks stocks using today's fundamentals snapshot (P/E, ROE, …), which wasn't known back then. ` +
          (longWindow
            ? `Your ${span.toFixed(0)}-year window reaches well before that snapshot, so the earlier results are unrealistically good — this is look-ahead bias. Only the most recent year or two is meaningfully trustworthy.`
            : `Your window is fairly recent, which limits the distortion — but it's still not point-in-time data, so treat it as indicative, not exact.`),
      });
    } else {
      items.push({
        level: "good",
        title: `“${picker.name}” uses only price history`,
        body: "It needs no fundamentals snapshot, so it's free of look-ahead bias and honest to backtest over any time period.",
      });
    }
  }
  // 2. Universe bias — pull the caveat text straight from the universe metadata.
  // A shortlist of index funds is the one case with no survivorship problem to
  // warn about, so it must not inherit the full-dataset caveat below.
  const shortlist = mode !== "manual" && tickersUsed && tickersUsed.length > 0;
  if (shortlist) {
    const allFunds = tickersUsed.every((t) => INDEX_FUNDS.has(t));
    items.push(
      allFunds
        ? {
            level: "good",
            title: "A shortlist of index funds — no survivorship bias",
            body: `The strategy ranked ${tickersUsed.length} broad index ETFs rather than individual companies. Every one of them still trades today and was buyable on the day the backtest says so, so unlike the per-stock data there are no quietly-missing losers inflating the result.`,
          }
        : {
            level: "moderate",
            title: "You ranked a shortlist you chose yourself",
            body: `The strategy only ever considered the ${tickersUsed.length} tickers on your shortlist. If you assembled that list knowing how these names turned out, the result flatters itself no matter how the ranking works.`,
          },
    );
  } else if (mode === "manual") {
    const funds =
      (basket ?? []).length > 0 &&
      basket.every((t) => INDEX_FUNDS.has(t) || LEVERAGED_ETFS.has(t));
    items.push(
      funds
        ? {
            level: "moderate",
            title: "You chose these funds with hindsight",
            body: "Every fund in your basket still trades, so the prices carry no survivorship bias. But you picked the funds (and any rule settings) knowing how this period turned out, and a combination tuned on the same history it is tested on tends to look better than it will going forward.",
          }
        : {
            level: "moderate",
            title: "You picked from today's well-known survivors",
            body: "The ~530 selectable stocks are companies that are prominent enough to still have data today. Firms that went bankrupt or were delisted aren't here, so hand-picking familiar names tends to look better than investing blindly would have.",
          },
    );
  } else if (universeOption) {
    if (universeOption.id === "sp500-pit") {
      items.push({
        level: "moderate",
        title: "Survivorship: delisted companies are missing",
        body: `Good news — buys are restricted to real S&P 500 members on each date, so there's no membership look-ahead. But: ${universeOption.bias_caveat}`,
      });
    } else {
      items.push({
        level: "high",
        title: "Membership look-ahead bias (full dataset)",
        body: `You used the full local dataset rather than point-in-time S&P 500 membership. ${universeOption.bias_caveat} Switching the universe to “S&P 500 point-in-time” under Advanced options gives a more honest result.`,
      });
    }
  }
  // 3. The trading rule, when it is doing the heavy lifting.
  if (tradeRule === "tax_managed") {
    items.push({
      level: "moderate",
      title: "Most of this edge is the trading rule, not the signal",
      body: "The tax-managed rule rations sales against a yearly realized-gain budget, which cuts the tax drag by roughly 3 points a year. Run the same combo with the standard rule to see how little the ranking is worth on its own — and remember this only helps in a taxable account. In an IRA or 401(k) there is nothing to defer.",
    });
  }
  // 4. Leveraged funds anywhere in the basket (manual or a picker's menu).
  const leverage = leverageCaveat(basket);
  if (leverage) items.push(leverage);
  // 5. Always-on reminder about what "after-tax" assumes.
  items.push({
    level: "low",
    title: "After-tax numbers assume you sell everything at the end",
    body: "The after-tax figures apply a final capital-gains tax as if the whole portfolio were liquidated on the last day. Costs (commission, slippage) are modeled on every trade. As always, past performance doesn't predict the future.",
  });
  return items;
}
