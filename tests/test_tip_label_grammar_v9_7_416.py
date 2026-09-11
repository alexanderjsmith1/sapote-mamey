"""Label grammar rulings of 2026-09-08 (docs/TREE_FIGURE_GRAMMAR.md rules 1-7), pinned."""
import importlib.util, sys
from pathlib import Path
import pytest
TOOL = Path(__file__).resolve().parent.parent / "tools" / "tip_label.py"
def _m():
    assert TOOL.exists(), "bundled label helper required"
    s = importlib.util.spec_from_file_location("_tl416", TOOL); m = importlib.util.module_from_spec(s); sys.modules[s.name] = m; s.loader.exec_module(m); return m
def test_reference_label_carries_deposited_source_like_a_query():
    assert _m().ref_label("Saccharopolyspora gloriosae", acc="NR_116119.1", source="hay meadow soil") == "Saccharopolyspora gloriosae [hay meadow soil] (NR_116119.1)"
def test_ruled_shortening_rhizosphere():
    assert "[rhizosphere]" in _m().ref_label("Streptomyces sp.", acc="KC1", source="rhizosphere soil")
def test_absent_source_omits_bracket():
    assert "[" not in _m().ref_label("Kitasatospora cinereorecta", acc="NR_041173.1", source="")
def test_bracket_always_closes_when_width_is_tight():
    lab = _m().ref_label("Micromonospora ureilytica", acc="NR_151944.1", is_type=True, source="root nodule of Lupinus angustifolius growing in a garden")
    assert lab.count("[") == lab.count("]") and lab.endswith("(NR_151944.1)")
def test_species_from_tip_strips_accession_first():
    assert _m().species_from_tip("NR_151944.1_Micromonospora_ureilytica") == ("Micromonospora ureilytica", "NR_151944.1")
def test_culture_collection_code_is_not_an_accession():
    assert _m().species_from_tip("IFO_14684_Streptomyces_griseus")[1] == ""
def test_query_label_grammar():
    assert _m().query_label("AS-427", "Bombus sp.", "PX565021") == "AS-427 [Bombus sp.] (PX565021)"
