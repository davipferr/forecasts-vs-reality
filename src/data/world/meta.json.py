"""IMF section metadata: indicators, groups, data version."""

from datetime import datetime, timezone

from pipeline import countries, frames, imf
from pipeline.io import emit_json

cells = frames.imf_cells()
wb = imf.files()
emit_json(
    {
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "indicators": [
            {"id": v.id, "name": v.name, "short": v.short, "unit": v.unit, "note": v.notes, "optimistic": imf.OPTIMISTIC.get(v.id)}
            for v in imf.VARIABLES
        ],
        "regions": countries.REGIONS,
        "firstEdition": int(cells["date"].min().year),
        "lastEdition": cells["date"].max().isoformat(),
        "lastScored": int(cells.drop_nulls("actual")["target"].max()),
        "mfpdVersion": wb["forecasts"].get("version"),
        "files": {k: f.get("filename") for k, f in wb.items()},
    }
)
