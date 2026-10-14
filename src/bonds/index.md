---
title: "Bond market: do forward rates predict?"
---

# Does the bond market predict future rates?

<p class="lede">The yield curve contains a forecast. If a 2-year bond pays more than two 1-year bonds in a row would be expected to, investors must expect 1-year rates to rise. That implied rate is the <em>forward rate</em>. Do forward rates predict the rates that actually come, or do they mostly contain a <em>term premium</em>, extra yield for tying money up longer?</p>

```js
import {diff, pct, rows, value} from "../components/format.js";
import {palette} from "../components/palette.js";

const curve = rows(await FileAttachment("../data/bonds/curve.parquet").parquet());
const tests = rows(await FileAttachment("../data/bonds/forward-tests.parquet").parquet());
const fstats = rows(await FileAttachment("../data/bonds/forward-stats.parquet").parquet());
const paths = rows(await FileAttachment("../data/bonds/forward-paths.parquet").parquet());
const pal = palette(dark);
const u = "%";
```

```js
const sample = view(Inputs.radio(new Map([["Since 1990", "1990"], ["Since 1961", "all"]]), {label: "Sample", value: "1990"}));
```

```js
const st = fstats.filter((d) => d.sample === sample);
const k1 = st.find((d) => d.k === 1);
const k3 = st.find((d) => d.k === 3);
const start = sample === "1990" ? new Date(Date.UTC(1990, 0, 1)) : new Date(Date.UTC(1961, 0, 1));
```

<div class="grid grid-cols-4">
  <div class="card">
    <h2>One year ahead</h2>
    <span class="big">${diff(k1.bias, u)}</span>
    <p class="muted">average gap between the forward rate and the 1-year rate a year later: forwards ran high</p>
  </div>
  <div class="card">
    <h2>Three years ahead</h2>
    <span class="big">${diff(k3.bias, u)}</span>
    <p class="muted">the further out, the bigger the gap: the signature of a term premium, not of a forecast</p>
  </div>
  <div class="card">
    <h2>Beats "no change"</h2>
    <span class="big">${pct(k1.beat_naive)}</span>
    <p class="muted">of months the 1-year-ahead forward was closer than simply assuming today's 1-year rate stays put</p>
  </div>
  <div class="card">
    <h2>Average miss, 1 year ahead</h2>
    <span class="big">${diff(k1.mae, u, false)}</span>
    <p class="muted">vs. ${diff(k1.naive_mae, u, false)} for "no change", over ${k1.n} months</p>
  </div>
</div>

## Forward paths vs. what happened

```js
const realised = curve.filter((d) => d.y1 != null && d.month >= start);
const fw = paths.filter((d) => d.month >= start);
```

<div class="card">
  <h2>The 1-year rate (thick) and the path the yield curve implied for it each January (thin)</h2>
  <h3>Each thin line starts at the 1-year yield in January and follows the forward rates for the next nine years. Lines that point above the thick one: the market expected (or priced) higher rates than came.</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 420,
    marginLeft: 44,
    x: {type: "utc", label: null},
    y: {grid: true, label: "1-year rate (%)", zero: true},
    marks: [
      Plot.lineY(fw, {x: "date", y: "forward", z: "month", stroke: pal.categorical[1], strokeWidth: 1, strokeOpacity: 0.65}),
      Plot.lineY(realised, {x: "month", y: "y1", stroke: pal.consensus, strokeWidth: 2.2}),
      Plot.ruleY([0]),
      Plot.tip(realised, Plot.pointerX({x: "month", y: "y1", title: (d) => `${d.month.toLocaleDateString("en", {month: "short", year: "numeric", timeZone: "UTC"})}\n1-year yield: ${value(d.y1, u)}`}))
    ]
  }))}
  <div class="legend">
    <span class="swatch"><i style=${`display:inline-block;width:18px;border-top:2px solid ${pal.consensus};vertical-align:middle`}></i> 1-year yield (zero-coupon, month end)</span>
    <span class="swatch"><i style=${`display:inline-block;width:18px;border-top:2px solid ${pal.categorical[1]};vertical-align:middle`}></i> Forward path implied each January</span>
  </div>
</div>

## Forecast or term premium?

