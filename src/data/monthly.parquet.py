"""One row per indicator × target year × horizon (last survey of each month), scored.

Errors are forecast − actual (negative = forecast too low). Benchmarks:
``naive`` is the latest value already published on the survey date, ``goal``
the official inflation target (IPCA only), ``top5`` the Top 5 consensus.
Years whose outcome isn't known yet have null ``actual`` and errors.
"""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.monthly())
