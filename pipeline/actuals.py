"""What actually happened, and what was already known on each survey date.

Every indicator returns two frames:

* ``actual``: ``target, actual``, the realised value the annual forecast is
  scored against.
* ``known``: ``available, value``, the latest published value as of
  ``available``. It is used *point-in-time* (as-of join on the survey date) for
  the naive "nothing changes" benchmark, so the benchmark never peeks at data that
  hadn't been released yet.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

from . import bcb

# SGS series codes.
IPCA_MONTHLY = 433  # IPCA, % change in the month
SELIC_TARGET = 432  # Meta Selic set by Copom, % a.a., daily
PTAX_DAILY = 1  # USD/BRL PTAX selling rate, daily
PTAX_MONTH_AVG = 3698  # USD/BRL PTAX selling rate, monthly average
GDP_ANNUAL = 7326  # Real GDP growth, % per year

# IBGE publishes month m's IPCA around the 10th of m+1.
IPCA_RELEASE_DAY = 11
# IBGE publishes the year's GDP (Q4 national accounts) in early March of the next year.
GDP_RELEASE = (3, 5)


def compound_annual(monthly: pl.DataFrame) -> pl.DataFrame:
    """Calendar-year inflation from monthly % changes; only complete years (12 months)."""
    return (
        monthly.group_by(target=pl.col("date").dt.year().cast(pl.Int32))
        .agg(
            n=pl.len(),
            actual=((1 + pl.col("value") / 100).product() - 1) * 100,
        )
        .filter(pl.col("n") == 12)
        .select("target", pl.col("actual").round(2))
        .sort("target")
    )


def rolling_12m(monthly: pl.DataFrame) -> pl.DataFrame:
    """Trailing 12-month inflation, stamped with the day it became public."""
    return (
        monthly.sort("date")
        .with_columns(
            value=((1 + pl.col("value") / 100).log().rolling_sum(12).exp() - 1) * 100,
            available=pl.col("date").dt.offset_by("1mo") + timedelta(days=IPCA_RELEASE_DAY - 1),
        )
        .drop_nulls("value")
        .select("available", pl.col("value").round(2))
    )


def year_end_value(daily: pl.DataFrame, today: date) -> pl.DataFrame:
    """Value in force on 31 December, for years that have ended."""
    return (
        daily.filter(pl.col("date") <= date(today.year - 1, 12, 31))
        .group_by(target=pl.col("date").dt.year().cast(pl.Int32))
        .agg(actual=pl.col("value").sort_by("date").last())
        .sort("target")
    )


def ipca() -> tuple[pl.DataFrame, pl.DataFrame]:
    monthly = bcb.sgs(IPCA_MONTHLY)
    return compound_annual(monthly), rolling_12m(monthly)


def selic(today: date) -> tuple[pl.DataFrame, pl.DataFrame]:
    daily = bcb.sgs(SELIC_TARGET, daily=True)
    return year_end_value(daily, today), daily.select(available="date", value="value")


def fx(today: date) -> tuple[pl.DataFrame, pl.DataFrame]:
    # The Focus FX question is scored against the *December average* rate: in the
    # years where the two differ, the final forecasts sit on the average, not on
    # the 31 Dec rate (e.g. 2016: last forecast 3.35, Dec avg 3.35, 31 Dec 3.26).
    monthly = bcb.sgs(PTAX_MONTH_AVG)
    actual = (
        monthly.filter(pl.col("date").dt.month() == 12, pl.col("date").dt.year() < today.year)
        .select(target=pl.col("date").dt.year().cast(pl.Int32), actual=pl.col("value"))
        .sort("target")
    )
    daily = bcb.sgs(PTAX_DAILY, daily=True)
    # PTAX is fixed in the afternoon, so a survey answer can only have used the previous day's.
    known = daily.select(available=pl.col("date") + timedelta(days=1), value="value")
    return actual, known


def gdp() -> tuple[pl.DataFrame, pl.DataFrame]:
    # Note: SGS holds today's *revised* figures; the first print was often different.
    annual = bcb.sgs(GDP_ANNUAL)
    actual = annual.select(target=pl.col("date").dt.year().cast(pl.Int32), actual="value")
    month, day = GDP_RELEASE
    known = annual.select(
        available=pl.date(pl.col("date").dt.year() + 1, month, day),
        value="value",
    )
    return actual, known