<div class="grid grid-cols-2">
  <div class="card">
    <h2>Average error by horizon</h2>
    <h3>Forward rate − the 1-year rate that came. Positive at every horizon, and growing: a premium, not a forecast error that cancels out</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 300,
      marginLeft: 48,
      x: {label: "Years ahead →", ticks: [1, 2, 3, 4, 5], tickFormat: "d"},
      y: {grid: true, label: "Average error (pp)", zero: true},
      color: {domain: ["Forward rate", "No change"], range: [pal.categorical[1], pal.naive], legend: true},
      marks: [
        Plot.ruleY([0]),
        Plot.lineY(st, {x: "k", y: "bias", stroke: pal.categorical[1], strokeWidth: 2.4}),
        Plot.dot(st, {x: "k", y: "bias", fill: pal.categorical[1], r: 3.5}),
        Plot.lineY(st, {x: "k", y: "naive_bias", stroke: pal.naive, strokeWidth: 1.5}),
        Plot.dot(st, {x: "k", y: "naive_bias", fill: pal.naive, r: 3}),
        Plot.tip(st, Plot.pointerX({x: "k", y: "bias", title: (d) => `${d.k} year${d.k > 1 ? "s" : ""} ahead\nForward rate: ${diff(d.bias, u)} on average\n"No change": ${diff(d.naive_bias, u)}\n${d.n} months`}))
      ]
    }))}
  </div>
  <div class="card">
    <h2>Average miss by horizon</h2>
    <h3>Mean absolute error: forward rates vs. "no change"</h3>
    ${resize((width) => Plot.plot({
      width,
      height: 300,
      marginLeft: 48,
      x: {label: "Years ahead →", ticks: [1, 2, 3, 4, 5], tickFormat: "d"},
      y: {grid: true, label: "Average miss (pp)", zero: true},
      color: {domain: ["Forward rate", "No change"], range: [pal.categorical[1], pal.naive], legend: true},
      marks: [
        Plot.lineY(st, {x: "k", y: "mae", stroke: pal.categorical[1], strokeWidth: 2.4}),
        Plot.dot(st, {x: "k", y: "mae", fill: pal.categorical[1], r: 3.5}),
        Plot.lineY(st, {x: "k", y: "naive_mae", stroke: pal.naive, strokeWidth: 1.5}),
        Plot.dot(st, {x: "k", y: "naive_mae", fill: pal.naive, r: 3}),
        Plot.tip(st, Plot.pointerX({x: "k", y: "mae", title: (d) => `${d.k} year${d.k > 1 ? "s" : ""} ahead\nForward rate: ${diff(d.mae, u, false)}\n"No change": ${diff(d.naive_mae, u, false)}\nForward closer in ${pct(d.beat_naive)} of months`}))
      ]
    }))}
  </div>
</div>

### Do forwards at least point the right way?

A forward rate can be biased (by the term premium) and still carry information: when forwards are far above today's rate, do rates rise more? The classic test (Fama and Bliss, 1987) regresses the change that came on the forward − spot spread. A slope of **1** means forwards move one for one with what follows; **0** means they say nothing about it.

```js
const k = view(Inputs.range([1, 5], {label: "Years ahead", step: 1, value: 2}));
```

```js
const pts = tests.filter((d) => d.k === k && d.realised != null && d.month >= start).map((d) => ({...d, spread: d.forward - d.naive, change: d.realised - d.naive}));
const reg = st.find((d) => d.k === k);
```

