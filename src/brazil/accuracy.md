---
title: Accuracy by horizon
---

# Accuracy by horizon

How wrong is the consensus, depending on how long before the end of the target year it was made? Computed over every year whose outcome is known, from the last survey of each month.

```js
import {diff, diffUnit, lowerFirst, rows} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {palette} from "../components/palette.js";
import {biasBars, horizonLines} from "../components/forecast-charts.js";

const meta = await FileAttachment("../data/indicators.json").json();
const allStats = rows(await FileAttachment("../data/horizon-stats.parquet").parquet());
const pal = palette(dark);
```

```js
const id = view(indicatorPicker(meta));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const u = ind.unit;
// From four years ahead to December; longer horizons have too few years.
const stats = allStats.filter((d) => d.indicator === id && d.h >= 0 && d.h <= 48);
const x = {
  reverse: true,
  label: "Months before the end of the target year →",
  ticks: [48, 36, 24, 12, 0],
  tickFormat: (h) => (h === 0 ? "Dec" : String(h))
};

const lines = (width, series) => horizonLines(stats, series, {width, unit: u, x});

const benchmarks = [
  {name: "Focus consensus", key: "mae", color: pal.consensus},
  {name: `Naive: ${lowerFirst(ind.naiveLabel)}`, key: "naive_mae", color: pal.naive},
  ...(ind.hasGoal ? [{name: "Always forecast the official target", key: "goal_mae", color: pal.goal}] : [])
];
const hasTop5 = stats.some((d) => d.t5_mae != null);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Average miss: the consensus vs. simple benchmarks</h2>
    <h3>Benchmarks only use data already published on each survey date</h3>
    ${resize((width) => lines(width, benchmarks))}
  </div>
  <div class="card">
    <h2>Bias: the average error</h2>
    <h3>Below zero: on average the market forecast too low</h3>
    ${resize((width) => biasBars(stats, {width, pal, unit: u, x}))}
  </div>
</div>

```js
hasTop5
  ? html`<div class="card">
      <h2>Do the "best" forecasters do better?</h2>
      <h3>The Focus Top 5 (medium-term ranking) vs. everyone, compared on exactly the same years and horizons</h3>
      ${resize((width) => lines(width, [
        {name: "Focus consensus (same years)", key: "cons_t5_mae", color: pal.consensus},
        {name: "Top 5 forecasters", key: "t5_mae", color: pal.top5}
      ]))}
    </div>`
  : html`<div class="note">No Top 5 comparison for ${ind.name}: ${ind.notes.find((n) => n.includes("Top 5")) ?? "the series is too short."}</div>`
```

## The numbers

```js
const table = [48, 36, 24, 12, 6, 0]
  .map((h) => stats.find((d) => d.h === h))
  .filter(Boolean)
  .map((d) => ({
    horizon: d.h === 0 ? "December" : `${d.h} months`,
    years: d.n,
    bias: d.bias,
    mae: d.mae,
    rmse: d.rmse,
    naive: d.naive_mae,
    ...(ind.hasGoal ? {goal: d.goal_mae} : {}),
    ...(hasTop5 ? {top5: d.t5_mae} : {})
  }));
const fmt = (v) => diff(v, u, false);
```

```js
Inputs.table(table, {
  header: {horizon: "Made…", years: "Years", bias: "Bias", mae: "MAE", rmse: "RMSE", naive: "Naive MAE", goal: "Target MAE", top5: "Top 5 MAE"},
  format: {bias: (v) => diff(v, u), mae: fmt, rmse: fmt, naive: fmt, goal: fmt, top5: fmt},
  select: false,
  layout: "auto"
})
```

<p class="muted">MAE = mean absolute error; RMSE weighs big misses more. The Top 5 column is over the Top 5's own (shorter) sample; see the chart above for the like-for-like comparison.</p>
