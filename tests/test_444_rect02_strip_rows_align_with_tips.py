"""v9.7.444: rect02 strip cells must sit on their tips all the way down the tree.

aplot drew the tree panel over [scale-bar y, n + 0.6] and each strip over its default [0.4, n + 0.6], so strip rows
were slightly shorter than tree rows and cells drifted off their tips toward the bottom (half a row at tip 21 of 22).
The renderer now gives the strips the tree's y range and refuses to write a figure whose panels differ.
"""
import csv, os, random, shutil, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKGS = '"ape","ggtree","ggplot2","aplot","treeio","patchwork"'


def _rscript():
    r = shutil.which("Rscript")
    if not r:
        pytest.skip("R graphics stack not installed")
    probe = subprocess.run([r, "-e", f"quit(status=if(all(sapply(c({PKGS}),requireNamespace,quietly=TRUE))) 0 else 1)"],
                           capture_output=True)
    if probe.returncode:
        pytest.skip("R graphics packages not installed")
    return r


def _tree(n):
    rng = random.Random(444)
    nodes = [f"T{i:02d}:{rng.uniform(0.005, 0.05):.4f}" for i in range(n - 1)]
    while len(nodes) > 1:
        a, b = nodes.pop(rng.randrange(len(nodes))), nodes.pop(rng.randrange(len(nodes)))
        nodes.append(f"({a},{b}):{rng.uniform(0.002, 0.03):.4f}")
    return f"({nodes[0]},OUTGROUP_REF:0.2);", [f"T{i:02d}" for i in range(n - 1)] + ["OUTGROUP_REF"]


def test_rendered_panels_share_one_y_range(tmp_path):
    r = _rscript()
    newick, tips = _tree(24)
    tree = tmp_path / "tree.nwk"; tree.write_text(newick)
    meta = tmp_path / "labels.tsv"
    with meta.open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t"); w.writerow(["tip", "label", "category", "category_raw", "source"])
        for t in tips:
            w.writerow([t, t + " [plant-associated] (NR_123456.1)", "plant-associated", "plant", "US"])
    out = tmp_path / "figure"
    cp = subprocess.run([r, str(ROOT / "tools/ggtree_rect_heatmap.R"), str(tree), str(meta), str(out), "T03"],
                        capture_output=True, text=True, timeout=180,
                        env=dict(os.environ, SAPOTE_PYTHON=shutil.which("python3") or "python3", GG_STRIPS="2"))
    assert cp.returncode == 0, cp.stdout + cp.stderr
    line = next((l for l in cp.stdout.splitlines() if l.startswith("PANEL_Y_RANGES:")), None)
    assert line, "renderer did not report its panel y ranges (the alignment guard did not run)"
    ranges = [x.strip() for x in line.split(":", 1)[1].split("|")]
    assert len(ranges) == 3, ranges          # tree + two strips were all measured
    assert len(set(ranges)) == 1, ranges     # and all span the same y range


def _guard(aligned):
    r = _rscript()
    expand = "ggplot2::scale_y_discrete(limits=to, expand=ggplot2::expansion(add=c(1 + 0.12, 0.6)))" if aligned else "NULL"
    code = f"""
suppressPackageStartupMessages({{library(ape);library(ggtree);library(ggplot2);library(aplot)}})
source({str(ROOT / 'tools/tree_annotation_geometry.R')!r})
set.seed(4); tr <- rtree(22)
p <- ggtree(tr) + geom_treescale(width=0.1, x=0, y=-0.12, offset=0.08); to <- rev(get_taxa_name(p))
d <- data.frame(tip=factor(to, levels=to), v=seq_along(to))
s <- function() ggplot(d, aes(0, tip, fill=v)) + geom_tile() + {expand}
cat(validate_panel_ranges(s() |> insert_left(s(), width=1) |> insert_left(p, width=13)), sep="|")
"""
    return subprocess.run([r, "-e", code], capture_output=True, text=True, timeout=120)


def test_guard_refuses_strips_that_do_not_share_the_tree_range():
    cp = _guard(aligned=False)
    assert cp.returncode != 0
    assert "ANNOTATION_PANEL_RANGE_MISMATCH" in cp.stderr, cp.stderr


def test_guard_accepts_panels_that_share_the_tree_range():
    cp = _guard(aligned=True)
    assert cp.returncode == 0, cp.stderr
    assert len(set(cp.stdout.strip().split("|"))) == 1 and cp.stdout.count("|") == 2, cp.stdout
