"""G2 — FLBR orphan-contig megasynthase motif scan (tiered, flank-aware).

scan_flbr is annotation-bound and misses megasynthase fragments on orphan contigs antiSMASH left
unannotated. scan_orphan_megasynthase_motifs detects them by conserved active-site motifs on CDS outside
every called BGC core ±20 kb flank, tiered by specificity:
  - ks_bearing  (Tier 1, evidential)  = KS DTACSSS present
  - at_only     (Tier 2, ambiguous)   = AT GHSxG only (alpha/beta-hydrolase elbow; NOT megasynthase evidence)

Covers the two v9.7.10 feedback fixes: §1 in-BGC flank CDS no longer mis-flagged + cov-format contig match;
§2 AT-only no longer pooled into the megasynthase headline. Claim-safe (motif-candidate, linkage unproven).

Standalone: python3 tests/test_flbr_orphan_motifs.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mamey.source_scans import scan_orphan_megasynthase_motifs, scan_flbr
from mamey.models import CDSFeature, BGCRecord

_KS = "DTACSSS"
_AT = "GHSQG"


def _cds(contig, locus, product, translation, start=1, end=None):
    end = end if end is not None else start + len(translation) * 3
    return CDSFeature(contig=contig, start=start, end=end, strand=1, locus_tag=locus,
                      product=product, translation=translation)


def _bgc(contig, start, end):
    return BGCRecord(bgc_id="BGC1", contig=contig, region_number=1, start=start, end=end, contig_length=500000)


def test_orphan_ks_fragment_is_tier1():
    cds = [_cds("orphanC", "orf1", "hypothetical protein", "M" + "A" * 250 + _KS + "A" * 250,
                start=1, end=1600)]
    res = scan_orphan_megasynthase_motifs(cds, [_bgc("bgcC", 1, 2000)])
    assert len(res["ks_bearing"]) == 1 and res["ks_bearing"][0]["locus_tag"] == "orf1"
    assert "KS" in res["ks_bearing"][0]["motifs"] and res["at_only"] == []


def test_at_only_is_tier2_not_megasynthase():
    """§2: an UNannotated GHSxG CDS is hydrolase-ambiguous, NOT a megasynthase candidate."""
    cds = [_cds("orphanC", "orf2", "hypothetical protein", "M" + "A" * 250 + _AT + "A" * 250,
                start=1, end=1600)]
    res = scan_orphan_megasynthase_motifs(cds, [_bgc("bgcC", 1, 2000)])
    assert res["ks_bearing"] == []                       # not pooled into the headline
    assert len(res["at_only"]) == 1 and res["at_only"][0]["motifs"] == ["AT"]
    assert "hydrolase" in res["at_only"][0]["parsimony"].lower()


def test_ks_plus_at_cooccurrence_is_tier1():
    cds = [_cds("orphanC", "orf3", "hypothetical", "M" + "A" * 200 + _KS + "A" * 100 + _AT + "A" * 200,
                start=1, end=2200)]
    res = scan_orphan_megasynthase_motifs(cds, [_bgc("bgcC", 1, 2000)])
    assert res["ks_bearing"] and set(res["ks_bearing"][0]["motifs"]) == {"KS", "AT"}


def test_flank_cds_not_orphan():
    """§1: a megasynthase CDS in a called cluster's 5' flank (outside core, inside region) is NOT orphan."""
    # BGC core 27933-74590; flank CDS at 20000-26657 (1.3 kb upstream of core) -> within ±20 kb -> excluded
    cds = [_cds("ctg21", "ctg21_41", "hypothetical", "M" + "A" * 700 + _KS + "A" * 700,
                start=20000, end=26657)]
    res = scan_orphan_megasynthase_motifs(cds, [_bgc("ctg21", 27933, 74590)])
    assert res["ks_bearing"] == [] and res["at_only"] == []


def test_distant_same_contig_ks_still_orphan():
    """A KS CDS far (> flank) from any cluster on the same contig still surfaces."""
    cds = [_cds("ctg21", "ctg21_far", "hypothetical", "M" + "A" * 250 + _KS + "A" * 250,
                start=300000, end=301600)]
    res = scan_orphan_megasynthase_motifs(cds, [_bgc("ctg21", 27933, 74590)])
    assert len(res["ks_bearing"]) == 1


def test_cov_format_contig_match():
    """§1: same physical contig with differently-formatted SPAdes cov suffix still matches (no false orphan)."""
    bgc = _bgc("NODE_21_length_53120_cov_63.042318", 27933, 74590)
    cds = [_cds("NODE_21_length_53120_cov_63.42318", "n21_flank", "hypothetical",
                "M" + "A" * 700 + _KS + "A" * 700, start=20000, end=26657)]
    res = scan_orphan_megasynthase_motifs(cds, [bgc])
    assert res["ks_bearing"] == []   # matched despite cov-string difference -> excluded as flank


def test_short_and_annotated_excluded():
    short = _cds("orphanC", "s", "hypothetical", "MDTACSSS")                       # < 200 aa
    pks = _cds("orphanC", "p", "polyketide synthase", "M" + "A" * 250 + _KS + "A" * 250)  # annotated
    lip = _cds("orphanC", "l", "alpha/beta hydrolase lipase", "M" + "A" * 250 + _AT + "A" * 250)  # hydrolase
    res = scan_orphan_megasynthase_motifs([short, pks, lip], [_bgc("bgcC", 1, 2000)])
    assert res["ks_bearing"] == [] and res["at_only"] == []


def test_scan_flbr_emits_both_tiers_additively():
    cds = [_cds("orphanC", "orf1", "hypothetical", "M" + "A" * 250 + _KS + "A" * 250, start=1, end=1600)]
    out = scan_flbr(cds, [])
    assert "orphan_megasynthase_candidates" in out and "orphan_at_hydrolase_ambiguous" in out
    assert any(c["locus_tag"] == "orf1" for c in out["orphan_megasynthase_candidates"])
    assert "flbr_grade" in out and "genome_wide_ks_like_count" in out   # existing contract intact


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    p = 0
    for fn in fns:
        try:
            fn(); p += 1; print(f"PASS {fn.__name__}")
        except AssertionError as e:
            print(f"FAIL {fn.__name__}: {e}")
    print(f"\n{p}/{len(fns)} passed")
