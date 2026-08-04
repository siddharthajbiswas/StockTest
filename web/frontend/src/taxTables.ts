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

export type FilingStatus = "single" | "married";

export const TAX_YEAR = 2025;

interface Bracket {
  /** Taxable income at which this rate starts. */
  from: number;
  rate: number;
}

// ----------------------------- federal --------------------------------------

/** Ordinary income — what short-term gains are taxed at. */
const FEDERAL_ORDINARY: Record<FilingStatus, Bracket[]> = {
  single: [
    { from: 0, rate: 0.10 },
    { from: 11_925, rate: 0.12 },
    { from: 48_475, rate: 0.22 },
    { from: 103_350, rate: 0.24 },
    { from: 197_300, rate: 0.32 },
    { from: 250_525, rate: 0.35 },
    { from: 626_350, rate: 0.37 },
  ],
  married: [
    { from: 0, rate: 0.10 },
    { from: 23_850, rate: 0.12 },
    { from: 96_950, rate: 0.22 },
    { from: 206_700, rate: 0.24 },
    { from: 394_600, rate: 0.32 },
    { from: 501_050, rate: 0.35 },
    { from: 751_600, rate: 0.37 },
  ],
};

/** Long-term capital gains — the preferential 0/15/20 schedule. */
const FEDERAL_LONG_TERM: Record<FilingStatus, Bracket[]> = {
  single: [
    { from: 0, rate: 0.0 },
    { from: 48_350, rate: 0.15 },
    { from: 533_400, rate: 0.20 },
  ],
  married: [
    { from: 0, rate: 0.0 },
    { from: 96_700, rate: 0.15 },
    { from: 600_050, rate: 0.20 },
  ],
};

/** Net Investment Income Tax: 3.8% above these thresholds. Not indexed to
 *  inflation, which is why they have been the same since 2013. */
const NIIT_RATE = 0.038;
const NIIT_THRESHOLD: Record<FilingStatus, number> = {
  single: 200_000,
  married: 250_000,
};

function marginalRate(brackets: Bracket[], income: number): number {
  let rate = brackets[0].rate;
  for (const b of brackets) if (income >= b.from) rate = b.rate;
  return rate;
}

// ------------------------------ states --------------------------------------

