"""v9.7.257: CLAIM_SAFETY must not false-positive on a multi-line denial list.

The AS-424 BGC019 §14 case: a denial introducer ends one line with a colon, the forbidden verb
sits on a following list item. Line-scoped checking flagged the item as a product-identity claim,
training authors to delete a correct denial. The fix looks back up to two lines for a denial-list
introducer — but only when the current line is a list item, so an unrelated earlier negation can't
mask a real, unhedged claim.
"""
from mamey.modeb_structure_gate import _claim_safety_findings


def _kinds(card):
    return [f["code"] for f in _claim_safety_findings(card)]


def test_multiline_denial_list_does_not_fire():
    card = (
        "§14 Novelty\n"
        "The evidence does not support:\n"
        "(1) that BGC019 produces frankiamicin\n"
        "(2) any confirmed enediyne here\n"
    )
    assert "CLAIM_SAFETY" not in _kinds(card)


def test_single_line_denial_still_clean():
    # existing behavior via _CLAIM_SAFE_CONTEXT_RE ("does not")
    card = "The card does not claim BGC019 produces frankiamicin.\n"
    assert "CLAIM_SAFETY" not in _kinds(card)


def test_real_unhedged_claim_still_fires():
    card = "§8 Assessment\nBGC019 produces frankiamicin.\n"
    assert "CLAIM_SAFETY" in _kinds(card)


def test_list_item_claim_without_denial_intro_still_fires():
    # a numbered item, but the line above is NOT a denial-list introducer → must still fire
    card = (
        "§8 Findings\n"
        "The cluster architecture is complete:\n"
        "(1) BGC019 produces frankiamicin\n"
    )
    assert "CLAIM_SAFETY" in _kinds(card)


def test_unrelated_earlier_negation_does_not_mask_claim():
    # a denial two lines up that does NOT end in a colon must not suppress a later real claim
    card = (
        "This is not a housekeeping gene.\n"
        "The scaffold is intact.\n"
        "BGC019 produces frankiamicin.\n"   # not a list item, no governing denial → fires
    )
    assert "CLAIM_SAFETY" in _kinds(card)
