import csv
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("workup",ROOT/"tools"/"bgc_functional_logic_workup.py")
MOD=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(MOD)


def write(path,fields,rows,delimiter=","):
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,delimiter=delimiter); w.writeheader(); w.writerows(rows)


def fixture(tmp_path):
    p=tmp_path/"pkg"; p.mkdir(); (p/"manifest.json").write_text("{}\n")
    cds_fields=["strain","contig","region","bgc_id","locus_tag","order","length_aa","product","sec_met_domains","gene_functions"]
    rows=[
      {"strain":"AS-X","contig":"NODE_1_length_900_cov_10.0","region":"region001","bgc_id":"BGC001","locus_tag":"q1","order":1,"length_aa":1100,"product":"NRPS core","sec_met_domains":"AMP-binding; Condensation; PP-binding","gene_functions":"biosynthetic"},
      {"strain":"AS-X","contig":"NODE_1_length_900_cov_10.0","region":"region001","bgc_id":"BGC001","locus_tag":"q2","order":2,"length_aa":400,"product":"cytochrome P450","sec_met_domains":"p450","gene_functions":"biosynthetic-additional"},
      {"strain":"AS-X","contig":"NODE_1_length_900_cov_10.0","region":"region001","bgc_id":"BGC001","locus_tag":"q3","order":3,"length_aa":250,"product":"ABC transporter","sec_met_domains":"ABC_tran","gene_functions":"transport"},
    ]
    write(p/"AS-X_cds_table.csv",cds_fields,rows)
    write(p/"AS-X_3_mibig_per_gene.csv",["bgc_id","query_gene","mibig_accession","subject_gene","pct_identity","pct_coverage_interpretation","blast_score"],[{"bgc_id":"BGC001","query_gene":"q1","mibig_accession":"BGC0000001","subject_gene":"r1","pct_identity":80,"pct_coverage_interpretation":100,"blast_score":500}])
    write(p/"AS-X_2_inventory.csv",["BGC_ID","Boundary","Products"],[{"BGC_ID":"BGC001","Boundary":"Interior","Products":"NRPS"}])
    rank=tmp_path/"rank.tsv"
    write(rank,["complete_identity","definitive_rank_all_bgcs","definitive_rank_within_strain","evidence_tier","standalone_biological_evidence_score_0_100","review_priority_score_0_100","current_antismash_products","boundary","dominant_mibig_accession","dominant_mibig_product","matched_gene_pairs","rggmci_partner_identity","rggmci_confidence","rggmci_subject_tiling_verdict"],[{"complete_identity":"AS-X / NODE_1_length_900_cov_10.0 / region001 / BGC001","definitive_rank_all_bgcs":1,"definitive_rank_within_strain":1,"evidence_tier":"B_SUPPORTED_PARTIAL_ARCHITECTURE","standalone_biological_evidence_score_0_100":60,"review_priority_score_0_100":60,"current_antismash_products":"NRPS","boundary":"Interior","dominant_mibig_accession":"BGC0000001","dominant_mibig_product":"test","matched_gene_pairs":1,"rggmci_partner_identity":"","rggmci_confidence":"","rggmci_subject_tiling_verdict":""}],delimiter="\t")
    return p,rank


def test_unmatched_functional_genes_are_preserved(tmp_path):
    p,rank=fixture(tmp_path); receipt=MOD.analyze([p],rank,tmp_path/"out")
    assert receipt["bgcs"]==1 and receipt["genes"]==3
    assert receipt["functional_genes_without_any_mibig_match"]==2
    assert receipt["functional_genes_without_dominant_reference_match"]==2
    bgc=MOD.read_rows(tmp_path/"out"/"ALL_BGC_FUNCTIONAL_LOGIC_WORKUP.tsv")[0]
    assert bgc["unmatched_tailoring_genes"]=="1"
    assert bgc["unmatched_transport_genes"]=="1"
    assert bgc["architecture_first_pathway_type"]=="NRPS"


def test_role_classifier_separates_maturation_and_tailoring():
    r={"product":"YcaO cyclization enzyme","gene_functions":"biosynthetic","sec_met_domains":"YcaO"}
    tags=MOD.logic_tags(r)
    assert "maturation_cyclization" in tags
    assert MOD.primary_role(r,tags)=="maturation"


def test_duplicate_source_strain_fails(tmp_path):
    p,rank=fixture(tmp_path)
    try: MOD.analyze([p,p],rank,tmp_path/"out")
    except ValueError as exc: assert "multiple packages" in str(exc)
    else: raise AssertionError("expected duplicate package failure")
