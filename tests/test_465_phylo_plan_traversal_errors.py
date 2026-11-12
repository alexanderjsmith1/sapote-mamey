"""Inventory plan must not silently omit unreadable directories."""
import importlib.util
import json
import os
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools/phylo_autopilot.py"
spec = importlib.util.spec_from_file_location("autopilot_inventory_review", TOOL)
AP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(AP)

@pytest.mark.parametrize("fail_at", ["root", "nested"])
def test_plan_refuses_traversal_errors(tmp_path, monkeypatch, capsys, fail_at):
    root = tmp_path / "input"
    root.mkdir()
    nested = root / "hidden"
    nested.mkdir()
    (root / "visible.fasta").write_text(">visible\n" + "ACGT" * 350 + "\n")
    (nested / "hidden.fasta").write_text(">hidden\n" + "ACGT" * 350 + "\n")
    target = root if fail_at == "root" else nested
    original = os.scandir
    def fault(path):
        if Path(path) == target:
            raise PermissionError(13, "synthetic unreadable directory", str(path))
        return original(path)
    monkeypatch.setattr(os, "scandir", fault)
    assert AP.main(["plan", str(root)]) == 2
    out = capsys.readouterr()
    assert not out.out and "refused" in out.err and "synthetic unreadable directory" in out.err

def test_readable_empty_and_nested_with_unknown_suffix(tmp_path, capsys):
    assert AP.main(["plan", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out) == {}
    nested = tmp_path / "nested"
    nested.mkdir()
    fasta = nested / "query.fasta"
    other = nested / "notes.txt"
    fasta.write_text(">q\n" + "ACGT" * 350 + "\n")
    other.write_text("not a FASTA input")
    assert AP.main(["plan", str(tmp_path)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["rrna"] == [str(fasta)]
    assert result["not_classified_suffix"] == [str(other)]
