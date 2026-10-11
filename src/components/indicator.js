import * as Inputs from "npm:@observablehq/inputs";

const KEY = "ifr-indicator";
const LABELS = {ipca: "IPCA", selic: "Selic", gdp: "GDP", fx: "Dollar"};

function remembered(ids) {
  const fromUrl = new URLSearchParams(location.search).get("i");
  if (ids.includes(fromUrl)) return fromUrl;
  try {
    const saved = localStorage.getItem(KEY);
    if (ids.includes(saved)) return saved;
  } catch {
    /* storage unavailable: fine */
  }
  return ids[0];
}

/**
 * Indicator picker shared by every page. The choice is remembered across pages
 * (localStorage) and can be linked to with `?i=fx`.
 */
export function indicatorPicker(meta) {
  const ids = meta.indicators.map((d) => d.id);
  const input = Inputs.radio(ids, {label: "Indicator", value: remembered(ids), format: (id) => LABELS[id] ?? id});
  input.addEventListener("input", () => {
    try {
      localStorage.setItem(KEY, input.value);
    } catch {
      /* ignore */
    }
    const url = new URL(location.href);
    url.searchParams.set("i", input.value);
    history.replaceState(null, "", url);
  });
  return input;
}
