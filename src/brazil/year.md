---
title: One year in detail
---

# One year in detail

How the consensus for a single year moved, week by week, from the first survey that asked about it until the outcome was known.

```js
import {day, diff, diffUnit, lowerFirst, rows, value} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {errorLimit, errorScale, palette} from "../components/palette.js";
import {eventMarks} from "../components/charts.js";

const meta = await FileAttachment("../data/indicators.json").json();
const forecasts = rows(await FileAttachment("../data/forecasts.parquet").parquet());
const top5 = rows(await FileAttachment("../data/top5.parquet").parquet());
const monthly = rows(await FileAttachment("../data/monthly.parquet").parquet());
const outcomes = rows(await FileAttachment("../data/outcomes.parquet").parquet());
const known = rows(await FileAttachment("../data/known.parquet").parquet());
const pal = palette(dark);
```

```js
const id = view(indicatorPicker(meta));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const u = ind.unit;
const outcome = new Map(outcomes.filter((d) => d.indicator === id).map((d) => [d.target, d]));
const years = d3.sort(new Set(forecasts.filter((d) => d.indicator === id).map((d) => d.target)));
const fromUrl = Number(new URLSearchParams(location.search).get("y"));
const yearInput = Inputs.select(years, {
  label: "Target year",
  value: years.includes(fromUrl) ? fromUrl : ind.headline.worst.year,
  format: (y) => (outcome.get(y)?.actual == null ? `${y} (pending)` : String(y))
});
yearInput.addEventListener("input", () => {
  const url = new URL(location.href);
  url.searchParams.set("y", yearInput.value);
  history.replaceState(null, "", url);
});
const year = Generators.input(yearInput);
display(yearInput);
```

```js
const o = outcome.get(year) ?? {};
const actual = o.actual ?? null;
const path = forecasts.filter((d) => d.indicator === id && d.target === year);
const t5 = top5.filter((d) => d.indicator === id && d.target === year);
const start = path[0].date;
const yearEnd = new Date(Date.UTC(year, 11, 31));
const end = new Date(Math.max(yearEnd, path.at(-1).date));
const naive = known.filter((d) => d.indicator === id && d.date >= start && d.date <= end);
const cellsOfYear = monthly.filter((d) => d.indicator === id && d.target === year);
const at = (h) => cellsOfYear.find((d) => d.h === h);
const latest = d3.least(cellsOfYear, (d) => d.h);
```

```js
function fact(label, cell) {
  if (!cell) return null;
  const cls = actual == null ? "" : cell.err < 0 ? "under" : "over";
  return html`<div class="card"><h2>${label}</h2><span class="big ${cls}">${value(cell.median, u)}</span><p class="muted">${actual == null ? "outcome not known yet" : `missed by ${diff(cell.err, u)}`}</p></div>`;
}
```

<div class="grid grid-cols-4">
  ${fact("2 years ahead", at(24))}
  ${fact("1 year ahead", at(12))}
  ${fact("6 months ahead", at(6))}
  ${actual != null
    ? html`<div class="card"><h2>What happened</h2><span class="big" style=${{color: pal.actual}}>${value(actual, u)}</span><p class="muted">${ind.actualLabel}</p></div>`
    : html`<div class="card"><h2>Latest consensus</h2><span class="big">${value(latest.median, u)}</span><p class="muted">survey of ${day(latest.date)}</p></div>`}
</div>

