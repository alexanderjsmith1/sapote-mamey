"""Wiring tests for the `mamey figure-factory` subcommand (v9.7.409).

The Figure Factory is a full subsystem (mamey/figure_factory_next.py) that was
previously reachable only via `python tools/figure_factory_next.py --config <json>`.
These tests pin the CLI wiring: the subcommand is registered, dispatches to the
command function, and drives the existing `build()` on a real hash-bound config.

Filename and the two cheap wiring tests deliberately avoid the conftest.py
slow-partition hints ("figure"/"atlas"/...) so they run in the default fast
partition and guard the wiring continuously; the one test that actually renders a
figure suite (matplotlib) carries an explicit @pytest.mark.slow instead.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey import cli


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_tsv(path: Path, fields: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fields)
        writer.writerows(rows)


def _aggregate_config(tmp_path: Path, *, output_dir: str = "outputs") -> Path:
    """A minimal, self-contained sapote.figure-factory-next.v2 config (mirrors the
    fixture in tests/test_figure_factory_next.py) so the CLI path renders a real suite."""
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
        ],
    )
    _write_tsv(
        manifest,
        ["identity", "role", "include_by_default", "genus", "cohort",
         "assembly_state", "assembly_reason"],
        [
            ["study-alpha-one", "STUDY", "true", "Genus alpha", "BEE", "PASS", "assembly checks passed"],
            ["study-alpha-two", "STUDY", "true", "Genus alpha", "WASP", "PASS", "assembly checks passed"],
            ["study-beta-one", "STUDY", "true", "Genus beta", "ATTINE", "PASS", "assembly checks passed"],
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
            "selected_optional_identities": [],
        },
        "owner_notes": ["Internal layout preference; never scientific caption text."],
    }
    path = tmp_path / f"config-{output_dir}.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    return path


def test_ff_subcommand_registered_and_dispatches() -> None:
    """The subcommand exists on the parser and binds args.func to the command fn."""
    parser = cli.build_parser()
    args = parser.parse_args(["figure-factory", "--config", "some_config.json"])
    assert args.command == "figure-factory"
    assert args.config == "some_config.json"
    # set_defaults(func=...) is the dispatch idiom main() invokes via args.func(args).
    assert getattr(args, "func", None) is cli.figure_factory_command


def test_ff_command_reports_missing_config(tmp_path: Path) -> None:
    """A missing config is a clean, non-crashing exit — no build attempted."""
    rc = cli.figure_factory_command(SimpleNamespace(config=str(tmp_path / "nope.json")))
    assert rc == 1


@pytest.mark.slow
def test_ff_command_runs_a_real_aggregate_config(tmp_path: Path) -> None:
    """End-to-end: the command drives build() and lands a real figure suite on disk."""
    config = _aggregate_config(tmp_path, output_dir="outputs")
    rc = cli.figure_factory_command(SimpleNamespace(config=str(config)))
    assert rc == 0
    out = tmp_path / "outputs"
    receipt = json.loads((out / "figure_factory_next_receipt.json").read_text(encoding="utf-8"))
    assert receipt["schema_version"] == "sapote.figure-factory-next.v2"
    assert (out / "figure_factory_next_single_column.svg").is_file()
    assert (out / "figure_factory_next_single_column.png").read_bytes().startswith(b"\x89PNG")
