"""Synthetic working copy only: the change record can never be an edited document or the edit file."""
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "manuscript_revision.py"
sys.path.insert(0, str(TOOL.parent))
spec = importlib.util.spec_from_file_location("manuscript_revision_alias_464r3", TOOL)
mr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mr)

TEXT = "The survey found 42 plots.\n"


def _case(tmp_path):
    root = tmp_path / "work"
    root.mkdir()
    doc = root / "01_intro.md"
    doc.write_text(TEXT, encoding="utf-8")
    edits = tmp_path / "edits.json"
    edits.write_text(json.dumps([{"doc": "01_intro.md", "find": "42 plots", "replace": "43 plots"}]), encoding="utf-8")
    return root, doc, edits


@pytest.mark.parametrize("how", ["same", "relative_dot", "hardlink", "symlink", "edit_file"])
def test_record_alias_is_refused_and_nothing_changes(tmp_path, how):
    root, doc, edits = _case(tmp_path)
    saved_edits = edits.read_bytes()
    if how == "same":
        record = doc
    elif how == "relative_dot":
        record = root / "." / "01_intro.md"
    elif how == "hardlink":
        record = tmp_path / "linked.jsonl"
        os.link(doc, record)
    elif how == "symlink":
        record = tmp_path / "linked.jsonl"
        record.symlink_to(doc)
    else:
        record = edits
    code = mr.main(["apply", str(edits), "--root", str(root), "--record", str(record)])
    assert code == mr.EXIT_INPUT
    assert doc.read_text(encoding="utf-8") == TEXT
    assert edits.read_bytes() == saved_edits


def test_separate_record_still_appends(tmp_path):
    root, doc, edits = _case(tmp_path)
    record = tmp_path / "changes.jsonl"
    assert mr.main(["apply", str(edits), "--root", str(root), "--record", str(record)]) == mr.EXIT_OK
    assert "43 plots" in doc.read_text(encoding="utf-8")
    assert json.loads(record.read_text(encoding="utf-8").splitlines()[0])["replace"] == "43 plots"
