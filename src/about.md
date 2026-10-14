---
title: About the data
---

# About the data

```js
const meta = await FileAttachment("data/indicators.json").json();
const world = await FileAttachment("data/world/meta.json").json();
const us = await FileAttachment("data/us/indicators.json").json();
```

Every number on this site is computed at build time by Python data loaders (httpx + Polars) from public files that need **no API key**. The browser only downloads the resulting Parquet and JSON files.

## Brazil: the Focus survey

From the **Banco Central do Brasil**:

- **Forecasts:** the *Focus* market expectations survey, annual targets (<a href="https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/aplicacao#!/recursos">Olinda OData API</a>, `ExpectativasMercadoAnuais` and `ExpectativasMercadoTop5Anuais`).
- **Outcomes and benchmarks:** time series from the <a href="https://www3.bcb.gov.br/sgspub/">SGS</a>.

```js
Inputs.table(meta.indicators.map((d) => ({indicator: d.name, outcome: d.actualLabel, naive: d.naiveLabel, latest: d.lastSurvey})), {
  header: {indicator: "Indicator", outcome: "Scored against", naive: "Naive benchmark", latest: "Latest survey"},
  layout: "auto",
  select: false
})
```

### Definitions

- **Consensus:** the Focus median over all forecasts submitted in the last 30 days (`baseCalculo = 0`), which is the headline Focus number.
- **Horizon:** months from the survey month to December of the target year. A January forecast for the same year has horizon 11; December, 0. GDP keeps being surveyed after the year ends, until IBGE publishes it in March, which gives small negative horizons.
- **Sampling:** the forecast map, the accuracy statistics and `monthly.parquet` use the last survey of each month; the weekly chart uses the last survey of each week.
- **Error** = forecast − actual. Negative: the market forecast too low.
- **"One year ahead"** = the consensus in December of the previous year (horizon 12).

### Benchmarks

- **Naive guess** (all indicators), computed *point in time*, using only what was already public on each survey date:
  - IPCA: the last published 12-month IPCA (IBGE releases each month around the 10th of the next).
  - Selic: the target in force that day.
  - Dollar: the previous day's PTAX.
  - GDP: the last published annual growth (released in early March).
- **Official target** (IPCA only): always forecast the CMN inflation target. 2003 and 2004 use the revised targets (4.0% and 5.5%) that replaced the original ones in 2002–03.
- **Top 5:** the consensus of the five institutions the BCB ranks as most accurate (medium-term ranking). It starts later than the full survey, so it's compared with the consensus **on the same years and horizons** only.

### Caveats

```js
const notes = meta.indicators.flatMap((d) => d.notes.map((n) => ({name: d.name, note: n})));
```

<ul>${notes.map((d) => html`<li><strong>${d.name}:</strong> ${d.note}</li>`)}</ul>

- **IPCA outcomes** are compounded from the 12 monthly releases (series 433), not read from a pre-computed annual series.
- **Selic outcomes** are the Copom target on 31 December (series 432).
- **Dollar outcomes:** in years like 2016 the last forecast (3.35) matches the December average (3.35), not the 31 December rate (3.26), so the survey answer is treated as a December average.

## World: the IMF

- **Forecasts:** every April and October *World Economic Outlook* since 1990, for real GDP growth, CPI inflation and the current account, from the <a href="https://data.mendeley.com/datasets/8dt6xpp6x4">IMF WEO Macroeconomic Forecasts Panel Dataset</a> (MFPD, N. Echcharfi, CC BY 4.0, version ${world.mfpdVersion}), a reshaped copy of the IMF's own historical forecast database. It's used because imf.org refuses scripted downloads and the IMF's open API keeps only the latest editions.
- **Outcome:** the value published in the October WEO of the following year, the convention of the IMF's own forecast evaluations. The latest scored year is ${world.lastScored}.
- **Naive benchmark:** "same as last year", using last year's value as published in that same edition.
- **Horizon:** months from the edition to December of the target year: 2 for October of the same year, 8 for April, 14 for October of the year before, and so on.
- **Groups:** the WEO's current classification (advanced economies, and five regions of emerging and developing economies), applied to every year.
- **Caveats:** inflation is the annual average, so it isn't comparable with Focus's December-on-December IPCA. A few hyperinflations make averages meaningless across countries, so the group statistics use medians. Some countries have gaps (the IMF stops publishing forecasts during wars or data disputes), and the early-1990s forecasts for the former Soviet Union include placeholder zeros and implausible values, kept as published: the medians limit their weight.

