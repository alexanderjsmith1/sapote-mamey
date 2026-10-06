#!/usr/bin/env python3
"""Per-strain protein PCoA panels: one strain's proteins marked against the other isolates, MIBiG and reference genomes.

Usage:
  python tools/strain_slides_pcoa.py --kit <kit folder> --strain <ID> --out <folder>
         [--groups "groupA:label A,groupB:label B"] [--drop-origins <file>] [--sets-a KS,AT,T3PKS,A,C,GT1]
         [--sets-b LANC,YCAO,TERP,NIS,P450,HALO]

Input is a protein PCoA kit as written by tools/protein_pcoa_ordinate.py: out_<SET>/PCOA_<SET>.tsv (coordinates; source,
group, strain, origin columns), NEAREST_<SET>.tsv (identity of each isolate protein to its best reference/MIBiG match) and
RUN_<SET>.json (pct_axes). Nothing is re-ordinated here.

Two figures per strain, six classes each (--sets-a, --sets-b). Layers, drawn bottom to top and listed in this order in the
legend from the top: the strain (red, three identity tiers: below 70%, 70-85%, 85% or more), then each isolate group in
--groups order, then MIBiG, then reference genomes. --groups also names the groups in the legend; groups not listed are
drawn last among the isolates as "other isolates". --drop-origins lists region files whose proteins are not drawn.
Writes <out>/<strain>_PCOA_biosynthetic_core.png/.pdf, <strain>_PCOA_ripp_tailoring.png/.pdf and <strain>_PCOA_COUNTS.tsv.
A low identity says a protein is unlike the reference set; it is not evidence of a new compound.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # noqa: F401

NAME = {"KS": ("PKS ketosynthase (KS) domains", "domains"), "AT": ("PKS acyltransferase (AT) domains", "domains"),
        "T3PKS": ("Type III PKSs", "proteins"), "A": ("NRPS adenylation (A) domains", "domains"),
        "C": ("NRPS condensation (C) domains", "domains"), "GT1": ("UDP-glycosyltransferases", "proteins"),
        "LANC": ("LanC-like cyclases", "proteins"), "YCAO": ("YcaO cyclodehydratases", "proteins"),
        "TERP": ("Terpene synthases", "proteins"), "NIS": ("NIS siderophore synthetases", "proteins"),
        "P450": ("Cytochrome P450s", "proteins"), "HALO": ("Flavin-dependent halogenases", "proteins"),
        "SARP": ("SARP-family regulators", "proteins"), "LUXR": ("LuxR-family regulators", "proteins")}
STRAIN, STRAIN_LIGHT = "#D7191C", "#F7A8A8"
GROUP_COLS = ["#E8A33D", "#4DAF6E", "#9B7FD4", "#E377C2", "#17BECF", "#8C564B"]
MIBIG, REF, OTHER = "#4A7FC1", "#C9CDD3", "#BDB8B2"
BAR, MID = 70.0, 85.0
NONE = "#9CA3AF"  # no best reference/MIBiG identity recorded: its own tier, never counted as 85% or more


def load(kit, T, drop):
    import numpy as np
    d = kit / f"out_{T}"
    with open(d / f"PCOA_{T}.tsv", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter="\t"))
    near = {}
    if (d / f"NEAREST_{T}.tsv").exists():
        with open(d / f"NEAREST_{T}.tsv", newline="") as fh:
            near = {r["id"]: float(r["nearest_pident"]) for r in csv.DictReader(fh, delimiter="\t") if r.get("nearest_pident")}
    pct = json.load(open(d / f"RUN_{T}.json")).get("pct_axes", [0, 0])
    return dict(X=np.array([[float(r["PC1"]), float(r["PC2"])] for r in rows]),
                src=np.array([r["source"] for r in rows]), size=np.array([float(r.get("n_represented") or 1) for r in rows]),
                strain=np.array([r.get("strain", "") for r in rows]), group=np.array([r.get("group", "") for r in rows]),
                pid=np.array([near.get(r["id"], np.nan) for r in rows]),
                iso=np.array([r["source"] == "isolate" and r.get("origin", "") not in drop for r in rows]), pct=pct)


def panel(ax, D, T, strain, groups):
    import numpy as np
    X, src, size = D["X"], D["src"], D["size"]
    bg = ~np.isin(src, ["isolate", "MIBiG"])
    mb = src == "MIBiG"
    me = D["iso"] & (D["strain"] == strain)
    ax.scatter(X[bg, 0], X[bg, 1], s=1.5 + np.sqrt(size[bg]), c=REF, lw=0, alpha=.8, rasterized=True, zorder=1)
    ax.scatter(X[mb, 0], X[mb, 1], s=2.5 + np.sqrt(size[mb]), c=MIBIG, lw=0, alpha=.75, rasterized=True, zorder=2)
    counts = {}
    known = [g for g, _ in groups]
    other = D["iso"] & ~me & ~np.isin(D["group"], known)
    ax.scatter(X[other, 0], X[other, 1], s=6, c=OTHER, lw=0, alpha=.9, rasterized=True, zorder=3)
    for z, (g, _) in enumerate(reversed(groups)):   # the first listed group is drawn on top
        m = D["iso"] & ~me & (D["group"] == g)
        counts[g] = int(m.sum())
        ax.scatter(X[m, 0], X[m, 1], s=7, c=GROUP_COLS[(len(groups) - 1 - z) % len(GROUP_COLS)], edgecolors="white",
                   lw=.2, alpha=.95, rasterized=True, zorder=3.1 + z / 10)
    pid = D["pid"]
    low, mid = me & (pid < BAR), me & (pid >= BAR) & (pid < MID)
    unk = me & np.isnan(pid)
    high = me & ~low & ~mid & ~unk
    ax.scatter(X[unk, 0], X[unk, 1], s=30, c=NONE, edgecolors="#4B5563", lw=.6, zorder=4)
    ax.scatter(X[high, 0], X[high, 1], s=36, facecolors="white", edgecolors=STRAIN, lw=1.4, zorder=4)
    ax.scatter(X[mid, 0], X[mid, 1], s=36, c=STRAIN_LIGHT, edgecolors=STRAIN, lw=.9, zorder=5)
    ax.scatter(X[low, 0], X[low, 1], s=40, c=STRAIN, edgecolors="black", lw=.6, zorder=6)
    lab, unit = NAME.get(T, (T, "proteins"))
    n, nl, nm = int(me.sum()), int(low.sum()), int(mid.sum())
    unit = unit[:-1] if n == 1 else unit
    ax.set_title(lab, fontsize=9.5, fontweight="bold", loc="left", color="#1F2937", pad=15)
    ax.text(0.0, 1.02, f"{strain}: {n} {unit}; {nl} below {BAR:.0f}%, {nm} at {BAR:.0f}-{MID:.0f}%" if n
            else f"{strain}: none in its antiSMASH regions", transform=ax.transAxes, fontsize=8, color="#374151", va="bottom")
    ax.set_xlabel(f"PCoA 1 ({D['pct'][0]:.1f}%)", fontsize=7.5, color="#4B5563")
    ax.set_ylabel(f"PCoA 2 ({D['pct'][1]:.1f}%)", fontsize=7.5, color="#4B5563")
    ax.tick_params(labelsize=6.5, colors="#6B7280", length=2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    return dict(set=T, n=n, below_70=nl, from_70_to_85=nm, **{f"n_other_{g}": c for g, c in counts.items()},
                n_mibig=int(size[mb].sum()), n_reference=int(size[bg].sum()))


ALL_SETS = ["KS", "AT", "T3PKS", "A", "C", "GT1", "LANC", "YCAO", "TERP", "NIS", "P450", "HALO", "SARP", "LUXR"]


def kit_sets(kit):
    """Every ordinated set in a kit (out_<SET>/PCOA_<SET>.tsv), the named classes first; CARD family names from
    RES_SETS.tsv (set, amr_gene_family) when the kit has one."""
    kit = Path(kit)
    have = sorted(d.name[4:] for d in kit.glob("out_*") if (d / f"PCOA_{d.name[4:]}.tsv").exists())
    if (kit / "RES_SETS.tsv").exists():
        with open(kit / "RES_SETS.tsv", newline="") as fh:
            for r in csv.DictReader(fh, delimiter="\t"):
                f = r["amr_gene_family"].split(";")
                NAME.setdefault(r["set"], ("CARD: " + (f[0] if len(f) == 1 else f"{f[0]} (+{len(f) - 1})")[:52], "proteins"))
    return [t for t in ALL_SETS if t in have] + [t for t in have if t not in ALL_SETS]


def place_labels(ax, pts, labels, fontsize=6.5, avoid=(), star_r=6.0):
    """Locus-tag labels beside their stars without overlapping one another: each label tries offsets around its point
    (right, below-right, left, below-left, then further out) and takes the first whose box clears every label already
    placed. Boxes are estimated in points from the font size. A label with no free spot is left out and counted."""
    fig = ax.figure
    fig.canvas.draw_idle()
    to_pt = 72.0 / fig.dpi
    # star_r: half the drawn star's width in points; no label box may cover any star, its own included
    placed = []
    for ax_, ay_ in avoid:
        sx, sy = (v * to_pt for v in ax.transData.transform((ax_, ay_)))
        k = star_r + 2  # 2 pt for the label's padding, which the size estimate leaves out
        placed.append((sx - k, sy - k, sx + k, sy + k))
    skipped = 0
    for (x, y), lab in zip(pts, labels):
        px, py = (v * to_pt for v in ax.transData.transform((x, y)))
        w, h = len(lab) * fontsize * 0.58 + 3, fontsize + 3
        g, r = star_r + 4, star_r + 3
        offs = [(g, -h / 2), (g, r), (g, -r - h), (-g, -h / 2), (-g, r), (-g, -r - h),
                (g, r + h + 3), (g, -r - 2 * h - 3), (-g, r + h + 3), (-g, -r - 2 * h - 3),
                (2 * g, 2 * r + h), (-2 * g, -2 * r - 2 * h)]
        for dx, dy in offs:
            x0 = px + dx if dx > 0 else px + dx - w
            box = (x0, py + dy, x0 + w, py + dy + h)
            if all(box[2] <= b[0] or box[0] >= b[2] or box[3] <= b[1] or box[1] >= b[3] for b in placed):
                placed.append(box)
                ax.annotate(lab, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=fontsize,
                            ha="left" if dx > 0 else "right", color="#111827", zorder=7,
                            bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=.8))
                break
        else:
            skipped += 1
    return skipped


def _short(tag):
    m = tag.rsplit("_", 1)
    return tag if len(m) < 2 else tag[-9:]


def bgc_figure(kit, strain, tags, out, cache, drop=frozenset(), max_panels=6, width=12.4, height=6.4, title="",
               compact=False):
    """One BGC's proteins in the protein PCoA: every set holding at least one of them (most points first, at most
    max_panels), each panel with this BGC's proteins as large stars filled by identity tier (solid below 70%, pink
    70-85%, white 85% or more, to the best reference/MIBiG match) and labelled by locus tag; the strain's other
    proteins pale red; other isolates, MIBiG and reference centroids beneath. Returns (path, [(set, n, n_below_70,
    tags)]) or (None, []) when no protein of the BGC is in the kit. compact: a small figure for the region slide (one
    row, smaller type, a two-row legend); the summary then still lists every set that holds the BGC, shown or not."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    kit = Path(kit)
    hits = []
    for T in kit_sets(kit):
        if T not in cache:
            cache[T] = load(kit, T, drop)
            with open(kit / f"out_{T}" / f"PCOA_{T}.tsv", newline="") as fh:
                cache[T]["tag"] = np.array([r.get("locus_tag", "") for r in csv.DictReader(fh, delimiter="\t")])
        D = cache[T]
        m = D["iso"] & (D["strain"] == strain) & np.isin(D["tag"], list(tags))
        if m.sum():
            hits.append((int(m.sum()), T, m))
    if not hits:
        return None, []
    hits = sorted(hits, key=lambda h: -h[0])
    every = [(T, n) for n, T, _ in hits]
    hits = hits[:max_panels]
    ncol = len(hits) if compact else min(3, len(hits))
    nrow = -(-len(hits) // ncol)
    fs = 0.72 if compact else 1.0  # type scale
    fig, axes = plt.subplots(nrow, ncol, figsize=(width, height if (nrow > 1 or compact) else height * 0.86), dpi=220 if compact else 200,
                             squeeze=False)
    for ax in axes.flat[len(hits):]:
        ax.axis("off")
    summary, any_unk = [], False
    for ax, (n, T, m) in zip(axes.flat, hits):
        D = cache[T]
        X, src, size, pid = D["X"], D["src"], D["size"], D["pid"]
        bg = ~np.isin(src, ["isolate", "MIBiG"])
        mb = src == "MIBiG"
        own = D["iso"] & (D["strain"] == strain) & ~m
        oth = D["iso"] & (D["strain"] != strain)
        ax.scatter(X[bg, 0], X[bg, 1], s=1.5 + np.sqrt(size[bg]), c=REF, lw=0, alpha=.8, rasterized=True, zorder=1)
        ax.scatter(X[mb, 0], X[mb, 1], s=2.5 + np.sqrt(size[mb]), c=MIBIG, lw=0, alpha=.75, rasterized=True, zorder=2)
        ax.scatter(X[oth, 0], X[oth, 1], s=6, c=GROUP_COLS[0], edgecolors="white", lw=.2, alpha=.8, rasterized=True, zorder=3)
        ax.scatter(X[own, 0], X[own, 1], s=14, c=STRAIN_LIGHT, edgecolors=STRAIN, lw=.4, zorder=4)
        fill = np.where(np.isnan(pid), NONE, np.where(pid < BAR, STRAIN, np.where(pid < MID, STRAIN_LIGHT, "white")))
        any_unk = any_unk or bool((m & np.isnan(pid)).any())
        idx = np.where(m)[0]
        ax.scatter(X[idx, 0], X[idx, 1], s=110 if compact else 320, marker="*", c=list(fill[idx]), edgecolors="black",
                   lw=.6 if compact else .9, zorder=6)
        # One label per protein: a protein with several domains in this set has several stars, labelled once "xn".
        by_tag = {}
        for i in idx:
            by_tag.setdefault(D["tag"][i], []).append(i)
        tags_here = list(by_tag)[:6 if compact else 12]
        pts = [(X[by_tag[t][0], 0], X[by_tag[t][0], 1]) for t in tags_here]
        labs = [_short(t) + (f" \u00d7{len(by_tag[t])}" if len(by_tag[t]) > 1 else "") for t in tags_here]
        left = place_labels(ax, pts, labs, avoid=[(X[i, 0], X[i, 1]) for i in idx],
                            star_r=np.sqrt(110 if compact else 320) / 2 + 1)
        if left or len(by_tag) > len(tags_here):
            ax.text(1.0, 0.01, f"{left + len(by_tag) - len(tags_here)} protein labels left out (crowded)", transform=ax.transAxes,
                    fontsize=6 * fs, color="#6B7280", ha="right", va="bottom")
        import textwrap
        lab = textwrap.fill(NAME.get(T, (T, ""))[0], 36 if compact else 52)
        nl = int((m & (pid < BAR)).sum())
        ax.set_title(lab, fontsize=9 * fs, fontweight="bold", loc="left", color="#1F2937",
                     pad=(13 if "\n" not in lab else 12) * fs)
        ax.text(0.0, 1.015, f"this BGC: {n} {'point' if n == 1 else 'points'} (stars), {nl} below {BAR:.0f}%", transform=ax.transAxes,
                fontsize=7.5 * fs, color="#374151", va="bottom")
        ax.set_xlabel(f"PCoA 1 ({D['pct'][0]:.1f}%)", fontsize=7 * fs, color="#4B5563", labelpad=1 if compact else 4)
        ax.set_ylabel(f"PCoA 2 ({D['pct'][1]:.1f}%)", fontsize=7 * fs, color="#4B5563", labelpad=1 if compact else 4)
        ax.tick_params(labelsize=6 * fs, colors="#6B7280", length=2)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        summary.append((T, n, nl, sorted(D["tag"][idx])))
    star = lambda fc, lab: Line2D([], [], ls="", marker="*", ms=13, mfc=fc, mec="black", mew=.8, label=lab)
    dot = lambda fc, lab, ec="none": Line2D([], [], ls="", marker="o", ms=5, mfc=fc, mec=ec, label=lab)
    h = [star(STRAIN, f"this BGC: best reference/MIBiG match below {BAR:.0f}%"), star(STRAIN_LIGHT, f"this BGC: {BAR:.0f}-{MID:.0f}%"),
         star("white", f"this BGC: {MID:.0f}% or more")] + ([star(NONE, "this BGC: no reference/MIBiG match recorded")]
                                                             if any_unk else []) + [dot(STRAIN_LIGHT, f"{strain}: its other proteins", STRAIN),
         dot(GROUP_COLS[0], "other isolates"), dot(MIBIG, "MIBiG 4.0"), dot(REF, "public reference genomes (centroids)")]
    if compact:  # short labels in two rows; the slide caption spells out the tiers
        for x, lab in zip(h, ["below 70%", "70-85%", "85% or more", "no match"] if any_unk else ["below 70%", "70-85%", "85% or more"]):
            x.set_label(lab)
        for x in h:
            x.set_markersize(x.get_markersize() * 0.65)
        tail = h[-4:]
        for x, lab in zip(tail, [f"{strain} other", "other isolates", "MIBiG 4.0", "public genomes"]):
            x.set_label(lab)
        fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, fontsize=5.4, bbox_to_anchor=(0.5, -0.01),
                   handletextpad=0.2, columnspacing=0.8)
        fig.tight_layout(rect=(0, 0.17, 1, 1), w_pad=0.6)
    else:
        fig.legend(handles=h, loc="lower center", ncol=4, frameon=False, fontsize=7.5, bbox_to_anchor=(0.5, -0.005))
        if title:
            fig.suptitle(title, fontsize=10, color="#1F2937", x=0.01, ha="left")
        fig.tight_layout(rect=(0, 0.07 if nrow > 1 else 0.11, 1, 0.97 if title else 1), h_pad=2.0)
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    if compact:
        shown = {T for T, *_ in summary}
        summary += [(T, n, None, []) for T, n in every if T not in shown]
    return out, summary


