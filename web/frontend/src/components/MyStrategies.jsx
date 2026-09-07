import { prettyId } from "../format";
function summarize(s) {
  const c = s.config;
  const who =
    c.mode === "manual"
      ? (c.tickers ?? []).join(", ") || "custom basket"
      : `${prettyId(c.picker_id)} picker`;
  return `${who} · ${prettyId(c.timer_id)} timer`;
}

export function MyStrategies({ strategies, onRun, onEdit, onDelete, busy }) {
  if (strategies.length === 0) return null;
  return (
    <section className="section" id="my-strategies">
      <div className="section-head">
        <div className="step-kicker">★ My strategies</div>
        <p className="sub">
          Re-run or edit a strategy you saved earlier — no need to reconfigure.
        </p>
      </div>
      <div className="grid cols-2">
        {strategies.map((s) => (
          <div key={s.id} className="card saved-card">
            <div className="saved-top">
              <h3 style={{ fontSize: 16 }}>{s.name}</h3>
              <button
                className="chip-x"
                title="Delete"
                aria-label={`Delete ${s.name}`}
                onClick={() => onDelete(s)}
              >
                ×
              </button>
            </div>
            <p className="desc" style={{ marginTop: 6 }}>
              {summarize(s)}
            </p>
            <div className="saved-actions">
              <button
                className="btn primary"
                disabled={busy}
                onClick={() => onRun(s)}
              >
                Re-run
              </button>
              <button className="btn" disabled={busy} onClick={() => onEdit(s)}>
                Edit
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
