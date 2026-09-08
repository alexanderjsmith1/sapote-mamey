"""Independent native board and normalized source-anchor association controls."""
import csv
import copy
import json
from pathlib import Path
import pytest
from mamey import good_guesses as gg
import mamey.exact_identity as owner
from mamey.crosswalk import infer_node_id

STRAIN="SYNTHETIC-001"
CONTIG="NODE_1_length_1000_cov_1.5"
def board(contig=CONTIG,alias="BGC001",native=True):
    data={"BGC_ID":alias,"Contig":contig,"antiSMASH_Region":"region001","Products":"NRPS","Arch_Capacity":"NRPS","Lead_tier_auto":"High"}
    if native:data["Node_ID"]=infer_node_id(contig,"")
    return data

def anchor(contig=CONTIG,alias="BGC001"):
    return {"strain":STRAIN,"contig":infer_node_id(contig,""),"region":"region001","bgc_id":alias}

def write(root,name,rows):
    if not rows:return
    fields=list(dict.fromkeys(key for row in rows for key in row))
    with (root/name).open("w",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)

def package(tmp_path,boards,anchors,*,fixture_contig=CONTIG):
    root=tmp_path/f"{STRAIN}__{fixture_contig}__region001__BGC001";root.mkdir()
    (root/"manifest.json").write_text(json.dumps({"strain_id":STRAIN}))
    write(root,"synthetic_4_triage_board.csv",boards)
    write(root,"synthetic_3_mibig_profile.csv",[{**a,"query_gene_count":"10","recognizable_gene_fraction":str((i+1)/10),"interpretation_class":"KNOWN_ANCHORED"} for i,a in enumerate(anchors)])
    write(root,"synthetic_3_mibig_convergence.csv",[{**a,"class_concordance":"CONCORDANT","convergence_tier":"H4_REPEATED_SUPPORT","dominance_status":"CLEAR_DOMINANT","dominant_reference":"True"} for a in anchors])
    return root

@pytest.mark.parametrize("contig",[CONTIG,"ctg10_extra_suffix","scaffold_42_segment_A","CP123456.1"])
def test_native_board_and_both_source_anchors_preserve_full_display(tmp_path,contig):
    root=package(tmp_path,[board(contig)],[anchor(contig)],fixture_contig=contig)
    before={p.name:p.read_bytes() for p in root.iterdir()}
    out=tmp_path/"output"
    result=gg.run(root,out_dir=out,pdf=False,docx=False)
    expected=f"{STRAIN} / {contig} / region001 / BGC001"
    assert result["rows"][0]["exact_locus"]==expected and expected in result["markdown"]
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}
    assert not list(out.glob("*.pdf")) and not list(out.glob("*.docx"))

@pytest.mark.parametrize("field,value",[("strain","SYNTHETIC-999"),("contig","NODE_9_length_1000_cov_1"),("region","region002"),("region",""),("Node_ID","NODE_9_length_1000_cov_1"),("Contig","NODE_9_length_1000_cov_1.5"),("strain_id","SYNTHETIC-999")])
def test_source_conflict_or_missing_role_refuses_without_output(tmp_path,field,value):
    a=anchor();a[field]=value
    root=package(tmp_path,[board()],[a]);out=tmp_path/"refused"
    with pytest.raises(owner.ExactLocusIdentityError):gg.run(root,out_dir=out,pdf=False,docx=False)
    assert not out.exists()

def test_normalized_collision_associates_each_source_to_its_exact_alias(tmp_path):
    other="NODE_1_length_1000_cov_1.9"
    root=package(tmp_path,[board(),board(other,"BGC002")],[anchor(),anchor(other,"BGC002")])
    result=gg.run(root,pdf=False,docx=False)
    rows={r["bgc_id"]:r for r in result["rows"]}
    assert rows["BGC001"]["recog_fraction"]==0.1 and rows["BGC002"]["recog_fraction"]==0.2
    assert rows["BGC001"]["exact_locus"]==f"{STRAIN} / {CONTIG} / region001 / BGC001"
    assert rows["BGC002"]["exact_locus"]==f"{STRAIN} / {other} / region001 / BGC002"

@pytest.mark.parametrize("native",[False,True])
@pytest.mark.parametrize("duplicate",["alias","physical"])
def test_board_ambiguity_refuses_without_bare_alias_diagnostic(tmp_path,native,duplicate):
    first=board("CP123456.1",native=native)
    second=board("CP123456.1" if duplicate=="physical" else "CP123457.1","BGC002" if duplicate=="physical" else "BGC001",native=native)
    root=package(tmp_path,[first,second],[anchor("CP123456.1")],fixture_contig="CP123456.1")
    out=tmp_path/"refused"
    with pytest.raises(owner.ExactLocusIdentityError) as error:gg.run(root,out_dir=out,pdf=False,docx=False)
    assert not out.exists()
    if "BGC001" in str(error.value):assert f"{STRAIN} / CP123456.1 / region001 / BGC001" in str(error.value)

@pytest.mark.parametrize("field",["strain","contig","region","bgc_id"])
def test_anchor_validator_requires_every_role(field):
    identity=owner.exact_locus_from_native_inventory_row(STRAIN,board())
    a=anchor();a.pop(field)
    validator=getattr(owner,"validate_native_legacy_evidence_anchor",None);assert callable(validator)
    with pytest.raises(owner.ExactLocusIdentityError):validator(STRAIN,a,identity)

def test_anchor_binding_retains_board_reference_without_rewriting_source_locator():
    identity=owner.exact_locus_from_native_inventory_row(STRAIN,board())
    a=anchor();before=copy.deepcopy(a)
    validator=getattr(owner,"validate_native_legacy_evidence_anchor",None);assert callable(validator)
    binding=validator(STRAIN,a,identity)
    assert binding.board_identity is identity and a==before
    assert a["contig"]!=identity.full_contig
