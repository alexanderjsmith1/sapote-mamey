"""plan_gtotree_iqtree discover (legacy route): a root-level file is nominated only when it parses as
an alignment. Header-only, duplicate-label and unequal-length files are held, not PASSed."""
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "plan_gtotree_iqtree.py"
sys.path.insert(0, str(TOOL.parents[1]))
SPEC = importlib.util.spec_from_file_location("plan_gtotree_464r3", TOOL)
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)


def _run(tmp_path, alignment_text):
    run = tmp_path / "run"
    out = run / "outputs/gtotree_alignment"
    out.mkdir(parents=True)
    (run / "RUN_MANIFEST.json").write_text(json.dumps({"run_id": "x", "panel_policy": {"admitted_unique_assemblies": 2}}))
    (out / "Genomes_summary_info.tsv").write_text("genome\tstatus\na\tok\nb\tok\n")
    (out / "aligned.faa").write_text(alignment_text)
    receipt = tmp_path / "receipt.json"
    rc = tool.discover_outputs(SimpleNamespace(run_dir=str(run), receipt=str(receipt)))
    return rc, json.loads(receipt.read_text())


@pytest.mark.parametrize("text,problem", [
    (">a\n>a\n", "EMPTY_SEQUENCE"),
    (">a\nAAAA\n>a\nAAAA\n", "DUPLICATE_LABEL"),
    (">a\nAAAA\n>b\nAA\n", "UNEQUAL_SEQUENCE_LENGTHS"),
    (">a\nAAAA\n>b\n", "EMPTY_SEQUENCE"),
])
def test_malformed_alignment_is_held(tmp_path, text, problem):
    rc, data = _run(tmp_path, text)
    assert rc == 2 and data["status"] == "HOLD_MALFORMED_ALIGNMENT"
    row = next(r for r in data["observed_files"] if r["relative_path"].endswith("aligned.faa"))
    assert row["alignment_problem"].startswith(problem)


def test_valid_alignment_passes(tmp_path):
    rc, data = _run(tmp_path, ">a\nAA-A\n>b\nAAAA\n")
    assert rc == 0 and data["status"] == "PASS_UNIQUE_ALIGNMENT"
    assert data["alignment_candidates"][0]["alignment_problem"] == ""
