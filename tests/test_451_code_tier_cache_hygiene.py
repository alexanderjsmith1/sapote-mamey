"""Exercise the real post-audit cleanup and archiver on a tiny synthetic CODE stage.

Never execute the tier builder or the release cut script.
"""
import os
from pathlib import Path
import json
import shutil
import subprocess
import sys
import zipfile

import pytest

from tools.finalize_public_archive import ArchiveTransactionError, finalize_archive

ROOT = Path(__file__).resolve().parents[1]
BAD_PARTS = {".pytest_cache", "__pycache__", ".DS_Store"}


@pytest.mark.skipif(shutil.which("bash") is None, reason="stage cleanup requires bash")
def test_code_zip_has_no_runtime_cache_members(tmp_path):
    script = (ROOT / "tools/make_public_tier.sh").read_text()
    section = script.split("# --- 3c.", 1)[1].split("# --- 3d.", 1)[0].split("\n", 1)[1]
    assert 'public_release_audit_stage' in section
    helper = script.split('public_release_audit_stage() {', 1)[1].split(
        '\nverify_code_tier_derivation() {', 1)[0]
    helper = 'public_release_audit_stage() {' + helper
    stage = tmp_path / "CODE stage"
    (stage / "tools").mkdir(parents=True)
    (stage / "README.md").write_text("synthetic CODE payload\n")
    # Explicit audit-child stub: this fixture tests the real shell call, its
    # failure boundary and subsequent cache cleanup, not content-audit policy.
    (stage / 'tools/public_release_audit.py').write_text('''import json, os, sys
from pathlib import Path
record = {"argv": sys.argv[1:], "python": sys.executable,
          "no_bytecode": sys.dont_write_bytecode}
with Path(os.environ["AUDIT_RECORD"]).open("a") as out:
    out.write(json.dumps(record) + "\\n")
raise SystemExit(int(os.environ["AUDIT_EXIT"]))
''')
    record_path = tmp_path/'audit.jsonl'
    source = tmp_path/'source binding'; source.mkdir()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHON=sys.executable,
               STAGE=str(stage), SRC=str(source), PRIVACY_PROFILE='', TIER='code',
               AUDIT_RECORD=str(record_path), AUDIT_EXIT='9')
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_PLUGINS", None)
    command = ['bash', '-eu', '-c', helper+'\n'+section]
    failed = subprocess.run(command, cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert failed.returncode == 5 and 'final public content audit FAILED' in failed.stderr
    env['AUDIT_EXIT'] = '0'
    result = subprocess.run(command, cwd=tmp_path, env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    rows = [json.loads(line) for line in record_path.read_text().splitlines()]
    assert len(rows) == 2
    assert all(row['argv'] == [str(stage), '--file-hold-source', str(source)] for row in rows)
    assert all(row['python'] == sys.executable and row['no_bytecode'] for row in rows)
    assert not (stage / ".pytest_cache").exists()

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
    intended = stage / "figures/selected_panel.pdf"
    intended.parent.mkdir()
    intended.write_bytes(b"%PDF-1.4\nsynthetic intended figure\n")
    default = stage / "Rplots.pdf"
    default.write_bytes(b"%PDF-1.4\nsynthetic default-device debris\n")
    before = default.read_bytes()
    with pytest.raises(ArchiveTransactionError, match="root_default_r_device_output"):
        finalize_archive(stage, output, name)
    assert default.read_bytes() == before
    assert not (output / name).exists()
    # Preserve the synthetic debris outside the synthetic stage, never delete it.
    default.rename(tmp_path / "preserved_Rplots.pdf")
    finalize_archive(stage, output, name)
    with zipfile.ZipFile(output / name) as archive:
        members = archive.namelist()
        assert members
        assert not [member for member in members if BAD_PARTS.intersection(member.split("/"))]
        assert archive.read("README.md") == b"synthetic CODE payload\n"
        assert "Rplots.pdf" not in members
        assert archive.read("figures/selected_panel.pdf") == intended.read_bytes()
    assert (stage / "README.md").read_text() == "synthetic CODE payload\n"
