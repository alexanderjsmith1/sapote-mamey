"""Tests for Tools/bgc_neighbor_layer.py — layer classification + tip-key derivation (generic taxa)."""
import importlib.util, pathlib
_T = pathlib.Path(__file__).resolve().parents[1] / "tools" / "bgc_neighbor_layer.py"
_s = importlib.util.spec_from_file_location("bgc_neighbor_layer", _T)
m = importlib.util.module_from_spec(_s); _s.loader.exec_module(m)

def test_tip_key_strips_ext():
    assert m.tip_key("path/GCF_1__Genusa_speciesa.fna") == "GCF_1__Genusa_speciesa"
    assert m.tip_key("STRAIN-1.fasta") == "STRAIN-1"

def _rows():
    return [
        {"strain":"STRAIN-1","genome_file":"STRAIN-1.fna","related_organism":"STRAIN-1","accession":"","status":"query"},
        {"strain":"STRAIN-1","genome_file":"Genusa_speciesa.fna","related_organism":"Genusa speciesa","accession":"","status":"already_in_tree"},
        {"strain":"STRAIN-1","genome_file":"GCF_9__Genusa_specz.fna","related_organism":"Genusa specz","accession":"GCF_9","status":"downloaded"},
    ]

def test_query_detected():
    lay = {x["tip_key"]: x["layer"] for x in m.build_layer(_rows())}
    assert lay["STRAIN-1"] == "query"

def test_type_anchor_tagged_when_in_types_list():
    lay = {x["tip_key"]: x["layer"] for x in m.build_layer(_rows(), type_names=["Genusa speciesa"])}
    assert lay["Genusa_speciesa"] == "type_16S"

def test_bgc_neighbor_is_default():
    lay = {x["tip_key"]: x["layer"] for x in m.build_layer(_rows(), type_names=["Genusa speciesa"])}
    assert lay["GCF_9__Genusa_specz"] == "bgc_neighbor"

def test_strain_filter():
    rows = _rows() + [{"strain":"STRAIN-2","genome_file":"x.fna","related_organism":"y","accession":"","status":"downloaded"}]
    assert all(x["source_strain"]=="STRAIN-1" for x in m.build_layer(rows, strain_filter="STRAIN-1"))
