"""Per sample (``all`` since 1961, ``1990`` since 1990) × horizon k: bias and MAE of forward rates and of
"no change", the share of months the forward was closer, and the Fama–Bliss regression of the realised
change in the 1-year yield on the forward − spot spread (``slope``, ``intercept``, ``r2``)."""

from pipeline import curve, frames
from pipeline.io import emit_parquet

emit_parquet(curve.forward_stats(frames.forward_tests()))
