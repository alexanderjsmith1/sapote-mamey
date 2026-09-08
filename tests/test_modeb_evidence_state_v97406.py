"""D6: Mode B evidence escalation has executable fail-closed transitions."""
import pytest

from mamey.modeb_evidence_state import (
    EVIDENCE_STATES, EvidenceTransitionError, transition_evidence,
)
from mamey.modeb_publication_gate import STREAM_STATES

SHA = "a" * 64


def test_publication_gate_and_state_machine_share_one_vocabulary():
    assert STREAM_STATES is EVIDENCE_STATES


def test_unbound_query_can_be_admitted_only_with_immutable_binding():
    with pytest.raises(EvidenceTransitionError, match="requires source_locator"):
        transition_evidence("UNBOUND", "ADMITTED", reason="reviewed")
    t = transition_evidence("UNBOUND", "ADMITTED", reason="reviewed exact result",
                            source_locator="evidence://blastp/result.csv", source_sha256=SHA)
    assert t.as_dict()["current_state"] == "ADMITTED"


def test_admitted_cannot_revert_or_be_silently_superseded():
    with pytest.raises(EvidenceTransitionError, match="illegal"):
        transition_evidence("ADMITTED", "UNBOUND", reason="changed mind")
    with pytest.raises(EvidenceTransitionError, match="replacement_id"):
        transition_evidence("ADMITTED", "SUPERSEDED", reason="newer source")
    t = transition_evidence("ADMITTED", "SUPERSEDED", reason="newer exact run",
                            replacement_id="run-002")
    assert t.current_state == "SUPERSEDED"


def test_absent_in_scope_is_not_admitted_negative_evidence():
    t = transition_evidence("UNBOUND", "ABSENT_IN_SCOPE",
                            reason="BLASTp was outside the declared run scope")
    assert t.current_state == "ABSENT_IN_SCOPE" and not t.source_sha256


def test_terminal_state_cannot_reopen():
    with pytest.raises(EvidenceTransitionError, match="illegal"):
        transition_evidence("SUPERSEDED", "ADMITTED", reason="reuse",
                            source_locator="x", source_sha256=SHA)


def test_modeb_blastp_declares_query_emission_unbound(tmp_path):
    from mamey.modeb_blastp import emit_for_bgc
    result = emit_for_bgc(tmp_path / "package", "BGC001")
    assert result["status"] == "SKIPPED"
    assert result["evidence_state"] == "UNBOUND"
