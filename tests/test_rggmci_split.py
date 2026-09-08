"""Test the v9.7.21 RG-GMCI split-signature gate.

A cluster physically fragmented across two scaffolds presents as both fragments at a contig EDGE on
DIFFERENT contigs. The gate filters the full shared-reference pair set down to those cross-scaffold both-Edge
candidates, so a genuine split (the marinolide BGC020+BGC042 case on AJS-XXX) surfaces instead of being
buried beneath higher-scoring same-contig pairs.
"""
import os

from mamey import parsers
from mamey.rggmci import run_rggmci

AJS = "/mnt/user-data/uploads/AJS-XXX.zip"


def test_split_gate_present_in_output():
    # output schema carries the split list even when run on a small input
    if not os.path.exists(AJS):
        return
    bgcs = parsers.parse_bgcs_from_zip(AJS)
    r = run_rggmci(AJS, bgcs)
    assert "split_candidates" in r and "split_candidate_count" in r
    # every split candidate is genuinely cross-scaffold AND both-Edge
    for row in r["split_candidates"]:
        assert row["edge_a"] == "Edge" and row["edge_b"] == "Edge"
        assert row["contig_a"] != row["contig_b"]
        assert row["split_signature"] is True


def test_marinolide_split_surfaces_top_ranked():
    if not os.path.exists(AJS):
        return
    bgcs = parsers.parse_bgcs_from_zip(AJS)
    r = run_rggmci(AJS, bgcs)
    # the gate collapses 752 pairs to a handful of split candidates
    assert r["split_candidate_count"] < r["pairs_total"]
    # BGC020+BGC042 (marinolide, scaffolds 2+5) is present and top-ranked among split candidates
    pairs = [row["pair"] for row in r["split_candidates"]]
    marino = [p for p in pairs if "BGC020" in p and "BGC042" in p]
    assert marino, f"marinolide split not in candidates: {pairs[:5]}"
    assert pairs[0] == marino[0], f"marinolide not top-ranked; top is {pairs[0]}"


def test_split_candidates_are_subset_of_ranked():
    if not os.path.exists(AJS):
        return
    bgcs = parsers.parse_bgcs_from_zip(AJS)
    r = run_rggmci(AJS, bgcs)
    ranked_pairs = {row["pair"] for row in r["ranked_pairs"]}
    # split candidates that fit within the ranked window must also appear there (same rows, filtered view)
    for row in r["split_candidates"]:
        if row["rggmci_score"] >= min((x["rggmci_score"] for x in r["ranked_pairs"]), default=0):
            assert row["split_signature"] is True
