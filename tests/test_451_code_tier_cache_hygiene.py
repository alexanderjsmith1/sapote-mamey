"""Exercise the real post-audit cleanup and archiver on a tiny synthetic CODE stage.

Never execute the tier builder or the release cut script.
"""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import zipfile

import pytest

from tools.finalize_public_archive import finalize_archive

ROOT = Path(__file__).resolve().parents[1]
BAD_PARTS = {".pytest_cache", "__pycache__", ".DS_Store"}


@pytest.mark.skipif(shutil.which("bash") is None, reason="stage cleanup requires bash")
def test_code_zip_has_no_runtime_cache_members(tmp_path):
    script = (ROOT / "tools/make_public_tier.sh").read_text()
    section = script.split("# --- 3c.", 1)[1].split("# --- 3d.", 1)[0]
    audit_line = next(line for line in section.splitlines() if "-m pytest" in line)
    # Run only the exact pytest argv from section 3c, never the builder or its fallback.
    argv = shlex.split(audit_line.split("&& {", 1)[1].split("2>/dev/null", 1)[0])
    assert argv[0] == "$PYTHON"
    stage = tmp_path / "CODE stage"
    (stage / "tests").mkdir(parents=True)
    (stage / "tests/test_no_unpublished_ids_in_public_tier.py").write_text(
        'def test_synthetic_stage():\n    assert "SYN-971".startswith("SYN-")\n')
    (stage / "README.md").write_text("synthetic CODE payload\n")
    # Neutralize inherited pytest configuration for the standalone fake stage.
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_PLUGINS", None)
    result = subprocess.run([sys.executable, *argv[1:]], cwd=stage, env=env,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (stage / ".pytest_cache").exists(), "section 3c recreated pytest cache"

    # Simulate debris left by a later audit, including nested cache directories.
    for relative in (".pytest_cache/v/cache/nodeids", "nested/.pytest_cache/README.md",
                     "nested/__pycache__/stub.pyc", ".DS_Store", "nested/.DS_Store"):
        path = stage / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic cache")
    cleanup = script.split("# BEGIN FINAL_STAGE_CACHE_CLEANUP\n", 1)[1].split(
        "# END FINAL_STAGE_CACHE_CLEANUP", 1)[0]
    result = subprocess.run(["bash", "-e", "-c", cleanup], cwd=tmp_path,
                            env=dict(env, STAGE=str(stage)), capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not [path for path in stage.rglob("*") if path.name in BAD_PARTS]

    output = tmp_path / "archives"
    output.mkdir()
    name = "sapote-mamey-v0.0.0-CODE-synthetic.zip"
    finalize_archive(stage, output, name)
    with zipfile.ZipFile(output / name) as archive:
        members = archive.namelist()
        assert members
        assert not [member for member in members if BAD_PARTS.intersection(member.split("/"))]
        assert archive.read("README.md") == b"synthetic CODE payload\n"
    assert (stage / "README.md").read_text() == "synthetic CODE payload\n"
