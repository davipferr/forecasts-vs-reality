"""Every SPF annual forecast (the median across forecasters), one row per indicator × target year × survey.

Same columns as the Focus ``monthly.parquet``: ``h`` = months from the survey
(mid-February, May, August, November) to December of the target year; errors
are forecast − actual; ``naive`` is the latest value published before the survey.
"""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.spf_monthly())
