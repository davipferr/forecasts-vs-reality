import * as Plot from "npm:@observablehq/plot";
import * as d3 from "npm:d3";
import {diff, diffUnit} from "./format.js";
import {errorLimit, errorScale} from "./palette.js";

// Charts shared by every forecast source (Focus, IMF, SPF). Each takes scored
// cells: {target, h, actual, err, <value>}, with h = months from the forecast
// to December of the target year.

/** Year-axis ticks: every fifth year, so 30-odd columns don't collide. */
const everyFifth = (y) => (y % 5 === 0 ? String(y) : "");

/**
 * The forecast map: one cell per target year (across) × horizon (up the side),
 * coloured by the error, or by the forecast itself with `colour: "value"`.
 * Cells whose outcome isn't known yet are drawn as outlines.
 *
 * `step` is the spacing of the horizons (1 for monthly surveys, 6 for the
 * IMF's April/October editions, 3 for a quarterly survey); `tip(d)` returns the
 * tooltip text; `onClick(d)` makes the cells clickable.
 */
export function forecastGrid(cells, {width, pal, dark, unit, value = "median", colour = "error", step = 1, rowHeight = 8.5, minHeight = 420, limit, tip, onClick, legendLabel, yTicks, yLabel = "Months before the end of the target year", marginLeft = 56}) {
  const byError = colour === "error";
  const years = d3.sort(new Set(cells.map((d) => d.target)));
  const [hMin, hMax] = d3.extent(cells, (d) => d.h);
  const hs = d3.range(hMax, hMin - 1, -step);
  limit ??= errorLimit(cells.map((d) => d.err));
  const known = cells.filter((d) => d.actual != null);
  const pending = cells.filter((d) => d.actual == null);
  const chart = Plot.plot({
    width,
    height: Math.max(minHeight, hs.length * rowHeight),
    marginLeft,
    padding: 0,
    x: {type: "band", domain: years, label: "Target year →", tickFormat: everyFifth, tickSize: 0},
    y: {
      type: "band",
      domain: hs,
      label: yLabel,
      tickFormat: yTicks ?? ((h) => (h === 0 ? "Dec" : h % 12 === 0 ? `${h / 12} yr` : "")),
      tickSize: 0
    },
    color: byError
      ? errorScale(pal, limit, legendLabel ?? `Forecast − actual (${diffUnit(unit)}): red = too low, blue = too high`)
      : {type: "linear", scheme: dark ? "magma" : "viridis", legend: true, label: `Forecast (${unit})`},
    marks: [
      byError
        ? [
            Plot.cell(known, {x: "target", y: "h", fill: "err", inset: 0.25}),
            Plot.cell(pending, {x: "target", y: "h", fill: "none", stroke: pal.muted, strokeWidth: 0.75, inset: 1})
          ]
        : Plot.cell(cells, {x: "target", y: "h", fill: value, inset: 0.25}),
      hs.includes(0) ? Plot.ruleY([0], {stroke: "var(--theme-foreground-faint)", dy: 4}) : null,
      Plot.tip(cells, Plot.pointer({x: "target", y: "h", title: tip}))
    ]
  });
  if (onClick) {
    chart.style.cursor = "pointer";
    chart.addEventListener("click", () => chart.value && onClick(chart.value));
  }
  return chart;
}

/**
 * Forecast at one horizon vs. what happened, per target year: a hollow dot
 * for the forecast, a filled one for the outcome, joined by the miss.
 */
export function aheadVsActual(cells, {width, pal, unit, value = "median", years, limit, tip, label, zero = true, marginLeft = 56, height = 300}) {
  years ??= d3.sort(new Set(cells.map((d) => d.target)));
  limit ??= errorLimit(cells.map((d) => d.err));
  return Plot.plot({
    width,
    height,
    marginLeft,
    x: {type: "band", domain: years, label: null, tickFormat: everyFifth, tickSize: 0},
    y: {grid: true, label, zero},
    color: {...errorScale(pal, limit, null), legend: false},
    marks: [
      Plot.link(cells, {x: "target", y1: value, y2: "actual", stroke: "err", strokeWidth: 3}),
      Plot.dot(cells, {x: "target", y: value, stroke: "var(--theme-foreground-muted)", fill: "var(--theme-background)", r: 3.5}),
      Plot.dot(cells, {x: "target", y: "actual", fill: pal.actual, r: 4}),
      Plot.tip(cells, Plot.pointerX({x: "target", y: "actual", title: tip}))
    ]
  });
}

/**
 * Average miss by horizon, one line per series: `series` = [{name, key, color}],
 * read from `stats` rows ({h, [key]}). The first series is drawn thicker.
 */
export function horizonLines(stats, series, {width, unit, x, height = 320, yLabel, describe, dots = false}) {
  const data = series.flatMap(({name, key}) => stats.filter((d) => d[key] != null).map((d) => ({h: d.h, series: name, value: d[key]})));
  describe ??= (h) => (h === 0 ? "In December" : `${h} months ahead`);
  return Plot.plot({
    width,
    height,
    marginLeft: 48,
    x,
    y: {grid: true, zero: true, label: yLabel ?? `Average miss (${diffUnit(unit)})`},
    color: {domain: series.map((s) => s.name), range: series.map((s) => s.color), legend: true},
    marks: [
      Plot.lineY(data, {x: "h", y: "value", stroke: "series", strokeWidth: (d) => (d.series === series[0].name ? 2.4 : 1.5)}),
      dots ? Plot.dot(data, {x: "h", y: "value", fill: "series", r: 2.5}) : null,
      Plot.ruleX(data, Plot.pointerX({x: "h", stroke: "var(--theme-foreground-faint)"})),
      Plot.dot(data, Plot.pointerX({x: "h", y: "value", fill: "series", r: 3})),
      Plot.tip(data, Plot.pointerX({x: "h", y: "value", title: (d) => `${d.series}\n${describe(d.h)}: ${diff(d.value, unit, false)}`}))
    ]
  });
}

/** Bias (average error) by horizon as bars coloured by sign. */
export function biasBars(stats, {width, pal, unit, x, key = "bias", height = 320, yLabel, describe, nLabel = "years"}) {
  describe ??= (h) => (h === 0 ? "In December" : `${h} months ahead`);
  return Plot.plot({
    width,
    height,
    marginLeft: 48,
    x: {...x, type: "band", padding: 0.15},
    y: {grid: true, label: yLabel ?? `Average error (${diffUnit(unit)})`},
    color: {...errorScale(pal, errorLimit(stats.map((d) => d[key]), 1), null), legend: false},
    marks: [
      Plot.barY(stats, {x: "h", y: key, fill: key}),
      Plot.ruleY([0]),
      Plot.tip(stats, Plot.pointerX({x: "h", y: key, title: (d) => `${describe(d.h)}\nAverage error: ${diff(d[key], unit)}\nOver ${d.n} ${nLabel}`}))
    ]
  });
}
