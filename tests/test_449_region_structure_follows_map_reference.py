"""The structure beside a region's locus map is the compound of the MIBiG cluster the map is drawn against, or none.
One region showed a nargenicin A1 map (BGC0001875) beside gargantulide B (BGC0002142), the region's top
KnownClusterBlast hit; 77 of 1,286 region slides in one deck build paired a map with another cluster's structure."""
import importlib.util
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load():
    spec = importlib.util.spec_from_file_location("strain_slides_t449", TOOLS / "strain_slides.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _entries(tmp_path):
    png = tmp_path / "s.png"
    png.write_bytes(b"x")
    kcb = {"mibig_accession": "BGC0002142", "representative_name": "gargantulide B", "drawing_available": True,
           "representative_png": "s.png", "locus_bindings": [{"bgc_alias": "BGC008", "full_contig": "NODE_128", "kcb_rank": "1",
                                                               "reference_match_metrics": {"query_genes_matched_fraction": 1}}]}
    nar = {"mibig_accession": "BGC0001875", "representative_name": "nargenicin A1", "drawing_available": True,
           "representative_png": "s.png", "locus_bindings": [{"bgc_alias": "BGC050", "full_contig": "NODE_94", "kcb_rank": "1",
                                                               "reference_match_metrics": {"query_genes_matched_fraction": 0.7}}]}
    return [kcb, nar]


def test_structure_is_the_map_reference_not_the_top_kcb_hit(tmp_path):
    m = _load()
    D = {"_structures": (tmp_path, _entries(tmp_path)), "strain": "STRAIN-1", "src": {}}
    e, b, _ = m.region_structure(D, tmp_path, "BGC008", "NODE_128", "BGC0001875.1")
    assert e["representative_name"] == "nargenicin A1"
    assert b == {}          # bound to BGC050, so BGC050's KCB numbers are not printed under BGC008


def test_no_structure_when_the_map_reference_has_no_drawing(tmp_path):
    m = _load()
    D = {"_structures": (tmp_path, _entries(tmp_path)[:1]), "strain": "STRAIN-1", "src": {}}
    assert m.region_structure(D, tmp_path, "BGC008", "NODE_128", "BGC0001875") is None


def test_own_binding_keeps_its_kcb_numbers(tmp_path):
    m = _load()
    D = {"_structures": (tmp_path, _entries(tmp_path)), "strain": "STRAIN-1", "src": {}}
    e, b, _ = m.region_structure(D, tmp_path, "BGC008", "NODE_128", "BGC0002142")
    assert e["representative_name"] == "gargantulide B" and b.get("bgc_alias") == "BGC008"


def test_without_a_map_reference_the_old_rule_holds(tmp_path):
    m = _load()
    D = {"_structures": (tmp_path, _entries(tmp_path)), "strain": "STRAIN-1", "src": {}}
    e, b, _ = m.region_structure(D, tmp_path, "BGC008", "NODE_128")
    assert e["representative_name"] == "gargantulide B"
