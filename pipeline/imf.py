"""IMF World Economic Outlook forecasts, every edition since 1990.

imf.org answers scripted downloads with 403 ("Access Denied"), and the IMF's
open SDMX API only keeps the latest editions. The full history comes from the
*IMF WEO Macroeconomic Forecasts Panel Dataset* (MFPD, Echcharfi 2024,
CC BY 4.0) on Mendeley Data: the IMF's own historical WEO forecasts reshaped
into one row per country × edition × target year, updated after each WEO.

Two workbooks:

* forecasts: ``country, IFSCode, year, Round, target_year, h`` and the
  forecasts ``Fngdp_rpch`` (real GDP growth), ``Fpcpi_pch`` (CPI inflation,
  annual average) and ``Fbca_gdp`` (current account, % of GDP). ``Round`` 1
  is the April edition, 2 the October one.
* outturns: per country and year, the value as published in the April
  (``S_Y1_*``) and October (``F_Y1_*``) editions of the following year.

Outcome convention (as in the IMF's own forecast evaluations): the value
published in the October edition of the following year. Naive benchmark
("same as last year"): last year's value as published in the same edition.
That's ``S_Y1`` for an April edition and ``F_Y1`` for an October one, so the
benchmark never uses data the IMF didn't have yet.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from datetime import timedelta

import polars as pl

from . import countries
from .http import fetch
from .schema import SchemaError, require_columns

MENDELEY = "https://data.mendeley.com/public-api/datasets/8dt6xpp6x4"


@dataclass(frozen=True)
class Variable:
    id: str
    forecast: str  # column in the forecasts workbook
    outturn: str  # suffix of the outturns columns
    name: str
    short: str
    unit: str
    notes: str


VARIABLES = [
    Variable("gdp", "Fngdp_rpch", "G", "Real GDP growth", "GDP", "%", "Annual % change in real GDP."),
    Variable("inflation", "Fpcpi_pch", "P", "CPI inflation", "Inflation", "%",
             "Annual-average consumer prices, % change (not December over December)."),
    Variable("ca", "Fbca_gdp", "ca", "Current account balance", "Current account", "% of GDP",
             "Current account balance as a share of GDP."),
]  # fmt: skip

# Survey month of each edition, for the horizon (months to December of the target year).
EDITION_MONTH = {1: 4, 2: 10}


def files() -> dict[str, dict]:
    """The latest version's workbooks: ``{"forecasts": file, "outturns": file}`` (Mendeley file records)."""
    meta = json.loads(fetch(MENDELEY, max_age=timedelta(hours=12)))
    out = {}
    for f in meta.get("files", []):
        # "WEO_MacroForecasts_Apr_2026 (Forecasts).xlsx" / "... (outturns).xlsx":
        # both names contain "Forecasts", so test for the outturns first.
        name = f.get("filename", "").lower()
        if name.endswith(".xlsx"):
            kind = "outturns" if "outturn" in name else "forecasts" if "forecast" in name else None
            if kind:
                out[kind] = f | {"version": meta.get("version")}
    missing = {"forecasts", "outturns"} - out.keys()
    if missing:
        names = [f.get("filename") for f in meta.get("files", [])]
        raise SchemaError(f"Mendeley MFPD: no {', '.join(sorted(missing))} workbook in version {meta.get('version')}: {names}")
    return out


def file_url(f: dict) -> str:
    return f["content_details"]["download_url"]


def _workbook(f: dict) -> pl.DataFrame:
    # Each file id belongs to one dataset version and never changes: cache forever.
    data = fetch(file_url(f), max_age=None, fmt="xlsx")
    return pl.read_excel(io.BytesIO(data), sheet_id=1, infer_schema_length=10_000)


