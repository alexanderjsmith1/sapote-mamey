"""Family names (ending in -aceae) are never italic in genus labels; genus names still are (owner ruling)."""
import importlib.util, sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod)
    return mod


def test_classes_per_genome_row_label_family_roman():
    m = _load("bgc_classes_per_genome")
    out = m.row_labels([{"strain": "AS-1", "genus": "Pseudonocardiaceae", "row_note": "Atta"},
                        {"strain": "AS-2", "genus": "Pseudonocardia", "row_note": ""}], {"Atta"})
    assert out["AS-1"] == "Pseudonocardiaceae (<i>Atta</i>)"
    assert out["AS-2"] == "<i>Pseudonocardia</i>"


def test_chitin_band_label_family_roman():
    m = _load("chitin_isolate_vs_references")
    assert m._gname("Pseudonocardiaceae") == "Pseudonocardiaceae"
    assert m._gname("Pseudonocardiaceae bacterium") == "Pseudonocardiaceae bacterium"
    assert m._gname("Streptomyces") == "$\\it{Streptomyces}$"


def test_r_label_helpers_skip_family_names():
    for f in ("taxonomy_T01_figures.py", "taxonomy_T02_within_genus.py", "genus_composition_figures.py"):
        assert 'grepl("aceae( bacterium)?$"' in (TOOLS / f).read_text(), f
    assert 'endswith(("aceae", "aceae bacterium"))' in (TOOLS / "collection_map.py").read_text()
    assert 'grepl("aceae( bacterium)?$",x)' in (TOOLS / "bioassay_paper_theme.R").read_text()
