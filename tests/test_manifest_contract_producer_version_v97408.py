"""v9.7.408 — the manifest-contract advisory reports which engine sealed the package.

The contract describes the CURRENT manifest shape, so a package sealed by an older
engine can only fail it — and does so for provenance reasons, not defects. Without the
producing version in the result, `MANIFEST_CONTRACT: FAIL (16 artifacts; 6 errors)` reads
identically for a stale package and a broken one, and a reader has to open the manifest to
tell them apart.

These tests pin that the context is present, that it stays quiet when there is nothing to
report, and — most importantly — that adding it changed no verdict.
"""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from mamey.manifest_schema import check_package_contract


def _pkg(tmp_path, manifest_text=None):
    if manifest_text is not None:
        (tmp_path / "manifest.json").write_text(manifest_text, encoding="utf-8")
    return tmp_path


def test_producer_version_is_reported_when_present(tmp_path):
    _pkg(tmp_path, json.dumps({"workflow_version": "Mamey v1.9.142"}))
    result = check_package_contract(tmp_path)
    assert result["producer_workflow_version"] == "Mamey v1.9.142"


def test_producer_version_is_none_when_manifest_absent(tmp_path):
    result = check_package_contract(tmp_path)
    assert result["producer_workflow_version"] is None


def test_producer_version_is_none_when_manifest_malformed(tmp_path):
    _pkg(tmp_path, "{not json")
    result = check_package_contract(tmp_path)
    assert result["producer_workflow_version"] is None


def test_producer_version_is_none_when_manifest_is_not_an_object(tmp_path):
    _pkg(tmp_path, "[]")
    result = check_package_contract(tmp_path)
    assert result["producer_workflow_version"] is None


def test_adding_provenance_changed_no_verdict(tmp_path):
    """The field is additive: status and error accounting must be untouched."""
    _pkg(tmp_path, json.dumps({"workflow_version": "Mamey v1.9.142"}))
    result = check_package_contract(tmp_path)
    assert result["status"] == "FAIL"          # still fails on the real contract errors
    assert result["advisory_only"] is True     # still advisory, still gates nothing
    assert result["error_count"] == len(result["errors"])
