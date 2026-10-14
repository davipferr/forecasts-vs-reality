---
title: "Bond market: yield curve and recessions"
---

# Does an inverted yield curve predict recessions?

<p class="lede">Normally long-term rates sit above short-term ones. When the curve <em>inverts</em> (short rates above long ones), markets expect rates to fall, usually because they expect a slowdown. It is the most famous recession signal in economics. How often has it been right, how much warning did it give, and how many false alarms?</p>

```js
import {diff, rows, value} from "../components/format.js";
import {palette} from "../components/palette.js";

const curve = rows(await FileAttachment("../data/bonds/curve.parquet").parquet());
const rec = await FileAttachment("../data/bonds/recessions.json").json();
const pal = palette(dark);
const toDate = (s) => (s == null ? null : new Date(s));
const monthLabel = (d) => d.toLocaleDateString("en", {month: "short", year: "numeric", timeZone: "UTC"});
```

```js
const sid = view(Inputs.radio(new Map(rec.spreads.map((s) => [`${s.name} (since ${s.first.slice(0, 4)})`, s.id])), {label: "Spread", value: rec.spreads[0].id}));
```

```js
const sp = rec.spreads.find((s) => s.id === sid);
const episodes = sp.episodes.map((e) => ({...e, start: toDate(e.start), end: toDate(e.end), peak: toDate(e.peak)}));
const recessions = sp.recessions.map((r) => ({...r, peak: toDate(r.peak), signal: toDate(r.signal)}));
const hits = episodes.filter((e) => e.outcome === "hit");
const falseAlarms = episodes.filter((e) => e.outcome === "false alarm");
const pending = episodes.filter((e) => e.outcome === "pending");
const missed = recessions.filter((r) => r.signal == null);
const leads = hits.map((e) => e.lead);
const first = toDate(sp.first);
const series = curve.filter((d) => d[sid] != null).map((d) => ({month: d.month, value: d[sid]}));
const shading = rec.nber
  .map((r) => ({start: toDate(r.peak), end: toDate(r.trough)}))
  .filter((r) => r.end >= first);
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>Recessions signalled</h2>
    <span class="big">${recessions.length - missed.length} of ${recessions.length}</span>
    <p class="muted">US recessions since ${sp.first.slice(0, 4)} came while the curve was inverted or within ${rec.window} months of an inversion</p>
  </div>
  <div class="card">
    <h2>Warning time</h2>
    <span class="big">${d3.min(leads)}–${d3.max(leads)} months</span>
    <p class="muted">from the start of the inversion to the start of the recession (median ${d3.median(leads)})</p>
  </div>
  <div class="card">
    <h2>False alarms</h2>
    <span class="big">${falseAlarms.length}</span>
    <p class="muted">${falseAlarms.length ? `inversion${falseAlarms.length > 1 ? "s" : ""} with no recession within ${rec.window} months: ${falseAlarms.map((e) => monthLabel(e.start)).join(", ")}` : `every inversion was followed by a recession within ${rec.window} months`}</p>
  </div>
  <div class="card">
    <h2>Today</h2>
    <span class="big">${diff(sp.latest, "%")}</span>
    <p class="muted">${sp.inverted ? "the curve is inverted" : "the curve is not inverted"} (monthly average, ${monthLabel(toDate(sp.last))})${pending.length ? `; ${pending.length} inversion still within its ${rec.window}-month window` : ""}</p>
  </div>
</div>

<div class="card">
  <h2>The ${sp.name} spread, ${sp.first.slice(0, 4)}–${sp.last.slice(0, 4)}</h2>
  <h3>Grey bands: NBER recessions. Below the line: an inverted curve. Markers: the start of each inversion, coloured by what followed.</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 360,
    marginLeft: 44,
    x: {type: "utc", label: null},
    y: {grid: true, label: "Spread (pp)"},
    color: {domain: ["hit", "false alarm", "pending"], range: [pal.categorical[2], pal.diverging.neg, pal.naive], legend: true, tickFormat: (d) => (d === "hit" ? "Recession within 2 years" : d === "false alarm" ? "False alarm" : "Too early to tell")},
    marks: [
      Plot.rectX(shading, {x1: "start", x2: "end", fill: "var(--theme-foreground)", fillOpacity: 0.09}),
      Plot.areaY(series, {x: "month", y1: 0, y2: (d) => Math.min(d.value, 0), fill: pal.diverging.neg, fillOpacity: 0.3}),
      Plot.lineY(series, {x: "month", y: "value", stroke: pal.consensus, strokeWidth: 1.4}),
      Plot.ruleY([0]),
      Plot.dot(episodes, {x: "start", y: 0, fill: "outcome", r: 6, stroke: "var(--theme-background)", strokeWidth: 2}),
      Plot.tip(series, Plot.pointerX({x: "month", y: "value", title: (d) => `${monthLabel(d.month)}\nSpread: ${diff(d.value, "%")}`}))
    ]
  }))}
</div>

## Every inversion

```js
Inputs.table(episodes, {
  columns: ["start", "end", "months", "deepest", "outcome", "peak", "lead"],
  header: {start: "Inverted from", end: "Until", months: "Months inverted", deepest: "Deepest", outcome: "What followed", peak: "Recession began", lead: "Warning (months)"},
  format: {start: monthLabel, end: monthLabel, deepest: (v) => diff(v, "%"), peak: (d) => (d ? monthLabel(d) : "—"), lead: (v) => (v == null ? "—" : v)},
  select: false,
  layout: "auto"
})
```

## Every recession

```js
Inputs.table(recessions, {
  columns: ["peak", "signal", "lead"],
  header: {peak: "Recession began (NBER peak)", signal: "Inversion that preceded it", lead: "Months of warning"},
  format: {peak: monthLabel, signal: (d) => (d ? monthLabel(d) : "None: missed"), lead: (v) => (v == null ? "—" : v)},
  select: false,
  layout: "auto"
})
```

```js
const recent = episodes.find((e) => e.start.getUTCFullYear() === 2022);
```

<div class="note">
  <p><strong>Read with care.</strong> Seven or eight recessions is a tiny sample, and the 2019 inversion "predicted" a recession that was caused by a pandemic.${recent?.outcome === "false alarm" ? " The long 2022–24 inversion, the deepest since the early 1980s, has not been followed by a recession the NBER has dated: either the signal's first big miss in half a century, or a sign that its reading was distorted (the term premium, which pushes long rates up, had been unusually low)." : recent?.outcome === "pending" ? " The 2022 inversion is still inside its two-year window." : ""}</p>
</div>

<p class="muted small">Rules: an inversion starts with the first month whose average spread is below zero and ends after six months back above zero. It counts as a hit if a recession began within ${rec.window} months of its start. A recession counts as signalled if the curve was inverted at some point in the ${rec.window} months before it began. Recession dates: NBER Business Cycle Dating Committee. The 10y − 1y spread uses the Fed's zero-coupon curve (Gürkaynak, Sack and Wright); the 10y − 3m spread uses Treasury's constant-maturity yields.</p>
