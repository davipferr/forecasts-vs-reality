"""One row per month since 1961: zero-coupon Treasury yields at month end (1, 2, 5, 10 years),
the 10y − 1y spread (monthly average, Fed zero curve) and 10y − 3m spread (Treasury, since 1990),
the ACM decomposition of the 10-year yield (``rn10`` = expected short rates, ``tp10`` = term premium),
and whether the month was in an NBER recession."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.curve_monthly())