def parse_forecasts(df: pl.DataFrame) -> pl.DataFrame:
    """Wide workbook -> ``ifs, edition_year, round, target, h, indicator, forecast`` (non-null only)."""
    df = require_columns(df, ["IFSCode", "year", "Round", "target_year", *(v.forecast for v in VARIABLES)], "MFPD forecasts")
    long = (
        df.select(
            pl.col("IFSCode").cast(pl.Int32).alias("ifs"),
            pl.col("year").cast(pl.Int32).alias("edition_year"),
            pl.col("Round").cast(pl.Int32).alias("round"),
            pl.col("target_year").cast(pl.Int32).alias("target"),
            *(pl.col(v.forecast).cast(pl.Float64).alias(v.id) for v in VARIABLES),
        )
        .filter(pl.col("round").is_in(list(EDITION_MONTH)))
        .unpivot(index=["ifs", "edition_year", "round", "target"], variable_name="indicator", value_name="forecast")
        .drop_nulls("forecast")
    )
    month = pl.col("round").replace_strict(EDITION_MONTH, return_dtype=pl.Int32)
    return long.with_columns(
        h=(pl.col("target") * 12 + 11 - (pl.col("edition_year") * 12 + month - 1)).cast(pl.Int32),
        date=pl.date(pl.col("edition_year"), month, 15),
    )


def parse_outturns(df: pl.DataFrame) -> pl.DataFrame:
    """``ifs, indicator, target, spring, autumn``: the value published in April / October of target + 1."""
    cols = [f"{s}_Y1_{v.outturn}" for v in VARIABLES for s in ("S", "F")]
    df = require_columns(df, ["IFSCode", "year", *cols], "MFPD outturns")
    parts = [
        df.select(
            pl.col("IFSCode").cast(pl.Int32).alias("ifs"),
            pl.lit(v.id).alias("indicator"),
            pl.col("year").cast(pl.Int32).alias("target"),
            pl.col(f"S_Y1_{v.outturn}").cast(pl.Float64).alias("spring"),
            pl.col(f"F_Y1_{v.outturn}").cast(pl.Float64).alias("autumn"),
        )
        for v in VARIABLES
    ]
    return pl.concat(parts).filter(pl.col("spring").is_not_null() | pl.col("autumn").is_not_null())


def score(fc: pl.DataFrame, out: pl.DataFrame) -> pl.DataFrame:
    """Attach the outcome, the naive benchmark and both errors (forecast − actual)."""
    actual = out.select("ifs", "indicator", "target", actual="autumn")
    # Last year as published in the edition itself: April -> the spring value, October -> autumn.
    last_year = out.select(
        "ifs", "indicator", pl.col("target") + 1, naive_1="spring", naive_2="autumn"
    ).rename({"target": "edition_year"})
    return (
        fc.join(actual, on=["ifs", "indicator", "target"], how="left")
        .join(last_year, on=["ifs", "indicator", "edition_year"], how="left")
        .with_columns(naive=pl.when(pl.col("round") == 1).then("naive_1").otherwise("naive_2"))
        .drop("naive_1", "naive_2")
        .with_columns(err=pl.col("forecast") - pl.col("actual"), naive_err=pl.col("naive") - pl.col("actual"))
    )


def cells() -> pl.DataFrame:
    """Every forecast, scored, keyed by ISO code: ``iso3, group, indicator, target, h, date, forecast, actual, err, naive, naive_err``."""
    wb = files()
    scored = score(parse_forecasts(_workbook(wb["forecasts"])), parse_outturns(_workbook(wb["outturns"])))
    ids = countries.table()
    unknown = scored.join(ids, on="ifs", how="anti")["ifs"].unique().to_list()
    if unknown:
        raise SchemaError(f"MFPD: IMF country codes missing from pipeline/countries.py: {sorted(unknown)}")
    return (
        scored.join(ids.select("ifs", "iso3", "group"), on="ifs")
        .select("iso3", "group", "indicator", "target", "h", "date", "forecast", "actual", "err", "naive", "naive_err")
        .sort("iso3", "indicator", "target", "h")
    )


