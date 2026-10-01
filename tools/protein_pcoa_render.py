#!/usr/bin/env python3
"""Draw protein-class PCoA figures from an ordination kit: cohort proteins among reference and MIBiG proteins.

Input: a kit folder with out_<SET>/PCOA_<SET>.tsv (id, PC1, PC2, n_represented, source, strain, locus_tag, origin, ...),
optional NEAREST_<SET>.tsv (best reference/MIBiG identity per cohort protein) and RUN_<SET>.json (pct_axes).
A cohort table (strain, cohort) assigns cohort points to panels: --panel NAME=COHORT[,COHORT...].

What is drawn:
- reference genomes grey and MIBiG blue, sized by the members each centroid represents; cohort points on top;
- fill shows identity: solid when the best reference/MIBiG match is below --label-below % (default 70), open otherwise;
- the class tag bold at top left; no title and no other text on the artwork (the caption carries it);
- labels, one of two rules:
  * --top-strains N: up to N strains by name, one label each; strains with a point below --label-below come first (lowest
    identity first), then the strains whose points lie farthest from any reference/MIBiG point; each label sits on the
    strain's most isolated point of the same fill; a panel with N or fewer cohort points labels every point;
  * otherwise distance only: a point is labelled when its distance to the nearest reference/MIBiG point exceeds the
    --quantile of the background's own nearest-neighbour distances; same-strain points close together share a label
    ("x n"); more than --number-above labels are numbered, with the key in LABELS_<SET>_<PANEL>.tsv.
Points whose origin is in --drop-origins and strains in --exclude-strain are not drawn (they stay in the ordination).

Renderer: R (ggplot2 + ggrepel, tools/protein_pcoa_render.R) when Rscript has those packages, else matplotlib. Python
chooses the labels either way, writes ONE stamped data file per panel, runs R on exactly that file and checks that R
wrote outputs for the same stamp, so a failed run can never leave stale inputs for a later drawing.
Every SVG's visible text passes mamey.figure_policy's banned-wording check.

Outputs per panel in --out (new or empty): PCOA_<SET>_<PANEL>.pdf/.svg/.png (PNG 600 dpi), LABELS_<SET>_<PANEL>.tsv and
panel_<SET>_<PANEL>.json (counts, threshold, stamp, renderer).
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
try:  # CSV formula-cell guard, as every tools/ writer (tests/test_410_tools_csv_writer_coverage.py)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
from mamey.figure_policy import FigureTextRefusal, assert_no_banned_figure_text, svg_visible_text  # noqa: E402

_LOG = logging.getLogger("protein_pcoa_render")
R_SCRIPT = Path(__file__).resolve().parent / "protein_pcoa_render.R"
PALETTE = ["#0072B2", "#009E73", "#8C510A", "#CC79A7", "#56B4E9", "#D55E00"]   # mamey.figure_policy.COHORT_PALETTE order
REF_COLOUR, MIBIG_COLOUR = "#b5b5b5", "#3a78b5"


class RenderRefusal(RuntimeError):
    """An input or output that would make a figure wrong."""


def read_tsv(path: Path) -> list[dict]:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


# ---------------------------------------------------------------- selection (pure, tested)
def nn_dist(points, others, k_self=False):
    """Distance from each point to its nearest point in `others` (excluding itself when k_self, where points is others)."""
    import numpy as np
    if not len(points) or not len(others):
        return [math.inf] * len(points)
    P, O = np.asarray(points, float), np.asarray(others, float)
    try:
        from scipy.spatial import cKDTree
        d, _ = cKDTree(O).query(P, k=2 if k_self else 1)
        return [float(x) for x in (d[:, 1] if k_self else d)]
    except ImportError:
        out = np.empty(len(P))
        for i0 in range(0, len(P), 512):
            block = ((P[i0:i0 + 512, None, :] - O[None, :, :]) ** 2).sum(-1)
            if k_self:
                block[np.arange(block.shape[0]), np.arange(i0, i0 + block.shape[0])] = np.inf
            out[i0:i0 + 512] = np.sqrt(block.min(1))
        return [float(x) for x in out]


def quantile(values, q):
    v = sorted(values)
    if not v:
        return math.inf
    pos = (len(v) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return v[lo] + (v[hi] - v[lo]) * (pos - lo)


def choose_labels(cohort_pts, background, *, label_below=70.0, top_strains=0, q=0.95, number_above=30, span=None):
    """cohort_pts: list of dict(x, y, strain, pid (float or None)). background: list of (x, y).
    span: the plot span the 1.5% same-strain grouping distance is taken from. Pass the span of EVERY point in the kit
    (all cohorts, excluded strains included), as the v5 script does; when None it falls back to this panel's points.
    Returns (groups, texts, threshold, numbered): groups are lists of indices into cohort_pts."""
    bg_nn = nn_dist(background, background, k_self=True) if len(background) > 1 else []
    thr = quantile(bg_nn, q)
    d = nn_dist([(p["x"], p["y"]) for p in cohort_pts], background) if background else [math.inf] * len(cohort_pts)
    low = [p["pid"] is not None and p["pid"] < label_below for p in cohort_pts]
    idx = list(range(len(cohort_pts)))
    if top_strains:
        if len(idx) <= top_strains:
            groups = [[i] for i in idx]
        else:
            order = sorted(idx, key=lambda i: (0, cohort_pts[i]["pid"], i) if low[i] else (1, -d[i], i))
            groups, seen = [], set()
            for i in order:
                s = cohort_pts[i]["strain"]
                if s in seen:
                    continue
                seen.add(s)
                same = [j for j in idx if cohort_pts[j]["strain"] == s and low[j] == low[i]]
                groups.append([max(same, key=lambda j: (d[j], -j))])
                if len(groups) >= top_strains:
                    break
        return groups, [cohort_pts[g[0]]["strain"] for g in groups], thr, False
    if span is None:
        xs = [p["x"] for p in cohort_pts] + [u for u, _ in background]
        ys = [p["y"] for p in cohort_pts] + [v for _, v in background]
        span = max(max(xs) - min(xs), max(ys) - min(ys)) if xs else 1.0
    cand = sorted([i for i in idx if d[i] > thr], key=lambda i: (-d[i], i))
    groups = []
    for i in cand:
        g = next((g for g in groups if cohort_pts[g[0]]["strain"] == cohort_pts[i]["strain"]
                  and math.hypot(cohort_pts[g[0]]["x"] - cohort_pts[i]["x"], cohort_pts[g[0]]["y"] - cohort_pts[i]["y"]) < .015 * span),
                 None)
        (g.append(i) if g else groups.append([i]))
    numbered = len(groups) > number_above
    texts = []
    for n, g in enumerate(groups, 1):
        if numbered:
            texts.append(str(n))
        else:
            pids = [cohort_pts[k]["pid"] for k in g if cohort_pts[k]["pid"] is not None]
            texts.append(f"{cohort_pts[g[0]]['strain']}{' x' + str(len(g)) if len(g) > 1 else ''}"
                         + (f" ({min(pids):.0f}%)" if pids else ""))
    return groups, texts, thr, numbered


# ---------------------------------------------------------------- rendering
def r_available() -> bool:
    exe = shutil.which("Rscript")
    if not exe:
        return False
    r = subprocess.run([exe, "-e", 'q(status = as.integer(!all(sapply(c("ggplot2","ggrepel","jsonlite","svglite"), '
                              'requireNamespace, quietly = TRUE))))'], capture_output=True)
    return r.returncode == 0


def render_r(spec: Path, out_prefix: Path, stamp: str) -> None:
    r = subprocess.run(["Rscript", str(R_SCRIPT), str(spec), str(out_prefix), stamp], capture_output=True, text=True)
    if r.returncode != 0:
        raise RenderRefusal(f"R renderer failed for {out_prefix.name}: {r.stderr.strip()[-400:]}")
    done = Path(str(out_prefix) + ".stamp")
    if not done.exists() or done.read_text().strip() != stamp:
        raise RenderRefusal(f"R renderer did not confirm stamp {stamp} for {out_prefix.name}")
    done.unlink()


def render_matplotlib(spec: dict, out_prefix: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"pdf.fonttype": 42, "svg.fonttype": "none", "font.family": ["Arial", "Helvetica", "DejaVu Sans"]})
    fig, ax = plt.subplots(figsize=(7, 7.2))
    for layer, colour in (("ref", REF_COLOUR), ("mibig", MIBIG_COLOUR)):
        pts = [p for p in spec["points"] if p["layer"] == layer]
        if pts:
            ax.scatter([p["x"] for p in pts], [p["y"] for p in pts], s=[3 + 1.5 * math.sqrt(p["size"]) for p in pts], c=colour,
                       lw=0, alpha=.7, label=spec["legend"][layer])
    col = spec["colour"]
    lo = [p for p in spec["points"] if p["layer"] == "iso_low"]
    hi = [p for p in spec["points"] if p["layer"] == "iso_high"]
    if lo:
        ax.scatter([p["x"] for p in lo], [p["y"] for p in lo], s=22, c=col, edgecolors="black", lw=.4, zorder=3,
                   label=spec["legend"]["iso_low"])
    if hi:
        ax.scatter([p["x"] for p in hi], [p["y"] for p in hi], s=22, facecolors="white", edgecolors=col, lw=1.1, zorder=3,
                   label=spec["legend"]["iso_high"])
    for lab in spec["labels"]:
        ax.annotate(lab["label"], (lab["x"], lab["y"]), xytext=(6, 6), textcoords="offset points", fontsize=6,
                    arrowprops=dict(arrowstyle="-", lw=.35, color="#555555"))
    ax.text(0.01, 0.99, spec["tag"], transform=ax.transAxes, ha="left", va="top", fontsize=9, fontweight="bold")
    ax.set_xlabel(spec["xlab"]); ax.set_ylabel(spec["ylab"]); ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", bbox_to_anchor=(0, -0.1))
    for ext in ("pdf", "svg"):
        fig.savefig(f"{out_prefix}.{ext}", bbox_inches="tight")
    fig.savefig(f"{out_prefix}.png", dpi=600, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- driver
def build_panel(a, s, rows, near, run, cohorts, panel, cohort_set, colour, label_text, titles, out: Path, renderer: str):
    drop = {l.strip() for l in open(a.drop_origins)} if a.drop_origins else set()
    excluded = set(a.exclude_strain or [])
    bg, cpts, points = [], [], []
    n_ref = n_mib = 0
    for r in rows:
        x, y = float(r["PC1"]), float(r["PC2"])
        size = float(r.get("n_represented") or 1)
        if r["source"] == "isolate":
            if r.get("origin") in drop or r["strain"] in excluded or cohorts.get(r["strain"]) not in cohort_set:
                continue
            pid = near.get(r["id"])
            cpts.append(dict(x=x, y=y, strain=r["strain"], pid=pid, row=r))
        else:
            layer = "mibig" if r["source"] == "MIBiG" else "ref"
            bg.append((x, y))
            points.append(dict(x=x, y=y, layer=layer, size=size))
            if layer == "mibig":
                n_mib += int(size)
            else:
                n_ref += int(size)
    kx, ky = [float(r["PC1"]) for r in rows], [float(r["PC2"]) for r in rows]
    kit_span = max(max(kx) - min(kx), max(ky) - min(ky)) if rows else 1.0   # every kit point, as in v5
    groups, texts, thr, numbered = choose_labels(cpts, bg, label_below=a.label_below, top_strains=a.top_strains, q=a.quantile,
                                                 number_above=a.number_above, span=kit_span)
    low = [p["pid"] is not None and p["pid"] < a.label_below for p in cpts]
    for p, lw in zip(cpts, low):
        points.append(dict(x=p["x"], y=p["y"], layer="iso_low" if lw else "iso_high", size=1))
    title, tag, unit = titles.get(s, (s, s, "proteins"))
    pct = run.get("pct_axes") or [float("nan"), float("nan")]
    mt = "reference/MIBiG" if n_mib else "reference"
    nlo = sum(low); nhi = len(cpts) - nlo
    slo = len({p["strain"] for p, lw in zip(cpts, low) if lw}); shi = len({p["strain"] for p, lw in zip(cpts, low) if not lw})
    spec = dict(set=s, panel=panel, tag=tag, colour=colour, xlab=f"PCoA 1 ({pct[0]:.1f}%)", ylab=f"PCoA 2 ({pct[1]:.1f}%)",
                legend=dict(ref=f"reference genomes ({n_ref:,} {unit})", mibig=f"MIBiG ({n_mib:,} {unit})",
                            iso_low=f"{label_text} ({nlo:,} {unit}, {slo} strains): best {mt} match < {a.label_below:.0f}% identity",
                            iso_high=f"{label_text} ({nhi:,} {unit}, {shi} strains): best {mt} match >= {a.label_below:.0f}% identity"),
                points=points,
                labels=[dict(x=sum(cpts[k]["x"] for k in g) / len(g), y=sum(cpts[k]["y"] for k in g) / len(g), label=t)
                        for g, t in zip(groups, texts)])
    assert_no_banned_figure_text([spec["tag"], spec["xlab"], spec["ylab"], *spec["legend"].values(), *texts],
                                 figure_id=f"{s}_{panel}")
    prefix = out / f"PCOA_{s}_{panel}"
    stamp = uuid.uuid4().hex
    if renderer == "r":
        spec_path = out / f".render_{s}_{panel}_{stamp}.json"
        spec_path.write_text(json.dumps(dict(spec, stamp=stamp)))
        try:
            render_r(spec_path, prefix, stamp)
        finally:
            spec_path.unlink(missing_ok=True)
    else:
        render_matplotlib(spec, prefix)
    for ext in ("pdf", "svg", "png"):
        if not Path(f"{prefix}.{ext}").exists():
            raise RenderRefusal(f"{prefix.name}.{ext} was not written")
    assert_no_banned_figure_text(svg_visible_text(Path(f"{prefix}.svg").read_text()), figure_id=prefix.name)
    with open(out / f"LABELS_{s}_{panel}.tsv", "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["label", "label_text", "strain", "region_file", "locus_tag", "PC1", "PC2", "nearest_identity_pct", "fill"])
        for n, (g, t) in enumerate(zip(groups, texts), 1):
            for k in g:
                p = cpts[k]
                w.writerow([n, t, p["strain"], p["row"].get("origin", ""), p["row"].get("locus_tag", ""), f"{p['x']:.5f}",
                            f"{p['y']:.5f}", f"{p['pid']:.1f}" if p["pid"] is not None else "", "solid" if low[k] else "open"])
    receipt = dict(set=s, panel=panel, cohorts=sorted(cohort_set), renderer=renderer, stamp=stamp, labels=len(groups),
                   numbered=numbered, threshold=thr, n_cohort_points=len(cpts), n_low=nlo, n_ref=n_ref, n_mibig=n_mib,
                   label_rule=("top_strains" if a.top_strains else "distance_quantile"), top_strains=a.top_strains,
                   quantile=a.quantile, label_below=a.label_below, title=title)
    (out / f"panel_{s}_{panel}.json").write_text(json.dumps(receipt, indent=1))
    return receipt


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", required=True, help="folder with out_<SET>/PCOA_<SET>.tsv")
    ap.add_argument("--set", action="append", help="set id to draw (repeatable); default: every set in the kit")
    ap.add_argument("--out", required=True, help="new or empty output folder")
    ap.add_argument("--cohort-table", required=True, help="TSV with strain and cohort columns")
    ap.add_argument("--panel", action="append", required=True, help="NAME=COHORT[,COHORT...] (repeatable)")
    ap.add_argument("--panel-label", action="append", default=[], help="NAME=legend text for the cohort points")
    ap.add_argument("--cohort-colour", action="append", default=[], help="NAME=#hex fill for a panel's points")
    ap.add_argument("--set-names", help="TSV: set, title (or amr_gene_family), optional tag and unit columns")
    ap.add_argument("--exclude-strain", action="append", help="strain not drawn (repeatable)")
    ap.add_argument("--drop-origins", help="file listing region files whose points are not drawn")
    ap.add_argument("--label-below", type=float, default=70.0)
    ap.add_argument("--top-strains", type=int, default=0, help="label up to N strains by name (0 = distance rule)")
    ap.add_argument("--quantile", type=float, default=0.95)
    ap.add_argument("--number-above", type=int, default=30)
    ap.add_argument("--renderer", choices=["auto", "r", "matplotlib"], default="auto")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        out = Path(a.out)
        if out.exists() and any(out.iterdir()):
            raise RenderRefusal(f"{out} is not empty; choose a new folder (delivered figures are never overwritten)")
        out.mkdir(parents=True, exist_ok=True)
        kit = Path(a.kit)
        sets = a.set or sorted(p.stem[len("PCOA_"):] for p in kit.glob("out_*/PCOA_*.tsv"))
        if not sets:
            raise RenderRefusal(f"{kit}: no out_<SET>/PCOA_<SET>.tsv")
        cohorts = {r["strain"]: r.get("cohort", "") for r in read_tsv(Path(a.cohort_table))}
        titles = {}
        if a.set_names:
            for r in read_tsv(Path(a.set_names)):
                t = r.get("title") or r.get("amr_gene_family") or r["set"]
                titles[r["set"]] = (t, r.get("tag") or t, r.get("unit") or "proteins")
        labels = dict(x.split("=", 1) for x in a.panel_label)
        colours = dict(x.split("=", 1) for x in a.cohort_colour)
        renderer = a.renderer if a.renderer != "auto" else ("r" if r_available() else "matplotlib")
        receipts = []
        for s in sets:
            f = kit / f"out_{s}" / f"PCOA_{s}.tsv"
            if not f.exists():
                raise RenderRefusal(f"{f} missing")
            rows = read_tsv(f)
            nf = f.parent / f"NEAREST_{s}.tsv"
            near = {r["id"]: float(r["nearest_pident"]) for r in read_tsv(nf) if r.get("nearest_pident")} if nf.exists() else {}
            rf = f.parent / f"RUN_{s}.json"
            run = json.load(open(rf)) if rf.exists() else {}
            for i, spec in enumerate(a.panel):
                name, cs = spec.split("=", 1)
                receipts.append(build_panel(a, s, rows, near, run, cohorts, name, set(cs.split(",")),
                                            colours.get(name, PALETTE[i % len(PALETTE)]), labels.get(name, f"{name} isolates"),
                                            titles, out, renderer))
        (out / "render_receipt.json").write_text(json.dumps(dict(args=vars(a), renderer=renderer, panels=receipts), indent=1))
    except (RenderRefusal, FigureTextRefusal) as exc:
        _LOG.error("REFUSED: %s", exc)
        return 2
    _LOG.info("%d panels drawn with %s", len(receipts), renderer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
