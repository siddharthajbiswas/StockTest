import { useState } from "react";
import type { RoundTrip } from "../types";
import { money, signedPct } from "../format";

const PAGE = 40;

export function TradeLog({ trips }: { trips: RoundTrip[] }) {
  const [limit, setLimit] = useState(PAGE);
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
              return (
                <tr key={i}>
                  <td className="mono" style={{ fontWeight: 650, textAlign: "left" }}>
                    {t.ticker}
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
    </div>
  );
}
