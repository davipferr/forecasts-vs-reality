// See https://observablehq.com/framework/config for documentation.
export default {
  title: "Forecasts vs. Reality",
  root: "src",
  lang: "en",
  pages: [
    {name: "Forecast map", path: "/map"},
    {name: "One year in detail", path: "/year"},
    {name: "Accuracy by horizon", path: "/accuracy"},
    {name: "SQL console", path: "/sql"},
    {name: "About the data", path: "/about"}
  ],
  head: '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">',
  theme: ["air", "near-midnight", "alt", "wide"],
  footer: "Data: Banco Central do Brasil (Focus survey via Olinda, time series via SGS). Processed at build time with Polars. Not affiliated with the BCB.",
  toc: true,
  search: true,
  // Python loaders run inside the uv-managed environment, so `import pipeline`
  // works and nobody needs a global Python setup. `-X utf8` keeps stderr logs
  // with accents ("Câmbio") from crashing on Windows consoles.
  interpreters: {
    ".py": ["uv", "run", "--quiet", "python", "-X", "utf8"]
  }
};