export interface StateTax {
  name: string;
  /**
   * Ordinary-income brackets for a single filer. A single entry means a flat
   * tax (or no tax at all, at rate 0).
   */
  brackets: Bracket[];
  /**
   * Whether married-filing-jointly thresholds are double the single ones. True
   * for most states with graduated rates; false where the state uses one
   * schedule regardless of status.
   */
  marriedDoubles: boolean;
  /**
   * Long-term gains treatment, when the state does something other than tax
   * them as ordinary income:
   *   exclude — fraction of the gain excluded from state tax
   *   flat    — a separate flat rate that replaces the ordinary one
   */
  longTerm?: { exclude?: number; flat?: number };
  /** Shown to the user whenever it exists. Use for anything surprising. */
  note?: string;
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
export const STATE_TAX: Record<string, StateTax> = {
  // ---- no individual income tax on wages or gains ----
  AK: { name: "Alaska", brackets: [{ from: 0, rate: 0 }], marriedDoubles: false },
  FL: { name: "Florida", brackets: [{ from: 0, rate: 0 }], marriedDoubles: false },
  NV: { name: "Nevada", brackets: [{ from: 0, rate: 0 }], marriedDoubles: false },
  SD: { name: "South Dakota", brackets: [{ from: 0, rate: 0 }], marriedDoubles: false },
  TX: { name: "Texas", brackets: [{ from: 0, rate: 0 }], marriedDoubles: false },
  WY: { name: "Wyoming", brackets: [{ from: 0, rate: 0 }], marriedDoubles: false },
  TN: { name: "Tennessee", brackets: [{ from: 0, rate: 0 }], marriedDoubles: false },
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
  AZ: { name: "Arizona", brackets: [{ from: 0, rate: 0.025 }], marriedDoubles: false },
  CO: { name: "Colorado", brackets: [{ from: 0, rate: 0.044 }], marriedDoubles: false },
  GA: { name: "Georgia", brackets: [{ from: 0, rate: 0.0519 }], marriedDoubles: false },
  ID: { name: "Idaho", brackets: [{ from: 0, rate: 0.05695 }], marriedDoubles: false },
  IL: { name: "Illinois", brackets: [{ from: 0, rate: 0.0495 }], marriedDoubles: false },
  IN: { name: "Indiana", brackets: [{ from: 0, rate: 0.03 }], marriedDoubles: false,
        note: "Counties levy an additional income tax, typically 1–3%, not included here." },
  KY: { name: "Kentucky", brackets: [{ from: 0, rate: 0.04 }], marriedDoubles: false },
  MI: { name: "Michigan", brackets: [{ from: 0, rate: 0.0425 }], marriedDoubles: false },
  MS: { name: "Mississippi", brackets: [{ from: 0, rate: 0.044 }], marriedDoubles: false },
  NC: { name: "North Carolina", brackets: [{ from: 0, rate: 0.0425 }], marriedDoubles: false },
  PA: { name: "Pennsylvania", brackets: [{ from: 0, rate: 0.0307 }], marriedDoubles: false,
        note: "Local earned-income taxes do not apply to capital gains, so the state rate is the whole story." },
  UT: { name: "Utah", brackets: [{ from: 0, rate: 0.0455 }], marriedDoubles: false },
  MA: {
    name: "Massachusetts",
    brackets: [{ from: 0, rate: 0.05 }, { from: 1_000_000, rate: 0.09 }],
    marriedDoubles: false,
    note: "Short-term gains are taxed at 8.5%, not the 5% ordinary rate. The 4% millionaire surtax applies above $1M of income.",
  },

  // ---- graduated states ----
  CA: {
    name: "California",
    brackets: [
      { from: 0, rate: 0.01 }, { from: 10_756, rate: 0.02 }, { from: 25_499, rate: 0.04 },
      { from: 40_245, rate: 0.06 }, { from: 55_866, rate: 0.08 }, { from: 70_606, rate: 0.093 },
      { from: 360_659, rate: 0.103 }, { from: 432_787, rate: 0.113 },
      { from: 721_314, rate: 0.123 }, { from: 1_000_000, rate: 0.133 },
    ],
    marriedDoubles: true,
    note: "California taxes capital gains fully as ordinary income — there is no long-term discount.",
  },
  NY: {
    name: "New York",
    brackets: [
      { from: 0, rate: 0.04 }, { from: 13_900, rate: 0.045 }, { from: 21_400, rate: 0.0525 },
      { from: 80_650, rate: 0.055 }, { from: 215_400, rate: 0.06 },
      { from: 1_077_550, rate: 0.0685 }, { from: 5_000_000, rate: 0.103 },
      { from: 25_000_000, rate: 0.109 },
    ],
    marriedDoubles: true,
    note: "New York City residents owe an additional city income tax of roughly 3.1–3.9%, which is not included here.",
  },
  NJ: {
    name: "New Jersey",
    brackets: [
      { from: 0, rate: 0.014 }, { from: 20_000, rate: 0.0175 }, { from: 35_000, rate: 0.035 },
      { from: 40_000, rate: 0.05525 }, { from: 75_000, rate: 0.0637 },
      { from: 500_000, rate: 0.0897 }, { from: 1_000_000, rate: 0.1075 },
    ],
    marriedDoubles: false,
  },
  OR: {
    name: "Oregon",
    brackets: [
      { from: 0, rate: 0.0475 }, { from: 4_400, rate: 0.0675 },
      { from: 11_050, rate: 0.0875 }, { from: 125_000, rate: 0.099 },
    ],
    marriedDoubles: true,
    note: "Portland-area residents also pay local income taxes not included here.",
  },
  MN: {
    name: "Minnesota",
    brackets: [
      { from: 0, rate: 0.0535 }, { from: 32_570, rate: 0.068 },
      { from: 106_990, rate: 0.0785 }, { from: 198_630, rate: 0.0985 },
    ],
    marriedDoubles: true,
    note: "An extra 1% surtax applies to net investment income above $1M.",
  },
  HI: {
    name: "Hawaii",
    brackets: [
      { from: 0, rate: 0.014 }, { from: 9_600, rate: 0.055 }, { from: 24_000, rate: 0.0765 },
      { from: 48_000, rate: 0.0825 }, { from: 175_000, rate: 0.09 },
      { from: 250_000, rate: 0.10 }, { from: 325_000, rate: 0.11 },
    ],
    marriedDoubles: true,
    longTerm: { flat: 0.0725 },
    note: "Long-term gains are capped at an alternative 7.25% rate.",
  },
  DC: {
    name: "District of Columbia",
    brackets: [
      { from: 0, rate: 0.04 }, { from: 10_000, rate: 0.06 }, { from: 40_000, rate: 0.065 },
      { from: 60_000, rate: 0.085 }, { from: 250_000, rate: 0.0925 },
      { from: 500_000, rate: 0.0975 }, { from: 1_000_000, rate: 0.1075 },
    ],
    marriedDoubles: false,
  },
  MD: {
    name: "Maryland",
    brackets: [
      { from: 0, rate: 0.02 }, { from: 1_000, rate: 0.03 }, { from: 2_000, rate: 0.04 },
      { from: 3_000, rate: 0.0475 }, { from: 100_000, rate: 0.05 },
      { from: 125_000, rate: 0.0525 }, { from: 150_000, rate: 0.055 },
      { from: 250_000, rate: 0.0575 },
    ],
    marriedDoubles: false,
    note: "Counties add a local income tax of roughly 2.25–3.2% on top, not included here.",
  },
  VA: {
    name: "Virginia",
    brackets: [
      { from: 0, rate: 0.02 }, { from: 3_000, rate: 0.03 },
      { from: 5_000, rate: 0.05 }, { from: 17_000, rate: 0.0575 },
    ],
    marriedDoubles: false,
  },
  CT: {
    name: "Connecticut",
    brackets: [
      { from: 0, rate: 0.02 }, { from: 10_000, rate: 0.045 }, { from: 50_000, rate: 0.055 },
      { from: 100_000, rate: 0.06 }, { from: 200_000, rate: 0.065 },
      { from: 250_000, rate: 0.069 }, { from: 500_000, rate: 0.0699 },
    ],
    marriedDoubles: true,
  },
  OH: {
    name: "Ohio",
    brackets: [
      { from: 0, rate: 0 }, { from: 26_050, rate: 0.0275 }, { from: 100_000, rate: 0.035 },
    ],
    marriedDoubles: false,
    note: "Municipalities levy their own income taxes, but most exempt capital gains.",
  },
  WI: {
    name: "Wisconsin",
    brackets: [
      { from: 0, rate: 0.035 }, { from: 14_680, rate: 0.044 },
      { from: 29_370, rate: 0.053 }, { from: 323_290, rate: 0.0765 },
    ],
    marriedDoubles: true,
    longTerm: { exclude: 0.30 },
    note: "Wisconsin excludes 30% of long-term capital gains from state tax.",
  },
  SC: {
    name: "South Carolina",
    brackets: [{ from: 0, rate: 0 }, { from: 3_560, rate: 0.03 }, { from: 17_830, rate: 0.062 }],
    marriedDoubles: false,
    longTerm: { exclude: 0.44 },
    note: "South Carolina excludes 44% of long-term capital gains.",
  },
  AR: {
    name: "Arkansas",
    brackets: [{ from: 0, rate: 0.02 }, { from: 8_800, rate: 0.03 }, { from: 25_000, rate: 0.039 }],
    marriedDoubles: false,
    longTerm: { exclude: 0.50 },
    note: "Arkansas excludes 50% of long-term capital gains.",
  },
  ND: {
    name: "North Dakota",
    brackets: [{ from: 0, rate: 0 }, { from: 48_475, rate: 0.0195 }, { from: 244_825, rate: 0.025 }],
    marriedDoubles: true,
    longTerm: { exclude: 0.40 },
    note: "North Dakota excludes 40% of long-term capital gains.",
  },
  NM: {
    name: "New Mexico",
    brackets: [
      { from: 0, rate: 0.017 }, { from: 5_500, rate: 0.032 }, { from: 16_500, rate: 0.047 },
      { from: 33_500, rate: 0.049 }, { from: 210_000, rate: 0.059 },
    ],
    marriedDoubles: true,
    longTerm: { exclude: 0.40 },
    note: "New Mexico deducts 40% of long-term gains (or $1,000, whichever is greater).",
  },
  MT: {
    name: "Montana",
    brackets: [{ from: 0, rate: 0.047 }, { from: 21_100, rate: 0.059 }],
    marriedDoubles: true,
    longTerm: { flat: 0.041 },
    note: "Montana taxes long-term gains on a separate, lower schedule.",
  },
  VT: {
    name: "Vermont",
    brackets: [
      { from: 0, rate: 0.0335 }, { from: 47_900, rate: 0.066 },
      { from: 116_000, rate: 0.076 }, { from: 242_000, rate: 0.0875 },
    ],
    marriedDoubles: true,
    longTerm: { exclude: 0.40 },
    note: "Vermont excludes 40% of gains on assets held more than three years, within limits.",
  },

  // ---- remaining graduated states, encoded to their main bands ----
  AL: { name: "Alabama", brackets: [{ from: 0, rate: 0.02 }, { from: 500, rate: 0.04 }, { from: 3_000, rate: 0.05 }], marriedDoubles: true },
  DE: { name: "Delaware", brackets: [{ from: 0, rate: 0 }, { from: 2_000, rate: 0.022 }, { from: 5_000, rate: 0.039 }, { from: 10_000, rate: 0.048 }, { from: 20_000, rate: 0.052 }, { from: 25_000, rate: 0.0555 }, { from: 60_000, rate: 0.066 }], marriedDoubles: false },
  IA: { name: "Iowa", brackets: [{ from: 0, rate: 0.038 }], marriedDoubles: false },
  KS: { name: "Kansas", brackets: [{ from: 0, rate: 0.052 }, { from: 23_000, rate: 0.0558 }], marriedDoubles: true },
  LA: { name: "Louisiana", brackets: [{ from: 0, rate: 0.03 }], marriedDoubles: false },
  ME: { name: "Maine", brackets: [{ from: 0, rate: 0.058 }, { from: 26_800, rate: 0.0675 }, { from: 63_450, rate: 0.0715 }], marriedDoubles: true },
  MO: { name: "Missouri", brackets: [{ from: 0, rate: 0.02 }, { from: 8_911, rate: 0.047 }], marriedDoubles: false },
  NE: { name: "Nebraska", brackets: [{ from: 0, rate: 0.0246 }, { from: 3_990, rate: 0.0351 }, { from: 23_910, rate: 0.0501 }, { from: 38_570, rate: 0.052 }], marriedDoubles: true },
  OK: { name: "Oklahoma", brackets: [{ from: 0, rate: 0.0025 }, { from: 1_000, rate: 0.0175 }, { from: 2_500, rate: 0.0275 }, { from: 3_750, rate: 0.0375 }, { from: 4_900, rate: 0.0475 }], marriedDoubles: true },
  RI: { name: "Rhode Island", brackets: [{ from: 0, rate: 0.0375 }, { from: 79_900, rate: 0.0475 }, { from: 181_650, rate: 0.0599 }], marriedDoubles: false },
  WV: { name: "West Virginia", brackets: [{ from: 0, rate: 0.0222 }, { from: 10_000, rate: 0.0296 }, { from: 25_000, rate: 0.0333 }, { from: 40_000, rate: 0.0444 }, { from: 60_000, rate: 0.0482 }], marriedDoubles: false },
};

/** Sorted for the dropdown. */
export const STATE_CODES = Object.keys(STATE_TAX).sort((a, b) =>
  STATE_TAX[a].name < STATE_TAX[b].name ? -1 : 1,
);

// ---------------------------- the calculation -------------------------------

export interface RateBreakdown {
  federalShort: number;
  federalLong: number;
  niit: number;
  stateShort: number;
  stateLong: number;
  /** Sum of the parts — what actually goes to the engine. */
  shortTotal: number;
  longTotal: number;
  stateNote?: string;
  stateName: string;
}

/**
 * Combined marginal rates on the next dollar of gain.
 *
 * State income tax is deductible against federal only for filers who itemize
 * and are under the SALT cap, which the great majority of filers are not, so
 * the parts are added rather than compounded. That is the standard
 * back-of-envelope treatment and errs slightly high for big itemizers.
 */
export function computeRates(
  status: FilingStatus,
  taxableIncome: number,
  stateCode: string,
): RateBreakdown {
  const income = Math.max(0, taxableIncome || 0);

  const federalShort = marginalRate(FEDERAL_ORDINARY[status], income);
  const federalLong = marginalRate(FEDERAL_LONG_TERM[status], income);
  const niit = income > NIIT_THRESHOLD[status] ? NIIT_RATE : 0;

  const st = STATE_TAX[stateCode];
  let stateShort = 0;
  let stateLong = 0;
  if (st) {
    const scale = st.marriedDoubles && status === "married" ? 2 : 1;
    const scaled = st.brackets.map((b) => ({ from: b.from * scale, rate: b.rate }));
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
    if (stateCode === "MA") stateShort = 0.085 + (income >= 1_000_000 ? 0.04 : 0);
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
