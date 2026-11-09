"""Guard and selection-rule wording states what the software did, not a biological conclusion.

The mis-anchor guard reads the supplied annotation only, so it cannot show a reference hit is
spurious. The rescue edge gate is a selection rule, so it cannot show an Interior region is complete.
"""
from __future__ import annotations

from pathlib import Path

from mamey import source_scans

ROOT = Path(__file__).resolve().parents[1]


def test_misanchor_claim_safety_is_a_routing_guard():
    text = source_scans.scan_misanchor_guards([], [])["claim_safety"]
    assert "spurious" not in text
    assert "routing guard" in text and "incomplete assembly or annotation" in text


def test_source_scans_does_not_call_the_anchor_spurious_for_the_locus():
    src = (ROOT / "mamey" / "source_scans.py").read_text(encoding="utf-8")
    assert "spurious for this locus" not in src
    assert "spurious hit for THIS locus" not in src
    assert "anchor is a spurious similarity hit" not in src


def test_rescue_edge_gate_is_described_as_a_selection_rule():
    src = (ROOT / "mamey" / "diagnostic_rescue.py").read_text(encoding="utf-8")
    assert "A complete (Interior) cluster is whole" not in src
    assert "complete (Interior) cluster, this is co-occurrence" not in src
    assert "selection rule" in src.lower()
