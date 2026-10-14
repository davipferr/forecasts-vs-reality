---
title: "Brazil: overview"
toc: false
---

# Brazil: the Focus survey

<p class="lede">How good is the Brazilian market at seeing the future? Every forecast in the Banco Central's weekly <em>Focus</em> survey since 2000, for inflation, the Selic rate, GDP growth and the dollar, scored against what actually happened.</p>

```js
import {diff, rows, value} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {insights} from "../components/insights.js";
import {palette} from "../components/palette.js";
import {miniColumns} from "../components/charts.js";

const meta = await FileAttachment("../data/indicators.json").json();
const stats = rows(await FileAttachment("../data/horizon-stats.parquet").parquet());
const pal = palette(dark);
```

<div class="grid grid-cols-4">${meta.indicators.map((ind) => html`<a class="card card-link" href="./year?i=${ind.id}">
    <h2>${ind.name}</h2>
    <span class="big">${diff(ind.headline.mae, ind.unit, false)}</span>
    <p class="muted">average miss one year ahead (${ind.headline.first}–${ind.headline.last}). Too ${ind.headline.under >= ind.headline.over ? `low in ${ind.headline.under}` : `high in ${ind.headline.over}`} of ${ind.headline.years} years.</p>
    ${resize((width) => miniColumns(ind.yearAhead, {
      width,
      x: "year",
      y: "err",
      fill: (d) => (d.err < 0 ? pal.diverging.neg : pal.diverging.pos),
      title: (d) => `${d.year}: forecast ${d.err < 0 ? "too low" : "too high"} by ${diff(d.err, ind.unit, false)}`
    }))}
  </a>`)}
</div>

<p class="muted small">Columns: each year's miss one year ahead, <span style="color: var(--under)">below zero when the forecast was too low</span>, <span style="color: var(--over)">above when too high</span>.</p>

## What the numbers say

```js
const id = view(indicatorPicker(meta));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const cards = insights(ind, stats.filter((d) => d.indicator === id));
```

<div class="grid grid-cols-3">${cards.map((c) => html`<div class="card"><span class="big">${c.stat}</span><p>${c.text}</p></div>`)}
</div>

<p class="muted small">"One year ahead" = the consensus in December of the previous year. The naive guess uses only data already published on the survey date. All numbers are recomputed from the data at every build.</p>

## Explore

<div class="grid grid-cols-3">
  <a class="card card-link" href="./map">
    <h3>Forecast map</h3>
    <p>Every forecast as one cell: target year across, how far ahead it was made up the side, coloured by how wrong it turned out to be.</p>
  </a>
  <a class="card card-link" href="./year">
    <h3>One year in detail</h3>
    <p>How the consensus for a single year moved, week by week, until the outcome was known, with the official target and the Top 5.</p>
  </a>
  <a class="card card-link" href="./accuracy">
    <h3>Accuracy by horizon</h3>
    <p>How the miss shrinks as the year approaches, whether the market is biased, and whether it beats simple benchmarks.</p>
  </a>
</div>

<div class="grid grid-cols-2">
  <a class="card card-link" href="../sql">
    <h3>SQL console</h3>
    <p>The same Parquet files behind the charts, queryable with SQL in your browser through DuckDB-WASM.</p>
  </a>
  <a class="card card-link" href="../about">
    <h3>About the data</h3>
    <p>Sources, definitions and caveats: which outcome each forecast is scored against, and why.</p>
  </a>
</div>

<p class="muted small">Latest survey: ${meta.indicators[0].lastSurvey}. Data generated ${new Date(meta.generatedAt).toLocaleString("en", {dateStyle: "medium", timeStyle: "short"})}.</p>