def region_panels(kit, strain, tags, out, cache, drop=frozenset(), max_panels=3, width=4.4, height=1.75):
    """Small PCoA panels for one BGC: the classes where its proteins (strain + locus tag) have the most points, at most
    max_panels. This BGC's points are red in three identity tiers; the strain's other points pale red; isolates, MIBiG
    and references grey. Returns (path, [(set, n, n_below_70)]) or (None, []) when the BGC has no point in the kit.
    cache holds loaded sets across calls."""
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    kit = Path(kit)
    hits = []
    for T in ALL_SETS:
        if not (kit / f"out_{T}" / f"PCOA_{T}.tsv").exists():
            continue
        if T not in cache:
            cache[T] = load(kit, T, drop)
            with open(kit / f"out_{T}" / f"PCOA_{T}.tsv", newline="") as fh:
                cache[T]["tag"] = np.array([r.get("locus_tag", "") for r in csv.DictReader(fh, delimiter="\t")])
        D = cache[T]
        m = D["iso"] & (D["strain"] == strain) & np.isin(D["tag"], list(tags))
        if m.sum():
            hits.append((int(m.sum()), T, m))
    if not hits:
        return None, []
    hits = sorted(hits, key=lambda h: -h[0])[:max_panels]
    fig, axes = plt.subplots(1, len(hits), figsize=(width, height), dpi=220, squeeze=False)
    summary = []
    for ax, (n, T, m) in zip(axes[0], hits):
        D = cache[T]
        X, src, size, pid = D["X"], D["src"], D["size"], D["pid"]
        bg = ~np.isin(src, ["isolate", "MIBiG"])
        mb = src == "MIBiG"
        own = D["iso"] & (D["strain"] == strain) & ~m
        oth = D["iso"] & (D["strain"] != strain)
        ax.scatter(X[bg, 0], X[bg, 1], s=0.6 + 0.5 * np.sqrt(size[bg]), c=REF, lw=0, rasterized=True)
        ax.scatter(X[mb, 0], X[mb, 1], s=1 + 0.5 * np.sqrt(size[mb]), c=MIBIG, lw=0, alpha=.7, rasterized=True)
        ax.scatter(X[oth, 0], X[oth, 1], s=2, c=OTHER, lw=0, rasterized=True)
        ax.scatter(X[own, 0], X[own, 1], s=5, c=STRAIN_LIGHT, lw=0, zorder=3)
        low, mid = m & (pid < BAR), m & (pid >= BAR) & (pid < MID)
        unk = m & np.isnan(pid)
        high = m & ~low & ~mid & ~unk
        ax.scatter(X[unk, 0], X[unk, 1], s=20, c=NONE, edgecolors="#4B5563", lw=.5, zorder=5)
        ax.scatter(X[high, 0], X[high, 1], s=22, facecolors="white", edgecolors=STRAIN, lw=1.1, zorder=5)
        ax.scatter(X[mid, 0], X[mid, 1], s=22, c=STRAIN_LIGHT, edgecolors=STRAIN, lw=.8, zorder=6)
        ax.scatter(X[low, 0], X[low, 1], s=24, c=STRAIN, edgecolors="black", lw=.5, zorder=7)
        lab = NAME.get(T, (T, ""))[0]
        ax.set_title(f"{lab}\n{n} here, {int(low.sum())} below {BAR:.0f}%", fontsize=5.6, color="#1F2937", pad=2)
        ax.set_xticks([]); ax.set_yticks([])
        for sp in ax.spines.values():
            sp.set_color("#D1D5DB"); sp.set_linewidth(.5)
        summary.append((T, n, int(low.sum())))
    fig.tight_layout(pad=0.3, w_pad=0.4)
    fig.savefig(out, facecolor="white")
    plt.close(fig)
    return out, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kit", required=True)
    ap.add_argument("--strain", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--groups", default="", help="group:label pairs in legend order, comma-separated")
    ap.add_argument("--drop-origins")
    ap.add_argument("--sets-a", default="KS,AT,T3PKS,A,C,GT1")
    ap.add_argument("--sets-b", default="LANC,YCAO,TERP,NIS,P450,HALO")
    a = ap.parse_args(argv)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.lines import Line2D
    except ImportError as e:
        sys.exit(f"strain_slides_pcoa needs matplotlib and numpy ({e})")
    plt.rcParams.update({"pdf.fonttype": 42, "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"]})
    kit, out = Path(a.kit), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    drop = {l.strip() for l in open(a.drop_origins)} if a.drop_origins else set()
    groups = [tuple(x.split(":", 1)) if ":" in x else (x, x) for x in a.groups.split(",") if x]
    counts = []
    for key, sets in (("biosynthetic_core", a.sets_a), ("ripp_tailoring", a.sets_b)):
        sets = [s for s in sets.split(",") if (kit / f"out_{s}" / f"PCOA_{s}.tsv").exists()]
        if not sets:
            continue
        fig, axes = plt.subplots(2, 3, figsize=(12.4, 6.6), dpi=200)
        for ax in axes.flat[len(sets):]:
            ax.axis("off")
        for ax, T in zip(axes.flat, sets):
            counts.append(dict(strain=a.strain, group=key, **panel(ax, load(kit, T, drop), T, a.strain, groups)))
        dot = lambda **k: Line2D([], [], ls="", marker="o", **k)
        h = [dot(ms=6.5, mfc=STRAIN, mec="black", mew=.6, label=f"{a.strain}: best reference/MIBiG match below {BAR:.0f}% identity"),
             dot(ms=6.5, mfc=STRAIN_LIGHT, mec=STRAIN, mew=.9, label=f"{a.strain}: {BAR:.0f}-{MID:.0f}%"),
             dot(ms=6.5, mfc="white", mec=STRAIN, mew=1.4, label=f"{a.strain}: {MID:.0f}% or more")]
        h += [dot(ms=4.5, mfc=GROUP_COLS[i % len(GROUP_COLS)], mec="white", mew=.3, label=lab) for i, (_, lab) in enumerate(groups)]
        h += [dot(ms=4.5, mfc=OTHER, mec="none", label="other isolates"), dot(ms=4.5, mfc=MIBIG, mec="none", label="MIBiG"),
              dot(ms=4.5, mfc=REF, mec="none", label="reference genomes (cluster centroids)")]
        ncol = 4
        rows_ = -(-len(h) // ncol)
        order = [i for c in range(ncol) for i in range(c, len(h), ncol)]  # matplotlib fills columns; rows read in order
        fig.legend(handles=[h[i] for i in order if i < len(h)], loc="lower center", ncol=ncol, frameon=False, fontsize=8)
        fig.tight_layout(rect=(0, 0.03 + 0.025 * rows_, 1, 1), h_pad=2.2)
        for ext in ("png", "pdf"):
            fig.savefig(out / f"{a.strain}_PCOA_{key}.{ext}", facecolor="white")
        plt.close(fig)
    if counts:
        keys = sorted({k for c in counts for k in c}, key=lambda k: list(counts[0]).index(k) if k in counts[0] else 99)
        with open(out / f"{a.strain}_PCOA_COUNTS.tsv", "w", newline="") as fh:
            w = _SafeDictWriter(fh, fieldnames=keys, delimiter="\t", restval="")
            w.writeheader()
            w.writerows(counts)
    print(a.strain, len(counts), "panels")
    return 0


if __name__ == "__main__":
    sys.exit(main())
