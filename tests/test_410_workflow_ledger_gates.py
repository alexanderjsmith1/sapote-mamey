"""v9.7.410 regression tests for the four sealed gate holes in mamey/sapote_workflow.py.

Each test synthesizes only the minimal on-disk artifacts and calls the per-step checker
directly (no engine run), asserting the RC.410 fix — a gate must read real content, not
merely confirm a file exists / parses:

  * s0_seal   — a FAIL gate_validation.json is PENDING, not PASS (verdict, not presence).
  * s7_compile — the real `<!-- SAPOTE:<key> -->` marker counts as an open slot.
  * s4_modeb   — an empty / heading-only judgment card does NOT credit W4.
  * s8_suite   — the suite tool resolves to tools/check_deliverable_suite.py (it exists).
"""
import json
import os
import importlib.util

HERE = os.path.dirname(__file__)
DRIVER = os.path.join(HERE, "..", "mamey", "sapote_workflow.py")

spec = importlib.util.spec_from_file_location("sapote_workflow", DRIVER)
wf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wf)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ── Fix 1: s0_seal reads the verdict, not mere file presence ───────────────────

def _seal_pkg(pkg, gate_obj):
    os.makedirs(pkg, exist_ok=True)
    json.dump({"strain": "AS-R7", "bgcs": [{"bgc_id": "BGC001"}]},
              open(os.path.join(pkg, "manifest.json"), "w"))
    json.dump(gate_obj, open(os.path.join(pkg, "gate_validation.json"), "w"))
    open(os.path.join(pkg, "checksums_sha256.txt"), "w").write("deadbeef  manifest.json\n")


def test_seal_fail_verdict_is_pending(tmp_path):
    pkg = str(tmp_path / "package")
    _seal_pkg(pkg, {"overall": "FAIL", "status": "FAIL"})
    status, receipt = wf.s0_seal(pkg, None, {})
    # pre-.410 this returned PASS because the file merely parsed.
    assert status == wf.PENDING, receipt
    assert "pass=False" in receipt


def test_seal_pass_family_verdicts_clear(tmp_path):
    # PASS, PASS_WITH_ISSUES, MAMEY_COMPLETE and a boolean ok:true all clear the seal
    # (matches seal_package.py / discover.py vocabulary; guards the existing convention).
    for gate_obj in ({"status": "PASS"}, {"status": "pass_with_issues"},
                     {"ok": "MAMEY_COMPLETE"}, {"ok": True}):
        pkg = str(tmp_path / ("pkg_" + str(abs(hash(str(gate_obj))))))
        _seal_pkg(pkg, gate_obj)
        status, receipt = wf.s0_seal(pkg, None, {})
        assert status == wf.PASS, f"{gate_obj} -> {receipt}"


def test_seal_missing_or_unparseable_gate_is_pending(tmp_path):
    pkg = str(tmp_path / "package")
    os.makedirs(pkg, exist_ok=True)
    json.dump({"strain": "AS-R7"}, open(os.path.join(pkg, "manifest.json"), "w"))
    open(os.path.join(pkg, "checksums_sha256.txt"), "w").write("x  manifest.json\n")
    # no gate_validation.json at all
    status, _ = wf.s0_seal(pkg, None, {})
    assert status == wf.PENDING
    # malformed JSON must be caught (json.JSONDecodeError guard), not raise
    open(os.path.join(pkg, "gate_validation.json"), "w").write("{ not valid json ")
    status, receipt = wf.s0_seal(pkg, None, {})
    assert status == wf.PENDING
    assert "unparseable" in receipt or "pass=False" in receipt


# ── Fix 2: s7_compile counts the real SAPOTE slot marker ───────────────────────

def test_compile_counts_sapote_slot_marker(tmp_path):
    pkg = str(tmp_path / "package")
    os.makedirs(pkg, exist_ok=True)
    rep = os.path.join(pkg, "AS-R7_compiled_report.md")
    _write(rep,
           "# Report\n\n"
           "<!-- SAPOTE:executive_summary -->\n"
           "<!-- /SAPOTE:executive_summary -->\n"
           "<!-- SAPOTE:ecology_synthesis -->\n"
           "<!-- /SAPOTE:ecology_synthesis -->\n"
           "Some real prose here.\n")
    status, receipt = wf.s7_compile(pkg, None, {})
    # two OPEN slots -> not ready. The closing `<!-- /SAPOTE:` tags must NOT be counted.
    assert status == wf.PENDING, receipt
    assert "2 open slot" in receipt, receipt


