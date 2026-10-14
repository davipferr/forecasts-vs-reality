"""The bond market as a forecaster: forward rates, the term premium, and the yield curve's recession signal.

Sources (all keyless):

* **Zero-coupon yield curve** (Gürkaynak, Sack and Wright, Federal Reserve
  Board, ``feds200628.csv``): daily fitted zero-coupon Treasury yields since
  1961, continuously compounded. Maturities up to 7 years start in 1961, the
  10-year in August 1971. Forward rates are computed from it.
* **ACM term premium** (Adrian, Crump and Moench, New York Fed): monthly
  decomposition of the 10-year yield into the expected path of short rates
  ("risk-neutral yield") and a term premium, since 1961.
* **Recessions:** NBER business-cycle peaks and troughs (JSON).
* The 3-month yield for the 10-year − 3-month spread comes from Treasury's
  daily curve (``treasury.py``), since 1990.

Everything is sampled at month ends (or monthly averages for the spreads, as in
the recession literature).
"""

from __future__ import annotations

import io
import json
from datetime import date, timedelta

import polars as pl

from . import treasury
from .http import fetch
from .schema import SchemaError, require_columns

GSW = "https://www.federalreserve.gov/data/yield-curve-tables/feds200628.csv"
ACM = "https://www.newyorkfed.org/medialibrary/media/research/data_indicators/ACMTermPremium.xls"
NBER = "https://data.nber.org/data/cycles/business_cycle_dates.json"

MATURITIES = range(1, 11)
FORWARD_YEARS = range(1, 6)  # forecast horizons k: the 1-year rate k years ahead


# ------------------------------------------------------------------ parsing


def parse_gsw(data: bytes) -> pl.DataFrame:
    """``date, y1..y10`` (zero-coupon, % continuously compounded), daily."""
    lines = data.decode("utf-8", errors="replace").splitlines()
    try:
        header = next(i for i, line in enumerate(lines) if line.startswith("Date,"))
    except StopIteration:
        raise SchemaError("GSW yield curve: no 'Date,' header row; the file format probably changed") from None
    df = pl.read_csv(io.StringIO("\n".join(lines[header:])), infer_schema_length=0, null_values=["NA", ""])
    cols = [f"SVENY{m:02d}" for m in MATURITIES]
    df = require_columns(df, ["Date", *cols], "GSW yield curve")
    return df.select(
        pl.col("Date").str.to_date("%Y-%m-%d").alias("date"),
        *(pl.col(f"SVENY{m:02d}").cast(pl.Float64, strict=False).alias(f"y{m}") for m in MATURITIES),
    ).sort("date")


def parse_acm(data: bytes) -> pl.DataFrame:
    """``month, acm_y10, tp10, rn10``: the 10-year yield, its term premium and risk-neutral part."""
    df = pl.read_excel(io.BytesIO(data), sheet_name="ACM Monthly", infer_schema_length=0)
    df = require_columns(df, ["DATE", "ACMY10", "ACMTP10", "ACMRNY10"], "ACM term premium")
    return df.select(
        pl.col("DATE").str.to_date("%d-%b-%Y").dt.month_start().alias("month"),
        pl.col("ACMY10").cast(pl.Float64).alias("acm_y10"),
        pl.col("ACMTP10").cast(pl.Float64).alias("tp10"),
        pl.col("ACMRNY10").cast(pl.Float64).alias("rn10"),
    ).sort("month")


def parse_nber(data: bytes) -> pl.DataFrame:
    """``peak, trough`` (first day of the month) for every US recession."""
    rows = json.loads(data)
    df = pl.DataFrame(rows, schema={"peak": pl.Utf8, "trough": pl.Utf8})
    df = require_columns(df, ["peak", "trough"], "NBER business cycle dates")
    return df.filter(pl.col("peak") != "").select(
        pl.col("peak").str.to_date("%Y-%m-%d"),
        pl.col("trough").replace("", None).str.to_date("%Y-%m-%d"),
    )


def gsw_daily() -> pl.DataFrame:
    return parse_gsw(fetch(GSW, max_age=timedelta(hours=12), fmt="csv"))


def acm() -> pl.DataFrame:
    return parse_acm(fetch(ACM, max_age=timedelta(hours=12), fmt="xls"))


def recessions() -> pl.DataFrame:
    return parse_nber(fetch(NBER, max_age=timedelta(hours=12)))


# ------------------------------------------------------------------ monthly curve


