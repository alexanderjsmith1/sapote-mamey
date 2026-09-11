"""Rescue-readiness signal in scan_flbr — genome-level contig-rescue triage.

rescue_priority_score = fragmented_megasynthase_count + orphan_megasynthase_count (Tier-1 KS only); the tier
requires a sub-Good assembly (interior_fraction < 0.70) so a good assembly with separate loci reads LOW.

Standalone: python3 tests/test_flbr_rescue_readiness.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.source_scans import _rescue_readiness
from mamey.models import BGCRecord


def _bgcs(n_interior, n_edge):
    out = [BGCRecord(bgc_id=f"I{i}", contig="c", region_number=i, start=1, end=9, contig_length=99,
                     edge_status="Interior") for i in range(n_interior)]
    out += [BGCRecord(bgc_id=f"E{i}", contig="c", region_number=100 + i, start=1, end=9, contig_length=99,
                      edge_status="Edge") for i in range(n_edge)]
    return out


def test_poor_assembly_many_fragments_high():
    # 4 interior / 16 edge -> interior_frac 0.20 (Poor); 5 orphan KS, 8 fragmented -> HIGH
    r = _rescue_readiness(_bgcs(4, 16), orphan_ks_count=5, orphan_at_count=30, fragmented_count=8)
    assert r["rescue_readiness"] == "HIGH"
    assert r["rescue_priority_score"] == 13              # 8 + 5, AT-only excluded
    assert r["assembly_interior_fraction"] == 0.2


def test_good_assembly_reads_low_even_with_counts():
    # 18 interior / 2 edge -> 0.90 (Good): counts more likely separate loci, not splits -> LOW
    r = _rescue_readiness(_bgcs(18, 2), orphan_ks_count=5, orphan_at_count=10, fragmented_count=8)
    assert r["rescue_readiness"] == "LOW"


def test_moderate_when_fragmented_only():
    # 10 interior / 10 edge -> 0.50 (Mod); 0 orphan KS but 4 fragmented -> MODERATE
    r = _rescue_readiness(_bgcs(10, 10), orphan_ks_count=0, orphan_at_count=12, fragmented_count=4)
    assert r["rescue_readiness"] == "MODERATE" and r["rescue_priority_score"] == 4


def test_at_only_does_not_drive_score_or_tier():
    # poor assembly, zero KS, zero fragmented, lots of AT-only -> LOW, score 0 (AT-only never inflates)
    r = _rescue_readiness(_bgcs(2, 18), orphan_ks_count=0, orphan_at_count=37, fragmented_count=0)
    assert r["rescue_readiness"] == "LOW" and r["rescue_priority_score"] == 0
    assert r["orphan_at_ambiguous_count"] == 37          # still reported for completeness


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
