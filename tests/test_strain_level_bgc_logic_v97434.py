import csv
import importlib.util
from pathlib import Path

TOOL=Path(__file__).parents[1]/"tools"/"strain_level_bgc_logic.py"
spec=importlib.util.spec_from_file_location("strain_level_bgc_logic",TOOL)
mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)


def test_full_contig_generic_pks_receives_extra_fragment_penalty():
    base={"standalone_biological_evidence_score_0_100":"60","functional_reference_relation":"ARCHITECTURE_SUPPORT_PRESENT","boundary":"Full-contig","evidence_tier":"B_SUPPORTED_PARTIAL_ARCHITECTURE","genes_matching_dominant_reference":"2","total_cds":"20","current_antismash_products":"PKS; T1PKS","architecture_first_pathway_type":"cis-AT T1PKS"}
    score,band,flag,fraction=mod.score_row(base)
    assert score==37.0
    assert band=="P3_PROVISIONAL_CAPACITY"
    assert "GENERIC_ASSEMBLY_LINE_FULL_CONTIG" in flag
    assert "SPARSE_REFERENCE_GENE_SUPPORT" in flag
    assert "LOW_REFERENCE_HIT_FRACTION" in flag
    assert fraction==0.1


def test_interior_corroborated_family_retains_named_like_family():
    row={"dominant_mibig_product":"example compound","functional_reference_relation":"ARCHITECTURE_CORROBORATES_REFERENCE","architecture_first_pathway_type":"lanthipeptide RiPP","current_antismash_products":"RiPP"}
    assert mod.product_label(row)=="example compound-like family (architecture corroborated)"


def test_build_writes_html_and_complete_identity(tmp_path):
    identity="AS-X / NODE_1_length_50000_cov_10 / region001 / BGC001"
    row={
      "complete_identity":identity,"standalone_biological_evidence_score_0_100":"70","functional_reference_relation":"ARCHITECTURE_CORROBORATES_REFERENCE","boundary":"Interior","evidence_tier":"A_STRONG_PATHWAY_FAMILY_ARCHITECTURE","genes_matching_dominant_reference":"5","total_cds":"6","current_antismash_products":"RiPP","architecture_first_pathway_type":"lanthipeptide RiPP","architecture_first_confidence":"HIGH","dominant_mibig_product":"example","functional_genes_without_any_mibig_match":"1","functional_logic_summary":"logic","rggmci_confidence":"","rggmci_partner_identity":"","decisive_review_question":"question","definitive_rank_within_strain":"1"
    }
    src=tmp_path/"bgc.tsv"
    with src.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(row),delimiter="\t"); w.writeheader(); w.writerow(row)
    receipt=mod.build(src,tmp_path/"out")
    assert receipt["strains"]==1 and receipt["bgcs"]==1
    report=(tmp_path/"out"/"PER_STRAIN"/"AS-X"/"REPORT.html").read_text()
    assert identity in report
    assert (tmp_path/"out"/"PER_STRAIN"/"AS-X"/"REPORT.md").exists()
    assert len(list((tmp_path/"out"/"PER_STRAIN"/"AS-X"/"LOCUS_MAPS").glob("*.svg")))==1
    assert (tmp_path/"out"/"CROSS_STRAIN_BGC_COMPARISON.md").exists()
    assert (tmp_path/"out"/"CROSS_STRAIN_BGC_COMPARISON.tsv").exists()
    assert (tmp_path/"out"/"INDEX.html").exists()


def test_high_rggmci_pair_is_one_adjacent_review_unit(tmp_path):
    a="AS-441 / NODE_69_length_9799_cov_77.372660 / region001 / BGC042"
    b="AS-441 / NODE_28_length_73283_cov_62.230719 / region002 / BGC018"
    rows=[]
    for rank,(identity,partner) in enumerate(((a,b),(b,a)),1):
        rows.append({
          "complete_identity":identity,"standalone_biological_evidence_score_0_100":str(80-rank),
          "functional_reference_relation":"ARCHITECTURE_SUPPORT_PRESENT","boundary":"Full-contig",
          "evidence_tier":"B_SUPPORTED_PARTIAL_ARCHITECTURE","genes_matching_dominant_reference":"9",
          "total_cds":"9","current_antismash_products":"RiPP","architecture_first_pathway_type":"LAP",
          "architecture_first_confidence":"MEDIUM","dominant_mibig_product":"bottromycin D",
          "functional_genes_without_any_mibig_match":"0","functional_logic_summary":"complementary bottromycin logic",
          "rggmci_confidence":"HIGH_RG_GMCI_RESCUE","rggmci_partner_identity":partner,
          "decisive_review_question":"confirm split pathway","definitive_rank_within_strain":str(rank)
        })
    src=tmp_path/"bgc.tsv"
    with src.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter="\t"); w.writeheader(); w.writerows(rows)
    mod.build(src,tmp_path/"out")
    html_report=(tmp_path/"out"/"PER_STRAIN"/"AS-441"/"REPORT.html").read_text()
    md_report=(tmp_path/"out"/"PER_STRAIN"/"AS-441"/"REPORT.md").read_text()
    assert html_report.count("HIGH RG-GMCI rescue unit")==1
    linked=html_report.split("HIGH RG-GMCI rescue unit",1)[1].split("</section>",1)[0]
    assert a in linked and b in linked
    assert md_report.count("HIGH RG-GMCI Rescue")==1
    assert a in md_report and b in md_report
