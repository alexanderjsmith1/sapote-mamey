"""CLAUDE_409_caption_reference_sensitivity — regression test.

The Figure Factory Next methods caption field ``benchmark_sensitivity`` used to
attribute selected sensitivity rows by the *visual* cohort field
(``row["cohort"] == "EXTERNAL_BENCHMARK"``). A REFERENCE-role strain selected as
a sensitivity row is plotted (it appears in the data TSV and in
``group_denominators``) yet contributed nothing to ``benchmark_sensitivity`` — the
caption silently understated the sensitivity analysis.

Fail-before (pristine .408): ``benchmark_sensitivity`` never mentions REFERENCE
and reports no reference count. Pass-after (.409): the field attributes every
sensitivity row to its authoritative manifest role, so REFERENCE-role sensitivity
rows appear, correctly attributed as REFERENCE, alongside the benchmark rows. The
plotted figure is unchanged (only caption/methods text is affected).
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


def _fixture(tmp_path: Path, *, output_dir: str, selected: list[str]) -> Path:
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
            ["benchmark-alpha-one", "alignment", "coverage", 4, 5, "declared-features"],
            ["reference-alpha-one", "alignment", "coverage", 2, 5, "declared-features"],
            ["reference-alpha-two", "alignment", "coverage", 3, 5, "declared-features"],
        ],
    )
    _write_tsv(
        manifest,
        ["identity", "role", "include_by_default", "genus", "cohort",
         "assembly_state", "assembly_reason"],
        [
            ["study-alpha-one", "STUDY", "true", "Genus alpha", "BEE", "PASS", "assembly checks passed"],
            ["study-alpha-two", "STUDY", "true", "Genus alpha", "WASP", "PASS", "assembly checks passed"],
            ["benchmark-alpha-one", "EXTERNAL_BENCHMARK", "false", "Genus alpha", "EXTERNAL_BENCHMARK", "PASS", "benchmark only"],
            ["reference-alpha-one", "REFERENCE", "false", "Genus alpha", "REFERENCE", "PASS", "reference only"],
            ["reference-alpha-two", "REFERENCE", "false", "Genus alpha", "REFERENCE", "PASS", "reference only"],
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
            "optional_genera": [],
            "selected_optional_genera": [],
            "selected_optional_identities": selected,
        },
        "owner_notes": [],
    }
    path = tmp_path / f"config-{output_dir}.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def _run(tmp_path: Path, output_dir: str, selected: list[str]) -> dict:
    config = _fixture(tmp_path, output_dir=output_dir, selected=selected)
    build(config)
    caption = json.loads(
        (tmp_path / output_dir / "figure_factory_next_caption_methods.json").read_text(encoding="utf-8")
    )
    return caption


def test_reference_role_sensitivity_rows_appear_in_benchmark_sensitivity(tmp_path: Path) -> None:
    # Two REFERENCE-role strains and one EXTERNAL_BENCHMARK strain, all selected as
    # sensitivity rows (default-off, not study-denominator members).
    caption = _run(
        tmp_path, "outputs-refsel",
        ["reference-alpha-one", "reference-alpha-two", "benchmark-alpha-one"],
    )
    field = caption["benchmark_sensitivity"]

    # --- fail-before on pristine .408: the pristine field is
    #     "available=..; selected=..; default_off=true; benchmarks remain excluded.."
    #     which never names REFERENCE nor carries a reference count. ---
    assert "reference_selected=2" in field
    assert "REFERENCE=2" in field  # role-attributed sensitivity-row breakdown
    assert "reference_available=2" in field

    # benchmark contribution is still reported (role-attributed, not cohort-attributed)
    assert "benchmark_selected=1" in field
    assert "EXTERNAL_BENCHMARK=1" in field
    assert "benchmark_available=1" in field

    # invariants the caption-methods validator enforces must be preserved
    assert field.count("default_off=") == 1
    assert "default_off=true" in field
    assert "excluded from study n and percentages" in field

    # The REFERENCE strains are plotted as sensitivity rows already; the caption now
    # matches what the figure data carries (the figure itself is unchanged).
    plotted = (tmp_path / "outputs-refsel" / "figure_factory_next_data.tsv").read_text(encoding="utf-8")
    assert "SENSITIVITY\treference-alpha-one" in plotted
    assert "SENSITIVITY\treference-alpha-two" in plotted


def test_benchmark_sensitivity_is_deterministic_across_runs(tmp_path: Path) -> None:
    selected = ["reference-alpha-one", "benchmark-alpha-one"]
    first = _run(tmp_path, "outputs-det-a", selected)
    second = _run(tmp_path, "outputs-det-b", selected)
    assert first["benchmark_sensitivity"] == second["benchmark_sensitivity"]
    # sorted role breakdown is stable: EXTERNAL_BENCHMARK before REFERENCE
    assert "sensitivity_rows_by_role=EXTERNAL_BENCHMARK=1,REFERENCE=1" in first["benchmark_sensitivity"]


def test_no_sensitivity_rows_reports_none_and_zero_counts(tmp_path: Path) -> None:
    # No optional identities selected: every sensitivity count is zero and the
    # role breakdown is the sentinel "none". Invariants still hold.
    caption = _run(tmp_path, "outputs-nosel", [])
    field = caption["benchmark_sensitivity"]
    assert "benchmark_selected=0" in field
    assert "reference_selected=0" in field
    assert "sensitivity_rows_by_role=none" in field
    assert field.count("default_off=") == 1
    assert "default_off=true" in field
    assert "excluded from study n and percentages" in field
