"""B2 Phase 2 first trial: bacterial PKS/macrolide marker-debug fixtures.

These tests deliberately do not globally activate HMM/DIAMOND/BLASTP. They prove
that two public bacterial reference fixtures can drive conservative support/caution
flags through annotation/KCB text only.
"""
from pathlib import Path

import pytest

from mamey.bacterial_pks_marker_debug import summarize_marker_files
from mamey.registry_detector import ACTIVE_DETECTORS, PHASE2_DETECTORS


FIX = Path(__file__).resolve().parent / "fixtures" / "tiny_public" / "bacterial_pks_marker_debug"
OPTIONAL_FIXTURES = (
    FIX / "BGC0002086.gbk",
    FIX / "BGC0002086_knownclusterblast_c1.txt",
    FIX / "LC529898.1.gbk",
    FIX / "LC529898.1_knownclusterblast_c1.txt",
)


def _require_optional_reference_fixtures():
    missing = [str(p.relative_to(Path(__file__).resolve().parents[1])) for p in OPTIONAL_FIXTURES if not p.exists()]
    if missing:
        pytest.skip("optional bacterial PKS marker-debug fixtures absent: " + ", ".join(missing))


def test_phase2_detectors_remain_inactive_globally():
    assert ACTIVE_DETECTORS == frozenset({"regex", "motif"})
    assert {"pfam", "tigrfam", "hmm", "diamond", "blastp"} <= PHASE2_DETECTORS


def test_bgc0002086_rosamicin_marker_seed_detects_support_and_caution():
    _require_optional_reference_fixtures()
    summary = summarize_marker_files(
        "BGC0002086",
        FIX / "BGC0002086.gbk",
        FIX / "BGC0002086_knownclusterblast_c1.txt",
    )
    markers = {h.marker for h in summary.marker_hits}
    assert "ABC_F_RIBOSOMAL_PROTECTION" in markers
    assert "ERM_23S_RRNA_METHYLTRANSFERASE" in markers
    assert "GLYCOSYLTRANSFERASE" in markers
    assert "DTDP_SUGAR_AMINOTRANSFERASE" in markers
    assert "DTDP_SUGAR_LYASE" in markers
    assert "MACRO_SUGAR_TAILORING" in summary.support_flags
    assert "MACRO_RIBOSOME_RESISTANCE" in summary.support_flags
    assert "MACRO_P450_SDR_TAILORING" in summary.support_flags
    assert "BOUNDARY_TRANSPOSASE_CAUTION" in summary.caution_flags


def test_lc529898_desertomycin_marker_seed_detects_large_pks_context():
    _require_optional_reference_fixtures()
    summary = summarize_marker_files(
        "LC529898.1",
        FIX / "LC529898.1.gbk",
        FIX / "LC529898.1_knownclusterblast_c1.txt",
    )
    markers = {h.marker for h in summary.marker_hits}
    assert sum(1 for h in summary.marker_hits if h.marker == "MODULAR_POLYKETIDE_SYNTHASE") >= 8
    assert "TYPEII_THIOESTERASE" in markers
    assert "GLYCOSYLTRANSFERASE" in markers
    assert "P450_TAILORING" in markers
    assert "ABC_TRANSPORTER" in markers
    assert "LUXR_REGULATOR" in markers
    assert "LARGE_T1PKS_POLYENE_BACKBONE" in summary.support_flags
    assert "PKS_TYPEII_TE_SUPPORT" in summary.support_flags
    assert "PKS_TRANSPORTER_CONTEXT" in summary.support_flags
    assert "PKS_REGULATORY_CONTEXT" in summary.support_flags


def test_marker_debug_output_does_not_claim_product_identity():
    _require_optional_reference_fixtures()
    summary = summarize_marker_files(
        "LC529898.1",
        FIX / "LC529898.1.gbk",
        FIX / "LC529898.1_knownclusterblast_c1.txt",
    ).as_dict()
    rendered = str(summary).lower()
    forbidden = [
        "proves production",
        "confirmed metabolite",
        "makes desertomycin",
        "makes rosamicin",
    ]
    assert not any(term in rendered for term in forbidden)
