"""The Philadelphia Fed's Survey of Professional Forecasters (SPF), scored.

Forecasts: the median across forecasters (``medianlevel.xlsx``), one sheet per
variable, one row per quarterly survey. The annual columns are the ones that
line up with Focus and the WEO: ``A`` = the current year, ``B`` the next, and
``C``/``D`` two and three years ahead (added in 2005 for CPI, 2009 for the rest).

Outcomes and the naive benchmark come from the same bank's *Real-Time Data Set
for Macroeconomists* (RTDSM): one column per "vintage", i.e. the data exactly as
published in the middle of each quarter, which is also when the SPF goes out.

* Outcome of year T: as published in the vintage of T+1:Q3 (mid-August of the
  following year, after the annual GDP revision), the counterpart of the IMF's
  "October of the following year".
* Naive benchmark: the latest value in the vintage of the survey's own quarter,
  so it only uses what forecasters could see. (CPI vintages start in 1994:
  earlier quarters use the first one, cut at what had been published; see
  ``backfill``.)

Interest rates aren't revised, so their outcomes are Treasury's daily constant-
maturity yields (see ``treasury.py``) averaged over the year, and the naive
benchmark is the yield on the day before the survey.

Survey timing: questionnaires go out at the start of the middle month of the
quarter and are due in the middle of it (``survey_date``: the 15th of February,
May, August and November). Horizon = months from the survey to December of the
target year: 10, 7, 4, 1 for the current year; +12 per year further out.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, timedelta

import polars as pl

from . import treasury
from .http import fetch
from .schema import SchemaError, require_columns

SPF = "https://www.philadelphiafed.org/-/media/frbp/assets/surveys-and-data/survey-of-professional-forecasters/historical-data/medianlevel.xlsx"
RTDSM = "https://www.philadelphiafed.org/-/media/FRBP/Assets/Surveys-And-Data/real-time-data/data-files/xlsx/{name}.xlsx"

# RTDSM files: quarterly vintages of real GDP (quarterly obs), CPI and the unemployment rate (monthly obs).
RTDSM_FILES = {"ROUTPUT": "ROUTPUTQvQd", "CPI": "CPIQvMd", "RUC": "rucQvMd"}

# Quarter of the vintage the outcome is read from, in the year after the target year.
OUTCOME_VINTAGE_Q = 3


@dataclass(frozen=True)
class Indicator:
    id: str
    sheet: str
    name: str
    short: str
    unit: str
    actual_label: str
    naive_label: str
    notes: list[str] = field(default_factory=list)


INDICATORS = [
    Indicator("cpi", "CPI", "CPI inflation", "CPI", "%",
              "CPI inflation, Q4 over Q4 (seasonally adjusted, real-time data a year later)",
              "Last published 12-month CPI inflation",
              ["Annual forecasts are fourth quarter over fourth quarter.",
               "Real-time CPI data start in 1994; for earlier surveys the first vintage stands in, cut at what had been published (CPI is only revised through its seasonal factors)."]),
    Indicator("gdp", "RGDP", "Real GDP growth", "GDP", "%",
              "Real GDP, annual-average growth (as published in August of the following year)",
              "Last published growth over four quarters",
              ["Growth is computed from the forecast levels: the current year against last year's level as published at the survey date."]),
    Indicator("unemp", "UNEMP", "Unemployment rate", "Unemployment", "%",
              "Unemployment rate, annual average (as published in August of the following year)",
              "Last published monthly unemployment rate"),
    Indicator("tbill", "TBILL", "3-month Treasury bill", "T-bill", "%",
              "3-month Treasury constant-maturity yield, annual average of daily values",
              "The 3-month yield the day before the survey",
              ["Scored from 1990, when Treasury's daily yield-curve file begins. The SPF asks for the secondary-market (discount-basis) bill rate; "
               "the constant-maturity yield is on a bond-equivalent basis and runs a few basis points higher, too little to change the picture."]),
    Indicator("tbond", "TBOND", "10-year Treasury yield", "10-year", "%",
              "10-year Treasury constant-maturity yield, annual average of daily values",
              "The 10-year yield the day before the survey",
              ["First asked in 1992."]),
]  # fmt: skip

SURVEY_MONTH = {1: 2, 2: 5, 3: 8, 4: 11}
YEARS_AHEAD = {"A": 0, "B": 1, "C": 2, "D": 3}


def survey_date(year: pl.Expr, quarter: pl.Expr) -> pl.Expr:
    return pl.date(year, quarter.replace_strict(SURVEY_MONTH, return_dtype=pl.Int32), 15)


def _xlsx(url: str, max_age: timedelta | None) -> bytes:
    return fetch(url, max_age=max_age, fmt="xlsx")


def _numbers(df: pl.DataFrame, cols: list[str]) -> pl.DataFrame:
    """"#N/A" and blanks -> null; everything else to float."""
    return df.with_columns(pl.col(c).cast(pl.Utf8).replace("#N/A", None).cast(pl.Float64, strict=False) for c in cols)


# ------------------------------------------------------------------ forecasts


def parse_sheet(df: pl.DataFrame, sheet: str) -> pl.DataFrame:
    """One SPF sheet -> ``year, quarter, ahead, value`` for the annual columns (A–D)."""
    cols = [f"{sheet}{k}" for k in YEARS_AHEAD if f"{sheet}{k}" in df.columns]
    df = require_columns(df, ["YEAR", "QUARTER", f"{sheet}A", f"{sheet}B"], f"SPF {sheet}")
    return (
        _numbers(df.select("YEAR", "QUARTER", *cols), cols)
        .with_columns(pl.col("YEAR", "QUARTER").cast(pl.Float64).cast(pl.Int32))
        .unpivot(index=["YEAR", "QUARTER"], variable_name="col", value_name="value")
        .drop_nulls("value")
        .select(
            pl.col("YEAR").alias("year"),
            pl.col("QUARTER").alias("quarter"),
            pl.col("col").str.slice(len(sheet)).replace_strict(YEARS_AHEAD, return_dtype=pl.Int32).alias("ahead"),
            "value",
        )
    )


def spf_sheets() -> dict[str, pl.DataFrame]:
    data = _xlsx(SPF, timedelta(hours=12))
    return {ind.sheet: pl.read_excel(io.BytesIO(data), sheet_name=ind.sheet, infer_schema_length=0) for ind in INDICATORS}


# ------------------------------------------------------------------ real-time data


def parse_rtdsm(df: pl.DataFrame, prefix: str) -> pl.DataFrame:
    """RTDSM wide file -> ``obs, vintage_year, vintage_q, value``.

    ``DATE`` is "1947:Q1" (quarterly obs) or "1947:01" (monthly); vintage columns
    are named ``ROUTPUT65Q4`` (two-digit year: 65–99 -> 19xx, the rest 20xx).
    """
    df = require_columns(df, ["DATE"], f"RTDSM {prefix}")
    vintages = [c for c in df.columns if c.upper().startswith(prefix.upper()) and c[-2:-1].upper() == "Q"]
    if not vintages:
        raise SchemaError(f"RTDSM {prefix}: no vintage columns like {prefix}65Q4; columns: {df.columns[:5]}...")
    period = pl.col("DATE").str.replace(":Q", ":").str.split(":")
    yy = pl.col("vintage").str.slice(len(prefix), 2).cast(pl.Int32)
    return (
        _numbers(df.select("DATE", *vintages), vintages)
        .with_columns(
            obs_year=period.list.get(0).cast(pl.Int32),
            obs_sub=period.list.get(1).cast(pl.Int32),
            quarterly=pl.col("DATE").str.contains("Q"),
        )
        .with_columns(
            obs=pl.date("obs_year", pl.when("quarterly").then(pl.col("obs_sub") * 3 - 2).otherwise("obs_sub"), 1)
        )
        .unpivot(index=["obs"], on=vintages, variable_name="vintage", value_name="value")
        .drop_nulls("value")
        .select(
            "obs",
            pl.when(yy >= 65).then(1900 + yy).otherwise(2000 + yy).alias("vintage_year"),
            pl.col("vintage").str.slice(-1).cast(pl.Int32).alias("vintage_q"),
            "value",
        )
    )


def rtdsm(prefix: str) -> pl.DataFrame:
    data = _xlsx(RTDSM.format(name=RTDSM_FILES[prefix]), timedelta(hours=12))
    return parse_rtdsm(pl.read_excel(io.BytesIO(data), sheet_id=1, infer_schema_length=0), prefix)


def backfill(rt: pl.DataFrame, since: int = 1981) -> pl.DataFrame:
    """Add pseudo-vintages for the quarters before the first real one.

    The CPI's real-time vintages only start in 1994:Q3. CPI is never revised
    except for its seasonal factors, so for each earlier quarter the first
    vintage stands in, cut at what had been published by then (monthly data up
    to the month before the survey month).
    """
    first_y, first_q = rt.select("vintage_year", "vintage_q").sort("vintage_year", "vintage_q").row(0)
    earliest = rt.filter(vintage_year=first_y, vintage_q=first_q)
    parts = [rt]
    for year in range(since, first_y + 1):
        for q in range(1, 5):
            if (year, q) >= (first_y, first_q):
                break
            cut = date(year, SURVEY_MONTH[q], 1)
            parts.append(earliest.filter(pl.col("obs") < cut).with_columns(vintage_year=pl.lit(year, pl.Int32), vintage_q=pl.lit(q, pl.Int32)))
    return pl.concat(parts)


def _annual(rt: pl.DataFrame, per_year: int, months: tuple[int, int] = (1, 12)) -> pl.DataFrame:
    """Per vintage and calendar year: the average of the year's observations
    (only months in ``months``), for years with all ``per_year`` of them."""
    lo, hi = months
    return (
        rt.filter(pl.col("obs").dt.month().is_between(lo, hi))
        .group_by("vintage_year", "vintage_q", pl.col("obs").dt.year().cast(pl.Int32).alias("year"))
        .agg(pl.col("value").mean(), pl.len().alias("n"))
        .filter(pl.col("n") == per_year)
        .drop("n")
    )


def outcome_from(annual: pl.DataFrame) -> pl.DataFrame:
    """``target, actual``: each year as published in the vintage of the following year's Q3."""
    return (
        annual.filter(pl.col("vintage_year") == pl.col("year") + 1, vintage_q=OUTCOME_VINTAGE_Q)
        .select(pl.col("year").alias("target"), pl.col("value").alias("actual"))
        .sort("target")
    )


