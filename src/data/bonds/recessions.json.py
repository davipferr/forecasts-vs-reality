"""NBER recessions, yield-curve inversion episodes for two spreads, and how each signal turned out.

An inversion is a hit if a recession began within 24 months of its start, a
false alarm if none did, pending if 24 months haven't passed yet.
"""

from datetime import datetime, timezone

import polars as pl

from pipeline import curve, frames
from pipeline.io import emit_json

WINDOW = 24
m = frames.curve_monthly()
peaks = curve.recessions()
out = {"generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"), "window": WINDOW, "spreads": []}
for col, name, source in (
    ("spread_10_1", "10-year − 1-year", "Fed zero-coupon curve"),
    ("spread_10_3m", "10-year − 3-month", "Treasury constant-maturity yields"),
):
    s = m.select("month", pl.col(col).alias("value")).drop_nulls()
    first, last = s["month"].min(), s["month"].max()
    episodes, recs = curve.score_signals(curve.inversions(s), peaks, first, last, WINDOW)
    out["spreads"].append(
        {
            "id": col,
            "name": name,
            "source": source,
            "first": first.isoformat(),
            "last": last.isoformat(),
            "inverted": bool(s["value"][-1] < 0),
            "latest": s["value"][-1],
            "episodes": episodes.to_dicts(),
            "recessions": recs.to_dicts(),
        }
    )
out["nber"] = peaks.filter(pl.col("peak").dt.year() >= 1960).to_dicts()
emit_json(out)
