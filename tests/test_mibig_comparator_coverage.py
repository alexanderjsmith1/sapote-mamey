"""Tests for the FA2 two-denominator comparator-coverage evidence layer.

Report-only / non-scoring layer: these tests assert the two denominators, the
collision flag on a transport-only comparator, within-BGC specificity
(UNIQUE vs CO_DOMINANT), gene-role classification, and the report-only contract.
"""
from __future__ import annotations

from mamey import mibig_comparator_coverage as mcc


# ---------------------------------------------------------------------------
# gene-role classification (antiSMASH gene_functions -> role)
# ---------------------------------------------------------------------------
def test_classify_gene_role_core_vs_tailoring_vs_accessory():
    assert (
        mcc.classify_gene_role("biosynthetic (rule-based-clusters) saccharide: RmlD_sub_bind")
        == mcc.ROLE_CORE
    )
    # additional == tailoring, NOT defining core
    assert (
        mcc.classify_gene_role("biosynthetic-additional (smcogs) SMCOG1152: nucleotide sugar dehydrogenase")
        == mcc.ROLE_TAILORING
    )
    assert (
        mcc.classify_gene_role("transport (smcogs) SMCOG1288: ABC transporter related protein")
        == mcc.ROLE_TRANSPORT
    )
    assert (
        mcc.classify_gene_role("regulatory (smcogs) SMCOG1057: TetR family transcriptional regulator")
        == mcc.ROLE_REGULATORY
    )
    # core wins when a core token co-occurs with a tailoring token
    mixed = "biosynthetic (rule-based-clusters) NRPS: AMP-binding biosynthetic-additional (smcogs) SMCOG1"
    assert mcc.classify_gene_role(mixed) == mcc.ROLE_CORE
    # no functions but has sec_met domains -> accessory biosynthetic; nothing -> unknown
    assert mcc.classify_gene_role("", "PKS_KR; adh_short") == mcc.ROLE_TAILORING
    assert mcc.classify_gene_role("", "") == mcc.ROLE_UNKNOWN


def test_load_locus_genes_from_cds_rows():
    cds_rows = [
        {"bgc_id": "BGC_A", "locus_tag": "g1", "gene_functions": "biosynthetic (rule-based-clusters) x", "sec_met_domains": ""},
        {"bgc_id": "BGC_A", "locus_tag": "g4", "gene_functions": "transport (smcogs) ABC", "sec_met_domains": ""},
    ]
    inv = mcc.load_locus_genes(cds_rows)
    assert inv["BGC_A"]["g1"] == mcc.ROLE_CORE
    assert inv["BGC_A"]["g4"] == mcc.ROLE_TRANSPORT


# ---------------------------------------------------------------------------
# fixtures: a 6-gene locus with 2 defining-core genes
# ---------------------------------------------------------------------------
def _bgc_a_inventory():
    # all_locus = 6, all_core = 2 (g1, g2)
    return {
        "BGC_A": {
            "g1": mcc.ROLE_CORE,
            "g2": mcc.ROLE_CORE,
            "g3": mcc.ROLE_TAILORING,
            "g4": mcc.ROLE_TRANSPORT,
            "g5": mcc.ROLE_REGULATORY,
            "g6": mcc.ROLE_OTHER,
        }
    }


def _hit(bgc, q, acc, pid=80.0, compound="", rtype="PKS", rank=1):
    return {
        "bgc_id": bgc,
        "query_gene": q,
        "subject_gene": f"{acc}_{q}",
        "mibig_accession": acc,
        "mibig_compound": compound,
        "reference_type": rtype,
        "pct_identity": pid,
        "blast_score": 300.0,
        "reference_rank": rank,
    }


def _row_for(result, bgc, acc):
    for r in result["rows"]:
        if r["bgc_id"] == bgc and r["mibig_accession"] == acc:
            return r
    raise AssertionError(f"no row for {bgc}/{acc}")


