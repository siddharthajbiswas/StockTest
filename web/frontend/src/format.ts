export const pct = (x: number | null | undefined, digits = 1) =>
  x == null || !Number.isFinite(x) ? "—" : `${(x * 100).toFixed(digits)}%`;

export const signedPct = (x: number | null | undefined, digits = 1) =>
  x == null || !Number.isFinite(x) ? "—" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(digits)}%`;

export const money = (x: number | null | undefined, digits = 0) =>
  x == null || !Number.isFinite(x)
    ? "—"
    : x.toLocaleString(undefined, {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: digits,
      });

export const num = (x: number | null | undefined, digits = 2) =>
  x == null || !Number.isFinite(x) ? "—" : x.toFixed(digits);

export const prettyId = (id: string | null): string =>
  !id ? "—" : id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * "2019-03-14" -> "Mar 14, 2019", for chart tooltips.
 *
 * Split rather than `new Date()`: parsing a bare YYYY-MM-DD gives UTC midnight,
 * which renders as the *previous* day for anyone west of Greenwich. These are
 * calendar labels, not instants, so they must not move with the viewer.
 */
export function prettyDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  const mi = Number(m) - 1;
  if (!y || !MONTHS[mi] || !d) return iso;
  return `${MONTHS[mi]} ${Number(d)}, ${y}`;
}
