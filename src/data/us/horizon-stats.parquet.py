"""Accuracy of the SPF by horizon over completed years: bias, MAE, RMSE, and the naive benchmark's MAE."""

import polars as pl

from pipeline import forecasts, frames, spf
from pipeline.io import emit_parquet

m = frames.spf_monthly()
parts = [
    forecasts.horizon_stats(m.filter(indicator=ind.id).drop("indicator")).select(pl.lit(ind.id).alias("indicator"), pl.all())
    for ind in spf.INDICATORS
]
emit_parquet(pl.concat(parts, how="diagonal_relaxed"))
