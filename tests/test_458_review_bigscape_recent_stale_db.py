"""An unchanged database from just before launch is still an earlier result."""
import importlib.util
import os
from pathlib import Path
import subprocess
import time

import pytest

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("recent_bigscape", ROOT / "deliverable_tools/bigscape_run.py")
br = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(br)


def setup(tmp_path, monkeypatch):
    inputs = tmp_path / "gbks"
    inputs.mkdir()
    (inputs / "ctg1.region001.gbk").write_text("LOCUS       ctg1 10 bp DNA\nORIGIN\n        1 acgtacgtac\n//\n")
    output = tmp_path / "output"
    output.mkdir()
    monkeypatch.setattr(br, "ensure_fasttree", lambda *a, **k: None)
    monkeypatch.setattr(br, "_stage_no_space", lambda p, w: p)
    monkeypatch.setattr(time, "time", lambda: 1000.0)
    return inputs, output


def run(inputs, output, tmp_path):
    return br.run_pipeline(input_gbk_dir=str(inputs), out=str(output), run_widgets=False,
                           work_dir=str(tmp_path / "work"))


@pytest.mark.parametrize("returncode", [0, 1])
def test_recent_unchanged_database_is_not_the_new_runs_result(tmp_path, monkeypatch, returncode):
    inputs, output = setup(tmp_path, monkeypatch)
    previous = output / "previous.db"
    previous.write_bytes(b"SQLite format 3\0old result")
    os.utime(previous, (999.75, 999.75))
    monkeypatch.setattr(br.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, returncode))
    result = run(inputs, output, tmp_path)
    assert result["db"] is None
    assert result["stale_db"] == str(previous)


@pytest.mark.parametrize("preexisting", [False, True])
def test_database_created_or_written_during_launch_is_still_usable(tmp_path, monkeypatch, preexisting):
    inputs, output = setup(tmp_path, monkeypatch)
    current = output / "result.db"
    if preexisting:
        current.write_bytes(b"previous result")
        os.utime(current, (999.75, 999.75))

    def cluster(cmd, **kwargs):
        current.write_bytes(b"SQLite format 3\0new result")
        os.utime(current, (1000.25, 1000.25))
        return subprocess.CompletedProcess(cmd, 1)

    monkeypatch.setattr(br.subprocess, "run", cluster)
    result = run(inputs, output, tmp_path)
    assert result["db"] == str(current)
    assert result["returncode"] == 1
