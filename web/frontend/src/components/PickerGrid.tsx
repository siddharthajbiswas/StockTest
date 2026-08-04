import { useState } from "react";
import type { Picker } from "../types";
import { PICKER_DETAIL } from "../content";
import { StrategyDetail } from "./StrategyDetail";

interface Props {
  pickers: Picker[];
  selected: string | null;
  onSelect: (id: string) => void;
}

/** Card grid of the 10 pickers. The look-ahead-risk caveat is surfaced directly
 *  on the card — a green "full-history" badge vs an amber "recent-period" one.
 *
 *  The card is a div rather than a button because it now contains its own
 *  "Learn more" control, and a button inside a button is invalid HTML that
 *  browsers resolve unpredictably. Role and key handling restore what the
 *  native element gave us. */
export function PickerGrid({ pickers, selected, onSelect }: Props) {
  const [detailId, setDetailId] = useState<string | null>(null);
  const detailFor = pickers.find((p) => p.id === detailId);

  return (
    <>
      <div className="grid cols-2">
        {pickers.map((p) => {
          const risky = p.look_ahead_risk;
          return (
            <div
              key={p.id}
              role="button"
              tabIndex={0}
              aria-pressed={selected === p.id}
              className={"card selectable" + (selected === p.id ? " selected" : "")}
              onClick={() => onSelect(p.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(p.id);
                }
              }}
            >
              <h3>
                {p.name}
                {selected === p.id && <span className="check">✓</span>}
              </h3>

              <span className={"badge " + (risky ? "warn" : "good")} style={{ marginTop: 10 }}>
                <span className="dotb" />
                {risky ? "Best for recent-period analysis" : "Reliable for full-history backtests"}
              </span>

              <p className="desc">{p.description}</p>

              {risky && (
                <div className="caveat">
                  ⚠️ Uses today’s fundamentals snapshot, not point-in-time data. Trust results
                  only over a recent window — historical numbers are optimistic.
                </div>
              )}

              <button
                className="btn-link learn-more"
                onClick={(e) => {
                  e.stopPropagation(); // don't also select the card
                  setDetailId(p.id);
                }}
              >
                Learn more →
              </button>
            </div>
          );
        })}
      </div>

      {detailFor && (
        <StrategyDetail
          kind="picker"
          name={detailFor.name}
          description={detailFor.description}
          detail={PICKER_DETAIL[detailFor.id]}
          params={detailFor.params}
          lookAheadRisk={detailFor.look_ahead_risk}
          onClose={() => setDetailId(null)}
        />
      )}
    </>
  );
}
