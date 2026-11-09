"""The RG-GMCI result says how many ranked pairs it exported and how many it left out.

The JSON caps `ranked_pairs` at RGGMCI_MAX_RANKED_PAIRS (keeping every HIGH pair past the cap),
but only `pairs_total` was recorded, so the "full result" could not be reconciled with what it held.
"""
from mamey import rggmci
from tests.test_447_rggmci_evidence_export_keeps_strong_pairs import BGCS, REFMAP


def test_counts_reconcile_without_a_cap():
    out = rggmci.compute_rggmci(BGCS, REFMAP)
    s = out["rggmci_summary"]
    assert s["ranked_pairs_exported"] == len(out["ranked_pairs"]) == s["pairs_total"]
    assert s["ranked_pairs_not_exported"] == 0


def test_counts_reconcile_with_a_cap(monkeypatch):
    monkeypatch.setattr(rggmci, "RGGMCI_MAX_RANKED_PAIRS", 2)
    out = rggmci.compute_rggmci(BGCS, REFMAP)
    s = out["rggmci_summary"]
    assert s["ranked_pairs_exported"] == len(out["ranked_pairs"])
    assert s["ranked_pairs_exported"] + s["ranked_pairs_not_exported"] == s["pairs_total"]
    assert s["ranked_pairs_not_exported"] > 0