def growth(levels: pl.DataFrame) -> pl.DataFrame:
    """``vintage_year, vintage_q, year, value`` annual levels -> % growth on the previous year, within each vintage."""
    return (
        levels.sort("vintage_year", "vintage_q", "year")
        .with_columns(
            prev=pl.col("value").shift(1).over("vintage_year", "vintage_q"),
            prev_year=pl.col("year").shift(1).over("vintage_year", "vintage_q"),
        )
        .filter(pl.col("prev_year") == pl.col("year") - 1)
        .with_columns(value=(pl.col("value") / pl.col("prev") - 1) * 100)
        .drop("prev", "prev_year")
    )


def latest_change(rt: pl.DataFrame, lag: int) -> pl.DataFrame:
    """Naive benchmark per vintage: % change of the latest observation on the one ``lag`` periods earlier."""
    return (
        rt.sort("vintage_year", "vintage_q", "obs")
        .group_by("vintage_year", "vintage_q")
        .agg(((pl.col("value").last() / pl.col("value").get(pl.len() - 1 - lag) - 1) * 100).alias("naive"))
    )


def latest_level(rt: pl.DataFrame) -> pl.DataFrame:
    return rt.sort("obs").group_by("vintage_year", "vintage_q").agg(pl.col("value").last().alias("naive"))


