"""IMF countries and aggregates: ISO codes (``iso_num`` matches world-atlas shapes), name and WEO group."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.imf_names())
