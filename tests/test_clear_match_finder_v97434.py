import csv
import importlib.util
import json
from pathlib import Path

MODULE=Path(__file__).parents[1]/"tools"/"clear_match_finder.py"
spec=importlib.util.spec_from_file_location("clear_match_finder",MODULE)
cm=importlib.util.module_from_spec(spec); spec.loader.exec_module(cm)

def write_csv(path, fields, rows):
    with path.open("w",newline="") as handle:
        w=csv.DictWriter(handle,fields); w.writeheader(); w.writerows(rows)

def fixture(tmp_path):
    pkg=tmp_path/"runs"/"TEST-1"/"package"; pkg.mkdir(parents=True)
    (pkg/"manifest.json").write_text(json.dumps({"strain_id":"TEST-1","package_status":"MAMEY_COMPLETE"}))
    cds_fields=["strain","contig","region","bgc_id","locus_tag","order","product","sec_met_domains","gene_functions"]
    write_csv(pkg/"TEST-1_cds_table.csv",cds_fields,[
        {"strain":"TEST-1","contig":"NODE_1_length_1000_cov_10.0","region":"region001","bgc_id":"BGC001","locus_tag":"g1","order":1,"product":"lasso cyclase","sec_met_domains":"Asn_synthase","gene_functions":"biosynthetic"},
        {"strain":"TEST-1","contig":"NODE_1_length_1000_cov_10.0","region":"region001","bgc_id":"BGC001","locus_tag":"g2","order":2,"product":"hypothetical","sec_met_domains":"","gene_functions":""},
        {"strain":"TEST-1","contig":"NODE_1_length_1000_cov_10.0","region":"region001","bgc_id":"BGC001","locus_tag":"g3","order":3,"product":"hypothetical","sec_met_domains":"","gene_functions":""},
    ])
    hit_fields=["bgc_id","query_gene","subject_gene","mibig_accession","mibig_compound","reference_type","pct_identity","pct_coverage","pct_coverage_interpretation","coverage_qc_flag","blast_score","evalue","reference_rank","source_file"]
    write_csv(pkg/"TEST-1_3_mibig_per_gene.csv",hit_fields,[
        {"bgc_id":"BGC001","query_gene":"g1","subject_gene":"top","mibig_accession":"BGC0001634","mibig_compound":"keywimysin","reference_type":"ribosomal:RiPP","pct_identity":97,"pct_coverage":100,"pct_coverage_interpretation":100,"coverage_qc_flag":"WITHIN_EXPECTED_RANGE","blast_score":1280,"evalue":0,"reference_rank":1,"source_file":"fixture.txt"},
        {"bgc_id":"BGC001","query_gene":"g1","subject_gene":"same_cluster_weaker","mibig_accession":"BGC0001634","mibig_compound":"keywimysin","reference_type":"ribosomal:RiPP","pct_identity":95,"pct_coverage":99,"pct_coverage_interpretation":99,"coverage_qc_flag":"WITHIN_EXPECTED_RANGE","blast_score":1200,"evalue":0,"reference_rank":1,"source_file":"fixture.txt"},
        {"bgc_id":"BGC001","query_gene":"g1","subject_gene":"runner","mibig_accession":"BGC0000578","mibig_compound":"SRO15-2005","reference_type":"ribosomal:unmodified","pct_identity":89,"pct_coverage":46.3,"pct_coverage_interpretation":46.3,"coverage_qc_flag":"WITHIN_EXPECTED_RANGE","blast_score":602,"evalue":"1.3e-213","reference_rank":2,"source_file":"fixture.txt"},
        {"bgc_id":"BGC001","query_gene":"g2","subject_gene":"top2","mibig_accession":"BGC0001634","mibig_compound":"keywimysin","reference_type":"ribosomal:RiPP","pct_identity":80,"pct_coverage":90,"pct_coverage_interpretation":90,"coverage_qc_flag":"WITHIN_EXPECTED_RANGE","blast_score":500,"evalue":"1e-100","reference_rank":1,"source_file":"fixture.txt"},
        {"bgc_id":"BGC001","query_gene":"g2","subject_gene":"runner2","mibig_accession":"BGC0000578","mibig_compound":"SRO15-2005","reference_type":"ribosomal:unmodified","pct_identity":60,"pct_coverage":70,"pct_coverage_interpretation":70,"coverage_qc_flag":"WITHIN_EXPECTED_RANGE","blast_score":250,"evalue":"1e-50","reference_rank":2,"source_file":"fixture.txt"},
    ])
    inv_fields=["BGC_ID","Boundary","Products"]
    write_csv(pkg/"TEST-1_2_inventory.csv",inv_fields,[{"BGC_ID":"BGC001","Boundary":"Interior","Products":"RiPP; lassopeptide"}])
    return pkg

