"""A failed blastn in the 16S similarity check is an error, not an empty hit list.

Before: the return code was ignored, so a missing database or a crash read as "no hits" and the strain
was reported with no nearest match.
"""
import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sixteen_s_458", ROOT / "tools" / "sixteen_s_similarity_check.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def test_failed_blastn_raises(monkeypatch, tmp_path):
    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 2, stdout="", stderr="BLAST Database error: No alias or index file found")
    monkeypatch.setattr(m.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="blastn failed"):
        m._nearest_search(lambda name: name, tmp_path / "q.fa", str(tmp_path / "missing_db"), 5)


def test_successful_empty_search_still_returns_no_hits(monkeypatch, tmp_path):
    monkeypatch.setattr(m.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout="", stderr=""))
    assert not any(l.strip() for l in m._nearest_search(lambda name: name, tmp_path / "q.fa", "db", 5))
