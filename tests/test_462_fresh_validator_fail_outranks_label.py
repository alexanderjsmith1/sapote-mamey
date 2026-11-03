"""DREL-043: a fresh validator FAIL outranks a saved package_status label."""
import pytest

from mamey.recovery_status import infer_package_status, package_status_receipt


@pytest.mark.parametrize("label", ["MAMEY_COMPLETE", "RECOVERY_VALIDATED"])
def test_fresh_fail_overrides_explicit_label(tmp_path, label):
    receipt = package_status_receipt(tmp_path, manifest={"package_status": label}, validator_status="FAIL")
    assert receipt["package_status"] == "PARTIAL_FAILED"
    assert receipt["merge_semantics"] == "partial_or_failed_do_not_merge_as_complete"
    assert receipt["status_conflict"] == label


def test_fresh_fail_overrides_recovery_marker_file(tmp_path):
    (tmp_path / "recovery_receipt.json").write_text('{"status":"FAILED"}', encoding="utf-8")
    assert infer_package_status(tmp_path, validator_status="FAIL") == "PARTIAL_FAILED"


def test_saved_label_still_wins_without_a_fresh_verdict(tmp_path):
    receipt = package_status_receipt(tmp_path, manifest={"package_status": "RECOVERY_VALIDATED"})
    assert receipt["package_status"] == "RECOVERY_VALIDATED"
    assert receipt["status_conflict"] == ""


def test_fresh_pass_keeps_explicit_label_and_no_conflict(tmp_path):
    receipt = package_status_receipt(tmp_path, manifest={"package_status": "RECOVERY_VALIDATED"}, validator_status="PASS")
    assert receipt["package_status"] == "RECOVERY_VALIDATED"
    assert receipt["status_conflict"] == ""
