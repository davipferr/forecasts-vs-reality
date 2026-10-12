import polars as pl

from pipeline import frames


def test_memo_rebuilds_when_code_version_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(frames, "FRAMES", tmp_path)
    calls = []

    def build():
        calls.append(1)
        return pl.DataFrame({"x": [len(calls)]})

    monkeypatch.setattr(frames, "CODE_VERSION", "aaaaaaaaaaaa")
    assert frames.memo("t", build)["x"].to_list() == [1]
    assert frames.memo("t", build)["x"].to_list() == [1]  # fresh cache hit
    assert len(calls) == 1

    # Same age, different pipeline code: must rebuild and drop the stale copy.
    monkeypatch.setattr(frames, "CODE_VERSION", "bbbbbbbbbbbb")
    assert frames.memo("t", build)["x"].to_list() == [2]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["t-bbbbbbbbbbbb.parquet"]


def test_memo_removes_old_unversioned_file_but_not_other_frames(tmp_path, monkeypatch):
    monkeypatch.setattr(frames, "FRAMES", tmp_path)
    monkeypatch.setattr(frames, "CODE_VERSION", "aaaaaaaaaaaa")
    pl.DataFrame({"x": [0]}).write_parquet(tmp_path / "monthly.parquet")  # pre-versioning name
    frames.memo("monthly_extra", lambda: pl.DataFrame({"x": [1]}))
    frames.memo("monthly", lambda: pl.DataFrame({"x": [1]}))
    assert sorted(p.name for p in tmp_path.iterdir()) == ["monthly-aaaaaaaaaaaa.parquet", "monthly_extra-aaaaaaaaaaaa.parquet"]


def test_code_version_is_stable():
    assert frames._code_version() == frames.CODE_VERSION
    assert len(frames.CODE_VERSION) == 12
