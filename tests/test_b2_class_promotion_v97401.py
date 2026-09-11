"""B2 schema v1.1 (.401): the 14 cohort-attested classes promoted from 'other' (Alex ruling
2026-09-02, n>=10 full-cohort threshold; decision memo beside COHORT_MASTER_v97400). Locks:
promoted tokens land in their own columns (case-insensitively), rare tokens still fold to
'other', the MW-01 sum invariant holds, and the widened canon stays lowercase-collision-free."""
from __future__ import annotations

from mamey.master_workbook import CANONICAL_V1_HEADERS, _b2_product_class_counts

PROMOTED = ["RiPP-like", "terpene-precursor", "quinone_isoprenoid_chain", "ectoine",
            "butyrolactone", "arylpolyene", "RRE-containing", "redox-cofactor",
            "ranthipeptide", "oligosaccharide", "hydrogen-cyanide",
            "aminopolycarboxylic-acid", "HR-T2PKS", "phosphonate"]


def _cols():
    return CANONICAL_V1_HEADERS["B2_Product_Class_Matrix"][1:]


def test_promoted_classes_are_canonical_columns():
    cols = _cols()
    for t in PROMOTED:
        assert t in cols, f"promoted class {t!r} missing from B2 v1.1 canon"
    assert cols[-2:] == ["other", "counts_reliability"], "tail columns must stay in place"


def test_promoted_tokens_no_longer_fold_into_other():
    row = _b2_product_class_counts(["RiPP-like", "ectoine", "butyrolactone", "ripp-like"])
    assert row["RiPP-like"] == 2, "case-insensitive landing in the promoted column"
    assert row["ectoine"] == 1 and row["butyrolactone"] == 1
    assert row["other"] == 0, f"promoted classes folded into other: {row}"


def test_rare_tokens_still_fold_and_sum_invariant_holds():
    products = ["melanin", "proteusin", "NRPS", "phosphonate"]
    row = _b2_product_class_counts(products)
    assert row["other"] == 2 and row["NRPS"] == 1 and row["phosphonate"] == 1
    class_cols = [c for c in _cols() if c not in ("label_provenance", "counts_reliability")]
    assert sum(row[c] for c in class_cols) == len(products)


def test_widened_canon_is_lowercase_collision_free():
    canon = set(_cols()) - {"other", "label_provenance", "counts_reliability"}
    assert len(canon) == len({c.lower() for c in canon}) == 38, (
        "v1.1 canon must be 38 distinct classes with no case-fold collision")
