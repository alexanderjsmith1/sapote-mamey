"""Per-orphan rescue work-order — _link_orphans_to_fragmented.

Connects each Tier-1 KS orphan to a fragmented megasynthase lead:
  same_contig => exact coordinate gap_estimate_bp (gap-PCR target)
  cross_contig => unresolvable; names the candidate fragmented PKS-class partners (not NRPS-only).
Claim-safe: candidate co-locus, not a confirmed join.

Standalone: python3 tests/test_flbr_orphan_linkage.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.source_scans import _link_orphans_to_fragmented, scan_flbr
from mamey.models import BGCRecord, CDSFeature


def _bgc(bid, contig, start, end, products, edge="Edge"):
    return BGCRecord(bgc_id=bid, contig=contig, region_number=1, start=start, end=end,
                     contig_length=max(end + 1000, 200000), edge_status=edge, products=products)


def _orphan(contig, locus, start, end):
    return {"contig": contig, "locus_tag": locus, "start": start, "end": end, "length_aa": 600, "motifs": ["KS"]}


def test_same_contig_exact_gap():
    bgcs = [_bgc("BGC07", "ctgA", 100000, 150000, ["T1PKS"])]
    o = [_orphan("ctgA", "oA", 160000, 162000)]   # 10 kb past the 3' edge
    _link_orphans_to_fragmented(o, bgcs, ["BGC07"])
    assert o[0]["linkage"] == "same_contig" and o[0]["nearest_fragmented_bgc"] == "BGC07"
    assert o[0]["gap_estimate_bp"] == 10000


def test_same_contig_picks_nearest():
    bgcs = [_bgc("BGC01", "ctgA", 10000, 20000, ["T1PKS"]), _bgc("BGC07", "ctgA", 100000, 150000, ["T1PKS"])]
    o = [_orphan("ctgA", "oA", 160000, 162000)]   # 10 kb from BGC07, ~140 kb from BGC01
    _link_orphans_to_fragmented(o, bgcs, ["BGC01", "BGC07"])
    assert o[0]["nearest_fragmented_bgc"] == "BGC07" and o[0]["gap_estimate_bp"] == 10000


def test_cross_contig_names_pks_partners_only():
    bgcs = [_bgc("BGC07", "ctgA", 100000, 150000, ["T1PKS"]),
            _bgc("BGC09", "ctgC", 1, 9000, ["NRPS"])]   # NRPS-only: not a KS-orphan partner
    o = [_orphan("ctgB", "oB", 1, 1500)]
    _link_orphans_to_fragmented(o, bgcs, ["BGC07", "BGC09"])
    assert o[0]["linkage"] == "cross_contig" and o[0]["nearest_fragmented_bgc"] is None
    assert o[0]["candidate_partner_bgcs"] == ["BGC07"]   # PKS only, NRPS excluded


def test_cov_format_contig_links_same():
    bgcs = [_bgc("BGC07", "NODE_5_length_90000_cov_40.1", 10000, 60000, ["transAT-PKS"])]
    o = [_orphan("NODE_5_length_90000_cov_40.10", "oA", 70000, 72000)]   # diff cov format, same contig
    _link_orphans_to_fragmented(o, bgcs, ["BGC07"])
    assert o[0]["linkage"] == "same_contig" and o[0]["gap_estimate_bp"] == 10000


def test_scan_flbr_attaches_linkage_to_ks_orphans():
    def cds(c, l, t, s, e):
        return CDSFeature(contig=c, start=s, end=e, strand=1, locus_tag=l, product="hypothetical", translation=t)
    ks = "M" + "A" * 250 + "DTACSSS" + "A" * 250
    cdss = [cds("ctgZ", "orf1", ks, 1, 1600)]   # orphan KS, no BGC on ctgZ
    bgcs = [_bgc("BGC07", "ctgA", 100000, 150000, ["T1PKS"])]
    out = scan_flbr(cdss, bgcs)
    cand = out["orphan_megasynthase_candidates"]
    assert cand and "linkage" in cand[0] and cand[0]["linkage"] == "cross_contig"


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
