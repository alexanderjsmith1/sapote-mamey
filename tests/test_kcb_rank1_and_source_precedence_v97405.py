"""v9.7.405 — the two separately-dated KCB_score defects, pinned TOGETHER on one synthetic fixture.

docs/KCB_SCORE_PROVENANCE.md records two 2026-07-01 fixes on the same real region (BGC058):
  (1) rank-1-vs-max: antiSMASH orders "Significant hits" by significance, not raw cumulative score;
      a rank-46 hit (tetrafibricin, 61753) numerically outscored rank 1 (aculeximycin, 37992) and
      the old max() reported the wrong hit. KCB_top and KCB_score must describe the SAME hit — rank 1.
  (2) source precedence: knownclusterblast/, clusterblast/ and subclusterblast/ share filenames and
      collapse onto one region key; a generic whole-genome ClusterBlast hit (Tu 4113, 73038) is NOT a
      MIBiG comparator and must never overwrite the KnownClusterBlast score. When no knownclusterblast
      record exists the fallback is FLAGGED (parse_confidence LOW, needs_manual_kcb_check yes).
No test pinned both on one fixture before; this one does, so a regression in either shows here.
"""
from __future__ import annotations

import zipfile

from mamey.antismash_evidence import apply_evidence_to_bgcs, parse_antismash_evidence

CONTIG = "NODE_1_length_90000_cov_50.0"


def _block(rank: int, acc: str, source: str, score: float, kind: str) -> str:
    return (f">>\n{rank}. {acc}\nSource: {source}\nType: {kind}\n"
            f"Number of proteins with BLAST hits to this cluster: 5\nCumulative BLAST score: {score}\n\n"
            "Table of Blast hits (query gene, subject gene, %identity, blast score, %coverage, e-value):\n"
            f"ctg1_10\t{acc}_g1\t60\t{int(score/5)}\t95.0\t0.0\n\n")


KCB_TXT = (f"ClusterBlast scores for {CONTIG}\n\nTable of genes, locations, strands and annotations of query cluster:\n\n"
           "Significant hits: \n1. BGC0000002\taculeximycin\n2. BGC0001234\ttetrafibricin\n\n\nDetails:\n\n"
           + _block(1, "BGC0000002", "aculeximycin", 37992.0, "PKS")
           + _block(2, "BGC0001234", "tetrafibricin", 61753.0, "PKS"))
CB_TXT = (f"ClusterBlast scores for {CONTIG}\n\nSignificant hits: \n1. NZ_XXXX\tStreptomyces violaceusniger Tu 4113, complete sequence\n\n\nDetails:\n\n"
          + _block(1, "NZ_XXXX", "Streptomyces violaceusniger Tu 4113, complete sequence", 73038.0, "other"))


def _zip(tmp_path, *, with_kcb: bool):
    z = tmp_path / "as.zip"
    with zipfile.ZipFile(z, "w") as zf:
        if with_kcb:
            zf.writestr(f"knownclusterblast/{CONTIG}_c1.txt", KCB_TXT)
        zf.writestr(f"clusterblast/{CONTIG}_c1.txt", CB_TXT)
    return z


def _bgc():
    """A real BGCRecord, required fields filled with typed blanks (the parser sets many attributes)."""
    import dataclasses, typing
    from mamey.models import BGCRecord
    kw = {}
    for f in dataclasses.fields(BGCRecord):
        if f.default is not dataclasses.MISSING or f.default_factory is not dataclasses.MISSING:  # type: ignore[attr-defined]
            continue
        t = str(f.type)
        kw[f.name] = 0 if "int" in t else 0.0 if "float" in t else [] if "list" in t else {} if "dict" in t else ""
    kw.update(bgc_id="BGC058", contig=CONTIG, region_number=1)
    if "products" in kw: kw["products"] = "T1PKS"
    return BGCRecord(**kw)


def test_rank1_wins_over_numerically_larger_rank2_and_kcb_beats_clusterblast(tmp_path):
    ev = parse_antismash_evidence(_zip(tmp_path, with_kcb=True), json_mode="off")
    b = _bgc(); apply_evidence_to_bgcs([b], ev)
    # defect (1): rank 1's score, not the file maximum
    assert b.kcb_cumulative == 37992.0, b.kcb_cumulative
    assert "aculeximycin" in (b.kcb_top or "").lower() or "BGC0000002" in (b.kcb_top or "")
    assert "tetrafibricin" not in (b.kcb_top or "").lower()
    # defect (2): the 73038 generic ClusterBlast hit never overwrites the KnownClusterBlast score
    assert b.kcb_cumulative != 73038.0
    assert b.kcb_evidence_state == "KNOWNCLUSTERBLAST_OBSERVED"
    assert getattr(b, "needs_manual_kcb_check", "yes") != "yes" or getattr(b, "parse_confidence", "LOW") != "LOW"


def test_clusterblast_only_fallback_is_flagged_not_silent(tmp_path):
    ev = parse_antismash_evidence(_zip(tmp_path, with_kcb=False), json_mode="off")
    b = _bgc(); apply_evidence_to_bgcs([b], ev)
    assert b.kcb_cumulative == 73038.0
    assert b.kcb_evidence_state == "CLUSTERBLAST_FALLBACK_OBSERVED"
    # observed final state (docs/KCB_SCORE_PROVENANCE.md, corrected v9.7.405): the precedence filter
    # sets LOW, the provenance step then names the ClusterBlast subject and lifts it to MEDIUM — never
    # HIGH — with the manual-check flag and the anchor-only ceiling intact.
    assert b.parse_confidence in ("LOW", "MEDIUM") and b.parse_confidence != "HIGH"
    assert b.needs_manual_kcb_check == "yes"
    assert b.denominator_type == "clusterblast best subject cluster"
    assert b.product_claim_ceiling == "source-derived similarity anchor only"


def test_no_matched_source_is_typed_unknown_not_low_similarity(tmp_path):
    z = tmp_path / "empty.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("README.txt", "no clusterblast evidence\n")
    ev = parse_antismash_evidence(z, json_mode="off")
    b = _bgc(); apply_evidence_to_bgcs([b], ev)
    assert b.kcb_evidence_state == "UNKNOWN_KCB"
    assert b.kcb_cumulative is None
    assert b.needs_manual_kcb_check == "yes"

    from mamey.serialize import records_payload
    row = records_payload("SYNTHETIC", [b])["records"][0]
    assert row["kcb_evidence_state"] == "UNKNOWN_KCB"
