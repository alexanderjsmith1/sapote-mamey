import pytest
from tools.audit_llm_companion_instructions import audit

def test_empty_instruction_policy_is_unassessed_not_pass(tmp_path):
    empty = {"active_documents": {}, "routing_documents": {}, "historical_documents": {}, "forbidden_active_fragments": {}}
    with pytest.raises(ValueError, match="nonempty"):
        audit(tmp_path, empty)

def test_nonempty_valid_instruction_scope_still_passes(tmp_path):
    (tmp_path / "guide.md").write_text("required")
    policy = {"active_documents": {"guide.md": "required"}, "routing_documents": {}, "historical_documents": {}, "forbidden_active_fragments": {}}
    assert audit(tmp_path, policy)["status"] == "PASS"
