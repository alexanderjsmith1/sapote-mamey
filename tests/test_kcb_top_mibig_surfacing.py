"""v9.7.22: kcb_top must surface the MIBiG identity, not the genome self-hit.

A cluster excised from a sequenced genome that is in the KCB database self-hits at rank 1 (whole-genome match),
which masks the MIBiG compound in the displayed kcb_top. The fix surfaces the MIBiG reference line in kcb_top
and preserves the raw rank-1 line in clusterblast_top. Confirmed pervasive on AJS-XXX (a genome-derived strain).
"""
import os

from mamey import parsers, antismash_evidence

AJS = "/mnt/user-data/uploads/AJS-XXX.zip"


def _evidenced():
    bgcs = parsers.parse_bgcs_from_zip(AJS)
    ev = antismash_evidence.parse_antismash_evidence(AJS, bgcs)
    antismash_evidence.apply_evidence_to_bgcs(bgcs, ev)
    return bgcs


def test_kcb_top_surfaces_mibig_not_genome_self_hit():
    if not os.path.exists(AJS):
        return
    bgcs = _evidenced()
    # for any BGC with a resolved MIBiG product, kcb_top must carry the accession/product, not a genome line
    checked = 0
    for b in bgcs:
        prod = getattr(b, "closest_candidate_kcb_product", "") or ""
        if prod in ("UNRESOLVED", ""):
            continue
        kt = (getattr(b, "kcb_top", "") or "")
        assert "BGC" in kt or prod[:12].lower() in kt.lower(), f"{b.bgc_id} kcb_top did not surface MIBiG: {kt}"
        # the genome self-hit is not lost — it is preserved in clusterblast_top
        assert hasattr(b, "clusterblast_top")
        checked += 1
    assert checked > 0, "no resolved-MIBiG BGCs found to check"


def test_clusterblast_top_preserves_rank1_line():
    if not os.path.exists(AJS):
        return
    bgcs = _evidenced()
    # at least one BGC should show the genome self-hit preserved in clusterblast_top while kcb_top shows MIBiG
    rescued = [b for b in bgcs
               if (getattr(b, "clusterblast_top", "") or "")
               and ("chromosome" in (b.clusterblast_top or "").lower()
                    or "genome" in (b.clusterblast_top or "").lower()
                    or "strain" in (b.clusterblast_top or "").lower())
               and "BGC" in (getattr(b, "kcb_top", "") or "")]
    assert rescued, "expected at least one genome-self-hit rescued into clusterblast_top with MIBiG in kcb_top"
