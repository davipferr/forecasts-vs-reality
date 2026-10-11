import {diff, lowerFirst, value} from "./format.js";

/** Relative difference below which two errors count as "about the same". */
const TIE = 0.05;

function compare(a, b) {
  const rel = (a - b) / Math.max(b, 1e-9);
  return rel < -TIE ? "better" : rel > TIE ? "worse" : "same";
}

/**
 * Plain-English findings for one indicator, all computed from its own numbers.
 * Returns [{stat, text}] for the headline cards.
 */
export function insights(ind, stats) {
  const h = ind.headline;
  if (!h?.years) return [];
  const u = ind.unit;
  const d = (x) => diff(x, u, false);
  const naive = lowerFirst(ind.naiveLabel);
  const out = [];

  out.push({stat: d(h.mae), text: `Average miss of the consensus made in December for the next year, ${h.first}–${h.last}.`});

  const low = h.under >= h.over;
  out.push({
    stat: `${low ? h.under : h.over} of ${h.years}`,
    text: `years the forecast a year ahead was too ${low ? "low" : "high"}. On average it was ${d(h.bias)} too ${h.bias < 0 ? "low" : "high"}.`
  });

  const w = h.worst;
  out.push({stat: String(w.year), text: `Biggest miss: ${value(w.forecast, u)} expected a year ahead, ${value(w.actual, u)} in reality.`});

  if (h.naiveMae != null) {
    const v = compare(h.mae, h.naiveMae);
    const tail =
      v === "better"
        ? `: ${d(h.mae)} vs ${d(h.naiveMae)} average miss.`
        : v === "same"
          ? `, and on average it's no more accurate: ${d(h.mae)} vs ${d(h.naiveMae)}.`
          : `, which is more accurate on average: ${d(h.naiveMae)} vs ${d(h.mae)}.`;
    out.push({stat: `${h.beatNaive} of ${h.years}`, text: `years the consensus beat the naive guess (${naive})${tail}`});
  }

  const far = stats.find((s) => s.h === 36);
  if (far?.goal_mae != null) {
    const v = compare(far.goal_mae, far.mae);
    out.push({
      stat: "3 years",
      text:
        v === "better"
          ? `ahead, simply forecasting the official inflation target misses by less than the market does (${d(far.goal_mae)} vs ${d(far.mae)}).`
          : v === "same"
            ? `ahead, simply forecasting the official inflation target is about as accurate as the market (${d(far.goal_mae)} vs ${d(far.mae)}).`
            : `ahead, the market beats simply forecasting the official target (${d(far.mae)} vs ${d(far.goal_mae)}).`
    });
  }

  const t5 = stats.find((s) => s.h === 12 && s.t5_mae != null && s.cons_t5_mae != null);
  if (t5) {
    const v = compare(t5.t5_mae, t5.cons_t5_mae);
    const verb = v === "better" ? "did better" : v === "same" ? "were no better" : "did worse";
    out.push({
      stat: "Top 5",
      text: `The five forecasters ranked most accurate ${verb} a year ahead: ${d(t5.t5_mae)} vs ${d(t5.cons_t5_mae)} for everyone, same years.`
    });
  }
  return out;
}
