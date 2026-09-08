"""B1 (v9.7.256) — phantom-locus MEMBERSHIP gate.

PHANTOM_LOCUS (v9.7.246) catches a locus that exists in NO BGC of the strain. It stays silent
when a leaked ctgN_M happens to exist in a DIFFERENT BGC of the same strain — the AS-424 class,
where a templated sentence read '…settled BGC006 ctg12_71' but ctg12_71's home is BGC010. These
tests pin the two new ERROR lints that close that gap.
"""
from mamey.modeb_structure_gate import (
    _locus_bgc_mismatch_findings,
    _panel_absent_claim_findings,
    lint_card,
)

# AS-424 reconstruction: ctg12_71 is a real gene whose home is BGC010; the leak attributes it to BGC006.
AS424_HOME = {"ctg12_71": "BGC010", "ctg12_21": "BGC010", "ctg115_3": "BGC006"}


def _codes(findings):
    return [f["code"] for f in findings]


# ---------- LOCUS_BGC_MISMATCH ----------

def test_mismatch_fires_on_as424_leak():
    card = "The offline, deterministic channel that settled BGC006 ctg12_71 overturned the call."
    f = _locus_bgc_mismatch_findings(card, {"locus_home": AS424_HOME})
    assert "LOCUS_BGC_MISMATCH" in _codes(f), "ctg12_71 (home BGC010) attributed to BGC006 must ERROR"
    assert f[0]["severity"] == "ERROR"
    assert "BGC010" in f[0]["found"] and "BGC006" in f[0]["found"]


def test_mismatch_silent_when_locus_cited_with_its_home():
    card = "In BGC010, ctg12_71 encodes the beta-lactamase-like gene."
    f = _locus_bgc_mismatch_findings(card, {"locus_home": AS424_HOME})
    assert "LOCUS_BGC_MISMATCH" not in _codes(f), "cited with its true home BGC010 -> no flag"


def test_mismatch_silent_on_legitimate_contrast():
    card = "Unlike BGC010's ctg12_71, this BGC006 gene shows no overturn."
    f = _locus_bgc_mismatch_findings(card, {"locus_home": AS424_HOME})
    # home BGC010 is named AND the sentence is contrastive -> passes on both counts
    assert "LOCUS_BGC_MISMATCH" not in _codes(f)


def test_mismatch_silent_without_locus_home():
    card = "…settled BGC006 ctg12_71 overturned the call."
    assert _locus_bgc_mismatch_findings(card, {}) == []
    assert _locus_bgc_mismatch_findings(card, None) == []


def test_mismatch_member_of_correct_bgc_passes():
    # ctg115_3's home IS BGC006, cited under BGC006 -> fine
    card = "BGC006's ctg115_3 is the core synthase."
    assert "LOCUS_BGC_MISMATCH" not in _codes(_locus_bgc_mismatch_findings(card, {"locus_home": AS424_HOME}))


# ---------- PANEL_ABSENT_CLAIM ----------

def test_panel_absent_fires_when_result_claimed_for_unrun_bgc():
    card = "Per-gene BLASTp overturned two of ten on BGC006 (beta-lactamase to esterase)."
    f = _panel_absent_claim_findings(card, {"panels_present": {"BGC010", "BGC042"}})
    assert "PANEL_ABSENT_CLAIM" in _codes(f), "BLASTp result for BGC006 (no panel) must ERROR"
    assert f[0]["severity"] == "ERROR"


def test_panel_absent_silent_for_denial():
    card = "No BLASTp panel was run on BGC006, so no per-gene overturn is claimed."
    f = _panel_absent_claim_findings(card, {"panels_present": {"BGC010"}})
    assert "PANEL_ABSENT_CLAIM" not in _codes(f), "an explicit denial is correct, not a claim"


def test_panel_absent_silent_when_bgc_has_panel():
    card = "Per-gene BLASTp on BGC042 overturned one of ten."
    f = _panel_absent_claim_findings(card, {"panels_present": {"BGC042"}})
    assert "PANEL_ABSENT_CLAIM" not in _codes(f)


def test_panel_absent_silent_without_inventory():
    card = "Per-gene BLASTp overturned two of ten on BGC006."
    assert _panel_absent_claim_findings(card, {}) == []          # key absent -> silent
    assert _panel_absent_claim_findings(card, None) == []


# ---------- integration through lint_card ----------

def test_lint_card_surfaces_both_b1_codes():
    # lint_card requires real §-headings before per-finding checks run (a one-liner bails on
    # NO_HEADINGS). A structurally valid card carrying the AS-424 leak must surface both codes.
    card = (
        "## §1 Identity\nBGC006 on NODE_115.\n\n"
        "## §4 Per-gene evidence\n"
        "Per-gene BLASTp settled BGC006 ctg12_71, overturning two of ten on BGC006.\n"
    )
    ctx = {"locus_home": AS424_HOME, "panels_present": {"BGC010"}}
    codes = _codes(lint_card(card, bgc_context=ctx))
    assert "LOCUS_BGC_MISMATCH" in codes
    assert "PANEL_ABSENT_CLAIM" in codes


def test_bgc_norm_alignment_gene_table_vs_prose():
    # gene table stores 'BGC010'; prose writes 'BGC006' (both 3-digit). _norm_bgc must align them
    # so the compare is apples-to-apples: locus home bgc010 != attributed bgc006 -> mismatch.
    from mamey.modeb_structure_gate import _norm_bgc
    assert _norm_bgc("BGC010") == _norm_bgc("010") == "bgc010"
    card = "settled BGC006 ctg12_71."   # home BGC010 != attributed BGC006
    f = _locus_bgc_mismatch_findings(card, {"locus_home": {"ctg12_71": "BGC010"}})
    assert "LOCUS_BGC_MISMATCH" in _codes(f)
