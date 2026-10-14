"""SPF indicator metadata and headline numbers one year ahead (the November survey for the next year, h = 13)."""

from datetime import datetime, timezone

import polars as pl

from pipeline import forecasts, frames, spf
from pipeline.io import emit_json

H = 13
m = frames.spf_monthly()
out = []
for ind in spf.INDICATORS:
    cells = m.filter(indicator=ind.id)
    ahead = cells.filter(pl.col("h") == H).drop_nulls("err").sort("target")
    out.append(
        {
            "id": ind.id,
            "name": ind.name,
            "short": ind.short,
            "unit": ind.unit,
            "actualLabel": ind.actual_label,
            "naiveLabel": ind.naive_label,
            "notes": ind.notes,
            "hasGoal": False,
            "hasTop5": False,
            "lastSurvey": cells["date"].max().isoformat(),
            "headline": forecasts.headline(cells, h=H),
            "yearAhead": [{"year": y, "err": round(e, 4)} for y, e in ahead.select("target", "err").iter_rows()],
        }
    )

emit_json({"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "h": H, "indicators": out})
