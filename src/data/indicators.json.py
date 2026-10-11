"""Indicator metadata, headline numbers (one year ahead) and build info."""

from datetime import datetime, timezone

from pipeline import forecasts, frames
from pipeline.indicators import INDICATORS
from pipeline.io import emit_json

daily = frames.focus_daily()
m = frames.monthly()
out = []
for ind in INDICATORS:
    last = daily.filter(indicator=ind.id)["date"].max()
    out.append(ind.meta() | {"lastSurvey": last.isoformat(), "headline": forecasts.headline(m.filter(indicator=ind.id))})

emit_json({"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "indicators": out})
