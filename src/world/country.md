---
title: "World: one country"
---

# One country

Every WEO forecast for one country (or one of the IMF's aggregates), from five years ahead down to the October edition of the year itself.

```js
import {diff, diffUnit, pct, rows, value} from "../components/format.js";
import {indicatorPicker} from "../components/indicator.js";
import {errorLimit, palette} from "../components/palette.js";
import {aheadVsActual, forecastGrid, horizonLines} from "../components/forecast-charts.js";
import {editionLabel, editionTick} from "../components/imf.js";

const meta = await FileAttachment("../data/world/meta.json").json();
const countries = rows(await FileAttachment("../data/world/countries.parquet").parquet());
const allCells = rows(await FileAttachment("../data/world/cells.parquet").parquet());
const stats = rows(await FileAttachment("../data/world/country-stats.parquet").parquet());
const focus = rows(await FileAttachment("../data/monthly.parquet").parquet());
const pal = palette(dark);
```

```js
// Countries first (alphabetical), then the IMF's aggregates.
const options = [
  ...countries.filter((d) => d.group !== "agg").sort((a, b) => a.name.localeCompare(b.name)),
  ...countries.filter((d) => d.group === "agg")
];
const fromUrl = new URLSearchParams(location.search).get("c");
const countryInput = Inputs.select(options, {
  label: "Country",
  value: options.find((d) => d.iso3 === fromUrl) ?? options.find((d) => d.iso3 === "BRA"),
  format: (d) => (d.group === "agg" ? `${d.name} (aggregate)` : d.name)
});
countryInput.addEventListener("input", () => {
  const url = new URL(location.href);
  url.searchParams.set("c", countryInput.value.iso3);
  history.replaceState(null, "", url);
});
const country = Generators.input(countryInput);
display(countryInput);
```

```js
const id = view(indicatorPicker(meta, {key: "ifr-world-indicator"}));
```

```js
const ind = meta.indicators.find((d) => d.id === id);
const u = ind.unit;
const cells = allCells
  .filter((d) => d.iso3 === country.iso3 && d.indicator === id)
  .map((d) => ({...d, err: d.actual == null ? null : d.forecast - d.actual, naive_err: d.actual == null || d.naive == null ? null : d.naive - d.actual}));
const s = stats.filter((d) => d.iso3 === country.iso3 && d.indicator === id);
const at = (h) => s.find((d) => d.h === h);
const ahead = cells.filter((d) => d.h === 14 && d.actual != null);
const worst = d3.greatest(ahead, (d) => Math.abs(d.err));
const limit = errorLimit(cells.map((d) => d.err));
const regionName = country.group === "agg" ? "IMF aggregate" : meta.regions[country.group];
```

<p class="muted">${regionName}. ${ind.note}</p>

```js
function card(title, big, text, cls = "") {
  return html`<div class="card"><h2>${title}</h2><span class="big ${cls}">${big}</span><p class="muted">${text}</p></div>`;
}
const y1 = at(14);
```

```js
cells.length === 0
  ? html`<div class="note">The WEO has no ${ind.name} forecasts for ${country.name}.</div>`
  : html`<div class="grid grid-cols-4">
      ${card("One year ahead", diff(y1?.mdae, u, false), `typical miss of the October forecast for the next year (${y1?.n ?? 0} years)`)}
      ${card("Bias (average error)", diff(y1?.bias, u), !y1 ? "too few years" : (y1.bias < 0) === (y1.over < 0.5) ? `on average the forecast was too ${y1.bias < 0 ? "low" : "high"}; too high in ${pct(y1.over)} of years` : `on average too ${y1.bias < 0 ? "low" : "high"}, yet too high in ${pct(y1.over)} of years: a few big misses drive the average`, y1 ? (y1.bias < 0 ? "under" : "over") : "")}
      ${card(`Beats "same as last year"`, pct(y1?.beat_naive), `of years, one year ahead. Naive's typical miss: ${diff(y1?.naive_mdae, u, false)}`)}
      ${worst ? card("Biggest miss", String(worst.target), `${value(worst.forecast, u)} expected in October ${worst.target - 1}, ${value(worst.actual, u)} in reality`) : card("Biggest miss", "–", "no completed years yet")}
    </div>`
```

```js
function tipText(d) {
  return [
    `${country.name}, ${ind.name} ${d.target}`,
    `${editionLabel(d.h)} edition: ${value(d.forecast, u)}`,
    d.actual == null ? "Outcome not known yet" : `Actual: ${value(d.actual, u)}`,
    d.actual == null ? null : `Miss: ${diff(d.err, u)} (${d.err < 0 ? "too low" : "too high"})`
  ].filter(Boolean).join("\n");
}
```

<div class="card">
  <h2>${country.name}: every forecast of ${ind.name}, editions ${meta.firstEdition}–${meta.lastEdition.slice(0, 4)}</h2>
  <h3>Across: the target year. Up the side: the edition, from five years before the target year down to October of the year itself. Colour saturates at ±${diff(limit, u, false)}; outlined cells are still pending.</h3>
  ${cells.length ? resize((width) => forecastGrid(cells, {
    width,
    pal,
    dark,
    unit: u,
    value: "forecast",
    step: 6,
    rowHeight: 26,
    minHeight: 300,
    limit,
    marginLeft: 64,
    yTicks: editionTick,
    yLabel: "Edition (years before the target year)",
    tip: tipText
  })) : ""}
</div>

<div class="card">
  <h2>October forecast for the next year → the outcome</h2>
  <h3>Hollow dot: the forecast in October of the year before. Filled dot: what happened. The line is the miss.</h3>
  ${ahead.length ? resize((width) => aheadVsActual(ahead, {
    width,
    pal,
    unit: u,
    value: "forecast",
    limit,
    label: `${ind.name} (${u})`,
    zero: true,
    tip: (d) => `${d.target}\nForecast in Oct ${d.target - 1}: ${value(d.forecast, u)}\nActual: ${value(d.actual, u)}\nMiss: ${diff(d.err, u)}`
  })) : html`<p class="muted">No completed years.</p>`}
</div>

<div class="card">
  <h2>How the miss shrinks as the year approaches</h2>
  <h3>Median absolute error by edition, the IMF vs. "same as last year"</h3>
  ${s.length ? resize((width) => horizonLines(s.filter((d) => d.h <= 50), [
    {name: "IMF forecast", key: "mdae", color: pal.consensus},
    {name: "Same as last year", key: "naive_mdae", color: pal.naive}
  ], {
    width,
    unit: u,
    x: {reverse: true, ticks: [50, 38, 26, 14, 2], tickFormat: editionTick, label: "Edition →"},
    yLabel: `Typical miss (${diffUnit(u)})`,
    describe: editionLabel,
    dots: true
  })) : html`<p class="muted">Too few completed years.</p>`}
</div>

```js
// The Brazil comparison: Focus GDP growth vs. the IMF at the same moments. The
// Focus monthly cells carry the last survey of each month, so October (h = 14)
// and April (h = 8 / 20) line up with the WEO editions. Inflation isn't
// comparable: the WEO forecasts annual-average CPI, Focus December/December IPCA.
const vsFocus = country.iso3 === "BRA" && id === "gdp"
  ? cells
      .filter((d) => d.actual != null)
      .map((d) => ({...d, focus: focus.find((f) => f.indicator === "gdp" && f.target === d.target && f.h === d.h)}))
      .filter((d) => d.focus?.actual != null)
  : [];
const vsFocusStats = d3.sort(
  d3.rollups(vsFocus, (v) => ({h: v[0].h, n: v.length, imf: d3.mean(v, (d) => Math.abs(d.err)), focus: d3.mean(v, (d) => Math.abs(d.focus.err)), imfWins: d3.sum(v, (d) => Math.abs(d.err) < Math.abs(d.focus.err))}), (d) => d.h).map(([, v]) => v),
  (d) => -d.h
);
```

```js
vsFocus.length
  ? html`<h2>Brazil: the IMF vs. the local market</h2>
    <p>The Banco Central's <a href="../brazil/">Focus survey</a> also forecasts Brazil's GDP growth, every week. Taking the Focus consensus at the end of the same month as each WEO edition, and scoring both against the same years:</p>
    <div class="card">
      <h2>Average miss, GDP growth: the IMF vs. the Focus consensus, same years</h2>
      <h3>Each forecast scored against its own source's outcome (the IMF's October estimate; IBGE's annual growth)</h3>
      ${Inputs.table(vsFocusStats, {
        columns: ["h", "n", "imf", "focus", "imfWins"],
        header: {h: "Forecast made in", n: "Years", imf: "IMF", focus: "Focus consensus", imfWins: "Years the IMF was closer"},
        format: {h: editionLabel, imf: (v) => diff(v, "%", false), focus: (v) => diff(v, "%", false), imfWins: (v, i, data) => `${v} of ${data[i].n}`},
        select: false,
        layout: "auto"
      })}
    </div>`
  : country.iso3 === "BRA"
    ? html`<p class="muted small">Pick GDP to compare the IMF with Brazil's Focus survey. Inflation isn't comparable: the IMF forecasts annual-average CPI, Focus the December-on-December IPCA.</p>`
    : ""
```
