"""The cut-marker guard must not refuse a cache this bundle's own code created.

`mamey_run.py` is not the only thing that writes `mamey/__pycache__`: the test suite imports
mamey, 196 `tools/` scripts import mamey, and `tools/intake_harness.py` imports mamey and then
shells out to `mamey_run.py` for every input -- so on a pristine tree the documented batch route
refused its own inputs. These tests pin both halves: an unmarked cache never serves stale code,
and it never blocks a run either.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

RUNNER = Path(__file__).resolve().parents[1] / "mamey_run.py"
STAMP = "version=9.7.441\nbuild=20260924v97441c\nengine=1.9.169\n"
OLD_CLI = 'def main():\n    print("OLD")\n    return 0\n'
NEW_CLI = OLD_CLI.replace("OLD", "NEW")


def _tree(tmp_path):
    root = tmp_path / "bundle"
    pkg = root / "mamey"
    pkg.mkdir(parents=True)
    shutil.copyfile(RUNNER, root / "mamey_run.py")
    (root / "BUILD_STAMP.txt").write_text(STAMP)
    (pkg / "__init__.py").write_text('__version__="1.9.169"\nBUNDLE_VERSION="9.7.441"\n')
    (pkg / "cli.py").write_text(NEW_CLI)
    for source in pkg.glob("*.py"):
        os.utime(source, (315540000, 315540000))
    return root


def _env(root):
    env = dict(os.environ)
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env["PYTHONPATH"] = str(root)
    return env


def _run(root, *args):
    return subprocess.run([sys.executable, "mamey_run.py", *args], cwd=root,
                          env=_env(root), text=True, capture_output=True)


def _seed_cache(root):
    """Import the package the way a tool or a test does -- not through the runner."""
    seeded = subprocess.run([sys.executable, "-c", "import mamey.cli"], cwd=root,
                            env=_env(root), text=True, capture_output=True)
    assert seeded.returncode == 0, seeded.stderr
    assert list((root / "mamey" / "__pycache__").glob("cli*.pyc"))
    assert not (root / "mamey" / "__pycache__" / ".sapote_cut").exists()


def test_cache_from_a_plain_import_does_not_block_the_runner(tmp_path):
    """The workflow case: nothing is stale, so the run must proceed."""
    root = _tree(tmp_path)
    _seed_cache(root)
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NEW"
    assert (root / "mamey" / "__pycache__" / ".sapote_cut").read_text().startswith(STAMP.strip() + "\nsource=")


def test_a_tool_that_imports_mamey_can_still_shell_out_to_the_runner(tmp_path):
    """The shape of tools/intake_harness.py: import mamey, then subprocess the runner."""
    root = _tree(tmp_path)
    tool = root / "harness.py"
    tool.write_text(
        "import subprocess, sys, os\n"
        "import mamey.cli  # the module-level import every tools/ script does\n"
        "done = subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__),"
        " 'mamey_run.py')], cwd=os.path.dirname(__file__), capture_output=True, text=True)\n"
        "print('INNER_RC', done.returncode)\n"
        "print(done.stdout.strip())\n")
    out = subprocess.run([sys.executable, "harness.py"], cwd=root, env=_env(root),
                         text=True, capture_output=True)
    assert out.returncode == 0, out.stderr
    assert "INNER_RC 0" in out.stdout, out.stdout + out.stderr
    assert "NEW" in out.stdout


def test_an_unmarked_cache_still_never_serves_stale_code(tmp_path):
    """The safety property the refusal was protecting: a same-version reseal is invisible to
    Python's (mtime, size) check, so the untrusted cache must not be executed."""
    root = _tree(tmp_path)
    cli = root / "mamey" / "cli.py"
    cli.write_text(OLD_CLI)
    os.utime(cli, (315540000, 315540000))
    _seed_cache(root)
    cli.write_text(NEW_CLI)                     # same size, same 1980 mtime: invisible to Python
    os.utime(cli, (315540000, 315540000))
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "NEW"
    assert "OLD" not in result.stdout
    assert "UNBOUND_BYTECODE_CLEARED" in result.stderr


def test_external_pycache_prefix_refused_before_stale_code_executes(tmp_path):
    root = _tree(tmp_path)
    cli = root / "mamey" / "cli.py"
    cli.write_text(OLD_CLI)
    os.utime(cli, (315540000, 315540000))
    env = _env(root)
    env["PYTHONPYCACHEPREFIX"] = str(tmp_path / "external_bytecode")
    seed = subprocess.run([sys.executable, "-c", "import mamey.cli"], cwd=root,
                          env=env, text=True, capture_output=True)
    assert seed.returncode == 0, seed.stderr
    assert list((tmp_path / "external_bytecode").rglob("cli*.pyc"))
    assert not list((root / "mamey").rglob("*.pyc"))
    cli.write_text(NEW_CLI)             # same size and restored archive mtime
    os.utime(cli, (315540000, 315540000))
    result = subprocess.run([sys.executable, "mamey_run.py"], cwd=root,
                            env=env, text=True, capture_output=True)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "EXTERNAL_BYTECODE_CACHE_REFUSED" in result.stderr
    assert "OLD" not in result.stdout
    assert not (root / "mamey" / "__pycache__" / ".sapote_cut").exists()


def test_symlinked_cache_refused_before_stale_code_executes(tmp_path):
    root = _tree(tmp_path)
    external = tmp_path / "linked_cache"
    external.mkdir()
    try:
        (root / "mamey" / "__pycache__").symlink_to(external, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    cli = root / "mamey" / "cli.py"
    cli.write_text(OLD_CLI)
    os.utime(cli, (315540000, 315540000))
    env = _env(root)
    env.pop("PYTHONPYCACHEPREFIX", None)
    seed = subprocess.run([sys.executable, "-c", "import mamey.cli"], cwd=root,
                          env=env, text=True, capture_output=True)
    assert seed.returncode == 0, seed.stderr
    assert list(external.glob("cli*.pyc"))
    cli.write_text(NEW_CLI)
    os.utime(cli, (315540000, 315540000))
    result = subprocess.run([sys.executable, "mamey_run.py"], cwd=root,
                            env=env, text=True, capture_output=True)
    assert result.returncode == 2, result.stdout + result.stderr
    assert "SYMLINKED_BYTECODE_CACHE_REFUSED" in result.stderr
    assert "OLD" not in result.stdout
    assert not (external / ".sapote_cut").exists()


@pytest.mark.skipif(
    hasattr(os, "geteuid") and os.geteuid() == 0,
    reason="root ignores directory permissions, so an undeletable cache cannot be staged",
)
def test_a_cache_that_cannot_be_cleared_still_refuses(tmp_path):
    """Fail closed. `1246F6CE` showed that rmtree runs with ignore_errors=True, so a cache the
    filesystem will not release is skipped silently. Clearing must not become a way to import the
    very bytecode this branch exists to distrust."""
    root = _tree(tmp_path)
    cli = root / "mamey" / "cli.py"
    cli.write_text(OLD_CLI)
    os.utime(cli, (315540000, 315540000))
    _seed_cache(root)
    cli.write_text(NEW_CLI)
    os.utime(cli, (315540000, 315540000))
    cache = root / "mamey" / "__pycache__"
    cache.chmod(0o555)                          # contents cannot be unlinked
    try:
        result = _run(root)
        assert result.returncode == 2, result.stdout + result.stderr
        assert "UNBOUND_BYTECODE_REFUSED" in result.stderr
        assert str(cache) in result.stderr      # name the directory the operator must fix
        assert "OLD" not in result.stdout
    finally:
        cache.chmod(0o755)
