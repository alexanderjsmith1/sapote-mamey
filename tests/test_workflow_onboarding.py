from __future__ import annotations

from mamey.workflow_onboarding import (
    build_onboarding_readset,
    classify_work_boundary,
    route_operator_intent,
)


def test_route_requires_typed_input_shape():
    result = route_operator_intent("start", None)
    assert result["widget_id"] == "W402-11"
    assert result["status"] == "HELD_WITH_EXACT_REASON"
    assert result["missingness"]["kind"] == "REQUIRED_INPUT_MISSING"


def test_route_delegates_to_existing_inspect_owner():
    result = route_operator_intent("start", "RAW_ANTISMASH_ZIP")
    assert result["status"] == "RUNNABLE_CANDIDATE"
    assert result["existing_owner"] == "mamey.package_inspector.inspect_command"
    assert result["next_command"] == "mamey inspect <antiSMASH-output.zip>"


def test_boundary_preserves_judgment_deferral():
    result = classify_work_boundary("judgment")
    assert result["widget_id"] == "W402-12"
    assert result["boundary"] == "JUDGMENT_DEFERRED"


def test_readset_returns_logical_locators_and_honest_absence(tmp_path):
    (tmp_path / "README.md").write_text("x", encoding="utf-8")
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "START_HERE.md").write_text("x", encoding="utf-8")
    result = build_onboarding_readset(tmp_path, "start")
    assert result["widget_id"] == "W402-13"
    assert result["status"] == "HELD_WITH_EXACT_REASON"
    assert result["readset"][0]["logical_locator"] == "README.md"
    assert result["readset"][2]["state"] == "ABSENT"
