"""Per country set (all, adv, emde) × indicator × target year, for the four shortest horizons:
the median miss and the share of countries over-forecast, year by year."""

from pipeline import frames, imf
from pipeline.io import emit_parquet

emit_parquet(imf.year_stats(frames.imf_cells()))
