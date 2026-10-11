"""Accuracy by horizon over completed years: bias, MAE, RMSE, and the benchmarks' MAE.

``cons_t5_mae`` is the consensus MAE on exactly the cells the Top 5 also has, so
the two are compared on the same years.
"""

import polars as pl

from pipeline import forecasts, frames
from pipeline.indicators import INDICATORS
from pipeline.io import emit_parquet

m = frames.monthly()
parts = [
    forecasts.horizon_stats(m.filter(indicator=ind.id).drop("indicator")).select(pl.lit(ind.id).alias("indicator"), pl.all())
    for ind in INDICATORS
]
emit_parquet(pl.concat(parts, how="diagonal_relaxed"))
