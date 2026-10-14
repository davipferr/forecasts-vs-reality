"""Offline tests for the IMF, SPF, Treasury and bond-market parsers and scoring rules."""

from datetime import date

import polars as pl
import pytest

from pipeline import countries, curve, imf, spf, treasury
from pipeline.schema import SchemaError

# ------------------------------------------------------------------ IMF


def mfpd_forecasts(rows):
    cols = ["country", "IFSCode", "year", "Round", "target_year", "h", "Fngdp_rpch", "Fpcpi_pch", "Fbca_gdp"]
    return pl.DataFrame(rows, schema=cols, orient="row")


def test_imf_horizon_matches_the_edition_month():
    fc = imf.parse_forecasts(
        mfpd_forecasts([
            ("Brazil", 223, 2019, 1, 2019, 0, 2.1, 3.6, None),  # April 2019 for 2019: 8 months to December
            ("Brazil", 223, 2019, 2, 2020, 1, 2.0, 3.6, -1.0),  # October 2019 for 2020: 14
        ])  # fmt: skip
    )
    assert sorted(fc.filter(indicator="gdp")["h"].to_list()) == [8, 14]
    # Null forecasts (current account in April) are dropped, not scored as zero.
    assert fc.filter(indicator="ca").height == 1


def test_imf_naive_uses_last_year_as_published_in_the_same_edition():
    fc = imf.parse_forecasts(
        mfpd_forecasts([("Brazil", 223, 2020, 1, 2020, 0, -5.3, 3.6, None), ("Brazil", 223, 2020, 2, 2020, 0, -5.8, 2.7, None)])
    ).filter(indicator="gdp")
    out = pl.DataFrame(
        {"ifs": [223, 223], "indicator": ["gdp", "gdp"], "target": [2019, 2020], "spring": [1.1, -4.1], "autumn": [1.14, -4.06]},
        schema_overrides={"ifs": pl.Int32, "target": pl.Int32},
    )
    s = imf.score(fc, out).sort("round")
    assert s["naive"].to_list() == [1.1, 1.14]  # April 2020 knew the April estimate of 2019; October the October one
    assert s["actual"].to_list() == [-4.06, -4.06]  # outcome: October of the following year
    assert s["err"][0] == pytest.approx(-5.3 + 4.06)


def test_imf_missing_columns_fail_clearly():
    with pytest.raises(SchemaError, match="Fpcpi_pch"):
        imf.parse_forecasts(pl.DataFrame({"IFSCode": [1], "year": [1990], "Round": [1], "target_year": [1990], "Fngdp_rpch": [1.0]}))


def test_country_table_is_unique_and_complete():
    t = countries.table()
    assert t["ifs"].n_unique() == t.height and t["iso3"].n_unique() == t.height
    assert set(t["group"]) <= {*countries.REGIONS, "agg"}
    assert t.filter(group="adv").height == 41


# ------------------------------------------------------------------ SPF


def test_spf_sheet_keeps_annual_columns_and_drops_na():
    sheet = pl.DataFrame({"YEAR": ["2024", "2024"], "QUARTER": ["3", "4"], "CPI1": ["1", "2"], "CPIA": ["3.1", "#N/A"], "CPIB": ["2.5", "2.4"]})
    out = spf.parse_sheet(sheet, "CPI").sort("quarter", "ahead")
    assert out.rows() == [(2024, 3, 0, 3.1), (2024, 3, 1, 2.5), (2024, 4, 1, 2.4)]


def test_rtdsm_vintage_years_and_monthly_obs():
    raw = pl.DataFrame({"DATE": ["1999:11", "1999:12"], "RUC99Q4": ["4.1", "#N/A"], "RUC00Q1": ["4.1", "4.0"]})
    out = spf.parse_rtdsm(raw, "RUC").sort("vintage_year", "obs")
    assert out.select("vintage_year", "vintage_q").unique().sort("vintage_year").rows() == [(1999, 4), (2000, 1)]
    assert out.filter(vintage_year=2000)["obs"].to_list() == [date(1999, 11, 1), date(1999, 12, 1)]
    assert spf.latest_level(out).sort("vintage_year")["naive"].to_list() == [4.1, 4.0]


def test_backfill_cuts_the_first_vintage_at_each_survey():
    rt = pl.DataFrame(
        {"obs": [date(1994, m, 1) for m in range(1, 7)], "vintage_year": [1994] * 6, "vintage_q": [3] * 6, "value": [1.0] * 6},
        schema_overrides={"vintage_year": pl.Int32, "vintage_q": pl.Int32},
    )
    out = spf.backfill(rt, since=1994)
    # Q1 survey (mid-February) knew January; Q2 (mid-May) knew through April.
    assert out.filter(vintage_q=1)["obs"].max() == date(1994, 1, 1)
    assert out.filter(vintage_q=2)["obs"].max() == date(1994, 4, 1)
    assert out.filter(vintage_q=3).height == 6


