"""Repeated separators do not convert an isolate into a reference layer."""
import csv
import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("gcf_fixture",Path(__file__).with_name("test_trees_433_gcf_synteny_tree_layers_and_pruning.py"))
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
gs=fixture.gs

@pytest.mark.parametrize("separator",["_","__","___"])
def test_isolate_identity_uses_bound_inventory(tmp_path,separator):
    contig="NODE_1_length_100_cov_5.0"
    inventory=tmp_path/"inventory.csv"
    inventory.write_text(f"BGC_ID,Contig,antiSMASH_Region,Source_GBK\nBGC001,{contig},region001,{contig}.region001.gbk\n")
    name=f"SYN-971{separator}{contig}.region001.gbk"
    assert gs.layer_identity(name,"") is None
    assert gs.split_region_name(name)==("SYN-971",contig,"region001")
    row=gs.row_identity(name,gs.load_identity([inventory]))
    assert row["label"]==f"SYN-971 / {contig} / region001 / BGC001"
    assert row["reference"] is False and row["hold"]==""

@pytest.mark.parametrize("name,layer",[("Streptomyces_sp_X__NZ_ABC12345.1.region001.gbk","REF"),("SID42__NZ_ABC12345.1.region001.gbk","REF"),("SID_SID42_NZ_ABC12345.1.region001.gbk","SID"),("TYPE_Genus_species_NZ_ABC12345.1.region001.gbk","TYPE")])
def test_reference_prefixes_and_names_stay_references(name,layer):
    row=gs.layer_identity(name,"")
    assert row["reference"] and row["layer"]==layer


def test_focal_isolate_survives_pruned_render(tmp_path):
    files,inventory,tree=fixture._family(tmp_path,n_ref=6)
    original=files["Q"]
    replacement=original.with_name("SYN-971__"+original.name.split("_",1)[1])
    original.rename(replacement);files["Q"]=replacement
    out=tmp_path/"pruned"
    assert gs.main(fixture._args(files,inventory,tree,out,["--max-tips","5","--focal","SYN-971"]))==0
    with (tmp_path/"pruned_rows.tsv").open() as stream:
        rows=list(csv.reader(stream,delimiter="\t"))
    query=next(row for row in rows[1:] if row[0]=="Q")
    assert query[2]=="SYN-971 / NODE_12_length_123456_cov_10.123456 / region003 / BGC012"
    assert query[8]=="False" and query[10]=="query"
    assert len(rows)==6
