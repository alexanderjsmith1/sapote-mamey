"""Pooling admission accepts only source-resolved strict/relaxed/loose labels.

A uniform arbitrary label, an unresolved "auto" label, or a package whose run recorded a
PROFILE_MISMATCH must not certify a pool. --warn-only stays an advisory exit.
"""
import json
import subprocess
import sys
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "tools" / "check_antismash_profile.py"


def _manifest(root, dirname, strain, profile, issues=None):
    path = root / dirname / "manifest.json"
    path.parent.mkdir(parents=True)
    data = {"strain": strain, "antismash_profile": profile}
    if issues is not None:
        data["issues"] = issues
    path.write_text(json.dumps(data))


def _run(root, *args):
    return subprocess.run([sys.executable, str(GUARD), str(root), *args], capture_output=True, text=True)


def test_uniform_arbitrary_label_is_refused(tmp_path):
    _manifest(tmp_path, "a", "A", "custom_profile")
    _manifest(tmp_path, "b", "B", "custom_profile")
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "UNRECOGNIZED" in result.stderr


def test_uniform_auto_label_is_refused(tmp_path):
    _manifest(tmp_path, "a", "A", "auto")
    _manifest(tmp_path, "b", "B", "auto")
    assert _run(tmp_path).returncode == 1


def test_recorded_profile_mismatch_is_refused(tmp_path):
    _manifest(tmp_path, "a", "A", "loose")
    _manifest(tmp_path, "b", "B", "loose", issues=[
        "PROFILE_MISMATCH: --antismash-profile=loose but the archive records strictness=strict"])
    result = _run(tmp_path)
    assert result.returncode == 1
    assert "PROFILE_MISMATCH" in result.stderr


def test_unrelated_issues_do_not_block_a_uniform_known_pool(tmp_path):
    _manifest(tmp_path, "a", "A", "relaxed", issues=["some other note"])
    _manifest(tmp_path, "b", "B", "relaxed")
    assert _run(tmp_path).returncode == 0


def test_warn_only_is_marked_advisory(tmp_path):
    _manifest(tmp_path, "a", "A", "custom_profile")
    result = _run(tmp_path, "--warn-only")
    assert result.returncode == 0
    assert "advisory" in result.stderr and "not acceptance" in result.stderr
