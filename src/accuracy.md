---
title: Accuracy by horizon
---

# Accuracy by horizon

How wrong is the consensus, depending on how long before the end of the target year it was made? Computed over every year whose outcome is known, from the last survey of each month.

```js
import {diff, diffUnit, lowerFirst, rows} from "./components/format.js";
import {indicatorPicker} from "./components/indicator.js";
import {errorLimit, errorScale, palette} from "./components/palette.js";

const meta = await FileAttachment("data/indicators.json").json();
const allStats = rows(await FileAttachment("data/horizon-stats.parquet").parquet());
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

function lines(width, series) {
  const data = series.flatMap(({name, key}) => stats.filter((d) => d[key] != null).map((d) => ({h: d.h, series: name, value: d[key]})));
  return Plot.plot({
    width,
    height: 320,
    marginLeft: 48,
    x,
    y: {grid: true, zero: true, label: `Average miss (${diffUnit(u)})`},
    color: {domain: series.map((s) => s.name), range: series.map((s) => s.color), legend: true},
    marks: [
      Plot.lineY(data, {x: "h", y: "value", stroke: "series", strokeWidth: (d) => (d.series === series[0].name ? 2.4 : 1.5)}),
      Plot.ruleX(data, Plot.pointerX({x: "h", stroke: "var(--theme-foreground-faint)"})),
      Plot.dot(data, Plot.pointerX({x: "h", y: "value", fill: "series", r: 3})),
      Plot.tip(data, Plot.pointerX({x: "h", y: "value", title: (d) => `${d.series}\n${d.h === 0 ? "In December" : `${d.h} months ahead`}: ${diff(d.value, u, false)}`}))
    ]
  });
}

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
    ${resize((width) => Plot.plot({
      width,
      height: 320,
      marginLeft: 48,
      x: {...x, type: "band", padding: 0.15},
      y: {grid: true, label: `Average error (${diffUnit(u)})`},
      color: {...errorScale(pal, errorLimit(stats.map((d) => d.bias), 1), null), legend: false},
      marks: [
        Plot.barY(stats, {x: "h", y: "bias", fill: "bias"}),
        Plot.ruleY([0]),
        Plot.tip(stats, Plot.pointerX({x: "h", y: "bias", title: (d) => `${d.h === 0 ? "In December" : `${d.h} months ahead`}\nAverage error: ${diff(d.bias, u)}\nOver ${d.n} years`}))
      ]
    }))}
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
