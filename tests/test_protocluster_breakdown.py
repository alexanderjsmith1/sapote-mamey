"""Composite-region attribution — protocluster_breakdown.

A composite region (>=3 single cand_clusters) is kept as one BGCRecord (inventory stable) but carries a
protocluster_breakdown that de-inflates its merged product string into the constituent single-class
protoclusters. Single-owner KCB/CCTT attribution is deliberately NOT forced: protocluster spans overlap, so
the region-level aggregate spans all of them.

Standalone: python3 tests/test_protocluster_breakdown.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.parsers import protocluster_breakdown
from mamey.models import BGCRecord


class _Loc:
    def __init__(self, s, e):
        self.start, self.end = s, e


class _F:
    def __init__(self, ftype, product=None, num=None, span=(0, 0)):
        self.type = ftype
        self.location = _Loc(*span)
        self.qualifiers = {}
        if product is not None:
            self.qualifiers["product"] = [product]
        if num is not None:
            self.qualifiers["protocluster_number"] = [str(num)]


def test_breakdown_extracts_each_protocluster_sorted():
    feats = [_F("region"), _F("cand_cluster", span=(0, 148271)),
             _F("protocluster", "T1PKS", 5, (84192, 148271)),
             _F("protocluster", "T3PKS", 1, (0, 26188)),
             _F("protocluster", "NRPS", 4, (6880, 93275))]
    pcs = protocluster_breakdown(feats)
    assert [p["product"] for p in pcs] == ["T3PKS", "NRPS", "T1PKS"]   # sorted by rel_start
    assert pcs[0]["rel_start"] == 0 and pcs[2]["rel_end"] == 148271
    assert pcs[1]["protocluster_number"] == 4


def test_no_protoclusters_empty():
    assert protocluster_breakdown([_F("region"), _F("CDS")]) == []


def test_bgcrecord_breakdown_default_additive():
    b = BGCRecord(bgc_id="B", contig="c", region_number=1, start=1, end=9, contig_length=99)
    assert b.protocluster_breakdown == []


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
