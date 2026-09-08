"""L4 output-correctness patches (v9.7.338): MPG-01, LWC-01, MW-01.

These are OUTPUT fixes — they change values emitted into _3_mibig_profile.csv / the trial
length-weighted rows / the B2_Product_Class_Matrix master sheet. None flips a gate, but
downstream figures and Mode-B cards reading these columns will change.
"""
from collections import Counter

from mamey.mibig_per_gene import build_bgc_mibig_profile
from mamey.length_weighted import nominal_length_profile
from mamey.master_workbook import _b2_product_class_counts, CANONICAL_V1_HEADERS


def _hits(count, identity=40):
    return [
        {
            "query_gene": f"q{i}",
            "subject_gene": f"s{i}",
            "mibig_accession": "BGC0000001",
            "pct_identity": identity,
            "blast_score": 100 - i,
        }
        for i in range(count)
    ]


# ----------------------------------------------------------------------------- MPG-01
def test_mpg01_sparse_anchored_region_is_true_dark_matter_not_known_anchored():
    """A KCB-anchored region with only ~10% recognizable genes must NOT be stamped
    KNOWN_ANCHORED; it falls through to the fraction tiers -> TRUE_DARK_MATTER."""
    bgcs = {
        "SPARSE_ANCHORED": {"kcb_top": "BGC0000001.1 | some reference"},
        "DENSE_ANCHORED": {"kcb_top": "BGC0000001.1 | some reference"},
    }
    profiles = build_bgc_mibig_profile(
        {
            "SPARSE_ANCHORED": _hits(1),  # 1/10 recognizable -> frac 0.1
            "DENSE_ANCHORED": _hits(3),   # 3/10 recognizable -> frac 0.3
        },
        {"SPARSE_ANCHORED": 10, "DENSE_ANCHORED": 10},
        bgcs,
    )
    # The bug: `elif anchored` short-circuited both to KNOWN_ANCHORED.
    assert profiles["SPARSE_ANCHORED"]["recognizable_gene_fraction"] == 0.1
    assert profiles["SPARSE_ANCHORED"]["interpretation_class"] == "TRUE_DARK_MATTER"
    # A genuinely-recognizable anchored region (frac >= 0.20) still reads KNOWN_ANCHORED.
    assert profiles["DENSE_ANCHORED"]["interpretation_class"] == "KNOWN_ANCHORED"


def test_mpg01_dark_matter_tiers_are_reachable_for_anchored_regions():
    """The three dark-matter tiers must all be reachable regardless of a KCB anchor."""
    bgcs = {b: {"kcb_top": "BGC0000001.1 | ref"} for b in ("TRUE", "PARTIAL", "INTERP")}
    profiles = build_bgc_mibig_profile(
        {"TRUE": _hits(1), "PARTIAL": _hits(3), "INTERP": _hits(6)},
        {"TRUE": 10, "PARTIAL": 10, "INTERP": 10},
        bgcs,
    )
    # frac 0.3 (> 0.20) is dense enough to keep the anchor call.
    assert profiles["PARTIAL"]["interpretation_class"] == "KNOWN_ANCHORED"
    assert profiles["INTERP"]["interpretation_class"] == "KNOWN_ANCHORED"
    # Only the sub-0.20 region is dark.
    assert profiles["TRUE"]["interpretation_class"] == "TRUE_DARK_MATTER"


# ----------------------------------------------------------------------------- LWC-01
def test_lwc01_mapped_family_outranks_unmapped_default():
    """A mapped family (ectoine, 5 kb) must win over an UNMAPPED co-product carrying the
    15 kb default, so the nominal basis reflects a real family, not the fallback."""
    profile = nominal_length_profile(["ectoine", "other"])
    assert profile["nominal_bp"] == 5_000
    assert profile["nominal_basis_family"] == "ECTOINE"
    assert profile["nominal_basis_product"] == "ectoine"
    assert profile["mapping_status"] != "DEFAULT_UNMAPPED"


def test_lwc01_all_unmapped_still_reports_default():
    """When nothing maps, the default (15 kb, UNMAPPED) is still selected honestly."""
    profile = nominal_length_profile(["mystery-a", "mystery-b"])
    assert profile["nominal_bp"] == 15_000
    assert profile["mapping_status"] == "DEFAULT_UNMAPPED"


def test_lwc01_largest_mapped_family_still_wins_among_mapped():
    """Among mapped families the largest nominal length still wins (PKS 30 kb > ectoine)."""
    profile = nominal_length_profile(["ectoine", "PKS-like"])
    assert profile["nominal_bp"] == 30_000
    assert profile["nominal_basis_family"] == "PKS"


# ----------------------------------------------------------------------------- MW-01
def test_mw01_noncanonical_products_folded_into_other():
    """Products outside the frozen B2 header are folded into `other`, never dropped."""
    # B2 v1.1 (.401 promotion ruling): the four examples below became canonical columns, so
    # the fold cases now use tokens still outside the v1.1 canon (n<10 in the cohort remeasure).
    products = [
        "NRPS", "NRPS",            # canonical
        "terpene",                 # canonical
        "melanin",                 # non-canonical -> other
        "linaridin",               # non-canonical -> other
        "crocagin",                # non-canonical -> other
        "proteusin",               # non-canonical -> other
    ]
    row = _b2_product_class_counts(products)
    assert row["NRPS"] == 2
    assert row["terpene"] == 1
    assert row["other"] == 4  # the four non-canonical products, folded not dropped


def test_mw01_row_totals_equal_total_product_count():
    """Invariant: the product-class columns sum to the strain's total product count."""
    products = [
        "NRPS", "PKS", "T1PKS", "RiPP-like", "terpene-precursor",
        "ectoine", "arylpolyene", "hglE-KS", "NAPAA", "mystery-unknown-class",
    ]
    row = _b2_product_class_counts(products)
    class_cols = [c for c in CANONICAL_V1_HEADERS["B2_Product_Class_Matrix"][1:]
                  if c not in ("label_provenance", "counts_reliability")]
    assert sum(row[c] for c in class_cols) == len(products)
    assert row["counts_reliability"] == 0  # placeholder, set later by the builder
