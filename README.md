# Forecasts vs. Reality

**How good is the Brazilian market at seeing the future?** Every forecast in the Banco Central's weekly
[Focus survey](https://www.bcb.gov.br/publicacoes/focus) since 2000 (IPCA inflation, the Selic rate, GDP growth and
the dollar) scored against what actually happened.

A static data site built with a Python pipeline (**httpx + Polars**) and **Observable Framework** (Observable Plot for
charts, DuckDB-WASM for in-browser SQL), the same stack as `public-data-explorer`.

Every API call happens **at build time** in Framework data loaders. The browser only downloads pre-scored Parquet/JSON
files (about 370 kB).

| Page | What it shows |
|---|---|
| Overview | Headline numbers per indicator and plain-English findings, all computed from the data |
| Forecast map | Every monthly consensus as one cell: target year × months ahead, coloured by the error; plus "a year ahead vs. what happened" |
| One year in detail | The weekly consensus for one year, with forecasters' spread, Top 5, naive benchmark, official target and outcome; every year's miss one year ahead |
| Accuracy by horizon | Average miss and bias by horizon; the consensus vs. naive benchmarks and vs. the Top 5 |
| SQL console | Free-form SQL over all Parquet files with DuckDB-WASM |
| About the data | Sources, definitions, benchmarks and caveats |

## What the data says (as of the latest build)

- **IPCA:** one year ahead, the consensus **under-forecast inflation in 16 of 25 years**, by about 1 pp on average.
  Three years out, simply forecasting the official CMN target misses by less than the market does.
- **Dollar:** the consensus is **no more accurate than "the rate stays where it is"** (a classic result in
  exchange-rate forecasting).
- **GDP:** the biggest miss is 2020 (+2.3% expected in December 2019, −3.3% in reality).
- **Top 5:** the forecasters ranked most accurate are not measurably better than the consensus over the same years.

## Quick start

Requirements: [uv](https://docs.astral.sh/uv/) and Node.js ≥ 18.

```bash
uv sync          # Python env (httpx, polars, pytest)
npm install      # Observable Framework
npm run dev      # http://127.0.0.1:3000; loaders run on first visit to each page
npm run build    # static site in dist/
```

No API key is needed: the Olinda and SGS APIs are open. The first build downloads about 30 MB of JSON from the
Banco Central (cached in `data_cache/`, git-ignored) and takes under a minute.

## How it's organised

```
pipeline/            Python package
  http.py            cached GET (one shared connection) with retries (Olinda needs %20, not "+", for spaces)
  schema.py          fails fast with a clear message when an API renames a field or returns nothing
  bcb.py             Olinda OData (Focus) + SGS clients; daily SGS series fetched in 10-year windows
  actuals.py         outcomes, and point-in-time "what was already published" series
  indicators.py      the four indicators: Focus name, outcome, labels, CMN targets
  forecasts.py       horizons, weekly/monthly sampling, scoring, stats by horizon
  frames.py          cleaned frames memoised as Parquet, shared across loaders
  io.py              stdout writers; casts int64 -> int32 so JS doesn't get BigInt
  manifest.py        data manifest (sources, row counts, headline numbers) and build-to-build comparison
src/data/*.py        Framework data loaders (thin; run via `uv run`, see observablehq.config.js)
src/components/      formatting, palette, chart helpers (event markers, mini columns), indicator picker, insight sentences
src/style.css        theme (light/dark), typography and shared components
src/*.md             pages
tests/               offline tests for parsing, horizons, scoring, HTTP cache, frames and manifest
```

Data files:

| File | Rows | Content |
|---|---|---|
| `forecasts.parquet` | ~27k | Weekly consensus per indicator × target year (median, spread, respondents) |
| `top5.parquet` | ~18k | Weekly Top 5 consensus |
| `monthly.parquet` | ~6k | Last survey of each month, scored: actual, error, naive / target / Top 5 benchmarks |
| `outcomes.parquet` | ~220 | What happened, plus the CMN target and tolerance (IPCA) |
| `known.parquet` | ~1k | The naive benchmark over time |
| `horizon-stats.parquet` | ~250 | Bias, MAE, RMSE by horizon, with benchmark MAEs |
| `indicators.json` | | Labels, notes, headline numbers, every year's miss one year ahead, build time |
| `manifest.json` | | Pipeline code version, download time of each API response, row counts (see below) |

## Messy-data problems handled

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
`main`, every Monday after the Focus survey is released, and on demand. Enable it once under
*Settings → Pages → Source: GitHub Actions*.

## Tests

```bash
uv run python -m pytest
```
