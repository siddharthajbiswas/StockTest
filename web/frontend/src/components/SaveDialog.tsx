import { useState } from "react";

/** A minimal modal to name and save the current strategy. */
export function SaveDialog({
  defaultName,
  onCancel,
  onSave,
  error,
  saving,
}: {
  defaultName: string;
  onCancel: () => void;
  onSave: (name: string) => void;
  error: string | null;
  saving: boolean;
}) {
  const [name, setName] = useState(defaultName);
  return (
    <div className="results-overlay" onClick={onCancel}>
      <div className="save-dialog" onClick={(e) => e.stopPropagation()}>
        <h3 style={{ fontSize: 18 }}>Save this strategy</h3>
        <p className="sub" style={{ marginTop: 6, marginBottom: 14 }}>
          Give it a name so you can re-run or edit it later.
        </p>
        <input
          className="input"
          autoFocus
          style={{ width: "100%" }}
          value={name}
          maxLength={80}
          placeholder="e.g. My momentum play"
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && name.trim()) onSave(name.trim());
            if (e.key === "Escape") onCancel();
          }}
        />
        {error && <div className="error-banner" style={{ marginTop: 12 }}>{error}</div>}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 18 }}>
          <button className="btn" onClick={onCancel}>
            Cancel
          </button>
          <button
            className="btn primary"
            disabled={!name.trim() || saving}
            onClick={() => onSave(name.trim())}
          >
            {saving ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
