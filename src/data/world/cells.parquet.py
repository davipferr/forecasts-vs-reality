"""Every IMF WEO forecast since 1990: one row per country × indicator × target year × edition.

``h`` = months from the edition to December of the target year (April editions
have h = 8, 20, 32...; October ones h = 2, 14, 26...). ``actual`` is the value
published in the October edition of the following year; ``naive`` is last
year's value as published in the same edition. Errors are forecast − actual.
Values are rounded to 3 decimals (the WEO publishes 1–3).
"""

import polars as pl

from pipeline import frames
from pipeline.io import emit_parquet

v = ["forecast", "actual", "naive"]
emit_parquet(frames.imf_cells().select("iso3", "indicator", "target", "h", *v).with_columns(pl.col(v).round(3)))
