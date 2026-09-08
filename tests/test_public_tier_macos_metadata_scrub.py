"""The tier builder removes Finder metadata from staging before content audits."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _build_stamp(root: Path) -> str | None:
    match = re.search(
        r"build=(\S+)",
        (root / "BUILD_STAMP.txt").read_text(encoding="utf-8"),
    )
    return match.group(1) if match else None


@pytest.mark.skipif(not shutil.which("bash"), reason="bash unavailable")
def test_code_tier_scrubs_ds_store_from_stage_without_mutating_source(tmp_path: Path):
    source = tmp_path / "source"
    shutil.copytree(
        ROOT,
        source,
        ignore=shutil.ignore_patterns(".DS_Store", ".pytest_cache", "__pycache__"),
    )
    nested = source / "docs" / ".DS_Store"
    root_metadata = source / ".DS_Store"
    nested.write_bytes(b"Finder metadata fixture\x00")
    root_metadata.write_bytes(b"Finder metadata fixture\x00")

    out = tmp_path / "out"
    out.mkdir()
    stamp = _build_stamp(source)
    assert stamp, "fixture must retain a usable build stamp"
    env = {**os.environ, "BUILD_STAMP": stamp, "SKIP_INTIER_PYTEST": "1", "PYTHON": sys.executable}  # v9.7.410: the cut script honours $PYTHON
    result = subprocess.run(
        ["bash", "tools/make_public_tier.sh", "code", str(source), str(out)],
        cwd=source,
        env=env,
        capture_output=True,
        text=True,
        timeout=420,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined[-3000:]
    archives = list(out.glob("*.zip"))
    assert len(archives) == 1, [path.name for path in archives]
    with zipfile.ZipFile(archives[0]) as archive:
        assert not [name for name in archive.namelist() if name.endswith(".DS_Store")]

    assert root_metadata.read_bytes() == b"Finder metadata fixture\x00"
    assert nested.read_bytes() == b"Finder metadata fixture\x00"
