"""Fabricated Mode B language fixtures, independent of empirical strain findings.

All subject names, assay descriptions and quantities in these examples are invented.
The intentionally over-promoted card must HOLD; the cautious card remains admissible.
"""
import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "modeb_evidence_gate.py"
_spec = importlib.util.spec_from_file_location("modeb_evidence_gate", TOOL)
meg = importlib.util.module_from_spec(_spec)
sys.modules["modeb_evidence_gate"] = meg  # required so @dataclass can resolve cls.__module__
_spec.loader.exec_module(meg)
assess = meg.assess_modeb_card


def _kinds(rep):
    return {v.kind for v in rep.violations}


# A fabricated negative control reproducing the same linguistic failure classes.
BAD_CARD = """
Fabricated negative-control card. Every assay description and quantity below is invented.
BGC010 — PROMOTED, authoritative, good confidence. Strongest antifungal lead in the cohort.
FkbH glyceryl starter + ornithine aminotransferase + trans-AT modules + release thioesterase = the HSAF grammar.
This is a clifednamide congener. Novelty read: real at the congener level (AS-private two-member BiG-SCAPE
family, 84.2% identity in one megasynthase, 2/41 KCB coverage; recognizable-gene share 0.625).
Most consistent with SYNTHETIC-MODEB-A's invented anti-Candida activity; SYNTHETIC-MODEB-A is most-active-in-vivo (crude-extract
whole-cell assay). A nearby ABC transporter provides dedicated export/self-protection. Edge; near-complete
full backbone. No fresh per-gene BLASTP panel exists.
"""

# A fabricated cautious verdict using the same generic evidence-governance grammar.
GOOD_CARD = """
BGC010 — HOLD. High-priority complex PKS-NRPS hypothesis.
OBSERVATION: the locus contains a trans-AT PKS/NRPS system and a separate FkbH/ACP-associated signal.
INFERENCE: available KCB and cohort evidence justify comparison with PTM and tetronate-bearing systems.
ALTERNATIVE: competing tetronate, hybrid-polyketide and tetramate-related hypotheses remain open;
they do not yet establish an HSAF/clifednamide pathway.
FALSIFIER: an A-domain not selective for ornithine, or a tetronate-consistent architecture, would overturn a PTM read.
Divergent within the surveyed cohort; chemical novelty unresolved. Judgment deferred.
"""


def test_bad_card_is_held():
    rep = assess(BAD_CARD)
    assert rep.status == "HOLD"
    k = _kinds(rep)
    assert "ADMISSION_GATE" in k            # promoted with no fresh per-gene BLASTP
    assert "MOTIF_GRAMMAR_CONFLICT" in k    # tetramate/HSAF identity fused with FkbH/tetronate
    assert "NOVELTY_FROM_WEAK_EVIDENCE" in k
    assert "ACTIVITY_INHERITANCE" in k
    assert "ASSAY_CONFLATION" in k
    assert "EDGE_VS_COMPLETENESS" in k
    assert "ARITHMETIC_MISMATCH" in k       # 2/41 = 0.049, not 0.625
    assert "STRUCTURE_MISSING" in k         # no OBS/INF/ALT/FALS


def test_good_hold_card_is_admissible():
    rep = assess(GOOD_CARD)
    assert rep.status == "ADMISSIBLE", f"unexpected violations: {_kinds(rep)}"


def test_promotion_without_fresh_blastp_blocks():
    rep = assess("BGC010 is the strongest antifungal lead. OBSERVATION x. INFERENCE y. "
                 "ALTERNATIVE z. FALSIFIER w.", has_fresh_blastp=False)
    assert rep.status == "HOLD"
    assert "ADMISSION_GATE" in _kinds(rep)


def test_promotion_with_fresh_blastp_and_structure_passes_admission():
    rep = assess("BGC010 authoritative call. per-gene BLASTP panel is present and current (U=0). "
                 "OBSERVATION: modules. INFERENCE: family. ALTERNATIVE: none material. "
                 "FALSIFIER: an ornithine-nonselective A-domain.", has_fresh_blastp=True)
    assert "ADMISSION_GATE" not in _kinds(rep)


def test_tetramate_tetronate_fusion_flagged():
    rep = assess("This establishes an HSAF pathway; the FkbH + discrete ACP pair is the hallmark starter.")
    assert "MOTIF_GRAMMAR_CONFLICT" in _kinds(rep)


def test_explicit_class_conflict_is_allowed():
    rep = assess("The FkbH/ACP pair triggers a competing tetronate hypothesis; these do not yet establish "
                 "an HSAF/PTM pathway — class-conflict adjudication pending.")
    assert "MOTIF_GRAMMAR_CONFLICT" not in _kinds(rep)


def test_activity_inheritance_needs_validation():
    unlinked = assess("This BGC is most consistent with the strain's anti-Candida activity.")
    assert "ACTIVITY_INHERITANCE" in _kinds(unlinked)
    linked = assess("Fraction-correlation plus a heterologous-expression validation link this BGC to the "
                    "strain's anti-Candida activity.")
    assert "ACTIVITY_INHERITANCE" not in _kinds(linked)


def test_arithmetic_denominator_mismatch():
    rep = assess("Support is 2/41 genes; recognizable-gene share 0.625.")
    assert "ARITHMETIC_MISMATCH" in _kinds(rep)
