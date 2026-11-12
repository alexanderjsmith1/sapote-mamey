"""Tests for tools/protein_ssn_render.py."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "protein_ssn_render.py"
spec = importlib.util.spec_from_file_location("ssn", TOOL)
ssn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ssn)


def nodes_tsv(path, rows, cols=("node", "identity", "group", "shape_class")):
    with open(path, "w", newline="") as f:
        w = csv.writer(f, delimiter="\t"); w.writerow(cols); w.writerows(rows)
    return path


def hit(q, s, pid, qlen=300, slen=300, qs=1, qe=300, ss=1, se=300):
    return "\t".join(map(str, (q, s, pid, qe - qs + 1, qlen, slen, qs, qe, ss, se, "1e-50", 200))) + "\n"


@pytest.fixture
def small(tmp_path):
    rows = [(f"p{i}", f"G{i} / c{i} / region001 / BGC00{i} / tag{i}", "A" if i < 4 else "B", "X" if i % 2 else "Y")
            for i in range(1, 8)]
    n = nodes_tsv(tmp_path / "nodes.tsv", rows)
    h = tmp_path / "hits.tsv"
    h.write_text(
        hit("p1", "p2", 62) + hit("p2", "p1", 60) + hit("p2", "p3", 45) + hit("p3", "p1", 33)   # triangle 1-2-3
        + hit("p4", "p5", 55)                                                                  # pair 4-5
        + hit("p6", "p7", 90, qlen=300, slen=900, ss=1, se=300)                                # p7 covered 0.33
        + hit("p1", "p1", 100))                                                                # self hit ignored
    return n, h


def test_edges_keep_best_identity_and_apply_cover(small):
    n, h = small
    nodes = ssn.load_nodes(n)
    pairs = ssn.load_edges(h, nodes, 0.5)
    assert pairs == {("p1", "p2"): 62.0, ("p2", "p3"): 45.0, ("p1", "p3"): 33.0, ("p4", "p5"): 55.0}
    assert ("p6", "p7") in ssn.load_edges(h, nodes, 0.3)


def test_cluster_counts_per_cutoff(small):
    n, h = small
    nodes = ssn.load_nodes(n); pairs = ssn.load_edges(h, nodes, 0.5)
    s30, s50, s70 = (ssn.summarise(list(nodes), pairs, c) for c in (30, 50, 70))
    assert (s30["clusters_2plus"], s30["singletons"], s30["largest_cluster"]) == (2, 2, 3)
    assert (s50["edges"], s50["clusters_2plus"], s50["singletons"]) == (2, 2, 3)
    assert (s70["edges"], s70["clusters_2plus"], s70["singletons"]) == (0, 0, 7)


def test_pairs_lie_flat_and_clusters_do_not_overlap(small):
    n, h = small
    nodes = ssn.load_nodes(n); pairs = ssn.load_edges(h, nodes, 0.5)
    we = [(a, b, v / 100) for (a, b), v in pairs.items() if v >= 30]
    _, pos = ssn.packed_layout(list(nodes), we)
    assert pos["p4"][1] == pos["p5"][1]
    tri_x = [pos[p][0] for p in ("p1", "p2", "p3")]
    assert max(tri_x) < min(pos["p4"][0], pos["p5"][0])          # the pair sits to the right of the larger cluster
    assert all(pos[p][1] < min(pos[q][1] for q in ("p1", "p2", "p3", "p4", "p5")) for p in ("p6", "p7"))


@pytest.mark.parametrize("content,msg", [
    (hit("p1", "zz", 50), "not in the node table"),
    ("p1\tp2\t50\n", "expected 12"),
    (hit("p1", "p2", "x"), "non-numeric"),
])
def test_bad_hits_stop(small, content, msg, capsys):
    n, h = small
    h.write_text(content)
    with pytest.raises(SystemExit) as e:
        ssn.load_edges(h, ssn.load_nodes(n), 0.5)
    assert msg in str(e.value)


def test_bad_nodes_stop(tmp_path):
    with pytest.raises(SystemExit, match="twice"):
        ssn.load_nodes(nodes_tsv(tmp_path / "a.tsv", [("p1", "i", "A", ""), ("p1", "j", "A", "")]))
    with pytest.raises(SystemExit, match="blank"):
        ssn.load_nodes(nodes_tsv(tmp_path / "b.tsv", [("p1", "", "A", "")]))
    with pytest.raises(SystemExit, match="needs columns"):
        ssn.load_nodes(nodes_tsv(tmp_path / "c.tsv", [("p1", "A")], cols=("node", "group")))
    with pytest.raises(SystemExit, match="no proteins"):
        ssn.load_nodes(nodes_tsv(tmp_path / "d.tsv", []))


def test_colors_need_every_group_and_a_palette_key():
    with pytest.raises(SystemExit, match="no color for"):
        ssn.parse_colors("A=teal", ["A", "B"])
    with pytest.raises(SystemExit, match="palette key"):
        ssn.parse_colors("A=hotpink,B=teal", ["A", "B"])
    assert ssn.parse_colors(None, ["A", "B"]) == {"A": ssn.PALETTE["teal"], "B": ssn.PALETTE["gold"]}


def test_end_to_end_outputs_and_no_overwrite(small, tmp_path):
    n, h = small
    out = tmp_path / "out"
    summary = ssn.main(["--nodes", str(n), "--hits", str(h), "--outdir", str(out), "--stem", "fam",
                        "--cutoffs", "30,40,50", "--search", "test search 1.0"])
    for suf in (".png", ".svg", ".pdf", "_plot_only.png", "_edges.tsv", "_plotted.tsv", "_CAPTION.md", "_receipt.json"):
        assert (out / f"fam{suf}").stat().st_size > 0, suf
    rec = json.loads((out / "fam_receipt.json").read_text())
    assert rec["cutoffs"] == summary and rec["nodes_sha256"] == ssn.sha(n)
    assert rec["outputs"]["fam.png"] == ssn.sha(out / "fam.png")
    plotted = list(csv.DictReader(open(out / "fam_plotted.tsv"), delimiter="\t"))
    assert len(plotted) == 3 * 7 and all(r["identity"].count(" / ") == 4 for r in plotted)
    cap = (out / "fam_CAPTION.md").read_text()
    assert "test search 1.0" in cap and "not a shared product" in cap
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        ssn.main(["--nodes", str(n), "--hits", str(h), "--outdir", str(out), "--stem", "fam"])


def test_output_may_not_equal_an_input(small):
    n, h = small
    edges_as_hits = n.parent / "x_edges.tsv"          # the planned <stem>_edges.tsv is the hits input
    edges_as_hits.write_text(h.read_text())
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        ssn.main(["--nodes", str(n), "--hits", str(edges_as_hits), "--outdir", str(n.parent), "--stem", "x"])
    assert edges_as_hits.read_text() == h.read_text()


def test_decimal_cutoffs_and_limits(small, tmp_path):
    n, h = small
    s = ssn.main(["--nodes", str(n), "--hits", str(h), "--outdir", str(tmp_path / "d"), "--stem", "f",
                  "--cutoffs", "32.5,62"])
    assert [x["identity_cutoff"] for x in s] == [32.5, 62.0]
    with pytest.raises(SystemExit, match="one to three"):
        ssn.main(["--nodes", str(n), "--hits", str(h), "--outdir", str(tmp_path / "e"), "--stem", "f",
                  "--cutoffs", "30,40,50,60"])


def test_legend_order_follows_group_colors(small, tmp_path):
    n, h = small
    out = tmp_path / "o"
    ssn.main(["--nodes", str(n), "--hits", str(h), "--outdir", str(out), "--stem", "f", "--cutoffs", "30",
              "--group-colors", "B=coral,A=teal"])
    assert json.loads((out / "f_receipt.json").read_text())["legend_groups"] == ["B", "A"]
