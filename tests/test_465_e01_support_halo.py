"""MAX4_SUPPORT_HALO in tools/render_max4_tree.R (with tools/sapote_support_labels.R).
Support labels are anchored at their node with a white halo; a label goes below the branch or right of the node only when a
branch line or tip symbol is in the way; a y nudge of at most MAX4_SUPPORT_NUDGE_PT pt separates labels that still collide.
Synthetic data only. Overlaps are measured from the SVG with tools/svg_label_overlaps.py. Drawing tests skip without R."""
import csv
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "max4_tree_figure.py"
RENDERER = ROOT / "tools" / "render_max4_tree.R"
HELPER = ROOT / "tools" / "sapote_support_labels.R"
MEASURE = ROOT / "tools" / "svg_label_overlaps.py"
# Short internal branches so the default spots crowd: one label must go below its branch and one right of its node.
TREE = ("(((A1:0.02,(B1:0.0005,(C1:0.002,D1:0.002)80/80:0.0004)90/93:0.006)70/96:0.004,(E1:0.03,(I1:0.01,J1:0.02)50/95:0.001)"
        "66/77:0.002)88/91:0.05,(F1:0.20,G1:0.15)60/79:0.10,H1:0.60);\n")
PKGS = ("ape", "ggtree", "ggplot2", "patchwork", "phangorn", "ggrepel", "svglite")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M4 = _load(TOOL, "max4_tree_figure_halo_uut")
MEAS = _load(MEASURE, "svg_label_overlaps_uut")


def _r_has(*pkgs):
    rs = shutil.which("Rscript")
    if not rs:
        return False
    code = "q(status=as.integer(!all(vapply(c(%s),requireNamespace,TRUE,quietly=TRUE))))" % ",".join(f"'{p}'" for p in pkgs)
    return subprocess.run([rs, "-e", code], capture_output=True).returncode == 0


def _inputs(tmp_path):
    tree = tmp_path / "t.treefile"
    tree.write_text(TREE)
    tips = re.findall(r"([A-J]1):", TREE)
    meta = tmp_path / "meta.tsv"
    with meta.open("w", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["tip", "role", "label_concise", "source_display", "geography_display"])
        for t in tips:
            w.writerow([t, "QUERY" if t == "A1" else "REFERENCE", f"Synthetica sp. {t}", "soil", "Chile"])
    return tree, meta


def _render(tmp_path, stem, *extra):
    tree, meta = _inputs(tmp_path)
    rc = M4.main(["render", "--tree", str(tree), "--metadata", str(meta), "--out", str(tmp_path / stem),
                  "--set", "SUPPORT_MIN=50", "--set", "WIDTH=7.5", "--set", "DPI=150", "--set", "MIN_BRANCH=1.0", *extra])
    receipt = json.loads((tmp_path / f"{stem}_receipt.json").read_text())
    assert rc == 0, receipt
    return receipt


def test_halo_options_are_listed_and_the_helper_ships():
    r = RENDERER.read_text()
    for opt in ("SUPPORT_HALO", "SUPPORT_NUDGE_PT", "SUPPORT_SEED"):
        assert f"'MAX4_{opt}'" in r and opt in M4.OPTIONS
    assert "sapote_support_labels.R" in r and HELPER.exists() and MEASURE.exists()
    h = HELPER.read_text()
    assert "max.time = Inf" in h and "bg.colour = 'white'" in h and "/Users/" not in h


def test_halo_render_has_no_overlaps_and_reruns_identically(tmp_path):
    if not _r_has(*PKGS):
        pytest.skip("R tree packages, ggrepel or svglite not installed")
    rec = _render(tmp_path, "a", "--set", "SUPPORT_HALO=1")
    _render(tmp_path, "b", "--set", "SUPPORT_HALO=1")
    line = next(l for l in rec["renderer_stdout"] if l.startswith("support halo:"))
    assert line.startswith("support halo: 7 labels") and "left-below 1" in line and "right-centre 1" in line, line
    for pad in (0.0, 0.8):   # glyph boxes, then the halo's reach
        n, rows, _ = MEAS.measure(str(tmp_path / "a.svg"), pad)
        assert n == 7 and rows == [], rows
    strip = lambda p: [l for l in p.read_text().splitlines() if "Sapote-Mamey" not in l]
    assert strip(tmp_path / "a.svg") == strip(tmp_path / "b.svg")


