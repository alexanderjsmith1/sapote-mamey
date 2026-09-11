"""REVIEWED_SCOPE_LIMIT: a third §28 section-disposition state (v9.7.412).

Motivating finding (Black Cherry audit, .412, "Corrections adopted after Codex review",
item 1): the two-state vocabulary {SUBSTANTIVE, REASONED_NOT_APPLICABLE} cannot express a
section that was reviewed but whose bound evidence is genuinely incomplete or unbound --
an author facing that state had to pick a wrong answer either way. This adds a third,
distinct state without re-deriving any existing card's §28 table (that is a content
judgement, left to the author/reviewer).
"""
from __future__ import annotations

from mamey.modeb_evidence_state import EVIDENCE_STATES
from mamey.modeb_publication_gate import (
    HISTORY_DISPOSITIONS,
    SECTION_STATES,
    _section_matrix_findings,
)


def _rows(state_by_section: dict[int, str]) -> list[list[str]]:
    return [
        [f"§{n}", state_by_section.get(n, "SUBSTANTIVE"), "basis", "NOT_APPLICABLE", "scope"]
        for n in range(1, 49)
    ]


def test_reviewed_scope_limit_is_accepted() -> None:
    """A row whose state cell is REVIEWED_SCOPE_LIMIT satisfies the state check."""
    rows = _rows({41: "REVIEWED_SCOPE_LIMIT", 44: "REVIEWED_SCOPE_LIMIT", 45: "REVIEWED_SCOPE_LIMIT"})
    findings = _section_matrix_findings(rows)
    assert [f for f in findings if f["code"] == "SECTION_RECONCILIATION_STATE"] == []


def test_original_two_states_still_accepted() -> None:
    """The pre-existing states are unaffected -- this is additive, not a replacement."""
    rows = _rows({7: "REASONED_NOT_APPLICABLE"})
    findings = _section_matrix_findings(rows)
    assert [f for f in findings if f["code"] == "SECTION_RECONCILIATION_STATE"] == []


def test_unrecognised_state_still_flagged() -> None:
    """Negative control: the check is not vacuous -- a bogus state still fires."""
    rows = _rows({1: "BOGUS_STATE"})
    findings = _section_matrix_findings(rows)
    state_findings = [f for f in findings if f["code"] == "SECTION_RECONCILIATION_STATE"]
    assert len(state_findings) == 1
    assert state_findings[0]["section"] == 1


def test_section_states_has_exactly_three_members() -> None:
    """Pins the vocabulary size so a future edit here is a deliberate, reviewed change."""
    assert SECTION_STATES == {"SUBSTANTIVE", "REASONED_NOT_APPLICABLE", "REVIEWED_SCOPE_LIMIT"}


def test_reviewed_scope_limit_does_not_collide_with_other_vocabularies() -> None:
    """A single §28 row's cells are checked against SECTION_STATES, HISTORY_DISPOSITIONS and
    (elsewhere) EVIDENCE_STATES by set membership, not by column position -- a state name
    shared with either of the other two vocabularies would create a false-positive match
    unrelated to section disposition. Guard that REVIEWED_SCOPE_LIMIT was chosen disjoint."""
    assert SECTION_STATES & EVIDENCE_STATES == set()
    assert SECTION_STATES & HISTORY_DISPOSITIONS == set()
