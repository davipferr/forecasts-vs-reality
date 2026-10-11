---
toc: false
---

# Forecasts vs. Reality

<p class="lede">How good is the Brazilian market at seeing the future? Every forecast in the Banco Central's weekly <em>Focus</em> survey since 2000, for inflation, the Selic rate, GDP growth and the dollar, scored against what actually happened.</p>

```js
import {diff, rows, value} from "./components/format.js";
import {indicatorPicker} from "./components/indicator.js";
import {insights} from "./components/insights.js";

const meta = await FileAttachment("data/indicators.json").json();
const stats = rows(await FileAttachment("data/horizon-stats.parquet").parquet());
```

<div class="grid grid-cols-4">${meta.indicators.map((ind) => html`<a class="card card-link" href="./year?i=${ind.id}">
    <h2>${ind.name}</h2>
    <span class="big">${diff(ind.headline.mae, ind.unit, false)}</span>
    <p class="muted">average miss one year ahead (${ind.headline.first}–${ind.headline.last}). Too ${ind.headline.under >= ind.headline.over ? `low in ${ind.headline.under}` : `high in ${ind.headline.over}`} of ${ind.headline.years} years.</p>
  </a>`)}
</div>

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
  <a class="card card-link" href="./sql">
    <h3>SQL console</h3>
    <p>The same Parquet files behind the charts, queryable with SQL in your browser through DuckDB-WASM.</p>
  </a>
  <a class="card card-link" href="./about">
    <h3>About the data</h3>
    <p>Sources, definitions and caveats: which outcome each forecast is scored against, and why.</p>
  </a>
</div>

<p class="muted small">Latest survey: ${meta.indicators[0].lastSurvey}. Data generated ${new Date(meta.generatedAt).toLocaleString("en", {dateStyle: "medium", timeStyle: "short"})}.</p>

<style>
.lede { font-size: 1.15rem; max-width: 52rem; color: var(--theme-foreground-muted); }
.card-link { display: block; text-decoration: none; color: inherit; transition: border-color 150ms; }
.card-link:hover { border-color: var(--theme-foreground-focus); }
.big { font-size: 2rem; font-weight: 700; line-height: 1.2; font-variant-numeric: tabular-nums; }
.card p { margin: 0.35rem 0 0; }
.small { font-size: 0.85rem; }
</style>
