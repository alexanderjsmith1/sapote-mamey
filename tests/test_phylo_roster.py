"""AMBER_04 (v9.7.349): tests for the numbered-roster / remove-by-number curation tool
(tools/phylo_roster.py).

Checks stable tree-leaf-order numbering, role/genus inference, the '30,31,36' removal
parser, and that apply_removals drops exactly the numbered entries and warns when a
removed index is a QUERY (an AS strain) — never a silent drop of the wrong strain.
"""
import os
import csv
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
_R = os.path.join(ROOT, "tools", "phylo_roster.py")
spec = importlib.util.spec_from_file_location("phylo_roster", _R)
roster = importlib.util.module_from_spec(spec)
spec.loader.exec_module(roster)

TREE = ("((AS-101_q:0.1,Streptomyces_griseus_DSM40236:0.1)90:0.2,"
        "(AS-102_q:0.1,Kitasatospora_setae_KM6054_OUTGROUP:0.3)80:0.2);")


def test_tree_tips_in_leaf_order():
    tips = roster.tree_tips(TREE)
    assert tips == ["AS-101_q", "Streptomyces_griseus_DSM40236",
                    "AS-102_q", "Kitasatospora_setae_KM6054_OUTGROUP"]


def test_roster_numbers_and_roles():
    r = roster.roster_from_tips(roster.tree_tips(TREE))
    assert [x["index"] for x in r] == [1, 2, 3, 4]
    roles = {x["label"]: x["role"] for x in r}
    assert roles["AS-101_q"] == "QUERY"
    assert roles["Streptomyces_griseus_DSM40236"] == "REFERENCE"
    assert roles["Kitasatospora_setae_KM6054_OUTGROUP"] == "OUTGROUP"
    assert r[1]["genus"] == "Streptomyces"


def test_parse_removals_accepts_commas_and_spaces():
    assert roster.parse_removals("30,31,36") == [30, 31, 36]
    assert roster.parse_removals("36 30  31") == [30, 31, 36]
    assert roster.parse_removals("") == []


def test_apply_removals_drops_exact_and_warns_on_query():
    r = roster.roster_from_tips(roster.tree_tips(TREE))
    kept, removed, warnings = roster.apply_removals(r, [2, 4])
    assert {x["label"] for x in removed} == {
        "Streptomyces_griseus_DSM40236", "Kitasatospora_setae_KM6054_OUTGROUP"}
    assert [x["label"] for x in kept] == ["AS-101_q", "AS-102_q"]
    assert warnings == []                                   # no QUERY removed


def test_removing_a_query_is_flagged():
    r = roster.roster_from_tips(roster.tree_tips(TREE))
    kept, removed, warnings = roster.apply_removals(r, [1])
    assert any("QUERY" in w for w in warnings)              # AS-101 flagged
    assert any("not in roster" not in w for w in warnings)


def test_out_of_range_index_warns():
    r = roster.roster_from_tips(roster.tree_tips(TREE))
    _, _, warnings = roster.apply_removals(r, [99])
    assert any("not in roster" in w for w in warnings)


def test_panel_roster_and_edit(tmp_path):
    p = tmp_path / "panel.tsv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(roster.PANEL_COLS)
        w.writerow(["AS-101", "QUERY", "/g/AS-101.fna", "", ""])
        w.writerow(["Streptomyces_x_R1", "REFERENCE", "/g/R1.fna",
                    "nearest_neighbour_patristic_MLSA", "AS-101"])
        w.writerow(["Out_z_OUTGROUP", "OUTGROUP", "/g/O.fna", "curator_outgroup", ""])
    rows = list(csv.DictReader(open(p), delimiter="\t"))
    r = roster.roster_from_panel(rows)
    assert [x["index"] for x in r] == [1, 2, 3]
    assert r[1]["related"] == "AS-101"
