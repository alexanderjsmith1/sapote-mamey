"""Round-five detectors must not borrow a denial from another clause."""
import pytest

from mamey.claim_safety_gate import lint_text


@pytest.mark.parametrize("claim", [
    "The cluster produ<!-- -->ces venezuelin.",
    "The cluster is venezuelin-producing.",
    "Product: venezuelin.",
])
def test_previous_sentence_cannot_suppress_claim(claim):
    assert lint_text("No evidence.\n" + claim)


@pytest.mark.parametrize("separator", [". ", "; ", "—", "? ", "! ", "\n"])
@pytest.mark.parametrize("claim", [
    "The cluster produ<!-- -->ces venezuelin.",
    "The cluster is venezuelin-producing.",
])
def test_independent_clause_cannot_borrow_negation(separator, claim):
    assert lint_text("No evidence" + separator + claim)


@pytest.mark.parametrize("claim", [
    "Cannot claim that the cluster produ<!-- -->ces venezuelin.",
    "Cannot claim that the cluster is venezuelin-producing.",
    "Cannot be claimed: that this strain produ<!-- -->ces mycofactocin.",
])
def test_genuine_local_denial_remains_clean(claim):
    assert lint_text(claim) == []
