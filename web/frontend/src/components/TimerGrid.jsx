import { useState } from "react";
import { TIMER_DETAIL } from "../content";
import { StrategyDetail } from "./StrategyDetail";

/** Card grid of the timers — same visual pattern as the picker grid, and the
 *  same div-with-role treatment so the "Learn more" button can live inside. */
export function TimerGrid({ timers, selected, onSelect }) {
  const [detailId, setDetailId] = useState(null);
  const detailFor = timers.find((t) => t.id === detailId);
  return (
    <>
      <div className="grid cols-2">
        {timers.map((t) => (
          <div
            key={t.id}
            role="button"
            tabIndex={0}
            aria-pressed={selected === t.id}
            className={
              "card selectable" + (selected === t.id ? " selected" : "")
            }
            onClick={() => onSelect(t.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(t.id);
              }
            }}
          >
            <h3>
              {t.name}
              {selected === t.id && <span className="check">✓</span>}
            </h3>
            <p className="desc">{t.description}</p>
            <button
              className="btn-link learn-more"
              onClick={(e) => {
                e.stopPropagation();
                setDetailId(t.id);
              }}
            >
              Learn more →
            </button>
          </div>
        ))}
      </div>

      {detailFor && (
        <StrategyDetail
          kind="timer"
          name={detailFor.name}
          description={detailFor.description}
          detail={TIMER_DETAIL[detailFor.id]}
          params={detailFor.params}
          onClose={() => setDetailId(null)}
        />
      )}
    </>
  );
}