def test_spf_outcome_comes_from_the_q3_vintage_a_year_later():
    annual = pl.DataFrame(
        {"vintage_year": [2024, 2025, 2025], "vintage_q": [4, 2, 3], "year": [2024, 2024, 2024], "value": [2.5, 2.6, 2.8]},
        schema_overrides={"year": pl.Int32},
    )
    assert spf.outcome_from(annual).rows() == [(2024, 2.8)]


def test_spf_score_horizons_and_daily_naive():
    fc = pl.DataFrame({"year": [2024, 2024], "quarter": [4, 4], "ahead": [0, 1], "value": [5.0, 4.5]}, schema_overrides={"year": pl.Int32, "quarter": pl.Int32, "ahead": pl.Int32})
    actual = pl.DataFrame({"target": [2024, 2025], "actual": [5.1, 4.2]}, schema_overrides={"target": pl.Int32})
    daily = pl.DataFrame({"date": [date(2024, 11, 13), date(2024, 11, 14), date(2024, 11, 15)], "value": [4.4, 4.5, 9.9]})
    s = spf.score(fc, actual, daily)
    assert s["h"].to_list() == [1, 13]  # mid-November: one month to December, plus twelve for next year
    assert s["naive"].to_list() == [4.5, 4.5]  # the day before the survey, never the survey day itself
    assert s["err"].to_list() == pytest.approx([-0.1, 0.3])


def test_growth_needs_consecutive_years():
    levels = pl.DataFrame({"vintage_year": [2025] * 3, "vintage_q": [3] * 3, "year": [2021, 2022, 2024], "value": [100.0, 102.0, 110.0]})
    assert spf.growth(levels).select("year", "value").rows() == [(2022, pytest.approx(2.0))]


# ------------------------------------------------------------------ Treasury


def test_treasury_csv_parsing_tolerates_missing_maturities():
    csv = b'Date,"3 Mo","6 Mo","10 Yr"\n12/31/1990,6.63,6.73,8.08\n12/28/1990,6.64,,8.14\n'
    df = treasury.parse(csv, 1990)
    assert df.columns == ["date", "m3", "y10"]
    assert df["date"].to_list() == [date(1990, 12, 31), date(1990, 12, 28)]
    out = treasury.annual_average(df.select("date", pl.col("y10").alias("value")), today=date(1991, 6, 1))
    assert out.rows() == [(1990, pytest.approx(8.11))]


# ------------------------------------------------------------------ bond market


def test_forward_rate_from_zero_yields():
    c = pl.DataFrame({"month": [date(2000, 1, 1)], "y1": [5.0], "y2": [6.0], "y3": [6.5]})
    f = curve.forwards(c, range(0, 3))
    assert f.row(0) == (date(2000, 1, 1), 5.0, 7.0, 7.5)  # 2·6 − 5, 3·6.5 − 2·6


def test_forward_test_pairs_with_the_rate_k_years_later():
    months = [date(2000 + y, 1, 1) for y in range(3)]
    c = pl.DataFrame({"month": months, **{f"y{m}": [float(m), 2.0, 3.0] for m in range(1, 7)}})
    t = curve.forward_tests(c).filter(k=1, month=date(2000, 1, 1))
    assert t["realised"][0] == 2.0  # y1 in January 2001
    assert t["naive"][0] == 1.0


def test_inversion_episodes_merge_brief_blips():
    months = [date(2000, m, 1) for m in range(1, 13)]
    values = [0.5, -0.1, -0.2, 0.1, -0.1, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    e = curve.inversions(pl.DataFrame({"month": months, "value": values}))
    assert e.rows() == [(date(2000, 2, 1), date(2000, 5, 1), 3, -0.2)]


def test_signals_hits_false_alarms_and_ongoing_inversions():
    episodes = pl.DataFrame(
        {"start": [date(1978, 9, 1), date(2022, 7, 1)], "end": [date(1982, 6, 1), date(2024, 10, 1)], "months": [38, 28], "deepest": [-3.0, -1.4]},
        schema_overrides={"months": pl.Int32},
    )
    peaks = pl.DataFrame({"peak": [date(1980, 1, 1), date(1981, 7, 1), date(1990, 7, 1)]})
    eps, recs = curve.score_signals(episodes, peaks, date(1971, 8, 1), date(2026, 9, 1))
    assert eps["outcome"].to_list() == ["hit", "false alarm"]
    assert eps["lead"].to_list() == [16, None]
    # 1981 came during the 1978 inversion: signalled. 1990 had no inversion before it: missed.
    assert recs["signal"].to_list() == [date(1978, 9, 1), date(1978, 9, 1), None]


def test_gsw_header_is_found_after_the_notes():
    csv = b'"Note: not official"\n\nSeries,Compounding\nDate,BETA0,' + b",".join(f"SVENY{m:02d}".encode() for m in range(1, 11)) + b"\n1990-01-02,1," + b",".join(b"NA" if m > 7 else f"{m}".encode() for m in range(1, 11)) + b"\n"
    df = curve.parse_gsw(csv)
    assert df["y1"].to_list() == [1.0]
    assert df["y10"].to_list() == [None]
