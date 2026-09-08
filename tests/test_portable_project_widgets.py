from __future__ import annotations

import json

from mamey.portable_project_widgets import (
    build_provenance_navigation,
    estimate_read_budget,
    plan_recompute_boundary,
    preview_export_readiness,
)


def _package(tmp_path, release="PRIVATE"):
    package = tmp_path / "portable_package"
    package.mkdir()
    (package / "manifest.json").write_text(json.dumps({
        "release": release,
        "input_zip": "logical-input.zip",
        "source_provenance": "TRACEABLE",
        "source_provenance_note": "generic",
        "taxonomy": "generic taxonomy",
        "source": "generic source",
        "files": [],
    }), encoding="utf-8")
    (package / "checksums_sha256.txt").write_text("abc  manifest.json\n", encoding="utf-8")
    return package


def test_provenance_navigation_emits_logical_locators_not_values(tmp_path):
    result = build_provenance_navigation(_package(tmp_path))
    assert result["widget_id"] == "W402-17"
    assert result["provenance_locations"][0]["logical_locator"] == "manifest.json#input_zip"
    assert "logical-input.zip" not in str(result)


def test_recompute_raw_input_refuses_postseal_substitution():
    result = plan_recompute_boundary("raw_input")
    assert result["widget_id"] == "W402-18"
    assert result["recompute_boundary"] == "RERUN_REQUIRED"
    assert "triage" in result["affected_surface"]


def test_private_package_is_refused_before_public_tier_audit(tmp_path):
    result = preview_export_readiness(_package(tmp_path, release="PRIVATE"))
    assert result["widget_id"] == "W402-19"
    assert result["export_decision"] == "PUBLIC_EXPORT_REFUSED"


def test_budget_is_deterministic_and_not_runtime_prediction(tmp_path):
    package = _package(tmp_path)
    result = estimate_read_budget(package, max_files=10, max_bytes=1_000)
    assert result["widget_id"] == "W402-20"
    assert result["budget_decision"] == "WITHIN_DECLARED_BUDGET"
    assert "not a runtime" in result["reproducibility_note"]
