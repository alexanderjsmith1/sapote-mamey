"""v9.7.86 A1/A2/A3: manifest carries triage scores, split candidates, per-BGC bldA tier.

Built end-to-end with the admitted full-locus synthetic fixture. Tests generic
package contracts, not public-reference biology or nonzero split-pathway detection.

v9.7.416 (BC2): these four tests were gated on a hardcoded `/mnt/user-data/uploads/` sandbox
path, so they were dark in every environment but one. While dark, A2 went STALE: v9.7.400
replaced the embedded `source_scans.rggmci` object with a channel-alias stub, and A2's direct
`["high_pairs"]` read stopped working without ever failing. A2 now follows the alias through
`mamey.scan_channel_alias.resolve_scan_channel` — the house resolver for exactly this — and
additionally asserts the channel RESOLVES, so the same silent staleness cannot recur.
"""
from __future__ import annotations
import json, os, subprocess, tempfile, glob
import pytest
import sys
from pathlib import Path

from mamey.scan_channel_alias import is_channel_stub, resolve_scan_channel

BUNDLE_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def package(tmp_path_factory, synthetic_single_contig_full_locus_zip):
    """Run the pipeline once on the admitted synthetic fixture; return (package_dir, manifest)."""
    out = str(tmp_path_factory.mktemp("a123_"))
    env = dict(os.environ, PYTHONPATH=str(BUNDLE_ROOT))
    subprocess.run(
        [sys.executable, str(BUNDLE_ROOT / "mamey_run.py"), "run",
         "--strain", "SYNTH-A123", "--display", "ref",
         "--input-zip", str(synthetic_single_contig_full_locus_zip),
         "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", out, "--mode", "gold", "--release", "PUBLIC",
         "--json-evidence", "bounded", "--brief", "none"],
        check=True, capture_output=True, timeout=300, env=env)
    pkg = glob.glob(os.path.join(out, "**", "package"), recursive=True)[0]
    return pkg, json.load(open(os.path.join(pkg, "manifest.json")))


@pytest.fixture(scope="module")
def manifest(package):
    return package[1]


def test_manifest_bgcs_carry_triage_scores(manifest):
    # A1: every bgcs[] record has numeric ab/af scores and a lead_tier
    assert manifest["bgcs"], "fixture must emit at least one BGC or this test is vacuous"
    for b in manifest["bgcs"]:
        assert isinstance(b.get("ab_score"), (int, float)), b["bgc_id"]
        assert isinstance(b.get("af_score"), (int, float)), b["bgc_id"]
        assert b.get("lead_tier"), b["bgc_id"]
        assert b.get("claim_confidence"), b["bgc_id"]


def test_split_pathway_candidates_matches_rggmci_high(package):
    # A2: top-level field length equals rggmci high_pairs (holds at 0 for single-cluster refs).
    # Since v9.7.400 the rggmci channel is an alias stub, so follow it via the house resolver.
    pkg, manifest = package
    rggmci = resolve_scan_channel(manifest.get("source_scans") or {}, "rggmci", pkg)
    assert not is_channel_stub(rggmci), (
        "rggmci channel did not resolve; a stale direct read here would silently stop testing")
    assert "high_pairs" in rggmci, "resolved rggmci channel must carry high_pairs"

    spc = manifest.get("split_pathway_candidates", [])
    assert len(spc) == rggmci["high_pairs"]
    for p in spc:
        assert "HIGH" in str(p.get("rggmci_confidence", "")).upper()


def test_blda_per_bgc_tier_populated(manifest):
    # A3: every bgcs[] record carries a bldA tier
    assert manifest["bgcs"], "fixture must emit at least one BGC or this test is vacuous"
    for b in manifest["bgcs"]:
        assert b.get("blda_tier") in ("T1", "T2", "T3", "T4"), b["bgc_id"]


def test_compound_class_annotation_present(manifest):
    # v9.7.86 annotation layer: the field exists on every BGC (may be empty chemotype)
    assert manifest["bgcs"], "fixture must emit at least one BGC or this test is vacuous"
    for b in manifest["bgcs"]:
        assert "compound_class_annotation" in b


