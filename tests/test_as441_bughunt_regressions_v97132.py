import csv
from types import SimpleNamespace

from mamey.parsers import _record_contig_id
from mamey.bgc_decomp import _fit_two_model, run_bgc_decomp


def test_spades_locus_contig_id_beats_biopython_version_decimal_loss():
    rec = SimpleNamespace(
        id="NODE_1_length_457136_cov_55.54054",
        name="NODE_1_length_457136_cov_55.054054",
    )
    assert _record_contig_id(rec) == "NODE_1_length_457136_cov_55.054054"


def test_rejected_cross_class_split_explains_gap_threshold():
    genes = [
        {"locus_tag": "a", "cds_start": 0, "cds_end": 1000, "broad_class": "RiPP"},
        {"locus_tag": "b", "cds_start": 6500, "cds_end": 7600, "broad_class": "NRPS"},
    ]
    r = _fit_two_model(genes)
    assert r["two_model_confidence"] == "ONE_MODEL_CONSISTENT"
    assert "gap" in r["null_reason"]


def test_kcb_disconnect_lookup_uses_source_gbk_region_stem(tmp_path):
    cb = tmp_path / "NODE_9_length_227199_cov_57.519373_c2.txt"
    cb.write_text("""ClusterBlast scores for NODE_9_length_227199_cov_57.519373

Significant hits:
1. NZ_TEST Example reference

>>
   1. NZ_TEST
Source: Example reference
Type: terpene
Cumulative BLAST score: 1000
Table of Blast hits
ctg9_131\trefA\t99\t700
ctg9_133\trefB\t99\t300
""", encoding="utf-8")
    gene_csv = tmp_path / "genes.csv"
    with gene_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["bgc_id", "locus_tag", "cds_start", "cds_end", "sec_met_domains"])
        w.writeheader()
        w.writerow({"bgc_id": "BGC047", "locus_tag": "ctg9_131", "cds_start": 0, "cds_end": 1000, "sec_met_domains": "Terpene_synth"})
        w.writerow({"bgc_id": "BGC047", "locus_tag": "ctg9_133", "cds_start": 1100, "cds_end": 2000, "sec_met_domains": "Terpene_synth_C"})
        w.writerow({"bgc_id": "BGC047", "locus_tag": "ctg9_144", "cds_start": 16000, "cds_end": 17000, "sec_met_domains": "PKS_KS"})
    bgc = SimpleNamespace(
        bgc_id="BGC047",
        contig="NODE_9_length_227199_cov_57.519373",
        node_id="NODE_9_length_227199_cov_57",
        source_gbk="NODE_9_length_227199_cov_57.519373.region002.gbk",
        region_number=2,
        start=0,
        end=40000,
        products=["terpene", "PKS"],
        kcb_top="example",
        closest_candidate_kcb_product="example",
    )
    res = run_bgc_decomp([bgc], gene_csv, kcb_dir=tmp_path)
    row = res["rows"][0]
    assert row["two_model_confidence"] == "TWO_MODEL_CANDIDATE"
    assert row["kcb_support_group_a_pct"] == 100.0
    assert row["kcb_support_group_b_pct"] == 0.0
    assert row["kcb_architectural_disconnect"] == "YES"
