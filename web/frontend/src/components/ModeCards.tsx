import type { Mode } from "../types";

interface Props {
  mode: Mode | null;
  onPick: (m: Mode) => void;
}

/** The first decision: who picks the stocks. Plain-language, one line each. */
export function ModeCards({ mode, onPick }: Props) {
  return (
    <div id="tour-mode" className="grid cols-2">
      <button
        className={"card selectable mode-card" + (mode === "manual" ? " selected" : "")}
        onClick={() => onPick("manual")}
      >
        <div className="emoji" aria-hidden>🧑‍💻</div>
        <h3>
          Pick stocks myself
          {mode === "manual" && <span className="check">✓</span>}
        </h3>
        <p className="desc">
          Choose your own basket of companies. You’ll still pick a timing rule next, which
          decides when to hold them.
        </p>
      </button>

      <button
        className={"card selectable mode-card" + (mode === "ai" ? " selected" : "")}
        onClick={() => onPick("ai")}
      >
        <div className="emoji" aria-hidden>🤖</div>
        <h3>
          Let a strategy pick for me
          {mode === "ai" && <span className="check">✓</span>}
        </h3>
        <p className="desc">
          Start from a known idea — momentum, value, quality — and let it rank the market and
          choose the basket for you.
        </p>
      </button>
    </div>
  );
}
