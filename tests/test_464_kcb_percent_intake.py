"""KCB percent similarity comes from antiSMASH's JSON ranking, and the cut-offs read it.

antiSMASH 8 knownclusterblast TXT files leave the subject-gene table empty, so the rank-1
percent exists only in the JSON (`knowncluster.results[].ranking[0][1].similarity`).
"""
import json
import zipfile
from types import SimpleNamespace

from mamey import antismash_evidence as ev
from mamey.chatgpt_commands import _claim_ceiling
from mamey.parsers import architecture_grade
from mamey.precision import similarity_band, kcb_pct_value

CONTIG = "NODE_1_length_613749_cov_47.990239"


def _record(region=1, accession="BGC0000853.3", similarity=100, ranking=True):
    rank = [[{"accession": accession, "proteins": []}, {"similarity": similarity, "hits": 4}]] if ranking else []
    return {"id": CONTIG, "name": CONTIG, "modules": {"antismash.modules.clusterblast": {
        "knowncluster": {"results": [{"region_number": region, "total_hits": len(rank), "ranking": rank}]}}}}


def _txt(accession="BGC0000853.3"):
    return ("ClusterBlast scores for x\n\nSignificant hits: \n"
            f"1. {accession}\tectoine\n\n\nDetails:\n\n>>\n1. {accession}\nSource: ectoine\n"
            "Type: other:other\nNumber of proteins with BLAST hits to this cluster: 4\n"
            "Cumulative BLAST score: 1211.0\n\n")


def _zip(path, records, txt_accession="BGC0000853.3"):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("genome.json", json.dumps({"records": records}))
        zf.writestr(f"knownclusterblast/{CONTIG}_c1.txt", _txt(txt_accession))
    return path


def _bgc():
    return SimpleNamespace(bgc_id="BGC001", contig=CONTIG, region_number=1, products=["ectoine"],
                           mibig_ranked=[], clusterblast_ranked=[], kcb_top=None)


def _apply(tmp_path, records, txt_accession="BGC0000853.3", want_tigrfam=True):
    path = _zip(tmp_path / "in.zip", records, txt_accession)
    evidence = ev.parse_antismash_evidence(path, json_mode="off", want_tigrfam=want_tigrfam)
    bgc = _bgc()
    ev.apply_evidence_to_bgcs([bgc], evidence)
    return bgc


def test_handler_keys_rows_like_the_txt_records():
    out = {}
    ev._kcb_similarity_from_rec(_record(region=2, similarity=20), "genome.json", out)
    assert out == {f"{CONTIG}_c2": [{"source": "genome.json", "region_number": 2,
                                     "accession": "BGC0000853.3", "similarity": 20}]}


def test_percent_observed_when_json_and_txt_name_the_same_hit(tmp_path):
    bgc = _apply(tmp_path, [_record(similarity=66)])
    assert (bgc.kcb_similarity_pct, bgc.kcb_similarity_state) == (66.0, "PCT_OBSERVED")
    assert bgc.kcb_cumulative == 1211.0   # the score is kept, separately


def test_percent_refused_when_comparators_differ(tmp_path):
    bgc = _apply(tmp_path, [_record(accession="BGC0002052.3")])
    assert (bgc.kcb_similarity_pct, bgc.kcb_similarity_state) == (None, "PCT_COMPARATOR_MISMATCH")


def test_percent_not_read_without_a_record_pass(tmp_path):
    bgc = _apply(tmp_path, [_record()], want_tigrfam=False)
    assert (bgc.kcb_similarity_pct, bgc.kcb_similarity_state) == (None, "PCT_NOT_READ")


def test_out_of_range_percent_is_invalid(tmp_path):
    bgc = _apply(tmp_path, [_record(similarity=150)])
    assert (bgc.kcb_similarity_pct, bgc.kcb_similarity_state) == (None, "PCT_INVALID")


def test_empty_ranking_is_no_ranked_hit(tmp_path):
    bgc = _apply(tmp_path, [_record(ranking=False)])
    assert (bgc.kcb_similarity_pct, bgc.kcb_similarity_state) == (None, "PCT_NO_RANKED_HIT")


def test_two_json_files_that_disagree_hold(tmp_path):
    path = tmp_path / "in.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("a.json", json.dumps({"records": [_record(similarity=90)]}))
        zf.writestr("b.json", json.dumps({"records": [_record(similarity=10)]}))
        zf.writestr(f"knownclusterblast/{CONTIG}_c1.txt", _txt())
    evidence = ev.parse_antismash_evidence(path, json_mode="off", want_tigrfam=True)
    bgc = _bgc()
    ev.apply_evidence_to_bgcs([bgc], evidence)
    assert (bgc.kcb_similarity_pct, bgc.kcb_similarity_state) == (None, "PCT_SOURCE_CONFLICT")


def test_pct_value_rejects_scores_and_blanks():
    assert kcb_pct_value(37992.0) is None
    assert kcb_pct_value("") is None
    assert kcb_pct_value("55") == 55.0
    assert similarity_band(None) == "unresolved"


def test_architecture_reads_percent_not_score():
    # Interior, no core annotation: only strong KCB support lifts it to B.
    grade_pct, _ = architecture_grade("Interior", ["other"], 20000, 80)
    grade_score, _ = architecture_grade("Interior", ["other"], 20000, 50000)
    assert grade_pct == "B"
    assert grade_score == "E"


def test_claim_ceiling_family_needs_moderate_percent():
    row = {"Products": "T1PKS"}
    base = {"kcb_cumulative": 9000, "kcb_protein_hits": 4, "clusterblast_top": "T1PKS",
            "products": ["T1PKS"], "architecture_confidence": "B"}
    assert _claim_ceiling(row, {**base, "kcb_similarity_pct": 45}) == "candidate family similarity"
    assert _claim_ceiling(row, {**base, "kcb_similarity_pct": 30}) == "source-derived similarity"
    assert _claim_ceiling(row, base) == "source-derived similarity"
