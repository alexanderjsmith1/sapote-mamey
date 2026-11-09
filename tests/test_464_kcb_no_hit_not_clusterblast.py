"""A KnownClusterBlast no-hit region is not filled from a genome-wide ClusterBlast hit."""
import zipfile
from mamey import antismash_evidence as ev
from mamey.models import BGCRecord

CONTIG = "NODE_12_length_177743_cov_50.810898"
EMPTY_KCB = (f"ClusterBlast scores for {CONTIG}\n\nTable of genes, locations, strands and annotations of query cluster:\n"
             "ctg12_14\t21025\t21781\t-\t\t\n\n\nSignificant hits: \n\n\nDetails:\n")
CB_HIT = ("ClusterBlast scores for x\n\nSignificant hits: \n1. CP000001\tSome genome\n\n\nDetails:\n\n>>\n"
          "1. CP000001\nSource: Some genome, complete sequence\nType: other\n"
          "Number of proteins with BLAST hits to this cluster: 5\nCumulative BLAST score: 7000.0\n\n")


def _bgc():
    return BGCRecord(bgc_id="BGC004", contig=CONTIG, region_number=1, start=1, end=9000, contig_length=177743,
                     products=["other"], edge_status="Interior", architecture_confidence="A")


def _apply(tmp_path, members):
    z = tmp_path / "in.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    evidence = ev.parse_antismash_evidence(z, json_mode="off")
    bgc = _bgc()
    ev.apply_evidence_to_bgcs([bgc], evidence)
    return bgc, evidence


def test_empty_kcb_file_is_a_typed_no_hit_and_blocks_fallback(tmp_path):
    bgc, evidence = _apply(tmp_path, {f"knownclusterblast/{CONTIG}_c1.txt": EMPTY_KCB,
                                      f"clusterblast/{CONTIG}_c1.txt": CB_HIT})
    assert bgc.kcb_evidence_state == "KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED"
    assert bgc.kcb_cumulative is None and not bgc.kcb_top
    assert bgc.clusterblast_ranked and bgc.clusterblast_ranked[0]["score"] == 7000.0  # organism channel kept
    assert {r["state"] for r in evidence["txt_parse_receipt"]
            if "knownclusterblast" in r["source"]} == {"NO_HITS_TEXT_UNVALIDATED"}


def test_without_any_kcb_file_the_clusterblast_fallback_is_unchanged(tmp_path):
    bgc, _ = _apply(tmp_path, {f"clusterblast/{CONTIG}_c1.txt": CB_HIT})
    assert bgc.kcb_evidence_state == "CLUSTERBLAST_FALLBACK_OBSERVED"
    assert bgc.kcb_cumulative == 7000.0
