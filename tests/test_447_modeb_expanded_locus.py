"""Synthetic interpretation tests: complete neighbours, source drift and rivals."""
import hashlib
import json
import re

import pytest

from tests.test_447_modeb_gap_rescue_reader import CORE, PARTNER, source, write_table
from mamey.modeb_gap_rescue import load_gap_rescue
from mamey.modeb_locus_scope import (build_scope, canonical_identity, findings, marker,
                                   render_scope, _digest)
from mamey import modeb_template_emitter as emitter
from mamey.modeb_current50_v2 import load_contract, v2_findings


def write_assembly(data):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from collections import defaultdict
    groups=defaultdict(list)
    for g in data["genes"]: groups[g["contig"]].append(g)
    records=[]
    for contig, genes in groups.items():
        r=SeqRecord(Seq("N"*genes[0]["contig_length_bp"]),id=contig,name=contig,description="synthetic offline source")
        r.annotations["molecule_type"]="DNA"
        r.features=[SeqFeature(FeatureLocation(g["start_1based"]-1,g["end_1based"],strand=g["strand"]),type="CDS",qualifiers={"locus_tag":[g["locus_tag"]],"translation":[g["aa_sequence"]]}) for g in genes]
        records.append(r)
    source=data["assembly_source"]
    SeqIO.write(records,source["path"],"genbank")
    from pathlib import Path
    source["sha256"]=hashlib.sha256(Path(source["path"]).read_bytes()).hexdigest()


def inputs(tmp_path):
    rescue, _ = source(tmp_path)
    assembly = tmp_path / "assembly.gbk"
    assembly.write_text("synthetic pinned source")
    def gene(tag, contig, lo, hi, seq, identity):
        return dict(locus_tag=tag, contig=contig, start_1based=lo, end_1based=hi,
                    strand=1, contig_length_bp=1000, aa_sequence=seq, aa_length=len(seq),
                    aa_sha256=hashlib.sha256(seq.encode()).hexdigest(), identities=[identity])
    genes = [gene("a_1", CORE.split(" / ")[1], 10, 30, "ACD", CORE),
             gene("b_1", PARTNER.split(" / ")[1], 100, 120, "EFG", PARTNER),
             gene("b_2", PARTNER.split(" / ")[1], 140, 220, "HIK", PARTNER),
             gene("b_3", PARTNER.split(" / ")[1], 700, 720, "LMN", PARTNER)]
    inv = tmp_path / "inventory.json"
    data=dict(schema="modeb_locus_inventory_v1", strain="PUBLIC-1",
              assembly_source=dict(path=str(assembly)), genes=genes)
    write_assembly(data)
    inv.write_text(json.dumps(data))
    return rescue, inv, genes


def scope(tmp_path, window=50):
    rescue, inv, genes = inputs(tmp_path)
    return build_scope(inv, load_gap_rescue(rescue, CORE), [dict(locus_tag="a_1", start=10,end=30,aa_length=3)],window), rescue, inv, genes


def card(s):
    return marker(s) + "\n" + "\n".join(f"## §{n} Example\n{render_scope(s,n)}\n" for n in (3,26,50))


def test_neighbour_is_complete_context_not_an_anchor(tmp_path):
    s, _, _, _ = scope(tmp_path)
    assert s["state"] == "BOUND" and s["selected_cds"] == 3 and s["selected_contigs"] == 2
    assert s["intervals"][1]["end_1based"] == 220
    assert {g["locus_tag"]:g["scope_role"] for g in s["genes"]} == dict(a_1="CORE",b_1="SUPPORTED_ANCHOR",b_2="NEIGHBOUR_CONTEXT")
    assert s["physical_joins"] == 0 and findings(card(s)) == []


