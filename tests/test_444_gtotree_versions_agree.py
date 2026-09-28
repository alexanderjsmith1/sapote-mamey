"""The planner, the execution gate and the workflow doc accept one list of GToTree versions.

Before: the planner accepted only 1.8.16, the gate only 1.8.19 or 2.0.x, and the doc bound 1.8.19, so no version passed
all three (rare-genera trees, 2026-09-27, held at HOLD_UNVERIFIED_VERSION on 1.8.19).
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{name}_444_versions", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


planner = _load("plan_gtotree_iqtree")
gate = _load("gtotree_execution_gate")
shared = _load("_gtotree_versions")

VERSIONS = [("GToTree v1.8.19", True), ("1.8.19", True), ("GToTree v2.0.0", True), ("GToTree v2.0.3", True),
            ("GToTree v1.8.16", False), ("GToTree v1.8.1", False), ("GToTree v1.8.190", False), ("", False)]


def _planner_verdict(monkeypatch, version):
    def fake_run(argv, **kwargs):
        if argv[0].endswith("GToTree"):
            text = version if argv[1] == "-v" else " ".join(planner.REQUIRED_GTOTREE_HELP)
        else:
            text = "IQ-TREE 3.1.2" if argv[1] == "--version" else " ".join(planner.REQUIRED_IQTREE_HELP)
        return SimpleNamespace(stdout=text, stderr="", returncode=0)
    monkeypatch.setattr(planner.subprocess, "run", fake_run)
    return planner.probe_toolchain("/x/GToTree", "/x/iqtree3")["gtotree"]["verified_interface"]


@pytest.mark.parametrize("version,ok", VERSIONS)
def test_planner_gate_and_shared_list_agree(monkeypatch, version, ok):
    assert shared.accepted(version) is ok
    assert bool(gate._ACCEPTED_GTOTREE_VERSIONS.search(version)) is ok
    assert (_planner_verdict(monkeypatch, version) == "PASS") is ok


def test_the_doc_states_the_same_list():
    doc = (ROOT / "docs" / "GTOTREE_WORKFLOW.md").read_text()
    for v in shared.ACCEPTED_GTOTREE_VERSIONS_TEXT:
        assert f"| {v} |" in doc
    assert "tools/_gtotree_versions.py" in doc


def test_threads_per_tree_sets_every_thread_flag():
    text = planner._command_text(Path("/tmp/run"), Path("hmm/targets.hmm"), "GToTree", "iqtree3", threads=4)
    assert '"-n" "4"' in text.replace("'", '"') or "-n 4" in text
    assert "-M 4" in text and "-T 4" in text and "-j 1" in text
    one = planner._command_text(Path("/tmp/run"), Path("hmm/targets.hmm"), "GToTree", "iqtree3")
    assert "-n 1" in one and "-M 1" in one and "-T 1" in one


def test_threads_cannot_exceed_the_core_ceiling():
    args = SimpleNamespace(max_concurrent_cores=2, threads_per_tree=3, prepared_panel=None)
    with pytest.raises(ValueError, match="threads-per-tree"):
        planner.plan(args)
    parser = planner.build_parser()
    parsed = parser.parse_args(["plan", "--panel-tsv", "p.tsv", "--workspace", "w", "--run-id", "x", "--hmm", "h.hmm"])
    assert parsed.threads_per_tree == 1
