"""Per country × indicator × horizon, over completed years: bias, mean and median
absolute error, the naive benchmark's errors, and the share of years the IMF was
closer than "same as last year" (``beat_naive``) or too high (``over``)."""

from pipeline import frames, imf
from pipeline.io import emit_parquet

emit_parquet(imf.country_stats(frames.imf_cells()))
