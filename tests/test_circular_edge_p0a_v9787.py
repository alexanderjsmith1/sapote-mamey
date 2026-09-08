"""v9.7.87 P0-a: closed/circular replicons don't get a false Edge at the origin."""
from __future__ import annotations
from mamey.parsers import _edge_status


def test_origin_adjacent_is_edge_when_linear():
    # a BGC near the start of a linear contig is Edge (possible truncation)
    assert _edge_status(100, 20000, 1_000_000, flank_bp=5000, is_circular=False) == "Edge"


def test_origin_adjacent_is_interior_when_circular():
    # the same BGC on a circular replicon is Interior (origin is not a truncation point)
    assert _edge_status(100, 20000, 1_000_000, flank_bp=5000, is_circular=True) == "Interior"


def test_end_adjacent_is_interior_when_circular():
    assert _edge_status(980_000, 999_000, 1_000_000, flank_bp=5000, is_circular=True) == "Interior"


def test_interior_unchanged_either_topology():
    # a mid-contig BGC is Interior regardless of topology
    assert _edge_status(400_000, 450_000, 1_000_000, is_circular=False) == "Interior"
    assert _edge_status(400_000, 450_000, 1_000_000, is_circular=True) == "Interior"


def test_full_contig_still_wins_over_circular():
    # a BGC spanning ~the whole replicon is Full-contig, not Interior, even if circular
    assert _edge_status(1, 990_000, 1_000_000, is_circular=True) == "Full-contig"


def test_closed_circular_parsing_control_no_edge():
    # parsing-control invariant: on a closed circular genome, no BGC should be Edge
    spans = [(100, 20000), (500_000, 520_000), (985_000, 999_500)]
    statuses = [_edge_status(s, e, 1_000_000, is_circular=True) for s, e in spans]
    assert "Edge" not in statuses, statuses
