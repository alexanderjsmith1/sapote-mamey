"""Unexecuted real template batch controls: no partial canonical census on parse failure."""
import json
import pytest
from mamey import modeb_template_emitter as m

@pytest.mark.parametrize("fault",["bad_json","nonobject","bad_cds_row","mixed_start_types","valid"])
def test_batch_commits_only_complete_gene_context_source(tmp_path,fault):
    pkg=tmp_path/"package";pkg.mkdir()
    (pkg/"manifest_short.json").write_text(json.dumps(dict(strain_id="SYNTHETIC")))
    (pkg/"SYNTHETIC_4_triage_board.csv").write_text("Strain,BGC_ID,Contig,Node_ID,antiSMASH_Region,Rank\nSYNTHETIC,BGC001,contigA,contigA,region001,1\n")
    gene=dict(locus_tag="gene1",start=1,end=90,strand=1,aa_length=30,product="source annotation",gene_kind="biosynthetic",sec_met_domains=[])
    prefix=json.dumps(dict(bgc_id="BGC001",cds=[gene]))+"\n"
    suffix={"bad_json":"{bad JSON\n","nonobject":"null\n","bad_cds_row":json.dumps(dict(bgc_id="BGC001",cds=[1]))+"\n",
       "mixed_start_types":json.dumps(dict(bgc_id="BGC001",cds=[dict(gene,locus_tag="gene2",start="100")]))+"\n",
       "valid":json.dumps(dict(bgc_id="BGC001",cds=[dict(gene,locus_tag="gene2",start=100)]))+"\n"}[fault]
    canonical=pkg/"SYNTHETIC_gene_context.jsonl";canonical.write_text(prefix+suffix)
    fallback=pkg/"gene_context.jsonl";fallback.write_text(prefix)
    original=canonical.read_bytes(),fallback.read_bytes()
    result=m.emit_batch(pkg)
    assert (canonical.read_bytes(),fallback.read_bytes())==original
    if fault=="valid":
        assert result["emitted"]==["BGC001"]
        text=next((pkg/"mode_b_templates").glob("*_template.md")).read_text()
        assert "2 CDS in locus" in text
    else:
        assert result["emitted"]==[]
        assert "GENE_CONTEXT_SOURCE_INVALID" in result["skipped"]["BGC001"]
        assert not list((pkg/"mode_b_templates").glob("*_template.md"))
