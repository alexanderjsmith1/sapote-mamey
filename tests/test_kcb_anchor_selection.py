"""Regression: preferred_kcb_anchor — the P1-C known-cluster-hit selector.

`kcb_top` is the raw rank-1 knownclusterblast line and is genome-self-hit-dominated (corpus-scale: ~2.2% of
3,422 BGCs surface a MIBiG accession in kcb_top, vs ~59% resolved in deep analysis). The resolved MIBiG line
is already captured in closest_candidate_kcb_product / closest_mibig_accession with provenance
MIBIG_REFERENCE_LINE. preferred_kcb_anchor surfaces that resolved field for display consumers; it does NOT
re-rank kcb_top (so it needs no raw KCB file). KCB remains a similarity signal, not identity.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from mamey.models import BGCRecord
from mamey.scoring import preferred_kcb_anchor


def _bgc(kcb_top, ccp="UNRESOLVED", acc="UNRESOLVED", prov="UNRESOLVED"):
    b = BGCRecord(bgc_id="BGC001", region_number=1, products=["T2PKS"], contig="c1", start=1, end=20000,
                  contig_length=200000, edge_status="Interior", architecture_confidence="A", kcb_top=kcb_top,
                  closest_candidate_kcb_product=ccp)
    b.closest_mibig_accession = acc
    b.closest_product_provenance = prov
    return b


def test_prefers_mibig_reference_over_genome_self_hit():
    """Granaticin positive control: kcb_top is the genome self-hit; the selector surfaces the MIBiG line."""
    b = _bgc("Streptomyces vietnamensis genome assembly, whole genome shotgun",
             ccp="granaticin", acc="BGC0000227", prov="MIBIG_REFERENCE_LINE")
    label, prov = preferred_kcb_anchor(b)
    assert prov == "MIBIG_REFERENCE_LINE"
    assert label == "granaticin (BGC0000227)"
    assert "genome" not in label  # the self-hit no longer masks the identity


def test_falls_back_to_kcb_top_when_no_mibig_reference():
    """No resolved MIBiG line -> the raw kcb_top is the honest best anchor (still a similarity signal)."""
    b = _bgc("Streptomyces sp. best subject cluster", prov="KCB_TOP_FIELD")
    label, prov = preferred_kcb_anchor(b)
    assert label == "Streptomyces sp. best subject cluster"
    assert prov == "KCB_TOP_FIELD"


def test_mibig_label_without_accession():
    b = _bgc("genome self-hit", ccp="lasalocid", acc="UNRESOLVED", prov="MIBIG_REFERENCE_LINE")
    label, prov = preferred_kcb_anchor(b)
    assert label == "lasalocid" and prov == "MIBIG_REFERENCE_LINE"


def test_unresolved_anchor():
    b = _bgc(None)
    label, prov = preferred_kcb_anchor(b)
    assert label == "UNRESOLVED"


if __name__ == "__main__":
    for fn in list(globals().values()):
        if callable(fn) and getattr(fn, "__name__", "").startswith("test_"):
            fn()
    print("preferred_kcb_anchor: all tests pass")
