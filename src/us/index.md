---
title: "United States: overview"
toc: false
---

# America's professional forecasters

<p class="lede">Every quarter since 1968, the Philadelphia Fed's <em>Survey of Professional Forecasters</em> asks some 30–40 economists at banks, consultancies and universities where the US economy is heading. Their median forecasts for inflation, growth, unemployment and interest rates, scored against what happened, and against the simplest forecast of all: "no change".</p>

```js
import {diff, rows, value} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {insights} from "../components/insights.js";
import {palette} from "../components/palette.js";
import {miniColumns} from "../components/charts.js";

const meta = await FileAttachment("../data/us/indicators.json").json();
const stats = rows(await FileAttachment("../data/us/horizon-stats.parquet").parquet());
const pal = palette(dark);
```

<div class="grid grid-cols-3">${meta.indicators.map((ind) => html`<a class="card card-link" href="./map?i=${ind.id}">
    <h2>${ind.name}</h2>
    <span class="big">${diff(ind.headline.mae, ind.unit, false)}</span>
    <p class="muted">average miss one year ahead (${ind.headline.first}–${ind.headline.last}). ${ind.headline.beatNaive != null ? `Closer than "no change" in ${ind.headline.beatNaive} of ${ind.headline.years} years.` : ""}</p>
    ${resize((width) => miniColumns(ind.yearAhead, {
      width,
      x: "year",
      y: "err",
      fill: (d) => (d.err < 0 ? pal.diverging.neg : pal.diverging.pos),
      title: (d) => `${d.year}: forecast ${d.err < 0 ? "too low" : "too high"} by ${diff(d.err, ind.unit, false)}`
    }))}
  </a>`)}
</div>

<p class="muted small">"One year ahead" = the November survey's forecast for the next year. Columns: each year's miss, <span style="color: var(--under)">below zero when the forecast was too low</span>, <span style="color: var(--over)">above when too high</span>.</p>

## What the numbers say

```js
const id = view(indicatorPicker(meta, {key: "ifr-us-indicator"}));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const cards = insights(ind, stats.filter((d) => d.indicator === id), {made: "in November for the next year", benchmarkName: "\"no change\""});
```

<div class="grid grid-cols-3">${cards.map((c) => html`<div class="card"><span class="big">${c.stat}</span><p>${c.text}</p></div>`)}
</div>

<p class="muted small">The naive benchmark uses only data already published before each survey, taken from the Philadelphia Fed's real-time data set. All numbers are recomputed from the data at every build.</p>

## Explore

<div class="grid grid-cols-2">
  <a class="card card-link" href="./map">
    <h3>Forecast map</h3>
    <p>Every quarterly forecast as one cell: target year across, how far ahead it was made up the side, coloured by the miss.</p>
  </a>
  <a class="card card-link" href="./accuracy">
    <h3>Accuracy by horizon</h3>
    <p>How the miss shrinks as the year approaches, whether forecasters are biased, and whether they beat "no change".</p>
  </a>
</div>

<p class="muted small">Latest survey: ${meta.indicators[0].lastSurvey}. Data generated ${new Date(meta.generatedAt).toLocaleString("en", {dateStyle: "medium", timeStyle: "short"})}.</p>