def names() -> pl.DataFrame:
    """``iso3, name`` as the IMF spells them (from the forecasts workbook)."""
    df = _workbook(files()["forecasts"])
    return (
        df.select(pl.col("IFSCode").cast(pl.Int32).alias("ifs"), pl.col("country").str.strip_chars().alias("name"))
        .unique("ifs")
        .join(countries.table(), on="ifs")
        .select("iso3", "iso_num", "group", "name")
        .sort("iso3")
    )


# ------------------------------------------------------------------ statistics
#
# Errors are forecast − actual. Inflation in a few countries (Venezuela,
# Zimbabwe, Sudan, Lebanon...) runs into the hundreds or thousands of percent, so
# pooled statistics across countries use medians: one hyperinflation would
# otherwise decide the "average" miss of a whole region.

OPTIMISTIC = {"gdp": 1, "inflation": -1}  # sign of an optimistic error (growth too high, inflation too low)


def _completed(cells: pl.DataFrame) -> pl.DataFrame:
    return cells.filter(pl.col("err").is_not_null())


def country_stats(cells: pl.DataFrame, min_years: int = 5) -> pl.DataFrame:
    """Per country × indicator × horizon: bias, mean and median absolute error, and the naive benchmark."""
    e = pl.col("err")
    paired = pl.col("naive_err").is_not_null()
    return (
        _completed(cells)
        .group_by("iso3", "indicator", "h")
        .agg(
            n=pl.len(),
            first=pl.col("target").min(),
            last=pl.col("target").max(),
            bias=e.mean(),
            mae=e.abs().mean(),
            mdae=e.abs().median(),
            naive_mae=pl.col("naive_err").abs().mean(),
            naive_mdae=pl.col("naive_err").abs().median(),
            # Share of years the forecast was closer than "same as last year".
            beat_naive=(e.abs() < pl.col("naive_err").abs()).filter(paired).mean(),
            over=(e > 0).mean(),
        )
        .filter(pl.col("n") >= min_years)
        .sort("iso3", "indicator", "h")
    )


def _group_aggs() -> list[pl.Expr]:
    e = pl.col("err")
    paired = pl.col("naive_err").is_not_null()
    return [
        pl.col("iso3").n_unique().alias("countries"),
        pl.len().alias("n"),
        e.median().alias("median_err"),
        e.abs().median().alias("mdae"),
        pl.col("naive_err").abs().median().alias("naive_mdae"),
        (e > 0).mean().alias("over"),
        (e < 0).mean().alias("under"),
        (e.abs() < pl.col("naive_err").abs()).filter(paired).mean().alias("beat_naive"),
    ]


def _with_groups(cells: pl.DataFrame) -> pl.DataFrame:
    """Each country row once per group it belongs to: ``all``, ``adv`` or ``emde``, and its region."""
    countries_only = cells.filter(pl.col("group") != "agg")
    emde = countries_only.filter(pl.col("group") != "adv")
    return pl.concat([
        countries_only.with_columns(pl.lit("all").alias("set")),
        countries_only.filter(group="adv").with_columns(pl.lit("adv").alias("set")),
        emde.with_columns(pl.lit("emde").alias("set")),
        emde.with_columns(pl.col("group").alias("set")),
    ])  # fmt: skip


def group_stats(cells: pl.DataFrame) -> pl.DataFrame:
    """Per country set (all, adv, emde, each EMDE region) × indicator × horizon, pooled over countries and years."""
    return _with_groups(_completed(cells)).group_by("set", "indicator", "h").agg(_group_aggs()).sort("set", "indicator", "h")


def year_stats(cells: pl.DataFrame, horizons: tuple[int, ...] = (2, 8, 14, 20)) -> pl.DataFrame:
    """Per country set × indicator × target year, for the short horizons: how the misses moved over time."""
    done = _completed(cells).filter(pl.col("h").is_in(horizons))
    return (
        _with_groups(done)
        .filter(pl.col("set").is_in(["all", "adv", "emde"]))
        .group_by("set", "indicator", "h", "target")
        .agg(_group_aggs())
        .filter(pl.col("countries") >= 10)
        .sort("set", "indicator", "h", "target")
    )
