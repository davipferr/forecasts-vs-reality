---
title: Forecast map
---

# Forecast map

Every monthly consensus as one cell. Across: the **target year**. Up the side: **how long before the end of that year** the forecast was made, from four or five years ahead at the top down to December. Read a column from top to bottom to watch the market converge on the outcome; read a row across to compare years at the same horizon.

```js
import {diff, diffUnit, horizon, monthYear, rows, value} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {errorLimit, palette} from "../components/palette.js";
import {aheadVsActual, forecastGrid} from "../components/forecast-charts.js";

const meta = await FileAttachment("../data/indicators.json").json();
const monthly = rows(await FileAttachment("../data/monthly.parquet").parquet());
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

function forecastMap(width) {
  return forecastGrid(cells, {
    width,
    pal,
    dark,
    unit: u,
    colour: colour === "Forecast error" ? "error" : "value",
    limit,
    tip: tipText,
    onClick: (d) => (location.href = `./year?i=${id}&y=${d.target}`)
  });
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
  ${resize((width) => aheadVsActual(yearAhead, {
    width,
    pal,
    unit: u,
    years,
    limit,
    label: `${ind.name} (${u})`,
    zero: id !== "fx",
    tip: (d) => `${d.target}\nForecast in Dec ${d.target - 1}: ${value(d.median, u)}\nActual: ${value(d.actual, u)}\nMiss: ${diff(d.err, u)}`
  }))}
</div>
