---
title: SQL console
---

# SQL console

The Parquet files behind every chart are loaded into **DuckDB running in your browser** (DuckDB-WASM). Nothing is sent to a server: ask your own questions.

```js
// Tables are decoded to Arrow first (parquet-wasm, the same reader the other pages
// use, so the files are already cached) and copied into DuckDB, instead of letting
// DuckDB-WASM read the Parquet files itself: its HTTP range requests break on
// GitHub Pages, which gzips .parquet responses.
const db = DuckDBClient.of({
  forecasts: FileAttachment("data/forecasts.parquet").parquet(),
  top5: FileAttachment("data/top5.parquet").parquet(),
  monthly: FileAttachment("data/monthly.parquet").parquet(),
  outcomes: FileAttachment("data/outcomes.parquet").parquet(),
  known: FileAttachment("data/known.parquet").parquet(),
  horizon_stats: FileAttachment("data/horizon-stats.parquet").parquet()
});
```

```js
const examples = new Map([
  ["Worst one-year-ahead misses, every indicator", `SELECT indicator, target, median AS forecast, actual, round(err, 2) AS miss
FROM monthly
WHERE h = 12 AND actual IS NOT NULL
ORDER BY abs(err) DESC
LIMIT 15`],
  ["Does the consensus beat the naive guess? Share of years, by indicator", `SELECT indicator,
       count(*)                                          AS years,
       sum(CASE WHEN abs(err) < abs(naive_err) THEN 1 ELSE 0 END) AS consensus_closer,
       round(avg(abs(err)), 2)                           AS consensus_mae,
       round(avg(abs(naive_err)), 2)                     AS naive_mae
FROM monthly
WHERE h = 12 AND actual IS NOT NULL
GROUP BY indicator
ORDER BY indicator`],
  ["IPCA: the year the market was closest to the official target", `SELECT target,
       median AS forecast_a_year_ahead,
       goal,
       actual,
       round(abs(median - goal), 2) AS distance_from_target
FROM monthly
WHERE indicator = 'ipca' AND h = 12 AND actual IS NOT NULL
ORDER BY distance_from_target`],
  ["Disagreement among forecasters (std) a year ahead, over time", `SELECT indicator, target, round(std, 3) AS std, respondents
FROM monthly
WHERE h = 12 AND std IS NOT NULL
ORDER BY indicator, target`],
  ["How fast the 2002 IPCA forecast moved, week by week", `SELECT date, median,
       round(median - lag(median) OVER (ORDER BY date), 2) AS weekly_change
FROM forecasts
WHERE indicator = 'ipca' AND target = 2002
ORDER BY date`]
]);
const example = view(Inputs.select(examples, {label: "Example"}));
```

```js
const query = view(Inputs.textarea({value: example, rows: 10, submit: "Run", spellcheck: false, monospace: true, width: "100%"}));
```

```js
// DuckDB returns BIGINT (e.g. count(*)) as JavaScript BigInt; convert to Number
// so formatting and charts work.
const result = await db.query(query).then(
  (r) => ({rows: Array.from(r, (row) => Object.fromEntries(Object.entries(row).map(([k, v]) => [k, typeof v === "bigint" ? Number(v) : v])))}),
  (error) => ({error})
);
```

${result.error ? html`<div class="caution"><strong>Error:</strong> <code>${result.error.message}</code></div>` : html`<p class="muted">${result.rows.length.toLocaleString("en")} rows</p>`}

```js
// Years are plain labels, not quantities: no "2,002".
result.error ? null : Inputs.table(result.rows, {rows: 20, format: {target: String}})
```

## Tables

```js
const tables = ["forecasts", "top5", "monthly", "outcomes", "known", "horizon_stats"];
const schema = await Promise.all(
  tables.map(async (t) => ({
    table: t,
    rows: Number(Array.from(await db.query(`SELECT count(*) AS n FROM ${t}`))[0].n),
    columns: Array.from(await db.query(`DESCRIBE ${t}`), (c) => `${c.column_name} (${c.column_type.toLowerCase()})`).join(", ")
  }))
);
```

```js
Inputs.table(schema, {format: {rows: (n) => n.toLocaleString("en")}, width: {table: 130, rows: 80}, layout: "auto", select: false})
```

<div class="tip">
  <code>indicator</code> is one of <code>ipca</code>, <code>selic</code>, <code>gdp</code>, <code>fx</code>. <code>h</code> is the number of months from the survey month to December of the <code>target</code> year. Errors (<code>err</code>, <code>naive_err</code>, …) are forecast − actual: negative means the forecast was too low. <code>monthly</code> keeps the last survey of each month; <code>forecasts</code> the last of each week.
</div>
