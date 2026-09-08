"""habitat-map (L5/L6): store-backed manifest.source -> habitat category. Hermetic."""
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("mamey_habitat_map", ROOT/"tools"/"mamey_habitat_map.py")
hm = importlib.util.module_from_spec(_s); _s.loader.exec_module(hm)

def test_core_habitats():
    assert hm.classify("bumblebee gut") == "bee"
    assert hm.classify("isolated from a wasp nest") == "wasp"
    assert hm.classify("Sphagnum moss") == "moss"
    assert hm.classify("Homo sapiens sputum") == "clinical"
    assert hm.classify("soil rhizosphere") == "environmental"

def test_termite_is_not_attine():
    # fungus-growing termite must NOT bucket as attine (attine = fungus-growing ANTS)
    assert hm.classify("fungus-growing termite Macrotermes") == "termite"
    assert hm.classify("Acromyrmex leaf-cutter ant") == "attine"

def test_unassigned_vs_reference():
    assert hm.classify("AS-series isolate; host not in record") == "UNASSIGNED"
    assert hm.classify("GCA_000123 type strain") == "reference/type"
    assert hm.classify("") == "reference/type"
