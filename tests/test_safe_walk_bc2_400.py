"""BC2 .400 audit: tools/_safe_walk.py — shared unreadable-dir-aware walk helper, consolidated
per Alex's direction after the identical `rglob()`-swallows-`OSError` defect was found and
independently fixed in three release/CI-hygiene gates this round (`check_no_brace_paths.py`,
`check_duplicate_dict_keys.py`, `public_release_audit.py`). This file tests the shared helper
directly, in isolation from any one gate's own business logic.

Permission-bit tests are skipped on platforms where chmod(0) doesn't actually restrict the
owner's own read access (notably: running as root).
"""
from __future__ import annotations

import os
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
from _safe_walk import safe_walk_files


def test_finds_files_in_an_ordinary_readable_tree(tmp_path):
    (tmp_path / "a.py").write_text("x")
    nested = tmp_path / "sub" / "deep"
    nested.mkdir(parents=True)
    (nested / "b.py").write_text("x")
    (nested / "c.txt").write_text("x")
    paths, unreadable = safe_walk_files(tmp_path)
    names = sorted(p.name for p in paths)
    assert names == ["a.py", "b.py", "c.txt"]
    assert unreadable == []


def test_suffix_filter(tmp_path):
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "b.txt").write_text("x")
    paths, _ = safe_walk_files(tmp_path, suffix=".py")
    assert [p.name for p in paths] == ["a.py"]


def test_missing_root_returns_empty_not_unreadable(tmp_path):
    """The edge case caught while consolidating this fix: os.walk's onerror fires even for a
    missing top path, unlike rglob. A simply-absent directory must not be reported as
    'unreadable' -- that would be a false positive on every tree lacking some optional dir."""
    missing = tmp_path / "does_not_exist_at_all"
    assert not missing.exists()
    paths, unreadable = safe_walk_files(missing)
    assert paths == []
    assert unreadable == []


def test_skip_dirs_prunes_the_walk_entirely(tmp_path):
    skipped = tmp_path / "__pycache__"
    skipped.mkdir()
    (skipped / "cached.pyc").write_text("x")
    (tmp_path / "real.py").write_text("x")
    paths, _ = safe_walk_files(tmp_path, skip_dirs=frozenset({"__pycache__"}))
    assert [p.name for p in paths] == ["real.py"]


def test_include_dirs_also_returns_directory_paths(tmp_path):
    (tmp_path / "{brace}").mkdir()
    (tmp_path / "ordinary.txt").write_text("x")
    paths, _ = safe_walk_files(tmp_path, include_dirs=True)
    names = sorted(p.name for p in paths)
    assert names == sorted(["{brace}", "ordinary.txt"])


@pytest.fixture
def locked_dir(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    (locked / "hidden.py").write_text("x")
    os.chmod(locked, 0o000)
    if os.access(locked, os.R_OK):
        os.chmod(locked, 0o755)
        pytest.skip("chmod(0) does not restrict read access for this user (e.g. running as root)")
    yield tmp_path, locked
    os.chmod(locked, 0o755)


def test_unreadable_directory_is_reported_and_excluded(locked_dir):
    root, locked = locked_dir
    (root / "visible.py").write_text("x")
    paths, unreadable = safe_walk_files(root)
    assert [p.name for p in paths] == ["visible.py"]
    assert any(str(locked) in u for u in unreadable)
