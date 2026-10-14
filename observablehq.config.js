// See https://observablehq.com/framework/config for documentation.
export default {
  title: "Forecasts vs. Reality",
  root: "src",
  lang: "en",
  pages: [
    {
      name: "Brazil: the Focus survey",
      pages: [
        {name: "Overview", path: "/brazil/"},
        {name: "Forecast map", path: "/brazil/map"},
        {name: "One year in detail", path: "/brazil/year"},
        {name: "Accuracy by horizon", path: "/brazil/accuracy"}
      ]
    },
    {
      name: "World: the IMF",
      pages: [
        {name: "World map", path: "/world/"},
        {name: "One country", path: "/world/country"},
        {name: "Optimism and emerging markets", path: "/world/groups"}
      ]
    },
    {
      name: "United States: professional forecasters",
      pages: [
        {name: "Overview", path: "/us/"},
        {name: "Forecast map", path: "/us/map"},
        {name: "Accuracy by horizon", path: "/us/accuracy"}
      ]
    },
    {
      name: "Bond market",
      pages: [
        {name: "Do forward rates predict?", path: "/bonds/"},
        {name: "Yield curve and recessions", path: "/bonds/recessions"}
      ]
    },
    {name: "SQL console", path: "/sql"},
    {name: "About the data", path: "/about"}
  ],
  head: [
    '<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🎯</text></svg>">',
    '<link rel="preconnect" href="https://fonts.googleapis.com">',
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>',
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Source+Serif+4:opsz,wght@8..60,600;8..60,700&display=swap">'
  ].join("\n"),
  // Theme imports (light/dark) + typography live in src/style.css.
  style: "style.css",
  footer: "Data: Banco Central do Brasil, IMF World Economic Outlook (via the MFPD panel on Mendeley Data), Federal Reserve Bank of Philadelphia, Federal Reserve Board, Federal Reserve Bank of New York, US Treasury, NBER. Processed at build time with Polars. Not affiliated with any of them.",
  toc: true,
  search: true,
  // Python loaders run inside the uv-managed environment, so `import pipeline`
  // works and nobody needs a global Python setup. `-X utf8` keeps stderr logs
  // with accents ("Câmbio") from crashing on Windows consoles.
  interpreters: {
    ".py": ["uv", "run", "--quiet", "python", "-X", "utf8"]
  }
};
