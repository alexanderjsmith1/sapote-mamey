"""The runner must name the build it runs, and warn when the package is not its own.

A reseal of the same cut moves neither __version__ nor BUNDLE_VERSION, so the build= line in
BUILD_STAMP.txt is the only field that tells two seals apart. mamey_run.py reports it on every
run ("mamey build: ...") and prints SHADOW_PACKAGE_WARNING when the imported mamey is not the
one beside the runner. Both are advisory: neither may block a run. Fixtures are synthetic.
"""
import os
from pathlib import Path
import shutil
import subprocess
import sys

RUNNER = Path(__file__).resolve().parents[1] / "mamey_run.py"
BUILD = "20990101v99999z"
STAMP = f"version=9.9.999\nbuild={BUILD}\nengine=9.9.999\n"
INIT = '__version__="9.9.999"\nBUNDLE_VERSION="9.9.999"\n'
CLI = 'def main():\n    print("RAN")\n    return 0\n'


def _package(parent):
    pkg = parent / "mamey"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text(INIT)
    (pkg / "cli.py").write_text(CLI)
    return pkg


def _bundle(tmp_path, with_package=True, with_stamp=True):
    root = tmp_path / "bundle"
    root.mkdir()
    shutil.copyfile(RUNNER, root / "mamey_run.py")
    if with_stamp:
        (root / "BUILD_STAMP.txt").write_text(STAMP)
    if with_package:
        _package(root)
    return root


def _run(root, pythonpath=None):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPYCACHEPREFIX", None)
    env.pop("PYTHONPATH", None)
    if pythonpath is not None:
        env["PYTHONPATH"] = str(pythonpath)
    return subprocess.run([sys.executable, "mamey_run.py"], cwd=root, env=env,
                          capture_output=True, text=True)


def test_normal_run_reports_the_build_id(tmp_path):
    result = _run(_bundle(tmp_path))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "RAN"
    assert f"mamey build: {BUILD}" in result.stderr, result.stderr
    assert "SHADOW_PACKAGE_WARNING" not in result.stderr


def test_package_resolved_outside_the_bundle_is_warned_not_blocked(tmp_path):
    root = _bundle(tmp_path, with_package=False)
    elsewhere = tmp_path / "elsewhere"
    _package(elsewhere)
    result = _run(root, pythonpath=elsewhere)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "RAN"
    assert "SHADOW_PACKAGE_WARNING" in result.stderr, result.stderr
    assert str(elsewhere / "mamey") in result.stderr
    assert f"this bundle's build: {BUILD}" in result.stderr
    assert "mamey build:" not in result.stderr


def test_missing_stamp_is_reported_as_unknown_not_guessed(tmp_path):
    result = _run(_bundle(tmp_path, with_stamp=False))
    assert result.returncode == 0, result.stderr
    assert "mamey build: (no BUILD_STAMP.txt)" in result.stderr, result.stderr
