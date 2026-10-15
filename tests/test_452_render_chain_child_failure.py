import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest

def test_failed_relabel_stage_never_consumes_stale_tree_or_launches_final_render(tmp_path, monkeypatch):
    source = tmp_path / "source.treefile"
    source.write_text("(synthetic:1,reference_OUTGROUP:1);")
    stale = tmp_path / "source_relabeled.treefile"
    stale.write_text("stale evidence")
    calls = []
    def run(cmd, **kwargs):
        calls.append(cmd)
        return SimpleNamespace(returncode=7, stdout="", stderr="synthetic child failure")
    monkeypatch.setattr(subprocess, "run", run)
    monkeypatch.setattr(sys, "argv", ["render_all", str(source), str(tmp_path), str(tmp_path / "out.png"), "synthetic"])
    script = Path(__file__).resolve().parents[1] / "tools/render_all.py"
    with pytest.raises(SystemExit) as stopped:
        runpy.run_path(str(script), run_name="__main__")
    assert stopped.value.code == 7
    assert len(calls) == 1
    assert stale.read_text() == "stale evidence"
