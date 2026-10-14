// Helpers for the IMF pages. WEO editions come out in April and October, so a
// horizon h (months to December of the target year) is always 2, 8, 14, 20...

/** The edition a horizon belongs to: {month: "April" | "October", before: years before the target year}. */
export function edition(h) {
  return {month: h % 12 === 2 ? "October" : "April", before: Math.floor(h / 12)};
}

/** "October of the year before", "April of the same year", "October, 3 years before". */
export function editionLabel(h) {
  const {month, before} = edition(h);
  return `${month} ${before === 0 ? "of the same year" : before === 1 ? "of the year before" : `${before} years before`}`;
}

/** Axis label: "Oct", "Apr", "Oct −1", "Apr −2"... */
export function editionTick(h) {
  const {month, before} = edition(h);
  return `${month.slice(0, 3)}${before ? ` −${before}` : ""}`;
}

/** The horizons offered in the pickers. */
export const HORIZONS = [2, 8, 14, 20, 26, 38, 50];

/** Where an error counts as optimistic: +1 if a forecast that is too high is optimistic (growth), −1 if too low (inflation). */
export function optimism(ind, err) {
  return ind.optimistic == null ? null : Math.sign(err) === ind.optimistic;
}
