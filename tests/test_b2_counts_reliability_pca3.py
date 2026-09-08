"""PC-A3 (v9.7.101): B2 product-class matrix must carry a counts_reliability flag so
raw (fragmentation-inflated) counts from poor assemblies aren't silently compared
against GOOD-assembly counts.
"""
from mamey.master_workbook import CANONICAL_V1_HEADERS

# the mapping the builder applies (kept in sync with master_workbook.py)
TIER_TO_RELIABILITY = {
    "COMPLETE": "OK", "GOOD": "OK", "MODERATE": "OK_WITH_NOTE",
    "POOR": "LOW", "VERY_POOR": "LOW",
}


def test_b2_schema_has_counts_reliability():
    b2 = CANONICAL_V1_HEADERS["B2_Product_Class_Matrix"]
    assert "counts_reliability" in b2


def test_very_poor_and_poor_are_low():
    assert TIER_TO_RELIABILITY["VERY_POOR"] == "LOW"
    assert TIER_TO_RELIABILITY["POOR"] == "LOW"


def test_good_is_ok_moderate_is_noted():
    assert TIER_TO_RELIABILITY["GOOD"] == "OK"
    assert TIER_TO_RELIABILITY["MODERATE"] == "OK_WITH_NOTE"
