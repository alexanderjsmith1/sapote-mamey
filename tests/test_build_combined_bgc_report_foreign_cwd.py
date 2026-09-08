"""Portable front-door regression for build_combined_bgc_report.py.

The source-tree tool must expose ``--help`` even when invoked by absolute path
from a directory that neither contains nor installs the ``mamey`` package.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


CODE_TIER = Path(__file__).resolve().parents[1]
SCRIPT = CODE_TIER / "tools" / "build_combined_bgc_report.py"


def test_combined_report_help_from_foreign_cwd(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "--job-spec" in result.stdout
    assert "--source-root" in result.stdout
    assert "--out-root" in result.stdout
