"""Generic upgrade-path controls for the Claude cache-provenance candidate."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

RUNNER = Path(__file__).resolve().parents[1] / "mamey_run.py"
STAMP = "version=9.7.441\nbuild=20260924v97441c\nengine=1.9.169\n"
OLD_CLI = 'def main():\n    print("OLD")\n    return 0\n'
NEW_CLI = OLD_CLI.replace('OLD', 'NEW')


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


def test_unmarked_legacy_cache_cleared_before_stale_code_executes(tmp_path):
    """v9.7.442 AUDITROUND (`2d6758ab`): this used to assert a refusal (rc=2). The refusal was
    correct about the danger and wrong about the remedy -- it also fired on caches this bundle's
    own test suite and tools/ scripts had just created, which broke the documented batch route.
    The untrusted cache is now cleared instead. The property under test is unchanged: the stale
    module must never execute."""
    root = _tree(tmp_path)
    cli = root / "mamey" / "cli.py"
    cli.write_text(OLD_CLI)
    os.utime(cli, (315540000, 315540000))
    seed = subprocess.run([sys.executable, "-c", "import mamey.cli"], cwd=root,
                          env=_env(root), capture_output=True, text=True)
    assert seed.returncode == 0, seed.stderr
    assert list((root / "mamey" / "__pycache__").glob("cli*.pyc"))
    assert not (root / "mamey" / "__pycache__" / ".sapote_cut").exists()
    cli.write_text(NEW_CLI)
    os.utime(cli, (315540000, 315540000))
    result = _run(root)
    assert result.returncode == 0, result.stderr
    assert "UNBOUND_BYTECODE_CLEARED" in result.stderr
    assert "OLD" not in result.stdout
    assert result.stdout.strip() == "NEW"
    assert (root / "mamey" / "__pycache__" / ".sapote_cut").read_text().startswith(STAMP.strip() + "\nsource=")
    purged = _run(root, "--purge-bytecode")
    assert purged.returncode == 0, purged.stderr
    assert purged.stdout.strip() == "NEW"


def test_clean_first_run_marks_before_bytecode_then_reuses(tmp_path):
    root = _tree(tmp_path)
    first = _run(root)
    assert first.returncode == 0, first.stderr
    assert first.stdout.strip() == "NEW"
    marker = root / "mamey" / "__pycache__" / ".sapote_cut"
    assert marker.read_text().startswith(STAMP.strip() + "\nsource=")
    second = _run(root)
    assert second.returncode == 0, second.stderr
    assert second.stdout.strip() == "NEW"
