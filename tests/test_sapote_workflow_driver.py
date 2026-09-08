"""Hermetic tests for tools/sapote_workflow.py — the mandatory Sapote workflow gate.

These build tiny fake package dirs (no engine run) and assert the driver's two core
guarantees: (1) order enforcement — a mandatory step is BLOCKED until its predecessor
PASSES; (2) artifact-driven advancement — adding the real artifact flips the step to PASS
and unblocks the next. Fail-closed: a missing artifact is PENDING, never silently PASS.
"""
import json
import os
import sys
import importlib.util

HERE = os.path.dirname(__file__)
DRIVER = os.path.join(HERE, "..", "mamey", "sapote_workflow.py")  # tools/ is a thin shim

spec = importlib.util.spec_from_file_location("sapote_workflow", DRIVER)
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)


def _seal(pkg, strain="AS-TEST", n_bgc=3):
    """Write the minimum artifacts that make W0 (seal) PASS."""
    os.makedirs(pkg, exist_ok=True)
    json.dump({"strain": strain, "bgcs": [{"bgc_id": f"BGC00{i}"} for i in range(1, n_bgc + 1)]},
              open(os.path.join(pkg, "manifest.json"), "w"))
    json.dump({"ok": "MAMEY_COMPLETE"}, open(os.path.join(pkg, "gate_validation.json"), "w"))
    open(os.path.join(pkg, "checksums_sha256.txt"), "w").write("deadbeef  manifest.json\n")
    return strain


def _status(pkg, sid):
    ctx, results, order = wf.run(pkg, None)
    return {s: results[s]["status"] for s in order}


def test_seal_only_blocks_downstream(tmp_path):
    pkg = str(tmp_path / "package")
    _seal(pkg)
    st = _status(pkg, "AS-TEST")
    assert st["W0"] == wf.PASS
    # nothing downstream of W1 authored -> W1 pending, and everything after BLOCKED
    assert st["W1"] == wf.PENDING
    for s in ["W3", "W4", "W6", "W7", "W8", "W9", "W10"]:
        assert st[s] in (wf.BLOCKED, wf.PENDING)
    # W4 must be BLOCKED (its predecessor W3 is not PASS)
    assert st["W4"] == wf.BLOCKED


def test_triage_and_leads_advance(tmp_path):
    pkg = str(tmp_path / "package")
    _seal(pkg)
    open(os.path.join(pkg, "AS-TEST_4_triage_board.csv"), "w").write("BGC_ID,rank\nBGC001,1\nBGC002,2\n")
    open(os.path.join(pkg, "AS-TEST_4c_AB_lead_board.csv"), "w").write("BGC_ID,ab\nBGC001,80\n")
    open(os.path.join(pkg, "AS-TEST_4c_AF_lead_board.csv"), "w").write("BGC_ID,af\nBGC002,70\n")
    st = _status(pkg, "AS-TEST")
    assert st["W1"] == wf.PASS
    assert st["W2"] == wf.PASS
    # W3 still pending (no templates) -> W4 BLOCKED
    assert st["W3"] == wf.PENDING
    assert st["W4"] == wf.BLOCKED


def test_templates_unblock_modeb(tmp_path):
    pkg = str(tmp_path / "package")
    _seal(pkg)
    open(os.path.join(pkg, "AS-TEST_4_triage_board.csv"), "w").write("BGC_ID\nBGC001\n")
    open(os.path.join(pkg, "AS-TEST_4c_AB_lead_board.csv"), "w").write("BGC_ID\nBGC001\n")
    open(os.path.join(pkg, "AS-TEST_4c_AF_lead_board.csv"), "w").write("BGC_ID\nBGC001\n")
    tdir = os.path.join(pkg, "mode_b_templates")
    os.makedirs(tdir)
    open(os.path.join(tdir, "AS-TEST_BGC001_ModeB.md"), "w").write("## \u00a71 ...\n")
    st = _status(pkg, "AS-TEST")
    assert st["W3"] == wf.PASS
    # W4 now reachable and PENDING (templates exist, no COMPLETE cards yet), not BLOCKED
    assert st["W4"] == wf.PENDING


def test_strict_exit_nonzero_when_incomplete(tmp_path, monkeypatch):
    pkg = str(tmp_path / "package")
    _seal(pkg)
    monkeypatch.setattr(sys, "argv", ["sapote_workflow.py", "--package", pkg, "--strict"])
    rc = wf.main()
    assert rc == 1  # mandatory steps incomplete -> fail closed


def test_missing_package_dir_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["sapote_workflow.py", "--package", str(tmp_path / "nope")])
    rc = wf.main()
    assert rc == 2


def test_cli_and_tools_shim_share_one_implementation():
    """tools/sapote_workflow.py must hold no logic — it delegates to mamey.sapote_workflow.

    The v9.7.213 tools/ audit retired build_master_figure_atlas.py for being a duplicate CLI
    shim that could drift. This pins the shim as a delegator.
    """
    import os
    shim = os.path.join(HERE, "..", "tools", "sapote_workflow.py")
    src = open(shim, encoding="utf-8").read()
    assert "from mamey.sapote_workflow import main" in src
    assert "def run(" not in src and "STEPS" not in src, "shim must not reimplement the driver"


def test_mamey_workflow_subcommand_is_registered():
    """`mamey workflow` must exist and dispatch to workflow_command."""
    from mamey.cli import build_parser
    p = build_parser()
    actions = [a for a in p._actions if hasattr(a, "choices") and a.choices]
    names = set()
    for a in actions:
        try:
            names.update(a.choices.keys())
        except AttributeError:
            pass
    assert "workflow" in names, f"`mamey workflow` not registered; found {sorted(names)[:12]}"
