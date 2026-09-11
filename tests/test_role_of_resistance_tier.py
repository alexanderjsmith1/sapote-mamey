"""P358-C05 — `_role_of()` must read the resistance TIER, not truth-test the string.

`resistance_tier` is a four-member enum (mamey/source_scans.py, mamey/cohort_figures.py)
whose NULL member is the string NULL_NO_SOURCE_DERIVED_RESISTANCE. That is deliberate: it
keeps "scanned and found nothing" distinct from "not scanned", which is the
missingness-is-not-absence discipline the project runs on.

Because it is a non-empty string it is TRUTHY, and the previous guard
    if res and res not in ("", "none") and "transporter_only" not in res
passed all three of its conditions for it — labelling a gene explicitly found to have NO
source-derived resistance as a `resistance` gene, indistinguishable downstream from a real
T1 self-protection gene. That inflates the single signal the AF lead ranking leans on
hardest, silently.

The NULL case is asserted explicitly so a future truthiness refactor cannot reintroduce it.
"""
import pytest

from mamey.bgc_guide import _role_of

T1 = "T1_DIAGNOSTIC_SELF_PROTECTION_SOURCE_DERIVED"
T2 = "T2_RESISTANCE_LIKE_SOURCE_DERIVED"
T3 = "T3_TRANSPORTER_ONLY_ROUTING"
NULL = "NULL_NO_SOURCE_DERIVED_RESISTANCE"


def _row(tier, fn="", dom=""):
    return {"resistance_tier": tier, "gene_function_inference": fn, "sec_met_domains": dom}


@pytest.mark.parametrize(
    "tier,expected",
    [
        (T1, "resistance"),      # real self-protection
        (T2, "resistance"),      # resistance-like
        (T3, "accessory"),       # transporter-only routing is NOT self-protection
        (NULL, "accessory"),     # <-- the regression this patch fixes
        ("", "accessory"),       # missing
        ("none", "accessory"),   # legacy literal
        (None, "accessory"),     # absent key / None
    ],
)
def test_role_of_maps_every_tier(tier, expected):
    assert _role_of(_row(tier)) == expected


def test_null_tier_is_never_resistance():
    """The explicit negative must never be promoted, in any casing."""
    for spelling in (NULL, NULL.lower(), NULL.title()):
        assert _role_of(_row(spelling)) != "resistance"


def test_core_still_wins_over_tier():
    """Core biosynthetic classification precedes the resistance branch."""
    assert _role_of(_row(T1, fn="core biosynthetic")) == "core"


def test_null_tier_does_not_mask_other_roles():
    """A NULL tier must fall through to the later branches, not short-circuit."""
    assert _role_of(_row(NULL, fn="transcriptional regulator")) == "regulation"
    assert _role_of(_row(NULL, fn="transposase")) == "mobile_element"