UNIT = r"""
suppressPackageStartupMessages(library(ggplot2)); source(commandArgs(TRUE)[1])
nd <- data.frame(x = c(0, 0), y = c(0, 3), label = c('81', '93'))           # 1 data unit = 1 pt
segs <- data.frame(x0 = c(0.6, -20), y0 = c(-20, -1.5), x1 = c(0.6, 0), y1 = c(20, -1.5))
hl <- support_halo_layers(nd, 8, 1, 1, segs = segs, max_nudge = 4)
tb <- attr(hl, 'table'); cat(sprintf('%s %s %.2f %d\n', tb$label, tb$side, tb$dy, tb$group), sep = '')
"""


def test_helper_nudge_is_capped_and_clears_lines_and_labels(tmp_path):
    """Two labels 3 pt apart, a line just right of the nodes and a branch 1.5 pt below: only a y nudge separates them."""
    if not _r_has("ggplot2", "ggrepel"):
        pytest.skip("R ggplot2 or ggrepel not installed")
    script = tmp_path / "unit.R"
    script.write_text(UNIT)
    out = subprocess.run([shutil.which("Rscript"), str(script), str(HELPER)], capture_output=True, text=True, check=True).stdout
    rows = [l.split() for l in out.strip().splitlines()]
    assert len(rows) == 2 and all(int(r[3]) > 0 for r in rows)          # one collision group
    dys = [float(r[2]) for r in rows]
    assert max(abs(d) for d in dys) <= 4.0 and any(d != 0 for d in dys)
    h, w, gx, gy, clear, pad = 0.716 * 8, 2 * 0.556 * 8, 1.0, 1.2, 0.8, 1.6
    boxes = []
    for (label, side, dy, _), y in zip(rows, (0.0, 3.0)):
        dy = float(dy)
        if side == "left-above":
            b = (-gx - w, y + gy + dy, -gx, y + gy + h + dy)
        elif side == "left-below":
            b = (-gx - w, y - gy - h + dy, -gx, y - gy + dy)
        else:
            b = (gx, y - h / 2 + dy, gx + w, y + h / 2 + dy)
        boxes.append(b)
        assert not (b[0] - clear < 0.6 < b[2] + clear)                               # vertical line at x = 0.6
        assert not (b[0] - clear < 0 and b[1] - clear < -1.5 < b[3] + clear)          # branch at y = -1.5, x <= 0
    (a0, a1, a2, a3), (b0, b1, b2, b3) = boxes
    assert not (a0 < b2 + pad and b0 < a2 + pad and a1 < b3 + pad and b1 < a3 + pad)  # labels apart by >= pad


AMBIG = r"""
suppressPackageStartupMessages({library(ggplot2); library(patchwork)}); source(commandArgs(TRUE)[1])
# Fig. 5 Micromonospora geometry in pt (1 data unit = 1 pt): node P (x 0, y 0) with a short branch to node Q (x 1.5, y 6);
# Q joins two tips at y 2 and 10; P's other child is a tip at y -6; P's parent sits at x -1.5. Before the rule, P's
# label went left of P and Q's right of Q, side by side across Q's vertical line.
nd <- data.frame(x = c(0, 1.5), y = c(0, 6), label = c('93', '80'))
segs <- data.frame(x0 = c(0, 0, 1.5, 1.5, 1.5, -1.5, -1.5), y0 = c(-6, 6, 2, 2, 10, 0, -12),
                   x1 = c(0, 1.5, 1.5, 9, 9, 0, -1.5), y1 = c(6, 6, 10, 2, 10, 0, 0))
hl <- support_halo_layers(nd, 8, 1, 1, segs = segs)
tb <- attr(hl, 'table'); cat(sprintf('%s %s %.2f\n', tb$label, tb$side, tb$dy), sep = '')
p <- ggplot(data.frame(x = c(0, 10), y = c(0, 50)), aes(x, y)) + geom_point() + scale_x_continuous(expand = c(0, 0))
pdf(NULL, width = 6, height = 4); sc <- tree_panel_scale(wrap_plots(list(p, p), widths = c(2, 1)), p, 6, 4); invisible(dev.off()); cat(sprintf('scale %.6f %.6f %.4f %.4f\n', sc[1], sc[2], sc[3], sc[4]))
"""


