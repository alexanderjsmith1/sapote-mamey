"""Tests for the v9.7.21 marker decision: T43-NUC narrowing + T43-BLA beta-lactam anchor.

Decision (validated against the reference set): the architecture layer subsumes the would-be T43-POL/GPA
keyword markers (aromatic T2PKS, glycopeptide get capacity calls), so those are NOT added; the two markers
that close real gaps are built — T43-NUC narrowed for claim-safety, T43-BLA for the beta-lactam anchor gap.
"""
import os
import re

from mamey import parsers
from mamey.source_scans import CCTT_PATTERNS, run_source_scans
from mamey.scoring import AB_DIAGNOSTIC_TRIGGERS, AF_DIAGNOSTIC_TRIGGERS

UPS = "/mnt/user-data/uploads"


def _fires(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)


def test_t43_nuc_no_longer_fires_on_generic_nucleoside():
    # the over-broad bare "nucleoside" term is gone: generic nucleoside metabolism must NOT trip an AF call
    pats = CCTT_PATTERNS["T43-NUC_nucleoside"]
    assert not _fires(pats, "nucleoside-diphosphate-sugar epimerase; nucleoside 2-deoxyribosyltransferase")


def test_t43_nuc_still_fires_on_nikkomycin_polyoxin():
    pats = CCTT_PATTERNS["T43-NUC_nucleoside"]
    assert _fires(pats, "nikkomycin biosynthesis protein NikJ")
    assert _fires(pats, "polyoxin biosynthetic cluster")


def test_t43_nuc_feeds_antifungal_axis():
    # nikkomycin/polyoxin are chitin-synthase-inhibitor antifungals -> must surface as AF
    assert "T43-NUC" in AF_DIAGNOSTIC_TRIGGERS


def test_t43_bla_exists_and_feeds_antibacterial_axis():
    assert "T43-BLA_betalactam" in CCTT_PATTERNS
    assert "T43-BLA" in AB_DIAGNOSTIC_TRIGGERS


def test_t43_bla_fires_on_nocardicin():
    p = os.path.join(UPS, "Nocardicin_AY541063.zip")
    if not os.path.exists(p):
        return
    bgcs = parsers.parse_bgcs_from_zip(p)
    cds = parsers.extract_cds_features(p)
    contigs = parsers.extract_contig_sequences(p)
    doms = parsers.extract_domain_features(p)
    ss = run_source_scans(bgcs, cds, contigs, doms)
    per = ss.cctt.get("per_bgc", {})
    b = max(bgcs, key=lambda x: x.end - x.start)
    assert any("T43-BLA" in str(m) for m in per.get(b.bgc_id, []))


def test_t43_bla_does_not_fire_on_unrelated():
    pats = CCTT_PATTERNS["T43-BLA_betalactam"]
    assert not _fires(pats, "beta-lactamase resistance protein; ABC transporter")  # resistance, not biosynthesis


def test_t43_dkp_vetoed_in_copalyl_context():
    # viguiepinol: ent-CDPS (copalyl diphosphate synthase, a terpene cyclase) collides with the cyclodipeptide
    # synthase (CDPS) token; the copalyl-context veto must suppress the spurious T43-DKP on this terpene cluster.
    p = os.path.join(UPS, "viguiepinol_BGC0000286.zip")
    if not os.path.exists(p):
        return
    bgcs = parsers.parse_bgcs_from_zip(p)
    cds = parsers.extract_cds_features(p)
    contigs = parsers.extract_contig_sequences(p)
    doms = parsers.extract_domain_features(p)
    ss = run_source_scans(bgcs, cds, contigs, doms)
    b = max(bgcs, key=lambda x: x.end - x.start)
    fired = [str(m) for m in ss.cctt.get("per_bgc", {}).get(b.bgc_id, [])]
    assert not any("T43-DKP" in m for m in fired), f"T43-DKP should be vetoed on viguiepinol, got {fired}"


def test_t43_dkp_survives_for_real_cdps():
    # albonoursin (genuine diketopiperazine): no copalyl context, so the veto must NOT fire
    p = os.path.join(UPS, "BGC0000851.zip")
    if not os.path.exists(p):
        return
    bgcs = parsers.parse_bgcs_from_zip(p)
    cds = parsers.extract_cds_features(p)
    contigs = parsers.extract_contig_sequences(p)
    doms = parsers.extract_domain_features(p)
    ss = run_source_scans(bgcs, cds, contigs, doms)
    b = max(bgcs, key=lambda x: x.end - x.start)
    fired = [str(m) for m in ss.cctt.get("per_bgc", {}).get(b.bgc_id, [])]
    assert any("T43-DKP" in m for m in fired), f"real DKP must survive, got {fired}"


