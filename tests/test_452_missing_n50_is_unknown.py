"""A missing N50 leaves contiguity unassessed; it is not read as a highly fragmented assembly."""
from mamey.assembly import fragmentation_tier


def test_missing_or_nonpositive_n50_is_unknown():
    for n50 in (None, 0, -5, True):
        assert fragmentation_tier(50, n50) == "UNKNOWN"


def test_measured_bands_are_unchanged():
    assert fragmentation_tier(1, 5_000_000) == "CLOSED"
    assert fragmentation_tier(15, 600_000) == "CONTIGUOUS"
    assert fragmentation_tier(80, 150_000) == "DRAFT"
    assert fragmentation_tier(500, 50_000) == "FRAGMENTED"
    assert fragmentation_tier(5_000, 2_000) == "HIGHLY_FRAGMENTED"
    assert fragmentation_tier(None, 50_000) == "UNKNOWN"
