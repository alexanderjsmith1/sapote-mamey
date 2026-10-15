"""P-LWC holds missing or invalid coordinates as not computed; it never creates a 1 bp length."""
from types import SimpleNamespace

import pytest

from mamey.length_weighted import length_weighted_profile, summary


def _bgc(start, end, edge="Interior", products=("NRPS",)):
    return SimpleNamespace(bgc_id="BGC001", contig="NODE_1", start=start, end=end,
                           products=list(products), edge_status=edge)


@pytest.mark.parametrize("start, end, status", [
    (None, None, "NOT_COMPUTED_MISSING_COORDINATES"),
    (None, 5000, "NOT_COMPUTED_MISSING_COORDINATES"),
    (100, None, "NOT_COMPUTED_MISSING_COORDINATES"),
    ("", "", "NOT_COMPUTED_MISSING_COORDINATES"),
    (5000, 100, "NOT_COMPUTED_INVALID_COORDINATES"),
    (-5, 100, "NOT_COMPUTED_INVALID_COORDINATES"),
    ("abc", 100, "NOT_COMPUTED_INVALID_COORDINATES"),
    (1.5, 100, "NOT_COMPUTED_INVALID_COORDINATES"),
    (float("nan"), 100, "NOT_COMPUTED_INVALID_COORDINATES"),
    (True, 100, "NOT_COMPUTED_INVALID_COORDINATES"),
])
def test_missing_or_invalid_coordinates_are_not_computed(start, end, status):
    row = length_weighted_profile([_bgc(start, end)])[0]
    assert row["length_bp"] is None and row["length_fraction"] is None
    assert row["coordinate_status"] == status


@pytest.mark.parametrize("start, end, length", [(0, 29_999, 30_000), (10, 10, 1), (1, 15_000, 15_000)])
def test_observed_coordinates_unchanged(start, end, length):
    row = length_weighted_profile([_bgc(start, end)])[0]
    assert row["length_bp"] == length
    assert row["length_fraction"] == round(min(1.0, length / 30_000), 6)
    assert row["coordinate_status"] == "OBSERVED"


def test_summary_keeps_held_rows_out_of_weighted_sums():
    rows = length_weighted_profile([_bgc(0, 14_999), _bgc(None, None), _bgc(9, 3, edge="Edge")])
    s = summary(rows)
    assert s["raw_regions"] == 3
    assert s["length_computed_regions"] == 1 and s["length_not_computed_regions"] == 2
    assert s["length_weighted_capacity_equivalents"] == 0.5
    assert s["interior_weighted"] == 0.5 and s["edge_weighted"] == 0.0