# ------------------------------------------------------------------ scoring


def indicator_frames(sheets: dict[str, pl.DataFrame], today: date | None = None) -> dict[str, tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]]:
    """Per indicator: (forecasts ``year, quarter, ahead, value``, outcomes ``target, actual``,
    naive benchmark), with the forecasts already as the published quantity (growth for GDP)."""
    out = {}
    survey = {"vintage_year": "year", "vintage_q": "quarter"}

    # CPI: Q4-over-Q4 inflation of the quarterly-average index (Q4 = three months).
    cpi_rt = backfill(rtdsm("CPI"))
    cpi_q4 = growth(_annual(cpi_rt, 3, months=(10, 12)))
    out["cpi"] = (parse_sheet(sheets["CPI"], "CPI"), outcome_from(cpi_q4), latest_change(cpi_rt, 12).rename(survey))

    # GDP: annual-average growth. The SPF forecasts levels, so turn them into growth:
    # A against last year's level as published in the survey's own vintage, B on A, C on B, D on C.
    gdp_rt = rtdsm("ROUTPUT")
    gdp_annual = _annual(gdp_rt, 4)
    levels = parse_sheet(sheets["RGDP"], "RGDP")
    base = gdp_annual.filter(pl.col("year") == pl.col("vintage_year") - 1).select(
        pl.col("vintage_year").alias("year"), pl.col("vintage_q").alias("quarter"), pl.lit(0, pl.Int32).alias("ahead"), pl.col("value").alias("base")
    )
    prev = levels.with_columns(pl.col("ahead") + 1).rename({"value": "base"})
    gdp_fc = (
        pl.concat([levels.join(base, on=["year", "quarter", "ahead"]), levels.join(prev, on=["year", "quarter", "ahead"])])
        .with_columns(value=(pl.col("value") / pl.col("base") - 1) * 100)
        .drop("base")
    )
    out["gdp"] = (gdp_fc, outcome_from(growth(gdp_annual)), latest_change(gdp_rt, 4).rename(survey))

    ruc_rt = rtdsm("RUC")
    out["unemp"] = (parse_sheet(sheets["UNEMP"], "UNEMP"), outcome_from(_annual(ruc_rt, 12)), latest_level(ruc_rt).rename(survey))

    rates = treasury.daily(today)
    for ind_id, col in (("tbill", "m3"), ("tbond", "y10")):
        r = rates.select("date", pl.col(col).alias("value")).drop_nulls()
        out[ind_id] = (parse_sheet(sheets[ind_id.upper()], ind_id.upper()), treasury.annual_average(r, today), r)
    return out


