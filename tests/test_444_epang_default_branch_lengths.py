"""v9.7.444: EPA-ng default branch lengths are restored before a placement tree is drawn.

EPA-ng writes -ln 0.9 = 0.1053605157 where it has not estimated a length:
- in the jplace tree, on reference branches that are exactly 0 in ref.tree;
- as some best-placement pendants.

Observed values: 12, 28, 23 and 118 reference edges on four real runs, and 16 of 100 bee-Streptomyces pendants.
RAxML-NG gives one isolate 0.0149 against EPA-ng's 0.1054.

verify_graft() checks the graft against the jplace tree, so it passes both defaults.
"""
import inspect
import io
import json
import shutil
from pathlib import Path

import pytest

Phylo = pytest.importorskip("Bio.Phylo")

from tools import graft_integrity as gi
from tools import phylo_place

PH = gi.PLACEHOLDER
REF = "((A:0.02,B:0.0):0.03,(C:0.04,D:0.01):0.02,OG:0.2);"
# EPA-ng's jplace backbone: B's zero branch comes back as the default, everything else identical.
JPLACE_TREE = "((A:0.02{0},B:0.1053605157{1}):0.03{2},(C:0.04{3},D:0.01{4}):0.02{5},OG:0.2{6}){7};"


def _jplace(tmp, placements):
    data = {"tree": JPLACE_TREE, "version": 3,
            "fields": ["edge_num", "likelihood", "like_weight_ratio", "distal_length", "pendant_length"],
            "placements": placements, "metadata": {}}
    p = tmp / "epa_result.jplace"
    p.write_text(json.dumps(data))
    return p


def _write(tmp, name, newick):
    p = tmp / name
    p.write_text(newick + "\n")
    return p


def _refs():
    return frozenset({"A", "B", "C", "D", "OG"})


def test_backbone_defaults_finds_the_reset_zero_edge(tmp_path):
    jp = _jplace(tmp_path, [{"p": [[3, -1.0, 1.0, 0.01, 0.02]], "n": ["Q1"]}])
    reset, other = gi.backbone_defaults(jp, _write(tmp_path, "ref.tree", REF))
    assert len(reset) == 1 and other == []


def test_backbone_defaults_refuses_a_different_backbone(tmp_path):
    jp = _jplace(tmp_path, [{"p": [[3, -1.0, 1.0, 0.01, 0.02]], "n": ["Q1"]}])
    other_topology = _write(tmp_path, "ref.tree", "((A:0.02,C:0.0):0.03,(B:0.04,D:0.01):0.02,OG:0.2);")
    with pytest.raises(ValueError, match="topology"):
        gi.backbone_defaults(jp, other_topology)


def test_restore_reference_edges_matches_ref_tree_and_keeps_query_pendants():
    # graft: Q1 on B's (default) edge, Q2 on C's edge with its own pendant
    graft = Phylo.read(io.StringIO(
        "((A:0.02,(B:0.1,Q1:0.03):0.0053605157):0.03,((C:0.03,Q2:0.015):0.01,D:0.01):0.02,OG:0.2);"), "newick")
    changed = gi.restore_reference_edges(graft, Phylo.read(io.StringIO(REF), "newick"), _refs())
    assert changed == 1
    q2 = next(t for t in graft.get_terminals() if t.name == "Q2")
    assert q2.branch_length == pytest.approx(0.015)          # a query pendant is never rescaled
    for q in [t for t in graft.get_terminals() if t.name.startswith("Q")]:
        graft.prune(q)
    got = gi._split_lengths(graft, _refs())
    want = gi._split_lengths(Phylo.read(io.StringIO(REF), "newick"), _refs())
    assert got.keys() == want.keys()
    assert all(abs(got[k] - want[k]) < 1e-9 for k in want)


def test_apply_pendant_estimates_on_a_shared_stem():
    # gappa cherry on one edge: stem 0.042635 + tip 0.062726 = default for Q1; Q2 tip 0 (path = default too)
    graft = Phylo.read(io.StringIO(
        "((A:0.02,((Q1:0.0627255157,Q2:0.0627255157):0.042635,B:0.0):0.0):0.03,(C:0.04,D:0.01):0.02,OG:0.2);"),
        "newick")
    est = {"Q1": 0.0635, "Q2": 0.0}
    assert gi.apply_pendant_estimates(graft, est, _refs()) == 2
    parent = {c: p for p in graft.find_clades() for c in p.clades}
    for name, want in est.items():
        tip = next(t for t in graft.get_terminals() if t.name == name)
        path, cur = 0.0, tip
        while all(x.name not in _refs() for x in cur.get_terminals()):
            path += cur.branch_length or 0.0
            cur = parent[cur]
        assert path == pytest.approx(want, abs=1e-9)
    assert all((c.branch_length or 0.0) >= 0 for c in graft.find_clades())


