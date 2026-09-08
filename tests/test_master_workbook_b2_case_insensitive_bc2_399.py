"""BC2 .399 audit: mamey/master_workbook.py::_b2_product_class_counts() -- the persistent
cross-strain master workbook's product-class pivot -- compared each product against the
canonical B2 column set with exact, case-sensitive matching. The frozen B2 header names
several classes in uppercase ("NRPS", "T1PKS", "T2PKS", "T3PKS", "NRPS-like",
"NRP-metallophore", "NI-siderophore"), but the real antiSMASH tokens on bgc.products (this
function's actual real-world input, `mamey/master_workbook.py:422`,
`_b2_product_class_counts(c for bgc in run.bgcs for c in bgc.products)`) are lowercase --
confirmed against mamey/class_architecture.py::_REAL_CLASSES.

Reproduced directly against the real function with realistic lowercase input before fixing:
every NRPS/T1PKS/T2PKS class was silently folded into `other` in the persistent master
workbook, for every real strain. The existing MW-01 test
(tests/test_patch_l4_mpg_length_wb.py::test_mw01_noncanonical_products_folded_into_other) uses
artificial uppercase "NRPS" input, matching the bug's own wrong assumption, so it never
exercised the real-world case.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.master_workbook import _b2_product_class_counts, CANONICAL_V1_HEADERS  # noqa: E402


def test_realistic_lowercase_products_land_in_their_real_canonical_column():
    """The consequential proof: realistic lowercase antiSMASH tokens for classes the B2
    header itself names in uppercase must land in their real column, not 'other'."""
    products = ["nrps", "nrps", "t1pks", "t2pks", "terpene"]
    row = _b2_product_class_counts(products)
    assert row["NRPS"] == 2, row
    assert row["T1PKS"] == 1, row
    assert row["T2PKS"] == 1, row
    assert row["terpene"] == 1, row
    assert row["other"] == 0, f"real canonical classes silently folded into other: {row}"


def test_genuinely_noncanonical_products_still_fold_into_other():
    """No regression: a product genuinely outside the canonical set (any case) still folds
    into 'other', matching the original MW-01 fix's own intent."""
    # B2 v1.1 (.401 promotion ruling): arylpolyene/ectoine are now canonical columns;
    # only the genuinely unknown token folds.
    products = ["arylpolyene", "mystery-unknown-class", "ectoine"]
    row = _b2_product_class_counts(products)
    assert row["other"] == 1 and row["arylpolyene"] == 1 and row["ectoine"] == 1, row


def test_existing_uppercase_fixture_behavior_unchanged():
    """No regression: the module's own existing MW-01 test fixture (uppercase 'NRPS') must
    still behave identically."""
    products = ["NRPS", "NRPS", "terpene", "RiPP-like", "terpene-precursor",
                "ectoine", "arylpolyene"]
    row = _b2_product_class_counts(products)
    assert row["NRPS"] == 2
    assert row["terpene"] == 1
    # B2 v1.1 (.401): the four former folds are now their own canonical columns.
    assert row["other"] == 0 and row["RiPP-like"] == 1 and row["terpene-precursor"] == 1


def test_row_totals_still_equal_total_product_count_with_mixed_case():
    """No regression: the MW-01 sum invariant holds with a realistic mixed-case product list."""
    products = ["nrps", "PKS", "t1pks", "RiPP-like", "terpene-precursor",
                "ectoine", "arylpolyene", "hglE-KS", "NAPAA", "mystery-unknown-class"]
    row = _b2_product_class_counts(products)
    class_cols = [c for c in CANONICAL_V1_HEADERS["B2_Product_Class_Matrix"][1:]
                  if c not in ("label_provenance", "counts_reliability")]
    assert sum(row[c] for c in class_cols) == len(products)
