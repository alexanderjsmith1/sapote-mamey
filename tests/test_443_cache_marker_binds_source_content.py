"""The cache marker must bind the source it was built from, not only the build stamp.

Every other guard in mamey_run.py keys on BUILD_STAMP.txt. Edit a module in place without touching
the stamp and the marker, the version strings, and -- at the fixed 1980 mtime and an unchanged size
-- Python's own (mtime, size) check all still agree, so stale bytecode executes. These tests pin
that the marker now carries a source digest and that drift under the same stamp clears the cache.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

RUNNER = Path(__file__).resolve().parents[1] / "mamey_run.py"
STAMP = "version=9.7.442\nbuild=20260924v97442a\nengine=1.9.169\n"
OLD_CLI = 'def main():\n    print("OLD")\n    return 0\n'
NEW_CLI = OLD_CLI.replace("OLD", "NEW")
FIXED = (315540000, 315540000)          # 1980-01-02, the cut's deterministic stamp


def _tree(tmp_path, cli=NEW_CLI):
    root = tmp_path / "bundle"
    pkg = root / "mamey"
    pkg.mkdir(parents=True)
    shutil.copyfile(RUNNER, root / "mamey_run.py")
    (root / "BUILD_STAMP.txt").write_text(STAMP)
    (pkg / "__init__.py").write_text('__version__="1.9.169"\nBUNDLE_VERSION="9.7.442"\n')
    (pkg / "cli.py").write_text(cli)
    for source in pkg.glob("*.py"):
        os.utime(source, FIXED)
    return root


def _run(root, *args):
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    env["PYTHONPATH"] = str(root)
    return subprocess.run([sys.executable, "mamey_run.py", *args], cwd=root, env=env,
                          text=True, capture_output=True)


def _marker(root):
    return root / "mamey" / "__pycache__" / ".sapote_cut"


def test_marker_records_a_source_digest(tmp_path):
    root = _tree(tmp_path)
    assert _run(root).returncode == 0
    text = _marker(root).read_text()
    assert text.startswith(STAMP.strip() + "\nsource=")
    digest = text.split("source=", 1)[1].strip()
    assert len(digest) == 64 and int(digest, 16) >= 0


def test_in_place_edit_under_the_same_stamp_never_serves_stale_code(tmp_path):
    """The bypass: same stamp, same size, same 1980 mtime, different bytes."""
    root = _tree(tmp_path, cli=OLD_CLI)
    first = _run(root)
    assert first.returncode == 0 and first.stdout.strip() == "OLD", first.stderr
    cli = root / "mamey" / "cli.py"
    cli.write_text(NEW_CLI)
    os.utime(cli, FIXED)
    assert cli.stat().st_size == len(OLD_CLI)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NEW"
    assert "SOURCE_DRIFT_DETECTED" in result.stderr
    assert "UNBOUND_BYTECODE_CLEARED" in result.stderr


def test_unchanged_source_is_not_drift(tmp_path):
    """No false positive: an ordinary second run reuses the cache silently."""
    root = _tree(tmp_path)
    assert _run(root).returncode == 0
    second = _run(root)
    assert second.returncode == 0
    assert "SOURCE_DRIFT_DETECTED" not in second.stderr
    assert "CLEARED" not in second.stderr


def test_a_stamp_only_marker_from_before_source_hashing_is_upgraded(tmp_path):
    """A .443-shape marker (stamp, no source line) must not bless the cache."""
    root = _tree(tmp_path)
    assert _run(root).returncode == 0
    _marker(root).write_text(STAMP)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "SOURCE_DRIFT_DETECTED" in result.stderr
    assert "\nsource=" in _marker(root).read_text()


def test_a_different_stamp_still_refuses(tmp_path):
    """Foreign-cut refusal is unchanged: two named builds are the operator's to reconcile."""
    root = _tree(tmp_path)
    assert _run(root).returncode == 0
    stamp = root / "BUILD_STAMP.txt"
    stamp.write_text(STAMP.replace("20260924v97442a", "20260926v97442b"))
    result = _run(root)
    assert result.returncode == 2
    assert "FOREIGN_BYTECODE_REFUSED" in result.stderr
    assert "build=20260924v97442a" in result.stderr and "build=20260926v97442b" in result.stderr
    assert "source=" not in result.stderr.split("cache was built by", 1)[1].splitlines()[0]