def test_side_by_side_labels_across_a_line_are_refused_and_the_scale_is_exact(tmp_path):
    if not _r_has("ggplot2", "ggrepel", "patchwork"):
        pytest.skip("R ggplot2, ggrepel or patchwork not installed")
    script = tmp_path / "ambig.R"
    script.write_text(AMBIG)
    out = subprocess.run([shutil.which("Rscript"), str(script), str(HELPER)], capture_output=True, text=True, check=True).stdout
    lines = out.strip().splitlines()
    place = {l.split()[0]: (l.split()[1], float(l.split()[2])) for l in lines if not l.startswith("scale")}
    h, w, gx, gy = 0.716 * 8, 2 * 0.556 * 8, 1.0, 1.2
    def box(x, y, side, dy):
        if side == "left-above":
            return (x - gx - w, y + gy + dy, x - gx, y + gy + h + dy)
        if side == "left-below":
            return (x - gx - w, y - gy - h + dy, x - gx, y - gy + dy)
        return (x + gx, y - h / 2 + dy, x + gx + w, y + h / 2 + dy)
    a = box(0.0, 0.0, *place["93"]); b = box(1.5, 6.0, *place["80"])
    if a[0] > b[0]:
        a, b = b, a
    side_by_side = 0 <= b[0] - a[2] <= 4 and not (a[1] > b[3] + 1 or b[1] > a[3] + 1)
    assert not side_by_side, place
    assert max(abs(place[k][1]) for k in place) <= 4.0
    sc = [float(v) for v in next(l for l in lines if l.startswith("scale")).split()[1:]]
    assert 0 < sc[2] < 6 and 0 < sc[3] < 4                       # panel smaller than the page
    assert abs(sc[0] - 10 / (sc[2] * 72)) < 1e-6                  # x: no expansion
    assert abs(sc[1] - 50 * 1.1 / (sc[3] * 72)) < 1e-6            # y: default 5 % expansion each side


def test_measure_flags_an_ambiguous_pair(tmp_path):
    svg = tmp_path / "pair.svg"
    svg.write_text("""<svg xmlns='http://www.w3.org/2000/svg' width='100pt' height='100pt' viewBox='0 0 100 100'>
<text x='50.00' y='50.00' text-anchor='end' style='font-size: 8.00px;fill: #595959;' textLength='8.88px'>93</text>
<text x='53.50' y='49.00' style='font-size: 8.00px;fill: #595959;' textLength='8.88px'>80</text>
<line x1='51.50' y1='30.00' x2='51.50' y2='60.00' style='stroke-width: 0.85;' />
</svg>""")
    n, rows, _ = MEAS.measure(str(svg), 0.0, ambig_gap=4.0)
    assert n == 2 and [r[0] for r in rows].count("ambiguous-pair") == 1
    n, rows, _ = MEAS.measure(str(svg), 0.0, ambig_gap=2.0)
    assert [r[0] for r in rows].count("ambiguous-pair") == 0      # the gap is 3.5 pt


def test_halo_off_keeps_the_old_labels(tmp_path):
    if not _r_has(*PKGS):
        pytest.skip("R tree packages, ggrepel or svglite not installed")
    rec = _render(tmp_path, "d")
    assert not any(line.startswith("support halo") for line in rec["renderer_stdout"])
    svg = (tmp_path / "d.svg").read_text()
    assert not re.search(r"fill: #FFFFFF;[^>]*>\d{2}</text>", svg)   # no white halo copies of support numbers
