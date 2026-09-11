"""v9.7.87 9.7.87-B + 9.7.87-C: release class is surfaced on the compact dashboard
(manifest_short.json) and as a row-level inventory CSV column.

Uses the admitted full-locus synthetic fixture for the end-to-end surface check, plus a direct unit check of the PRIVATE fail-safe via resolve_release
on a synthetic AS-style id (no private genome needed)."""
from __future__ import annotations
import json, os, subprocess, tempfile, glob, csv
import pytest
import sys
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parents[1]

from mamey.dedup_and_guard import resolve_release



def test_resolve_release_fail_safe_private_for_as_style_id():
    # v9.7.236: AS- resolves PUBLIC per PI decision; the PRIVATE guard now keys on AJS-/PENDING-.
    assert resolve_release("AS-001", None)[0] == "PUBLIC"   # synthetic, not a real strain
    rel, _ = resolve_release("AJS-001", None)
    assert rel == "PRIVATE"
    rel2, _ = resolve_release("PENDING-002", None)
    assert rel2 == "PRIVATE"


def test_manifest_short_and_inventory_carry_release_public(tmp_path, synthetic_single_contig_full_locus_zip):
    out = str(tmp_path / "run")
    env = dict(os.environ, PYTHONPATH=str(BUNDLE_ROOT))
    subprocess.run(
        [sys.executable, str(BUNDLE_ROOT / "mamey_run.py"), "run", "--strain", "SID-reltest", "--display", "ref",
         "--input-zip", str(synthetic_single_contig_full_locus_zip), "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", out, "--mode", "gold", "--release", "PUBLIC",
         "--json-evidence", "bounded", "--brief", "none"],
        check=True, capture_output=True, timeout=300, env=env)
    pkg = glob.glob(os.path.join(out, "**", "package"), recursive=True)[0]

    ms = json.load(open(os.path.join(pkg, "manifest_short.json")))
    assert ms.get("release") == "PUBLIC", "manifest_short must carry the release class"

    inv = glob.glob(os.path.join(pkg, "*_2_inventory.csv"))[0]
    with open(inv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert "Release" in rows[0], "inventory CSV must carry a Release column"
    assert all(r["Release"] == "PUBLIC" for r in rows)