# ---------------------------------------------------------------------------
# two-denominator coverage
# ---------------------------------------------------------------------------
def test_two_denominator_coverage():
    per_gene = [
        # CORE1 hits 2 core + 1 tailoring gene
        _hit("BGC_A", "g1", "BGC_CORE", compound="coreymycin"),
        _hit("BGC_A", "g2", "BGC_CORE", compound="coreymycin"),
        _hit("BGC_A", "g3", "BGC_CORE", compound="coreymycin"),
    ]
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=_bgc_a_inventory())
    row = _row_for(result, "BGC_A", "BGC_CORE")
    # denominator 1: matched genes / all physical locus genes = 3/6
    assert row["matched_locus_genes"] == 3
    assert row["all_locus_genes"] == 6
    assert row["locus_coverage"] == 0.5
    # denominator 2: matched defining-core / all defining-core = 2/2
    assert row["matched_core_genes"] == 2
    assert row["all_core_genes"] == 2
    assert row["core_coverage"] == 1.0
    assert row["collision_flag"] == "OK_HAS_CORE_SUPPORT"
    assert result["report_only_contract"] == "REPORT_ONLY_NO_SCORING"


def test_identity_below_threshold_not_counted():
    per_gene = [
        _hit("BGC_A", "g1", "BGC_WEAK", pid=20.0),  # below RECOGNIZABLE_MIN_IDENTITY
        _hit("BGC_A", "g2", "BGC_WEAK", pid=90.0),
    ]
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=_bgc_a_inventory())
    row = _row_for(result, "BGC_A", "BGC_WEAK")
    assert row["matched_locus_genes"] == 1  # only g2 counts
    assert row["matched_core_genes"] == 1


# ---------------------------------------------------------------------------
# collision / promiscuity flag on a transport-only comparator
# ---------------------------------------------------------------------------
def test_collision_flag_transport_only_comparator():
    per_gene = [
        # comparator supported ONLY by transport + regulatory genes, no core
        _hit("BGC_A", "g4", "BGC_TRANSPORT", compound="apramycin"),
        _hit("BGC_A", "g5", "BGC_TRANSPORT", compound="apramycin"),
    ]
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=_bgc_a_inventory())
    row = _row_for(result, "BGC_A", "BGC_TRANSPORT")
    assert row["matched_core_genes"] == 0
    assert row["core_coverage"] == 0.0
    assert row["matched_transport"] == 1
    assert row["matched_regulatory"] == 1
    assert row["collision_flag"] == "LOW_SPECIFICITY_ACCESSORY_ONLY"
    assert result["summary"]["low_specificity_collision_count"] == 1


def test_no_core_tailoring_only_is_softer_flag():
    per_gene = [
        # zero core but a tailoring gene -> softer NO_CORE_TAILORING_ONLY, not collision
        _hit("BGC_A", "g3", "BGC_TAIL"),
    ]
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=_bgc_a_inventory())
    row = _row_for(result, "BGC_A", "BGC_TAIL")
    assert row["collision_flag"] == "NO_CORE_TAILORING_ONLY"
    assert result["summary"]["low_specificity_collision_count"] == 0


# ---------------------------------------------------------------------------
# within-BGC specificity: UNIQUE vs CO_DOMINANT vs CLEAR
# ---------------------------------------------------------------------------
def test_within_bgc_specificity_unique():
    per_gene = [_hit("BGC_U", "g1", "BGC_ONLY")]
    inv = {"BGC_U": {"g1": mcc.ROLE_CORE, "g2": mcc.ROLE_TAILORING}}
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=inv)
    row = _row_for(result, "BGC_U", "BGC_ONLY")
    assert row["within_bgc_specificity"] == "UNIQUE"
    assert row["is_bgc_dominant_comparator"] is True


