import csv
import importlib.util
import io
import json
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("definitive_bgc_ranker", ROOT / "tools" / "definitive_bgc_ranker.py")
MOD = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)


def write_csv(path, fields, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def read_tsv(path):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def mibig_archive(path):
    features = []
    kinds = ["biosynthetic", "biosynthetic", "biosynthetic-additional", "transport"]
    for i, kind in enumerate(kinds, 1):
        features.append(f"     CDS             {i*100}..{i*100+90}\n                     /locus_tag=\"REF{i}\"\n                     /protein_id=\"PROT{i}.1\"\n                     /gene_kind=\"{kind}\"\n                     /product=\"enzyme {i}\"")
    text = "LOCUS       BGC0000001 500 bp DNA linear\nFEATURES             Location/Qualifiers\n" + "\n".join(features) + "\nORIGIN\n        1 " + "a"*500 + "\n//\n"
    with tarfile.open(path, "w:gz") as tf:
        data = text.encode(); info = tarfile.TarInfo("mibig_gbk_4.0/BGC0000001.gbk"); info.size = len(data)
        tf.addfile(info, io.BytesIO(data))


def package(tmp_path):
    p = tmp_path / "package"; p.mkdir(); (p / "manifest.json").write_text("{}\n")
    cds_fields = ["strain", "contig", "region", "bgc_id", "locus_tag", "order", "product", "gene_functions"]
    write_csv(p / "AS-X_cds_table.csv", cds_fields, [
        {"strain":"AS-X","contig":"NODE_1_length_1000_cov_10.0","region":"region001","bgc_id":"BGC001","locus_tag":f"q{i}","order":i,"product":"enzyme","gene_functions":"biosynthetic"}
        for i in range(1, 5)])
    hit_fields = ["bgc_id","query_gene","subject_gene","mibig_accession","mibig_compound","pct_identity","pct_coverage_interpretation","blast_score"]
    write_csv(p / "AS-X_3_mibig_per_gene.csv", hit_fields, [
        {"bgc_id":"BGC001","query_gene":f"q{i}","subject_gene":f"PROT{i}.1","mibig_accession":"BGC0000001.4","mibig_compound":"test product","pct_identity":90,"pct_coverage_interpretation":100,"blast_score":500-i}
        for i in range(1, 5)])
    write_csv(p / "AS-X_2_inventory.csv", ["BGC_ID","Boundary","Products"], [{"BGC_ID":"BGC001","Boundary":"Interior","Products":"RiPP"}])
    write_csv(p / "AS-X_4A_RGGMCI_ranked_pairs.csv", ["pair","bgc_a","bgc_b","rggmci_score","rggmci_confidence","subject_tiling_verdict"], [])
    return p


def test_reciprocal_core_weighted_rank(tmp_path):
    p = package(tmp_path); archive = tmp_path / "mibig.tar.gz"; mibig_archive(archive)
    receipt = MOD.analyze([p], archive, tmp_path / "out")
    rows = read_tsv(tmp_path / "out" / "ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv")
    assert receipt["bgcs"] == 1 and receipt["mibig_rosters_resolved"] == 1
    assert rows[0]["complete_identity"] == "AS-X / NODE_1_length_1000_cov_10.0 / region001 / BGC001"
    assert rows[0]["matched_gene_pairs"] == "4"
    assert rows[0]["reciprocal_coverage_f1"] == "1.0"
    assert rows[0]["reference_core_completeness"] == "1.0"
    assert rows[0]["evidence_tier"] == "A_STRONG_PATHWAY_FAMILY_ARCHITECTURE"


def test_boundary_and_rggmci_are_separate_channels(tmp_path):
    p = package(tmp_path)
    inv = MOD.read_csv(p / "AS-X_2_inventory.csv"); inv[0]["Boundary"] = "Full-contig"
    write_csv(p / "AS-X_2_inventory.csv", ["BGC_ID","Boundary","Products"], inv)
    archive = tmp_path / "mibig.tar.gz"; mibig_archive(archive)
    MOD.analyze([p], archive, tmp_path / "out")
    row = read_tsv(tmp_path / "out" / "ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv")[0]
    assert row["evidence_tier"] == "B_SUPPORTED_PARTIAL_ARCHITECTURE"
    assert row["boundary_penalty"] == "12"
    assert row["rggmci_routing_bonus"] == "0"


def test_greedy_pairing_is_one_to_one():
    roster = {"id_map": {"REF": {"order":1,"primary_id":"REF","gene_kind":"biosynthetic","core_weight":3.0}}}
    hits = [
        {"query_gene":"q1","subject_gene":"REF","pct_identity":"90","pct_coverage_interpretation":"100","blast_score":"100"},
        {"query_gene":"q2","subject_gene":"REF","pct_identity":"80","pct_coverage_interpretation":"100","blast_score":"90"},
    ]
    assert len(MOD.greedy_pairs(hits, roster)) == 1


def test_rg_gmci_high_genuine_can_form_linked_tier():
    m = {"matched_gene_pairs":0,"reciprocal_coverage_f1":0,"reference_core_completeness":0,
         "median_effective_similarity":0,"orientation_aware_order_concordance":None,
         "boundary":"Full-contig","clear_specific_gene_count":0,"rggmci_genuine_high":True}
    assert MOD.evidence_tier(m) == "B_SUPPORTED_LINKED_FRAGMENT_CANDIDATE"