def score(fc: pl.DataFrame, actual: pl.DataFrame, naive: pl.DataFrame) -> pl.DataFrame:
    """``target, h, date, median, actual, err, naive, naive_err`` for one indicator.

    ``naive`` is either per survey (``year, quarter, naive``) or a daily series
    (``date, value``), as-of the day before the survey.
    """
    cells = fc.with_columns(
        target=(pl.col("year") + pl.col("ahead")).cast(pl.Int32),
        date=survey_date(pl.col("year"), pl.col("quarter")),
    )
    if "naive" in naive.columns:
        cells = cells.join(naive, on=["year", "quarter"], how="left")
    else:
        cells = (
            cells.with_columns(before=pl.col("date") - pl.duration(days=1))
            .sort("before")
            .join_asof(naive.sort("date").rename({"date": "known", "value": "naive"}), left_on="before", right_on="known", strategy="backward")
            .drop("before", "known")
        )
    return (
        cells.with_columns(h=(pl.col("target") * 12 + 11 - (pl.col("date").dt.year() * 12 + pl.col("date").dt.month() - 1)).cast(pl.Int32))
        .join(actual, on="target", how="left")
        .select(
            "target", "h", "date", pl.col("value").alias("median"), "actual",
            (pl.col("value") - pl.col("actual")).alias("err"),
            "naive", (pl.col("naive") - pl.col("actual")).alias("naive_err"),
        )
        .sort("target", "h")
    )  # fmt: skip


def monthly(today: date | None = None) -> pl.DataFrame:
    """Every SPF annual forecast, scored: same columns as the Focus ``monthly`` frame (minus Focus-only ones)."""
    frames = indicator_frames(spf_sheets(), today)
    parts = [score(*frames[ind.id]).select(pl.lit(ind.id).alias("indicator"), pl.all()) for ind in INDICATORS]
    return pl.concat(parts).sort("indicator", "target", "h")


def outcomes(today: date | None = None) -> pl.DataFrame:
    frames = indicator_frames(spf_sheets(), today)
    return pl.concat([frames[ind.id][1].select(pl.lit(ind.id).alias("indicator"), pl.all()) for ind in INDICATORS])
