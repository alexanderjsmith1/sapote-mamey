"""GCF tags stop calling unmatched type I PKS regions polyene, give other PKS a general bucket, and NAPAA stays
housekeeping in the tools that already file it so.

tools/build_gcf_tags.py falls back to a class-level orphan tag when a region's KnownClusterBlast anchor matches no
thesaurus alias. For T1PKS it took the first orphan tag in the thesaurus, PKS1_polyene_orphan, so every unmatched
type I PKS read as a polyene family (88 of 89 polyene tags on 23 public genomes). Type III PKS, hglE-KS,
arylpolyene and PKS-like regions reached the same tag through the category word "PKS".

The inventory table, the lead board and the saccharide triage each file NAPAA as housekeeping. The family word
"NRPS" pre-empted that, so a NAPAA region read as NRPS.
"""
import importlib.util
from pathlib import Path

import pytest

from mamey.class_architecture import ANTISMASH_PRODUCT_CATEGORY, with_family_labels

ROOT = Path(__file__).resolve().parents[1]


def _tool(name):
    spec = importlib.util.spec_from_file_location(f"_t444_{name}", ROOT / "tools" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def gcf():
    module = _tool("build_gcf_tags")
    module.PAIRS, module.ORPHAN = module.load_aliases(ROOT / "resources" / "gcf_thesaurus.json")
    return module


def _tag(gcf, products, anchor="an unmatched compound"):
    return gcf.tag_bgc(anchor, products, gcf.PAIRS, gcf.ORPHAN)


def test_unmatched_type_i_pks_is_not_called_polyene(gcf):
    assert _tag(gcf, "T1PKS") == ("PKS1_class_orphan", "unmatched_anchor")
    assert _tag(gcf, "T1PKS;NRPS;saccharide")[0] == "PKS1_class_orphan"
    # a real polyene anchor still gets the polyene family
    assert _tag(gcf, "T1PKS", anchor="tetramycin")[0] == "PKS1_polyene_orphan"


@pytest.mark.parametrize("types", ["T3PKS", "hglE-KS", "arylpolyene", "PKS-like", "PUFA"])
def test_other_pks_types_get_the_general_pks_bucket(gcf, types):
    assert _tag(gcf, types)[0] == "PKS_other_orphan"


def test_class_fallback_never_carries_compound_aliases_when_a_class_level_tag_exists(gcf):
    import json
    th = json.loads((ROOT / "resources" / "gcf_thesaurus.json").read_text())
    for cls, tags in th.items():
        fallback = [t for t in tags if t["tag"] == gcf.ORPHAN[cls]]
        if any(not t["aliases"] for t in tags if t["tag"].endswith(("_orphan", "_unknown"))):
            assert fallback and not fallback[0]["aliases"], cls


@pytest.mark.parametrize("product", sorted(ANTISMASH_PRODUCT_CATEGORY))
def test_predicted_class_is_an_antismash_type_not_a_family_word(gcf, product):
    assert gcf.primary_class(product) == product


def test_napaa_adds_no_family_word_when_asked():
    assert with_family_labels("NAPAA", without=("napaa",)) == ["NAPAA"]
    assert with_family_labels("NAPAA;CDPS", without=("napaa",)) == ["NAPAA", "CDPS", "NRPS"]
    assert with_family_labels("NAPAA") == ["NAPAA", "NRPS"]          # groupings that did not ask keep .443a


def test_napaa_stays_housekeeping_in_the_tools():
    inventory = _tool("build_inventory_table")
    sugar = _tool("build_saccharide_triage")
    assert inventory.headline_class("NAPAA") == "NAPAA (excl.)"
    assert inventory.headline_class("NAPAA;saccharide") == "saccharide (excl.)"
    assert sugar.classify({"products": "saccharide;NAPAA", "length_kb": 10})[0] != "TAILORING"
    assert sugar.classify({"products": "saccharide;NRPS", "length_kb": 10})[0] == "TAILORING"
    board = (ROOT / "tools" / "lead_board.py").read_text(encoding="utf-8")
    assert "with_family_labels(b.get('products') or '', without=('napaa',))" in board


@pytest.mark.parametrize("products,expected", [
    ("RiPP-like;saccharide", "ripp-like"),              # ranks as RiPP, shows the type
    ("saccharide;terpene-precursor", "terpene-precursor"),
    ("NAPAA;saccharide", "saccharide"),                 # NAPAA does not rank as NRPS
    ("CDPS;NAPAA", "cdps"),
])
def test_predicted_class_ranks_by_family_but_shows_the_type(gcf, products, expected):
    assert gcf.primary_class(products) == expected
