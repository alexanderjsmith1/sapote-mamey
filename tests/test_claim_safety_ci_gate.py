import json
from pathlib import Path

from mamey.claim_safety_gate import lint_text, run_claim_safety_gate
from mamey.packaging import write_manifest


def test_claim_safety_lint_flags_known_overclaim():
    findings = lint_text("BGC001 makes desertomycin.")
    assert findings


def test_claim_safety_lint_allows_capacity_framing():
    findings = lint_text("BGC001 encodes biosynthetic capacity consistent with a desertomycin-like comparator_context.")
    assert findings == []


def test_package_manifest_records_claim_safety_pass(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "safe_Mode_B_report.md").write_text(
        "BGC001 encodes biosynthetic capacity consistent with a desertomycin-like pathway. KCB is similarity, not identity.",
        encoding="utf-8",
    )
    manifest = write_manifest(pkg)
    assert manifest["claim_safety_status"] == "PASS"
    receipt = json.loads((pkg / "claim_safety_status.json").read_text())
    assert receipt["claim_safety_status"] == "PASS"


def test_package_manifest_records_claim_safety_fail(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "unsafe_Mode_B_report.md").write_text("BGC001 makes desertomycin.", encoding="utf-8")
    manifest = write_manifest(pkg)
    assert manifest["claim_safety_status"] == "FAIL"
    receipt = json.loads((pkg / "claim_safety_status.json").read_text())
    assert receipt["finding_count"] == 1
    assert receipt["findings"][0]["path"] == "unsafe_Mode_B_report.md"


def test_package_manifest_records_claim_safety_not_requested(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    manifest = write_manifest(pkg)
    assert manifest["claim_safety_status"] == "NOT_REQUESTED"