def test_apply_pendant_estimates_refuses_a_non_default_path():
    graft = Phylo.read(io.StringIO("((A:0.02,(B:0.0,Q1:0.05):0.0):0.03,(C:0.04,D:0.01):0.02,OG:0.2);"), "newick")
    with pytest.raises(ValueError, match="not the EPA-ng default"):
        gi.apply_pendant_estimates(graft, {"Q1": 0.01}, _refs())


def test_generate_restored_graft_without_raxml_lists_defaults(tmp_path):
    jp = _jplace(tmp_path, [{"p": [[0, -1.0, 1.0, 0.01, PH]], "n": ["Q1"]}])
    graft = _write(tmp_path, "epa_result.newick", "((A:0.02,(B:0.1,Q1:0.1053605157):0.0053605157):0.03,"
                                                   "(C:0.04,D:0.01):0.02,OG:0.2);")
    out, n_reset, names, how = gi.generate_length_restored_graft(graft, jp, _write(tmp_path, "ref.tree", REF), tmp_path)
    assert n_reset == 1 and names == ["Q1"] and how == "NOT_REESTIMATED"
    ledger = (tmp_path / "BRANCH_LENGTH_RESTORE.tsv").read_text()
    assert "NOT_REESTIMATED" in ledger and "Q1" in ledger
    tree = Phylo.read(out, "newick")
    assert not any(abs((c.branch_length or 0) - PH) < 1e-6 and c.name != "Q1" for c in tree.find_clades())


@pytest.mark.skipif(not shutil.which("raxml-ng"), reason="raxml-ng not on PATH")
def test_reestimate_replaces_the_default_pendant(tmp_path):
    import random
    random.seed(1)
    base = [random.choice("ACGT") for _ in range(300)]

    def mut(seq, n):
        s = list(seq)
        for i in random.sample(range(len(s)), n):
            s[i] = random.choice([c for c in "ACGT" if c != s[i]])
        return "".join(s)
    seqs = {"A": mut(base, 6), "B": mut(base, 6), "C": mut(base, 12), "D": mut(base, 9), "OG": mut(base, 60)}
    seqs["Q1"] = mut(seqs["B"], 3)
    (tmp_path / "ref.aln.fasta").write_text("".join(f">{k}\n{v}\n" for k, v in seqs.items() if k != "Q1"))
    (tmp_path / "query.aligned.fasta").write_text(f">Q1\n{seqs['Q1']}\n")
    jp = _jplace(tmp_path, [{"p": [[1, -1.0, 1.0, 0.0, PH]], "n": ["Q1"]}])
    graft = _write(tmp_path, "epa_result.newick", "((A:0.02,(B:0.1,Q1:0.1053605157):0.0053605157):0.03,"
                                                   "(C:0.04,D:0.01):0.02,OG:0.2);")
    out, _, names, how = gi.generate_length_restored_graft(
        graft, jp, _write(tmp_path, "ref.tree", REF), tmp_path, ref_aln=tmp_path / "ref.aln.fasta",
        query_aln=tmp_path / "query.aligned.fasta", model="GTR+G", raxml=shutil.which("raxml-ng"))
    assert how == "RAXML_NG_EVALUATE"
    q = next(t for t in Phylo.read(out, "newick").get_terminals() if t.name == "Q1")
    assert abs(q.branch_length - PH) > 1e-3                  # estimated, no longer the default
    assert q.branch_length < 0.06                             # 3 of 300 sites differ from B


def test_report_draws_the_restored_graft():
    src = inspect.getsource(phylo_place.cmd_report)
    assert "generate_length_restored_graft" in src
    assert "BRANCH_LENGTHS_NOT_RESTORED" in src
    # the restored graft is created before the neighbourhood table and every figure are built from `graft`
    assert src.index("generate_length_restored_graft(") < src.index("_grafted_neighborhoods(graft")