def test_effective_demote_removes_primary_scope_but_retains_alternative(tmp_path):
    _, d, inv, _ = scope(tmp_path)
    adjud = tmp_path / "explicit.tsv"
    write_table(adjud,[dict(reference_gene="tailor",candidate_locus="b_1",verdict="PARALOG_FAMILY")])
    r=load_gap_rescue(d,CORE,gene_adjudication_tsv=adjud)
    s=build_scope(inv,r,[dict(locus_tag="a_1")],50)
    assert s["selected_cds"]==1 and s["alternatives"][0]["ruling"]=="PARALOG_FAMILY"
    assert r["rows"][1]["run_partner_verdict"]=="SUPPORTED"


@pytest.mark.parametrize("fault",["aa_hash","strain","location","duplicate","geometry","package_geometry","core_missing"])
def test_binding_fault_is_hold(tmp_path,fault):
    _, d, inv, genes=scope(tmp_path)
    data=json.loads(inv.read_text());core=[dict(locus_tag="a_1",start=10)]
    if fault=="aa_hash":data["genes"][1]["aa_sha256"]="0"*64
    elif fault=="strain":data["strain"]="OTHER"
    elif fault=="location":data["genes"][1]["locus_tag"]="wrong_tag"
    elif fault=="duplicate":data["genes"].append(data["genes"][1])
    elif fault=="geometry":data["genes"][1]["end_1based"]=1001
    elif fault=="package_geometry":core[0]["start"]=11
    elif fault=="core_missing":core=[]
    inv.write_text(json.dumps(data))
    assert build_scope(inv,load_gap_rescue(d,CORE),core,50)["state"]=="HOLD"


@pytest.mark.parametrize("window",[-1,True,1.5])
def test_invalid_window(tmp_path,window):
    s,*_=scope(tmp_path,window)
    assert s["state"]=="HOLD"


def test_visible_gene_drop_is_rejected(tmp_path):
    s,*_=scope(tmp_path)
    md=card(s)
    md="\n".join(x for x in md.splitlines() if not x.startswith("| b_2;"))
    assert any(f["code"]=="LOCUS_SCOPE_GENE_DROPPED" for f in findings(md))


def test_hidden_gene_drop_and_rehash_is_rejected(tmp_path):
    s,*_=scope(tmp_path)
    s["genes"]=[g for g in s["genes"] if g["locus_tag"]!="b_2"]
    s["selected_cds"]=2;s["selected_unique_aa_sequences"]=2
    s.pop("scope_sha256");s["scope_sha256"]=_digest(s)
    assert findings(card(s))[0]["code"]=="LOCUS_SCOPE_SOURCE_INVALID"


def test_source_change_is_rejected(tmp_path):
    s,_,inv,_=scope(tmp_path)
    inv.write_text(inv.read_text()+"\n")
    assert "source changed" in findings(card(s))[0]["message"]


def test_required_marker_cannot_disappear_and_legacy_is_unchanged():
    assert findings("<!-- MODEB_EXPANDED_LOCUS_REQUIRED -->")[0]["code"]=="LOCUS_SCOPE_MISSING"
    assert findings("ordinary legacy card") == []
    assert canonical_identity("PUBLIC-1 / X (no antiSMASH region)") == "PUBLIC-1 / X / no antiSMASH region / no BGC alias"


def test_emitter_routes_scope_into_all_affected_sections(tmp_path,monkeypatch):
    d,inv,_=inputs(tmp_path)
    monkeypatch.setattr(emitter,"_bgc_facts",lambda *_:dict(strain_id="PUBLIC-1",contig=CORE.split(" / ")[1],
        node="CONTIG_A",region="region001",bgc_id="BGC001",gene_rows=[dict(locus_tag="a_1",start=10,end=30,aa_length=3)]))
    md=emitter.emit_card_template(tmp_path,"BGC001",contract=load_contract("current50_v2"),
        sources=dict(gap_rescue_dir=str(d),rescue_locus_inventory=str(inv)))
    assert len(re.findall(r"^## §\d+ ",md,re.M))==50
    assert findings(md)==[]
    s50=md.split("## §50 ")[1]
    matrix=s50.split("#### Complete named-match, channel-separated table")[1]
    for tag in ("a_1","b_1","b_2","b_3"):
        assert f"`{tag}`" in matrix
    for n in (3,5,6,7,8,10,19,22,26,36,37,38,43,44,50):
        body=md.split(f"## §{n} ")[1].split("\n## §")[0]
        assert "Expanded-locus interpretation scope" in body


