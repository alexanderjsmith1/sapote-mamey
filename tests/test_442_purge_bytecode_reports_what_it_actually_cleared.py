"""A purge that cannot delete must not report that it did.

Both bytecode refusals in `mamey_run.py` send the operator to `--purge-bytecode` as their
remediation. `shutil.rmtree(..., ignore_errors=True)` skips a directory the filesystem refuses
to release, so counting attempts reports a purge that did not happen and the next run refuses
again with no way out. These tests build a throwaway bundle, make one cache directory
undeletable, and check what the runner says about it.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[1]
RUNNER = BUNDLE / "mamey_run.py"

pytestmark = pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores directory permissions, so an undeletable cache cannot be staged",
)


def _fake_bundle(root: Path) -> Path:
    """A minimal tree the real runner will accept: a stamp, a package whose source agrees with
    itself, a nested subpackage so there is a second __pycache__, and a cli.main to call."""
    assert BUNDLE not in root.resolve().parents, (
        "the throwaway bundle must live outside the shipped tree, or enabling bytecode here "
        "would leak .pyc into it and break the v9.7.404 invariant")
    pkg = root / "mamey"
    (pkg / "sub").mkdir(parents=True)
    (pkg / "__init__.py").write_text(
        '__version__ = "0.0.0"\nBUNDLE_VERSION = "9.9.999"\nfrom . import sub\n', encoding="utf-8")
    (pkg / "sub" / "__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg / "cli.py").write_text("def main():\n    return 0\n", encoding="utf-8")
    (root / "BUILD_STAMP.txt").write_text(
        "version=9.9.999\nbuild=TESTBUILDa\nengine=0.0.0\ntier=code\n", encoding="utf-8")
    shutil.copy2(RUNNER, root / "mamey_run.py")
    return root


def _run(root: Path, *args: str) -> subprocess.CompletedProcess:
    """Run the runner in the throwaway bundle, with bytecode writing switched back ON.

    conftest exports PYTHONDONTWRITEBYTECODE=1 for the whole session (v9.7.404) so children do
    not litter .pyc into the tree under test. A test of a bytecode guard needs real .pyc, so this
    is the one place that opts out -- safely, because `root` is under tmp_path, outside the
    shipped tree, and _fake_bundle asserts that. The .404 invariant is about the tree, not about
    the variable, and nothing here writes bytecode into the bundle.
    """
    env = {**os.environ}
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    return subprocess.run(
        [sys.executable, "mamey_run.py", *args],
        cwd=root, capture_output=True, text=True, timeout=120, env=env,
    )


@pytest.fixture
def bundle(tmp_path):
    root = _fake_bundle(tmp_path / "bundle")
    yield root
    for cache in root.rglob("__pycache__"):      # restore write bits so tmp_path can be cleaned
        cache.chmod(0o755)


def _stage_undeletable_cache(bundle: Path) -> Path:
    """Warm the caches, then take write permission off one of them so its .pyc survive rmtree."""
    first = _run(bundle)
    assert first.returncode == 0, first.stderr
    stuck = bundle / "mamey" / "sub" / "__pycache__"
    assert list(stuck.glob("*.pyc")), "no bytecode was produced for the subpackage"
    stuck.chmod(0o500)
    return stuck


def test_purge_names_the_cache_it_could_not_clear(bundle):
    stuck = _stage_undeletable_cache(bundle)
    result = _run(bundle, "--purge-bytecode")
    assert list(stuck.glob("*.pyc")), "the cache was deletable after all; test staged nothing"
    assert "PURGE_INCOMPLETE" in result.stderr, (
        "purge reported no failure while bytecode survived:\n" + result.stderr)
    assert str(stuck) in result.stderr, "the surviving cache was not named:\n" + result.stderr


def test_purge_count_excludes_a_cache_that_still_holds_bytecode(bundle):
    _stage_undeletable_cache(bundle)
    result = _run(bundle, "--purge-bytecode")
    assert "purged 1 __pycache__ directory under this bundle" in result.stderr, (
        "the count should exclude the cache that still holds .pyc:\n" + result.stderr)


def test_unbound_refusal_names_the_offending_cache(bundle):
    stuck = _stage_undeletable_cache(bundle)
    result = _run(bundle, "--purge-bytecode")
    assert "UNBOUND_BYTECODE_REFUSED" in result.stderr, result.stderr
    assert f"unbound cache: {stuck}" in result.stderr, (
        "the refusal should name the cache it is refusing over:\n" + result.stderr)


def test_a_clean_purge_still_reports_and_the_run_proceeds(bundle):
    """Unchanged behaviour: nothing is stuck, so the purge clears both caches and the run works."""
    assert _run(bundle).returncode == 0
    result = _run(bundle, "--purge-bytecode")
    assert result.returncode == 0, result.stderr
    assert "purged 2 __pycache__ directories under this bundle" in result.stderr, result.stderr
    assert "PURGE_INCOMPLETE" not in result.stderr
    assert "UNBOUND_BYTECODE_REFUSED" not in result.stderr
