"""US Treasury daily par yield curve (constant-maturity yields), 1990 to date.

One CSV per year from home.treasury.gov. The columns change over time (the
1-month yield starts in 2001, 2-month in 2018, 4-month in 2022), so only the
maturities the pipeline uses are read, each when present. Past years never
change and are cached forever; the current year is refreshed every 12 hours.
"""

from __future__ import annotations

import io
from datetime import date, timedelta

import polars as pl

from .http import fetch
from .schema import require_columns

URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all"
FIRST_YEAR = 1990
# Treasury column -> our name.
COLUMNS = {"3 Mo": "m3", "1 Yr": "y1", "2 Yr": "y2", "10 Yr": "y10"}


def request(year: int) -> tuple[str, dict]:
    return URL.format(year=year), {"type": "daily_treasury_yield_curve", "field_tdr_date_value": year, "page": "", "_format": "csv"}


def parse(data: bytes, year: int) -> pl.DataFrame:
    df = pl.read_csv(io.BytesIO(data), infer_schema_length=0)
    df = require_columns(df, ["Date", "3 Mo", "10 Yr"], f"Treasury yield curve {year}")
    return df.select(
        pl.col("Date").str.to_date("%m/%d/%Y").alias("date"),
        *(pl.col(src).cast(pl.Float64, strict=False).alias(dst) for src, dst in COLUMNS.items() if src in df.columns),
    )


def daily(today: date | None = None) -> pl.DataFrame:
    """``date, m3, y1, y2, y10`` (percent), every business day since 1990."""
    today = today or date.today()
    parts = []
    for year in range(FIRST_YEAR, today.year + 1):
        url, params = request(year)
        max_age = None if year < today.year - 1 else timedelta(hours=12)
        parts.append(parse(fetch(url, params=params, max_age=max_age, fmt="csv"), year))
    return pl.concat(parts, how="diagonal_relaxed").sort("date")


def annual_average(series: pl.DataFrame, today: date | None = None) -> pl.DataFrame:
    """``date, value`` -> ``target, actual``: the average of each completed calendar year."""
    today = today or date.today()
    return (
        series.group_by(pl.col("date").dt.year().cast(pl.Int32).alias("target"))
        .agg(pl.col("value").mean().alias("actual"))
        .filter(pl.col("target") < today.year)
        .sort("target")
    )
