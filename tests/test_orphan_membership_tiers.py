"""RC-1 lock — orphan-megasynthase membership + AT-only tiering (scan_orphan_megasynthase_motifs).

Locks the v9.7.x fix the bee-cohort feedback flagged as fixed-but-untested:
  (a) a megasynthase CDS within the antiSMASH ±20 kb flank of a called BGC is NOT an orphan;
  (c) an AT-only CDS (GHSxG nucleophile elbow, shared with esterases/lipases/hydrolases) is tiered to
      at_only (Tier-2), not the headline KS-bearing list.
Case (b) — two contig names differing only in cov-float formatting collapse to one key — is locked in
test_flbr_orphan_linkage.py::test_cov_format_contig_links_same; a util-level belt is added here too.

Standalone: python3 tests/test_orphan_membership_tiers.py
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mamey.models import BGCRecord, CDSFeature
from mamey.source_scans import scan_orphan_megasynthase_motifs, _contig_key, _ORPHAN_FLANK

# >= 200 aa, neutral product. KS_SEQ carries the catalytic motif [DE]TAC[ST]S; AT_SEQ carries ONLY GHS[..]G.
KS_SEQ = "M" + "A" * 120 + "DTACSS" + "A" * 120
AT_SEQ = "M" + "A" * 120 + "GHSLG" + "A" * 120


def _cds(contig, start, end, seq, product="hypothetical protein", locus="o1"):
    return CDSFeature(contig, start, end, 1, locus, product, seq, None, {})


def _bgc(contig, start, end):
    return BGCRecord(bgc_id="BGC01", contig=contig, region_number=1, start=start, end=end,
                     contig_length=400000, edge_status="Interior", products=["T1PKS"])


def test_flank_ks_cds_within_20kb_is_not_orphan():
    """(a) A KS CDS inside the ±20 kb flank of a called BGC is excluded; a KS CDS outside it is a genuine orphan."""
    bgc = _bgc("NODE_1_length_400000_cov_50.0", 100000, 120000)
    flank = _cds("NODE_1_length_400000_cov_50.0", 125000, 128000, KS_SEQ, locus="flank")  # 125k < 120k+20k
    far = _cds("NODE_1_length_400000_cov_50.0", 200000, 203000, KS_SEQ, locus="far")       # well outside
    out = scan_orphan_megasynthase_motifs([flank, far], [bgc])
    tags = {o["locus_tag"] for o in out["ks_bearing"]}
    assert "flank" not in tags, "in-flank megasynthase CDS mis-flagged as orphan"
    assert "far" in tags, "genuine orphan KS CDS (outside ±20 kb) not detected"


def test_at_only_cds_is_tier2_not_headline():
    """(c) An AT-only CDS is tiered to at_only (Tier-2), never the KS-bearing headline list."""
    at = _cds("NODE_9_length_50000_cov_30.0", 1000, 4000, AT_SEQ, locus="at1")
    out = scan_orphan_megasynthase_motifs([at], [])
    assert not out["ks_bearing"], "AT-only CDS leaked into the KS-bearing headline list"
    entry = next((o for o in out["at_only"] if o["locus_tag"] == "at1"), None)
    assert entry is not None, "AT-only CDS not tiered to at_only"
    assert entry["motifs"] == ["AT"]
    assert entry.get("likely_standalone_hydrolase") is True  # <=400 aa => most parsimoniously a hydrolase


def test_ks_with_at_is_tier1_ks_bearing():
    """A CDS bearing BOTH motifs is KS-bearing (Tier-1), with AT noted — not demoted to at_only."""
    seq = "M" + "A" * 80 + "DTACSS" + "A" * 40 + "GHSLG" + "A" * 80
    cds = _cds("NODE_7_length_60000_cov_20.0", 1000, 5000, seq, locus="ksat")
    out = scan_orphan_megasynthase_motifs([cds], [])
    ks = next((o for o in out["ks_bearing"] if o["locus_tag"] == "ksat"), None)
    assert ks is not None and "KS" in ks["motifs"] and "AT" in ks["motifs"]


def test_contig_key_collapses_cov_float():
    """(b) belt at the util level: cov-float formatting must not split one physical contig into two keys."""
    assert _contig_key("NODE_5_length_90000_cov_40.1") == _contig_key("NODE_5_length_90000_cov_40.10")
    assert _contig_key("NODE_5_length_90000_cov_40.1") == "NODE_5_length_90000"
    assert _ORPHAN_FLANK == 20000


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    print("orphan membership/tier RC-1 lock: all tests pass")