## United States: professional forecasters

- **Forecasts:** the median of the Federal Reserve Bank of Philadelphia's <a href="https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters">Survey of Professional Forecasters</a> (<code>medianlevel.xlsx</code>), annual forecasts for the current year and up to three years ahead.
- **Outcomes and naive benchmark** for GDP, CPI and unemployment: the bank's <a href="https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/real-time-data-set-full-time-series-history">Real-Time Data Set for Macroeconomists</a>, which keeps every quarterly vintage of each series. The outcome of year T is the value as published in August of T+1; the benchmark is the latest value published before the survey.
- **Interest rates:** <a href="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve">Treasury's daily par yield curve</a> (from 1990), averaged over each year; the benchmark is the yield the day before the survey.
- **Survey dates** are taken as the 15th of the middle month of each quarter, close to the response deadline.

```js
Inputs.table(us.indicators.map((d) => ({indicator: d.name, outcome: d.actualLabel, naive: d.naiveLabel, notes: d.notes.join(" ")})), {
  header: {indicator: "Indicator", outcome: "Scored against", naive: "Naive benchmark", notes: "Notes"},
  layout: "auto",
  select: false
})
```

## The bond market

- **Yield curve:** Gürkaynak, Sack and Wright's <a href="https://www.federalreserve.gov/data/nominal-yield-curve.htm">zero-coupon Treasury curve</a> (Federal Reserve Board), daily since 1961, sampled at month ends. 1-year forward rates are computed from it as f(k) = (k+1)·y(k+1) − k·y(k) (continuous compounding).
- **Term premium:** Adrian, Crump and Moench's <a href="https://www.newyorkfed.org/research/data_indicators/term-premia-tabs">decomposition of the 10-year yield</a> (New York Fed), a model estimate.
- **Recessions:** <a href="https://www.nber.org/research/data/us-business-cycle-expansions-and-contractions">NBER business-cycle dates</a>.
- **Spreads:** monthly averages of the 10-year minus the 1-year zero-coupon yield (since 1971), and of Treasury's 10-year minus 3-month yields (since 1990).

## Data version

Every build publishes a manifest with the pipeline code version, when each API response was downloaded and the row counts of every table. It is also served at a fixed address, `/manifest.json`, so each build can be compared with the previous one before it goes live.

```js
const manifest = await FileAttachment("data/manifest.json").json();
```

<p class="muted">Pipeline code: <code>${manifest.pipeline_code}</code>${manifest.commit ? html` · commit <a href=${`https://github.com/davipferr/inflation-forecasts-vs-reality/commit/${manifest.commit}`}><code>${manifest.commit.slice(0, 7)}</code></a>` : ""}.</p>

```js
Inputs.table(manifest.sources, {
  columns: ["name", "downloaded_at"],
  header: {name: "Source", downloaded_at: "Downloaded"},
  format: {
    name: (d, i, data) => html`<a href=${data[i].url}>${d}</a>`,
    downloaded_at: (d) => (d ? new Date(d).toLocaleString("en", {dateStyle: "medium", timeStyle: "short"}) : "—")
  },
  layout: "auto",
  select: false,
  rows: 20
})
```

<p class="muted">Data generated ${new Date(meta.generatedAt).toLocaleString("en", {dateStyle: "medium", timeStyle: "short"})}. Not affiliated with any of the institutions above.</p>
