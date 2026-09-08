"""v9.7.409 — third hostile pass on sealed .408: H12 oversized annotation field crashes CSV read-back;
H13 two concurrent runs into one package race on an atomic rename."""
from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


def _run(args, timeout=900):
    return subprocess.run([sys.executable, str(ROOT / "mamey_run.py")] + args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def test_engine_reads_back_its_own_long_csv_fields(tmp_path):
    """A 300 KB /product qualifier (well over csv's 128 KB default limit) must not crash validate."""
    big = tmp_path / "patho.zip"
    with zipfile.ZipFile(SMOKE) as src, zipfile.ZipFile(big, "w") as dst:
        for n in src.namelist():
            d = src.read(n)
            if n.endswith("region001.gbk"):
                d = d.decode("utf-8", "replace").replace('/product="', '/product="' + "A" * 300_000, 1).encode()
            dst.writestr(n, d)
    r = _run(["run", "--strain", "P1", "--input-zip", str(big), "--outdir", str(tmp_path / "out"), "--mode", "gold", "--capped-session", "--json-evidence", "off"])
    assert "Traceback" not in r.stdout + r.stderr, (r.stdout + r.stderr)[-600:]
    assert r.returncode == 0 and "MAMEY_COMPLETE" in r.stdout


def test_csv_field_limit_is_raised_on_import():
    import csv
    import mamey.validate  # noqa: F401  (raises the limit at import)
    assert csv.field_size_limit() >= 2**31 - 1


@pytest.mark.skipif(sys.platform == "win32", reason="advisory locks are POSIX")
def test_second_run_into_a_locked_package_is_refused(tmp_path):
    import fcntl
    out = tmp_path / "out"; (out / "L1").mkdir(parents=True)
    fh = open(out / "L1" / ".mamey.lock", "a+")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        r = _run(["run", "--strain", "L1", "--input-zip", str(SMOKE), "--outdir", str(out), "--mode", "gold", "--capped-session", "--json-evidence", "off"])
        assert r.returncode != 0 and "[lock]" in r.stderr, r.stderr[-400:]
        assert not any((out / "L1" / "package").iterdir()) if (out / "L1" / "package").exists() else True, "a refused run must not write into the package"
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN); fh.close()
    r = _run(["run", "--strain", "L1", "--input-zip", str(SMOKE), "--outdir", str(out), "--mode", "gold", "--capped-session", "--json-evidence", "off"])
    assert r.returncode == 0, "once the lock is released the same run proceeds"


def test_lock_file_never_enters_the_package_checksums(tmp_path):
    out = tmp_path / "out"
    r = _run(["run", "--strain", "L2", "--input-zip", str(SMOKE), "--outdir", str(out), "--mode", "gold", "--capped-session", "--json-evidence", "off"])
    assert r.returncode == 0
    assert (out / "L2" / ".mamey.lock").exists()
    sums = (out / "L2" / "package" / "checksums_sha256.txt").read_text(encoding="utf-8")
    assert ".mamey.lock" not in sums
    assert _run(["validate", str(out / "L2" / "package")]).returncode == 0
