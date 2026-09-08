"""Region-merge inflation flag — count_single_cand_clusters / composite_region.

antiSMASH collapses neighbouring protoclusters into one region; when >=3 /kind="single" cand_clusters share
a region, its product string is a merge of several distinct single-class clusters (not one hybrid) and a
single lead score aggregates them. The parser counts single cand_clusters and sets BGCRecord.composite_region
(>=3) + single_protocluster_count; the triage board surfaces it. Verified to reproduce on panel genomes
(CNQ490 region001 x2, Actinomadura, Micromonospora).

Standalone: python3 tests/test_composite_region_flag.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.parsers import count_single_cand_clusters
from mamey.models import BGCRecord


class _F:
    def __init__(self, ftype, kind=None):
        self.type = ftype
        self.qualifiers = {"kind": [kind]} if kind is not None else {}


def test_counts_only_single_cand_clusters():
    feats = [_F("region"), _F("cand_cluster", "single"), _F("cand_cluster", "single"),
             _F("cand_cluster", "neighbouring"), _F("cand_cluster", "single"), _F("protocluster"),
             _F("CDS"), _F("cand_cluster", "chemical_hybrid")]
    assert count_single_cand_clusters(feats) == 3


def test_below_threshold_not_composite():
    feats = [_F("cand_cluster", "single"), _F("cand_cluster", "single"), _F("cand_cluster", "neighbouring")]
    n = count_single_cand_clusters(feats)
    assert n == 2 and (n >= 3) is False


def test_missing_kind_qualifier_ignored():
    feats = [_F("cand_cluster"), _F("cand_cluster", "single")]
    assert count_single_cand_clusters(feats) == 1


def test_bgcrecord_defaults_are_additive():
    b = BGCRecord(bgc_id="BGC1", contig="c", region_number=1, start=1, end=9, contig_length=99)
    assert b.composite_region is False and b.single_protocluster_count == 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
