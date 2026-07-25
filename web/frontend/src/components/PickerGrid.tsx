import type { Picker } from "../types";

interface Props {
  pickers: Picker[];
  selected: string | null;
  onSelect: (id: string) => void;
}

/** Card grid of the 10 pickers. The look-ahead-risk caveat is surfaced directly
 *  on the card — a green "full-history" badge vs an amber "recent-period" one. */
export function PickerGrid({ pickers, selected, onSelect }: Props) {
  return (
    <div className="grid cols-2">
      {pickers.map((p) => {
        const risky = p.look_ahead_risk;
        return (
          <button
            key={p.id}
            className={"card selectable" + (selected === p.id ? " selected" : "")}
            onClick={() => onSelect(p.id)}
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
          </button>
        );
      })}
    </div>
  );
}
