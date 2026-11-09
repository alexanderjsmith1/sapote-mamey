"""`assembly_qc_check.py --snapshot` reads one package record and refuses other shapes clearly.

A package's own snapshot is an alias stub that resolves to its flat manifest; `from_snapshot`
iterated its top-level keys as strains and crashed (`AttributeError: 'str' object has no
attribute 'get'`).
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "assembly_qc_check.py"
SPEC = importlib.util.spec_from_file_location("aqc", TOOL)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def test_a_flat_package_record_is_one_strain(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"strain_id": "EXAMPLE", "taxonomy": "Streptomyces sp.",
                                "assembly": {"genome_bp": 8000000, "contigs": 3, "n50": 1},
                                "bgc_counts": {"raw": 30, "interior_pct": 80}}), encoding="utf-8")
    rows = MOD.from_snapshot(str(path))
    assert [r["strain"] for r in rows] == ["EXAMPLE"]
    assert rows[0]["raw_bgcs"] == 30


def test_a_cohort_snapshot_still_works(tmp_path):
    path = tmp_path / "cohort.json"
    path.write_text(json.dumps({"EXAMPLE": {"assembly": {"genome_bp": 1}, "bgc_counts": {"raw": 2}}}),
                    encoding="utf-8")
    assert [r["strain"] for r in MOD.from_snapshot(str(path))] == ["EXAMPLE"]


def test_another_shape_is_refused_with_a_message(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"EXAMPLE": "not a record"}), encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        MOD.from_snapshot(str(path))
    assert "ASSEMBLY_QC_SNAPSHOT_SHAPE" in str(exc.value)
