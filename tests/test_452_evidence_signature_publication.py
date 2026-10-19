"""Static unexecuted publication controls for actual protein-signature main."""
import json
from pathlib import Path
import pytest
from mamey import protein_signature as tool, output_transaction

def _inputs(tmp_path):
    first, second = tmp_path / "first.faa", tmp_path / "second.faa"
    first.write_text(">g\nMPEPTIDE\n"); second.write_text(">g\nMPEPTIDE\n")
    return first, second

def test_dangling_output_symlink_is_retained(tmp_path):
    first, second = _inputs(tmp_path)
    out = tmp_path / "out.json"; target = tmp_path / "absent.json"; out.symlink_to(target)
    with pytest.raises(SystemExit): tool.main([str(first), str(second), "--out", str(out)])
    assert out.is_symlink() and not target.exists()

def test_target_created_during_computation_is_preserved(tmp_path, monkeypatch):
    first, second = _inputs(tmp_path); out = tmp_path / "out.json"
    original = tool.compare
    def competitor(*args):
        result = original(*args); out.write_text("independent claimant"); return result
    monkeypatch.setattr(tool, "compare", competitor)
    with pytest.raises(SystemExit): tool.main([str(first), str(second), "--out", str(out)])
    assert out.read_text() == "independent claimant"

def test_target_created_at_link_publication_is_preserved(tmp_path, monkeypatch):
    first, second = _inputs(tmp_path); out = tmp_path / "out.json"
    original = output_transaction.os.link
    def competitor(source, destination):
        Path(destination).write_text("late independent claimant")
        return original(source, destination)
    monkeypatch.setattr(output_transaction.os, "link", competitor)
    with pytest.raises(SystemExit): tool.main([str(first), str(second), "--out", str(out)])
    assert out.read_text() == "late independent claimant"

def test_fresh_output_keeps_exact_signature_payload(tmp_path):
    first, second = _inputs(tmp_path); out = tmp_path / "new" / "out.json"
    expected = tool.compare(first, second)
    assert tool.main([str(first), str(second), "--out", str(out)]) == 0
    assert out.read_text() == json.dumps(expected, indent=2) + "\n"
