"""P5 acceptance: the public-release audit FAILS CLOSED on a planted leak.

These are hermetic: each builds a minimal tree with the Sapote identity anchors
(`mamey/__init__.py` + `BUILD_STAMP.txt`) so the audit proceeds past root-validation into the
whole-tree scan. Whether the LIVE bundle is clean is a CI question against the actual public
artifact, not a unit test asserting the internal dev tree is leak-free.
"""
import shutil, subprocess, sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.public
_ROOT = Path(__import__("mamey").__file__).parent.parent
_AUDIT = _ROOT / "tools" / "public_release_audit.py"


def _run(tree):
    return subprocess.run([sys.executable, str(_AUDIT), str(tree)], capture_output=True, text=True)


def _valid_tree(tmp_path):
    """A minimal tree that passes root-validation (anchors present) and is otherwise clean."""
    tree = tmp_path / "t"
    (tree / "mamey" / "data").mkdir(parents=True)
    (tree / "tools").mkdir()
    (tree / "mamey" / "__init__.py").write_text("__version__ = '0.0.0'\n")
    (tree / "BUILD_STAMP.txt").write_text("version=0.0.0\nbuild=test\nengine=0.0.0\n")
    shutil.copy(_AUDIT, tree / "tools" / "public_release_audit.py")
    return tree


def test_missing_root_fails_closed(tmp_path):
    r = _run(tmp_path / "does-not-exist")
    assert r.returncode == 1 and "root does not exist" in r.stdout


def test_root_without_anchors_fails_closed(tmp_path):
    bare = tmp_path / "bare"; (bare / "mamey").mkdir(parents=True)
    r = _run(bare)
    assert r.returncode == 1 and "identity anchor" in r.stdout


def test_clean_valid_tree_passes(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "engine.py").write_text("def f():\n    return 1\n")
    r = _run(tree)
    assert r.returncode == 0, r.stdout


def test_empty_file_is_not_a_finding(tmp_path):
    # regression: a legitimately-empty file must not be reported as "unreadable"
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "empty.py").write_text("")
    r = _run(tree)
    assert r.returncode == 0, r.stdout
    assert "unreadable" not in r.stdout


def test_planted_roster_fails(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "data" / "strain_genus.csv").write_text("strain,genus\nAS-999,Streptomyces\n")
    r = _run(tree)
    assert r.returncode == 1 and "strain_genus.csv" in r.stdout


def test_planted_personal_path_fails(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "leak.py").write_text('ROOT = "/Users/someone/some_workspace/"\n')
    r = _run(tree)
    assert r.returncode == 1 and "personal path" in r.stdout


def test_planted_codename_fails(tmp_path):
    tree = _valid_tree(tmp_path)
    (tree / "mamey" / "note.py").write_text('# staged in the BLACK_CHERRY audit lane\n')
    r = _run(tree)
    assert r.returncode == 1 and "BLACK_CHERRY" in r.stdout
