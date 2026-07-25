import type { Timer } from "../types";

interface Props {
  timers: Timer[];
  selected: string | null;
  onSelect: (id: string) => void;
}

/** Card grid of the 10 timers — same visual pattern as the picker grid. */
export function TimerGrid({ timers, selected, onSelect }: Props) {
  return (
    <div className="grid cols-2">
      {timers.map((t) => (
        <button
          key={t.id}
          className={"card selectable" + (selected === t.id ? " selected" : "")}
          onClick={() => onSelect(t.id)}
        >
          <h3>
            {t.name}
            {selected === t.id && <span className="check">✓</span>}
          </h3>
          <p className="desc">{t.description}</p>
        </button>
      ))}
    </div>
  );
}
