"""Each month × horizon k (1–5 years): the 1-year forward rate k years ahead vs. the 1-year yield
that actually came, and the "no change" benchmark (today's 1-year yield). Errors are forecast − realised."""

import polars as pl

from pipeline import frames
from pipeline.io import emit_parquet

v = ["forward", "realised", "naive", "err", "naive_err"]
emit_parquet(frames.forward_tests().with_columns(pl.col(v).round(4)))
