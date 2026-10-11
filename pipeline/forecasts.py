"""Turning the daily Focus series into horizons, grids and error statistics.

Horizon convention: months from the survey month to December of the target
year. A forecast made in January for the same year has horizon 11; in December,
0. GDP is still surveyed after the year ends (until IBGE publishes it in March),
which gives small negative horizons.
"""

from __future__ import annotations

import polars as pl


def with_horizon(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        h=(pl.col("target") * 12 + 11 - (pl.col("date").dt.year() * 12 + pl.col("date").dt.month() - 1)).cast(pl.Int32)
    )


def _keys(df: pl.DataFrame) -> list[str]:
    """Group per target year, and per indicator when several are stacked."""
    return ["indicator", "target"] if "indicator" in df.columns else ["target"]


def weekly(df: pl.DataFrame) -> pl.DataFrame:
    """Last survey of each week, per target: the daily series is ~5× denser than needed for a chart."""
    keys = _keys(df)
    return (
        df.sort("date")
        .group_by(*keys, pl.col("date").dt.truncate("1w").alias("week"))
        .agg(pl.all().exclude("week").last())
        .drop("week")
        .sort(*keys, "date")
    )


def monthly(df: pl.DataFrame) -> pl.DataFrame:
    """Last survey of each month, per target, with its horizon."""
    keys = _keys(df)
    return (
        with_horizon(df)
        .sort("date")
        .group_by(*keys, "h")
        .agg(pl.all().last())
        .sort(*keys, "h")
    )


def as_of(df: pl.DataFrame, known: pl.DataFrame, name: str) -> pl.DataFrame:
    """Attach the latest value of ``known`` published on or before each survey date."""
    return (
        df.sort("date")
        .join_asof(known.sort("available").rename({"value": name}), left_on="date", right_on="available", strategy="backward")
        .drop("available")
    )


def score(cells: pl.DataFrame, actual: pl.DataFrame) -> pl.DataFrame:
    """Attach the outcome and errors (forecast − actual) to each monthly cell.

    Years whose outcome isn't known yet are kept, with null ``actual`` and errors.
    """
    out = cells.join(actual, on="target", how="left").with_columns(err=pl.col("median") - pl.col("actual"))
    for col in ("naive", "goal", "top5"):
        if col in out.columns:
            out = out.with_columns((pl.col(col) - pl.col("actual")).alias(f"{col}_err"))
    return out


def horizon_stats(scored: pl.DataFrame, min_years: int = 5) -> pl.DataFrame:
    """Bias, MAE and RMSE by horizon for the consensus and the benchmarks (completed years only).

    The Top 5 series starts later than the consensus, so it is compared with the
    consensus *on the same target years and horizons* (``cons_t5_mae``); comparing
    it with the full-sample consensus would mix in the 2002 miss it never faced.
    """
    done = scored.filter(pl.col("actual").is_not_null())
    e = pl.col("err")
    aggs = [
        e.mean().alias("bias"),
        e.abs().mean().alias("mae"),
        (e**2).mean().sqrt().alias("rmse"),
        e.count().alias("n"),
    ]
    for col in ("naive", "goal"):
        if f"{col}_err" in done.columns:
            aggs.append(pl.col(f"{col}_err").abs().mean().alias(f"{col}_mae"))
    if "top5_err" in done.columns:
        paired = pl.col("top5_err").is_not_null()
        aggs += [
            pl.col("top5_err").abs().mean().alias("t5_mae"),
            e.filter(paired).abs().mean().alias("cons_t5_mae"),
            paired.sum().alias("t5_n"),
        ]
    stats = done.group_by("h").agg(aggs).filter(pl.col("n") >= min_years)
    if "t5_n" in stats.columns:
        too_few = pl.col("t5_n") < min_years
        stats = stats.with_columns(
            pl.when(too_few).then(None).otherwise(pl.col(c)).alias(c) for c in ("t5_mae", "cons_t5_mae")
        )
    return stats.sort("h")


def headline(scored: pl.DataFrame, h: int = 12) -> dict:
    """The few numbers the page leads with, at a one-year horizon."""
    at = scored.filter(pl.col("h") == h).drop_nulls("err")
    if at.is_empty():
        return {}
    worst = at.sort(pl.col("err").abs(), descending=True).row(0, named=True)
    out = {
        "h": h,
        "years": at.height,
        "first": int(at["target"].min()),
        "last": int(at["target"].max()),
        "mae": at["err"].abs().mean(),
        "bias": at["err"].mean(),
        "under": int((at["err"] < 0).sum()),
        "over": int((at["err"] > 0).sum()),
        "worst": {"year": worst["target"], "forecast": worst["median"], "actual": worst["actual"], "err": worst["err"]},
    }
    if "naive_err" in at.columns:
        out["naiveMae"] = at["naive_err"].abs().mean()
        out["beatNaive"] = int((at["err"].abs() < at["naive_err"].abs()).sum())
    return out
