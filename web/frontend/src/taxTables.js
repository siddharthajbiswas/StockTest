// ---------------------------------------------------------------------------
// Capital-gains rate lookup — 2025 tax year.
//
// Feeds the rate helper in the settings panel, which turns "what do you earn and
// where do you live" into the two numbers the engine actually needs: a
// short-term rate and a long-term rate.
//
// WHAT THIS MODELS
//   * Federal ordinary-income brackets (short-term gains are taxed as income).
//   * Federal long-term capital-gains brackets (0 / 15 / 20%).
//   * Net Investment Income Tax — a flat 3.8% surtax above a MAGI threshold.
//   * State income tax, which most states levy on capital gains at their
//     ordinary rates. A handful give long-term gains preferential treatment;
//     those are encoded per state.
//
// WHAT THIS DOES NOT MODEL, and why the output is an estimate
//   * MARGINAL vs EFFECTIVE. A realized gain stacks on top of your other
//     income, so a large gain can push you into a higher bracket partway
//     through. We report the marginal rate at your stated taxable income — the
//     rate the NEXT dollar of gain is taxed at — which is the right rate for
//     "what does trading cost me", but it overstates tax on a gain that
//     straddles a bracket edge and understates it on one that clears several.
//   * Deductions, credits, AMT, the $3,000 capital-loss offset against ordinary
//     income, state-level phase-outs, and local/city income taxes (NYC's own
//     income tax is a notable omission for New York City residents).
//   * State brackets are simplified — see STATE_TAX below.
//
// It is a sensible starting point, not tax advice. Every number it produces
// lands in an editable field precisely so an informed user can correct it.
// ---------------------------------------------------------------------------
export const TAX_YEAR = 2025;
// ----------------------------- federal --------------------------------------

/** Ordinary income — what short-term gains are taxed at. */
const FEDERAL_ORDINARY = {
  single: [
    { from: 0, rate: 0.1 },
    { from: 11925, rate: 0.12 },
    { from: 48475, rate: 0.22 },
    { from: 103350, rate: 0.24 },
    { from: 197300, rate: 0.32 },
    { from: 250525, rate: 0.35 },
    { from: 626350, rate: 0.37 },
  ],
  married: [
    { from: 0, rate: 0.1 },
    { from: 23850, rate: 0.12 },
    { from: 96950, rate: 0.22 },
    { from: 206700, rate: 0.24 },
    { from: 394600, rate: 0.32 },
    { from: 501050, rate: 0.35 },
    { from: 751600, rate: 0.37 },
  ],
};

/** Long-term capital gains — the preferential 0/15/20 schedule. */
const FEDERAL_LONG_TERM = {
  single: [
    { from: 0, rate: 0.0 },
    { from: 48350, rate: 0.15 },
    { from: 533400, rate: 0.2 },
  ],
  married: [
    { from: 0, rate: 0.0 },
    { from: 96700, rate: 0.15 },
    { from: 600050, rate: 0.2 },
  ],
};

/** Net Investment Income Tax: 3.8% above these thresholds. Not indexed to
 *  inflation, which is why they have been the same since 2013. */
const NIIT_RATE = 0.038;
const NIIT_THRESHOLD = {
  single: 200000,
  married: 250000,
};
function marginalRate(brackets, income) {
  let rate = brackets[0].rate;
  for (const b of brackets) if (income >= b.from) rate = b.rate;
  return rate;
}

/**
 * State treatment of capital gains, 2025.
 *
 * SIMPLIFICATIONS, stated plainly because they affect the answer:
 *   * Brackets are the state's own taxable-income brackets, which differ from
 *     federal taxable income (different deductions and exemptions). We apply
 *     your federal taxable-income figure to them, which is close enough to pick
 *     the right band for most people but is not exact.
 *   * Graduated states are encoded down to the bands that matter at realistic
 *     incomes; the lowest bands of states whose bottom rates apply only to the
 *     first few thousand dollars are collapsed.
 *   * Local income taxes are excluded (notably New York City and Yonkers, and
 *     Maryland's county piggyback tax, which adds roughly 2.25–3.2%).
 */
