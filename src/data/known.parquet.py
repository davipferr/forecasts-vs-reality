"""The naive benchmark over time: the latest published value, sampled monthly."""

import polars as pl

from pipeline import frames
from pipeline.io import emit_parquet

df = (
    frames.known()
    .filter(pl.col("available").dt.year() >= 1999)
    .sort("available")
    .group_by("indicator", pl.col("available").dt.truncate("1mo").alias("month"))
    .agg(pl.col("available").last().alias("date"), pl.col("value").last())
    .drop("month")
    .sort("indicator", "date")
)
emit_parquet(df)
