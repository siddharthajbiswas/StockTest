import { overallTrust, TRUST_HEADLINE } from "../content";
const LEVEL_LABEL = {
  good: "Reassuring",
  low: "Minor",
  moderate: "Caution",
  high: "Big caveat",
};
const LEVEL_ICON = { good: "✓", low: "•", moderate: "!", high: "⚠︎" };
export function TrustPanel({ items }) {
  const overall = overallTrust(items);
  return (
    <div className={"trust-panel lvl-" + overall}>
      <div className="trust-head">
        <span className="trust-chip">{LEVEL_ICON[overall]}</span>
        <div>
          <div className="step-kicker" style={{ marginBottom: 4 }}>
            How much should you trust this result?
          </div>
          <h3 style={{ fontSize: 17 }}>{TRUST_HEADLINE[overall]}</h3>
        </div>
      </div>
      <ul className="trust-list">
        {items.map((it, idx) => (
          <li key={idx} className={"trust-item lvl-" + it.level}>
            <span className={"badge trust-badge lvl-" + it.level}>
              {LEVEL_ICON[it.level]} {LEVEL_LABEL[it.level]}
            </span>
            <div>
              <strong>{it.title}</strong>
              <p>{it.body}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