export const STATE_TAX = {
  // ---- no individual income tax on wages or gains ----
  AK: {
    name: "Alaska",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
  },
  FL: {
    name: "Florida",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
  },
  NV: {
    name: "Nevada",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
  },
  SD: {
    name: "South Dakota",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
  },
  TX: {
    name: "Texas",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
  },
  WY: {
    name: "Wyoming",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
  },
  TN: {
    name: "Tennessee",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
  },
  NH: {
    name: "New Hampshire",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
    note: "No tax on capital gains. New Hampshire's interest-and-dividends tax was fully repealed for 2025.",
  },
  WA: {
    name: "Washington",
    brackets: [{ from: 0, rate: 0 }],
    marriedDoubles: false,
    longTerm: { flat: 0.07 },
    note: "No income tax, but a 7% excise tax applies to long-term gains above roughly $270k per year. Short-term gains are untaxed by the state.",
  },
  // ---- flat-rate states ----
  AZ: {
    name: "Arizona",
    brackets: [{ from: 0, rate: 0.025 }],
    marriedDoubles: false,
  },
  CO: {
    name: "Colorado",
    brackets: [{ from: 0, rate: 0.044 }],
    marriedDoubles: false,
  },
  GA: {
    name: "Georgia",
    brackets: [{ from: 0, rate: 0.0519 }],
    marriedDoubles: false,
  },
  ID: {
    name: "Idaho",
    brackets: [{ from: 0, rate: 0.05695 }],
    marriedDoubles: false,
  },
  IL: {
    name: "Illinois",
    brackets: [{ from: 0, rate: 0.0495 }],
    marriedDoubles: false,
  },
  IN: {
    name: "Indiana",
    brackets: [{ from: 0, rate: 0.03 }],
    marriedDoubles: false,
    note: "Counties levy an additional income tax, typically 1–3%, not included here.",
  },
  KY: {
    name: "Kentucky",
    brackets: [{ from: 0, rate: 0.04 }],
    marriedDoubles: false,
  },
  MI: {
    name: "Michigan",
    brackets: [{ from: 0, rate: 0.0425 }],
    marriedDoubles: false,
  },
  MS: {
    name: "Mississippi",
    brackets: [{ from: 0, rate: 0.044 }],
    marriedDoubles: false,
  },
  NC: {
    name: "North Carolina",
    brackets: [{ from: 0, rate: 0.0425 }],
    marriedDoubles: false,
  },
  PA: {
    name: "Pennsylvania",
    brackets: [{ from: 0, rate: 0.0307 }],
    marriedDoubles: false,
    note: "Local earned-income taxes do not apply to capital gains, so the state rate is the whole story.",
  },
  UT: {
    name: "Utah",
    brackets: [{ from: 0, rate: 0.0455 }],
    marriedDoubles: false,
  },
  MA: {
    name: "Massachusetts",
    brackets: [
      { from: 0, rate: 0.05 },
      { from: 1000000, rate: 0.09 },
    ],
    marriedDoubles: false,
    note: "Short-term gains are taxed at 8.5%, not the 5% ordinary rate. The 4% millionaire surtax applies above $1M of income.",
  },
  // ---- graduated states ----
  CA: {
    name: "California",
    brackets: [
      { from: 0, rate: 0.01 },
      { from: 10756, rate: 0.02 },
      { from: 25499, rate: 0.04 },
      { from: 40245, rate: 0.06 },
      { from: 55866, rate: 0.08 },
      { from: 70606, rate: 0.093 },
      { from: 360659, rate: 0.103 },
      { from: 432787, rate: 0.113 },
      { from: 721314, rate: 0.123 },
      { from: 1000000, rate: 0.133 },
    ],
    marriedDoubles: true,
    note: "California taxes capital gains fully as ordinary income — there is no long-term discount.",
  },
  NY: {
    name: "New York",
    brackets: [
      { from: 0, rate: 0.04 },
      { from: 13900, rate: 0.045 },
      { from: 21400, rate: 0.0525 },
      { from: 80650, rate: 0.055 },
      { from: 215400, rate: 0.06 },
      { from: 1077550, rate: 0.0685 },
      { from: 5000000, rate: 0.103 },
      { from: 25000000, rate: 0.109 },
    ],
    marriedDoubles: true,
    note: "New York City residents owe an additional city income tax of roughly 3.1–3.9%, which is not included here.",
  },
  NJ: {
    name: "New Jersey",
    brackets: [
      { from: 0, rate: 0.014 },
      { from: 20000, rate: 0.0175 },
      { from: 35000, rate: 0.035 },
      { from: 40000, rate: 0.05525 },
      { from: 75000, rate: 0.0637 },
      { from: 500000, rate: 0.0897 },
      { from: 1000000, rate: 0.1075 },
    ],
    marriedDoubles: false,
  },
  OR: {
    name: "Oregon",
    brackets: [
      { from: 0, rate: 0.0475 },
      { from: 4400, rate: 0.0675 },
      { from: 11050, rate: 0.0875 },
      { from: 125000, rate: 0.099 },
    ],
    marriedDoubles: true,
    note: "Portland-area residents also pay local income taxes not included here.",
  },
  MN: {
    name: "Minnesota",
    brackets: [
      { from: 0, rate: 0.0535 },
      { from: 32570, rate: 0.068 },
      { from: 106990, rate: 0.0785 },
      { from: 198630, rate: 0.0985 },
    ],
    marriedDoubles: true,
    note: "An extra 1% surtax applies to net investment income above $1M.",
  },
  HI: {
    name: "Hawaii",
    brackets: [
      { from: 0, rate: 0.014 },
      { from: 9600, rate: 0.055 },
      { from: 24000, rate: 0.0765 },
      { from: 48000, rate: 0.0825 },
      { from: 175000, rate: 0.09 },
      { from: 250000, rate: 0.1 },
      { from: 325000, rate: 0.11 },
    ],
    marriedDoubles: true,
    longTerm: { flat: 0.0725 },
    note: "Long-term gains are capped at an alternative 7.25% rate.",
  },
  DC: {
    name: "District of Columbia",
    brackets: [
      { from: 0, rate: 0.04 },
      { from: 10000, rate: 0.06 },
      { from: 40000, rate: 0.065 },
      { from: 60000, rate: 0.085 },
      { from: 250000, rate: 0.0925 },
      { from: 500000, rate: 0.0975 },
      { from: 1000000, rate: 0.1075 },
    ],
    marriedDoubles: false,
  },
  MD: {
    name: "Maryland",
    brackets: [
      { from: 0, rate: 0.02 },
      { from: 1000, rate: 0.03 },
      { from: 2000, rate: 0.04 },
      { from: 3000, rate: 0.0475 },
      { from: 100000, rate: 0.05 },
      { from: 125000, rate: 0.0525 },
      { from: 150000, rate: 0.055 },
      { from: 250000, rate: 0.0575 },
    ],
    marriedDoubles: false,
    note: "Counties add a local income tax of roughly 2.25–3.2% on top, not included here.",
  },
  VA: {
    name: "Virginia",
    brackets: [
      { from: 0, rate: 0.02 },
      { from: 3000, rate: 0.03 },
      { from: 5000, rate: 0.05 },
      { from: 17000, rate: 0.0575 },
    ],
    marriedDoubles: false,
  },
  CT: {
    name: "Connecticut",
    brackets: [
      { from: 0, rate: 0.02 },
      { from: 10000, rate: 0.045 },
      { from: 50000, rate: 0.055 },
      { from: 100000, rate: 0.06 },
      { from: 200000, rate: 0.065 },
      { from: 250000, rate: 0.069 },
      { from: 500000, rate: 0.0699 },
    ],
    marriedDoubles: true,
  },
  OH: {
    name: "Ohio",
    brackets: [
      { from: 0, rate: 0 },
      { from: 26050, rate: 0.0275 },
      { from: 100000, rate: 0.035 },
    ],
    marriedDoubles: false,
    note: "Municipalities levy their own income taxes, but most exempt capital gains.",
  },
  WI: {
    name: "Wisconsin",
    brackets: [
      { from: 0, rate: 0.035 },
      { from: 14680, rate: 0.044 },
      { from: 29370, rate: 0.053 },
      { from: 323290, rate: 0.0765 },
    ],
    marriedDoubles: true,
    longTerm: { exclude: 0.3 },
    note: "Wisconsin excludes 30% of long-term capital gains from state tax.",
  },
  SC: {
    name: "South Carolina",
    brackets: [
      { from: 0, rate: 0 },
      { from: 3560, rate: 0.03 },
      { from: 17830, rate: 0.062 },
    ],
    marriedDoubles: false,
    longTerm: { exclude: 0.44 },
    note: "South Carolina excludes 44% of long-term capital gains.",
  },
  AR: {
    name: "Arkansas",
    brackets: [
      { from: 0, rate: 0.02 },
      { from: 8800, rate: 0.03 },
      { from: 25000, rate: 0.039 },
    ],
    marriedDoubles: false,
    longTerm: { exclude: 0.5 },
    note: "Arkansas excludes 50% of long-term capital gains.",
  },
  ND: {
    name: "North Dakota",
    brackets: [
      { from: 0, rate: 0 },
      { from: 48475, rate: 0.0195 },
      { from: 244825, rate: 0.025 },
    ],
    marriedDoubles: true,
    longTerm: { exclude: 0.4 },
    note: "North Dakota excludes 40% of long-term capital gains.",
  },
  NM: {
    name: "New Mexico",
    brackets: [
      { from: 0, rate: 0.017 },
      { from: 5500, rate: 0.032 },
      { from: 16500, rate: 0.047 },
      { from: 33500, rate: 0.049 },
      { from: 210000, rate: 0.059 },
    ],
    marriedDoubles: true,
    longTerm: { exclude: 0.4 },
    note: "New Mexico deducts 40% of long-term gains (or $1,000, whichever is greater).",
  },
  MT: {
    name: "Montana",
    brackets: [
      { from: 0, rate: 0.047 },
      { from: 21100, rate: 0.059 },
    ],
    marriedDoubles: true,
    longTerm: { flat: 0.041 },
    note: "Montana taxes long-term gains on a separate, lower schedule.",
  },
  VT: {
    name: "Vermont",
    brackets: [
      { from: 0, rate: 0.0335 },
      { from: 47900, rate: 0.066 },
      { from: 116000, rate: 0.076 },
      { from: 242000, rate: 0.0875 },
    ],
    marriedDoubles: true,
    longTerm: { exclude: 0.4 },
    note: "Vermont excludes 40% of gains on assets held more than three years, within limits.",
  },
  // ---- remaining graduated states, encoded to their main bands ----
  AL: {
    name: "Alabama",
    brackets: [
      { from: 0, rate: 0.02 },
      { from: 500, rate: 0.04 },
      { from: 3000, rate: 0.05 },
    ],
    marriedDoubles: true,
  },
  DE: {
    name: "Delaware",
    brackets: [
      { from: 0, rate: 0 },
      { from: 2000, rate: 0.022 },
      { from: 5000, rate: 0.039 },
      { from: 10000, rate: 0.048 },
      { from: 20000, rate: 0.052 },
      { from: 25000, rate: 0.0555 },
      { from: 60000, rate: 0.066 },
    ],
    marriedDoubles: false,
  },
  IA: {
    name: "Iowa",
    brackets: [{ from: 0, rate: 0.038 }],
    marriedDoubles: false,
  },
  KS: {
    name: "Kansas",
    brackets: [
      { from: 0, rate: 0.052 },
      { from: 23000, rate: 0.0558 },
    ],
    marriedDoubles: true,
  },
  LA: {
    name: "Louisiana",
    brackets: [{ from: 0, rate: 0.03 }],
    marriedDoubles: false,
  },
  ME: {
    name: "Maine",
    brackets: [
      { from: 0, rate: 0.058 },
      { from: 26800, rate: 0.0675 },
      { from: 63450, rate: 0.0715 },
    ],
    marriedDoubles: true,
  },
  MO: {
    name: "Missouri",
    brackets: [
      { from: 0, rate: 0.02 },
      { from: 8911, rate: 0.047 },
    ],
    marriedDoubles: false,
  },
  NE: {
    name: "Nebraska",
    brackets: [
      { from: 0, rate: 0.0246 },
      { from: 3990, rate: 0.0351 },
      { from: 23910, rate: 0.0501 },
      { from: 38570, rate: 0.052 },
    ],
    marriedDoubles: true,
  },
  OK: {
    name: "Oklahoma",
    brackets: [
      { from: 0, rate: 0.0025 },
      { from: 1000, rate: 0.0175 },
      { from: 2500, rate: 0.0275 },
      { from: 3750, rate: 0.0375 },
      { from: 4900, rate: 0.0475 },
    ],
    marriedDoubles: true,
  },
  RI: {
    name: "Rhode Island",
    brackets: [
      { from: 0, rate: 0.0375 },
      { from: 79900, rate: 0.0475 },
      { from: 181650, rate: 0.0599 },
    ],
    marriedDoubles: false,
  },
  WV: {
    name: "West Virginia",
    brackets: [
      { from: 0, rate: 0.0222 },
      { from: 10000, rate: 0.0296 },
      { from: 25000, rate: 0.0333 },
      { from: 40000, rate: 0.0444 },
      { from: 60000, rate: 0.0482 },
    ],
    marriedDoubles: false,
  },
};

