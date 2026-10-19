"""Ambiguous tabular authority and malformed enums must produce typed holds."""
import csv
import pytest
from mamey import evidence_registry as er
from mamey import bioactivity_metadata as bm
from mamey.mode_b import gene_first_explore as gf

@pytest.mark.parametrize("key",["metadata_state","observation_state","usage_scope"])
@pytest.mark.parametrize("value",[[],{}])
def test_canonical_enum_containers_are_typed_holds(key,value):
    obj=bm.not_supplied();obj[key]=value
    with pytest.raises(bm.BioactivityMetadataError,match="BIOACTIVITY_LEGACY_SHAPE_HOLD"):
        bm.normalize_bioactivity(obj)

def registry_row():
    r=dict.fromkeys(er.REQUIRED_HEADERS,"SYNTHETIC-NOT-APPLICABLE")
    r.update(record_id="SYN-ROW",strain_id="SYNTHETIC-CASE-ONE",material_id="SYN-MAT",parent_material_id="ROOT",evidence_type="material",material_level="crude_extract",assay_state="NOT_SCREENED",claim_ceiling="Availability only")
    return r

def write(path,headers,values):
    with path.open("w",newline="") as f:w=csv.writer(f,delimiter="\t");w.writerow(headers);w.writerow(values)

@pytest.mark.parametrize("kind",["duplicate","wide"])
def test_registry_ambiguous_columns_refused(tmp_path,kind):
    r=registry_row();headers=list(er.REQUIRED_HEADERS);values=[r[h] for h in headers]
    if kind=="duplicate":headers.append("strain_id");values.append("SYNTHETIC-CASE-OTHER")
    else:values.append("SYNTHETIC-UNDECLARED-FIELD")
    path=tmp_path/"ambiguous_registry.tsv";write(path,headers,values)
    with pytest.raises(er.EvidenceRegistryError):er.validate_evidence_registry(path)

@pytest.mark.parametrize("kind",["duplicate","wide"])
def test_gene_index_ambiguous_columns_refused(tmp_path,kind):
    identity={"strain":"SYNTHETIC-CASE-ONE","full_node":"SYN-CONTIG","region":"region001","bgc_alias":"BGC001"}
    r={"channel":"mibig",**identity,"gene":"syn_gene","evidence_state":"UNBOUND","source_locator":"evidence://synthetic/one","source_sha256":"a"*64,"note":"constructed"}
    headers=list(r);values=list(r.values())
    if kind=="duplicate":headers.append("evidence_state");values.append("BOUND")
    else:values.append("SYNTHETIC-UNDECLARED-FIELD")
    path=tmp_path/"ambiguous_index.tsv";write(path,headers,values)
    with pytest.raises(gf.GeneFirstHold):gf.load_evidence_index(path,identity,{"syn_gene"})

def test_unique_extra_registry_metadata_preserved(tmp_path):
    r=registry_row();r["extra_metadata"]="SYNTHETIC-EXPLICIT-EXTENSION"
    p=tmp_path/"valid_registry.tsv";write(p,list(r),list(r.values()))
    assert er.validate_evidence_registry(p)["record_count"]==1

def test_valid_metadata_unchanged():
    obj=bm.not_supplied();assert bm.normalize_bioactivity(obj)==obj


def test_gene_table_header_hold_names_gene_table(tmp_path):
    path=tmp_path/"duplicate_gene_table.csv"
    with path.open("w",newline="") as f:
        w=csv.writer(f);w.writerow(["bgc_id","bgc_id"]);w.writerow(["BGC001","BGC001"])
    with pytest.raises(gf.GeneFirstHold,match="duplicate or blank gene-table columns"):
        gf.load_gene_rows(path,{"bgc_alias":"BGC001"})