<div class="grid grid-cols-2" style="grid-auto-rows: auto;">
  <div class="card">
    <h2>${k} year${k > 1 ? "s" : ""} ahead: the forward − spot spread vs. the change that came</h2>
    <h3>One dot per month. The line is the least-squares fit; the dashed diagonal is a perfect forecast.</h3>
    ${resize((width) => Plot.plot({
      width,
      height: Math.min(420, width * 0.85),
      marginLeft: 48,
      x: {label: "Forward − 1-year yield at the time (pp) →", grid: true},
      y: {label: "↑ Change in the 1-year yield that followed (pp)", grid: true},
      marks: [
        Plot.ruleX([0]),
        Plot.ruleY([0]),
        Plot.line([[-4, -4], [6, 6]], {stroke: "var(--theme-foreground-faint)", strokeDasharray: "4 3"}),
        Plot.dot(pts, {x: "spread", y: "change", r: 2, fill: pal.categorical[0], fillOpacity: 0.35}),
        Plot.linearRegressionY(pts, {x: "spread", y: "change", stroke: pal.categorical[1], strokeWidth: 2, ci: 0}),
        Plot.tip(pts, Plot.pointer({x: "spread", y: "change", title: (d) => `${d.month.toLocaleDateString("en", {month: "short", year: "numeric", timeZone: "UTC"})}\nForward ${value(d.forward, u)} vs. 1-year ${value(d.naive, u)}\n${k} year${k > 1 ? "s" : ""} later: ${value(d.realised, u)}`}))
      ]
    }))}
  </div>
  <div class="card">
    <h2>The regression, every horizon</h2>
    <h3>Change in the 1-year yield = intercept + slope × (forward − spot)</h3>
    ${Inputs.table(st, {
      columns: ["k", "n", "slope", "intercept", "r2"],
      header: {k: "Years ahead", n: "Months", slope: "Slope", intercept: "Intercept (pp)", r2: "R²"},
      format: {slope: (v) => v.toFixed(2), intercept: (v) => v.toFixed(2), r2: (v) => v.toFixed(2)},
      select: false,
      layout: "auto"
    })}
    <p class="muted small">Overlapping monthly observations: neighbouring months share most of the same future, so the effective sample is far smaller than the month count, and these are descriptive fits, not significance tests.</p>
    <p>${reg.slope > 0.75 ? `At ${k} year${k > 1 ? "s" : ""}, the slope is ${reg.slope.toFixed(2)}: forwards do point the right way, but the low R² (${reg.r2.toFixed(2)}) says most of the movement in rates was a surprise.` : `At ${k} year${k > 1 ? "s" : ""}, the slope is only ${reg.slope.toFixed(2)}: forward rates move much more than the rates that follow, consistent with a varying term premium.`}</p>
  </div>
</div>

## The term premium itself

```js
const acm = curve.filter((d) => d.tp10 != null && d.month >= start);
const last = acm.at(-1);
```

The New York Fed's ACM model splits the 10-year yield into the **average short rate expected over ten years** and the **term premium**. In ${last.month.toLocaleDateString("en", {month: "long", year: "numeric", timeZone: "UTC"})}, the 10-year yield of ${value(last.acm_y10, u)} was ${value(last.rn10, u)} of expected short rates plus a term premium of ${diff(last.tp10, u)}.

<div class="card">
  <h2>The 10-year yield, split into expected short rates and the term premium</h2>
  <h3>${sample === "all" ? "The premium was large in the 1970s and 1980s (inflation risk), and sank below zero in the 2010s, when bonds became a hedge" : "The premium sank below zero in the 2010s, when bonds became a hedge, and has climbed back since 2022. Pick \"Since 1961\" for the high-inflation decades"}</h3>
  ${resize((width) => Plot.plot({
    width,
    height: 340,
    marginLeft: 44,
    x: {type: "utc", label: null},
    y: {grid: true, label: "Percent"},
    color: {domain: ["10-year yield", "Expected short rates", "Term premium"], range: [pal.consensus, pal.categorical[0], pal.categorical[1]], legend: true},
    marks: [
      Plot.ruleY([0]),
      Plot.lineY(acm, {x: "month", y: "acm_y10", stroke: pal.consensus, strokeWidth: 2}),
      Plot.lineY(acm, {x: "month", y: "rn10", stroke: pal.categorical[0], strokeWidth: 1.5}),
      Plot.areaY(acm, {x: "month", y: "tp10", fill: pal.categorical[1], fillOpacity: 0.25}),
      Plot.lineY(acm, {x: "month", y: "tp10", stroke: pal.categorical[1], strokeWidth: 1.5}),
      Plot.tip(acm, Plot.pointerX({x: "month", y: "acm_y10", title: (d) => `${d.month.toLocaleDateString("en", {month: "short", year: "numeric", timeZone: "UTC"})}\n10-year yield: ${value(d.acm_y10, u)}\nExpected short rates: ${value(d.rn10, u)}\nTerm premium: ${diff(d.tp10, u)}`}))
    ]
  }))}
</div>

<p class="muted small">Yields: Gürkaynak, Sack and Wright's zero-coupon Treasury curve (Federal Reserve Board), continuously compounded, month ends; forward rates are computed from it. The "1-year rate that came" is that curve's 1-year yield k years later. Term premium: Adrian, Crump and Moench (New York Fed), a model estimate, not an observed price.</p>
