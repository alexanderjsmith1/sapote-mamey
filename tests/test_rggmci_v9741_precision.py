"""v9.7.41 HIGH-precision patch regression.

Two gates, both load-bearing per a 5-strain internal PRIVATE calibration:
  1. _geometry_gate now requires >=2 good-geometry references for HIGH (gg=1 over-promotion was
     50-76% of HIGH pairs on every strain).
  2. _product_class_gate (P-2) demotes HIGH unless a specific shared product class or a known
     compatible hybrid survives exclusion of other/saccharide/NAPAA + the RiPP umbrella.

Fixtures use REAL product strings captured from a v9.7.40 run so the negative
(BGC014+BGC040: both-Interior, shared token = NAPAA only, reaches HIGH on gg=2) and the positives
(BGC017+BGC025, BGC027+BGC036) are exercised deterministically without a full pipeline run.
"""
import mamey.rggmci as rg


# ---- gg>=2 geometry gate ----

def test_high_with_single_good_geometry_demotes():
    conf, gate = rg._geometry_gate("HIGH_RG_GMCI_RESCUE", 1, split_signature=False)
    assert conf == "MODERATE_RG_GMCI_CANDIDATE"
    assert "fewer_than_2_good_geometry" in gate


def test_high_with_zero_good_geometry_demotes():
    # gg=0 + no split signal chains through both demotions (HIGH->MODERATE->LOW) -- preserved behaviour.
    conf, gate = rg._geometry_gate("HIGH_RG_GMCI_RESCUE", 0, split_signature=False)
    assert conf == "LOW_SHARED_REFERENCE_SIGNAL"


def test_high_with_zero_good_geometry_but_split_signal_stops_at_moderate():
    conf, gate = rg._geometry_gate("HIGH_RG_GMCI_RESCUE", 0, split_signature=True)
    assert conf == "MODERATE_RG_GMCI_CANDIDATE"


def test_high_with_two_good_geometry_survives_geometry_gate():
    conf, gate = rg._geometry_gate("HIGH_RG_GMCI_RESCUE", 2, split_signature=False)
    assert conf == "HIGH_RG_GMCI_RESCUE"
    assert gate == "OK"


# ---- P-2 product-class gate ----

def test_p2_negative_napaa_only_shared_demotes():
    # Negative: both-Interior pair (gg=2, survives geometry), shared token = NAPAA only.
    conf, gate = rg._product_class_gate(
        "HIGH_RG_GMCI_RESCUE",
        "aminopolycarboxylic-acid; other",
        "PKS; aminopolycarboxylic-acid; arylpolyene; other")
    assert conf == "MODERATE_RG_GMCI_CANDIDATE"
    assert "no_specific_product_class" in gate


def test_p2_positive_shared_specific_class_survives():
    # Positive: shared PKS/T1PKS.
    conf, gate = rg._product_class_gate("HIGH_RG_GMCI_RESCUE", "PKS; T1PKS", "PKS; T1PKS")
    assert conf == "HIGH_RG_GMCI_RESCUE"
    assert gate == "OK_shared_specific_product_class"


def test_p2_positive_shared_nrps_under_ripp_umbrella_survives():
    # Positive: shared NRPS once the RiPP umbrella is stripped.
    conf, gate = rg._product_class_gate(
        "HIGH_RG_GMCI_RESCUE", "NRPS; RiPP; ranthipeptide", "NRPS; RiPP; RiPP-like")
    assert conf == "HIGH_RG_GMCI_RESCUE"


def test_p2_compatible_hybrid_survives():
    conf, gate = rg._product_class_gate("HIGH_RG_GMCI_RESCUE", "NRPS", "T1PKS")
    assert conf == "HIGH_RG_GMCI_RESCUE"
    assert gate == "OK_compatible_hybrid"


def test_p2_distinct_ripp_subclasses_demote():
    conf, gate = rg._product_class_gate("HIGH_RG_GMCI_RESCUE", "lanthipeptide", "lassopeptide")
    assert conf == "MODERATE_RG_GMCI_CANDIDATE"
    assert "distinct_ripp_subclasses" in gate


def test_p2_unrelated_specific_classes_demote():
    conf, gate = rg._product_class_gate("HIGH_RG_GMCI_RESCUE", "terpene", "siderophore")
    assert conf == "MODERATE_RG_GMCI_CANDIDATE"
    assert "incompatible_product_classes" in gate


def test_p2_saccharide_only_shared_demotes():
    # saccharide is a permanent exclusion -> not a compatibility driver.
    conf, gate = rg._product_class_gate("HIGH_RG_GMCI_RESCUE", "saccharide; other", "saccharide")
    assert conf == "MODERATE_RG_GMCI_CANDIDATE"


def test_p2_never_promotes_non_high():
    # demote-only: a MODERATE input is returned unchanged regardless of products.
    conf, gate = rg._product_class_gate("MODERATE_RG_GMCI_CANDIDATE", "PKS", "PKS")
    assert conf == "MODERATE_RG_GMCI_CANDIDATE"
    assert gate == "OK"


# ---- constant ----

def test_adj_max_locus_gap_tightened_to_30():
    assert rg.ADJ_MAX_LOCUS_GAP == 30
    assert rg.ADJ_MAX_SPAN == 400
