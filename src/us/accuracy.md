---
title: "United States: accuracy by horizon"
---

# Accuracy by horizon

How wrong is the SPF median, depending on how long before the end of the target year the survey was taken? Over every year whose outcome is known.

```js
import {diff, lowerFirst, rows} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {palette} from "../components/palette.js";
import {biasBars, horizonLines} from "../components/forecast-charts.js";

const meta = await FileAttachment("../data/us/indicators.json").json();
const allStats = rows(await FileAttachment("../data/us/horizon-stats.parquet").parquet());
const pal = palette(dark);
```

```js
const id = view(indicatorPicker(meta, {key: "ifr-us-indicator"}));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const u = ind.unit;
const stats = allStats.filter((d) => d.indicator === id && d.h >= 0 && d.h <= 46);
const describe = (h) => `${h} months ahead`;
const hMax = d3.max(stats, (d) => d.h);
const x = {reverse: true, label: "Months before the end of the target year →", ticks: [46, 37, 25, 13, 1].filter((h) => h <= hMax), tickFormat: String};
const series = [
  {name: "SPF median", key: "mae", color: pal.consensus},
  {name: `"No change": ${lowerFirst(ind.naiveLabel)}`, key: "naive_mae", color: pal.naive}
];
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Average miss: the forecasters vs. "no change"</h2>
    <h3>The benchmark only uses data published before each survey</h3>
    ${resize((width) => horizonLines(stats, series, {width, unit: u, x, describe, dots: true}))}
  </div>
  <div class="card">
    <h2>Bias: the average error</h2>
    <h3>Below zero: on average the forecasters were too low</h3>
    ${resize((width) => biasBars(stats, {width, pal, unit: u, x, describe}))}
  </div>
</div>

## The numbers

```js
const table = [46, 37, 25, 13, 7, 1]
  .map((h) => stats.find((d) => d.h === h))
  .filter(Boolean)
  .map((d) => ({horizon: `${d.h} months`, years: d.n, bias: d.bias, mae: d.mae, rmse: d.rmse, naive: d.naive_mae, ratio: d.mae / d.naive_mae}));
const fmt = (v) => diff(v, u, false);
```

```js
Inputs.table(table, {
  header: {horizon: "Made…", years: "Years", bias: "Bias", mae: "MAE", rmse: "RMSE", naive: "\"No change\" MAE", ratio: "MAE ÷ no-change MAE"},
  format: {bias: (v) => diff(v, u), mae: fmt, rmse: fmt, naive: fmt, ratio: (v) => v.toFixed(2)},
  select: false,
  layout: "auto"
})
```

<p class="muted">Below 1 in the last column: the forecasters beat "no change" on average. MAE = mean absolute error; RMSE weighs big misses more. Horizons beyond two years only exist since 2009 (2005 for CPI), so they cover fewer years, or too few to show.</p>
