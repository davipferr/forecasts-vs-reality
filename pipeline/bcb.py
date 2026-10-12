"""Banco Central APIs: Focus expectations (Olinda OData) and time series (SGS)."""

from __future__ import annotations

import json
from datetime import date, timedelta

import polars as pl

from .http import fetch, log
from .schema import SchemaError, require_columns

OLINDA = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata"
SGS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"

FOCUS_SCHEMA = {
    "date": pl.Date,
    "target": pl.Int32,
    "mean": pl.Float64,
    "median": pl.Float64,
    "std": pl.Float64,
    "min": pl.Float64,
    "max": pl.Float64,
    "respondents": pl.Int32,
}
# Olinda fields shared by the full survey and the Top 5.
FOCUS_FIELDS = ["Data", "DataReferencia", "Media", "Mediana", "DesvioPadrao", "Minimo", "Maximo"]


# Requests are built by these functions (not inline) so pipeline.manifest can
# find the exact cached responses a build used.


def _odata_request(entity: str, filter_: str, select: list[str]) -> tuple[str, dict]:
    # Olinda returns the whole result set in one response (~30k rows for one
    # indicator), so no paging is needed. It rejects some query forms ($count)
    # with a bare 403, so keep the query to $filter/$select/$format.
    return f"{OLINDA}/{entity}", {"$filter": filter_, "$select": ",".join(select), "$format": "json"}


FOCUS_ANNUAL_FIELDS = [*FOCUS_FIELDS, "numeroRespondentes"]


def focus_request(indicator: str) -> tuple[str, dict]:
    """``baseCalculo = 0`` is the statistic over every forecast submitted in the
    last 30 days (the headline Focus number); ``1`` uses only the last 5 days and
    starts much later."""
    return _odata_request("ExpectativasMercadoAnuais", f"Indicador eq '{indicator}' and baseCalculo eq 0", FOCUS_ANNUAL_FIELDS)


def top5_request(indicator: str, kind: str = "M") -> tuple[str, dict]:
    """``kind`` is the ranking the Top 5 is drawn from: C (short), M (medium), L (long term)."""
    return _odata_request("ExpectativasMercadoTop5Anuais", f"Indicador eq '{indicator}' and tipoCalculo eq '{kind}'", FOCUS_FIELDS)


def focus_annual(indicator: str) -> pl.DataFrame:
    """Daily Focus consensus for annual targets of one indicator."""
    url, params = focus_request(indicator)
    rows = json.loads(fetch(url, params=params))["value"]
    log(f"  Focus {indicator}: {len(rows):,} rows")
    return _focus_frame(rows, FOCUS_ANNUAL_FIELDS, f"Olinda ExpectativasMercadoAnuais ({indicator})")


def focus_top5(indicator: str, kind: str = "M") -> pl.DataFrame:
    """Consensus of the five institutions with the best track record."""
    url, params = top5_request(indicator, kind)
    rows = json.loads(fetch(url, params=params))["value"]
    log(f"  Focus Top 5 {indicator}: {len(rows):,} rows")
    return _focus_frame(rows, FOCUS_FIELDS, f"Olinda ExpectativasMercadoTop5Anuais ({indicator})")


def _focus_frame(rows: list[dict], fields: list[str], source: str) -> pl.DataFrame:
    """Rename and type Olinda rows. An empty answer is an error: every indicator
    has had forecasts since 2000, so zero rows means the query or the API broke."""
    if not rows:
        raise SchemaError(f"{source}: the API returned no rows")
    return (
        require_columns(pl.DataFrame(rows, infer_schema_length=None), fields, source)
        .rename(
            {
                "Data": "date",
                "DataReferencia": "target",
                "Media": "mean",
                "Mediana": "median",
                "DesvioPadrao": "std",
                "Minimo": "min",
                "Maximo": "max",
            }
        )
        .with_columns(
            pl.col("date").str.to_date("%Y-%m-%d"),
            # DataReferencia is a string ("2026"); annual endpoints only ever hold years.
            pl.col("target").cast(pl.Int32),
            # Only the full survey reports respondents; the Top 5 is always five.
            respondents=pl.col("numeroRespondentes").cast(pl.Int32) if "numeroRespondentes" in fields else pl.lit(None, pl.Int32),
        )
        .select(list(FOCUS_SCHEMA))
        .cast(FOCUS_SCHEMA)
        .drop_nulls("median")
        .sort("target", "date")
    )


def parse_sgs(rows: list[dict], source: str = "SGS") -> pl.DataFrame:
    """SGS returns ``[{"data": "dd/mm/yyyy", "valor": "1.23"}]`` with numbers as strings.

    An empty list is allowed here (a daily window may hold no data); ``sgs``
    checks that the whole series isn't empty.
    """
    if not rows:
        return pl.DataFrame(schema={"date": pl.Date, "value": pl.Float64})
    return (
        require_columns(pl.DataFrame(rows), ["data", "valor"], source)
        .select(
            date=pl.col("data").str.to_date("%d/%m/%Y"),
            value=pl.col("valor").cast(pl.Float64, strict=False),
        )
        .drop_nulls()
        .unique("date", keep="last")
        .sort("date")
    )


SGS_START = date(1999, 1, 1)


def sgs_requests(code: int, *, daily: bool = False, start: date = SGS_START, today: date | None = None) -> list[tuple[str, dict, timedelta | None]]:
    """``(url, params, max_age)`` of every request that makes up one SGS series.

    Daily series only accept queries of at most 10 years, so they are fetched in
    windows; windows that ended more than a month ago never change and are cached forever.
    """
    url = SGS.format(code=code)
    if not daily:
        return [(url, {"formato": "json"}, timedelta(hours=12))]
    today = today or date.today()
    out = []
    lo = start
    while lo <= today:
        hi = min(date(lo.year + 9, 12, 31), today)
        closed = hi < today - timedelta(days=31)
        params = {"formato": "json", "dataInicial": lo.strftime("%d/%m/%Y"), "dataFinal": hi.strftime("%d/%m/%Y")}
        out.append((url, params, None if closed else timedelta(hours=12)))
        lo = date(hi.year + 1, 1, 1)
    return out


def sgs(code: int, *, daily: bool = False, start: date = SGS_START) -> pl.DataFrame:
    """One SGS series as ``date, value``."""
    source = f"SGS series {code}"
    frames = []
    for url, params, max_age in sgs_requests(code, daily=daily, start=start):
        window = f"{source}, {params['dataInicial']}-{params['dataFinal']}" if "dataInicial" in params else source
        frames.append(parse_sgs(json.loads(fetch(url, params=params, max_age=max_age)), window))
    return require_columns(pl.concat(frames).unique("date", keep="last").sort("date"), [], source)
