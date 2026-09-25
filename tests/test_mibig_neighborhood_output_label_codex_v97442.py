"""Bounded MIBiG neighborhood output containment regression tests."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "mibig_neighborhoods.py"


def _run(tmp_path, label):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(workspace))
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--faa", str(tmp_path / "missing.faa"), "--fam", label],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )
    return proc, workspace


def test_parent_traversal_refused_before_directory_creation(tmp_path):
    proc, workspace = _run(tmp_path, "../escaped")
    assert proc.returncode == 1
    assert "OUTPUT_LABEL_HAS_SEPARATOR" in proc.stdout
    assert not (workspace / "strain_data" / "escaped").exists()
    assert not (workspace / "strain_data" / "_NEIGHBORHOODS_2026-08-10").exists()


def test_absolute_label_refused_before_directory_creation(tmp_path):
    target = tmp_path / "absolute_escape"
    proc, workspace = _run(tmp_path, str(target))
    assert proc.returncode == 1
    assert "OUTPUT_LABEL_" in proc.stdout
    assert not target.exists()
    assert not (workspace / "strain_data" / "_NEIGHBORHOODS_2026-08-10").exists()


def test_valid_family_still_uses_intended_directory(tmp_path):
    proc, workspace = _run(tmp_path, "KS")
    assert proc.returncode != 0  # missing FASTA makes the scientific run fail later
    assert (workspace / "strain_data" / "_NEIGHBORHOODS_2026-08-10" / "KS").is_dir()
