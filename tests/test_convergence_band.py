"""Guards for the convergence strength band (display-only, post-seal).

The band exists so a reader cannot quote a weak per-gene MIBiG similarity as though it were
convergence. The tests that matter are the boundary cases and, above all, the distinction between
*missing* evidence and *weak* evidence — conflating those is the error the module exists to prevent.
"""
from __future__ import annotations

import pytest

from mamey.convergence_band import BAND_NOTE, annotate, band


@pytest.mark.parametrize(
    "pct,expected",
    [
        (100, "strong"), (80, "strong"), (80.0, "strong"),
        (79.9, "moderate"), (60, "moderate"),
        (59.9, "weak"), (40, "weak"),
        (39.9, "very weak"), (0, "very weak"),
    ],
)
def test_band_boundaries(pct, expected):
    assert band(pct) == expected


def test_missing_evidence_is_not_banded_as_weak():
    """A blank median means NOT MEASURED. Banding it 'very weak' would turn absence of evidence
    into evidence of weakness — the exact conflation this module guards against."""
    for empty in (None, "", "   ", "n/a", "NA"):
        assert band(empty) == "", f"{empty!r} must not be banded"
        assert annotate(empty) == "", f"{empty!r} must render as blank, not as a band"


def test_strings_from_csv_are_accepted():
    """Medians arrive from sealed-package CSVs as strings, sometimes with a trailing %."""
    assert band("72.5") == "moderate"
    assert band("72.5%") == "moderate"
    assert band(" 85 ") == "strong"


def test_annotate_renders_value_and_band_together():
    assert annotate(72.5) == "72.5% (moderate)"
    assert annotate(98) == "98% (strong)"
    assert annotate(52.0) == "52% (weak)"
    assert annotate(72.5, parens=False) == "72.5% moderate"


def test_thresholds_match_the_cohort_calibration():
    """The bands are calibrated on the measured cohort distribution: >=80 is the top 6.8% of hits,
    and <60 is 61% of them. If someone moves these, the docstring's numbers stop being true."""
    assert band(80) == "strong" and band(79.99) != "strong"
    assert band(60) == "moderate" and band(59.99) != "moderate"


def test_claim_ceiling_is_carried_with_the_module():
    """The band describes similarity strength, never product confidence. The note must say so."""
    lowered = BAND_NOTE.lower()
    assert "similarity" in lowered
    assert "not identity" in lowered or "not a product" in lowered
    assert "judgment deferred" in lowered


def test_band_never_raises_on_unexpected_input():
    for junk in ([], {}, object(), "abc", "%"):
        assert band(junk) == ""


# ---- shared vocabulary contract (cross-chat, v9.7.349) ----------------------------------------

def test_shared_thresholds_are_exported_for_other_modules():
    """CLAUDE_AUG3_02's reference-dark novelty imports its cutoff from here rather than hard-coding
    60, so the cut speaks one language. If these names move, that import breaks loudly — which is
    the point."""
    from mamey.convergence_band import (MODERATE_MIN, REFERENCE_DARK_BELOW, STRONG_MIN,
                                        is_reference_dark)
    assert STRONG_MIN == 80.0
    assert MODERATE_MIN == 60.0
    assert REFERENCE_DARK_BELOW == MODERATE_MIN, "reference-dark must equal the weak/moderate edge"
    assert is_reference_dark(59.9) is True
    assert is_reference_dark(60.0) is False


def test_reference_dark_distinguishes_unmeasured_from_divergent():
    """A gene with no hit is NOT reference-dark — it is unmeasured. Returning None forces the
    caller to say which it means; coverage gap must never be counted as novelty."""
    from mamey.convergence_band import is_reference_dark
    assert is_reference_dark(None) is None
    assert is_reference_dark("") is None
    assert is_reference_dark("n/a") is None


def test_bands_are_derived_from_the_shared_constants():
    """The band table must not drift from the exported constants."""
    from mamey.convergence_band import BANDS, MODERATE_MIN, STRONG_MIN
    lows = [lo for lo, _ in BANDS]
    assert STRONG_MIN in lows and MODERATE_MIN in lows