def test_nuc_veto_not_defeated_by_nucleoside_sugar():
    """BH-001: T43-NUC veto misfire on nucleoside-sugar product class.

    antiSMASH uses bare 'nucleoside' for true nucleoside antibiotic clusters.
    'nucleoside-sugar' is a sugar-nucleotide biosynthesis pathway — NOT a nucleoside
    antibiotic. The veto check used bare substring matching, so 'nucleoside' inside
    'nucleoside-sugar' prevented the veto from firing, giving the glycogen/APH cluster
    a false +25 AF diagnostic bonus.

    Fix: token-split on [;,/|]+ or whitespace before membership test.
    """
    from types import SimpleNamespace
    from mamey.source_scans import apply_cctt_vetoes, _region_context

    # Simulate a BGC typed nucleoside-sugar in a glycogen/trehalose context
    bgc = SimpleNamespace(
        bgc_id="BGC_TEST_NUC",
        products=["nucleoside-sugar", "saccharide"],
        start=0, end=10000, contig="NODE_1"
    )

    # Minimal cctt with T43-NUC_nucleoside in coupling
    cctt = {
        "bgc_coupling": {"BGC_TEST_NUC": ["T43-NUC_nucleoside"]},
        "bgc_coupling_context": {},
        "related_family_vetoes": {},
        "veto_claim_safety": "",
        "status": "SOURCE_DERIVED",
        "hits": {},
        "counts": {},
        "per_bgc": {},
        "claim_safety": "",
    }

    # CDS list with a glycogen/trehalose context marker so the veto can fire
    # The veto needs v[0] ('glycogen_trehalose') in ctx — supply a matching CDS
    cds_glycogen = SimpleNamespace(
        locus_tag="g1", start=100, end=1000, contig="NODE_1",
        qualifiers={"gene_functions": ["biosynthetic glycogen_trehalose synthase"]},
        gene_functions=["biosynthetic glycogen_trehalose synthase"],
        product="glycogen_trehalose synthase"
    )

    result = apply_cctt_vetoes(cctt, [bgc], [cds_glycogen])

    # After fix: T43-NUC_nucleoside must be VETOED (suppressed) on nucleoside-sugar
    remaining = result.get("bgc_coupling", {}).get("BGC_TEST_NUC", [])
    vetoed = result.get("related_family_vetoes", {}).get("BGC_TEST_NUC", [])
    assert "T43-NUC_nucleoside" not in remaining, (
        f"BH-001: T43-NUC_nucleoside must be vetoed on nucleoside-sugar product class, "
        f"but it survived. remaining={remaining}"
    )
    assert any(v["marker"] == "T43-NUC_nucleoside" for v in vetoed), (
        f"BH-001: veto not recorded in audit trail. vetoed={vetoed}"
    )


def test_nuc_veto_does_not_fire_on_bare_nucleoside():
    """BH-001 companion: true nucleoside antibiotic cluster must NOT be vetoed.

    antiSMASH product class 'nucleoside' is the real nucleoside antibiotic label.
    The veto must not suppress T43-NUC when the cluster is genuinely typed nucleoside.
    """
    from types import SimpleNamespace
    from mamey.source_scans import apply_cctt_vetoes

    bgc = SimpleNamespace(
        bgc_id="BGC_TEST_NUC_REAL",
        products=["nucleoside", "other"],
        start=0, end=10000, contig="NODE_1"
    )

    cctt = {
        "bgc_coupling": {"BGC_TEST_NUC_REAL": ["T43-NUC_nucleoside"]},
        "bgc_coupling_context": {},
        "related_family_vetoes": {},
        "veto_claim_safety": "",
        "status": "SOURCE_DERIVED",
        "hits": {}, "counts": {}, "per_bgc": {}, "claim_safety": "",
    }

    cds_glycogen = SimpleNamespace(
        locus_tag="g1", start=100, end=1000, contig="NODE_1",
        qualifiers={"gene_functions": ["biosynthetic glycogen_trehalose synthase"]},
        gene_functions=["biosynthetic glycogen_trehalose synthase"],
        product="glycogen_trehalose synthase"
    )

    result = apply_cctt_vetoes(cctt, [bgc], [cds_glycogen])
    remaining = result.get("bgc_coupling", {}).get("BGC_TEST_NUC_REAL", [])
    assert "T43-NUC_nucleoside" in remaining, (
        f"BH-001: true nucleoside cluster must keep T43-NUC_nucleoside, "
        f"but it was vetoed. remaining={remaining}"
    )
