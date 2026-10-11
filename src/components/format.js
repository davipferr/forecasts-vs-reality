// Formatting for rates (%) and the exchange rate (R$/US$).

const fixed = (x, digits) => x.toLocaleString("en", {minimumFractionDigits: digits, maximumFractionDigits: digits});

/** "4.50%" or "R$ 5.45"; `short` drops trailing zeros (axis ticks). */
export function value(x, unit, short = false) {
  if (x == null || Number.isNaN(x)) return "–";
  const s = short ? x.toLocaleString("en", {maximumFractionDigits: 2}) : fixed(x, 2);
  return unit === "%" ? `${s}%` : `R$ ${s}`;
}

/** A difference: "−1.50 pp" for rates, "+R$ 0.40" for FX. `signed = false` gives the magnitude. */
export function diff(d, unit, signed = true) {
  if (d == null || Number.isNaN(d)) return "–";
  const abs = fixed(Math.abs(d), 2);
  const sign = !signed ? "" : d > 0.0049 ? "+" : d < -0.0049 ? "−" : "";
  return unit === "%" ? `${sign}${abs} pp` : `${sign}R$ ${abs}`;
}

/** Unit for differences, for axis labels. */
export const diffUnit = (unit) => (unit === "%" ? "pp" : "R$");

/** "in December", "1 year ahead", "2 years 3 months ahead", "1 month after the year ended". */
export function horizon(h) {
  if (h === 0) return "in December of that year";
  if (h < 0) return `${-h} month${h === -1 ? "" : "s"} after the year ended`;
  const y = Math.floor(h / 12);
  const m = h % 12;
  const parts = [];
  if (y) parts.push(`${y} year${y > 1 ? "s" : ""}`);
  if (m) parts.push(`${m} month${m > 1 ? "s" : ""}`);
  return `${parts.join(" ")} ahead`;
}

export const monthYear = (date) => date.toLocaleDateString("en", {month: "short", year: "numeric", timeZone: "UTC"});
export const day = (date) => date.toLocaleDateString("en", {dateStyle: "medium", timeZone: "UTC"});

/** "Last published 12-month IPCA" -> "last published 12-month IPCA" (keeps acronyms). */
export const lowerFirst = (s) => s.charAt(0).toLowerCase() + s.slice(1);

/**
 * Arrow table -> array of plain objects (Plot/D3 want plain objects).
 * Arrow hands Parquet DATE columns over as epoch milliseconds; turn them into Dates.
 */
export function rows(table) {
  const dates = table.schema.fields.filter((f) => String(f.type).startsWith("Date")).map((f) => f.name);
  return Array.from(table, (r) => {
    const o = r.toJSON();
    for (const k of dates) if (o[k] != null) o[k] = new Date(o[k]);
    return o;
  });
}
