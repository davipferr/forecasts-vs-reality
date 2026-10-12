from datetime import date

import polars as pl
import pytest

from pipeline import bcb
from pipeline.schema import SchemaError, require_columns

FOCUS_ROW = {
    "Data": "2025-01-03",
    "DataReferencia": "2025",
    "Media": 4.9,
    "Mediana": 5.0,
    "DesvioPadrao": 0.3,
    "Minimo": 4.0,
    "Maximo": 6.0,
    "numeroRespondentes": 80,
}


def test_passes_through_when_columns_present():
    df = pl.DataFrame({"a": [1], "b": [2], "extra": [3]})
    assert require_columns(df, ["a", "b"], "test") is df


def test_missing_column_names_source_and_suggests_rename():
    df = pl.DataFrame({"Data": ["2025-01-03"], "MedianaAgregada": [5.0]})
    with pytest.raises(SchemaError) as exc:
        require_columns(df, ["Data", "Mediana"], "Olinda")
    msg = str(exc.value)
    assert msg.startswith("Olinda: 1 expected column(s) missing")
    assert "'Mediana' (did you mean 'MedianaAgregada'?)" in msg


def test_alias_is_renamed_to_expected_name():
    for col in ("numeroRespondentes", "NumeroRespondentes"):
        out = require_columns(pl.DataFrame({col: [1]}), ["numeroRespondentes"], "x", aliases={"NumeroRespondentes": "numeroRespondentes"})
        assert out.columns == ["numeroRespondentes"]


def test_empty_frame_is_an_error():
    with pytest.raises(SchemaError, match="at least 1 row"):
        require_columns(pl.DataFrame({"a": []}), ["a"], "empty")


def test_focus_frame_parses_a_valid_row():
    df = bcb._focus_frame([FOCUS_ROW], bcb.FOCUS_ANNUAL_FIELDS, "Olinda")
    assert df.row(0, named=True) == {
        "date": date(2025, 1, 3), "target": 2025, "mean": 4.9, "median": 5.0,
        "std": 0.3, "min": 4.0, "max": 6.0, "respondents": 80,
    }  # fmt: skip


def test_focus_frame_rejects_renamed_field_and_empty_answer():
    renamed = {("Mediana_" if k == "Mediana" else k): v for k, v in FOCUS_ROW.items()}
    with pytest.raises(SchemaError, match="'Mediana'"):
        bcb._focus_frame([renamed], bcb.FOCUS_ANNUAL_FIELDS, "Olinda")
    with pytest.raises(SchemaError, match="no rows"):
        bcb._focus_frame([], bcb.FOCUS_ANNUAL_FIELDS, "Olinda")


def test_parse_sgs_rejects_unexpected_shape():
    # SGS answers some errors with a JSON object instead of a list of rows.
    with pytest.raises(SchemaError, match="SGS 433"):
        bcb.parse_sgs([{"erro": "Value(s) not found"}], "SGS 433")


def test_sgs_daily_windows_are_ten_years_and_only_recent_ones_expire():
    reqs = bcb.sgs_requests(1, daily=True, today=date(2026, 10, 12))
    assert [(p["dataInicial"], p["dataFinal"]) for _, p, _ in reqs] == [
        ("01/01/1999", "31/12/2008"),
        ("01/01/2009", "31/12/2018"),
        ("01/01/2019", "12/10/2026"),
    ]
    assert [age is None for _, _, age in reqs] == [True, True, False]
