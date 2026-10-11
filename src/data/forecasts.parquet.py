"""Weekly Focus consensus per indicator and target year (last survey of each week).

``h`` = months from the survey month to December of the target year; ``std`` is
the dispersion across forecasters.
"""

from pipeline import forecasts, frames
from pipeline.io import emit_parquet

df = forecasts.with_horizon(forecasts.weekly(frames.focus_daily()))
emit_parquet(df.select("indicator", "target", "date", "h", "median", "mean", "std", "min", "max", "respondents"))
