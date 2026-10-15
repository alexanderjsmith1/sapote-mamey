"""P300-064: reference adjacency keeps the locus namespace, and unknown adjacency never supports a split.

Synthetic subject locus tags only.
"""
from mamey import diagnostic_rescue as DR


def _cb(acc, subjects, cum=500.0):
    return {acc: {"hits": [{"subject": s} for s in subjects], "cum_score": cum, "source": "ref"}}


# --- namespace is preserved --------------------------------------------------------------------------
def test_locus_key_keeps_namespace_and_strips_version():
    assert DR._locus_ns_num("AMK09_RS30055") == ("AMK09_RS", 30055)
    assert DR._locus_ns_num("QJU69504.1") == ("QJU", 69504)
    assert DR._locus_ns_num("nodigits") == (None, None)


def test_distinct_namespaces_with_near_numbers_are_unknown_not_adjacent():
    adj, gap, span = DR._adjacent({"AAA_RS100", "AAA_RS105"}, {"BBB_RS110", "BBB_RS115"})
    assert adj is None and gap is None and span is None


def test_missing_numbers_on_one_or_both_sides_are_unknown():
    assert DR._adjacent({"geneA", "geneB"}, {"X_RS10"}) == (None, None, None)
    assert DR._adjacent({"geneA"}, {"geneB"}) == (None, None, None)


def test_version_suffix_does_not_split_namespace():
    adj, gap, _ = DR._adjacent({"QJU69504.1"}, {"QJU69510.1"})
    assert adj is True and gap == 6


def test_exact_gap_and_span_boundaries_unchanged():
    # gap 60 and span 400 are inclusive limits (thresholds unchanged)
    adj, gap, span = DR._adjacent({"X_RS1000", "X_RS1340"}, {"X_RS1400"})
    assert (adj, gap, span) == (True, 60, 400)
    adj, gap, _ = DR._adjacent({"X_RS1000"}, {"X_RS1061"})
    assert adj is False and gap == 61
    adj, _, span = DR._adjacent({"X_RS1000", "X_RS1350"}, {"X_RS1401"})
    assert adj is False and span == 401


def test_only_the_shared_namespace_is_measured():
    # Y_RS9000 has no partner namespace on the other side; it cannot widen the span
    adj, gap, span = DR._adjacent({"X_RS100", "Y_RS9000"}, {"X_RS110"})
    assert (adj, gap, span) == (True, 10, 10)


# --- tile_pair verdicts --------------------------------------------------------------------------------
def test_unknown_adjacency_low_overlap_is_not_supported():
    r = DR.tile_pair(_cb("REF", ["AAA_RS100", "AAA_RS105"]), _cb("REF", ["BBB_RS110", "BBB_RS115"]))
    assert r["verdict"] == "RECONSTRUCTION_ADJACENCY_UNKNOWN"
    assert not r["verdict"].startswith("RECONSTRUCTION_SUPPORTED")
    assert r["adjacency_gap"] is None and r["adjacency_span"] is None


def test_unnumbered_subjects_are_not_supported():
    r = DR.tile_pair(_cb("REF", ["geneA", "geneB"]), _cb("REF", ["geneC", "geneD"]))
    assert r["verdict"] == "RECONSTRUCTION_ADJACENCY_UNKNOWN"


def test_same_namespace_adjacent_pair_still_supported():
    r = DR.tile_pair(_cb("REF", ["X_RS100", "X_RS105"]), _cb("REF", ["X_RS110", "X_RS115"]))
    assert r["verdict"] == "RECONSTRUCTION_SUPPORTED_COMPLEMENTARY"
    assert r["adjacency_gap"] == 5 and r["adjacency_span"] == 15


def test_same_namespace_distant_pair_still_distant():
    r = DR.tile_pair(_cb("REF", ["X_RS100"]), _cb("REF", ["X_RS9000"]))
    assert r["verdict"] == "RECONSTRUCTION_NOT_SUPPORTED_DISTANT_LOCI"


def test_high_overlap_verdict_unchanged_without_numbers():
    r = DR.tile_pair(_cb("REF", ["G1", "G2", "G3"]), _cb("REF", ["G1", "G2", "G4"]))
    assert r["verdict"] == "RECONSTRUCTION_NOT_SUPPORTED_HIGH_REFERENCE_OVERLAP"


# --- an unknown-adjacency tiling cannot drive a HIGH rescue --------------------------------------------
def test_unknown_adjacency_tiling_cannot_be_high():
    pair = {"pair": "BGC001+BGC013", "bgc_a": "BGC001", "bgc_b": "BGC013",
            "contig_a": "NODE_105", "contig_b": "NODE_182",
            "products_a": "halogenated", "products_b": "indole", "edge_a": "Edge", "edge_b": "Edge"}
    cb_a = _cb("REF", ["AAA_RS1", "AAA_RS2"])
    cb_b = _cb("REF", ["BBB_RS%d" % i for i in range(1, 7)])
    tiling = DR.tile_pair(cb_a, cb_b)
    assert tiling["covered"] == 8 and tiling["overlap"] == 0
    fmap = {"by_accession": {"BGC0000809": "indolocarbazole"}, "compatible_pairs": []}
    lead = DR.assess_pair(pair, ["T43-HAL_halogenase"], ["T43-IDC_indolocarbazole"], deep_tiling=tiling,
                          kcb_a="BGC0000809.3", kcb_b="BGC0000809.3", family_map=fmap)
    assert lead["tiling_verdict"] == "RECONSTRUCTION_ADJACENCY_UNKNOWN"
    assert lead["rescue_tier"] == "DIAGNOSTIC_RESCUE_MODERATE"
