import * as Plot from "npm:@observablehq/plot";

// Events that moved forecasts: presidential elections (first round) and the
// shocks behind the biggest misses. `short` is the label on narrow charts.
export const EVENTS = [
  {date: new Date(Date.UTC(2002, 9, 6)), name: "2002 election", short: "Election"},
  {date: new Date(Date.UTC(2006, 9, 1)), name: "2006 election", short: "Election"},
  {date: new Date(Date.UTC(2008, 8, 15)), name: "Lehman Brothers collapse", short: "Lehman"},
  {date: new Date(Date.UTC(2010, 9, 3)), name: "2010 election", short: "Election"},
  {date: new Date(Date.UTC(2014, 9, 5)), name: "2014 election", short: "Election"},
  {date: new Date(Date.UTC(2016, 4, 12)), name: "Rousseff suspended", short: "Impeachment"},
  {date: new Date(Date.UTC(2018, 9, 7)), name: "2018 election", short: "Election"},
  {date: new Date(Date.UTC(2020, 2, 11)), name: "COVID-19 declared a pandemic", short: "COVID-19"},
  {date: new Date(Date.UTC(2022, 1, 24)), name: "Russia invades Ukraine", short: "Ukraine"},
  {date: new Date(Date.UTC(2022, 9, 2)), name: "2022 election", short: "Election"},
  {date: new Date(Date.UTC(2026, 9, 4)), name: "2026 election", short: "Election"}
];

/**
 * Hairline + label for each event inside [start, end]. Pair with
 * `y: {insetTop: 22}` so the labels get a band of their own above the data.
 * Charts narrower than 640 px use the short labels.
 */
export function eventMarks([start, end], {width = Infinity} = {}) {
  const ev = EVENTS.filter((e) => e.date >= start && e.date <= end);
  // Labels near the right edge go on the left of their line so they aren't cut off.
  const late = (e) => e.date > +start + 0.7 * (end - start);
  const text = width < 640 ? "short" : "name";
  const label = (data, textAnchor, dx) =>
    Plot.text(data, {x: "date", text, frameAnchor: "top", textAnchor, dx, fill: "var(--theme-foreground-muted)", fontSize: 11});
  return [
    Plot.ruleX(ev, {x: "date", stroke: "currentColor", strokeOpacity: 0.35, strokeDasharray: "1 2"}),
    label(ev.filter((e) => !late(e)), "start", 4),
    label(ev.filter(late), "end", -4)
  ];
}

/**
 * Compact column chart for a stat card: no axes, a hover tooltip. `fill` is a
 * colour or a function of the datum.
 */
export function miniColumns(data, {width, x, y, fill = "currentColor", title, height = 56}) {
  return Plot.plot({
    width,
    height,
    margin: 0,
    marginTop: 2,
    marginBottom: 2,
    x: {axis: null, type: "band", padding: 0.2},
    y: {axis: null},
    marks: [
      Plot.barY(data, {x, y, fill, tip: false}),
      Plot.ruleY([0], {stroke: "currentColor", strokeOpacity: 0.3}),
      Plot.tip(data, Plot.pointerX({x, y, title}))
    ]
  });
}