def test_clear_match_reproduces_top_vs_distinct_second_and_keeps_no_hit(tmp_path):
    pkg=fixture(tmp_path); out=tmp_path/"out"
    receipt=cm.analyze([pkg],out)
    rows=list(csv.DictReader((out/"ALL_GENE_TOP_VS_SECOND_MIBIG.tsv").open(),delimiter="\t"))
    g1=next(r for r in rows if r["query_gene"]=="g1"); g3=next(r for r in rows if r["query_gene"]=="g3")
    assert g1["complete_identity"]=="TEST-1 / NODE_1_length_1000_cov_10.0 / region001 / BGC001"
    assert g1["top_mibig_accession"]=="BGC0001634"
    assert g1["second_mibig_accession"]=="BGC0000578"
    assert g1["match_band"]=="CLEAR_SPECIFIC_HIGH"
    assert float(g1["top_minus_second_identity_x_coverage_points"])==55.79
    assert float(g1["top_to_second_blast_score_ratio"])==2.126
    assert g3["match_band"]=="NO_MIBIG_HIT_RECORDED"
    assert receipt["cds_rows"]==3 and receipt["raw_mibig_hit_rows"]==5

def test_recursive_discovery_and_bgc_rank(tmp_path):
    pkg=fixture(tmp_path); found=cm.discover_packages([],tmp_path/"runs")
    assert found==[pkg.resolve()]
    out=tmp_path/"out"; cm.analyze(found,out)
    row=next(csv.DictReader((out/"ALL_BGC_CLEAR_MATCH_RANK.tsv").open(),delimiter="\t"))
    assert row["bgc_clear_match_rank"]=="1"
    assert row["interior_only_rank"]=="1"
    assert row["clear_specific_high_genes"]=="2"
    assert row["dominant_top_mibig_accession"]=="BGC0001634"
    assert (out/"CLEAR_MATCH_RECEIPT.json").is_file()
    top2=next(csv.DictReader((out/"ALL_BGC_TOP_2_GENE_MATCH_RANK.tsv").open(),delimiter="\t"))
    top3=next(csv.DictReader((out/"ALL_BGC_TOP_3_GENE_MATCH_RANK.tsv").open(),delimiter="\t"))
    assert top2["top_2_gene_rank_all_bgcs"]=="1" and top2["top_2_rank_eligible"]=="YES"
    assert top3["top_3_gene_rank_all_bgcs"]=="" and top3["top_3_rank_eligible"]=="NO"
    strain_dir=out/"PER_STRAIN"/"TEST-1"
    assert (strain_dir/"BGC_CLEAR_MATCH_RANK.tsv").is_file()
    assert (strain_dir/"BGC_TOP_2_GENE_MATCH_RANK.tsv").is_file()
    assert (strain_dir/"BGC_TOP_3_GENE_MATCH_RANK.tsv").is_file()
    counts=next(csv.DictReader((out/"ALL_BGC_MATCHING_GENE_COUNT_RANK.tsv").open(),delimiter="\t"))
    assert counts["matching_gene_count_rank_all_bgcs"]=="1"
    assert counts["matching_gene_percentage_rank_all_bgcs"]=="1"
    assert counts["dominant_cluster_gene_count_rank_all_bgcs"]=="1"
    assert counts["dominant_cluster_gene_percentage_rank_all_bgcs"]=="1"
    assert counts["genes_with_any_mibig_match"]=="2"
    assert counts["genes_matching_dominant_mibig_cluster"]=="2"
    fraction=next(csv.DictReader((out/"ALL_BGC_HIT_FRACTION_RANK.tsv").open(),delimiter="\t"))
    assert fraction["matching_gene_percentage_rank_all_bgcs"]=="1"
    assert abs(float(fraction["fraction_cds_with_any_mibig_match"])-2/3)<0.0001
    per_counts=next(csv.DictReader((strain_dir/"BGC_MATCHING_GENE_COUNT_RANK.tsv").open(),delimiter="\t"))
    assert per_counts["matching_gene_count_rank_within_strain"]=="1"
    assert per_counts["matching_gene_percentage_rank_within_strain"]=="1"
    assert per_counts["dominant_cluster_gene_count_rank_within_strain"]=="1"
    assert per_counts["dominant_cluster_gene_percentage_rank_within_strain"]=="1"
    assert (strain_dir/"BGC_HIT_FRACTION_RANK.tsv").is_file()
