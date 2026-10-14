---
title: "United States: forecast map"
---

# Forecast map

Every SPF median as one cell. Across: the **target year**. Up the side: **how long before the end of that year** the survey was taken. Four surveys a year (February, May, August, November) give rows three months apart; forecasts more than two years out only start in 2005 (CPI) and 2009 (the rest).

```js
import {diff, horizon, monthYear, rows, value} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {errorLimit, palette} from "../components/palette.js";
import {aheadVsActual, forecastGrid} from "../components/forecast-charts.js";

const meta = await FileAttachment("../data/us/indicators.json").json();
const monthly = rows(await FileAttachment("../data/us/monthly.parquet").parquet());
const pal = palette(dark);
```

```js
const id = view(indicatorPicker(meta, {key: "ifr-us-indicator"}));
```

```js
const colour = view(Inputs.radio(["Forecast error", "Forecast value"], {label: "Colour", value: "Forecast error"}));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const u = ind.unit;
// Years before 1990 have no Treasury outcome for the T-bill; keep the map to scored years plus pending ones.
const cells = monthly.filter((d) => d.indicator === id && (d.actual != null || d.target >= new Date().getUTCFullYear() - 1));
const years = d3.sort(new Set(cells.map((d) => d.target)));
const limit = errorLimit(cells.map((d) => d.err));

function tipText(d) {
  return [
    `${ind.name} ${d.target}`,
    `Survey of ${monthYear(d.date)}, ${horizon(d.h)}: ${value(d.median, u)}`,
    d.actual == null ? "Outcome not known yet" : `Actual: ${value(d.actual, u)}`,
    d.actual == null ? null : `Miss: ${diff(d.err, u)} (${d.err < 0 ? "too low" : "too high"})`,
    d.naive == null ? null : `"No change": ${value(d.naive, u)}`
  ].filter(Boolean).join("\n");
}
```

<div class="card">
  <h2>${ind.name}: every forecast, ${years[0]}–${years.at(-1)}</h2>
  <h3>${colour === "Forecast error" ? `Colour saturates at ±${diff(limit, u, false)} (90th percentile of the misses). Outlined cells: the outcome isn't known yet.` : "Colour = the forecast itself; the outcome doesn't matter here."}</h3>
  ${resize((width) => forecastGrid(cells, {
    width,
    pal,
    dark,
    unit: u,
    colour: colour === "Forecast error" ? "error" : "value",
    step: 3,
    rowHeight: 18,
    minHeight: 260,
    limit,
    tip: tipText,
    yTicks: (h) => (h % 12 === 1 ? (h === 1 ? "Nov" : `Nov −${(h - 1) / 12}`) : "")
  }))}
</div>

## A year ahead vs. what happened

```js
const ahead = cells.filter((d) => d.h === meta.h && d.actual != null);
```

<div class="card">
  <h2>The November forecast for the next year → the outcome</h2>
  <h3>Hollow dot: the median forecast in November of the year before. Filled dot: what happened. The line is the miss.</h3>
  ${resize((width) => aheadVsActual(ahead, {
    width,
    pal,
    unit: u,
    limit,
    label: `${ind.name} (${u})`,
    tip: (d) => `${d.target}\nForecast in Nov ${d.target - 1}: ${value(d.median, u)}\nActual: ${value(d.actual, u)}\nMiss: ${diff(d.err, u)}\n"No change" missed by: ${diff(d.naive_err, u)}`
  }))}
</div>

<p class="muted small">Scored against: ${ind.actualLabel.charAt(0).toLowerCase() + ind.actualLabel.slice(1)}. ${ind.notes.join(" ")}</p>
