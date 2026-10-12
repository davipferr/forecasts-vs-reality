"""Indicator metadata, headline numbers (one year ahead) and build info.

``yearAhead`` is every completed year's one-year-ahead miss, for the overview's mini charts.
"""

from datetime import datetime, timezone

import polars as pl

from pipeline import forecasts, frames
from pipeline.indicators import INDICATORS
from pipeline.io import emit_json

daily = frames.focus_daily()
m = frames.monthly()
out = []
for ind in INDICATORS:
    last = daily.filter(indicator=ind.id)["date"].max()
    cells = m.filter(indicator=ind.id)
    year_ahead = cells.filter(pl.col("h") == 12).drop_nulls("err").sort("target")
    out.append(
        ind.meta()
        | {
            "lastSurvey": last.isoformat(),
            "headline": forecasts.headline(cells),
            "yearAhead": [{"year": y, "err": round(e, 4)} for y, e in year_ahead.select("target", "err").iter_rows()],
        }
    )

emit_json({"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "indicators": out})
