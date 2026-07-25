// ---------------------------------------------------------------------------
// SINGLE SOURCE OF TRUTH for user-facing explanations.
//
// Everything a non-expert reads about a metric or a caveat lives here, so the
// copy is easy to review and edit for accuracy in one place — nothing is
// scattered through the chart/panel components. The trust logic below CHOOSES
// which caveats apply from the picker/universe METADATA (Phase W2); it never
// hardcodes a verdict per strategy.
// ---------------------------------------------------------------------------

import type { Mode, Picker, UniverseOption } from "./types";

// ----------------------------- metric help ---------------------------------
export interface MetricInfo {
  label: string;
  help: string; // what it measures · what's good · (why pre/post-tax differ)
}

export const METRIC_INFO: Record<string, MetricInfo> = {
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

// ------------------------------ caveats ------------------------------------
export type TrustLevel = "good" | "low" | "moderate" | "high";

export interface TrustItem {
  level: TrustLevel;
  title: string;
  body: string;
}

const RANK: Record<TrustLevel, number> = { good: 0, low: 1, moderate: 2, high: 3 };

export function overallTrust(items: TrustItem[]): TrustLevel {
  return items.reduce<TrustLevel>(
    (worst, it) => (RANK[it.level] > RANK[worst] ? it.level : worst),
    "good",
  );
}

export const TRUST_HEADLINE: Record<TrustLevel, string> = {
  good: "This result is about as trustworthy as free data allows",
  low: "Trustworthy, with a couple of things to keep in mind",
  moderate: "Take this result with a pinch of salt",
  high: "Treat this result with real skepticism",
};

function yearsBetween(start: string, end: string): number {
  return (new Date(end).getTime() - new Date(start).getTime()) / (365.25 * 864e5);
}

/**
 * Decide which honest caveats apply to THIS run, from metadata — not hardcoded
 * per result. Inputs are the picker that was used (with its `look_ahead_risk`
 * flag) and the universe option that was used (with its `bias_caveat` text),
 * both straight from the backend catalog.
 */
export function assessTrust(args: {
  mode: Mode;
  picker?: Picker;
  universeOption?: UniverseOption;
  period: { start: string; end: string };
}): TrustItem[] {
  const { mode, picker, universeOption, period } = args;
  const items: TrustItem[] = [];
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
  if (mode === "manual") {
    items.push({
      level: "moderate",
      title: "You picked from today's well-known survivors",
      body: "The ~530 selectable stocks are companies that are prominent enough to still have data today. Firms that went bankrupt or were delisted aren't here, so hand-picking familiar names tends to look better than investing blindly would have.",
    });
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

  // 3. Always-on reminder about what "after-tax" assumes.
  items.push({
    level: "low",
    title: "After-tax numbers assume you sell everything at the end",
    body: "The after-tax figures apply a final capital-gains tax as if the whole portfolio were liquidated on the last day. Costs (commission, slippage) are modeled on every trade. As always, past performance doesn't predict the future.",
  });

  return items;
}