```js
function pathChart(width) {
  const band = path.filter((d) => d.std != null);
  const marks = [
    Plot.rectX([0], {x1: new Date(Date.UTC(year, 0, 1)), x2: yearEnd, fill: "var(--theme-foreground)", fillOpacity: 0.04}),
    Plot.text([String(year)], {x: new Date(Date.UTC(year, 6, 1)), frameAnchor: "top", dy: 26, fill: "var(--theme-foreground-muted)"}),
    ...eventMarks([start, end], {width})
  ];
  if (o.goal != null) {
    marks.push(
      Plot.rectY([0], {x1: start, x2: end, y1: o.goal - o.goal_tolerance, y2: o.goal + o.goal_tolerance, fill: pal.goal, fillOpacity: 0.1}),
      Plot.ruleY([o.goal], {stroke: pal.goal, strokeDasharray: "2 3"})
    );
  }
  marks.push(
    Plot.areaY(band, {x: "date", y1: (d) => d.median - d.std, y2: (d) => d.median + d.std, fill: pal.consensus, fillOpacity: 0.12, curve: "step-after"}),
    Plot.lineY(naive, {x: "date", y: "value", stroke: pal.naive, strokeDasharray: "3 3", curve: "step-after"}),
    Plot.lineY(t5, {x: "date", y: "median", stroke: pal.top5, strokeWidth: 1.2}),
    Plot.lineY(path, {x: "date", y: "median", stroke: pal.consensus, strokeWidth: 2})
  );
  if (actual != null) {
    marks.push(
      Plot.ruleY([actual], {stroke: pal.actual, strokeWidth: 2}),
      Plot.text([actual], {y: (d) => d, frameAnchor: "left", dx: 4, dy: -9, text: (d) => `actual ${value(d, u)}`, fill: pal.actual, fontWeight: 600})
    );
  }
  marks.push(
    Plot.ruleX(path, Plot.pointerX({x: "date", stroke: "var(--theme-foreground-faint)"})),
    Plot.dot(path, Plot.pointerX({x: "date", y: "median", fill: pal.consensus, r: 3.5})),
    Plot.tip(path, Plot.pointerX({
      x: "date",
      y: "median",
      title: (d) => [
        `Survey of ${day(d.date)}`,
        `Consensus: ${value(d.median, u)}`,
        d.std != null ? `Forecasters' spread (±1 sd): ${diff(d.std, u, false)}` : null,
        d.respondents != null ? `${d.respondents} respondents` : null,
        actual != null ? `Miss: ${diff(d.median - actual, u)}` : null
      ].filter(Boolean).join("\n")
    }))
  );
  return Plot.plot({
    width,
    height: 400,
    marginLeft: 48,
    x: {type: "utc", domain: [start, end], label: null},
    y: {grid: true, label: `${ind.name} (${u})`, zero: id !== "fx", nice: true, insetTop: 22},
    marks
  });
}

function swatch(color, label, kind = "line", dash = false) {
  const s = kind === "band"
    ? `display:inline-block;width:14px;height:10px;background:${color};opacity:.35`
    : `display:inline-block;width:18px;border-top:2px ${dash ? "dashed" : "solid"} ${color};vertical-align:middle`;
  return html`<span class="swatch"><i style=${s}></i> ${label}</span>`;
}
```

<div class="card">
  <h2>${ind.name} ${year}: the weekly consensus</h2>
  <h3>Band: ±1 standard deviation across forecasters. Shaded: the target year itself. Dotted lines: elections and shocks.</h3>
  ${resize((width) => pathChart(width))}
  <div class="legend">
    ${swatch(pal.consensus, "Consensus (median)")}
    ${swatch(pal.consensus, "±1 std. deviation", "band")}
    ${t5.length ? swatch(pal.top5, "Top 5 forecasters") : ""}
    ${swatch(pal.naive, ind.naiveLabel, "line", true)}
    ${o.goal != null ? swatch(pal.goal, "Official target ± tolerance", "band") : ""}
    ${actual != null ? swatch(pal.actual, "What happened") : ""}
  </div>
</div>

## Every year's miss, one year ahead

```js
const yearAhead = monthly.filter((d) => d.indicator === id && d.h === 12 && d.actual != null);
const limit = errorLimit(monthly.filter((d) => d.indicator === id).map((d) => d.err));
```

<div class="card">
  <h2>Consensus in December of the previous year, minus what happened</h2>
  <h3>Below zero: the market forecast too low. The dashed tick is the naive guess's miss (${lowerFirst(ind.naiveLabel)}). Click a bar to inspect that year.</h3>
  ${resize((width) => {
    const chart = Plot.plot({
      width,
      height: 300,
      marginLeft: 48,
      x: {type: "band", label: null, padding: 0.18, tickFormat: (y) => (width < 640 && y % 5 !== 0 ? "" : `'${String(y).slice(2)}`)},
      y: {grid: true, label: `Miss (${diffUnit(u)})`},
      color: {...errorScale(pal, limit, null), legend: false},
      marks: [
        Plot.barY(yearAhead, {x: "target", y: "err", fill: "err", stroke: (d) => (d.target === year ? "var(--theme-foreground)" : "none"), strokeWidth: 2}),
        Plot.tickY(yearAhead.filter((d) => d.naive_err != null), {x: "target", y: "naive_err", stroke: pal.naive, strokeWidth: 2, strokeDasharray: "2 1.5"}),
        Plot.ruleY([0]),
        Plot.tip(yearAhead, Plot.pointerX({x: "target", y: "err", title: (d) => `${d.target}\nForecast in Dec ${d.target - 1}: ${value(d.median, u)}\nActual: ${value(d.actual, u)}\nMiss: ${diff(d.err, u)}\nNaive guess's miss: ${diff(d.naive_err, u)}`}))
      ]
    });
    chart.style.cursor = "pointer";
    chart.addEventListener("click", () => {
      if (!chart.value) return;
      yearInput.value = chart.value.target;
      yearInput.dispatchEvent(new Event("input", {bubbles: true}));
    });
    return chart;
  })}
</div>
