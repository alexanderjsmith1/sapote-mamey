import os
import sys
import pytest
from tools import session_cost_audit as mod

@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink", "existing"])
def test_cost_audit_never_replaces_selected_logs_or_prior_output(tmp_path, monkeypatch, alias):
    source = tmp_path / "session.jsonl"
    source.write_text("{}\n")
    output = tmp_path / "output.tsv"
    if alias == "direct": output = source
    elif alias == "symlink": output.symlink_to(source)
    elif alias == "hardlink": os.link(source, output)
    else: output.write_text("prior output")
    before = output.read_bytes()
    monkeypatch.setattr(sys, "argv", ["session_cost_audit", "--proj", str(tmp_path), "--tsv", str(output)])
    assert mod.main() == 2
    assert output.read_bytes() == before
    assert source.read_text() == "{}\n"
