import json
import sys
import pytest
from tools import audit_llm_companion_instructions as mod

@pytest.mark.parametrize("mode", ["source_output", "policy_output", "escape"])
def test_instruction_gate_refuses_source_aliases_and_policy_escape(tmp_path, monkeypatch, mode):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    source = bundle / "guide.md"
    source.write_text("required")
    policy = tmp_path / "policy.json"
    payload = {"active_documents": {"../outside.md" if mode == "escape" else "guide.md": "required"}, "routing_documents": {}, "historical_documents": {}, "forbidden_active_fragments": {}}
    policy.write_text(json.dumps(payload))
    output = source if mode == "source_output" else policy if mode == "policy_output" else tmp_path / "report.json"
    before = source.read_bytes(), policy.read_bytes()
    monkeypatch.setattr(sys, "argv", ["gate", "--bundle-root", str(bundle), "--policy", str(policy), "--out", str(output)])
    with pytest.raises(ValueError):mod.main()
    assert (source.read_bytes(), policy.read_bytes()) == before
