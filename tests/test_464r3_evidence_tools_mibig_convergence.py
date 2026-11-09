"""Missing KnownClusterBlast coverage stays missing, and the convergence wording stays bounded."""
from mamey.mibig_per_gene import build_mibig_convergence


def _rows(coverage):
    return [{"bgc_id": "BGC001", "query_gene": f"q{i}", "subject_gene": f"s{i}",
             "mibig_accession": "BGC0000123", "mibig_compound": "reference family",
             "reference_type": "PKS", "reference_rank": 1, "pct_identity": 75,
             "pct_coverage": coverage, "pct_coverage_interpretation": None,
             "coverage_qc_flag": "MISSING_OR_NONNUMERIC", "blast_score": 500} for i in range(12)]


def test_missing_coverage_is_not_zero_and_not_in_range():
    row = build_mibig_convergence({"BGC001": _rows(None)}, {"BGC001": 12},
                                  {"BGC001": {"products": ["T1PKS"]}})[0]
    assert row["median_pct_coverage"] is None
    assert row["median_pct_coverage_interpretation"] is None
    assert row["coverage_qc_flag"] == "MISSING_OR_NONNUMERIC_COVERAGE"
    assert row["coverage_missing_row_count"] == 12
    # Twelve genes at 75% identity would reach H1 with coverage; without it the tier is held.
    assert row["convergence_tier"] == "HOLD_COVERAGE_UNMEASURED"


def test_measured_coverage_keeps_its_tier():
    row = build_mibig_convergence({"BGC001": _rows(95)}, {"BGC001": 12},
                                  {"BGC001": {"products": ["T1PKS"]}})[0]
    assert row["convergence_tier"] == "H1_HIGH_DENSITY"
    assert row["coverage_qc_flag"] == "WITHIN_EXPECTED_RANGE"
    assert row["coverage_missing_row_count"] == 0


def test_claim_safety_is_bounded_similarity_not_direct_pathway_evidence():
    row = build_mibig_convergence({"BGC001": _rows(95)}, {"BGC001": 12}, {})[0]
    text = row["claim_safety"]
    assert "direct sequence evidence" not in text
    assert "hypothesis" in text and "locus-specific review" in text
