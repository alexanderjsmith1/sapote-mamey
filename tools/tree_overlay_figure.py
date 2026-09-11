#!/usr/bin/env python3
"""tree_overlay_figure.py — ONE tree, MANY overlay matrices.

Render a fixed phylogeny once and drape any number of per-tip quantitative matrices over it,
producing one aligned tree+heatmap figure per matrix (and, optionally, a combined multi-strip
figure). The tree is the constant; matrices are swappable overlays — BGC class depth, KS-domain
burden, novelty load, lead-tier counts, bioassay, anything keyed to tree tips.

DESIGN INVARIANTS (borrowed from tools/tree_bgc_overlay.py, deliberately):
- The tree is CONSUMED, never re-inferred, re-rooted for topology, or relabeled. Display rooting on
  a declared outgroup is allowed; it changes drawing order only.
- Tip -> data binding is through an EXPLICIT crosswalk. No fuzzy matching, no prefix repair. A tree
  tip absent from the crosswalk is a hard error (never a silent drop). This exists because
  near-name collisions are real and dangerous: e.g. a "gossypii" filename may be *Actinophytocola*
  gossypii, NOT the tree's *Streptomyces* gossypii — a fuzzy match would plot the wrong organism.
- A tip present in the crosswalk but absent from a given matrix is rendered "not profiled" (a thin
  grey mark), never as zero. Missing != absence. (Set overlays[].omit_unprofiled=true to drop such
  tips from that figure instead.)

Counts/values are whatever the matrix says; this tool renders, it does not compute biology. Any
antiSMASH product-class matrix is a CLASS-LEVEL capacity inventory, not a function/novelty claim.

Usage:  tree_overlay_figure.py <config.json>
Config schema: see _CONFIG_DOC below and tests/test_tree_overlay_figure.py.
"""
from __future__ import annotations

import csv
import json
import contextlib
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from Bio import Phylo

_CONFIG_DOC = """
{
  "tree": "iqtree_relabeled.treefile",          # newick; consumed as-is
  "outgroup_substring": "OUTGROUP",             # optional; display rooting only
  "crosswalk": "crosswalk.tsv",                 # cols: newick_label, display_label, role
                                                #   role in {STUDY, REFERENCE, OUTGROUP}
  "out_dir": "figs",                            # where PNG/PDF/receipts are written
  "figure_title": "…",                          # top suptitle, shared by every overlay
  "tree_caption": "Core-genome phylogram · …",  # left-panel heading
  "claim_footer": "…",                          # mandatory claim-safety line
  "overlays": [
    {
      "id": "bgc_classdepth",
      "title": "BGC regions per class · antiSMASH product roll-up",
      "matrix": "classdepth.tsv",               # col 1 = tip id (matches crosswalk newick_label),
                                                #   remaining cols = numeric columns
      "colormap": "YlGnBu",                     # any matplotlib cmap
      "annotate": true,                         # print the value in each cell
      "omit_unprofiled": false                  # drop tips absent from THIS matrix
    }
  ]
}
"""


class OverlayHold(Exception):
    """Raised on any binding/validation failure — the figure is never drawn on a bad input."""


def _read_tsv(path: Path, required: tuple[str, ...]) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        missing = [c for c in required if c not in (reader.fieldnames or [])]
        if missing:
            raise OverlayHold(f"{path.name} missing columns {missing}")
        return list(reader)


