#!/usr/bin/env python3
r"""cluster_relate — relationship tree + distance matrix from a set of homologous clusters.

The comparative tools produce ortholog tables, but the *relationship* between clusters — which
are near-identical, which are diverged, which is the outgroup — was left to eyeball. This turns a
set of cluster GBKs into a distance matrix, a UPGMA dendrogram, a Newick tree, and a distance
heatmap, so "x-80 and NPDC are near-identical, the query is diverged, the references are the
outgroup" becomes a figure with numbers.

Distance between two clusters combines *how many* genes they share with *how similar* those genes
are:

    similarity(A,B) = (shared_orthologs / min(|A|,|B|)) * mean_global_identity_over_orthologs
    distance(A,B)   = 1 - similarity(A,B)

Orthologs are confident global-identity (clinker-consistent) pairs >= --min-id. This rewards both
gene-content overlap and sequence conservation, so a shared 3-gene warhead at 40% ranks far from a
14-gene near-identical cluster at 79%.

    cluster_relate.py --gbk LABEL:cluster.gbk (repeatable) --outdir OUT [--pdf]

Outputs: distance_matrix.csv, dendrogram.png, tree.nwk, (comparison with --pdf: figure + methods +
interpretation naming the closest pair and the outgroup). Capacity/architecture-level.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path


# ---- alignment core (self-contained; same global metric as cluster_gene_compare) --------------
def _aligner():
    from Bio import Align
    from Bio.Align import substitution_matrices
    a = Align.PairwiseAligner()
    a.substitution_matrix = substitution_matrices.load("BLOSUM62")
    a.open_gap_score = -11; a.extend_gap_score = -1; a.mode = "global"
    return a


def _gid(al, s1, s2):
    aln = al.align(s1, s2)[0]
    a, b = aln[0], aln[1]
    length = len(a); m = 0
    for x, y in zip(a, b):
        if x == y and x not in "-.":
            m += 1
        elif x == y:
            length -= 1
    return 100 * m / length if length else 0


def _genes(gbk):
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    out = []
    for rec in SeqIO.parse(str(gbk), "genbank"):
        for f in rec.features:
            if f.type == "CDS" and "translation" in f.qualifiers:
                out.append(f.qualifiers["translation"][0])
    return out


def pairwise_distances(labels, gbks, min_id=30.0, engine="biopython"):
    clusters = [_genes(p) for p in gbks]
    al = _aligner()
    n = len(clusters)
    # optional pyswrd prefilter of candidate ortholog pairs (fast for large inputs)
    cand = None
    if engine == "pyswrd":
        try:
            import pyswrd
            flat = [(ci, gi, aa) for ci, gs in enumerate(clusters) for gi, aa in enumerate(gs)]
            hits = list(pyswrd.search([x[2] for x in flat], [x[2] for x in flat],
                                      max_evalue=1.0, max_alignments=25))
            cand = set()
            for h in hits:
                ci, gi, _ = flat[h.query_index]; cj, gj, _ = flat[h.target_index]
                if ci != cj:
                    cand.add((min(ci, cj), gi if ci < cj else gj, max(ci, cj), gj if ci < cj else gi))
        except Exception:
            cand = None
    D = [[0.0] * n for _ in range(n)]
    S = [[1.0] * n for _ in range(n)]
    detail = {}
    for ci in range(n):
        for cj in range(ci + 1, n):
            best = {}          # gene in ci -> best global id to any gene in cj
            for gi, a in enumerate(clusters[ci]):
                for gj, b in enumerate(clusters[cj]):
                    if cand is not None and (ci, gi, cj, gj) not in cand:
                        continue
                    g = _gid(al, a, b)
                    if g >= min_id and g > best.get(gi, 0):
                        best[gi] = g
            shared = len(best)
            mean_id = (sum(best.values()) / shared / 100) if shared else 0
            denom = max(1, min(len(clusters[ci]), len(clusters[cj])))
            sim = (shared / denom) * mean_id
            dist = 1 - sim
            D[ci][cj] = D[cj][ci] = round(dist, 4)
            S[ci][cj] = S[cj][ci] = round(sim, 4)
            detail[(ci, cj)] = (shared, round(mean_id * 100, 1))
    return clusters, D, S, detail


# ---- tree + outputs ---------------------------------------------------------------------------
def upgma_newick(labels, D):
    """Pure-python UPGMA -> Newick (no external tree lib needed)."""
    import copy
    n = len(labels)
    clusters = {i: (labels[i], 1) for i in range(n)}   # id -> (newick_str, size)
    dist = {(i, j): D[i][j] for i in range(n) for j in range(i + 1, n)}
    heights = {i: 0.0 for i in range(n)}
    next_id = n
    active = list(range(n))
    while len(active) > 1:
        # find closest pair
        (a, b), dmin = min(((p, dist[p]) for p in
                            ((min(i, j), max(i, j)) for ii, i in enumerate(active)
                             for j in active[ii + 1:])), key=lambda x: x[1])
        na, sa = clusters[a]; nb, sb = clusters[b]
        h = dmin / 2
        na2 = f"{na}:{h - heights[a]:.4f}"
        nb2 = f"{nb}:{h - heights[b]:.4f}"
        clusters[next_id] = (f"({na2},{nb2})", sa + sb)
        heights[next_id] = h
        # update distances (UPGMA average)
        for k in active:
            if k in (a, b):
                continue
            dak = dist[(min(a, k), max(a, k))]; dbk = dist[(min(b, k), max(b, k))]
            dist[(min(next_id, k), max(next_id, k))] = (dak * sa + dbk * sb) / (sa + sb)
        active = [x for x in active if x not in (a, b)] + [next_id]
        next_id += 1
    return clusters[active[0]][0] + ";"


def make_dendrogram(labels, D, outdir, title):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.cluster.hierarchy import linkage, dendrogram
    from scipy.spatial.distance import squareform
    import numpy as np
    condensed = squareform(np.array(D), checks=False)
    Z = linkage(condensed, method="average")
    fig, ax = plt.subplots(figsize=(2.2 + 1.2 * len(labels), 4.2), dpi=150)
    dendrogram(Z, labels=labels, ax=ax, leaf_rotation=25, color_threshold=0.6,
               above_threshold_color="#6a7f95")
    ax.set_ylabel("cluster distance  (1 - similarity)", fontsize=9)
    ax.set_title(title, fontsize=11)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    plt.tight_layout()
    p = Path(outdir) / "dendrogram.png"
    fig.savefig(p, facecolor="white"); plt.close(fig)
    from PIL import Image
    im = Image.open(p)
    if im.mode != "RGB":
        im.convert("RGB").save(p)
    return str(p)


def interpret(labels, D, S, detail):
    n = len(labels)
    pairs = [(S[i][j], i, j) for i in range(n) for j in range(i + 1, n)]
    closest = max(pairs); farthest = min(pairs)
    # outgroup = the cluster with the lowest mean similarity to the rest
    mean_sim = [sum(S[i][j] for j in range(n) if j != i) / (n - 1) for i in range(n)]
    outgroup = min(range(n), key=lambda i: mean_sim[i])
    sh_c, id_c = detail[(min(closest[1], closest[2]), max(closest[1], closest[2]))]
    lines = [
        f"Closest pair: {labels[closest[1]]} and {labels[closest[2]]} "
        f"({sh_c} shared genes at {id_c}% mean identity; similarity {closest[0]:.2f}).",
        f"Most divergent pair: {labels[farthest[1]]} and {labels[farthest[2]]} "
        f"(similarity {farthest[0]:.2f}).",
        f"Outgroup (least similar to the rest on average): {labels[outgroup]} "
        f"(mean similarity {mean_sim[outgroup]:.2f}).",
        "Distance combines gene-content overlap and global sequence identity (clinker-consistent); "
        "it reflects homology, not identity of the final product.",
    ]
    return "\n\n".join(lines)


def make_pdf(labels, D, S, detail, dendro_png, outdir, title, min_id):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from PIL import Image as PILImage
    styles = getSampleStyleSheet()
    H = ParagraphStyle("H", parent=styles["Heading2"], textColor="#1a3a5a", spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=9.5, leading=13)
    p = Path(outdir) / "comparison.pdf"
    doc = SimpleDocTemplate(str(p), pagesize=letter, leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    iw, ih = PILImage.open(dendro_png).size
    w = 6.4 * inch; h = w * ih / iw
    story = [Paragraph(title, styles["Title"]), Spacer(1, 6),
             RLImage(dendro_png, width=w, height=min(h, 4.5 * inch)), Spacer(1, 6),
             Paragraph("Figure 1. UPGMA dendrogram of cluster distance (1 - similarity, where "
                       "similarity combines shared-ortholog fraction and mean global identity).", body),
             Paragraph("Interpretation", H)]
    for para in interpret(labels, D, S, detail).split("\n\n"):
        story.append(Paragraph(para, body))
    story.append(Paragraph("Computational methods", H))
    story.append(Paragraph(
        f"Inputs: {len(labels)} cluster GenBank files. Every CDS was aligned to every CDS in every "
        f"other cluster by global Needleman-Wunsch alignment (BLOSUM62, gap -11/-1); a gene pair is a "
        f"confident ortholog at global identity >= {min_id}%. For each cluster pair, similarity = "
        f"(shared orthologs / min gene count) x mean ortholog identity, and distance = 1 - similarity. "
        f"The distance matrix was clustered by UPGMA (average linkage) for the dendrogram and Newick "
        f"tree. Identity is homology, not product identity; capacity-level throughout.", body))
    doc.build(story)
    return str(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Relationship tree + distance matrix from cluster GBKs.")
    ap.add_argument("--gbk", action="append", required=True, metavar="LABEL:cluster.gbk")
    ap.add_argument("--outdir", default="cluster_relate_out")
    ap.add_argument("--title", default="Cluster relationships")
    ap.add_argument("--min-id", type=float, default=30.0)
    ap.add_argument("--engine", choices=["biopython", "pyswrd"], default="biopython")
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args(argv)
    labels, gbks = [], []
    for spec in a.gbk:
        lab, path = spec.split(":", 1); labels.append(lab); gbks.append(path)
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    clusters, D, S, detail = pairwise_distances(labels, gbks, min_id=a.min_id, engine=a.engine)
    # distance matrix CSV
    with open(Path(a.outdir) / "distance_matrix.csv", "w", newline="") as fh:
        w = _SafeWriter(fh); w.writerow([""] + labels)
        for i, lab in enumerate(labels):
            w.writerow([lab] + D[i])
    nwk = upgma_newick(labels, D)
    (Path(a.outdir) / "tree.nwk").write_text(nwk + "\n")
    dendro = make_dendrogram(labels, D, a.outdir, a.title)
    outs = ["distance_matrix.csv", "tree.nwk", "dendrogram.png"]
    if a.pdf:
        make_pdf(labels, D, S, detail, dendro, a.outdir, a.title, a.min_id); outs.append("comparison.pdf")
    emit(f"[cluster_relate] {len(labels)} clusters -> {', '.join(outs)} in {a.outdir}/", '[cluster_relate] ' + interpret(labels, D, S, detail).split('\n\n')[0], sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
