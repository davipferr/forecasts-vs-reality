"""Cleaned, shared frames, memoised as Parquet in the cache directory.

Several loaders need the same tables (e.g. the scored monthly cells feed both
``monthly.parquet`` and ``horizon-stats.parquet``), so each frame is built once
and reused for ``max_age``. Every frame covers all four indicators, keyed by an
``indicator`` column.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, timedelta

import polars as pl

from . import bcb, forecasts
from .http import CACHE_DIR, log
from .indicators import INDICATORS, goals_frame

FRAMES = CACHE_DIR / "frames"


def memo(name: str, build: Callable[[], pl.DataFrame], max_age: timedelta = timedelta(hours=12)) -> pl.DataFrame:
    path = FRAMES / f"{name}.parquet"
    if path.exists() and time.time() - path.stat().st_mtime < max_age.total_seconds():
        return pl.read_parquet(path)
    t0 = time.time()
    df = build()
    FRAMES.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.part")
    df.write_parquet(tmp)
    tmp.replace(path)
    log(f"frame {name}: {df.height:,} rows in {time.time() - t0:.1f}s")
    return df


def _tag(df: pl.DataFrame, indicator: str) -> pl.DataFrame:
    return df.select(pl.lit(indicator).alias("indicator"), pl.all())


def focus_daily() -> pl.DataFrame:
    """Daily Focus consensus (30-day window) for annual targets."""
    return memo("focus_daily", lambda: pl.concat([_tag(bcb.focus_annual(i.focus), i.id) for i in INDICATORS]))


def top5_daily() -> pl.DataFrame:
    """Daily Top 5 consensus (medium-term ranking), where it's long enough to compare."""
    return memo("top5_daily", lambda: pl.concat([_tag(bcb.focus_top5(i.focus), i.id) for i in INDICATORS if i.top5]))


def _sources() -> dict[str, tuple[pl.DataFrame, pl.DataFrame]]:
    today = date.today()
    return {i.id: i.sources(today) for i in INDICATORS}


def outcomes() -> pl.DataFrame:
    """``indicator, target, actual`` plus the official target where there is one (IPCA)."""

    def build() -> pl.DataFrame:
        parts = []
        for ind, (actual, _) in zip(INDICATORS, _sources().values()):
            df = actual
            if ind.goals:
                df = df.join(goals_frame(ind), on="target", how="full", coalesce=True)
            else:
                df = df.with_columns(goal=pl.lit(None, pl.Float64), goal_tolerance=pl.lit(None, pl.Float64))
            parts.append(_tag(df.select("target", "actual", "goal", "goal_tolerance"), ind.id))
        return pl.concat(parts).sort("indicator", "target")

    return memo("outcomes", build)


def known() -> pl.DataFrame:
    """What was public at each point in time (``indicator, available, value``): the naive benchmark."""
    return memo("known", lambda: pl.concat([_tag(k.sort("available"), i) for i, (_, k) in _sources().items()]))


def monthly() -> pl.DataFrame:
    """One row per indicator × target year × horizon (last survey of the month), scored."""

    def build() -> pl.DataFrame:
        daily = focus_daily()
        top5 = top5_daily()
        out = known()
        res = outcomes()
        parts = []
        for ind in INDICATORS:
            cells = forecasts.as_of(
                forecasts.monthly(daily.filter(indicator=ind.id).drop("indicator")),
                out.filter(indicator=ind.id).drop("indicator"),
                "naive",
            )
            t5 = top5.filter(indicator=ind.id)
            if t5.height:
                t5_cells = forecasts.monthly(t5.drop("indicator")).select("target", "h", top5="median")
                cells = cells.join(t5_cells, on=["target", "h"], how="left")
            else:
                cells = cells.with_columns(top5=pl.lit(None, pl.Float64))
            r = res.filter(indicator=ind.id)
            cells = cells.join(r.select("target", "goal"), on="target", how="left")
            scored = forecasts.score(cells, r.select("target", "actual"))
            parts.append(_tag(scored, ind.id))
        cols = ["indicator", "target", "h", "date", "median", "std", "respondents", "actual", "err",
                "naive", "naive_err", "goal", "goal_err", "top5", "top5_err"]  # fmt: skip
        return pl.concat([p.select(cols) for p in parts]).sort("indicator", "target", "h")

    return memo("monthly", build)
