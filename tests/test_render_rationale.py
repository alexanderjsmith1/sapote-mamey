"""render_rationale unit tests (#17) — the rationale renderer split out of scoring.py so it can be tested
independently of the scorer. Before this split the rationale was an inline f-string in the TriageRecord
construction and could not be exercised without running the full scoring path.
"""
from types import SimpleNamespace
from mamey.scoring import render_rationale


def _bgc(**kw):
    d = dict(edge_status="Interior", architecture_confidence="A", kcb_cumulative=100, riq_score=0.5,
             products=["NRPS"], architecture_capacity="", architecture_class_confidence="")
    d.update(kw)
    return SimpleNamespace(**d)


def test_base_rationale_has_no_flag_notes():
    r = render_rationale(_bgc())
    assert r.startswith("Interior; Arch A; KCB=100; RiQ=0.5; products=NRPS")
    for token in ("DIAG-FLOOR", "RIPP-FRAGMENT-FLOOR", "CCTT-UNCORROBORATED",
                  "PRIMARY-METAB", "STANDING-RULE", "MIS-ANCHOR"):
        assert token not in r


def test_arch_capacity_note():
    r = render_rationale(_bgc(architecture_capacity="small NRPS peptide", architecture_class_confidence="MODERATE"))
    assert "ARCH-CAPACITY: small NRPS peptide [MODERATE]" in r


def test_diag_floor_note():
    r = render_rationale(_bgc(), floored=True, floor_triggers=["T43-LAN"])
    assert "DIAG-FLOOR: T43-LAN floored to Medium" in r


def test_cctt_uncorroborated_note_only_for_fired_triggers():
    r = render_rationale(_bgc(), _uncorr={"T43-PHO_phosphonate"}, triggers={"T43-PHO_phosphonate"})
    assert "CCTT-UNCORROBORATED (T43-PHO_phosphonate)" in r
    # an uncorroborated trigger that did NOT fire on this BGC must not appear
    r2 = render_rationale(_bgc(), _uncorr={"T43-PHO_phosphonate"}, triggers={"T43-HAL_halogenase"})
    assert "CCTT-UNCORROBORATED" not in r2


def test_standing_rule_hglE_keeps_novelty_note():
    r = render_rationale(_bgc(), standing_rule="hglE-KS-PREV-001")
    assert "STANDING-RULE DOWNGRADE (hglE-KS-PREV-001)" in r
    assert "structural novelty unaffected" in r
    r2 = render_rationale(_bgc(), standing_rule="saccharide")
    assert "structural novelty unaffected" not in r2


def test_primary_metab_and_misanchor_notes():
    r = render_rationale(_bgc(), primary_flag=True, pm_families={"pigment"})
    assert "PRIMARY-METAB/PIGMENT FLAG (pigment)" in r
    r2 = render_rationale(_bgc(), misanchor_flag="enediyne_anchor_no_ene_KS")
    assert "MIS-ANCHOR (enediyne_anchor_no_ene_KS)" in r2
