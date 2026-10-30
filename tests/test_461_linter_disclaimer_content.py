"""Boilerplate labels must not hide the following assertion; literal text only."""
import importlib.util
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "tools/claim_safety_linter.py"
SPEC = importlib.util.spec_from_file_location("disclaimer_scope_461", SOURCE)
linter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(linter)


@pytest.mark.parametrize("prefix", [
    "Claim-safety: ",
    "KCB comparisons are similarity signals, not identity. ",
    "Bioactivity links are mechanistic hypotheses requiring experimental validation. ",
    "Claim-safety: KCB comparisons are similarity signals, not identity. ",
])
def test_prefix_preserves_following_assertion_for_both_interfaces(prefix):
    text = prefix + "The software locus produces softwarecompound."
    assert linter.lint_claim_safety(text, {"softwarecompound"})
    findings = linter.lint_claim_safety_report(text, compound_names={"softwarecompound"})
    assert any(row["violation_type"] == "identity_overclaim" for row in findings)


@pytest.mark.parametrize("text", [
    "Claim-safety: Similarity is not identity.",
    "KCB comparisons are similarity signals, not identity.",
    "Claim-safety: Bioactivity links are mechanistic hypotheses requiring experimental validation.",
])
def test_boilerplate_alone_remains_clear(text):
    assert linter.lint_claim_safety(text) == []
    assert linter.lint_claim_safety_report(text) == []
