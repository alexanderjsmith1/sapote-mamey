"""Tests for kcb_frontpage — the corroboration tiering that distinguishes a real
cluster hit from a couple of coincidentally-matching proteins."""
from mamey.kcb_frontpage import _corroboration_tier


def test_high_similarity_few_genes_is_coincidental():
    # the geosmin/rhizomide case: 100% similarity but 1-2 genes = single-protein fluke
    assert _corroboration_tier(100, 1) == "COINCIDENTAL"
    assert _corroboration_tier(100, 2) == "COINCIDENTAL"


def test_moderate_similarity_many_genes_is_strong():
    # the mycotrienin case: 50% similarity, 26 genes = real cluster relationship
    assert _corroboration_tier(50, 26) == "STRONG"
    # selvamicin: 100%, 29 genes
    assert _corroboration_tier(100, 29) == "STRONG"


def test_large_generic_overlap_demoted():
    # a big region shares a few generic genes with many MIBiG clusters at tiny similarity
    assert _corroboration_tier(5, 60) == "LARGE_GENERIC"


def test_low_when_neither_signal():
    assert _corroboration_tier(10, 3) == "LOW"


def test_tier_ordering_makes_sense():
    # STRONG requires BOTH axes; a hit strong on only one axis must not be STRONG
    assert _corroboration_tier(90, 3) != "STRONG"   # high sim, few genes
    assert _corroboration_tier(20, 40) != "STRONG"  # many genes, low sim
