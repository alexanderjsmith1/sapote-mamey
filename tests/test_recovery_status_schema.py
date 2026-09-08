import json
from pathlib import Path

from mamey.packaging import write_manifest
from mamey.recovery_status import infer_package_status, package_status_receipt
from mamey.validate import validate_package


def _minimal_pkg(tmp_path: Path):
    pkg = tmp_path / "package"
    pkg.mkdir(parents=True)
    # required-ish suffix fixtures for write_manifest/status tests; validate tests use explicit recovery only
    (pkg / "dummy_1_intake.json").write_text("{}", encoding="utf-8")
    (pkg / "dummy_2_inventory.csv").write_text("BGC_ID\n", encoding="utf-8")
    (pkg / "dummy_3_bgc_data.json").write_text("{}", encoding="utf-8")
    (pkg / "dummy_4_triage_board.csv").write_text("BGC_ID\n", encoding="utf-8")
    (pkg / "dummy_4A_RGGMCI_full.json").write_text('{"status":"NULL_NO_RGGMCI_PAIRS","pairs_total":0,"reference_record_count":0}', encoding="utf-8")
    return pkg


def test_write_manifest_defaults_to_mamey_complete(tmp_path):
    pkg = _minimal_pkg(tmp_path)
    manifest = write_manifest(pkg)
    assert manifest["package_status"] == "MAMEY_COMPLETE"
    receipt = json.loads((pkg / "package_status.json").read_text())
    assert receipt["package_status"] == "MAMEY_COMPLETE"


def test_recovery_validated_is_not_classified_as_mamey_complete(tmp_path):
    pkg = _minimal_pkg(tmp_path)
    (pkg / "recovery_receipt.json").write_text('{"status":"RECOVERY_VALIDATED"}', encoding="utf-8")
    manifest = write_manifest(pkg)
    assert manifest["package_status"] == "RECOVERY_VALIDATED"
    receipt = package_status_receipt(pkg, manifest=manifest, validator_status="PASS")
    assert receipt["package_status"] == "RECOVERY_VALIDATED"
    assert receipt["merge_semantics"] == "validated_recovery_not_uninterrupted"


def test_recovery_needed_and_partial_failed_statuses(tmp_path):
    pkg = _minimal_pkg(tmp_path)
    (pkg / "RECOVERY_NEEDED.json").write_text("{}", encoding="utf-8")
    assert infer_package_status(pkg) == "RECOVERY_NEEDED"

    pkg2 = _minimal_pkg(tmp_path / "other")
    assert infer_package_status(pkg2, validator_status="FAIL") == "PARTIAL_FAILED"


def test_unrecognized_status_fails_safe_not_complete(tmp_path):
    """CORE-P02: a non-empty, non-success validator status must not render MAMEY_COMPLETE."""
    for bad in ("GATE_FAILED", "INCOMPLETE", "ERROR", "WEIRD_UNKNOWN"):
        pkg = _minimal_pkg(tmp_path / bad.lower())
        status = infer_package_status(pkg, validator_status=bad)
        assert status == "PARTIAL_FAILED", f"{bad} should fail safe, got {status}"
        receipt = package_status_receipt(pkg, validator_status=bad)
        assert receipt["merge_semantics"] == "partial_or_failed_do_not_merge_as_complete"
    # affirmative signals and the empty packaging-time default still read complete
    ok = _minimal_pkg(tmp_path / "ok")
    assert infer_package_status(ok, validator_status="PASS_WITH_ISSUES") == "MAMEY_COMPLETE"
    assert infer_package_status(_minimal_pkg(tmp_path / "empty")) == "MAMEY_COMPLETE"


def test_validate_package_surfaces_package_status(tmp_path):
    pkg = _minimal_pkg(tmp_path)
    (pkg / "recovery_receipt.json").write_text('{"status":"RECOVERY_VALIDATED"}', encoding="utf-8")
    write_manifest(pkg)
    result = validate_package(pkg, gold_aware=False)
    assert result["package_status"] == "RECOVERY_VALIDATED"
    assert result["package_status_receipt"]["merge_semantics"] == "validated_recovery_not_uninterrupted"
