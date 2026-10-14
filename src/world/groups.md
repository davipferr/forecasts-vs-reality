---
title: "World: optimism and emerging markets"
---

# Is the IMF too optimistic? Are emerging markets harder?

Two classic questions about the WEO, answered from every forecast since 1990. Statistics pool every country and year and use **medians**: a few hyperinflations (Venezuela, Zimbabwe, Sudan) would otherwise decide the "average" of a whole region.

```js
import {diff, diffUnit, pct, rows} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {errorLimit, errorScale, palette} from "../components/palette.js";
import {HORIZONS, editionLabel, editionTick} from "../components/imf.js";

const meta = await FileAttachment("../data/world/meta.json").json();
const groups = rows(await FileAttachment("../data/world/group-stats.parquet").parquet());
const years = rows(await FileAttachment("../data/world/year-stats.parquet").parquet());
const pal = palette(dark);
```

```js
const id = view(indicatorPicker({indicators: meta.indicators.filter((d) => d.optimistic != null)}, {key: "ifr-world-groups"}));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const u = ind.unit;
const sign = ind.optimistic; // +1: too high is optimistic (growth); −1: too low is (inflation)
const optimistic = (d) => (sign === 1 ? d.over : d.under);
const SETS = [
  {set: "adv", name: "Advanced economies", color: pal.categorical[0]},
  {set: "emde", name: "Emerging and developing", color: pal.categorical[1]}
];
const g = groups.filter((d) => d.indicator === id && d.h <= 50);
const x = {reverse: true, ticks: [50, 38, 26, 14, 2], tickFormat: editionTick, label: "Edition →"};
const at = (set, h) => g.find((d) => d.set === set && d.h === h);
const word = sign === 1 ? "growth too high" : "inflation too low";
```

## Optimism

<div class="grid grid-cols-3">
  <div class="card">
    <h2>One year ahead, all countries</h2>
    <span class="big">${pct(optimistic(at("all", 14)))}</span>
    <p class="muted">of October forecasts for the next year had ${word}</p>
  </div>
  <div class="card">
    <h2>Five years ahead</h2>
    <span class="big">${pct(optimistic(at("all", 50)))}</span>
    <p class="muted">of forecasts four to five years out had ${word}</p>
  </div>
  <div class="card">
    <h2>Same year, October</h2>
    <span class="big">${pct(optimistic(at("all", 2)))}</span>
    <p class="muted">with only three months left: close to a coin flip means no bias</p>
  </div>
</div>

