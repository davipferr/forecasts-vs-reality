# Forecasts vs. Reality

**How good are forecasters at seeing the future?** Four of them, each scored against what actually happened and
against the simplest forecast of all, "nothing changes":

| Section | Forecaster | Data (all keyless) |
|---|---|---|
| **Brazil** | The Banco Central's weekly [Focus survey](https://www.bcb.gov.br/publicacoes/focus) since 2000: IPCA, Selic, GDP, the dollar | BCB Olinda (Focus) and SGS (outcomes) |
| **World** | Every IMF *World Economic Outlook* since 1990, ~190 countries: GDP growth, inflation, current account | [MFPD panel](https://data.mendeley.com/datasets/8dt6xpp6x4) on Mendeley Data (a copy of the IMF's historical WEO forecasts) |
| **United States** | The Philadelphia Fed's [Survey of Professional Forecasters](https://www.philadelphiafed.org/surveys-and-data/real-time-data-research/survey-of-professional-forecasters) since 1981: CPI, GDP, unemployment, T-bill, 10-year | SPF medians; Philadelphia Fed real-time data (outcomes, benchmark); Treasury's daily yield curve |
| **Bond market** | Forward rates as forecasts of future rates; the term premium; the inverted yield curve as a recession signal | Fed Board zero-coupon curve (Gürkaynak–Sack–Wright); NY Fed ACM term premium; NBER recession dates; Treasury |

A static data site built with a Python pipeline (**httpx + Polars**) and **Observable Framework** (Observable Plot for
charts, DuckDB-WASM for in-browser SQL), the same stack as `public-data-explorer`.

Every download happens **at build time** in Framework data loaders. The browser only downloads pre-scored
Parquet/JSON files (about 2 MB in all, half of it the IMF's 240,000 forecasts).

| Section | Pages |
|---|---|
| Home | One headline per section, and how everything is scored |
| Brazil | Overview · Forecast map (target year × months ahead, coloured by the miss) · One year in detail (the weekly consensus, Top 5, benchmarks) · Accuracy by horizon |
| World | World map (bias or typical miss per country) · One country (forecast map, IMF vs. Focus for Brazil's GDP) · Optimism and emerging markets |
| United States | Overview · Forecast map · Accuracy by horizon (vs. "no change") |
| Bond market | Do forward rates predict? (forward paths vs. realised rates, bias by horizon, Fama–Bliss regression, term premium) · Yield curve and recessions (hits, lead times, false alarms) |
| Tools | SQL console over every table · About the data |

## What the data says (as of the latest build)

- **Brazil, IPCA:** one year ahead, the Focus consensus **under-forecast inflation in 16 of 25 years**. On the
  dollar it's no more accurate than "the rate stays where it is".
- **IMF:** one year ahead, **56 % of growth forecasts were too optimistic**. Emerging and developing economies are
  harder to forecast (typical miss 1.5 pp vs 1.1 pp for advanced ones); the IMF beats "same as last year" 62 % of
  the time. For Brazil's GDP the local Focus consensus beats the IMF at most horizons.
- **US forecasters** beat "no change" on CPI, GDP and unemployment, but **not on interest rates**: a year ahead,
  "no change" was closer for the 10-year yield in 21 of 33 years.
- **Bond market:** since 1990, forward rates overshot the 1-year rate that came by about 0.5 pp one year ahead and
  1.3 pp three years ahead: mostly **term premium**. The 10y − 1y curve inverted before all **7 recessions since
  1971**, with 6–22 months' warning, and gave **one false alarm** (2022–24).

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/) and Node.js ≥ 18.

```bash
uv sync          # Python env (httpx, polars, fastexcel, pytest)
npm install      # Observable Framework
npm run dev      # http://127.0.0.1:3000; loaders run on first visit to each page
npm run build    # static site in dist/
```

No API key is needed anywhere. The first build downloads about 65 MB (cached in `data_cache/`, git-ignored). Most of
it is quick, except Treasury's yield-curve files: one CSV per year since 1990 at ~20 s each, so **the first build
takes about 15 minutes**. Past years are then cached forever; later builds only refetch the current and previous year.

## How it's organised

```
pipeline/            Python package
  http.py            cached GET (one shared connection) with retries; checks each body is the expected format
                     (JSON, xlsx, xls, CSV), so an HTML bot wall answered with 200 is retried, never cached
  schema.py          fails fast with a clear message when a source renames a field or returns nothing
  frames.py          cleaned frames memoised as Parquet, keyed by a hash of the pipeline source
  io.py              stdout writers; casts int64 -> int32 so JS doesn't get BigInt
  manifest.py        data manifest (sources, row counts, headline numbers) and build-to-build comparison
  forecasts.py       horizons, sampling, scoring, stats by horizon (shared by Focus and the SPF)
  # Brazil
  bcb.py             Olinda OData (Focus) + SGS clients; daily SGS series fetched in 10-year windows
  actuals.py         outcomes, and point-in-time "what was already published" series
  indicators.py      the four Focus indicators: Focus name, outcome, labels, CMN targets
  # World
  imf.py             MFPD workbooks -> scored forecasts; country / group / year statistics (medians)
  countries.py       IMF country codes -> ISO codes (for the map) and WEO groups
  # United States
  spf.py             SPF medians; Philadelphia Fed real-time vintages (outcomes, naive benchmark)
  treasury.py        Treasury daily par yield curve, one CSV per year
  # Bond market
  curve.py           zero-coupon curve, forward rates, Fama–Bliss tests, ACM term premium, inversions vs. recessions
src/data/            Framework data loaders (thin; run via `uv run`): Brazil at the top level, then world/, us/, bonds/
src/components/      formatting, palette, shared forecast charts (map grid, ahead-vs-actual, horizon lines), pickers
src/style.css        theme (light/dark), typography and shared components
src/index.md         home; src/brazil/, src/world/, src/us/, src/bonds/: the sections; sql.md, about.md
tests/               offline tests for every parser, horizon, scoring rule, HTTP cache, frames and manifest
```

Brazil data files:

| File | Rows | Content |
|---|---|---|
| `forecasts.parquet` | ~27k | Weekly consensus per indicator × target year (median, spread, respondents) |
| `top5.parquet` | ~18k | Weekly Top 5 consensus |
| `monthly.parquet` | ~6k | Last survey of each month, scored: actual, error, naive / target / Top 5 benchmarks |
| `outcomes.parquet` | ~220 | What happened, plus the CMN target and tolerance (IPCA) |
| `known.parquet` | ~1k | The naive benchmark over time |
| `horizon-stats.parquet` | ~250 | Bias, MAE, RMSE by horizon, with benchmark MAEs |
| `indicators.json` | | Labels, notes, headline numbers, every year's miss one year ahead, build time |
| `manifest.json` | | Pipeline code version, download time of each source, row counts (see below) |

World, US and bond-market files:

| File | Rows | Content |
|---|---|---|
| `world/cells.parquet` | ~240k | Every WEO forecast: country × indicator × target year × edition, with outcome and naive benchmark |
| `world/country-stats.parquet` | ~7k | Per country × indicator × horizon: bias, mean and median absolute error, beats-naive share |
| `world/group-stats.parquet`, `year-stats.parquet` | | Pooled by country group (advanced, emerging, regions) and by target year |
| `us/monthly.parquet` | ~2.4k | Every SPF annual forecast, scored (same columns as the Brazil `monthly.parquet`) |
| `us/horizon-stats.parquet`, `indicators.json` | | Accuracy by horizon; headline numbers |
| `bonds/curve.parquet` | ~790 | Monthly yields, spreads, ACM decomposition, recession flag |
| `bonds/forward-tests.parquet`, `forward-stats.parquet`, `forward-paths.parquet` | | Forward rates vs. realised rates, and the Fama–Bliss regression |
| `bonds/recessions.json` | | NBER dates, inversion episodes and how each signal turned out |

## Messy-data problems handled

### Brazil

- **Olinda quirks:** the OData endpoint answers 400 to `+`-encoded spaces and 403 to `$count`.
- **SGS limits:** daily series only accept 10-year windows; closed windows are cached forever.
- **Which outcome?** The Focus FX question is answered as the **December average** rate, not the 31 December rate.
  In years where the two differ, the last forecasts sit on the average (2016: forecast 3.35, Dec. average 3.35,
  31 Dec. 3.26).
- **No look-ahead:** the naive benchmark only uses data already public on each survey date: the IPCA released
  around the 10th of the next month, the previous day's PTAX, and the annual GDP released in early March.
- **Different sample lengths:** the Top 5 series starts in late 2001, so it's compared with the consensus on the
  same target years and horizons only, not against a full sample that includes the 2002 miss it never faced.
- **Revisions:** GDP outcomes are today's revised figures, not the first release the market saw (noted on the site).
- **Changing targets:** the CMN revised the 2003 and 2004 inflation targets; the revised values are used.

### World, US and bond market

- **Blocked sources:** imf.org answers scripted downloads with 403, so the IMF history comes from the MFPD copy on
  Mendeley Data; FRED and the Fed's old Data Download Program (being retired) aren't used. Treasury refuses a
  single all-years request, so its curve is fetched one year at a time.
- **No look-ahead, again:** the SPF's naive benchmark uses the Philadelphia Fed's real-time vintages (the data as
  published in the survey's own quarter); the IMF's uses last year's value as published in the same edition.
- **Outcomes as first settled:** IMF outcomes are the October estimate of the following year; SPF outcomes the
  real-time vintage of August of the following year.
- **Growth from levels:** the SPF forecasts GDP *levels*; growth is computed against last year's level as published
  at the survey date, so base-year changes never mix.
- **Short real-time CPI history:** CPI vintages start in 1994; earlier surveys use the first vintage, cut at what
  had been published (CPI is only revised through seasonal factors).
- **Hyperinflations:** cross-country statistics use medians, so Venezuela or Zimbabwe can't decide a region's average.
- **Overlapping observations:** monthly forward-rate tests overlap, so their regressions are descriptive, not tests.

## Refreshing data

Framework caches each loader's output in `src/.observablehq/cache` and only reruns a loader when its own file
changes. The memoised frames in `data_cache/frames` are keyed by a hash of the `pipeline/` source, so they rebuild
automatically after any code change (also in CI, where `data_cache/` is restored from the previous run).
Framework's own loader cache doesn't see `pipeline/` changes, though: locally, run `npm run clean` to force the
loaders to rerun (it keeps raw downloads). Raw API responses expire after 12 hours, except the closed 10-year SGS
windows, which never change and are kept forever.

## Data manifest

Each build writes `manifest.json`: the pipeline code version, the commit, when each API response was downloaded,
row counts per table and indicator, and the headline numbers. `npm run build` copies it to a stable path,
`dist/manifest.json`, so it is served at `<site>/manifest.json`.

In CI, before deploying, the workflow downloads the live manifest and runs

```bash
uv run python -m pipeline.manifest compare previous-manifest.json dist/manifest.json
```

The changed metrics go to the job summary. Row counts that drop by more than 10 %, counts that disappear (e.g. a
whole indicator) and removed output columns become warnings; changes in the headline numbers (e.g. after an IBGE
GDP revision) are listed but not flagged. Add `--strict` in the workflow to block the deploy on warnings.

## Deploying

`.github/workflows/deploy.yml` runs the tests, builds the site and publishes it to GitHub Pages on every push to
`main`, every Monday after the Focus survey is released, and on demand. `data_cache/` is restored between runs, so
only the first run pays for the slow Treasury downloads. Enable it once under
*Settings → Pages → Source: GitHub Actions*.

## Tests

```bash
uv run python -m pytest
```
