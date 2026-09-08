"""v9.7.412 — W4 (Mode B cards) content-commitment floors + strict verify-modeb invocation.

Fail-before (sealed .411): a judgment card holding ONE prose line passed W4 ("authored .md on disk").
Synthetic packages only; no engine run.
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(__file__)
DRIVER = os.path.join(HERE, "..", "mamey", "sapote_workflow.py")
spec = importlib.util.spec_from_file_location("sapote_workflow_412", DRIVER)
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)


def _pkg_through_w3(root, strain="AS-TEST"):
    pkg = os.path.join(root, strain, "package")
    os.makedirs(os.path.join(pkg, "judgment"), exist_ok=True)
    os.makedirs(os.path.join(pkg, "mode_b_templates"), exist_ok=True)
    json.dump({"strain": strain, "bgcs": [{"bgc_id": "BGC001"}]}, open(os.path.join(pkg, "manifest.json"), "w"))
    json.dump({"status": "MAMEY_COMPLETE", "checksum_integrity": "PASS"}, open(os.path.join(pkg, "gate_validation.json"), "w"))
    open(os.path.join(pkg, "checksums_sha256.txt"), "w").write("deadbeef  manifest.json\n")
    open(os.path.join(pkg, f"{strain}_4_triage_board.csv"), "w").write("BGC_ID\nBGC001\n")
    open(os.path.join(pkg, f"{strain}_4c_AB_lead_board.csv"), "w").write("BGC_ID\nBGC001\n")
    open(os.path.join(pkg, f"{strain}_4c_AF_lead_board.csv"), "w").write("BGC_ID\nBGC001\n")
    open(os.path.join(pkg, "mode_b_templates", f"{strain}_BGC001_ModeB.md"), "w").write("## §1 ...\n")
    return pkg


def _w4(pkg, strict=False):
    ctx, results, order = wf.run(pkg, None, strict=strict)
    return results["W4"]["status"], results["W4"]["receipt"]


def test_one_line_stub_card_no_longer_passes_w4(tmp_path):
    pkg = _pkg_through_w3(str(tmp_path))
    open(os.path.join(pkg, "judgment", "AS-TEST_BGC001_mode_b.md"), "w").write("# BGC001\n\nsome prose\n")
    status, receipt = _w4(pkg)
    assert status == wf.PENDING, receipt
    assert "below the content floors" in receipt


def test_card_meeting_the_floors_passes_w4_non_strict(tmp_path):
    pkg = _pkg_through_w3(str(tmp_path))
    body = "".join(f"## §{i} Section {i}\n\n" + ("authored evidence text " * 6) + "\n\n" for i in range(1, 5))
    open(os.path.join(pkg, "judgment", "AS-TEST_BGC001_mode_b.md"), "w").write(body)
    status, receipt = _w4(pkg)
    assert status == wf.PASS, receipt


def test_strict_mode_invokes_verify_modeb_and_fails_closed(tmp_path, monkeypatch):
    pkg = _pkg_through_w3(str(tmp_path))
    body = "".join(f"## §{i} Section {i}\n\n" + ("authored evidence text " * 6) + "\n\n" for i in range(1, 5))
    open(os.path.join(pkg, "judgment", "AS-TEST_BGC001_mode_b.md"), "w").write(body)
    calls = []
    monkeypatch.setattr(wf, "_run_verify_modeb", lambda p, c: calls.append(c) or 1)
    status, receipt = _w4(pkg, strict=True)
    assert calls, "strict mode must invoke the verifier"
    assert status == wf.PENDING and "fail verify-modeb" in receipt
    monkeypatch.setattr(wf, "_run_verify_modeb", lambda p, c: 0)
    status, receipt = _w4(pkg, strict=True)
    assert status == wf.PASS and "all pass verify-modeb" in receipt


def test_verifier_launch_failure_is_not_credited(tmp_path, monkeypatch):
    pkg = _pkg_through_w3(str(tmp_path))
    body = "".join(f"## §{i} Section {i}\n\n" + ("authored evidence text " * 6) + "\n\n" for i in range(1, 5))
    open(os.path.join(pkg, "judgment", "AS-TEST_BGC001_mode_b.md"), "w").write(body)
    monkeypatch.setattr(wf.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(OSError("no interpreter")))
    assert wf._run_verify_modeb(pkg, os.path.join(pkg, "judgment", "AS-TEST_BGC001_mode_b.md")) == 2
