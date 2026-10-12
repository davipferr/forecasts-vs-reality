import json

import polars as pl

from pipeline import manifest


def _manifest(tables=None, headline=None):
    return {"generated_at": "2026-10-01T00:00:00+00:00", "pipeline_code": "abc", "sources": [], "tables": tables or {}, "headline": headline or {}}


def test_table_counts_by_indicator():
    df = pl.DataFrame({"indicator": ["ipca", "ipca", "fx"], "target": [2024, 2025, 2025]})
    t = manifest._table(df, counts={"target_years": pl.col("target").n_unique()})
    assert t == {
        "rows": 3,
        "columns": ["indicator", "target"],
        "rows_by_indicator": {"fx": 1, "ipca": 2},
        "target_years_by_indicator": {"fx": 1, "ipca": 2},
    }


def test_compare_flags_drops_missing_metrics_and_removed_columns():
    old = _manifest(
        {
            "monthly": {"rows": 1000, "columns": ["a", "b"], "rows_by_indicator": {"fx": 600, "ipca": 400}},
            "outcomes": {"rows": 50, "columns": ["target"]},
        }
    )
    new = _manifest(
        {
            "monthly": {"rows": 1100, "columns": ["a", "c"], "rows_by_indicator": {"ipca": 1100}},  # fx vanished
            "outcomes": {"rows": 40, "columns": ["target"]},  # -20 %
        }
    )
    report, warnings = manifest.compare(old, new, threshold=0.10)
    assert warnings == [
        "tables.monthly.rows_by_indicator.fx disappeared (was 600)",
        "tables.outcomes.rows dropped 20%: 50 → 40",
        "monthly: columns removed: b",
    ]
    assert "| `tables.monthly.rows` | 1,000 | 1,100 | +10.0% |" in report  # growth is reported, not flagged
    assert "+c" in report


def test_headline_changes_are_reported_but_never_flagged():
    old = _manifest(headline={"gdp": {"mae": 1.6, "years": 26}})
    new = _manifest(headline={"gdp": {"mae": 1.2}})  # revised GDP; and "years" missing
    report, warnings = manifest.compare(old, new)
    assert warnings == []
    assert "`headline.gdp.mae` | 1.6 | 1.2 | -25.0% |" in report


def test_compare_identical_manifests_is_quiet():
    m = _manifest({"monthly": {"rows": 10, "columns": ["a"]}}, {"ipca": {"mae": 1.5}})
    report, warnings = manifest.compare(m, m)
    assert warnings == []
    assert "2 metric(s) unchanged." in report  # columns aren't metrics


def test_cli_compare_without_previous_manifest(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    current = tmp_path / "manifest.json"
    current.write_text(json.dumps(_manifest({"monthly": {"rows": 1}})), encoding="utf-8")
    assert manifest.main(["compare", str(tmp_path / "missing.json"), str(current)]) == 0
    assert "No previous manifest" in capsys.readouterr().out


def test_cli_strict_fails_on_warnings(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    old, new = tmp_path / "old.json", tmp_path / "new.json"
    old.write_text(json.dumps(_manifest({"monthly": {"rows": 100}})), encoding="utf-8")
    new.write_text(json.dumps(_manifest({"monthly": {"rows": 10}})), encoding="utf-8")
    assert manifest.main(["compare", str(old), str(new)]) == 0
    assert manifest.main(["compare", str(old), str(new), "--strict"]) == 1


def test_publish_copies_hashed_manifest_to_stable_path(tmp_path):
    built = tmp_path / "_file" / "data" / "manifest.1a2b3c4d.json"
    built.parent.mkdir(parents=True)
    built.write_text('{"ok": true}', encoding="utf-8")
    assert manifest.main(["publish", "--dist", str(tmp_path)]) == 0
    assert json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8")) == {"ok": True}
