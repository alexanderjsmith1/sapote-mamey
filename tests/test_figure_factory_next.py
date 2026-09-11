from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

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
        [
            "identity", "role", "include_by_default", "genus", "cohort",
            "assembly_state", "assembly_reason",
        ],
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


def test_manifest_policy_vector_raster_and_deterministic_outputs(tmp_path: Path) -> None:
    first_config = _fixture(tmp_path, output_dir="outputs-a")
    second_config = _fixture(tmp_path, output_dir="outputs-b")
    first = build(first_config)
    second = build(second_config)
    first_hashes = {row["logical_locator"]: row["sha256"] for row in first["outputs"]}
    second_hashes = {row["logical_locator"]: row["sha256"] for row in second["outputs"]}
    assert first_hashes == second_hashes

    policy = first["cohort_policy"]
    assert policy["manifest_default_study_count"] == 3
    assert policy["default_study_count"] == 2
    assert policy["genus_excluded_default_study_count"] == 1
    assert policy["assembly_flag_count"] == 1
    assert policy["assembly_default_off_count"] == 1
    assert policy["selected_optional_count"] == 2
    assert first["palette"]["fill_mode"] == "SOLID"

    rows = first["denominators"]
    assert [row["group_kind"] for row in rows].count("STUDY") == 2
    assert [row["group_kind"] for row in rows].count("SENSITIVITY") == 2
    assert all(row["genus"] == "Genus alpha" for row in rows)
    assert sum(row["assembly_flagged_metric_rows"] for row in rows) == 1
    assert sum(row["assembly_default_off_metric_rows"] for row in rows) == 1

    output = tmp_path / "outputs-a"
    for profile in ("single_column", "double_column"):
        svg = output / f"figure_factory_next_{profile}.svg"
        png = output / f"figure_factory_next_{profile}.png"
        assert "<text" in svg.read_text(encoding="utf-8")
        assert png.read_bytes().startswith(b"\x89PNG")
    assert all(profile["artwork"]["svg"]["vector_preserved"] for profile in first["profiles"])
    assert all(profile["artwork"]["png"]["effective_dpi"] >= 300 for profile in first["profiles"])
    assert all(
        profile["layout"]["tick_label_data_clearance"]["status"] == "PASS"
        for profile in first["profiles"]
    )
    assert all(
        profile["layout"]["tick_label_data_clearance"]["axis_ids"] == ["main"]
        for profile in first["profiles"]
    )

    caption = (output / "figure_factory_next_caption_methods.md").read_text(encoding="utf-8")
    notes = (output / "figure_factory_next_owner_notes.json").read_text(encoding="utf-8")
    assert "Internal layout preference" not in caption
    assert "Internal layout preference" in notes
    plotted = (output / "figure_factory_next_data.tsv").read_text(encoding="utf-8")
    assert "SENSITIVITY\theld-alpha-one" in plotted
    exclusions = (output / "figure_factory_next_exclusions.tsv").read_text(encoding="utf-8")
    assert "study-beta-one" in exclusions
    assert "reference-alpha-one" in exclusions


def test_legacy_schema_hash_escape_and_unknown_cohort_fail_closed(tmp_path: Path) -> None:
    config = _fixture(tmp_path)
    payload = json.loads(config.read_text(encoding="utf-8"))
    payload["schema_version"] = "sapote.figure-factory-next.v1"
    config.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="is refused"):
        build(config)

    payload["schema_version"] = "sapote.figure-factory-next.v2"
    payload["inputs"][0]["sha256"] = "0" * 64
    config.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        build(config)

    payload["inputs"][0]["logical_locator"] = "../outside.tsv"
    config.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="escapes external_data_root"):
        build(config)

    config = _fixture(tmp_path, output_dir="outputs-b")
    payload = json.loads(config.read_text(encoding="utf-8"))
    manifest = Path(payload["external_data_root"]) / "cohort_manifest.tsv"
    text = manifest.read_text(encoding="utf-8").replace("\tBEE\t", "\tUNKNOWN_COHORT\t", 1)
    manifest.write_text(text, encoding="utf-8")
    payload["inputs"][1]["sha256"] = _sha(manifest)
    config.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="FIGURE_COHORT_PALETTE_ROLE_INVALID"):
        build(config)


def test_distributable_sources_have_no_workspace_paths_or_private_ids() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "mamey" / "figure_factory_next.py",
        root / "tools" / "figure_factory_next.py",
        root / "docs" / "FIGURE_FACTORY_NEXT.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    prohibited = ("/" + "Users/", "Co" + "dex", "Clau" + "de", "AS" + "-216")
    assert not any(marker in text for marker in prohibited)


def test_csv_sidecar_preserves_tidy_table_and_receipt(tmp_path):
    config = _fixture(tmp_path)
    receipt = build(config)
    out = tmp_path / "outputs-a"
    csv_path = out / "figure_factory_next_data.csv"
    assert csv_path.is_file(), "Missing machine-readable CSV twin"
    with csv_path.open(newline="") as handle:
        comma_rows = list(csv.DictReader(handle))
    with (out / "figure_factory_next_data.tsv").open(newline="") as handle:
        tab_rows = list(csv.DictReader(handle, delimiter="\t"))
    assert comma_rows == tab_rows
    entry = next(x for x in receipt["outputs"] if x["logical_locator"] == csv_path.name)
    assert entry["sha256"] == hashlib.sha256(csv_path.read_bytes()).hexdigest()
