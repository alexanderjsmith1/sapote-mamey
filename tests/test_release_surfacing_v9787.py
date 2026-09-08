"""v9.7.87 9.7.87-B + 9.7.87-C: release class is surfaced on the compact dashboard
(manifest_short.json) and as a row-level inventory CSV column.

Uses a PUBLIC MIBiG reference for the end-to-end surface check (so no private strain ID
ships in this test), plus a direct unit check of the PRIVATE fail-safe via resolve_release
on a synthetic AS-style id (no private genome needed)."""
from __future__ import annotations
import json, os, subprocess, tempfile, glob, csv
import pytest

from mamey.dedup_and_guard import resolve_release

_REFS = ["/mnt/user-data/uploads/BGC0000093.zip", "/mnt/user-data/uploads/BGC0000218.zip"]
REF = next((p for p in _REFS if os.path.exists(p)), None)


def test_resolve_release_fail_safe_private_for_as_style_id():
    # v9.7.236: AS- resolves PUBLIC per PI decision; the PRIVATE guard now keys on AJS-/PENDING-.
    assert resolve_release("AS-001", None)[0] == "PUBLIC"   # synthetic, not a real strain
    rel, _ = resolve_release("AJS-001", None)
    assert rel == "PRIVATE"
    rel2, _ = resolve_release("PENDING-002", None)
    assert rel2 == "PRIVATE"


@pytest.mark.skipif(REF is None, reason="no public reference cluster present")
def test_manifest_short_and_inventory_carry_release_public():
    out = tempfile.mkdtemp(prefix="rel_")
    env = dict(os.environ, PYTHONPATH=".")
    subprocess.run(
        ["python3", "-m", "mamey", "run", "--strain", "SID-reltest", "--display", "ref",
         "--input-zip", REF, "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", out, "--mode", "standard", "--release", "PUBLIC",
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
