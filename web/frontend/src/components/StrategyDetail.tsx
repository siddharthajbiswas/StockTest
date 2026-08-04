import { useEffect } from "react";
import type { StrategyDetail } from "../content";
import type { ParamSpec } from "../types";

interface Props {
  kind: "picker" | "timer";
  name: string;
  /** The one-liner already shown on the card. */
  description: string;
  detail?: StrategyDetail;
  params: ParamSpec[];
  /** Present for pickers only. */
  lookAheadRisk?: boolean;
  onClose: () => void;
}

/**
 * The "learn more" sheet for one picker or timer.
 *
 * Deliberately includes the weakness section: every strategy here has a
 * documented failure mode, and a tool whose whole premise is honest backtesting
 * should not present ten strategies as ten good ideas.
 */
export function StrategyDetail({
  kind,
  name,
  description,
  detail,
  params,
  lookAheadRisk,
  onClose,
}: Props) {
  // Escape closes, matching the results sheet.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="results-overlay" onClick={onClose}>
      <div
        className="detail-sheet"
        role="dialog"
        aria-modal="true"
        aria-label={`About ${name}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="results-head">
          <div>
            <div className="step-kicker">
              {kind === "picker" ? "Stock-picking strategy" : "Timing rule"}
            </div>
            <h2 style={{ fontSize: 22 }}>{name}</h2>
          </div>
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>

        <div className="detail-body">
          <p className="detail-lead">{detail?.summary ?? description}</p>

          {detail && (
            <>
              <h4 className="detail-h">Why people use it</h4>
              <p>{detail.rationale}</p>

              <h4 className="detail-h">Where it breaks down</h4>
              <p>{detail.weakness}</p>
            </>
          )}

          {lookAheadRisk && (
            <div className="caveat" style={{ marginTop: 16 }}>
              ⚠️ This strategy ranks stocks using today's fundamentals snapshot, because
              point-in-time fundamentals aren't freely available. Over a long backtest that
              means it “knew” numbers that hadn't been published yet, which flatters the
              result. Trust it only over a recent window.
            </div>
          )}

          {params.length > 0 && (
            <>
              <h4 className="detail-h">Settings you can change</h4>
              <table className="mini-table detail-params">
                <tbody>
                  {params.map((p) => (
                    <tr key={p.name}>
                      <td className="mono" style={{ textAlign: "left", whiteSpace: "nowrap" }}>
                        {p.name}
                      </td>
                      <td style={{ textAlign: "left" }}>{p.description}</td>
                      <td className="mono" style={{ whiteSpace: "nowrap" }}>
                        {String(p.default)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="hint">
                Tuning these until the backtest looks good is the classic way to fool yourself.
                If you change them, run the out-of-sample validation on the result.
              </p>
            </>
          )}

          {detail?.wiki && (
            <p className="detail-wiki">
              Background reading:{" "}
              <a href={detail.wiki.url} target="_blank" rel="noopener noreferrer">
                {detail.wiki.title} on Wikipedia ↗
              </a>
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
