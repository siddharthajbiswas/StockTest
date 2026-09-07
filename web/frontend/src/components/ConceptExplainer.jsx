import { PICKER_VS_TIMER as C } from "../content";

/**
 * The picker-vs-timer explainer.
 *
 * Testers consistently could not tell the two apart, and the fix isn't more
 * words on the cards — it's showing the two halves side by side once, with a
 * concrete pairing, before the choices are asked for.
 */
export function ConceptExplainer() {
  return (
    <div className="concept">
      <div className="concept-lead">{C.short}</div>
      <div className="concept-pair">
        <div className="concept-half">
          <h5>{C.picker.label}</h5>
          <p>{C.picker.body}</p>
        </div>
        <div className="concept-arrow" aria-hidden>
          →
        </div>
        <div className="concept-half">
          <h5>{C.timer.label}</h5>
          <p>{C.timer.body}</p>
        </div>
      </div>
      <div className="concept-example">
        <strong>{C.example.title}: </strong>
        {C.example.body}
      </div>
      <div className="concept-example">{C.why}</div>
    </div>
  );
}
