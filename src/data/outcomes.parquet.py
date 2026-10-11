"""What actually happened, per indicator and year, plus the official inflation target (IPCA)."""

from pipeline import frames
from pipeline.io import emit_parquet

emit_parquet(frames.outcomes())
