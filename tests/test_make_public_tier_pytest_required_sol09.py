"""The public-tier builder must not silently turn a missing test runner into permission to ship."""
from __future__ import annotations

import os
from pathlib import Path
import shlex
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "tools" / "make_public_tier.sh"


def _wrapper(path: Path, *, pytest_probe: bool, pytest_exit: int = 0) -> Path:
    lines = ["#!/bin/sh"]
    lines += [
        'if [ "$1" = "-c" ] && [ "$2" = "import pytest" ]; then',
        f"  exit {0 if pytest_probe else 1}",
        "fi",
    ]
    if pytest_probe:
        lines += [
            'if [ "$1" = "-m" ] && [ "$2" = "pytest" ]; then',
            '  echo "synthetic pytest failure control" >&2',
            f"  exit {pytest_exit}",
            "fi",
        ]
    lines.append(f"exec {shlex.quote(sys.executable)} \"$@\"")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)
    return path


def _run(tmp_path: Path, wrapper: Path) -> subprocess.CompletedProcess[str]:
    output = tmp_path / "output"
    output.mkdir()
    env = {
        **os.environ,
        "BUILD_STAMP": "20260909v97420a",
        "PYTHON": str(wrapper),
    }
    return subprocess.run(
        ["bash", str(BUILDER), "public", str(ROOT), str(output)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
        check=False,
    )


def test_missing_pytest_refuses_before_archive_commit(tmp_path):
    wrapper = _wrapper(tmp_path / "python-without-pytest", pytest_probe=False)
    result = _run(tmp_path, wrapper)

    assert result.returncode != 0
    assert "RELEASE GATE FAILED: pytest is required" in result.stderr
    assert not list((tmp_path / "output").glob("*.zip"))


def test_real_pytest_failure_still_refuses_before_archive_commit(tmp_path):
    wrapper = _wrapper(tmp_path / "python-with-failing-pytest", pytest_probe=True, pytest_exit=7)
    result = _run(tmp_path, wrapper)

    assert result.returncode != 0
    assert "pytest reported failures" in result.stderr
    assert "synthetic pytest failure control" in result.stderr
    assert not list((tmp_path / "output").glob("*.zip"))
