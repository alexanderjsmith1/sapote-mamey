#!/usr/bin/env python3
"""Sequence-similarity network of one protein family, drawn at one to three identity cut-offs.

Inputs:
  --nodes   TSV, one row per protein: node (the FASTA ID used in the search), identity (the full record identity,
            e.g. strain / contig / region / BGC alias / locus tag), group (color), and optionally shape_class.
  --hits    all-against-all tabular hits with exactly 12 columns:
            qseqid sseqid pident length qlen slen qstart qend sstart send evalue bitscore
            (DIAMOND: --outfmt 6 qseqid sseqid pident length qlen slen qstart qend sstart send evalue bitscore).
An edge joins two proteins when an alignment covers at least --min-cover of both proteins; its identity is the
best pident over all such alignments in either direction. Each cut-off gets its own panel and its own layout:
every connected cluster is laid out alone (spring layout weighted by identity, fixed seed), pairs lie flat,
clusters are packed largest first, and unconnected proteins sit in rows along the bottom.

The tool stops on: a hit naming a protein absent from --nodes, a duplicate or blank node, a blank identity or
group, a malformed hit line, an empty node table, a group without a color, more than three cut-offs, and any
planned output that already exists or equals an input.

Outputs in --outdir: <stem>.png/.svg (bundle theme, manuscript profile), <stem>_plot_only.png, <stem>.pdf,
<stem>_edges.tsv, <stem>_plotted.tsv (coordinates per cut-off with each node's identity), <stem>_CAPTION.md
(method text with the counts; interpretation is the author's) and <stem>_receipt.json (input and output SHA-256,
parameters, per-cut-off counts). A shared cluster shows sequence similarity, not a shared product.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
from pathlib import Path

try:
    from mamey.figure_theme import PALETTE, apply_theme, save_figure_pair
except ImportError:  # run from tools/ without the package on the path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mamey.figure_theme import PALETTE, apply_theme, save_figure_pair
from mamey.csv_safety import SafeWriter  # noqa: E402  (formula-injection guard for TSV output)

DEFAULT_COLORS = ["teal", "gold", "coral", "navy", "muted"]
MARKERS = ["o", "s", "^", "D", "v", "P"]
SEED = 1904823
ROW_WIDTH = 9.0


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_nodes(path: Path) -> dict[str, dict]:
    with open(path, newline="") as fh:
        rd = csv.DictReader(fh, delimiter="\t")
        need = {"node", "identity", "group"}
        if not rd.fieldnames or not need <= set(rd.fieldnames):
            sys.exit(f"{path}: needs columns {sorted(need)} (shape_class optional)")
        nodes: dict[str, dict] = {}
        for i, r in enumerate(rd, start=2):
            n = (r.get("node") or "").strip()
            if not n or not (r.get("identity") or "").strip() or not (r.get("group") or "").strip():
                sys.exit(f"{path}: line {i} has a blank node, identity or group")
            if n in nodes:
                sys.exit(f"{path}: node {n} appears twice")
            r["shape_class"] = (r.get("shape_class") or "").strip() or "protein"
            nodes[n] = r
    if not nodes:
        sys.exit(f"{path}: no proteins")
    return nodes


def load_edges(path: Path, nodes: dict, min_cover: float) -> dict[tuple[str, str], float]:
    """Best identity per unordered pair over alignments covering >= min_cover of both proteins."""
    pairs: dict[tuple[str, str], float] = {}
    with open(path) as fh:
        for i, line in enumerate(fh, start=1):
            if not line.strip():
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) != 12:
                sys.exit(f"{path}: line {i} has {len(f)} columns, expected 12 (see --help)")
            q, s = f[0], f[1]
            for x in (q, s):
                if x not in nodes:
                    sys.exit(f"{path}: line {i} names {x}, which is not in the node table")
            if q == s:
                continue
            try:
                pid = float(f[2]); qlen, slen = int(f[4]), int(f[5])
                qs, qe, ss, se = (int(v) for v in f[6:10])
            except ValueError:
                sys.exit(f"{path}: line {i} has a non-numeric field")
            cover = min((abs(qe - qs) + 1) / qlen, (abs(se - ss) + 1) / slen)
            if cover < min_cover:
                continue
            k = tuple(sorted((q, s)))
            pairs[k] = max(pairs.get(k, 0.0), pid)
    return pairs


def components(node_ids, edges):
    """Connected components, largest first, ties by smallest member."""
    adj = {n: set() for n in node_ids}
    for a, b in edges:
        adj[a].add(b); adj[b].add(a)
    seen, comps = set(), []
    for n in sorted(adj):
        if n in seen:
            continue
        stack, comp = [n], set()
        while stack:
            x = stack.pop()
            if x in comp:
                continue
            comp.add(x); stack.extend(adj[x] - comp)
        seen |= comp; comps.append(comp)
    return sorted(comps, key=lambda c: (-len(c), min(c)))


def packed_layout(node_ids, weighted_edges):
    """Lay out each cluster alone and pack clusters on rows, largest first; pairs flat; singletons in rows last."""
    import networkx as nx
    G = nx.Graph(); G.add_nodes_from(node_ids); G.add_weighted_edges_from(weighted_edges)
    comps = components(node_ids, [(a, b) for a, b, _ in weighted_edges])
    multi = [c for c in comps if len(c) > 1]; single = [c for c in comps if len(c) == 1]
    pos, x0, y0, rowh = {}, 0.0, 0.0, 0.0
    for c in multi:
        r = 0.45 * len(c) ** 0.5 + 0.35
        if len(c) == 2:  # pairs lie flat, so stacked pairs never read as chains
            a, b = sorted(c); sub = {a: (-r * 0.8, 0.0), b: (r * 0.8, 0.0)}
        else:
            sub = nx.spring_layout(G.subgraph(c), seed=SEED, weight="weight", k=1.6 / len(c) ** 0.5,
                                   iterations=400, scale=r)
        if x0 + 2 * r > ROW_WIDTH and x0 > 0:
            x0, y0, rowh = 0.0, y0 - rowh - 1.2, 0.0
        for n, (x, y) in sub.items():
            pos[n] = (x0 + r + float(x), y0 - r + float(y))
        x0 += 2 * r + 0.8; rowh = max(rowh, 2 * r)
    x0, y0 = 0.0, y0 - rowh - 0.7
    for c in single:
        n = next(iter(c))
        if x0 > ROW_WIDTH:
            x0, y0 = 0.0, y0 - 1.3
        pos[n] = (x0, y0); x0 += 0.9
    return G, pos


def summarise(node_ids, pairs, cut):
    edges = [(a, b) for (a, b), v in pairs.items() if v >= cut]
    comps = components(node_ids, edges)
    return {"identity_cutoff": cut, "edges": len(edges), "clusters_2plus": sum(len(c) > 1 for c in comps),
            "singletons": sum(len(c) == 1 for c in comps), "largest_cluster": max(len(c) for c in comps)}


def parse_colors(spec: str | None, groups: list[str]) -> dict[str, str]:
    if spec:
        out = {}
        for item in spec.split(","):
            if "=" not in item:
                sys.exit(f"--group-colors: '{item}' is not group=palette_key")
            g, k = (x.strip() for x in item.split("=", 1))
            if k not in PALETTE:
                sys.exit(f"--group-colors: '{k}' is not a bundle palette key ({', '.join(sorted(PALETTE))})")
            out[g] = PALETTE[k]
        missing = [g for g in groups if g not in out]
        if missing:
            sys.exit(f"--group-colors gives no color for: {', '.join(missing)}")
        return out
    if len(groups) > len(DEFAULT_COLORS):
        sys.exit(f"{len(groups)} groups; give --group-colors for more than {len(DEFAULT_COLORS)}")
    return {g: PALETTE[DEFAULT_COLORS[i]] for i, g in enumerate(groups)}


def fmt_cut(c: float) -> str:
    return f"{c:g}"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--nodes", type=Path, required=True)
    ap.add_argument("--hits", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--stem", required=True)
    ap.add_argument("--cutoffs", default="30,40,50", help="one to three identity cut-offs in percent")
    ap.add_argument("--min-cover", type=float, default=0.5, help="minimum alignment cover of both proteins (0-1)")
    ap.add_argument("--group-colors", help="group=palette_key,... (default: teal, gold, coral, navy, muted in group order)")
    ap.add_argument("--search", default="", help="search command and version, written to the caption and receipt")
    a = ap.parse_args(argv)
    cuts = [float(x) for x in a.cutoffs.split(",") if x.strip()]
    if not 1 <= len(cuts) <= 3:
        sys.exit("--cutoffs takes one to three values")
    if not 0 < a.min_cover <= 1:
        sys.exit("--min-cover must be in (0, 1]")
    nodes = load_nodes(a.nodes)
    pairs = load_edges(a.hits, nodes, a.min_cover)
    groups = list(dict.fromkeys(r["group"] for r in nodes.values()))
    colors = parse_colors(a.group_colors, groups)
    groups = [g for g in colors if g in groups]          # legend order follows --group-colors when given
    shapes = list(dict.fromkeys(r["shape_class"] for r in nodes.values()))
    if len(shapes) > len(MARKERS):
        sys.exit(f"{len(shapes)} shape classes; at most {len(MARKERS)}")
    marker = {s: MARKERS[i] for i, s in enumerate(shapes)}

    a.outdir.mkdir(parents=True, exist_ok=True)
    stem = a.outdir / a.stem
    outs = [Path(f"{stem}{x}") for x in (".png", ".svg", ".pdf", "_plot_only.png", "_edges.tsv", "_plotted.tsv",
                                         "_CAPTION.md", "_receipt.json")]
    ins = {a.nodes.resolve(), a.hits.resolve()}
    for p in outs:
        if p.exists() or p.resolve() in ins:
            sys.exit(f"refusing to overwrite {p}")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import networkx as nx

    apply_theme(plt, "manuscript"); plt.rcParams["font.size"] = 10.0
    fig, axes = plt.subplots(2, 2, figsize=(7.6, 7.8))
    summary, layouts = [], {}
    for ax, cut, lab in zip(axes.flat, cuts, "ABC"):
        we = [(x, y, v / 100) for (x, y), v in pairs.items() if v >= cut]
        G, pos = packed_layout(list(nodes), we); layouts[cut] = pos
        nx.draw_networkx_edges(G, pos, ax=ax, edge_color=PALETTE["muted"], width=0.4, alpha=0.45)
        for s, m in marker.items():
            ns = [n for n in G if nodes[n]["shape_class"] == s]
            if ns:
                nx.draw_networkx_nodes(G, pos, nodelist=ns, ax=ax, node_shape=m, node_size=34,
                                       node_color=[colors[nodes[n]["group"]] for n in ns],
                                       edgecolors=PALETTE["navy"], linewidths=0.4)
        summary.append(summarise(list(nodes), pairs, cut))
        ax.set_title(f"{lab}   ≥{fmt_cut(cut)}% identity", loc="left", fontsize=11, fontweight="bold")
        ax.axis("off")
    for ax in list(axes.flat)[len(cuts):]:
        ax.axis("off")
    leg = axes.flat[3]
    h = [Line2D([], [], marker="o", linestyle="", markersize=7, markerfacecolor=colors[g],
                markeredgecolor=PALETTE["navy"], label=f"{g} ({sum(r['group'] == g for r in nodes.values())})") for g in groups]
    if len(shapes) > 1:
        h += [Line2D([], [], marker=m, linestyle="", markersize=7, markerfacecolor=PALETTE["white"],
                     markeredgecolor=PALETTE["navy"], label=s) for s, m in marker.items()]
    leg.legend(handles=h, loc="upper center", bbox_to_anchor=(0.5, 1.0), frameon=False, fontsize=9.5)
    panels = ", ".join(f"{lab} {fmt_cut(c)}%" for lab, c in zip("ABC", cuts))
    key = ["How to read it", "Each symbol is one protein.", "Color: its group."]
    if len(shapes) > 1:
        key.append("Shape: its class.")
    key += ["A line joins two proteins whose alignment", f"covers at least {a.min_cover * 100:g}% of both and reaches",
            "the panel's identity.", "Each panel sets the identity needed", f"for a line ({panels}).",
            "Proteins without a line are along the bottom."]
    leg.text(0.5, 0.02, "\n".join(key), transform=leg.transAxes, ha="center", va="bottom", fontsize=9,
             linespacing=1.35, color=PALETTE["ink"])
    fig.tight_layout()
    png, svg = save_figure_pair(fig, stem, profile="manuscript")
    fig.savefig(f"{stem}.pdf", bbox_inches="tight", metadata={"Creator": "Sapote-Mamey governed figure theme"})
    plt.close(fig)
    shutil.copyfile(png, f"{stem}_plot_only.png")

    with open(f"{stem}_edges.tsv", "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["node_a", "node_b", "best_identity_pct", "identity_a", "identity_b"])
        for (x, y), v in sorted(pairs.items()):
            w.writerow([x, y, v, nodes[x]["identity"], nodes[y]["identity"]])
    with open(f"{stem}_plotted.tsv", "w", newline="") as fh:
        w = SafeWriter(fh, delimiter="\t", lineterminator="\n")
        w.writerow(["cutoff", "node", "x", "y", "identity", "group", "shape_class"])
        for cut, pos in layouts.items():
            for n in sorted(pos):
                w.writerow([fmt_cut(cut), n, f"{pos[n][0]:.4f}", f"{pos[n][1]:.4f}", nodes[n]["identity"],
                            nodes[n]["group"], nodes[n]["shape_class"]])
    search = f" ({a.search})" if a.search else ""
    Path(f"{stem}_CAPTION.md").write_text(
        f"Sequence-similarity network of {len(nodes)} proteins. Each node is one protein, colored by group"
        + (" and shaped by class" if len(shapes) > 1 else "") + ". "
        f"Edges join proteins from an all-against-all search{search} whose alignment covers at least "
        f"{a.min_cover * 100:g}% of both proteins, at "
        + "; ".join(f"{fmt_cut(s['identity_cutoff'])}% identity ({s['edges']} edges, {s['clusters_2plus']} clusters "
                    f"of two or more, {s['singletons']} unconnected)" for s in summary)
        + ". Each panel has its own layout: clusters are drawn separately, largest first, and unconnected proteins "
          "along the bottom. Each node's full identity is in the plotted table. "
          "A shared cluster indicates sequence similarity, not a shared product.\n")
    rec = {"tool": "tools/protein_ssn_render.py", "nodes": str(a.nodes), "nodes_sha256": sha(a.nodes),
           "hits": str(a.hits), "hits_sha256": sha(a.hits), "search": a.search, "min_cover_both": a.min_cover,
           "layout": f"per-cut-off packed layout; spring per cluster (seed {SEED}, identity-weighted); pairs flat",
           "legend_groups": groups, "cutoffs": summary, "outputs": {}}
    for p in outs[:-1]:
        rec["outputs"][p.name] = sha(p)
    Path(f"{stem}_receipt.json").write_text(json.dumps(rec, indent=1) + "\n")
    for s in summary:
        sys.stdout.write(f"{fmt_cut(s['identity_cutoff'])}%\tedges {s['edges']}\tclusters {s['clusters_2plus']}\tsingletons {s['singletons']}\n")
    return summary


if __name__ == "__main__":
    main()
