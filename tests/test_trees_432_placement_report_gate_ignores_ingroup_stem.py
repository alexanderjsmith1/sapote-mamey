"""TREES_432 — `phylo_place.py report` gated the graft as written, so a correctly rooted small
panel with a distant outgroup could never get a figure.

build-ref roots the backbone with Biopython's root_with_outgroup, which leaves the outgroup pendant
at 0.0 and puts the whole outgroup separation on the root-to-ingroup branch. That branch's leaves
are all ingroup, so the outgroup exemption does not apply and DOMINATING_BRANCH fires (AS-150
panel: ingroup stem 0.5053 = 60 % of depth, "figure skipped"). The display convention now applied
before gating: split the outgroup separation evenly across the two root children — same topology,
same total length — and gate that tree, written beside the figure as `*.rooted_split.newick`.
"""
import importlib.util
import json
import sys
from io import StringIO
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location("phylo_place_trees432_stem", ROOT / "tools" / "phylo_place.py")
pp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pp)
_tspec = importlib.util.spec_from_file_location("tsc_trees432_stem", ROOT / "tools" / "tree_sanity_check.py")
tsc = importlib.util.module_from_spec(_tspec)
_tspec.loader.exec_module(tsc)

OG = "NR_000002_1_Outer_b_outgroup_for_Genus"
# Small panel, one distant outgroup, rooted the way build-ref leaves it: pendant 0.0, separation
# 0.20 on the ingroup stem. Ingroup depth 0.11 (balanced: no single ingroup branch over 0.06).
# Plain gate on this shape FAILs: stem 0.20 / depth 0.31 = 65 %. After the split display root the
# two root children are 0.10 each, depth 0.21, longest non-outgroup branch 0.10 = 48 %: PASS.
# (A bare 3-taxon ingroup cannot pass either way: with tips t off a stem s/2, the gate needs
# t > s/2 for the stem and t < (s/2 + t)/2 for the tip, which is impossible.)
INGROUP_TIPS = {"SID1", "NR_000001_1_Genus_a", "NR_000003_1_Genus_c", "NR_000004_1_Genus_d"}
THREE = (f"(((SID1:0.05,NR_000001_1_Genus_a:0.05):0.06,"
         f"(NR_000003_1_Genus_c:0.05,NR_000004_1_Genus_d:0.05):0.06):0.20,{OG}:0.0);")


def test_plain_gate_fails_the_build_ref_rooting_shape(tmp_path):
    f = tmp_path / "graft.newick"; f.write_text(THREE)
    ok, msg = tsc.check(str(f), outgroup=[OG])
    assert not ok and "DOMINATING_BRANCH" in msg


def test_three_taxon_distant_outgroup_passes_after_display_rooting(tmp_path):
    Phylo = pytest.importorskip("Bio.Phylo")
    t = Phylo.read(StringIO(THREE), "newick")
    before = t.total_branch_length()
    og = [x for x in t.get_terminals() if x.name == OG]
    receipt = pp._display_root_on_outgroup(t, og)
    assert receipt["outgroup_separation"] == pytest.approx(0.20)
    assert receipt["each_root_child"] == pytest.approx(0.10)
    assert t.total_branch_length() == pytest.approx(before)          # same total length
    assert {x.name for x in t.get_terminals()} == INGROUP_TIPS | {OG}
    a, b = t.root.clades
    assert a.branch_length == pytest.approx(0.10) and b.branch_length == pytest.approx(0.10)
    out = tmp_path / "rooted_split.newick"
    Phylo.write(t, str(out), "newick", format_branch_length="%.10g")
    ok, msg = tsc.check(str(out), outgroup=[OG])
    assert ok, msg


def test_render_tree_gates_the_split_tree_and_writes_the_receipt(tmp_path):
    pytest.importorskip("matplotlib"); pytest.importorskip("Bio")
    f = tmp_path / "graft.newick"; f.write_text(THREE)
    png = tmp_path / "Genus_placement_tree.png"; svg = tmp_path / "Genus_placement_tree.svg"
    labelmap = {"SID1": "SID1", "NR_000001_1_Genus_a": "NR_000001.1 Genus a strain X 16S ribosomal RNA",
                "NR_000003_1_Genus_c": "NR_000003.1 Genus c strain Z 16S ribosomal RNA",
                "NR_000004_1_Genus_d": "NR_000004.1 Genus d strain W 16S ribosomal RNA",
                OG: "NR_000002.1 Outer b strain Y 16S ribosomal RNA [outgroup for Genus]"}
    pp._render_tree(str(f), labelmap, str(png), str(svg), "Genus")   # real gate: must not raise
    assert png.is_file()
    assert f.read_text() == THREE                                    # graft file untouched
    gated = tmp_path / "Genus_placement_tree.rooted_split.newick"
    assert gated.is_file()
    ok, msg = tsc.check(str(gated), outgroup=[OG])
    assert ok, msg
    receipt = json.loads(Path(str(svg) + ".labels.json").read_text())
    assert receipt["gated_tree"] == gated.name
    assert receipt["display_rooting"]["each_root_child"] == pytest.approx(0.10)
    assert receipt["display_rooting"]["outgroup_tips"] == [OG]


def test_plain_gate_and_graft_file_unchanged_without_registry_outgroup(tmp_path, monkeypatch):
    pytest.importorskip("matplotlib"); pytest.importorskip("Bio")
    plain = "((SID1:0.01,Streptomyces_a:0.01):0.01,(Streptomyces_b:0.01,Kitasatospora_ref1:0.02):0.01,Streptomyces_c:0.02);"
    f = tmp_path / "graft.newick"; f.write_text(plain)
    calls = []
    monkeypatch.setattr(pp, "_graft_sane", lambda *a: (calls.append(a) or (False, "stop here")))
    with pytest.raises(RuntimeError):
        pp._render_tree(str(f), {}, str(tmp_path / "x.png"), str(tmp_path / "x.svg"), "fixture")
    assert calls == [(str(f), "Kitasatospora")]                    # legacy hint, original file
    assert not list(tmp_path.glob("*.rooted_split.newick"))
