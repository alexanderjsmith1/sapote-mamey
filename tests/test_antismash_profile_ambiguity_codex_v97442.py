"""Fail-closed profile collection for ambiguous and missing metadata."""
import json
import subprocess
import sys
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "tools" / "check_antismash_profile.py"


def _manifest(root, dirname, strain, profile):
    path = root / dirname / "manifest.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"strain": strain, "antismash_profile": profile}))


def _run(root, *args):
    return subprocess.run([sys.executable, str(GUARD), str(root), *args], capture_output=True, text=True)


def test_duplicate_strain_with_mixed_profiles_refuses(tmp_path):
    _manifest(tmp_path, "first", "X", "default")
    _manifest(tmp_path, "second", "X", "loose")
    p = _run(tmp_path)
    assert p.returncode == 1
    assert "duplicate strain" in p.stderr
    assert "UNKNOWN" in p.stderr


def test_duplicate_strain_even_same_profile_refuses(tmp_path):
    _manifest(tmp_path, "first", "X", "loose")
    _manifest(tmp_path, "second", "X", "loose")
    assert _run(tmp_path).returncode == 1


def test_blank_and_null_profiles_refuse(tmp_path):
    _manifest(tmp_path, "first", "A", "")
    _manifest(tmp_path, "second", "B", None)
    p = _run(tmp_path)
    assert p.returncode == 1
    assert "UNKNOWN" in p.stderr


def test_non_object_manifest_refuses(tmp_path):
    path = tmp_path / "first" / "manifest.json"
    path.parent.mkdir()
    path.write_text("[]")
    assert _run(tmp_path).returncode == 1


def test_uniform_known_profiles_still_pass(tmp_path):
    _manifest(tmp_path, "first", "A", "loose")
    _manifest(tmp_path, "second", "B", "loose")
    assert _run(tmp_path).returncode == 0


def test_warn_only_remains_explicit_override(tmp_path):
    _manifest(tmp_path, "first", "A", "")
    p = _run(tmp_path, "--warn-only")
    assert p.returncode == 0
    assert "UNSAFE TO POOL" in p.stderr
