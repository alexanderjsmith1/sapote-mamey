"""Only exact success tokens count as success when inferring package_status."""
import pytest

from mamey.recovery_status import infer_package_status, package_status_receipt


@pytest.mark.parametrize("value", ["PASS", "PASS_WITH_ISSUES", "MAMEY_COMPLETE",
                                   "MAMEY_COMPLETE_WITH_ISSUES", "OK", "COMPLETE", " pass_with_issues "])
def test_recognized_success(tmp_path, value):
    assert infer_package_status(tmp_path, validator_status=value) == "MAMEY_COMPLETE"


@pytest.mark.parametrize("value", ["PASSAGE", "PASSWORD", "PASS_BUT_FAILED", "PASS_WITH_UNKNOWN_ERROR",
                                   "MAMEY_COMPLETE_NOT", "MAMEY_COMPLETE_FAILED", "FAIL", "UNKNOWN"])
def test_look_alike_is_not_success(tmp_path, value):
    receipt = package_status_receipt(tmp_path, validator_status=value)
    assert receipt["package_status"] == "PARTIAL_FAILED"
    assert receipt["merge_semantics"] == "partial_or_failed_do_not_merge_as_complete"


def test_look_alike_also_overrides_a_saved_label(tmp_path):
    receipt = package_status_receipt(tmp_path, manifest={"package_status": "MAMEY_COMPLETE"},
                                     validator_status="PASS_BUT_FAILED")
    assert receipt["package_status"] == "PARTIAL_FAILED"
    assert receipt["status_conflict"] == "MAMEY_COMPLETE"


def test_no_status_still_defaults_to_complete(tmp_path):
    assert infer_package_status(tmp_path) == "MAMEY_COMPLETE"


def test_real_validator_fail_maps_to_non_success(tmp_path):
    from mamey.validate import validate_package
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text('{"strain_id": "SYN-1", "package_status": "MAMEY_COMPLETE"}', encoding="utf-8")
    result = validate_package(pkg, gold_aware=False)
    assert result["status"] == "FAIL"
    assert result["package_status"] == "PARTIAL_FAILED"
    assert result["package_status_receipt"]["merge_semantics"] == "partial_or_failed_do_not_merge_as_complete"