def test_within_bgc_specificity_co_dominant():
    # two comparators tie at 2 matched genes each -> CO_DOMINANT
    per_gene = [
        _hit("BGC_C", "g1", "BGC_X"),
        _hit("BGC_C", "g2", "BGC_X"),
        _hit("BGC_C", "g3", "BGC_Y"),
        _hit("BGC_C", "g4", "BGC_Y"),
    ]
    inv = {
        "BGC_C": {
            "g1": mcc.ROLE_CORE,
            "g2": mcc.ROLE_CORE,
            "g3": mcc.ROLE_CORE,
            "g4": mcc.ROLE_CORE,
        }
    }
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=inv)
    x = _row_for(result, "BGC_C", "BGC_X")
    y = _row_for(result, "BGC_C", "BGC_Y")
    assert x["within_bgc_specificity"] == "CO_DOMINANT"
    assert y["within_bgc_specificity"] == "CO_DOMINANT"
    assert result["summary"]["co_dominant_bgc_count"] == 1


def test_within_bgc_specificity_clear_dominant():
    # top comparator leads runner-up by a wide margin -> CLEAR
    per_gene = [
        _hit("BGC_D", "g1", "BGC_TOP"),
        _hit("BGC_D", "g2", "BGC_TOP"),
        _hit("BGC_D", "g3", "BGC_TOP"),
        _hit("BGC_D", "g4", "BGC_TOP"),
        _hit("BGC_D", "g5", "BGC_SMALL"),
    ]
    inv = {"BGC_D": {f"g{i}": mcc.ROLE_CORE for i in range(1, 7)}}
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=inv)
    top = _row_for(result, "BGC_D", "BGC_TOP")
    assert top["within_bgc_specificity"] == "CLEAR"
    assert top["is_bgc_dominant_comparator"] is True


# ---------------------------------------------------------------------------
# cohort prevalence de-weighting (optional)
# ---------------------------------------------------------------------------
def test_cohort_prevalence_promiscuous_flag():
    per_gene = [_hit("BGC_A", "g1", "BGC_UBIQ")]
    prevalence = {"BGC_UBIQ": {"strains": 30, "total": 42, "fraction": 30 / 42}}
    result = mcc.compute_comparator_coverage(
        per_gene, locus_genes=_bgc_a_inventory(), cohort_prevalence=prevalence
    )
    row = _row_for(result, "BGC_A", "BGC_UBIQ")
    assert row["cohort_prevalence"] == "30/42"
    assert row["cohort_prevalence_flag"] == "PROMISCUOUS_DE_WEIGHT"


# ---------------------------------------------------------------------------
# fallback when no CDS role table is supplied
# ---------------------------------------------------------------------------
def test_fallback_without_cds_table_core_unavailable():
    per_gene = [
        _hit("BGC_A", "g1", "BGC_CORE"),
        _hit("BGC_A", "g2", "BGC_CORE"),
    ]
    convergence = [{"bgc_id": "BGC_A", "query_gene_count_total": 10}]
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=None, convergence_rows=convergence)
    row = _row_for(result, "BGC_A", "BGC_CORE")
    assert row["all_locus_genes"] == 10
    assert row["locus_denominator_basis"] == "kcb_query_gene_union_fallback"
    assert row["matched_core_genes"] == ""  # unavailable without roles
    assert row["collision_flag"] == "UNRESOLVED_NO_CDS_ROLES"


def test_report_only_contract_and_no_scoring_fields():
    per_gene = [_hit("BGC_A", "g1", "BGC_CORE")]
    result = mcc.compute_comparator_coverage(per_gene, locus_genes=_bgc_a_inventory())
    assert result["report_only_contract"] == mcc.REPORT_ONLY_CONTRACT
    # the layer must not emit any AB/AF/triage/novelty scoring field
    banned = {"ab_score", "af_score", "novelty", "triage_tier", "priority_score"}
    for row in result["rows"]:
        assert banned.isdisjoint(row.keys())
        assert "claim_safety" in row
