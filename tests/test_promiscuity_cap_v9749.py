"""v9.7.49 — promiscuity cap on the co-cluster exemption.

A genuine cross-contig split tiles ONE characterized cluster (a few shared MIBiG references) and stays
exempt; a conserved cassette tiling many distinct MIBiG clusters (the aromatic-PKS over-call, ~28 refs)
must NOT be exempt. This is the shared-MIBiG-count cap, orthogonal to the hub-degree guard."""
from mamey.rggmci import _cocluster_exempt, RGGMCI_MAX_COCLUSTER_MIBIG_REFS

REASON = "DEMOTED_HIGH_TO_MODERATE_incompatible_product_classes"


def test_genuine_cocluster_two_refs_exempt():
    # the validated indolocarbazole split: 2 adjacent MIBiG refs -> exempt
    assert _cocluster_exempt(REASON, 2) is True


def test_at_cap_still_exempt():
    assert _cocluster_exempt(REASON, RGGMCI_MAX_COCLUSTER_MIBIG_REFS) is True


def test_promiscuous_cassette_not_exempt():
    # the aromatic-PKS over-call: ~28 shared MIBiG refs -> promiscuity, exemption withheld
    assert _cocluster_exempt(REASON, 28) is False
    assert _cocluster_exempt(REASON, RGGMCI_MAX_COCLUSTER_MIBIG_REFS + 1) is False


def test_below_floor_not_exempt():
    assert _cocluster_exempt(REASON, 1) is False
    assert _cocluster_exempt(REASON, 0) is False


def test_only_on_incompatible_product_reason():
    # exemption never fires on the saccharide/NAPAA convergence reason, regardless of ref count
    assert _cocluster_exempt("DEMOTED_no_specific_product_class_after_exclusions", 3) is False
    assert _cocluster_exempt("DEMOTED_distinct_ripp_subclasses", 3) is False
