"""v9.7.86 A1/A2/A3: manifest carries triage scores, split candidates, per-BGC bldA tier.

Built end-to-end against a PUBLIC reference so the test ships safely in all tiers and
does not depend on any private strain. Skips cleanly if no reference zip is present.
"""
from __future__ import annotations
import json, os, subprocess, tempfile, glob
import pytest

# public MIBiG reference clusters (no private strain data); first present one is used
_CANDIDATES = [
    "/mnt/user-data/uploads/BGC0000093.zip",
    "/mnt/user-data/uploads/BGC0000218.zip",
]
REF = next((p for p in _CANDIDATES if os.path.exists(p)), None)
pytestmark = pytest.mark.skipif(REF is None, reason="no public reference cluster present")


@pytest.fixture(scope="module")
def manifest():
    out = tempfile.mkdtemp(prefix="a123_")
    env = dict(os.environ, PYTHONPATH=".")
    subprocess.run(
        ["python3", "-m", "mamey", "run", "--strain", "MIBIG-REF", "--display", "ref",
         "--input-zip", REF, "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", out, "--mode", "standard", "--release", "PUBLIC",
         "--json-evidence", "bounded"],
        check=True, capture_output=True, timeout=300, env=env)
    pkgs = glob.glob(os.path.join(out, "**", "package"), recursive=True)
    return json.load(open(os.path.join(pkgs[0], "manifest.json")))


def test_manifest_bgcs_carry_triage_scores(manifest):
    # A1: every bgcs[] record has numeric ab/af scores and a lead_tier
    for b in manifest["bgcs"]:
        assert isinstance(b.get("ab_score"), (int, float)), b["bgc_id"]
        assert isinstance(b.get("af_score"), (int, float)), b["bgc_id"]
        assert b.get("lead_tier"), b["bgc_id"]
        assert b.get("claim_confidence"), b["bgc_id"]


def test_split_pathway_candidates_matches_rggmci_high(manifest):
    # A2: top-level field length equals rggmci high_pairs (holds at 0 for single-cluster refs)
    spc = manifest.get("split_pathway_candidates", [])
    high = manifest["source_scans"]["rggmci"]["high_pairs"]
    assert len(spc) == high
    for p in spc:
        assert "HIGH" in str(p.get("rggmci_confidence", "")).upper()


def test_blda_per_bgc_tier_populated(manifest):
    # A3: every bgcs[] record carries a bldA tier
    for b in manifest["bgcs"]:
        assert b.get("blda_tier") in ("T1", "T2", "T3", "T4"), b["bgc_id"]


def test_compound_class_annotation_present(manifest):
    # v9.7.86 annotation layer: the field exists on every BGC (may be empty chemotype)
    for b in manifest["bgcs"]:
        assert "compound_class_annotation" in b
