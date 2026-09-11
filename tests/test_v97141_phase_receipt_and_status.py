import json
from pathlib import Path

from mamey.cli import _terminal_mamey_status, _stamp_terminal_status
from mamey.recovery_status import package_status_receipt


def test_terminal_status_preserves_issue_bearing_pass():
    assert _terminal_mamey_status("PASS", []) == "MAMEY_COMPLETE"
    assert _terminal_mamey_status("PASS", ["MULTIBATCH"]) == "MAMEY_COMPLETE_WITH_ISSUES"
    assert _terminal_mamey_status("FAIL", []) == "VALIDATION_FAIL"


def test_package_status_receipt_carries_terminal_status_and_issue_count(tmp_path):
    receipt = package_status_receipt(
        tmp_path,
        validator_status="PASS",
        terminal_status="MAMEY_COMPLETE_WITH_ISSUES",
        issue_count=2,
    )
    assert receipt["package_status"] == "MAMEY_COMPLETE"
    assert receipt["terminal_status"] == "MAMEY_COMPLETE_WITH_ISSUES"
    assert receipt["issue_count"] == 2
    assert receipt["merge_semantics"] == "normal_complete_with_issues"


def test_stamp_terminal_status_updates_manifest_and_receipt(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    terminal = _stamp_terminal_status(
        tmp_path,
        validator_status="PASS",
        issues=["MULTIBATCH", "PHO_CLUSTER"],
    )
    assert terminal == "MAMEY_COMPLETE_WITH_ISSUES"
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["terminal_status"] == "MAMEY_COMPLETE_WITH_ISSUES"
    assert manifest["issue_count"] == 2
    receipt = json.loads((tmp_path / "package_status.json").read_text(encoding="utf-8"))
    assert receipt["terminal_status"] == "MAMEY_COMPLETE_WITH_ISSUES"
    assert receipt["issue_count"] == 2
    assert receipt["merge_semantics"] == "normal_complete_with_issues"
