"""Native CSV identity adapter contract; full display and normalized key are distinct."""
import copy
from dataclasses import FrozenInstanceError
import pytest
import mamey.exact_identity as identity
from mamey.crosswalk import infer_node_id

STRAIN="SYNTHETIC-001"
CONTIG="NODE_1_length_1000_cov_1.5"
def row(contig=CONTIG):
    return {"BGC_ID":"BGC001","Contig":contig,"Node_ID":infer_node_id(contig,""),"antiSMASH_Region":"region001","Score":"1"}

def adapt(data):
    adapter=getattr(identity,"exact_locus_from_native_inventory_row",None)
    assert callable(adapter), "Current native CSV adapter is missing"
    return adapter(STRAIN,data)

@pytest.mark.parametrize("contig",[CONTIG,"ctg10_extra_suffix","scaffold_42_segment_A","CP123456.1"])
def test_csv_adapter_retains_full_identity_and_existing_normalized_key(contig):
    data=row(contig);before=copy.deepcopy(data)
    result=adapt(data)
    assert result.exact_locus==f"{STRAIN} / {contig} / region001 / BGC001"
    assert result.full_contig==contig and result.normalized_node_id==data["Node_ID"]
    assert result.strain==STRAIN and result.region=="region001" and result.bgc_alias=="BGC001"
    assert data==before
    with pytest.raises(FrozenInstanceError):result.full_contig="changed"

@pytest.mark.parametrize("field,value",[
    ("Node_ID","NODE_9_length_1000_cov_1"),("Node_ID",None),("Node_ID",""),
    ("Contig",None),("Contig",""),("Contig","NODE_1"),
    ("antiSMASH_Region",None),("antiSMASH_Region","region1"),("BGC_ID",None),
    ("node_id","NODE_9_length_1000_cov_1"),("node_id",None),("node_id",""),
    ("contig","NODE_9_length_1000_cov_1.5"),("region","region002"),
    ("bgc_alias","BGC009"),("strain_id","SYNTHETIC-999"),
    ("Full_Node_ID","NODE_9_length_1000_cov_1.5"),
])
def test_csv_adapter_preserves_all_conflicts_and_required_roles(field,value):
    data=row();data[field]=value
    with pytest.raises(identity.ExactLocusIdentityError):adapt(data)

@pytest.mark.parametrize("field",["Contig","Node_ID","antiSMASH_Region","BGC_ID"])
def test_csv_adapter_does_not_repair_missing_native_columns(field):
    data=row();data.pop(field)
    with pytest.raises(identity.ExactLocusIdentityError):adapt(data)

def test_agreeing_explicit_native_role_pairs_are_supported():
    data=row();data.update(contig=data["Contig"],node_id=data["Node_ID"],antismash_region=data["antiSMASH_Region"],bgc_id=data["BGC_ID"])
    assert adapt(data).full_contig==CONTIG

def test_source_filename_does_not_supply_or_override_identity():
    data=row();data["source_gbk"]="NODE_9_length_1000_cov_1.region999.gbk"
    assert adapt(data).full_contig==CONTIG
    data["Contig"]="CP123456.1"
    with pytest.raises(identity.ExactLocusIdentityError):adapt(data)

def test_generic_synonym_owner_stays_strict_for_native_csv():
    with pytest.raises(identity.ExactLocusIdentityError):identity.exact_locus_from_mapping(STRAIN,row())


@pytest.mark.parametrize("number,label",[(1,"region001"),(6,"region006"),(1234,"region1234"),("002","region002")])
def test_native_inventory_numeric_region_has_distinct_validated_role(number,label):
    data=row();data.update(Region=number,antiSMASH_Region=label)
    before=copy.deepcopy(data)
    assert adapt(data).exact_locus==f"{STRAIN} / {CONTIG} / {label} / BGC001"
    assert data==before

@pytest.mark.parametrize("number",["2","",None,"1.0",True,"region001","-1","1e0"])
def test_native_inventory_numeric_region_cannot_hide_invalid_pair(number):
    data=row();data["Region"]=number
    with pytest.raises(identity.ExactLocusIdentityError):adapt(data)

def test_numeric_region_does_not_relax_other_label_conflicts():
    data=row();data.update(Region="1",region="region002")
    with pytest.raises(identity.ExactLocusIdentityError):adapt(data)

def test_generic_region_synonyms_remain_textually_strict():
    data={"Contig":CONTIG,"BGC_ID":"BGC001","antiSMASH_Region":"region001","Region":"1"}
    with pytest.raises(identity.ExactLocusIdentityError):identity.exact_locus_from_mapping(STRAIN,data)
