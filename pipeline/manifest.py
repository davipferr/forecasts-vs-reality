"""Data manifest: what each build was made from, and how it compares to the last one.

``build()`` records the code version, when each raw response was downloaded,
row counts of every cleaned frame and the headline numbers. The site publishes
it at a stable URL (``/manifest.json``), so CI can fetch the live copy before
deploying and report what changed:

    python -m pipeline.manifest publish                     # dist/_file/... -> dist/manifest.json
    python -m pipeline.manifest compare previous.json dist/manifest.json

``compare`` warns when a count under ``tables`` drops by more than
``--threshold`` (default 10 %), when a count disappears (e.g. a whole indicator)
and when an output column is removed: the usual signature of an API that changed
format or a join that broke. Changes in ``headline`` (average misses, which move
when outcomes are revised) are reported but never flagged. It never fails the
build unless ``--strict`` is given.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from . import actuals, bcb, forecasts, frames
from .http import ROOT, cached_path, full_url
from .indicators import INDICATORS

# Every SGS series the outcomes and benchmarks are built from: (code, daily, name).
SGS_SERIES = [
    (actuals.IPCA_MONTHLY, False, "IPCA, monthly change"),
    (actuals.SELIC_TARGET, True, "Selic target"),
    (actuals.PTAX_MONTH_AVG, False, "PTAX, monthly average"),
    (actuals.PTAX_DAILY, True, "PTAX, daily"),
    (actuals.GDP_ANNUAL, False, "GDP growth, annual"),
]


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def _source(name: str, url: str, params: dict | None = None) -> dict:
    """A raw response and when it entered the cache."""
    path = cached_path(url, params)
    return {"name": name, "url": full_url(url, params), "downloaded_at": _iso(path.stat().st_mtime) if path else None}


def sources() -> list[dict]:
    out = []
    for ind in INDICATORS:
        out.append(_source(f"Focus: {ind.name}", *bcb.focus_request(ind.focus)))
        if ind.top5:
            out.append(_source(f"Focus Top 5: {ind.name}", *bcb.top5_request(ind.focus)))
    for code, daily, name in SGS_SERIES:
        for url, params, _ in bcb.sgs_requests(code, daily=daily):
            window = f", {params['dataInicial'][-4:]}–{params['dataFinal'][-4:]}" if daily else ""
            out.append(_source(f"SGS {code}: {name}{window}", url, params))
    return out


def _table(df: pl.DataFrame, *, counts: dict[str, pl.Expr] | None = None) -> dict:
    """Row count and columns, plus per-indicator counts (``{name: expr}``, each
    aggregated per indicator; ``rows`` is always included)."""
    out: dict = {"rows": df.height, "columns": df.columns}
    aggs = {"rows": pl.len(), **(counts or {})}
    per = df.group_by("indicator").agg(**aggs).sort("indicator")
    for name in aggs:
        out[f"{name}_by_indicator"] = {r["indicator"]: int(r[name]) for r in per.iter_rows(named=True)}
    return out


def build() -> dict:
    daily = frames.focus_daily()
    top5 = frames.top5_daily()
    res = frames.outcomes()
    known = frames.known()
    m = frames.monthly()

    headline = {}
    for ind in INDICATORS:
        h = forecasts.headline(m.filter(indicator=ind.id))
        headline[ind.id] = {k: round(v, 4) if isinstance(v, float) else v for k, v in h.items() if k in ("years", "mae", "bias", "under", "over", "naiveMae", "beatNaive")}

    last_survey = daily.group_by("indicator").agg(pl.col("date").max()).sort("indicator")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "commit": os.environ.get("GITHUB_SHA"),
        "pipeline_code": frames.CODE_VERSION,
        "last_survey": {r["indicator"]: r["date"].isoformat() for r in last_survey.iter_rows(named=True)},
        "sources": sources(),
        "tables": {
            "focus_daily": _table(daily, counts={"target_years": pl.col("target").n_unique()}),
            "top5_daily": _table(top5, counts={"target_years": pl.col("target").n_unique()}),
            "outcomes": _table(res, counts={"known_outcomes": pl.col("actual").is_not_null().sum()}),
            "known": _table(known),
            "monthly": _table(m, counts={"scored_cells": pl.col("err").is_not_null().sum()}),
        },
        "headline": headline,
    }


# ------------------------------------------------------------------- compare


def _numbers(d: dict, prefix: str = "") -> dict[str, float]:
    """Flatten numeric leaves: {"monthly": {"rows": 3}} -> {"monthly.rows": 3}."""
    out: dict[str, float] = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out |= _numbers(v, f"{key}.")
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = v
    return out


def _fmt(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}" if abs(v) >= 100 or float(v).is_integer() else f"{v:,.4g}"


def _changes(old: dict, new: dict, prefix: str, flag_drops: bool, threshold: float) -> tuple[list[str], list[str], int]:
    """Markdown rows of changed metrics, warnings, and how many were unchanged."""
    rows: list[str] = []
    warnings: list[str] = []
    unchanged = 0
    a, b = _numbers(old, f"{prefix}."), _numbers(new, f"{prefix}.")
    for key in sorted(a.keys() | b.keys()):
        va, vb = a.get(key), b.get(key)
        if va == vb:
            unchanged += 1
            continue
        change = (vb - va) / abs(va) if va not in (None, 0) and vb is not None else None
        flag = False
        if flag_drops and vb is None:
            flag = True
            warnings.append(f"{key} disappeared (was {_fmt(va)})")
        elif flag_drops and change is not None and change < -threshold:
            flag = True
            warnings.append(f"{key} dropped {-change:.0%}: {_fmt(va)} → {_fmt(vb)}")
        rows.append(f"| {'⚠ ' if flag else ''}`{key}` | {_fmt(va)} | {_fmt(vb)} | {'—' if change is None else f'{change:+.1%}'} |")
    return rows, warnings, unchanged


def compare(old: dict, new: dict, threshold: float = 0.10) -> tuple[str, list[str]]:
    """Markdown report of changed metrics, and the list of warnings."""
    rows, warnings, unchanged = _changes(old.get("tables", {}), new.get("tables", {}), "tables", True, threshold)
    h_rows, _, h_unchanged = _changes(old.get("headline", {}), new.get("headline", {}), "headline", False, threshold)
    rows += h_rows
    unchanged += h_unchanged

    for name, table in new.get("tables", {}).items():
        before = set(old.get("tables", {}).get(name, {}).get("columns", []))
        after = set(table.get("columns", []))
        if before and (gone := before - after):
            warnings.append(f"{name}: columns removed: {', '.join(sorted(gone))}")
        if before and (added := after - before):
            rows.append(f"| `{name}.columns` | | +{', '.join(sorted(added))} | |")

    lines = [
        "## Data manifest vs. live site",
        "",
        f"Previous build: {old.get('generated_at', '?')} (code `{old.get('pipeline_code', '?')}`) · "
        f"this build: {new.get('generated_at', '?')} (code `{new.get('pipeline_code', '?')}`)",
        "",
    ]
    if warnings:
        lines += [f"### ⚠ {len(warnings)} warning(s)", "", *[f"- {w}" for w in warnings], ""]
    if rows:
        lines += ["| Metric | Previous | Current | Change |", "|---|--:|--:|--:|", *rows, ""]
    lines.append(f"{unchanged} metric(s) unchanged.")
    lines += ["", "### Sources", "", "| Source | Downloaded |", "|---|---|"]
    lines += [f"| [{f['name']}]({f['url']}) | {f['downloaded_at'] or '—'} |" for f in new.get("sources", [])]
    return "\n".join(lines) + "\n", warnings


def _load(path: Path) -> dict | None:
    try:
        # utf-8-sig: tolerate a BOM (e.g. a manifest saved by Windows PowerShell).
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def _publish(dist: Path) -> Path:
    """Copy Framework's content-hashed copy of the manifest to a stable URL."""
    candidates = [p for p in dist.glob("_file/**/manifest*.json") if re.fullmatch(r"manifest(\.[0-9a-f]+)?\.json", p.name)]
    if len(candidates) != 1:
        raise SystemExit(f"expected one built manifest under {dist}/_file, found {len(candidates)}: {candidates}")
    target = dist / "manifest.json"
    shutil.copyfile(candidates[0], target)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.manifest")
    sub = parser.add_subparsers(dest="cmd", required=True)
    pub = sub.add_parser("publish", help="copy the built manifest to dist/manifest.json")
    pub.add_argument("--dist", type=Path, default=ROOT / "dist")
    cmp_ = sub.add_parser("compare", help="report changes between two manifests")
    cmp_.add_argument("previous", type=Path)
    cmp_.add_argument("current", type=Path)
    cmp_.add_argument("--threshold", type=float, default=0.10, help="warn on drops larger than this fraction")
    cmp_.add_argument("--strict", action="store_true", help="exit 1 when there are warnings")
    args = parser.parse_args(argv)

    if args.cmd == "publish":
        print(f"manifest published at {_publish(args.dist)}")
        return 0

    new = _load(args.current)
    if new is None:
        print(f"::error::cannot read {args.current}")
        return 1
    old = _load(args.previous)
    if old is None:
        report, warnings = "## Data manifest\n\nNo previous manifest to compare with (first deploy?).\n", []
    else:
        report, warnings = compare(old, new, args.threshold)

    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(report)
    else:
        # As bytes: the report has "⚠" and "→", which a Windows console codepage can't encode.
        sys.stdout.flush()
        sys.stdout.buffer.write(report.encode("utf-8"))
        sys.stdout.buffer.flush()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        for w in warnings:
            print(f"::warning title=Data regression::{w}")
    return 1 if args.strict and warnings else 0


if __name__ == "__main__":
    raise SystemExit(main())
