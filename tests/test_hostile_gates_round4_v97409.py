"""v9.7.409 — fourth hostile pass on sealed .408: post-seal readers. H14 compile-report built a deliverable from a
package that no longer validates; H15 ingest-blastp traced back on a garbage master workbook."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


def _run(args, timeout=900):
    return subprocess.run([sys.executable, str(ROOT / "mamey_run.py")] + args, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout)


def _package(tmp_path):
    out = tmp_path / "run"
    r = _run(["run", "--strain", "TEST-01", "--input-zip", str(SMOKE), "--outdir", str(out), "--mode", "gold", "--capped-session", "--json-evidence", "off"])
    assert r.returncode == 0, r.stdout[-600:]
    return out / "TEST-01" / "package"


def test_compile_report_refuses_a_package_that_no_longer_validates(tmp_path):
    pkg = _package(tmp_path)
    (next(pkg.glob("*_4_triage_board.csv"))).unlink()          # tamper AFTER seal: gate_validation.json still says PASS
    r = _run(["compile-report", str(pkg)])
    assert r.returncode != 0 and "REFUSED" in r.stderr and "validate" in r.stderr, r.stderr[-400:]
    assert "Traceback" not in r.stderr


def test_compile_report_refuses_manifest_identity_swap(tmp_path):
    pkg = _package(tmp_path)
    m = json.loads((pkg / "manifest.json").read_text(encoding="utf-8")); m["strain_id"] = "AS-999"; m["strain"] = "AS-999"
    (pkg / "manifest.json").write_text(json.dumps(m), encoding="utf-8")
    r = _run(["compile-report", str(pkg)])
    assert r.returncode != 0 and "identity_binding" in r.stderr, r.stderr[-400:]


def test_compile_report_still_runs_on_a_valid_package(tmp_path):
    pkg = _package(tmp_path)
    r = _run(["compile-report", str(pkg)])
    assert r.returncode == 0, r.stderr[-400:]


def test_ingest_blastp_refuses_unreadable_master_without_traceback(tmp_path):
    pkg = _package(tmp_path)
    bad = tmp_path / "master.xlsx"; bad.write_bytes(b"not a workbook")
    # Admit a valid HitTable so this control reaches the corrupt-workbook boundary.
    hits = tmp_path / "hits.csv"
    hits.write_text("query001,subject001,90,20,0,0,1,20,1,20,1e-20,100\n", encoding="utf-8")
    r = _run(["ingest-blastp", "--master", str(bad), "--strain", "TEST-01", "--hit-table", str(hits), "--package", str(pkg)])
    assert r.returncode != 0 and "master workbook unreadable" in r.stderr, r.stderr[-400:]
    assert "Traceback" not in r.stderr
