---
toc: false
---

# Forecasts vs. Reality

<p class="lede">How good are forecasters at seeing the future? Four of them, each scored against what actually happened and against the simplest forecast of all, "nothing changes": Brazil's market economists, the IMF, America's professional forecasters, and the bond market itself.</p>

```js
import {diff, pct, rows} from "./components/format.js";

const brazil = await FileAttachment("data/indicators.json").json();
const world = rows(await FileAttachment("data/world/group-stats.parquet").parquet());
const us = await FileAttachment("data/us/indicators.json").json();
const fstats = rows(await FileAttachment("data/bonds/forward-stats.parquet").parquet());
const rec = await FileAttachment("data/bonds/recessions.json").json();
```

```js
const ipca = brazil.indicators.find((d) => d.id === "ipca").headline;
const fx = brazil.indicators.find((d) => d.id === "fx").headline;
const gdpAll = world.find((d) => d.set === "all" && d.indicator === "gdp" && d.h === 14);
const gdpAdv = world.find((d) => d.set === "adv" && d.indicator === "gdp" && d.h === 14);
const gdpEmde = world.find((d) => d.set === "emde" && d.indicator === "gdp" && d.h === 14);
const usRates = us.indicators.filter((d) => d.id === "tbill" || d.id === "tbond").map((d) => d.headline);
const usCpi = us.indicators.find((d) => d.id === "cpi").headline;
const fw1 = fstats.find((d) => d.sample === "1990" && d.k === 1);
const fw3 = fstats.find((d) => d.sample === "1990" && d.k === 3);
const sp = rec.spreads[0];
const signalled = sp.recessions.filter((r) => r.signal != null).length;
const falseAlarms = sp.episodes.filter((e) => e.outcome === "false alarm");
```

<div class="grid grid-cols-2">
  <a class="card card-link" href="./brazil/">
    <h2>Brazil: the Focus survey</h2>
    <p class="muted">The Banco Central's weekly survey of ~100 market economists, since 2000: inflation, the Selic rate, GDP and the dollar.</p>
    <span class="big">${ipca.under} of ${ipca.years}</span>
    <p>years the market <strong>under-forecast inflation</strong> a year ahead. On the dollar, it is no more accurate than "the rate stays where it is" (${diff(fx.mae, "R$", false)} vs ${diff(fx.naiveMae, "R$", false)} average miss).</p>
  </a>
  <a class="card card-link" href="./world/">
    <h2>World: the IMF</h2>
    <p class="muted">Every <em>World Economic Outlook</em> since 1990, about 190 countries: growth, inflation, the current account.</p>
    <span class="big">${pct(gdpAll.over)}</span>
    <p>of the IMF's growth forecasts a year ahead were <strong>too optimistic</strong>. Emerging economies are harder: a typical miss of ${diff(gdpEmde.mdae, "%", false)}, vs ${diff(gdpAdv.mdae, "%", false)} for advanced ones.</p>
  </a>
  <a class="card card-link" href="./us/">
    <h2>United States: professional forecasters</h2>
    <p class="muted">The Philadelphia Fed's quarterly Survey of Professional Forecasters: inflation, GDP, unemployment, interest rates.</p>
    <span class="big">${usRates.map((h) => `${h.beatNaive} of ${h.years}`).join(" · ")}</span>
    <p>years the forecasters beat "no change" a year ahead for the <strong>3-month and 10-year rates</strong>. For CPI inflation: ${usCpi.beatNaive} of ${usCpi.years}.</p>
  </a>
  <a class="card card-link" href="./bonds/">
    <h2>The bond market</h2>
    <p class="muted">Forward rates as forecasts of future rates, the term premium, and the inverted yield curve as a recession signal.</p>
    <span class="big">${diff(fw1.bias, "%")} · ${diff(fw3.bias, "%")}</span>
    <p>average gap between forward rates and the rates that came, one and three years ahead (since 1990): mostly <strong>term premium</strong>. The inverted curve came before ${signalled} of ${sp.recessions.length} recessions since ${sp.first.slice(0, 4)}, with ${falseAlarms.length} false alarm${falseAlarms.length === 1 ? "" : "s"}${falseAlarms.length ? ` (${falseAlarms.map((e) => e.start.slice(0, 4)).join(", ")})` : ""}.</p>
  </a>
</div>

## How everything is scored

- **Error** = forecast − what happened. Negative: the forecast was too low.
- **Horizon**: months from the forecast to December of the year it's about. A forecast made in October for the next year is 14 months ahead.
- **"Nothing changes"**: every source is compared with the naive forecast that repeats the latest published value, using only data that was public at the time.
- **Outcomes** are the values as first settled (about a year later), not today's revised numbers, where the source allows it.

<div class="grid grid-cols-2">
  <a class="card card-link" href="./sql">
    <h3>SQL console</h3>
    <p>The Parquet files behind every chart, queryable with SQL in your browser through DuckDB-WASM.</p>
  </a>
  <a class="card card-link" href="./about">
    <h3>About the data</h3>
    <p>Sources, definitions, benchmarks and caveats for each section.</p>
  </a>
</div>

<p class="muted small">All numbers are recomputed from the data at every build. Data generated ${new Date(brazil.generatedAt).toLocaleString("en", {dateStyle: "medium", timeStyle: "short"})}.</p>
