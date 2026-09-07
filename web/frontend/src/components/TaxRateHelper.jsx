import { computeRates, STATE_CODES, STATE_TAX, TAX_YEAR } from "../taxTables";
const pct1 = (x) => `${(x * 100).toFixed(2).replace(/\.?0+$/, "")}%`;

/**
 * Turns "what do you earn and where do you live" into the two capital-gains
 * rates the engine needs.
 *
 * Deliberately shows its work rather than just emitting two numbers: the split
 * between federal, NIIT and state is the part people are actually unsure about,
 * and seeing that a third of the short-term rate is state tax is the insight
 * that makes the after-tax comparison mean something.
 */
export function TaxRateHelper({
  status,
  income,
  state,
  onChange,
  onApply,
  applied,
}) {
  const r = computeRates(status, income, state);
  const st = STATE_TAX[state];
  const rows = [
    { label: "Federal", short: r.federalShort, long: r.federalLong },
  ];
  if (r.niit > 0) {
    rows.push({
      label: "Net Investment Income Tax",
      short: r.niit,
      long: r.niit,
    });
  }
  rows.push({
    label: `State — ${r.stateName}`,
    short: r.stateShort,
    long: r.stateLong,
  });
  return (
    <div className="tax-helper">
      <div className="row">
        <div className="field">
          <label htmlFor="filing">Filing status</label>
          <select
            id="filing"
            className="input"
            value={status}
            onChange={(e) => onChange({ taxStatus: e.target.value })}
          >
            <option value="single">Single</option>
            <option value="married">Married, filing jointly</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="taxable-income">Annual taxable income</label>
          <input
            id="taxable-income"
            type="number"
            className="input"
            min={0}
            step={5000}
            value={income}
            onChange={(e) => onChange({ taxIncome: Number(e.target.value) })}
          />
          <p className="hint">
            Income after deductions — line 15 of your 1040.
          </p>
        </div>
        <div className="field">
          <label htmlFor="tax-state">State</label>
          <select
            id="tax-state"
            className="input"
            value={state}
            onChange={(e) => onChange({ taxState: e.target.value })}
          >
            {STATE_CODES.map((code) => (
              <option key={code} value={code}>
                {STATE_TAX[code].name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <table className="mini-table rate-table">
        <thead>
          <tr>
            <th style={{ textAlign: "left" }}>Component</th>
            <th>Short-term</th>
            <th>Long-term</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.label}>
              <td style={{ textAlign: "left" }}>{row.label}</td>
              <td className="mono">{pct1(row.short)}</td>
              <td className="mono">{pct1(row.long)}</td>
            </tr>
          ))}
          <tr className="rate-total">
            <td style={{ textAlign: "left" }}>Your marginal rate</td>
            <td className="mono">{pct1(r.shortTotal)}</td>
            <td className="mono">{pct1(r.longTotal)}</td>
          </tr>
        </tbody>
      </table>

      {r.stateNote && (
        <div className="caveat" style={{ marginTop: 10 }}>
          {r.stateNote}
        </div>
      )}
      {st &&
        st.brackets.length === 1 &&
        st.brackets[0].rate === 0 &&
        !st.longTerm && (
          <p className="hint" style={{ marginTop: 8 }}>
            {r.stateName} levies no income tax, so your rate is federal only.
          </p>
        )}

      <div className="tax-helper-actions">
        <button
          className="btn primary"
          onClick={() => onApply(r.shortTotal * 100, r.longTotal * 100)}
        >
          {applied ? "✓ Applied" : "Use these rates"}
        </button>
        <p className="hint" style={{ margin: 0 }}>
          {applied
            ? "The backtest is using these rates."
            : "Applying fills in the rate boxes above — you can still edit them."}
        </p>
      </div>

      <p className="hint" style={{ marginTop: 12 }}>
        {TAX_YEAR} rates. This is the rate on your <em>next</em> dollar of gain,
        so a very large gain that pushes you into a higher bracket would be
        taxed at a blend. State brackets are simplified and local income taxes
        (e.g. New York City) are not included. An estimate to start from — not
        tax advice.
      </p>
    </div>
  );
}
