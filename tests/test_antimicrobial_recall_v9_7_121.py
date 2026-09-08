"""Tests for the antimicrobial recall layer (v9.7.120).

Validates the boost-only, no-penalty, concordance-gated compound-anchor AB/AF
capacity scoring against the 12-genome ground-truth reference panel.
"""
import pytest
from mamey import antimicrobial_recall as ar


# (name, accession, resolved_product, ab_keyword, af_keyword)
ANTIBACTERIAL = [
    ("ristomycin",   "BGC0000419", "ristomycin A",   45, 28),
    ("caboxamycin",  "BGC0001444", "caboxamycin",    45, 32),
    ("lobophorin",   "BGC0002550", "lobophorin CR4", 43, 30),
    ("K41A",         "BGC0002526", "K-41A",          43, 30),
]
ANTIFUNGAL = [
    ("nystatin",     "BGC0000115", "nystatin A1",            43, 72),
    ("tetramycin",   "BGC0002540", "tetramycin B",           55, 38),
    ("venturicidin", "BGC0002454", "venturicidin A",         55, 38),
    ("bafilomycin",  "BGC0000028", "bafilomycin B1",         43, 30),
    ("HSAF",         "BGC0000999", "heat-stable antifungal", 51, 65),
]
NON_ANTIMICROBIAL = [
    ("meridamycin",  "BGC0001011", "meridamycin",    47, 38),
    ("trioxacarcin", "BGC0002141", "trioxacarcin A", 45, 20),
    ("didemnin",     "BGC0000985", "didemnin B",     37, 28),
]


@pytest.mark.parametrize("name,acc,prod,abk,afk", ANTIBACTERIAL)
def test_antibacterial_anchor_boosts_ab(name, acc, prod, abk, afk):
    r = ar.recall_scores(abk, afk, closest_mibig_accession=acc, closest_kcb_product=prod)
    assert r["ab_recall"] >= 70, f"{name}: AB should reach High, got {r['ab_recall']}"
    assert r["ab_recall"] >= abk, "boost-only: recall AB never below keyword"
    assert r["recall_applied"] is True


@pytest.mark.parametrize("name,acc,prod,abk,afk", ANTIFUNGAL)
def test_antifungal_anchor_boosts_af(name, acc, prod, abk, afk):
    r = ar.recall_scores(abk, afk, closest_mibig_accession=acc, closest_kcb_product=prod)
    assert r["af_recall"] >= 70, f"{name}: AF should reach High, got {r['af_recall']}"
    assert r["af_recall"] >= afk, "boost-only: recall AF never below keyword"
    assert r["recall_applied"] is True


@pytest.mark.parametrize("name,acc,prod,abk,afk", NON_ANTIMICROBIAL)
def test_non_antimicrobial_left_at_baseline(name, acc, prod, abk, afk):
    """No penalty AND no boost: a non-antimicrobial known stays exactly at keyword baseline."""
    r = ar.recall_scores(abk, afk, closest_mibig_accession=acc, closest_kcb_product=prod)
    assert r["ab_recall"] == abk, f"{name}: AB must be unchanged, got {r['ab_recall']}"
    assert r["af_recall"] == afk, f"{name}: AF must be unchanged, got {r['af_recall']}"
    assert r["recall_applied"] is False


def test_boost_only_never_lowers():
    """Even a low-capacity family must never pull a high keyword score down."""
    r = ar.recall_scores(95, 90, closest_mibig_accession="BGC0000419", closest_kcb_product="ristomycin A")
    assert r["ab_recall"] >= 95 and r["af_recall"] >= 90


def test_no_anchor_is_passthrough():
    r = ar.recall_scores(50, 40, closest_mibig_accession="UNRESOLVED", closest_kcb_product="")
    assert r["ab_recall"] == 50 and r["af_recall"] == 40
    assert r["recall_applied"] is False


def test_suppressing_misanchor_gates_out():
    """A genuine suppressing mis-anchor blocks the boost; falls back to keyword baseline."""
    r = ar.recall_scores(45, 32, closest_mibig_accession="BGC0000115",
                         closest_kcb_product="nystatin A1",
                         misanchor_flag="polyene_anchor_<4_PKS_KS(ks=2)")
    assert r["recall_applied"] is False
    assert r["af_recall"] == 32


def test_informational_anchor_note_does_not_gate():
    """The engine records '[polyene=nystatin]' as an informational tag — must NOT be read
    as a suppressing mis-anchor."""
    r = ar.recall_scores(43, 72, closest_mibig_accession="BGC0000115",
                         closest_kcb_product="nystatin A1",
                         misanchor_flag="[polyene=nystatin]")
    assert r["recall_applied"] is True
    assert r["af_recall"] >= 70


def test_discordant_concordance_gates_out():
    r = ar.recall_scores(45, 28, closest_mibig_accession="BGC0000419",
                         closest_kcb_product="ristomycin A",
                         concordance_verdict="DISCORDANT")
    assert r["recall_applied"] is False
    assert r["ab_recall"] == 45


def test_spore_pigment_name_gates_out():
    """A T2-aromatic accession whose product is a spore pigment must not be boosted."""
    # use a real aromatic_polyketide_t2 accession from the base family map
    r = ar.recall_scores(45, 28, closest_mibig_accession="BGC0000194",
                         closest_kcb_product="spore pigment")
    assert r["recall_applied"] is False


def test_raw_kcb_top_is_not_read():
    """The layer must read closest_mibig_accession, never raw kcb_top (P-7 guard)."""
    # passing only a product string with no resolved accession -> no boost
    r = ar.recall_scores(45, 28, closest_mibig_accession="", closest_kcb_product="ristomycin A")
    assert r["recall_applied"] is False
