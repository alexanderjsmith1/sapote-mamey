"""Release-blocker regressions for ChatGPT-safe package sealing instrumentation (v9.7.128)."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


def _receipts(pkg_dir):
    return [json.loads(line) for line in (pkg_dir / "run_phase_receipts.jsonl").read_text().splitlines() if line.strip()]


@pytest.mark.skipif(not FIXTURE.exists(), reason="smoke fixture absent")
def test_chatgpt_safe_has_terminal_subphase_receipts(tmp_path):
    out = tmp_path / "out"
    cmd = [sys.executable, "-m", "mamey", "run", "--chatgpt-safe",
           "--strain", "RB_SAFE", "--input-zip", str(FIXTURE),
           "--taxonomy", "Test species", "--source", "fixture",
           "--mode", "gold", "--chatgpt-followup", "--outdir", str(out)]
    subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=180, check=True)
    pkg = out / "RB_SAFE" / "package"
    phases = {(r.get("phase"), r.get("status")) for r in _receipts(pkg)}
    assert ("write_package", "END") in phases
    assert ("per_strain_workbook", "END") in phases
    assert ("workbook", "END") in phases
    assert ("manifest_write", "END") in phases
    assert ("zip_package", "END") in phases


def test_zip_package_honors_stored_env(tmp_path, monkeypatch):
    from mamey.packaging import zip_package
    pkg = tmp_path / "run" / "package"
    pkg.mkdir(parents=True)
    (pkg / "a.txt").write_text("hello")
    out = tmp_path / "run" / "pkg.zip"
    monkeypatch.setenv("MAMEY_ZIP_COMPRESSION", "stored")
    zip_package(pkg, out)
    with zipfile.ZipFile(out) as zf:
        infos = [i for i in zf.infolist() if i.filename.endswith("a.txt")]
    assert infos and infos[0].compress_type == zipfile.ZIP_STORED
