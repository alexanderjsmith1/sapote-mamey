"""`mamey_run.py` pins the directory; it must also refuse the wrong bytecode in that directory.

The runner's documented job is that "a previously installed version of mamey" cannot win. Putting
the bundle first on `sys.path` settles WHICH DIRECTORY is imported. It does not settle WHICH
BYTECODE: CPython's default `.pyc` invalidation compares `(source mtime, source size)`, a cut
writes a fixed 1980 timestamp so archives stay byte-reproducible, and an engine version bump keeps
`__init__.py` exactly the same length. Re-extract a newer cut over a reused directory and both
criteria are unchanged, so the old cache is reused and the import reports a version its own source
does not contain.

Not hypothetical: that is the 1.9.154 shadow at the workspace root, and the reason the house rule
"run Mamey tools from the bundle root" exists. Measured on the real .439 -> .440 pair: of 2304
`.py` files in both cuts, 12 changed content and exactly one is invisible to the (mtime, size)
check -- `mamey/__init__.py`, 231 bytes in both. The narrowest possible exposure, landing on the
one file that defines reported identity.

These tests build a miniature bundle in `tmp_path` rather than mutating the real one. That keeps
them hermetic and, more importantly, keeps pytest's own in-process `mamey` import from rewriting
the cache the test is trying to hold stale.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CUT_STAMP = 315540000  # 1980-01-02, the deterministic timestamp a cut writes
GUARD_SOURCE = (ROOT / "mamey_run.py").read_text()


def _mini_bundle(tmp_path: Path, version: str) -> Path:
    """A runnable stand-in carrying the real guard and the real 231-byte __init__ shape."""
    root = tmp_path / "bundle"
    (root / "mamey").mkdir(parents=True)
    (root / "mamey_run.py").write_text(GUARD_SOURCE.replace("from mamey.cli import main",
                                                            "from mamey.cli import main"))
    (root / "mamey" / "__init__.py").write_text(f'__version__ = "{version}"\n')
    (root / "mamey" / "cli.py").write_text(
        "import mamey, sys\n"
        "def main():\n"
        "    sys.stdout.write(mamey.__version__ + '\\n')\n"
        "    return 0\n")
    _restamp(root)
    return root


def _restamp(root: Path):
    for path in (root / "mamey").rglob("*.py"):
        os.utime(path, (CUT_STAMP, CUT_STAMP))


def _bytecode_env():
    """Re-enable bytecode writing for these subprocesses only.

    `tests/conftest.py` sets PYTHONDONTWRITEBYTECODE=1 process-wide (v9.7.404, to stop test runs
    leaving .pyc litter in the tree). Children inherit it, which means the suite cannot normally
    observe bytecode behaviour at all -- and that is precisely why a stale-.pyc defect could sit
    in the workspace unnoticed. These tests are about bytecode, so they opt back in, in their own
    tmp_path, leaving no litter in the bundle.
    """
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    return env


def _run(root: Path):
    return subprocess.run([sys.executable, "mamey_run.py"], cwd=str(root),
                          capture_output=True, text=True, timeout=120, env=_bytecode_env())


def test_the_guard_is_wired_before_the_cli_in_the_real_runner():
    assert "_refuse_stale_bytecode" in GUARD_SOURCE
    assert GUARD_SOURCE.index("_refuse_stale_bytecode()") < GUARD_SOURCE.index("from mamey.cli import main")


def test_a_clean_bundle_runs_normally(tmp_path):
    root = _mini_bundle(tmp_path, "1.9.169")
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1.9.169"
    assert "STALE_BYTECODE_REFUSED" not in result.stderr


def test_stale_bytecode_from_a_same_length_version_is_refused(tmp_path):
    """The real failure: same length, same 1980 stamp, a different cut."""
    root = _mini_bundle(tmp_path, "1.9.154")
    assert _run(root).stdout.strip() == "1.9.154"          # seeds the cache

    init = root / "mamey" / "__init__.py"
    before = init.stat().st_size
    init.write_text('__version__ = "1.9.169"\n')            # the re-extraction
    assert init.stat().st_size == before, "precondition: the two versions are the same length"
    _restamp(root)

    result = _run(root)
    assert result.returncode == 2
    assert "STALE_BYTECODE_REFUSED" in result.stderr
    assert "1.9.169" in result.stderr and "1.9.154" in result.stderr
    assert "__pycache__" in result.stderr, "the refusal must name the remediation"


def test_without_the_guard_the_shadow_would_be_silent(tmp_path):
    """Pins the defect itself: the bare import returns the stale version, no error."""
    root = _mini_bundle(tmp_path, "1.9.154")
    _run(root)
    (root / "mamey" / "__init__.py").write_text('__version__ = "1.9.169"\n')
    _restamp(root)
    bare = subprocess.run([sys.executable, "-c",
                           "import sys; sys.path.insert(0, '.'); import mamey; print(mamey.__version__)"],
                          cwd=str(root), capture_output=True, text=True, timeout=120,
                          env=_bytecode_env())
    assert bare.returncode == 0
    assert bare.stdout.strip() == "1.9.154", "the unguarded import must reproduce the shadow"


def test_the_refusal_clears_once_the_cache_is_removed(tmp_path):
    root = _mini_bundle(tmp_path, "1.9.154")
    _run(root)
    (root / "mamey" / "__init__.py").write_text('__version__ = "1.9.169"\n')
    _restamp(root)
    assert _run(root).returncode == 2

    shutil.rmtree(root / "mamey" / "__pycache__")
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "1.9.169"


def test_the_guard_deletes_nothing_itself(tmp_path):
    """It reports and stops. Removing caches is the operator's action, not the runner's."""
    root = _mini_bundle(tmp_path, "1.9.154")
    _run(root)
    cached = sorted(p.name for p in (root / "mamey" / "__pycache__").glob("*.pyc"))
    assert cached, "precondition: a cache exists"

    (root / "mamey" / "__init__.py").write_text('__version__ = "1.9.169"\n')
    _restamp(root)
    assert _run(root).returncode == 2
    assert sorted(p.name for p in (root / "mamey" / "__pycache__").glob("*.pyc")) == cached


def test_an_unreadable_or_unrecognised_init_does_not_block_a_run(tmp_path):
    """Fail-open on shapes it cannot parse: the guard must not become its own outage."""
    root = _mini_bundle(tmp_path, "1.9.169")
    (root / "mamey" / "__init__.py").write_text("VERSION = '1.9.169'\n")  # no __version__
    (root / "mamey" / "cli.py").write_text(
        "import sys\ndef main():\n    sys.stdout.write('ran\\n')\n    return 0\n")
    _restamp(root)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "STALE_BYTECODE_REFUSED" not in result.stderr


def test_same_engine_stale_bundle_version_is_also_refused(tmp_path):
    root = _mini_bundle(tmp_path, "1.9.169")
    init = root / "mamey" / "__init__.py"
    init.write_text('__version__ = "1.9.169"\nBUNDLE_VERSION = "9.7.439"\n')
    _restamp(root)
    assert _run(root).returncode == 0
    init.write_text('__version__ = "1.9.169"\nBUNDLE_VERSION = "9.7.440"\n')
    _restamp(root)
    result = _run(root)
    assert result.returncode == 2
    assert "BUNDLE_VERSION" in result.stderr and "9.7.439" in result.stderr and "9.7.440" in result.stderr
