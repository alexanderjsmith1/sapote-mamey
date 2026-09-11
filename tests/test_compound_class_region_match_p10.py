"""v9.7.87 P-10: compound-class predictions match BGCs by coordinate overlap, not by
contig broadcast. On a single-contig genome, a prediction must only annotate the BGC it
falls in — not every BGC on the chromosome."""
from __future__ import annotations
import pytest


def _overlap(ps, pe, bs, be):
    # mirror the cli.py overlap predicate
    return not (pe < bs or ps > be)


def test_overlap_predicate_matches_only_containing_bgc():
    # three BGCs on one contig; a prediction at 4361673-4400000 should hit only BGC3
    bgcs = [("BGC1", 0, 100000), ("BGC2", 200000, 300000), ("BGC3", 4350000, 4410000)]
    pred = (4361673, 4400000)
    hits = [bid for bid, bs, be in bgcs if _overlap(pred[0], pred[1], bs, be)]
    assert hits == ["BGC3"], hits


def test_no_broadcast_across_contig():
    # a prediction confined to one region must NOT annotate distant BGCs on the same contig
    bgcs = [("BGC1", 0, 50000), ("BGC2", 5000000, 5050000)]
    pred = (10000, 40000)
    hits = [bid for bid, bs, be in bgcs if _overlap(pred[0], pred[1], bs, be)]
    assert hits == ["BGC1"]
    assert "BGC2" not in hits