def test_compile_no_open_slots_is_pass(tmp_path):
    pkg = str(tmp_path / "package")
    os.makedirs(pkg, exist_ok=True)
    _write(os.path.join(pkg, "AS-R7_compiled_report.md"),
           "# Report\n\nFully authored narrative, no open markers.\n")
    status, receipt = wf.s7_compile(pkg, None, {})
    assert status == wf.PASS, receipt
    assert "0 open slot" in receipt


# ── Fix 3: s4_modeb requires real content in an authored card ──────────────────

def test_modeb_empty_card_does_not_credit(tmp_path):
    pkg = str(tmp_path / "package")
    os.makedirs(pkg, exist_ok=True)
    # no COMPLETE register entry; only a heading-only skeleton file on disk.
    _write(os.path.join(pkg, "judgment", "AS-R7_mode_b_BGC001.md"),
           "# BGC001 Mode B card\n\n##  Section 1\n\n#\n")
    status, receipt = wf.s4_modeb(pkg, None, {})
    assert status == wf.PENDING, receipt


def test_modeb_authored_card_with_content_credits(tmp_path):
    pkg = str(tmp_path / "package")
    os.makedirs(pkg, exist_ok=True)
    # Two globs both match this name; dedupe must keep it a single authored card.
    # v9.7.412: W4 now applies the gold-block content-commitment floors (>= 3 recognised §-headings and
    # >= 200 non-whitespace chars); a one-line card is a stub and is no longer credited. The fixture
    # therefore carries a minimal AUTHORED body; the dedupe assertion is unchanged.
    body = "# BGC001 Mode B card\n\n" + "".join(
        f"## §{i} Section {i}\n\nThis cluster shows biosynthetic capacity consistent with a class-level read; judgment deferred.\n\n"
        for i in range(1, 5))
    _write(os.path.join(pkg, "judgment", "AS-R7_mode_b_BGC001.md"), body)
    status, receipt = wf.s4_modeb(pkg, None, {})
    assert status == wf.PASS, receipt
    assert "1 authored .md on disk" in receipt, receipt


# ── Fix 4: s8_suite resolves the real tools/ path ──────────────────────────────

def test_suite_tool_path_resolves_to_tools_dir():
    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(wf.__file__)))
    real = os.path.join(pkg_root, "tools", "check_deliverable_suite.py")
    assert os.path.isfile(real), f"expected suite tool at {real}"
    wrong = os.path.join(pkg_root, "mamey", "check_deliverable_suite.py")
    assert not os.path.exists(wrong), "the old (nonexistent) mamey/ path must stay nonexistent"


def test_suite_tool_actually_executes(tmp_path):
    # With a DELIVERABLE_MANIFEST present, the checker must REACH and RUN the real tool.
    # Pre-.410 the path was mamey/check_deliverable_suite.py (nonexistent), so subprocess
    # raised FileNotFoundError -> receipt "suite gate not run: ...". Post-fix the tool at
    # tools/ runs and the receipt reports its rc. We assert the tool ran (any rc), which is
    # only possible when the corrected path resolves.
    pkg = str(tmp_path / "package")
    deliv = str(tmp_path / "deliverables")
    os.makedirs(pkg, exist_ok=True)
    os.makedirs(deliv, exist_ok=True)
    json.dump({"strain": "AS-R7"}, open(os.path.join(pkg, "manifest.json"), "w"))
    _write(os.path.join(deliv, "DELIVERABLE_MANIFEST_AS-R7.md"), "# manifest\n")
    status, receipt = wf.s8_suite(pkg, deliv, {})
    assert receipt.startswith("check_deliverable_suite rc="), receipt
    assert "suite gate not run" not in receipt
