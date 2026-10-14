import * as Inputs from "npm:@observablehq/inputs";

const LABELS = {ipca: "IPCA", selic: "Selic", gdp: "GDP", fx: "Dollar"};

function remembered(ids, key, param) {
  const fromUrl = new URLSearchParams(location.search).get(param);
  if (ids.includes(fromUrl)) return fromUrl;
  try {
    const saved = localStorage.getItem(key);
    if (ids.includes(saved)) return saved;
  } catch {
    /* storage unavailable: fine */
  }
  return ids[0];
}

/**
 * Indicator picker shared by every page. The choice is remembered across the
 * pages of a section (localStorage, one `key` per section) and can be linked to
 * with `?i=fx`. Labels come from each indicator's `short` name when it has one.
 */
export function indicatorPicker(meta, {key = "ifr-indicator", label = "Indicator", param = "i"} = {}) {
  const ids = meta.indicators.map((d) => d.id);
  const short = new Map(meta.indicators.map((d) => [d.id, d.short ?? LABELS[d.id] ?? d.id]));
  const input = Inputs.radio(ids, {label, value: remembered(ids, key, param), format: (id) => short.get(id)});
  input.addEventListener("input", () => {
    try {
      localStorage.setItem(key, input.value);
    } catch {
      /* ignore */
    }
    const url = new URL(location.href);
    url.searchParams.set(param, input.value);
    history.replaceState(null, "", url);
  });
  return input;
}
