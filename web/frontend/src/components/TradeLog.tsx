import { useState } from "react";
import type { RoundTrip } from "../types";
import { money, signedPct } from "../format";
import { StockHistory } from "./StockHistory";

const PAGE = 40;

interface Props {
  trips: RoundTrip[];
  /** symbol -> company name, for the hover title. Empty map is fine. */
  names: Map<string, string>;
}

export function TradeLog({ trips, names }: Props) {
  const [limit, setLimit] = useState(PAGE);
  const [openSymbol, setOpenSymbol] = useState<string | null>(null);

  if (trips.length === 0) {
    return (
      <p className="hint">
        No completed round trips — positions were opened but not closed within the window
        (e.g. a Buy &amp; Hold strategy still holding at the end).
      </p>
    );
  }
  // Most recent exits first.
  const sorted = [...trips].sort((a, b) => (a.exit_date < b.exit_date ? 1 : -1));
  const shown = sorted.slice(0, limit);

  return (
    <div>
      <div style={{ overflowX: "auto" }}>
        <table className="mini-table trade-log">
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Entry</th>
              <th>Exit</th>
              <th>Held</th>
              <th>Buy</th>
              <th>Sell</th>
              <th>P&amp;L</th>
              <th>Return</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((t, i) => {
              const win = t.pnl > 0;
              const name = names.get(t.ticker);
              return (
                <tr key={i}>
                  <td style={{ textAlign: "left" }}>
                    <button
                      className="ticker-link mono"
                      // The native title is the tooltip here on purpose: it
                      // works on the table's horizontal scroll and needs no
                      // positioning logic against a clipped container.
                      title={name ? `${t.ticker} — ${name}\nClick for price history` : `${t.ticker}\nClick for price history`}
                      onClick={() => setOpenSymbol(t.ticker)}
                    >
                      {t.ticker}
                    </button>
                  </td>
                  <td>{t.entry_date}</td>
                  <td>{t.exit_date}</td>
                  <td>{t.holding_days}d</td>
                  <td className="mono">{money(t.entry_price, 2)}</td>
                  <td className="mono">{money(t.exit_price, 2)}</td>
                  <td className={"mono " + (win ? "pnl-pos" : "pnl-neg")}>{money(t.pnl)}</td>
                  <td className={win ? "pnl-pos" : "pnl-neg"}>{signedPct(t.return_pct)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {limit < sorted.length && (
        <button className="btn" style={{ marginTop: 12 }} onClick={() => setLimit((l) => l + PAGE)}>
          Show more ({sorted.length - limit} left)
        </button>
      )}

      {openSymbol && (
        <StockHistory
          symbol={openSymbol}
          name={names.get(openSymbol)}
          // Every trip in this symbol, oldest first, so the table reads
          // chronologically alongside the chart.
          trips={trips
            .filter((t) => t.ticker === openSymbol)
            .sort((a, b) => (a.entry_date < b.entry_date ? -1 : 1))}
          onClose={() => setOpenSymbol(null)}
        />
      )}
    </div>
  );
}
