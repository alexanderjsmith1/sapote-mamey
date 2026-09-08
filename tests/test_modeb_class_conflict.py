"""test_modeb_class_conflict.py — the PTM(tetramate)-vs-tetronate class-conflict adjudication (v9.7.354).

Encodes the PTM/tetramate-vs-tetronate lesson: when antiSMASH fires BOTH a PTM/tetramate and a tetronate CCTT trigger,
the card must adjudicate the two grammars (FkbH+ACP => tetronate review, necessary-not-sufficient; PTM needs
an ornithine-selective A-domain), not commit to one HSAF story. Advisory WARN, never blocks.
"""
from mamey.modeb_class_checklist import check_class_conflict

DUAL = "T43-PTM_hsaf_tetramate, T43-TET_tetronate_spirotetronate"


def test_dual_trigger_unadjudicated_warns():
    bad = "This is an HSAF polycyclic tetramate macrolactam; the assembly line builds the product."
    f = check_class_conflict(bad, DUAL)
    assert len(f) == 1
    assert f[0]["code"] == "CLASS_CONFLICT" and f[0]["severity"] == "WARN"


def test_dual_trigger_adjudicated_is_clean():
    good = ("Both PTM and tetronate triggers fire; FkbH+ACP points to a tetronate review "
            "(necessary-not-sufficient); a PTM call would need an ornithine-selective A-domain.")
    assert check_class_conflict(good, DUAL) == []


def test_single_trigger_never_warns():
    body = "HSAF polycyclic tetramate macrolactam."
    assert check_class_conflict(body, "T43-PTM_hsaf_tetramate") == []
    assert check_class_conflict(body, ["T43-TET_tetronate_spirotetronate"]) == []


def test_accepts_string_and_iterable_triggers():
    bad = "HSAF tetramate macrolactam product."
    assert len(check_class_conflict(bad, DUAL)) == 1
    assert len(check_class_conflict(bad, ["T43-PTM_hsaf_tetramate", "T43-TET_tetronate_spirotetronate"])) == 1
