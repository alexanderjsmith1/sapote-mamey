"""tools/gap_rescue_locus_map.py: an opt-in context row shows the genes around an off-region match the map does not draw.

A gap rescue can find a reference gene's best match on a contig that holds no antiSMASH region, and the map then leaves
that contig off entirely: an excluded verdict (paralog family, housekeeping context) never pulls a contig in, which is
deliberate, because letting such finds in drew reference-flank housekeeping operons on phosphonoglycan maps. The reader
is then told a match exists somewhere else and shown nothing around it.

Worked case: AS-810 / NODE_169_length_16810_cov_48.483177 / region001 / BGC009 against the LP2006 cluster
(MIBiG BGC0001655). Its lasso RiPP leader-peptide reference gene matches ctg977_3 at 38.2% on NODE_977, which is
3,764 bp, carries no antiSMASH region and is flagged paralog family. NODE_977 holds six genes, among them a second
39 aa CDS adjacent to ctg977_3 on the same strand. None of that reaches the figure.

These tests fix what the context row must and must not do. It is not a rescue: it adds nothing to the drawn matches and
nothing to any count. Class level, judgment deferred.
"""
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gap_rescue_locus_map_449ctx", ROOT / "tools/gap_rescue_locus_map.py")
glm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(glm)


def _prot(tag, contig, start_kb, contig_len=2_000_000, strand=1):
    return {"tag": tag, "contig": contig, "start": int(start_kb * 1000), "end": int(start_kb * 1000) + 900,
            "strand": strand, "contig_len": contig_len}


def _row(pid, status="MISSING_FOUND_CLEAR", ident=38.2, verdict="PARALOG_FAMILY"):
    return {"best_protein": pid, "best_locus": pid, "status": status, "best_identity_pct": ident,
            "reciprocal_best": True, "partner_verdict": verdict}


def _node977():
    """NODE_977 as the ledger records it: six genes, the match on the third."""
    starts = {"c1": 0.003, "c2": 0.761, "c3": 1.022, "c4": 1.374, "c5": 2.299, "c6": 2.798}
    return {k: _prot(k, "NODE_977", v, contig_len=3764) for k, v in starts.items()}


def test_an_off_region_match_gets_a_context_window_around_it():
    prots = {"core1": _prot("core1", "core", 10), **_node977()}
    ctx = glm.context_contigs([_row("c3")], prots, [(0, "core1", 70.0)], "core")
    assert set(ctx) == {"NODE_977"}
    lo, hi, n = ctx["NODE_977"]
    assert n == 1
    # three genes either side of c3: c1 is the lowest kept, c6 the highest
    assert lo == prots["c1"]["start"]
    assert hi == prots["c6"]["end"]


def test_the_flank_stops_at_three_genes_either_side():
    prots = {"core1": _prot("core1", "core", 10)}
    prots.update({f"g{i}": _prot(f"g{i}", "other", 10 * i) for i in range(1, 12)})
    ctx = glm.context_contigs([_row("g6")], prots, [(0, "core1", 70.0)], "core")
    lo, hi, _ = ctx["other"]
    assert lo == prots["g3"]["start"]    # g3, not g2
    assert hi == prots["g9"]["end"]      # g9, not g10


def test_a_contig_already_on_the_map_is_not_repeated_as_context():
    prots = {"core1": _prot("core1", "core", 10), "d1": _prot("d1", "other", 20), "d2": _prot("d2", "other", 30)}
    ctx = glm.context_contigs([_row("d2")], prots, [(0, "core1", 70.0), (1, "d1", 80.0)], "core")
    assert ctx == {}


def test_the_core_contig_is_never_a_context_row():
    prots = {"core1": _prot("core1", "core", 10), "core2": _prot("core2", "core", 500)}
    ctx = glm.context_contigs([_row("core2")], prots, [(0, "core1", 70.0)], "core")
    assert ctx == {}


def test_a_reference_gene_not_found_gives_no_context_row():
    """MISSING_NOT_FOUND has no match to sit beside. 'No hit under the filters' is not a location."""
    prots = {"core1": _prot("core1", "core", 10), **_node977()}
    ctx = glm.context_contigs([_row("c3", status="MISSING_NOT_FOUND")], prots, [(0, "core1", 70.0)], "core")
    assert ctx == {}


def test_at_most_three_context_rows_ranked_by_how_many_matches_each_contig_holds():
    prots = {"core1": _prot("core1", "core", 10)}
    rows = []
    for c, n in (("one", 1), ("two", 2), ("three", 3), ("four", 4)):
        for i in range(n):
            pid = f"{c}_{i}"
            prots[pid] = _prot(pid, c, 10 + 10 * i)
            rows.append(_row(pid))
    ctx = glm.context_contigs(rows, prots, [(0, "core1", 70.0)], "core")
    assert list(ctx) == ["four", "three", "two"]


def test_a_context_row_adds_nothing_to_the_drawn_matches_or_the_counts():
    """The guard that keeps this from becoming a rescue: context_contigs only reports windows. It returns contig
    windows and match counts, never matches, so nothing it reports can reach `drawn`, `not_drawn` or a caption."""
    prots = {"core1": _prot("core1", "core", 10), **_node977()}
    drawn = [(0, "core1", 70.0)]
    before = list(drawn)
    ctx = glm.context_contigs([_row("c3")], prots, drawn, "core")
    assert drawn == before
    for value in ctx.values():
        assert len(value) == 3
        assert all(isinstance(v, int) for v in value)
