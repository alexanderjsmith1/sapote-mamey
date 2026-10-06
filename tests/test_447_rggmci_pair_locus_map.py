"""tools/rggmci_pair_locus_map.py and the pair mode of tools/gap_rescue_locus_map.py.

2026-10-01: "locus maps for any fragment rescue would be needed." RG-GMCI links two contig-edge fragments; the pair
map draws fragment A's contig end, a link marker and fragment B's contig end under the shared MIBiG cluster, with each
fragment's own matches, so two fragments that repeat the same part of the reference read as overlap, not as a split.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


glm = _load("gap_rescue_locus_map")

REF = [{"name": n, "product": "p", "s": i, "e": i + 0.9, "strand": 1} for i, n in
       enumerate(["abcA", "abcB", "abcC", "abcD"])]


def _prot(tag, contig, start, contig_len=20000):
    return {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": 1, "contig_len": contig_len}


PROTS = {"q1": _prot("a_1", "ctgA", 18000), "q2": _prot("b_1", "ctgB", 500), "q3": _prot("x_1", "ctgX", 5000),
         "q4": _prot("b_2", "ctgB", 1600)}


def _row(status, pid, ident, recip=True):
    return {"status": status, "best_protein": pid, "best_identity_pct": ident, "reciprocal_best": recip}


def test_pair_mode_draws_the_partner_next_to_the_core_and_pulls_in_nothing_else():
    rows = [_row("PRESENT_IN_CORE", "q1", 60.0), _row("MISSING_FOUND_CLEAR", "q2", 55.0),
            _row("MISSING_FOUND_CLEAR", "q3", 70.0), _row("MISSING_NOT_FOUND", None, 0.0)]
    _, _, order, not_drawn, _ = glm.choose(REF, rows, [], PROTS, "ctgA")
    assert "ctgX" in order                                   # the gap-rescue figure pulls a clear find in
    _, _, order, not_drawn, secondary = glm.choose(REF, rows, [], PROTS, "ctgA", partner_contig="ctgB")
    assert order == ["ctgA", "ctgB"] and secondary == set()
    assert not_drawn == 1                                    # the ctgX find is counted, not drawn


def test_the_partners_own_matches_are_drawn_even_when_the_core_holds_the_best_one():
    rows = [_row("PRESENT_IN_CORE", "q1", 60.0)] + [_row("MISSING_NOT_FOUND", None, 0.0)] * 3
    rows_b = [_row("PRESENT_IN_CORE", "q2", 58.0), _row("MISSING_NOT_FOUND", None, 0.0),
              _row("PRESENT_IN_CORE", "q4", 41.0), _row("MISSING_NOT_FOUND", None, 0.0)]
    drawn, *_ = glm.choose(REF, rows, [], PROTS, "ctgA", partner_contig="ctgB", partner_rows=rows_b)
    assert sorted((k, pid) for k, pid, _ in drawn) == [(0, "q1"), (0, "q2"), (2, "q4")]


def test_edge_side_reads_which_contig_end_a_region_touches():
    assert glm.edge_side({"start": 0, "end": 30000}, 200000) == "left"
    assert glm.edge_side({"start": 170000, "end": 200000}, 200000) == "right"
    assert glm.edge_side({"start": 50000, "end": 80000}, 200000) is None
    assert glm.edge_side({"start": 0, "end": 60000}, 60000) is None          # a whole-contig region


pm = _load("rggmci_pair_locus_map")

PAIRS = [
    {"bgc_a": "BGC050", "bgc_b": "BGC054", "edge_a": "Edge", "edge_b": "Edge", "rggmci_score": "31",
     "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE", "best_sources": "BGC0002497.3 (ADJACENT, ranks 1/1) | NZ_CP016174"},
    {"bgc_a": "BGC008", "bgc_b": "BGC022", "edge_a": "Interior", "edge_b": "Interior", "rggmci_score": "31",
     "rggmci_confidence": "MODERATE_RG_GMCI_CANDIDATE", "best_sources": "BGC0000290.5"},
    {"bgc_a": "BGC043", "bgc_b": "BGC050", "edge_a": "Edge", "edge_b": "Full-contig", "rggmci_score": "40",
     "rggmci_confidence": "LOW_SHARED_REFERENCE_SIGNAL", "best_sources": "NZ_CP031455 only"},
]


def test_interior_pairs_are_refused_and_missing_pairs_named():
    plan = pm.select(PAIRS, [("BGC054", "BGC050"), ("BGC008", "BGC022"), ("BGC001", "BGC002")], top=10)
    assert [why == "" for *_, why in plan] == [True, False, False]
    assert "interior fragment" in plan[1][3] and "BGC008 is Interior" in plan[1][3]
    assert plan[2][3] == "pair not in the RG-GMCI table"


def test_top_takes_moderate_or_high_edge_pairs_only_best_first():
    plan = pm.select(PAIRS, [], top=10)
    assert [(a, b) for a, b, *_ in plan] == [("BGC050", "BGC054")]


def test_reference_is_the_first_mibig_cluster_on_disk(tmp_path):
    assert pm.mibig_reference(PAIRS[0], tmp_path) is None
    (tmp_path / "BGC0002497.gbk").write_text("")
    assert pm.mibig_reference(PAIRS[0], tmp_path).name == "BGC0002497.gbk"
    assert pm.mibig_reference(PAIRS[2], tmp_path) is None   # ClusterBlast-only support: nothing local to draw


def test_overlap_wording_separates_complement_from_repeat():
    assert pm.overlap({1, 2, 3}, {7, 8}) == "complementary parts of the reference"
    assert pm.overlap({1, 2, 3}, {1, 2}).startswith("the same part of the reference")
    assert pm.overlap({1, 2, 3}, {3, 9}) == "partly overlapping"
    assert pm.overlap({1}, set()).startswith("one fragment holds none")


def test_identity_hold_and_same_contig_pairs_are_refused():
    regions = [{"contig": "c1", "start": 0, "end": 10, "identity": "S / c1 / region001 / BGC001"},
               {"contig": "c2", "start": 0, "end": 10, "identity": "S / c2 / region001 / IDENTITY_HOLD"},
               {"contig": "c1", "start": 50, "end": 90, "identity": "S / c1 / region002 / BGC003"}]
    rec, why = pm.draw_pair("S", {}, regions, "BGC001", "IDENTITY_HOLD", {}, Path("x.gbk"), {}, Path("."), 1, None, {})
    assert rec is None and why.startswith("identity hold")
    rec, why = pm.draw_pair("S", {}, regions, "BGC001", "BGC003", {}, Path("x.gbk"), {}, Path("."), 1, None, {})
    assert rec is None and "one contig" in why


def test_pair_map_renders_with_facing_contig_ends(tmp_path):
    pytest.importorskip("matplotlib")
    SeqIO = pytest.importorskip("Bio.SeqIO")
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    rec = SeqRecord(Seq("A" * 4000), id="REF1", name="REF1", description="test cluster",
                    annotations={"molecule_type": "DNA"})
    for i, n in enumerate(["abcA", "abcB", "abcC", "abcD"]):
        rec.features.append(SeqFeature(FeatureLocation(i * 1000, i * 1000 + 900, strand=1), type="CDS",
                                       qualifiers={"gene": [n], "translation": ["M" * 290]}))
    gbk = tmp_path / "REF1.gbk"
    SeqIO.write(rec, str(gbk), "genbank")
    prots = {"q1": _prot("a_1", "ctgA", 1000), "q2": _prot("b_1", "ctgB", 18000)}
    core = {"contig": "ctgA", "start": 0, "end": 4000, "identity": "S / ctgA / region001 / BGC001"}      # left end
    partner = {"contig": "ctgB", "start": 16000, "end": 20000, "identity": "S / ctgB / region001 / BGC002"}  # right end
    rows = [{"status": "PRESENT_IN_CORE", "best_protein": "q1", "best_identity_pct": 60.0, "reciprocal_best": True}] + \
        [{"status": "MISSING_NOT_FOUND"}] * 3
    rows_b = [{"status": "MISSING_NOT_FOUND"}, {"status": "PRESENT_IN_CORE", "best_protein": "q2",
                                               "best_identity_pct": 50.0, "reciprocal_best": True}] + \
        [{"status": "MISSING_NOT_FOUND"}] * 2
    res = glm.draw_locus_map(gbk, rows, [], prots, [core, partner], core, "S", "test", tmp_path / "m.png",
                             tmp_path / "m.pdf", partner=partner, pair_note="RG-GMCI pair BGC001 + BGC002",
                             partner_rows=rows_b)
    assert (tmp_path / "m.png").stat().st_size > 0 and (tmp_path / "m.pdf").stat().st_size > 0
    assert res["link_drawn"] and res["contigs_drawn"] == ["ctgA", "ctgB"]
    # both matches lie on the reference's strand, so neither contig is turned, even though the contig ends then do not
    # face each other: strand evidence outranks facing (3 Oct: a core drawn backwards against its reference)
    assert res["flipped"] == {"ctgA": False, "ctgB": False}


def test_every_non_complementary_reading_gets_a_plain_marker_word():
    # a pair that repeats the same part of the reference must not be drawn as a "link" (the owner, 1 Oct: the overlap map
    # with a purple link "did not make sense")
    for reading in (pm.overlap({1, 2}, {1, 2}), pm.overlap({1, 2, 3}, {3, 9}), pm.overlap({1}, set())):
        assert reading in pm.LINK_WORD
    assert pm.overlap({1}, {2}) not in pm.LINK_WORD


def test_counts_follow_the_drawing_rule():
    assert pm.drawn_rule({"reciprocal_best": True}) and pm.drawn_rule({"reciprocal_best": "True"})
    assert not pm.drawn_rule({"reciprocal_best": False}) and not pm.drawn_rule({})
