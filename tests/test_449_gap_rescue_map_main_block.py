"""tools/gap_rescue_locus_map.py: matches more than 100 kb from a contig's anchor block are left off the map, and a SUPPORTED find
never pulls in a contig for an unnamed reference gene.

Two loseolamycin-like maps were squeezed to an unreadable scale by one clean match about 1 Mb along the core contig, and a
third map hid clean finds at 52-84% on three contigs because the reference names one gene and only its biosynthetic-kind
genes could pull a contig in. Letting SUPPORTED finds in drew reference-flank housekeeping genes (NADH dehydrogenase,
topoisomerase) on phosphonoglycan maps, so that half was dropped: the gene table lists those finds, and the map does not.
"""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_449m", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)


def _prot(tag, contig, start_kb):
    return {"tag": tag, "contig": contig, "start": int(start_kb * 1000), "end": int(start_kb * 1000) + 900, "strand": 1,
            "contig_len": 2_000_000}


def test_the_core_contig_keeps_the_block_beside_the_core_region_not_the_largest():
    prots = {"a1": _prot("a1", "core", 10), "a2": _prot("a2", "core", 20),
             "b1": _prot("b1", "core", 900), "b2": _prot("b2", "core", 905), "b3": _prot("b3", "core", 910)}
    drawn = [(0, "a1", 60.0), (1, "a2", 60.0), (2, "b1", 80.0), (3, "b2", 80.0), (4, "b3", 80.0)]
    kept, dropped = glm.main_blocks(drawn, prots, {"contig": "core", "start": 0, "end": 50_000}, {})
    assert {m[1] for m in kept} == {"a1", "a2"}
    assert dropped == 3


def test_every_block_inside_the_core_region_is_kept():
    """A spore-pigment map kept one regulator match and dropped the 9-gene WhiE block: both lay inside a large core region,
    and the tie went to the first block."""
    prots = {"r": _prot("r", "core", 10), **{f"w{i}": _prot(f"w{i}", "core", 100 + i) for i in range(9)},
             "far": _prot("far", "core", 400)}
    drawn = [(0, "r", 34.0)] + [(i + 1, f"w{i}", 70.0) for i in range(9)] + [(10, "far", 60.0)]
    kept, dropped = glm.main_blocks(drawn, prots, {"contig": "core", "start": 0, "end": 120_000}, {})
    assert {m[1] for m in kept} == {"r"} | {f"w{i}" for i in range(9)}
    assert dropped == 1


def test_another_contig_keeps_its_largest_block_and_any_block_with_a_split_piece():
    prots = {"c": _prot("c", "core", 10), "x1": _prot("x1", "x", 1), "x2": _prot("x2", "x", 3), "x3": _prot("x3", "x", 5),
             "x4": _prot("x4", "x", 200), "x5": _prot("x5", "x", 300)}
    drawn = [(0, "c", 70.0), (1, "x1", 55.0), (2, "x2", 55.0), (3, "x3", 55.0), (4, "x4", 90.0), (5, "x5", 60.0)]
    split = {5: ("x5", "c", 60.0, 70.0)}
    kept, dropped = glm.main_blocks(drawn, prots, {"contig": "core", "start": 0, "end": 50_000}, split)
    assert {m[1] for m in kept} == {"c", "x1", "x2", "x3", "x5"}   # the lone 90% match 194 kb away is left off
    assert dropped == 1


def test_a_block_just_outside_the_core_region_is_kept():
    """Kedarcidin-like map: tailoring genes 28-44 kb outside the core region belong on the map; a helicase 110 kb out does not."""
    prots = {"c1": _prot("c1", "core", 10), "c2": _prot("c2", "core", 20),
             "t1": _prot("t1", "core", 90), "t2": _prot("t2", "core", 95), "h": _prot("h", "core", 200)}
    drawn = [(0, "c1", 70.0), (1, "c2", 70.0), (2, "t1", 60.0), (3, "t2", 60.0), (4, "h", 55.0)]
    kept, dropped = glm.main_blocks(drawn, prots, {"contig": "core", "start": 0, "end": 50_000}, {})
    assert {m[1] for m in kept} == {"c1", "c2", "t1", "t2"}
    assert dropped == 1


def test_matches_within_the_gap_stay_one_block():
    prots = {f"m{i}": _prot(f"m{i}", "core", 10 + 25 * i) for i in range(5)}   # 25 kb apart, under the 30 kb gap
    drawn = [(i, f"m{i}", 60.0) for i in range(5)]
    kept, dropped = glm.main_blocks(drawn, prots, {"contig": "core", "start": 0, "end": 20_000}, {})
    assert len(kept) == 5 and dropped == 0


def _ref():
    # one curated name only, so cluster_genes falls back to the three biosynthetic-kind genes
    names = ["abcA", "WP_000001.1", "WP_000002.1", "WP_000003.1", "WP_000004.1"]
    kinds = ["biosynthetic", "biosynthetic", "biosynthetic", "", ""]
    return [{"i": i + 1, "name": n, "product": "hypothetical protein", "kind": k, "s": i, "e": i + 0.9, "strand": 1}
            for i, (n, k) in enumerate(zip(names, kinds))]


def _row(pid, status, verdict, ident):
    return {"status": status, "best_protein": pid, "best_identity_pct": ident, "reciprocal_best": True,
            "partner_verdict": verdict}


def test_a_supported_find_for_an_unnamed_gene_does_not_pull_in_a_contig():
    """Partner support is adjacency; a reference-flank housekeeping operon is adjacent too, so it must not pull a contig in."""
    prots = {"q1": _prot("c_1", "core", 10), "q4": _prot("f_1", "far", 10), "q5": _prot("g_1", "far2", 10)}
    rows = [_row("q1", "PRESENT_IN_CORE", "", 80.0), {"status": "MISSING"}, {"status": "MISSING"},
            _row("q4", "MISSING_FOUND_CLEAR", "SUPPORTED", 70.0), _row("q5", "MISSING_FOUND_CLEAR", "SINGLE_GENE", 70.0)]
    drawn, _, order, not_drawn, _ = glm.choose(_ref(), rows, [], prots, "core")
    assert {p for _, p, _ in drawn} == {"q1"}
    assert order == ["core"]
