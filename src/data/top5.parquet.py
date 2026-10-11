"""Weekly consensus of the Focus "Top 5" (medium-term ranking): the five most accurate forecasters."""

from pipeline import forecasts, frames
from pipeline.io import emit_parquet

df = forecasts.with_horizon(forecasts.weekly(frames.top5_daily()))
emit_parquet(df.select("indicator", "target", "date", "h", "median"))
