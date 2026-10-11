"""Banco Central APIs: Focus expectations (Olinda OData) and time series (SGS)."""

from __future__ import annotations

import json
from datetime import date, timedelta

import polars as pl

from .http import fetch, log

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


def _odata(entity: str, filter_: str, select: list[str]) -> list[dict]:
    # Olinda returns the whole result set in one response (~30k rows for one
    # indicator), so no paging is needed. It rejects some query forms ($count)
    # with a bare 403, so keep the query to $filter/$select/$format.
    body = fetch(
        f"{OLINDA}/{entity}",
        params={"$filter": filter_, "$select": ",".join(select), "$format": "json"},
    )
    return json.loads(body)["value"]


def focus_annual(indicator: str) -> pl.DataFrame:
    """Daily Focus consensus for annual targets of one indicator.

    ``baseCalculo = 0`` is the statistic over every forecast submitted in the
    last 30 days (the headline Focus number); ``1`` uses only the last 5 days and
    starts much later.
    """
    rows = _odata(
        "ExpectativasMercadoAnuais",
        f"Indicador eq '{indicator}' and baseCalculo eq 0",
        ["Data", "DataReferencia", "Media", "Mediana", "DesvioPadrao", "Minimo", "Maximo", "numeroRespondentes"],
    )
    log(f"  Focus {indicator}: {len(rows):,} rows")
    return _focus_frame(rows)


def focus_top5(indicator: str, kind: str = "M") -> pl.DataFrame:
    """Consensus of the five institutions with the best track record.

    ``kind`` is the ranking the Top 5 is drawn from: C (short), M (medium), L (long term).
    """
    rows = _odata(
        "ExpectativasMercadoTop5Anuais",
        f"Indicador eq '{indicator}' and tipoCalculo eq '{kind}'",
        ["Data", "DataReferencia", "Media", "Mediana", "DesvioPadrao", "Minimo", "Maximo"],
    )
    log(f"  Focus Top 5 {indicator}: {len(rows):,} rows")
    return _focus_frame(rows)


def _focus_frame(rows: list[dict]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(schema=FOCUS_SCHEMA)
    return (
        pl.DataFrame(rows, infer_schema_length=None)
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
            respondents=pl.col("numeroRespondentes").cast(pl.Int32) if "numeroRespondentes" in rows[0] else pl.lit(None, pl.Int32),
        )
        .select(list(FOCUS_SCHEMA))
        .cast(FOCUS_SCHEMA)
        .drop_nulls("median")
        .sort("target", "date")
    )


def parse_sgs(rows: list[dict]) -> pl.DataFrame:
    """SGS returns ``[{"data": "dd/mm/yyyy", "valor": "1.23"}]`` with numbers as strings."""
    if not rows:
        return pl.DataFrame(schema={"date": pl.Date, "value": pl.Float64})
    return (
        pl.DataFrame(rows)
        .select(
            date=pl.col("data").str.to_date("%d/%m/%Y"),
            value=pl.col("valor").cast(pl.Float64, strict=False),
        )
        .drop_nulls()
        .unique("date", keep="last")
        .sort("date")
    )


def sgs(code: int, *, daily: bool = False, start: date = date(1999, 1, 1)) -> pl.DataFrame:
    """One SGS series as ``date, value``.

    Daily series only accept queries of at most 10 years, so they are fetched in
    windows; windows that ended more than a month ago never change and are cached forever.
    """
    url = SGS.format(code=code)
    if not daily:
        return parse_sgs(json.loads(fetch(url, params={"formato": "json"})))

    today = date.today()
    frames = []
    lo = start
    while lo <= today:
        hi = min(date(lo.year + 9, 12, 31), today)
        closed = hi < today - timedelta(days=31)
        body = fetch(
            url,
            params={"formato": "json", "dataInicial": lo.strftime("%d/%m/%Y"), "dataFinal": hi.strftime("%d/%m/%Y")},
            max_age=None if closed else timedelta(hours=12),
        )
        frames.append(parse_sgs(json.loads(body)))
        lo = date(hi.year + 1, 1, 1)
    return pl.concat(frames).unique("date", keep="last").sort("date")