def _load_crosswalk(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_tsv(path, ("newick_label", "display_label", "role"))
    by_tip: dict[str, dict[str, str]] = {}
    for i, r in enumerate(rows, 1):
        if not all(r[c].strip() for c in ("newick_label", "display_label", "role")):
            raise OverlayHold(f"crosswalk row {i} incomplete")
        if r["role"] not in {"STUDY", "REFERENCE", "OUTGROUP"}:
            raise OverlayHold(f"crosswalk row {i}: invalid role {r['role']!r}")
        if r["newick_label"] in by_tip:
            raise OverlayHold(f"duplicate crosswalk newick_label {r['newick_label']!r}")
        by_tip[r["newick_label"]] = r
    return by_tip


def _load_matrix(path: Path) -> tuple[list[str], dict[str, dict[str, float]]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh, delimiter="\t")
        header = next(reader)
        cols = header[1:]
        mat: dict[str, dict[str, float]] = {}
        for row in reader:
            if not row or not row[0].strip():
                continue
            vals: dict[str, float] = {}
            for c, v in zip(cols, row[1:]):
                v = v.strip()
                vals[c] = float(v) if v not in ("", "NA", "na") else None
            mat[row[0].strip()] = vals
    return cols, mat


def _tree_geometry(tree):
    tree.ladderize()
    terms = tree.get_terminals()
    ypos = {t.name: i for i, t in enumerate(terms)}
    depths = tree.depths()

    def clade_y(cl):
        tl = cl.get_terminals()
        return sum(ypos[t.name] for t in tl) / len(tl)

    return terms, ypos, depths, clade_y


def _render(tree, geom, crosswalk, overlay, cfg, out_dir: Path) -> dict:
    terms, ypos, depths, clade_y = geom
    n = len(terms)
    cols, mat = _load_matrix(Path(cfg["_root"], overlay["matrix"]))

    # bind: every tip must be in the crosswalk (hard). Matrix coverage is per-tip optional.
    profiled = {t.name for t in terms if t.name in mat}
    drawn_terms = [t for t in terms
                   if not (overlay.get("omit_unprofiled") and t.name not in mat)]
    # per-column colour scale over the profiled tips only
    colmax = {c: max([mat[s][c] for s in profiled if mat[s].get(c) is not None] + [1.0])
              for c in cols}
    cmap = plt.get_cmap(overlay.get("colormap", "YlGnBu"))

    fig, (axT, axH) = plt.subplots(
        1, 2, figsize=(13.5, max(4.0, 0.34 * n + 1.8)),
        gridspec_kw={"width_ratios": [1.35, max(0.5, 0.16 * len(cols))], "wspace": 0.02})

    # --- tree ---
    def draw(cl):
        x = depths[cl]
        if cl.clades:
            ys = [ypos[c.name] if c.is_terminal() else clade_y(c) for c in cl.clades]
            axT.plot([x, x], [min(ys), max(ys)], color="#333", lw=1.0)
            for c in cl.clades:
                cy = ypos[c.name] if c.is_terminal() else clade_y(c)
                axT.plot([x, depths[c]], [cy, cy], color="#333", lw=1.0)
                draw(c)
    draw(tree.root)
    for t in terms:
        role = crosswalk[t.name]["role"]
        study = role == "STUDY"
        axT.text(depths[t] + max(depths.values()) * 0.01, ypos[t.name],
                 crosswalk[t.name]["display_label"], va="center", ha="left",
                 fontsize=8.3, fontweight="bold" if study else "normal",
                 color="#0b3d91" if study else ("#111" if role == "OUTGROUP" else "#444"))
    for cl in tree.get_nonterminals():
        if cl.name and "/" in str(cl.name):
            # v9.7.408: a support label that is not an integer simply gets no marker. Stated with
            # suppress() rather than try/except/pass so the intent is in the syntax.
            with contextlib.suppress(ValueError):
                if int(str(cl.name).split("/")[-1]) >= 90:
                    axT.plot(depths[cl], clade_y(cl), "o", ms=3.0, color="#333", zorder=5)
    TOP = -1.9
    axT.set_ylim(n - 0.5, TOP); axT.set_xlim(-0.01, max(depths.values()) * 1.55)
    axT.axis("off")
    axT.text(0, TOP, cfg.get("tree_caption", ""), fontsize=10, fontweight="bold",
             va="bottom", ha="left")
    mx = max(depths.values())
    sb = round(mx / 5, 2) or 0.05
    axT.plot([0, sb], [n - 0.2, n - 0.2], color="#333", lw=1.4)
    axT.text(sb / 2, n - 0.55, f"{sb} subs/site", ha="center", va="top", fontsize=7.3)
    axT.plot([], [], "o", color="#333", ms=3.0, label="support ≥ 90")
    axT.legend(loc="lower right", fontsize=7.3, frameon=False)

    # --- heatmap ---
    for j, c in enumerate(cols):
        axH.text(j + 0.5, -0.55, c, ha="center", va="bottom", fontsize=7.6, fontweight="bold")
    for t in drawn_terms:
        y = ypos[t.name]
        if t.name in mat:
            for j, c in enumerate(cols):
                v = mat[t.name].get(c)
                if v is None:
                    continue
                frac = v / colmax[c]
                axH.add_patch(Rectangle((j, y - 0.42), 1.0, 0.84,
                              facecolor=cmap(0.15 + 0.8 * frac), edgecolor="white", lw=0.8))
                if overlay.get("annotate", True):
                    axH.text(j + 0.5, y, f"{v:g}", ha="center", va="center", fontsize=7.2,
                             color="white" if frac > 0.55 else "#222")
        else:
            axH.plot(len(cols) / 2, y, marker="_", ms=7, color="#bbb")
    axH.set_xlim(0, len(cols)); axH.set_ylim(n - 0.5, TOP); axH.axis("off")
    axH.text(0, TOP, overlay["title"] + "\ncolored = profiled · grey – = not profiled",
             fontsize=9.5, fontweight="bold", va="bottom", ha="left")

    fig.suptitle(cfg.get("figure_title", ""), fontsize=12.5, fontweight="bold",
                 x=0.02, ha="left", y=0.998)
    fig.text(0.02, 0.006, cfg["claim_footer"], fontsize=7.0, color="#555", wrap=True)
    fig.subplots_adjust(top=0.925, bottom=0.075, left=0.01, right=0.99)

    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / f"{cfg.get('out_stem','tree_overlay')}__{overlay['id']}"
    for ext in ("png", "pdf"):
        fig.savefig(f"{prefix}.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)
    receipt = {
        "overlay_id": overlay["id"], "n_tips": n, "n_profiled": len(profiled),
        "n_unprofiled": n - len(profiled), "columns": cols,
        "omit_unprofiled": bool(overlay.get("omit_unprofiled")),
        "outputs": [f"{prefix.name}.png", f"{prefix.name}.pdf"],
        "claim_footer": cfg["claim_footer"],
    }
    (Path(f"{prefix}_receipt.json")).write_text(json.dumps(receipt, indent=2))
    return receipt


def build(config_path: str | Path) -> list[dict]:
    config_path = Path(config_path)
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    cfg["_root"] = str(config_path.resolve().parent)
    root = Path(cfg["_root"])
    if "claim_footer" not in cfg or len(str(cfg["claim_footer"]).strip()) < 20:
        raise OverlayHold("config must carry a substantive claim_footer")
    tree = Phylo.read(str(Path(root, cfg["tree"])), "newick")
    og = cfg.get("outgroup_substring")
    if og:
        m = [t for t in tree.get_terminals() if og.lower() in (t.name or "").lower()]
        if m:
            tree.root_with_outgroup(m[0])
    crosswalk = _load_crosswalk(Path(root, cfg["crosswalk"]))
    tips = {t.name for t in tree.get_terminals()}
    missing = sorted(tips - set(crosswalk))
    if missing:
        raise OverlayHold(f"tree tips with no crosswalk row (no silent drop): {missing}")
    geom = _tree_geometry(tree)
    out_dir = Path(root, cfg.get("out_dir", "."))
    receipts = [_render(tree, geom, crosswalk, ov, cfg, out_dir) for ov in cfg["overlays"]]
    return receipts


def main(argv=None):
    argv = argv or sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__, _CONFIG_DOC, sep="\n")
    try:
        receipts = build(argv[0])
    except OverlayHold as e:
        print(f"OVERLAY_HOLD: {e}", file=sys.stderr); return 2
    for r in receipts:
        print(f"  {r['overlay_id']}: {r['n_profiled']}/{r['n_tips']} tips profiled -> {r['outputs'][0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
