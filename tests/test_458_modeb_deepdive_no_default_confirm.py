"""A Mode B deep dive never renders CONFIRM without a recorded verdict, and CONFIRM claims no expression.

A missing verdict defaulted to CONFIRM, and the CONFIRM text said the genes support "a genuine,
expressed ... pathway". Gene content cannot show expression; the claim ceiling is class level.
"""
from __future__ import annotations

import tools.build_modeb_deepdive as bmd

SID, BID = "AS-XXX", "BGC001"
BREC = {(SID, BID): {"contig": "c1", "products": "NRPS", "closest_kcb_product": "fixture",
                     "closest_mibig": "BGC0000001", "region": "1.1", "length_kb": 40, "edge_status": "Interior"}}
PROF = {(SID, BID): {"PKS_KS": 0, "NRPS_C": 3, "total_domains": 12, "resistance_tier": "NU"}}


def _render(verdict):
    return bmd.deepdive(SID, BID, BREC, PROF, [], [], {}, {}, [], None, verdict)


def test_missing_verdict_is_not_confirm():
    text = _render(None)
    assert "CONFIRM" not in text
    assert "Verdict — none recorded" in text


def test_unknown_status_is_not_rendered_as_confirm():
    text = _render({"status": "CONFRIM", "note": "", "modeb_class": ""})
    assert "Verdict — CONFIRM" not in text and "none recorded" in text


def test_confirm_text_makes_no_expression_claim():
    text = _render({"status": "CONFIRM", "note": "", "modeb_class": "NRPS"})
    assert "Verdict — CONFIRM (class-level)" in text
    assert "expressed" not in text and "genuine" not in text
    assert "is consistent with a NRPS-class biosynthetic locus" in text
