"""The EFLS pairing-scope label must name the filter the scan applies.

The scan skips a pair only when both members are Interior. A pair with an Unknown boundary is
kept, so a label that promises "at least one Edge or Full-contig" member is wrong.
"""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.source_scans import EFLS_PAIRING_SCOPE, scan_efls  # noqa: E402


def _bgc(bgc_id, edge_status):
    return SimpleNamespace(bgc_id=bgc_id, edge_status=edge_status, products=["T1PKS"], mibig_hits=[])


def _pairs(statuses):
    out = scan_efls([_bgc(f"BGC{i + 1:03d}", s) for i, s in enumerate(statuses)], {}, {}, {})
    return out, {(p["edge_status_a"], p["edge_status_b"]) for p in out["candidate_pairs"]}


def test_only_interior_interior_pairs_are_excluded():
    out, kept = _pairs(["Interior", "Interior", "Unknown", "Edge", "Full-contig"])
    assert ("Interior", "Interior") not in kept
    assert ("Interior", "Unknown") in kept
    assert ("Interior", "Edge") in kept
    assert ("Interior", "Full-contig") in kept
    assert out["candidate_pair_count"] == 9   # ten pairs, less the one Interior/Interior pair


def test_label_names_the_exclusion_and_makes_no_edge_promise():
    out, kept = _pairs(["Unknown", "Interior"])
    assert kept == {("Unknown", "Interior")}
    assert out["pairing_scope"] == EFLS_PAIRING_SCOPE == "all_vs_all_excluding_interior_interior_pairs"
    assert "edge" not in out["pairing_scope"]


def test_two_interior_members_give_no_pairs():
    out, kept = _pairs(["Interior", "Interior"])
    assert kept == set() and out["candidate_pair_count"] == 0
