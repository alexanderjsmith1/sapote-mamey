"""plan_gtotree_iqtree: the generated 1.8.19 COMMAND.sh runs only with --approved, an approved
RUN_STATE.json for this run, and unchanged staged inputs and HMM. `/usr/bin/true` stands in for GToTree
and IQ-TREE, so no tree is built. Also: on `plan`, a --gtotree-cpu-budget that differs from
--max-concurrent-cores is refused instead of silently ignored."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "plan_gtotree_iqtree.py"
sys.path.insert(0, str(TOOL.parent))
SPEC = importlib.util.spec_from_file_location("plan_gtotree_v1guard_464r3", TOOL)
tool = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tool
SPEC.loader.exec_module(tool)

TRUE = "/usr/bin/true"


def _run_dir(tmp_path, approved):
    run = tmp_path / "run"
    (run / "input_objects").mkdir(parents=True)
    (run / "resources").mkdir()
    genome = run / "input_objects" / "g1.fna"
    genome.write_text(">c\nACGT\n")
    hmm = run / "resources" / "h.hmm"
    hmm.write_text("NAME x\n")
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    (run / "RUN_MANIFEST.json").write_text(json.dumps({
        "run_id": "r1", "assemblies": [{"object_relpath": "input_objects/g1.fna", "object_sha256": sha(genome)}],
        "hmm": {"object_relpath": "resources/h.hmm", "sha256": sha(hmm)}}))
    (run / "RUN_STATE.json").write_text(json.dumps({"run_id": "r1", "approved": approved}))
    script = run / "COMMAND.sh"
    script.write_text(tool._command_text(run, Path("resources/h.hmm"), TRUE, TRUE))
    return run, script, genome


def _bash(script, *args):
    return subprocess.run(["bash", str(script), *args], text=True, capture_output=True)


def test_refuses_without_approved_flag(tmp_path):
    run, script, _ = _run_dir(tmp_path, True)
    r = _bash(script)
    assert r.returncode == 2 and "pass --approved" in r.stderr


def test_refuses_when_run_state_not_approved(tmp_path):
    run, script, _ = _run_dir(tmp_path, False)
    r = _bash(script, "--approved")
    assert r.returncode == 2 and "does not record approved=true" in r.stderr


def test_refuses_when_a_staged_input_changed(tmp_path):
    run, script, genome = _run_dir(tmp_path, True)
    genome.write_text(">c\nTTTT\n")
    r = _bash(script, "--approved")
    assert r.returncode == 2 and "staged input changed: input_objects/g1.fna" in r.stderr


def test_runs_when_approved_and_unchanged(tmp_path):
    run, script, _ = _run_dir(tmp_path, True)
    r = _bash(script, "--approved")
    assert r.returncode == 0, r.stderr


def test_plan_refuses_a_cpu_budget_it_would_ignore(tmp_path):
    args = tool.build_parser().parse_args(["plan", "--panel-tsv", str(tmp_path / "p.tsv"), "--workspace", str(tmp_path),
                                           "--run-id", "r1", "--hmm", str(tmp_path / "h.hmm"),
                                           "--max-concurrent-cores", "4", "--gtotree-cpu-budget", "2"])
    with pytest.raises(ValueError, match="differs from --max-concurrent-cores"):
        tool.plan(args)
    args = tool.build_parser().parse_args(["plan", "--panel-tsv", str(tmp_path / "p.tsv"), "--workspace", str(tmp_path),
                                           "--run-id", "r1", "--hmm", str(tmp_path / "h.hmm")])
    assert args.gtotree_cpu_budget is None
