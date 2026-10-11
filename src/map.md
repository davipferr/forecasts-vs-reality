---
title: Forecast map
---

# Forecast map

Every monthly consensus as one cell. Across: the **target year**. Up the side: **how long before the end of that year** the forecast was made, from four or five years ahead at the top down to December. Read a column from top to bottom to watch the market converge on the outcome; read a row across to compare years at the same horizon.

```js
import {diff, diffUnit, horizon, monthYear, rows, value} from "./components/format.js";
import {indicatorPicker} from "./components/indicator.js";
import {errorLimit, errorScale, palette} from "./components/palette.js";

const meta = await FileAttachment("data/indicators.json").json();
const monthly = rows(await FileAttachment("data/monthly.parquet").parquet());
const pal = palette(dark);
```

```js
const id = view(indicatorPicker(meta));
```

```js
const colour = view(Inputs.radio(["Forecast error", "Forecast value"], {label: "Colour", value: "Forecast error"}));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const cells = monthly.filter((d) => d.indicator === id);
const years = d3.sort(new Set(cells.map((d) => d.target)));
const [hMin, hMax] = d3.extent(cells, (d) => d.h);
const limit = errorLimit(cells.map((d) => d.err));
const u = ind.unit;
```

```js
function tipText(d) {
  return [
    `${ind.name} ${d.target}`,
    `Forecast made in ${monthYear(d.date)}, ${horizon(d.h)}: ${value(d.median, u)}`,
    d.actual == null ? "Outcome not known yet" : `Actual: ${value(d.actual, u)}`,
    d.actual == null ? null : `Miss: ${diff(d.err, u)} (${d.err < 0 ? "too low" : "too high"})`,
    "Click to open this year"
  ].filter(Boolean).join("\n");
}

const MARGIN_LEFT = 56;

function forecastMap(width) {
  const byError = colour === "Forecast error";
  const known = cells.filter((d) => d.actual != null);
  const pending = cells.filter((d) => d.actual == null);
  const chart = Plot.plot({
    width,
    height: Math.max(420, (hMax - hMin + 1) * 8.5),
    marginLeft: MARGIN_LEFT,
    padding: 0,
    x: {type: "band", domain: years, label: "Target year →", tickFormat: (y) => (y % 5 === 0 ? String(y) : ""), tickSize: 0},
    y: {
      type: "band",
      domain: d3.range(hMax, hMin - 1, -1),
      label: "Months before the end of the target year",
      tickFormat: (h) => (h === 0 ? "Dec" : h % 12 === 0 ? `${h / 12} yr` : ""),
      tickSize: 0
    },
    color: byError
      ? errorScale(pal, limit, `Forecast − actual (${diffUnit(u)}): red = too low, blue = too high`)
      : {type: "linear", scheme: dark ? "magma" : "viridis", legend: true, label: `Forecast (${u})`},
    marks: [
      byError
        ? [
            Plot.cell(known, {x: "target", y: "h", fill: "err", inset: 0.25}),
            Plot.cell(pending, {x: "target", y: "h", fill: "none", stroke: pal.muted, strokeWidth: 0.75, inset: 1})
          ]
        : Plot.cell(cells, {x: "target", y: "h", fill: "median", inset: 0.25}),
      Plot.ruleY([0], {stroke: "var(--theme-foreground-faint)", dy: 4}),
      Plot.tip(cells, Plot.pointer({x: "target", y: "h", title: tipText}))
    ]
  });
  chart.style.cursor = "pointer";
  chart.addEventListener("click", () => {
    if (chart.value) location.href = `./year?i=${id}&y=${chart.value.target}`;
  });
  return chart;
}
```

<div class="card">
  <h2>${ind.name}: every forecast, ${years[0]}–${years.at(-1)}</h2>
  <h3>${colour === "Forecast error" ? `Colour saturates at ±${diff(limit, u, false)} (90th percentile of the misses). Outlined cells: the outcome isn't known yet.` : "Colour = the consensus itself; the outcome doesn't matter here."}</h3>
  ${resize((width) => forecastMap(width))}
</div>

## A year ahead vs. what happened

```js
const yearAhead = cells.filter((d) => d.h === 12 && d.actual != null);
```

<div class="card">
  <h2>The consensus in December of the previous year → the outcome</h2>
  <h3>Hollow dot: what the market expected a year ahead. Filled dot: what happened. The line is the miss.</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 300,
    marginLeft: MARGIN_LEFT,
    x: {type: "band", domain: years, label: null, tickFormat: (y) => (y % 5 === 0 ? String(y) : ""), tickSize: 0},
    y: {grid: true, label: `${ind.name} (${u})`, zero: id !== "fx"},
    color: {...errorScale(pal, limit, null), legend: false},
    marks: [
      Plot.link(yearAhead, {x: "target", y1: "median", y2: "actual", stroke: "err", strokeWidth: 3}),
      Plot.dot(yearAhead, {x: "target", y: "median", stroke: "var(--theme-foreground-muted)", fill: "var(--theme-background)", r: 3.5}),
      Plot.dot(yearAhead, {x: "target", y: "actual", fill: pal.actual, r: 4}),
      Plot.tip(yearAhead, Plot.pointerX({x: "target", y: "actual", title: (d) => `${d.target}\nForecast in Dec ${d.target - 1}: ${value(d.median, u)}\nActual: ${value(d.actual, u)}\nMiss: ${diff(d.err, u)}`}))
    ]
  }))}
</div>