def month_end(daily: pl.DataFrame) -> pl.DataFrame:
    """Last observation of each month, stamped with the first day of the month."""
    return daily.sort("date").group_by(pl.col("date").dt.month_start().alias("month")).agg(pl.all().exclude("date").last()).sort("month")


def month_mean(daily: pl.DataFrame) -> pl.DataFrame:
    return daily.group_by(pl.col("date").dt.month_start().alias("month")).agg(pl.all().exclude("date").mean()).sort("month")


def forwards(curve: pl.DataFrame, ks: range = range(0, 10)) -> pl.DataFrame:
    """1-year forward rates k years ahead from zero yields: f(k) = (k+1)·y(k+1) − k·y(k).

    Continuously compounded, so the forward is exact; f(0) is the 1-year yield itself.
    """
    return curve.select(
        "month",
        *((pl.col("y1") if k == 0 else (k + 1) * pl.col(f"y{k + 1}") - k * pl.col(f"y{k}")).alias(f"f{k}") for k in ks),
    )


def forward_tests(curve: pl.DataFrame) -> pl.DataFrame:
    """Each month × horizon k: the 1-year forward rate k years ahead vs. the 1-year yield that came.

    ``err`` = forward − realised; ``naive`` = today's 1-year yield ("no change");
    ``change``/``spread`` feed the Fama–Bliss regression (realised change on the
    forward − spot spread).
    """
    fw = forwards(curve, FORWARD_YEARS)
    y1 = curve.select("month", "y1")
    parts = []
    for k in FORWARD_YEARS:
        realised = y1.select(pl.col("month").dt.offset_by(f"-{k}y").alias("month"), pl.col("y1").alias("realised"))
        parts.append(
            fw.select("month", pl.col(f"f{k}").alias("forward"))
            .join(y1, on="month")
            .join(realised, on="month", how="left")
            .select(
                "month",
                pl.lit(k, pl.Int32).alias("k"),
                "forward",
                "realised",
                pl.col("y1").alias("naive"),
                (pl.col("forward") - pl.col("realised")).alias("err"),
                (pl.col("y1") - pl.col("realised")).alias("naive_err"),
            )
            .drop_nulls("forward")
        )
    return pl.concat(parts).sort("k", "month")


def _ols(x: pl.Expr, y: pl.Expr) -> list[pl.Expr]:
    """Slope, intercept and R² of y on x, as aggregation expressions."""
    cov = ((x - x.mean()) * (y - y.mean())).mean()
    slope = cov / x.var(ddof=0)
    return [
        slope.alias("slope"),
        (y.mean() - slope * x.mean()).alias("intercept"),
        (cov**2 / (x.var(ddof=0) * y.var(ddof=0))).alias("r2"),
    ]


SAMPLES = {"all": date(1961, 1, 1), "1990": date(1990, 1, 1)}


def forward_stats(tests: pl.DataFrame) -> pl.DataFrame:
    """Per sample × horizon: bias and MAE of the forward rate and of "no change", and the Fama–Bliss slope.

    A slope of 1 means forward rates move one for one with the change that
    follows (the expectations hypothesis); 0 means they carry no information
    about it beyond the term premium.
    """
    done = tests.drop_nulls("realised")
    change = pl.col("realised") - pl.col("naive")
    spread = pl.col("forward") - pl.col("naive")
    parts = []
    for name, start in SAMPLES.items():
        parts.append(
            done.filter(pl.col("month") >= start)
            .group_by("k")
            .agg(
                pl.len().alias("n"),
                pl.col("month").min().alias("first"),
                pl.col("month").max().alias("last"),
                pl.col("err").mean().alias("bias"),
                pl.col("err").abs().mean().alias("mae"),
                pl.col("naive_err").mean().alias("naive_bias"),
                pl.col("naive_err").abs().mean().alias("naive_mae"),
                (pl.col("err").abs() < pl.col("naive_err").abs()).mean().alias("beat_naive"),
                *_ols(spread, change),
            )
            .with_columns(pl.lit(name).alias("sample"))
        )
    return pl.concat(parts).select("sample", pl.all().exclude("sample")).sort("sample", "k")


def forward_paths(curve: pl.DataFrame, months: tuple[int, ...] = (1,)) -> pl.DataFrame:
    """The whole forward path (k = 0..9) at the start of each year: ``month, k, date, forward``,
    where ``date`` is when that 1-year rate would start. For the "hairy" chart."""
    fw = forwards(curve).filter(pl.col("month").dt.month().is_in(months))
    return (
        fw.unpivot(index="month", variable_name="k", value_name="forward")
        .with_columns(pl.col("k").str.slice(1).cast(pl.Int32))
        .drop_nulls("forward")
        .with_columns(date=pl.col("month").dt.offset_by(pl.format("{}y", pl.col("k"))))
        .sort("month", "k")
    )