def test_explicit_adjudication_contig_mismatch_is_hold(tmp_path):
    _,d,_,_=scope(tmp_path)
    a=tmp_path/"wrong.tsv"
    write_table(a,[dict(reference_gene="tailor",candidate_locus="b_1",verdict="SUPPORTED",contig="OTHER")])
    assert load_gap_rescue(d,CORE,gene_adjudication_tsv=a)["state"]=="HOLD"


def test_cli_preserves_expansion_sources_all_routes():
    from mamey.cli import build_parser
    flags=["--rescue-locus-inventory","i.json","--rescue-gene-adjudication-tsv","a.tsv"]
    for route in (["emit-modeb-template","--package","p"],["modeb-round","--package","p"],
                  ["deliverable-queue","--runs-dir","r","--out-root","o"]):
        args=build_parser().parse_args(route+flags)
        assert emitter.source_argv(emitter.sources_from_args(args))[-4:]==[flags[2],flags[3],flags[0],flags[1]]


def test_separated_anchor_windows_do_not_include_remote_middle_genes(tmp_path):
    _,d,inv,_=scope(tmp_path)
    data=json.loads(inv.read_text())
    g=dict(data["genes"][3]);g["locus_tag"]="b_4";g["start_1based"]=400;g["end_1based"]=420
    data["genes"].append(g);write_assembly(data);inv.write_text(json.dumps(data))
    r=load_gap_rescue(d,CORE)
    extra=dict(r["rows"][1]);extra.update(name="other",best_locus="b_3",protein_sha256=data["genes"][3]["aa_sha256"])
    r["rows"].append(extra)
    s=build_scope(inv,r,[dict(locus_tag="a_1")],50)
    assert s["state"]=="BOUND" and s["selected_cds"]==4
    assert len(s["intervals"])==3 and "b_4" not in {g["locus_tag"] for g in s["genes"]}


def test_sequence_duplicate_at_another_location_is_not_interchangeable(tmp_path):
    _,d,inv,_=scope(tmp_path)
    data=json.loads(inv.read_text());g=dict(data["genes"][1])
    g.update(locus_tag="other",contig="OTHER",identities=["PUBLIC-1 / OTHER / no antiSMASH region / no BGC alias"])
    data["genes"].append(g);data["genes"][1]["locus_tag"]="renamed"
    inv.write_text(json.dumps(data))
    assert build_scope(inv,load_gap_rescue(d,CORE),[dict(locus_tag="a_1")],50)["state"]=="HOLD"


def test_inventory_exporter_preserves_literal_locus_name(tmp_path):
    import importlib.util
    from pathlib import Path
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from Bio import SeqIO
    tool=Path(__file__).parents[1]/"tools/build_modeb_locus_inventory.py"
    spec=importlib.util.spec_from_file_location("inventory_exporter",tool)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    rawid="NODE_121_length_100_cov_69.24320";literal="NODE_121_length_100_cov_69.024320"
    record=SeqRecord(Seq("ATG"*33+"A"),id=rawid,name=literal,description="synthetic public fixture")
    record.annotations["molecule_type"]="DNA"
    record.features=[SeqFeature(FeatureLocation(0,9,strand=1),type="CDS",qualifiers={"locus_tag":["gene_1"],"translation":["MMM"]})]
    source=tmp_path/"whole.gbk";SeqIO.write([record],source,"genbank")
    pkg=tmp_path/"pkg";pkg.mkdir()
    (pkg/"PUBLIC-1_cds_table.csv").write_text("strain,contig,locus_tag,start,end,strand,length_aa,region,bgc_id\n"+f"PUBLIC-1,{literal},gene_1,1,9,1,3,region001,BGC001\n")
    out=tmp_path/"export.json";mod.export(source,None,pkg,"PUBLIC-1",out)
    data=json.loads(out.read_text())
    assert data["genes"][0]["contig"]==literal and data["genes"][0]["genbank_record_id"]==rawid


