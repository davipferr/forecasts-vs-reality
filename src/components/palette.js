import * as d3 from "npm:d3";

// Same validated palette as public-data-explorer (light + dark steps of the same hues).
const CATEGORICAL = {
  light: ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"],
  dark: ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
};

export function palette(dark = false) {
  const cat = dark ? CATEGORICAL.dark : CATEGORICAL.light;
  return {
    categorical: cat,
    // Series roles, fixed across every chart.
    consensus: dark ? "#e8e7e3" : "#2b2b29",
    naive: dark ? "#8f8e88" : "#8a8981",
    goal: cat[2],
    top5: cat[6],
    actual: cat[3],
    muted: dark ? "#5f5e5a" : "#c3c2b7",
    // Error = forecast − actual: negative (forecast too LOW) is red, positive (too HIGH) is blue.
    diverging: {
      neg: dark ? "#e66767" : "#e34948",
      mid: dark ? "#383835" : "#f0efec",
      pos: dark ? "#3987e5" : "#2a78d6"
    },
    noData: dark ? "#2b2b29" : "#e8e7e3"
  };
}

/** Plot colour scale for errors, symmetric around zero and saturating at ±`limit`. */
export function errorScale(pal, limit, label) {
  return {
    type: "diverging",
    domain: [-limit, limit],
    range: [pal.diverging.neg, pal.diverging.mid, pal.diverging.pos],
    clamp: true,
    legend: true,
    label
  };
}

/** Saturation point for the error colours: a high percentile of |error|, so one crisis year doesn't wash out the rest. */
export function errorLimit(errors, q = 0.9) {
  const abs = errors.filter((e) => e != null).map(Math.abs);
  return abs.length ? Math.max(d3.quantile(abs, q), 1e-6) : 1;
}
