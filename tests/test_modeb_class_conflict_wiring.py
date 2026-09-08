"""test_modeb_class_conflict_wiring.py — check_class_conflict wired into lint_card (v9.7.354).

Confirms the PTM-vs-tetronate adjudication actually fires through the structure gate's authored-verify
path (reusing the existing check_class_content flag), not just as a standalone library function.
"""
from mamey.modeb_structure_gate import lint_card

_DUAL_CARD = (
    "## §2\nCCTT triggers: T43-PTM_hsaf_tetramate, T43-TET_tetronate_spirotetronate\n"
    "This is an HSAF polycyclic tetramate macrolactam; the assembly line builds the product.\n"
)
_CTX = {"products": "NRPS; PKS; transAT-PKS"}


def test_lint_card_fires_class_conflict_on_dual_trigger():
    codes = [f.get("code") for f in lint_card(_DUAL_CARD, bgc_context=_CTX, check_class_content=True)]
    assert "CLASS_CONFLICT" in codes


def test_lint_card_clean_when_adjudicated():
    card = _DUAL_CARD.replace(
        "the assembly line builds the product.",
        "FkbH+ACP points to a tetronate review; PTM needs an ornithine-selective A-domain.",
    )
    codes = [f.get("code") for f in lint_card(card, bgc_context=_CTX, check_class_content=True)]
    assert "CLASS_CONFLICT" not in codes


def test_no_conflict_check_when_flag_off():
    # check_class_content=False (default) must not run the conflict check
    codes = [f.get("code") for f in lint_card(_DUAL_CARD, bgc_context=_CTX)]
    assert "CLASS_CONFLICT" not in codes


def test_single_trigger_card_is_clean():
    single = _DUAL_CARD.replace(", T43-TET_tetronate_spirotetronate", "")
    codes = [f.get("code") for f in lint_card(single, bgc_context=_CTX, check_class_content=True)]
    assert "CLASS_CONFLICT" not in codes
