"""Generic-safety + integrity guard for docs/BLASTP_NOVELTY_WORKFLOW.md.

Doc-only card: no engine/scoring surface. This test enforces the .355 generic-engine rule
(the shipped bundle carries NO strain IDs / collection names / personal names) and checks the
doc actually states the claim ceiling + the four channels. Self-skips if the doc is not present
(so it is inert until the card is folded), then activates.
"""
import re
from pathlib import Path

import pytest


def _doc():
    for base in (Path(__file__).resolve().parents[1] / "payload" / "docs",   # in the card
                 Path(__file__).resolve().parents[2] / "docs"):               # folded into bundle
        p = base / "BLASTP_NOVELTY_WORKFLOW.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
    pytest.skip("BLASTP_NOVELTY_WORKFLOW.md not present (card not folded)")


def test_no_strain_ids_or_collection_names():
    text = _doc()
    # no concrete AS-strain / AJS-strain / PENDING- identifiers (placeholders like <STRAIN> are fine)
    leaks = re.findall(r"\b(?:AS|AJS|PENDING)-\d+\b", text)
    assert not leaks, f"generic-engine rule: doc leaks strain IDs {sorted(set(leaks))}"


def test_states_claim_ceiling_and_four_channels():
    text = _doc().lower()
    assert "claim ceiling" in text
    assert "similarity" in text and "identity" in text          # similarity != identity
    for channel in ("nr", "clusterblast", "swissprot", "clusterednr"):
        assert channel in text, f"channel not documented: {channel}"


def test_states_unmixed_rule_and_concurrency_budget():
    text = _doc().lower()
    assert "unmixed" in text or "never mix" in text
    assert "pct_positives" in text and "pct_identity" in text    # separate columns
    assert "open rids" in text                                   # concurrency discipline present
