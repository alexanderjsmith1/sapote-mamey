"""RG-GMCI v2 adjacency guard — complementary-but-distant loci must NOT be SUPPORTED."""
from mamey.diagnostic_rescue import tile_pair, _adjacent


def _cb(acc, subjects, cum=500.0, source="ref"):
    return {acc: {"hits": [{"subject": s} for s in subjects], "cum_score": cum, "source": source}}


def test_adjacent_complementary_is_supported():
    # two fragments hitting NEAR-BY, non-overlapping loci of one reference cluster (e.g. AT2433 split)
    a = _cb("AT2433", ["ABC02789", "ABC02790", "ABC02791", "ABC02795"])
    b = _cb("AT2433", ["ABC02798", "ABC02801", "ABC02805"])
    r = tile_pair(a, b)
    assert r["verdict"] == "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY", r


def test_distant_complementary_is_rejected():
    # complementary (0 overlap) but DISTANT loci on a shared genome = two clusters, not a split
    a = _cb("GENOME", ["X_RS10010", "X_RS10015", "X_RS10020"])
    b = _cb("GENOME", ["X_RS88000", "X_RS88005", "X_RS88010"])
    r = tile_pair(a, b)
    assert r["verdict"] == "RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI", r
    assert r["overlap_fraction"] == 0.0  # was previously SUPPORTED on overlap alone


def test_high_overlap_unchanged():
    a = _cb("R", ["G1", "G2", "G3"])
    b = _cb("R", ["G1", "G2", "G4"])
    assert tile_pair(a, b)["verdict"] == "RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP"


def test_no_shared_reference():
    assert tile_pair(_cb("R1", ["A", "B"]), _cb("R2", ["C", "D"]))["verdict"] == "NO_SHARED_REFERENCE"


def test_adjacency_helper():
    adj, gap, span = _adjacent({"X_RS100", "X_RS105"}, {"X_RS110", "X_RS115"})
    assert adj and gap == 5
    far, gap2, _ = _adjacent({"X_RS100"}, {"X_RS9000"})
    assert not far and gap2 == 8900