```js
function lines(width, key, {yLabel, format, rule}) {
  const data = SETS.flatMap(({set, name}) => g.filter((d) => d.set === set).map((d) => ({h: d.h, name, value: key(d), n: d.n})));
  return Plot.plot({
    width,
    height: 300,
    marginLeft: 48,
    x,
    y: {grid: true, label: yLabel, tickFormat: format, zero: rule == null},
    color: {domain: SETS.map((s) => s.name), range: SETS.map((s) => s.color), legend: true},
    marks: [
      rule != null ? Plot.ruleY([rule], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "3 3"}) : null,
      Plot.lineY(data, {x: "h", y: "value", stroke: "name", strokeWidth: 2}),
      Plot.dot(data, {x: "h", y: "value", fill: "name", r: 3}),
      Plot.tip(data, Plot.pointer({x: "h", y: "value", title: (d) => `${d.name}\n${editionLabel(d.h)}: ${format(d.value)}\nOver ${d.n.toLocaleString("en")} forecasts`}))
    ]
  });
}
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Share of forecasts with ${word}</h2>
    <h3>Above the dashed line: optimistic more often than not</h3>
    ${resize((width) => lines(width, optimistic, {yLabel: "Share of forecasts", format: pct, rule: 0.5}))}
  </div>
  <div class="card">
    <h2>The median error</h2>
    <h3>Forecast − outcome; ${sign === 1 ? "above zero = growth over-forecast" : "below zero = inflation under-forecast"}</h3>
    ${resize((width) => lines(width, (d) => d.median_err, {yLabel: `Median error (${diffUnit(u)})`, format: (v) => diff(v, u), rule: 0}))}
  </div>
</div>

```js
const h = view(Inputs.select([2, 8, 14, 20], {label: "Forecast made in", value: 14, format: editionLabel}));
```

```js
const yr = years.filter((d) => d.indicator === id && d.h === h && d.set !== "all");
const yLimit = errorLimit(yr.map((d) => d.median_err), 0.95);
```

<div class="card">
  <h2>Year by year: the median error across countries</h2>
  <h3>Forecasts made in ${editionLabel(h)}. ${sign === 1 ? "Global recessions (2009, 2020) are the big optimistic misses: the IMF, like everyone, didn't see them coming." : "Inflation surprises (2008, 2021–22) show as years where most countries' forecasts were too low."}</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 320,
    marginLeft: 48,
    x: {label: null, tickFormat: (y) => String(y), ticks: width < 640 ? 5 : 10},
    y: {grid: true, label: `Median error (${diffUnit(u)})`},
    color: {domain: SETS.map((s) => s.name), range: SETS.map((s) => s.color), legend: true},
    marks: [
      Plot.ruleY([0]),
      Plot.lineY(yr, {x: "target", y: "median_err", stroke: (d) => SETS.find((s) => s.set === d.set).name, strokeWidth: 2}),
      Plot.tip(yr, Plot.pointer({x: "target", y: "median_err", title: (d) => `${SETS.find((s) => s.set === d.set).name}, ${d.target}\nMedian error: ${diff(d.median_err, u)}\n${pct(optimistic(d))} of ${d.countries} countries with ${word}`}))
    ]
  }))}
</div>

## Are emerging markets harder to forecast?

```js
const regionRows = Object.entries(meta.regions)
  .filter(([k]) => k !== "adv")
  .map(([k, name]) => ({set: k, name, ...at(k, 14)}))
  .concat([{set: "adv", name: meta.regions.adv, ...at("adv", 14)}])
  .filter((d) => d.mdae != null);
```

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Typical miss by edition</h2>
    <h3>Median absolute error: emerging and developing economies vs. advanced ones</h3>
    ${resize((width) => lines(width, (d) => d.mdae, {yLabel: `Typical miss (${diffUnit(u)})`, format: (v) => diff(v, u, false)}))}
  </div>
  <div class="card">
    <h2>By region, one year ahead</h2>
    <h3>Typical miss of the October forecast for the next year; the tick is "same as last year"</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 300,
      marginLeft: Math.min(210, width * 0.42),
      x: {grid: true, label: `Typical miss (${diffUnit(u)})`, zero: true},
      y: {label: null, domain: d3.sort(regionRows, (d) => -d.mdae).map((d) => d.name)},
      marks: [
        Plot.barX(regionRows, {y: "name", x: "mdae", fill: (d) => (d.set === "adv" ? SETS[0].color : SETS[1].color), insetTop: 4, insetBottom: 4}),
        Plot.tickX(regionRows, {y: "name", x: "naive_mdae", stroke: pal.naive, strokeWidth: 2, strokeDasharray: "2 1.5"}),
        Plot.tip(regionRows, Plot.pointerY({y: "name", x: "mdae", title: (d) => `${d.name}\nTypical miss: ${diff(d.mdae, u, false)}\n"Same as last year": ${diff(d.naive_mdae, u, false)}\n${d.countries} countries, ${d.n.toLocaleString("en")} forecasts`}))
      ]
    }))}
  </div>
</div>

## Does the IMF beat "same as last year"?

<div class="card">
  <h2>Share of forecasts closer to the outcome than last year's value</h2>
  <h3>Above 50%: the IMF beats the simplest possible forecast more often than not. The benchmark uses last year's value as published in the same edition.</h3>
  ${resize((width) => lines(width, (d) => d.beat_naive, {yLabel: "Share of forecasts", format: pct, rule: 0.5}))}
</div>

<p class="muted small">Groups use the WEO's current classification for every year. "Optimistic" means growth forecast too high, or inflation forecast too low. Cells: a country × target year × edition; the same year appears once per edition.</p>
