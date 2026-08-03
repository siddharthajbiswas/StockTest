import type { ParamSpec } from "../types";

export type Params = Record<string, unknown>;

/** Build the default params object for a set of specs (skips null defaults so
 *  the engine applies its own default, e.g. RandomPicker.fraction). */
export function defaultParams(specs: ParamSpec[]): Params {
  const out: Params = {};
  for (const s of specs) {
    if (s.default !== null && s.default !== undefined) out[s.name] = s.default;
  }
  return out;
}

function isNumeric(type: string) {
  return type.includes("int") || type.includes("float");
}
function isBool(type: string) {
  return type.includes("bool");
}

/** Expandable form for a picker/timer's configurable parameters. */
export function ParamEditor({
  title,
  specs,
  values,
  onChange,
}: {
  title: string;
  specs: ParamSpec[];
  values: Params;
  onChange: (next: Params) => void;
}) {
  if (specs.length === 0) {
    return (
      <div className="param-panel">
        <p className="hint" style={{ margin: 0 }}>
          {title} has no adjustable parameters — it runs the same way every time.
        </p>
      </div>
    );
  }

  const setField = (name: string, raw: string, type: string) => {
    const next = { ...values };
    if (raw === "") {
      delete next[name]; // empty -> fall back to the engine default
    } else if (isNumeric(type)) {
      next[name] = Number(raw);
    } else {
      next[name] = raw;
    }
    onChange(next);
  };

  const isDefault = specs.every(
    (s) => JSON.stringify(values[s.name] ?? null) === JSON.stringify(s.default ?? null),
  );

  return (
    <div className="param-panel">
      <div className="param-grid">
        {specs.map((s) => {
          const current = values[s.name];
          const display = current === undefined || current === null ? "" : String(current);
          return (
            <div className="field param-field" key={s.name}>
              <label htmlFor={`p-${s.name}`}>
                {s.name}
                <span className="param-type">{s.type}</span>
              </label>
              {isBool(s.type) ? (
                <input
                  id={`p-${s.name}`}
                  type="checkbox"
                  checked={Boolean(current)}
                  onChange={(e) => onChange({ ...values, [s.name]: e.target.checked })}
                />
              ) : (
                <input
                  id={`p-${s.name}`}
                  className="input"
                  type={isNumeric(s.type) ? "number" : "text"}
                  value={display}
                  placeholder={s.default === null ? "(auto)" : String(s.default)}
                  onChange={(e) => setField(s.name, e.target.value, s.type)}
                />
              )}
              <p className="hint">{s.description}</p>
            </div>
          );
        })}
      </div>
      {!isDefault && (
        <button
          type="button"
          className="btn ghost"
          style={{ marginTop: 6, padding: "4px 8px" }}
          onClick={() => onChange(defaultParams(specs))}
        >
          ↺ Reset to defaults
        </button>
      )}
    </div>
  );
}
