"""Offline tests for the cleaning and scoring steps (no network)."""

from datetime import date

import polars as pl
import pytest

from pipeline import actuals
from pipeline.bcb import parse_sgs
from pipeline.forecasts import as_of, headline, horizon_stats, monthly, score, weekly, with_horizon


def focus(rows):
    return pl.DataFrame(rows, schema={"date": pl.Date, "target": pl.Int32, "median": pl.Float64})


def test_parse_sgs_dates_and_string_numbers():
    df = parse_sgs([{"data": "01/12/2024", "valor": "0.52"}, {"data": "01/11/2024", "valor": "0.39"}, {"data": "01/10/2024", "valor": ""}])
    assert df["date"].to_list() == [date(2024, 11, 1), date(2024, 12, 1)]
    assert df["value"].to_list() == [0.39, 0.52]


def test_compound_annual_only_complete_years():
    months = [date(2023, m, 1) for m in range(1, 13)] + [date(2024, 1, 1)]
    monthly_ = pl.DataFrame({"date": months, "value": [1.0] * 12 + [5.0]})
    out = actuals.compound_annual(monthly_)
    assert out["target"].to_list() == [2023]
    assert out["actual"][0] == pytest.approx(12.68, abs=0.01)  # 1.01^12 − 1, not 12


def test_rolling_12m_is_stamped_with_release_date():
    months = [date(2023, m, 1) for m in range(1, 13)]
    out = actuals.rolling_12m(pl.DataFrame({"date": months, "value": [1.0] * 12}))
    assert out.height == 1
    # December's IPCA becomes public on 11 January.
    assert out["available"][0] == date(2024, 1, 11)


def test_year_end_value_skips_current_year():
    daily = pl.DataFrame(
        {"date": [date(2024, 12, 30), date(2024, 12, 31), date(2025, 6, 1)], "value": [12.0, 12.25, 15.0]}
    )
    out = actuals.year_end_value(daily, today=date(2025, 10, 1))
    assert out.rows() == [(2024, 12.25)]


def test_horizon_counts_months_to_december_of_target():
    df = with_horizon(focus({"date": [date(2025, 1, 6), date(2025, 12, 1), date(2026, 3, 2), date(2024, 12, 20)], "target": [2025] * 4, "median": [0.0] * 4}))
    assert df["h"].to_list() == [11, 0, -3, 12]


def test_weekly_and_monthly_keep_the_last_survey():
    df = focus(
        {
            "date": [date(2025, 3, 3), date(2025, 3, 7), date(2025, 3, 10), date(2025, 3, 31)],
            "target": [2025] * 4,
            "median": [1.0, 2.0, 3.0, 4.0],
        }
    )
    assert weekly(df)["median"].to_list() == [2.0, 3.0, 4.0]
    m = monthly(df)
    assert m.rows(named=True)[0]["median"] == 4.0
    assert m["h"].to_list() == [9]


def test_as_of_never_uses_unreleased_values():
    cells = focus({"date": [date(2024, 1, 10), date(2024, 1, 11)], "target": [2024, 2024], "median": [4.0, 4.0]})
    known = pl.DataFrame({"available": [date(2023, 12, 11), date(2024, 1, 11)], "value": [4.7, 4.6]})
    out = as_of(cells, known, "naive")
    assert out["naive"].to_list() == [4.7, 4.6]


@pytest.fixture
def scored():
    cells = pl.DataFrame(
        {
            "target": [2020, 2020, 2021, 2021, 2022, 2022, 2023],
            "h": [12, 0, 12, 0, 12, 0, 12],
            "median": [3.0, 4.4, 3.5, 10.0, 5.0, 5.8, 4.0],
            "naive": [4.0, 4.0, 4.5, 9.0, 10.0, 6.0, 5.0],
            "top5": [None, None, 9.5, None, None, None, None],
        },
        schema_overrides={"target": pl.Int32, "h": pl.Int32},
    )
    actual = pl.DataFrame({"target": [2020, 2021, 2022], "actual": [4.5, 10.0, 5.8]}, schema_overrides={"target": pl.Int32})
    return score(cells, actual)


def test_score_keeps_pending_years_without_errors(scored):
    pending = scored.filter(target=2023)
    assert pending.height == 1 and pending["actual"][0] is None and pending["err"][0] is None
    assert scored.filter(target=2020, h=12)["err"][0] == pytest.approx(-1.5)
    assert scored.filter(target=2021, h=12)["top5_err"][0] == pytest.approx(-0.5)


def test_horizon_stats_pairs_top5_with_same_cells(scored):
    stats = horizon_stats(scored, min_years=1)
    row = stats.filter(h=12).row(0, named=True)
    assert row["n"] == 3  # 2023 has no outcome yet
    assert row["mae"] == pytest.approx((1.5 + 6.5 + 0.8) / 3)
    assert row["t5_mae"] == pytest.approx(0.5)
    assert row["cons_t5_mae"] == pytest.approx(6.5)  # only 2021, not the full-sample MAE
    assert row["t5_n"] == 1


def test_horizon_stats_hides_top5_with_too_few_years(scored):
    row = horizon_stats(scored, min_years=2).filter(h=12).row(0, named=True)
    assert row["n"] == 3 and row["t5_mae"] is None


def test_headline(scored):
    h = headline(scored)
    assert h["years"] == 3 and h["under"] == 3 and h["over"] == 0
    assert h["worst"]["year"] == 2021
    assert h["beatNaive"] == 1  # only 2022: the naive forecast is closer in 2020 and 2021


def test_weekly_and_monthly_keep_indicators_apart():
    df = pl.DataFrame(
        {
            "indicator": ["ipca", "fx"],
            "date": [date(2025, 3, 3), date(2025, 3, 4)],
            "target": [2025, 2025],
            "median": [5.0, 5.8],
        },
        schema_overrides={"target": pl.Int32},
    )
    assert weekly(df).height == 2
    assert sorted(monthly(df)["median"].to_list()) == [5.0, 5.8]
