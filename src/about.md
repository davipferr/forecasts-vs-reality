---
title: About the data
---

# About the data

```js
const meta = await FileAttachment("data/indicators.json").json();
```

## Sources

Everything comes from the **Banco Central do Brasil**, fetched at build time by Python data loaders (httpx + Polars). The browser only downloads the resulting Parquet files.

- **Forecasts:** the *Focus* market expectations survey, annual targets (<a href="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/aplicacao#!/recursos">Olinda OData API</a>, `ExpectativasMercadoAnuais` and `ExpectativasMercadoTop5Anuais`).
- **Outcomes and benchmarks:** time series from the <a href="https://www3.bcb.gov.br/sgspub/">SGS</a>.

```js
Inputs.table(meta.indicators.map((d) => ({indicator: d.name, outcome: d.actualLabel, naive: d.naiveLabel, latest: d.lastSurvey})), {
  header: {indicator: "Indicator", outcome: "Scored against", naive: "Naive benchmark", latest: "Latest survey"},
  layout: "auto",
  select: false
})
```

## Definitions

- **Consensus:** the Focus median over all forecasts submitted in the last 30 days (`baseCalculo = 0`), which is the headline Focus number.
- **Horizon:** months from the survey month to December of the target year. A January forecast for the same year has horizon 11; December, 0. GDP keeps being surveyed after the year ends, until IBGE publishes it in March, which gives small negative horizons.
- **Sampling:** the forecast map, the accuracy statistics and `monthly.parquet` use the last survey of each month; the weekly chart uses the last survey of each week.
- **Error** = forecast − actual. Negative: the market forecast too low.
- **"One year ahead"** = the consensus in December of the previous year (horizon 12).

## Benchmarks

- **Naive guess** (all indicators), computed *point in time*, using only what was already public on each survey date:
  - IPCA: the last published 12-month IPCA (IBGE releases each month around the 10th of the next).
  - Selic: the target in force that day.
  - Dollar: the previous day's PTAX.
  - GDP: the last published annual growth (released in early March).
- **Official target** (IPCA only): always forecast the CMN inflation target. 2003 and 2004 use the revised targets (4.0% and 5.5%) that replaced the original ones in 2002–03.
- **Top 5:** the consensus of the five institutions the BCB ranks as most accurate (medium-term ranking). It starts later than the full survey, so it's compared with the consensus **on the same years and horizons** only.

## Caveats

```js
const notes = meta.indicators.flatMap((d) => d.notes.map((n) => ({name: d.name, note: n})));
```

<ul>${notes.map((d) => html`<li><strong>${d.name}:</strong> ${d.note}</li>`)}</ul>

- **IPCA outcomes** are compounded from the 12 monthly releases (series 433), not read from a pre-computed annual series.
- **Selic outcomes** are the Copom target on 31 December (series 432).
- **Dollar outcomes:** in years like 2016 the last forecast (3.35) matches the December average (3.35), not the 31 December rate (3.26), so the survey answer is treated as a December average.

<p class="muted">Data generated ${new Date(meta.generatedAt).toLocaleString("en", {dateStyle: "medium", timeStyle: "short"})}. Not affiliated with the Banco Central do Brasil.</p>