# --- A2, non-vacuously -------------------------------------------------------
# The end-to-end check above holds at 0 == 0 on the synthetic fixture (it emits no HIGH
# RG-GMCI pair), so on its own it cannot tell a correct projection from one that always
# returns []. These unit tests drive the real projection in MameyRun.to_dict() with HIGH
# pairs present, so the equality has to mean something.

from mamey.models import AssemblyMetrics, BGCRecord, MameyRun, RunContext, SourceScanBundle

_EMPTY_SCAN = {"status": "NULL", "counts": {}, "bgc_coupling": {}}


def _bundle(rggmci: dict) -> SourceScanBundle:
    """A bundle whose only interesting member is RG-GMCI; every other scan is inert."""
    return SourceScanBundle(
        chitinase=dict(_EMPTY_SCAN), tfbs=dict(_EMPTY_SCAN), blda_tta=dict(_EMPTY_SCAN),
        regulators=dict(_EMPTY_SCAN), transporters=dict(_EMPTY_SCAN),
        resistance=dict(_EMPTY_SCAN), cctt=dict(_EMPTY_SCAN), flbr=dict(_EMPTY_SCAN),
        cassettes=dict(_EMPTY_SCAN), umed={"per_bgc": {}}, efls=dict(_EMPTY_SCAN),
        domain_architecture=dict(_EMPTY_SCAN), resistance_tiers={"per_bgc": {}},
        wetlab_rows={}, qs_signals=dict(_EMPTY_SCAN), glycosylation_arms=dict(_EMPTY_SCAN),
        per_bgc_dss={}, rggmci=rggmci,
    )


def _run_with_rggmci(rggmci: dict) -> MameyRun:
    bgcs = [BGCRecord(bgc_id=f"BGC{i:03d}", contig=f"NODE_{i}_length_1000_cov_1",
                      region_number=i, start=10, end=900, contig_length=1000,
                      products=["NRPS"], antismash_region=f"region{i:03d}",
                      node_id=f"NODE_{i}_length_1000_cov_1", release="PUBLIC",
                      privacy_tier="OPEN", privacy_assignment_state="EXACT")
            for i in (1, 2, 3)]
    return MameyRun(
        context=RunContext(strain_id="SYNTHETIC-A2", display_name="Synthetic A2",
                           version="1.9.152", analysis_mode="gold",
                           input_zip="synthetic.zip", outdir="out"),
        assembly=AssemblyMetrics(genome_bp=3000, contigs=3, n50=1000,
                                 gc_pct=70.0, largest_contig=1000),
        bgcs=bgcs, scan_status={}, source_scans=_bundle(rggmci),
    )


def _pair(name: str, confidence: str) -> dict:
    return {"pair": name, "rggmci_confidence": confidence}


def test_split_pathway_candidates_projects_only_high_pairs():
    """HIGH pairs are carried; MODERATE and LOW are not."""
    manifest = _run_with_rggmci({
        "high_pairs": 2,
        "ranked_pairs": [
            _pair("BGC001|BGC002", "HIGH_RG_GMCI_RESCUE"),
            _pair("BGC002|BGC003", "MODERATE_RG_GMCI_CANDIDATE"),
            _pair("BGC001|BGC003", "HIGH_RG_GMCI_RESCUE"),
            _pair("BGC003|BGC003", "LOW_SHARED_REFERENCE_SIGNAL"),
        ],
    }).to_dict()
    spc = manifest["split_pathway_candidates"]
    assert [p["pair"] for p in spc] == ["BGC001|BGC002", "BGC001|BGC003"]
    assert len(spc) == 2


def test_split_pathway_candidates_do_not_double_count_across_lists():
    """A HIGH pair listed in BOTH ranked_pairs and split_candidates is carried once."""
    high = _pair("BGC001|BGC002", "HIGH_RG_GMCI_RESCUE")
    manifest = _run_with_rggmci({
        "high_pairs": 1,
        "ranked_pairs": [high],
        "split_candidates": [dict(high)],
    }).to_dict()
    assert len(manifest["split_pathway_candidates"]) == 1


def test_split_pathway_candidates_empty_when_no_high_pair():
    manifest = _run_with_rggmci({
        "high_pairs": 0,
        "ranked_pairs": [_pair("BGC001|BGC002", "MODERATE_RG_GMCI_CANDIDATE")],
    }).to_dict()
    assert manifest["split_pathway_candidates"] == []