# ------------------------------------------------------------------ recessions


def inversions(spread: pl.DataFrame, gap: int = 6) -> pl.DataFrame:
    """Episodes of an inverted curve: ``start, end, months, deepest``.

    ``spread``: ``month, value`` (monthly average). An episode starts with the
    first month below zero and ends after ``gap`` months back above zero, so a
    brief positive blip doesn't split one inversion into two.
    """
    s = spread.drop_nulls("value").sort("month")
    episodes, current, positive = [], None, 0
    for month, value in s.iter_rows():
        if value < 0:
            if current is None:
                current = {"start": month, "end": month, "months": 0, "deepest": value}
            current["end"] = month
            current["months"] += 1
            current["deepest"] = min(current["deepest"], value)
            positive = 0
        elif current is not None:
            positive += 1
            if positive >= gap:
                episodes.append(current)
                current, positive = None, 0
    if current is not None:
        episodes.append(current)
    return pl.DataFrame(episodes, schema={"start": pl.Date, "end": pl.Date, "months": pl.Int32, "deepest": pl.Float64})


def score_signals(episodes: pl.DataFrame, peaks: pl.DataFrame, first: date, last: date, window: int = 24) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Match inversions to recessions.

    An inversion is a **hit** if a recession began (NBER peak) within ``window``
    months of its start, a **false alarm** if none did and ``window`` months have
    passed, and **pending** otherwise. A recession is **signalled** if the curve
    was inverted at some point in the ``window`` months before it began (the
    1981 recession came while the 1978 inversion was still going), and
    **missed** otherwise.
    Returns (episodes with ``outcome, peak, lead``; recessions with ``signal, lead``).
    """
    peak_list = [p for p in peaks["peak"].to_list() if first <= p <= last]

    def months_between(a: date, b: date) -> int:
        return (b.year - a.year) * 12 + b.month - a.month

    ep_rows = []
    for e in episodes.iter_rows(named=True):
        hits = [p for p in peak_list if 0 <= months_between(e["start"], p) <= window]
        if hits:
            ep_rows.append(e | {"outcome": "hit", "peak": hits[0], "lead": months_between(e["start"], hits[0])})
        elif months_between(e["start"], last) >= window:
            ep_rows.append(e | {"outcome": "false alarm", "peak": None, "lead": None})
        else:
            ep_rows.append(e | {"outcome": "pending", "peak": None, "lead": None})
    rec_rows = []
    for p in peak_list:
        # Episodes inverted at some point in [peak − window, peak].
        before = [e["start"] for e in episodes.iter_rows(named=True) if e["start"] <= p and months_between(e["end"], p) <= window]
        rec_rows.append({"peak": p, "signal": before[0] if before else None, "lead": months_between(before[0], p) if before else None})
    ep_schema = {**episodes.schema, "outcome": pl.Utf8, "peak": pl.Date, "lead": pl.Int32}
    return (
        pl.DataFrame(ep_rows, schema=ep_schema),
        pl.DataFrame(rec_rows, schema={"peak": pl.Date, "signal": pl.Date, "lead": pl.Int32}),
    )


# ------------------------------------------------------------------ assembled


def monthly(today: date | None = None) -> pl.DataFrame:
    """One row per month: zero yields (month end), spreads (monthly averages), ACM decomposition, recession flag."""
    daily = gsw_daily()
    ends = month_end(daily)
    avg = month_mean(daily.select("date", "y1", "y10")).select("month", (pl.col("y10") - pl.col("y1")).alias("spread_10_1"))
    tsy = treasury.daily(today).select("date", "m3", "y10")
    tsy_avg = month_mean(tsy).select("month", (pl.col("y10") - pl.col("m3")).alias("spread_10_3m"))
    rec = recessions()
    out = (
        ends.select("month", "y1", "y2", "y5", "y10")
        .join(avg, on="month", how="left")
        .join(tsy_avg, on="month", how="left")
        .join(acm(), on="month", how="left")
    )
    in_recession = pl.lit(False)
    for peak, trough in rec.iter_rows():
        # NBER dates: the recession runs from the month after the peak to the trough.
        in_recession = in_recession | ((pl.col("month") > peak) & (pl.col("month") <= (trough or date.max)))
    return out.with_columns(recession=in_recession).sort("month")