/** Sorted for the dropdown. */
export const STATE_CODES = Object.keys(STATE_TAX).sort((a, b) =>
  STATE_TAX[a].name < STATE_TAX[b].name ? -1 : 1,
);

/**
 * Combined marginal rates on the next dollar of gain.
 *
 * State income tax is deductible against federal only for filers who itemize
 * and are under the SALT cap, which the great majority of filers are not, so
 * the parts are added rather than compounded. That is the standard
 * back-of-envelope treatment and errs slightly high for big itemizers.
 */
export function computeRates(status, taxableIncome, stateCode) {
  const income = Math.max(0, taxableIncome || 0);
  const federalShort = marginalRate(FEDERAL_ORDINARY[status], income);
  const federalLong = marginalRate(FEDERAL_LONG_TERM[status], income);
  const niit = income > NIIT_THRESHOLD[status] ? NIIT_RATE : 0;
  const st = STATE_TAX[stateCode];
  let stateShort = 0;
  let stateLong = 0;
  if (st) {
    const scale = st.marriedDoubles && status === "married" ? 2 : 1;
    const scaled = st.brackets.map((b) => ({
      from: b.from * scale,
      rate: b.rate,
    }));
    stateShort = marginalRate(scaled, income);
    stateLong = stateShort;
    if (st.longTerm?.flat !== undefined) {
      stateLong = st.longTerm.flat;
      // Washington's excise tax is on long-term gains only; its ordinary rate
      // is zero, so short-term stays untaxed by the state.
    } else if (st.longTerm?.exclude !== undefined) {
      stateLong = stateShort * (1 - st.longTerm.exclude);
    }
    // Massachusetts taxes short-term gains on their own 8.5% schedule rather
    // than the 5% ordinary rate. The 4% millionaire surtax still stacks on top,
    // so it is re-added here — the bracket table already carries it for the
    // long-term side.
    if (stateCode === "MA") stateShort = 0.085 + (income >= 1000000 ? 0.04 : 0);
  }
  return {
    federalShort,
    federalLong,
    niit,
    stateShort,
    stateLong,
    shortTotal: federalShort + niit + stateShort,
    longTotal: federalLong + niit + stateLong,
    stateNote: st?.note,
    stateName: st?.name ?? "—",
  };
}