def test_native_v2_findings_include_dropped_scope_marker():
    result=v2_findings("<!-- MODEB_EXPANDED_LOCUS_REQUIRED -->")
    assert any(f["code"]=="LOCUS_SCOPE_MISSING" for f in result)


def test_validated_context_is_existence_only_and_rejects_foreign_card(tmp_path):
    from mamey.modeb_locus_scope import context_loci
    s,*_=scope(tmp_path)
    from mamey.modeb_current50_v2 import header_line
    md=header_line(*CORE.split(" / "))+"\n# Mode B — PUBLIC-1 / BGC001\n"+card(s)
    assert context_loci(md,bgc="BGC001")=={"a_1","b_1","b_2"}
    assert context_loci(md,bgc="BGC999")==set()
    assert context_loci(md.replace("# Mode B — PUBLIC-1 /", "# Mode B — FOREIGN /"))==set()
    assert context_loci(md,package=tmp_path/"other-package")==set()


@pytest.mark.parametrize("saved_query",[True,False])
def test_split_rival_is_bound_without_expanding_primary_scope(tmp_path,saved_query):
    _,d,inv,_=scope(tmp_path)
    if saved_query:
        with (d/"gap_rescue_proteins.faa").open("a") as f:f.write(">q3\nLMN\n")
    write_table(d/"gap_rescue_split_genes.tsv",[dict(name="tailor",split_call="MODULAR_UNRESOLVED",
        piece1_locus="b_3",piece1_region_identity=PARTNER,piece2_region_identity=PARTNER)])
    s=build_scope(inv,load_gap_rescue(d,CORE),[dict(locus_tag="a_1")],50)
    if saved_query:
        assert s["state"]=="BOUND" and s["selected_cds"]==3
        assert s["split_context"][0]["locus_tag"]=="b_3"
        assert "b_3" not in {g["locus_tag"] for g in s["genes"]}
    else:assert s["state"]=="HOLD"


def test_expanded_matrix_roster_is_separate_from_core_roster():
    from mamey import modeb_structure_gate as gate
    from tests.test_modeb_complete_blastp_matrix_v9_7_372 import GOOD, ROSTER
    ctx=dict(known_locus_tags=[ROSTER[0]], modeb_matrix_locus_tags=ROSTER,require_complete_blastp_matrix=True)
    assert gate._section4_complete_blastp_matrix_findings(GOOD,ctx)==[]
    assert ctx["known_locus_tags"]==[ROSTER[0]]
    missing="\n".join(x for x in GOOD.splitlines() if not x.startswith("| `ctg9_2`"))
    assert gate._section4_complete_blastp_matrix_findings(missing,ctx)[0]["code"]=="BLASTP_MATRIX_ROSTER"


def test_coverage_counts_primary_matrix_genes_once():
    from mamey import modeb_structure_gate as gate
    matrix="## §4 Evidence\n#### Complete channel-separated BLASTp matrix\n\n| Gene | nr identity | verdict |\n|---|---|---|\n| ctg9_1 |80%|CONFIRM|\n| ctg9_2 |70%|REFINE|\n| ctg9_3 |60%|REFINE|\n"
    extra="\n#### Scope\n| Gene | context |\n|---|---|\n"+"| ctg9_1 |context|\n"*30
    ctx=dict(known_locus_tags=["ctg9_1"],modeb_matrix_locus_tags=["ctg9_1","ctg9_2","ctg9_3"],n_core_genes=1)
    assert gate._section4_blastp_coverage_findings(matrix+extra,ctx)==[]
    one=matrix.replace("| ctg9_2 |70%|REFINE|\n", "").replace("| ctg9_3 |60%|REFINE|\n", "")
    result=gate._section4_blastp_coverage_findings(one+extra,ctx)
    assert result[0]["found"]=="1/3 selected CDS" and "selected CDS" in result[0]["message"]
