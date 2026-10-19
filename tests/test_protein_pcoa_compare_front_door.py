"""The comparison CLI must resolve sibling tools even with mamey already installed."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "protein_pcoa_compare.py"


def _help(command, cwd):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                            text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "--kit" in result.stdout and "--cohort" in result.stdout
    assert "--out" in result.stdout and "--no-figures" in result.stdout
    assert not list(cwd.iterdir()), "--help wrote files in the working directory"


@pytest.mark.parametrize("without_site", [False, True], ids=["normal", "stdlib-only"])
def test_compare_direct_help_from_foreign_cwd(tmp_path, without_site):
    cwd = tmp_path / "foreign"
    cwd.mkdir()
    flags = ["-S"] if without_site else []
    _help([sys.executable, "-B", *flags, str(TOOL), "--help"], cwd)


def test_compare_help_with_installed_mamey_and_no_bundle_on_path(tmp_path):
    # Copy only the stdlib-only import dependencies into an installed-style package.
    # This forces the first mamey import to succeed without exposing sibling tools.
    installed = tmp_path / "installed"
    package = installed / "mamey"
    package.mkdir(parents=True)
    for name in ("__init__.py", "csv_safety.py", "path_safety.py", "logging_setup.py"):
        shutil.copyfile(ROOT / "mamey" / name, package / name)
    cwd = tmp_path / "foreign"
    cwd.mkdir()
    bootstrap = """
import importlib.util
from pathlib import Path
import runpy
import sys
tool, installed, bundle = map(Path, sys.argv[1:])
sys.path[:] = [str(tool.parent), str(installed)] + [
    p for p in sys.path if p and not Path(p).resolve().is_relative_to(bundle.resolve())]
assert importlib.util.find_spec('tools') is None
assert Path(importlib.util.find_spec('mamey').origin).parent == installed / 'mamey'
sys.argv = [str(tool), '--help']
runpy.run_path(str(tool), run_name='__main__')
"""
    # -S keeps unrelated site packages/editable finders out of this controlled case.
    _help([sys.executable, "-B", "-S", "-c", bootstrap,
           str(TOOL), str(installed), str(ROOT)], cwd)
