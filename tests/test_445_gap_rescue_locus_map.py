"""tools/gap_rescue_locus_map.py: which contigs the gap-rescue figure draws.

The owner, 2026-09-30, on the first automatic figure: the hand-made two-row map "looked a lot better"; the automatic one
pulled in unrelated contigs (a transposase, a P450, an esterase from the reference's flanks). Then: "we could have a
secondary 35% threshold that can help find more rescues", because a real cluster can have low homology to MIBiG.
"""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)

REF = [{"name": n, "product": p, "s": i, "e": i + 0.9, "strand": 1} for i, (n, p) in enumerate(
    [("ABC00001.1", "transposase"), ("abcA", "synthase"), ("abcB", "kinase"), ("abcC", "oxidoreductase"),
     ("abcD", "hydrolase"), ("ABC00002.1", "cytochrome P450")])]


def _prot(tag, contig, start=1000):
    return {"tag": tag, "contig": contig, "start": start, "end": start + 900, "strand": 1, "contig_len": 20000}


PROTS = {"q1": _prot("core_1", "core"), "q2": _prot("far_1", "far"), "q3": _prot("mid_1", "mid"),
         "q4": _prot("low_1", "low"), "q5": _prot("flank_1", "flank"), "q6": _prot("p450_1", "p450")}


def _row(status, pid, ident, recip=True):
    return {"status": status, "best_protein": pid, "best_identity_pct": ident, "reciprocal_best": recip}


def test_named_genes_pull_contigs_in_two_tiers_and_flank_genes_never_do():
    rows = [_row("MISSING_FOUND_CLEAR", "q5", 70.0),   # transposase (accession-named flank gene)
            _row("PRESENT_IN_CORE", "q1", 40.0),       # abcA in the core: drawn at any identity
            _row("MISSING_FOUND_CLEAR", "q2", 64.0),   # abcB: primary
            _row("MISSING_FOUND_CLEAR", "q3", 42.0),   # abcC: secondary (35-50%)
            _row("MISSING_FOUND_CLEAR", "q4", 33.0),   # abcD: under 35%
            _row("MISSING_FOUND_CLEAR", "q6", 58.0)]   # P450 (accession-named flank gene)
    drawn, splits, order, not_drawn, secondary = glm.choose(REF, rows, [], PROTS, "core")
    assert order[0] == "core" and set(order) == {"core", "far", "mid"}
    assert secondary == {"mid"}
    assert not_drawn == 3 and splits == {}


def test_a_clear_split_partner_is_always_drawn_but_a_weak_split_is_not():
    rows = [_row("PRESENT_IN_CORE", "q1", 55.0)] + [_row("MISSING_NOT_FOUND", None, 0.0)] * 5
    split = {"reference_gene": "3", "piece1_locus": "core_1", "piece2_locus": "low_1", "piece1_identity_pct": "40",
             "piece2_identity_pct": "31"}
    _, info, order, _, _ = glm.choose(REF, rows, [dict(split, split_call="CLEAR")], PROTS, "core")
    assert order == ["core", "low"] and 2 in info
    _, info, order, _, _ = glm.choose(REF, rows, [dict(split, split_call="WEAK")], PROTS, "core")
    assert order == ["core"] and info == {}


def test_when_the_reference_names_almost_nothing_every_gene_counts():
    ref = [dict(g, name=f"XYZ{i:05d}.1") for i, g in enumerate(REF)]
    rows = [_row("PRESENT_IN_CORE", "q1", 55.0), _row("MISSING_FOUND_CLEAR", "q2", 60.0)] + \
        [_row("MISSING_NOT_FOUND", None, 0.0)] * 4
    _, _, order, _, _ = glm.choose(ref, rows, [], PROTS, "core")
    assert order == ["core", "far"]
