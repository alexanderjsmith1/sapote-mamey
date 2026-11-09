"""Synthetic policy only: a file entry that configures no strings is a failed row, not a pass."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("llm_companion_audit_464r3", ROOT / "tools" / "audit_llm_companion_instructions.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def _policy(**overrides):
    policy = {"active_documents": {}, "routing_documents": {}, "historical_documents": {},
              "forbidden_active_fragments": {}}
    policy.update(overrides)
    return policy


@pytest.mark.parametrize("section", ["active_documents", "routing_documents", "historical_documents"])
@pytest.mark.parametrize("value", [[], "", [""]])
def test_required_entry_with_no_strings_fails(tmp_path, section, value):
    (tmp_path / "guide.md").write_text("text\n", encoding="utf-8")
    report = gate.audit(tmp_path, _policy(**{section: {"guide.md": value}}))
    assert report["status"] == "FAIL"
    assert report["results"][0]["detail"] == "no required strings configured"


@pytest.mark.parametrize("value", [[], [""]])
def test_forbidden_entry_with_no_fragments_fails(tmp_path, value):
    (tmp_path / "guide.md").write_text("text\n", encoding="utf-8")
    report = gate.audit(tmp_path, _policy(forbidden_active_fragments={"guide.md": value}))
    assert report["status"] == "FAIL"


def test_configured_strings_still_pass(tmp_path):
    (tmp_path / "guide.md").write_text("alpha beta\n", encoding="utf-8")
    report = gate.audit(tmp_path, _policy(active_documents={"guide.md": ["alpha"]},
                                          forbidden_active_fragments={"guide.md": ["gamma"]}))
    assert report["status"] == "PASS" and report["checks"] == 2
