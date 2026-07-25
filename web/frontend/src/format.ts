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
