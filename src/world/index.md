---
title: "World: the IMF map"
toc: false
---

# The IMF's forecasts, country by country

<p class="lede">Twice a year, in April and October, the IMF's <em>World Economic Outlook</em> forecasts growth, inflation and the current account for about 190 countries. Here is every edition since 1990, scored against what happened.</p>

```js
import * as topojson from "npm:topojson-client";
import {diff, diffUnit, pct, rows, value} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {errorLimit, errorScale, magnitudeScale, palette} from "../components/palette.js";
import {HORIZONS, editionLabel} from "../components/imf.js";

const meta = await FileAttachment("../data/world/meta.json").json();
const countries = rows(await FileAttachment("../data/world/countries.parquet").parquet());
const stats = rows(await FileAttachment("../data/world/country-stats.parquet").parquet());
const groups = rows(await FileAttachment("../data/world/group-stats.parquet").parquet());
const world = await fetch(import.meta.resolve("npm:world-atlas/countries-110m.json")).then((r) => r.json());
const pal = palette(dark);
```

```js
const id = view(indicatorPicker(meta, {key: "ifr-world-indicator"}));
```

```js
const h = view(Inputs.select(HORIZONS, {label: "Forecast made in", value: 14, format: editionLabel}));
```

```js
const metric = view(Inputs.radio(new Map([["Bias (average error)", "bias"], ["Typical miss", "mdae"]]), {label: "Colour", value: "bias"}));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const u = ind.unit;
const byIso = new Map(countries.map((d) => [d.iso3, d]));
const here = stats.filter((d) => d.indicator === id && d.h === h);
const statByNum = new Map(here.filter((d) => byIso.get(d.iso3)?.iso_num).map((d) => [byIso.get(d.iso3).iso_num, d]));
const land = topojson.feature(world, world.objects.countries);
land.features = land.features.filter((f) => f.id !== "010"); // Antarctica
const g = (set) => groups.find((d) => d.set === set && d.indicator === id && d.h === h);
const all = g("all");
const adv = g("adv");
const emde = g("emde");
const limit = metric === "bias" ? errorLimit(here.map((d) => d.bias)) : errorLimit(here.map((d) => d.mdae));
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Typical miss</h2>
    <span class="big">${diff(all?.mdae, u, false)}</span>
    <p class="muted">median absolute error over ${all?.n.toLocaleString("en")} forecasts in ${all?.countries} countries</p>
  </div>
  <div class="card">
    <h2>${ind.optimistic == null ? "Too high" : "Too optimistic"}</h2>
    <span class="big">${pct(ind.optimistic === -1 ? all?.under : all?.over)}</span>
    <p class="muted">of forecasts ${ind.optimistic === 1 ? "expected more growth than happened" : ind.optimistic === -1 ? "expected less inflation than happened" : "were above the outcome"}</p>
  </div>
  <div class="card">
    <h2>Emerging vs. advanced</h2>
    <span class="big">${diff(emde?.mdae, u, false)} <span class="muted small">vs</span> ${diff(adv?.mdae, u, false)}</span>
    <p class="muted">typical miss for emerging and developing economies vs. advanced ones</p>
  </div>
  <div class="card">
    <h2>Beats "same as last year"</h2>
    <span class="big">${pct(all?.beat_naive)}</span>
    <p class="muted">of forecasts were closer than simply repeating last year's value</p>
  </div>
</div>

```js
function tipText(f) {
  const s = statByNum.get(f.id);
  const c = s && byIso.get(s.iso3);
  if (!s) return `${f.properties.name}\nNo forecasts scored`;
  return [
    c.name,
    `${s.n} years scored (${s.first}–${s.last})`,
    `Bias: ${diff(s.bias, u)} (${s.bias < 0 ? "too low" : "too high"} on average)`,
    `Typical miss: ${diff(s.mdae, u, false)}`,
    `Closer than "same as last year" in ${pct(s.beat_naive)} of years`,
    "Click for this country"
  ].join("\n");
}

function mapChart(width) {
  const chart = Plot.plot({
    width,
    height: width * 0.5,
    projection: {type: "equal-earth", domain: land},
    color: metric === "bias"
      ? errorScale(pal, limit, `Average error (${diffUnit(u)}): red = forecast too low, blue = too high`)
      : magnitudeScale(pal, limit, `Typical miss, median absolute error (${diffUnit(u)})`),
    marks: [
      // No data: an empty outline, so it can't be mistaken for a near-zero error (the grey midpoint).
      Plot.geo(land, {fill: "var(--theme-background)", stroke: "var(--theme-foreground-faint)", strokeWidth: 0.5}),
      // Plot evaluates channels before filtering, hence the optional chaining;
      // countries without a value keep the grey base layer.
      Plot.geo(land, {
        filter: (f) => statByNum.has(f.id),
        fill: (f) => statByNum.get(f.id)?.[metric],
        stroke: "var(--theme-background)",
        strokeWidth: 0.5
      }),
      Plot.tip(land.features, Plot.pointer(Plot.geoCentroid({title: tipText})))
    ]
  });
  chart.style.cursor = "pointer";
  chart.addEventListener("click", () => {
    const s = chart.value && statByNum.get(chart.value.id);
    if (s) location.href = `./country?c=${s.iso3}&i=${id}`;
  });
  return chart;
}
```

<div class="card">
  <h2>${ind.name}, forecast in ${editionLabel(h)}: ${metric === "bias" ? "the average error" : "the typical miss"} per country</h2>
  <h3>${metric === "bias" ? `Average of forecast − outcome over every scored year. Colour saturates at ±${diff(limit, u, false)}.` : `Median absolute error, so a single crisis year doesn't decide it. Colour saturates at ${diff(limit, u, false)}.`} Outlined: no data or fewer than five scored years. Small islands are too small to see at this scale; they're in the table below.</h3>
  ${resize((width) => mapChart(width))}
</div>

<p class="muted small">${ind.note} Outcome: the value published in the October edition of the following year (the IMF's own convention), so the latest scored year is ${meta.lastScored}.</p>

## Every country

```js
const search = view(Inputs.search(here.map((d) => ({...d, name: byIso.get(d.iso3)?.name, group: byIso.get(d.iso3)?.group})), {placeholder: "Search countries…"}));
```

```js
Inputs.table(search, {
  columns: ["name", "group", "n", "bias", "mdae", "naive_mdae", "beat_naive"],
  header: {name: "Country", group: "Group", n: "Years", bias: "Bias", mdae: "Typical miss", naive_mdae: "Naive's typical miss", beat_naive: "Beats naive"},
  format: {
    name: (n, i, data) => html`<a href=${`./country?c=${data[i].iso3}&i=${id}`}>${n}</a>`,
    group: (g) => (g === "agg" ? "Aggregate" : meta.regions[g]),
    bias: (v) => diff(v, u),
    mdae: (v) => diff(v, u, false),
    naive_mdae: (v) => diff(v, u, false),
    beat_naive: pct
  },
  sort: "mdae",
  reverse: true,
  layout: "auto",
  select: false,
  rows: 15
})
```

<p class="muted small">Naive benchmark: "same as last year", using last year's value as published in that same edition, so it only uses what the IMF already knew. Aggregates (World, advanced economies, emerging and developing economies, euro area) are in the table but not on the map.</p>
