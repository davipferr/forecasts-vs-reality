"""Pooled over countries and years, per country set × indicator × horizon.

``set``: all, adv (advanced economies), emde (emerging and developing), or an
EMDE region (asia, europe, latam, meca, ssa). Medians, because a few
hyperinflations would dominate means.
"""

from pipeline import frames, imf
from pipeline.io import emit_parquet

emit_parquet(imf.group_stats(frames.imf_cells()))
