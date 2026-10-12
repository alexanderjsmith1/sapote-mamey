"""The tier builder removes Finder metadata from staging before content audits."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

from tests._public_cut_fixture import public_cut_env, public_cut_source


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(not shutil.which("bash"), reason="bash unavailable")
def test_code_tier_scrubs_ds_store_from_stage_without_mutating_source(tmp_path: Path):
    source = public_cut_source(tmp_path)
    nested = source / "docs" / ".DS_Store"
    root_metadata = source / ".DS_Store"
    nested.write_bytes(b"Finder metadata fixture\x00")
    root_metadata.write_bytes(b"Finder metadata fixture\x00")

    out = tmp_path / "out"
    out.mkdir()
    env = public_cut_env()
    result = subprocess.run(
        ["bash", str(ROOT / "tools/make_public_tier.sh"), "code", str(source), str(out)],
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
