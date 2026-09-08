"""v9.7.395: modeb_evidence_gate gates (2) and (4) must not be defeatable by
document-scope matches unrelated to (or negating) the actual claim.

The v9.7.371 fix bounded gate (3)'s disclaimer window after showing any card could defeat the
novelty gate "just by containing the standard boilerplate ANYWHERE later in the document". The
same defeat existed, unfixed, in the two sibling gates of the same file:

- Gate (2) MOTIF_GRAMMAR_CONFLICT: `CONFLICT_OK` (whose `do not (?:yet )?establish` branch
  matches routine claim-safety hedging) was searched over the WHOLE document. A real
  HSAF-identity-vs-FkbH/tetronate conflict was cleared by an unrelated hedge sentence
  ~1,100 characters away.
- Gate (4) ACTIVITY_INHERITANCE: `ACTIVITY_VALIDATED` matched the bare term anywhere — so the
  sentence "No heterologous expression or knockout data exist", which ADMITS the validation is
  absent, cleared the validation gate. Deferrals ("heterologous expression would be required")
  did the same.

Both reproduced on pristine .394: base cards -> HOLD with the expected violation; the same cards
plus the defeat sentence -> ADMISSIBLE with zero violations.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "modeb_evidence_gate.py"
_spec = importlib.util.spec_from_file_location("modeb_evidence_gate_scope_ut", TOOL)
meg = importlib.util.module_from_spec(_spec)
sys.modules["modeb_evidence_gate_scope_ut"] = meg  # so @dataclass can resolve cls.__module__
_spec.loader.exec_module(meg)
assess = meg.assess_modeb_card

PAD = ("Neighboring loci carry standard housekeeping functions. " * 20).strip()

G2_BASE = ("The FkbH plus discrete ACP pair is the hallmark starter of this cluster, "
           "read here as HSAF grammar.")
G4_BASE = ("The strain's measured anti-Candida profile is most consistent with this BGC's "
           "activity, making it the leading explanation.")


def _kinds(rep):
    return {v.kind for v in rep.violations}


def test_gate2_base_conflict_still_fires():
    assert "MOTIF_GRAMMAR_CONFLICT" in _kinds(assess(G2_BASE))


def test_gate2_distant_unrelated_hedge_does_not_clear_conflict():
    text = (G2_BASE + "\n\n" + PAD + "\n\nSeparately, the TFBS hits in the flanking region "
            "do not establish regulon membership.")
    assert "MOTIF_GRAMMAR_CONFLICT" in _kinds(assess(text)), \
        "an unrelated hedge 1,100+ chars away must not adjudicate the motif-grammar conflict"


def test_gate2_adjacent_adjudication_still_clears_conflict():
    """The legitimate escape (hedge NEXT TO the claim) must keep working."""
    text = ("The FkbH/ACP pair triggers a competing tetronate hypothesis; these do not yet "
            "establish an HSAF/PTM pathway — class-conflict adjudication pending.")
    assert "MOTIF_GRAMMAR_CONFLICT" not in _kinds(assess(text))


def test_gate4_base_inheritance_still_fires():
    assert "ACTIVITY_INHERITANCE" in _kinds(assess(G4_BASE))


def test_gate4_admission_of_absent_validation_does_not_clear():
    text = G4_BASE + "\n\n" + PAD + "\n\nNo heterologous expression or knockout data exist for this locus."
    assert "ACTIVITY_INHERITANCE" in _kinds(assess(text)), \
        "a sentence ADMITTING validation is absent must not count as validation evidence"


def test_gate4_deferred_validation_does_not_clear():
    text = G4_BASE + " Heterologous expression would be required to confirm the link."
    assert "ACTIVITY_INHERITANCE" in _kinds(assess(text)), \
        "a deferred/future validation must not count as validation evidence"


def test_gate4_affirmed_validation_still_clears():
    """The legitimate escape (real validation evidence) must keep working."""
    text = ("Fraction-correlation plus a heterologous-expression validation link this BGC to "
            "the strain's anti-Candida activity.")
    assert "ACTIVITY_INHERITANCE" not in _kinds(assess(text))
