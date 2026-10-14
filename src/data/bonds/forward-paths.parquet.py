"""The forward path every January: for each k = 0..9, the 1-year rate the curve implied for k years later
(``date`` = when that rate would start). The "hairy chart" of forward rates vs. what happened."""

import polars as pl

from pipeline import curve, frames
from pipeline.io import emit_parquet

emit_parquet(curve.forward_paths(frames.month_end_curve()).with_columns(pl.col("forward").round(4)))
