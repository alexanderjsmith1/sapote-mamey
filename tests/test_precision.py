"""Tests for mamey.precision (W26 — no false-precise similarity numbers)."""
from mamey import precision as P


def test_similarity_bands():
    assert P.similarity_band(95) == "high"
    assert P.similarity_band(55) == "moderate"
    assert P.similarity_band(10) == "low"
    assert P.similarity_band(0) == "none"
    assert P.similarity_band(None) == "unresolved"


def test_identity_rounds_to_nearest_5():
    assert P.round_identity(97) == 95
    assert P.round_identity(93) == 95
    assert P.round_identity(91) == 90
    assert P.round_identity(None) is None


def test_bitscore_rounds_to_integer():
    assert P.round_bitscore(563.5) == 564
    assert P.round_bitscore(563.2) == 563
    assert P.round_bitscore(None) is None


def test_kcb_display_always_carries_disclaimer():
    out = P.kcb_display(80, raw_label="MIBiG BGC0000123")
    assert P.SIMILARITY_DISCLAIMER in out
    assert "high similarity" in out
    # a bare percentage must never appear
    assert "80%" not in out and "80 " not in out


def test_unresolved_still_disclaims():
    assert P.SIMILARITY_DISCLAIMER in P.kcb_display(None)
