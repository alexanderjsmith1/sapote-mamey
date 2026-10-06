#!/usr/bin/env python3
r"""Cluster protein-inventory comparisons and descriptive UPGMA summaries.

--metric one_to_one_v1: maximum-weight one-to-one global-identity matching, with
identity below --min-id excluded, normalized by the larger CDS inventory. This is
bounded and symmetric; repeated copies are counted individually. It establishes
neither orthology, compound identity, activity, nor a phylogenetic outgroup.
The default legacy_checked retains the historical formula only when both directions
agree within floating-point tolerance and are bounded; otherwise it refuses.
The selected metric, threshold, alignment engine and inventories accompany outputs.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, sys, math, re, unicodedata, json
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


def _legacy_pair_result(left, right, al, min_id, allowed):
    """Legacy directed result, retained solely for the temporary refusal check."""
    best = {}
    for gi, a in enumerate(left):
        for gj, b in enumerate(right):
            if not allowed(gi, gj):
                continue
            g = _gid(al, a, b)
            if not math.isfinite(g) or not 0 <= g <= 100:
                raise ValueError("cluster_relate held: global identity is nonfinite or outside [0, 100]")
            if g >= min_id and g > best.get(gi, 0):
                best[gi] = g
    shared = len(best)
    mean_id = (sum(best.values()) / shared / 100) if shared else 0
    sim = (shared / max(1, min(len(left), len(right)))) * mean_id
    dist = 1 - sim
    if not all(math.isfinite(x) and 0 <= x <= 1 for x in (sim, dist)):
        raise ValueError("cluster_relate held: legacy similarity/distance is nonfinite or outside [0, 1]; "
                         "repeat handling and the scientific metric require a declared contract")
    return shared, mean_id, sim, dist


def _same_directional_result(a, b):
    # Compare unrounded results; tolerance admits floating arithmetic noise only.
    emitted_a = (a[0], round(a[1] * 100, 1), round(a[2], 4), round(a[3], 4))
    emitted_b = (b[0], round(b[1] * 100, 1), round(b[2], 4), round(b[3], 4))
    return emitted_a == emitted_b and all(math.isclose(x, y, rel_tol=1e-12, abs_tol=1e-12)
                                         for x, y in zip(a[1:], b[1:]))


def _newick_label(label):
    # Biopython NewickIO.Writer uses single quotes and doubles embedded apostrophes.
    if re.fullmatch(r"[^\s()\[\]\x27:;,]+", label):
        return label
    return "'" + label.replace("'", "''") + "'"


def _validate_labels(labels):
    if any(not isinstance(label, str) or not label.strip() for label in labels):
        raise ValueError("cluster_relate labels must be nonempty strings (not blank)")
    if len(set(labels)) != len(labels):
        raise ValueError("cluster_relate labels must be unique")
    for label in labels:
        if any(unicodedata.category(ch) in {'Cc', 'Cf', 'Cs'} for ch in label):
            raise ValueError("cluster_relate labels cannot contain control, format or surrogate characters")
        serialized = _newick_label(label)
        if serialized == label:
            continue
        # Installed Newick readers can differ on escaped apostrophes. Admit only a
        # quoted spelling that preserves exactly one identical leaf in Bio.Phylo.
        _verify_newick_label_roundtrip(serialized + ';', [label])


def _verify_newick_label_roundtrip(newick, labels):
    try:
        from io import StringIO
        from Bio import Phylo
        tree = Phylo.read(StringIO(newick), 'newick')
        names = [leaf.name for leaf in tree.get_terminals()]
        exact = len(names) == len(labels) and set(names) == set(labels)
    except Exception as exc:
        raise ValueError("cluster_relate label cannot be verified with the installed Newick parser") from exc
    if not exact:
        raise ValueError("cluster_relate labels cannot round-trip exactly through the installed Newick parser")


def _maximum_weight_matching(weights):
    """Rectangular assignment padded with zero-valued unmatched slots (Hungarian)."""
    if not weights or not weights[0]:
        return []
    nr, nc = len(weights), len(weights[0])
    if any(len(row) != nc for row in weights):
        raise ValueError("matching matrix must be rectangular")
    if any(not math.isfinite(x) or x < 0 for row in weights for x in row):
        raise ValueError("matching weights must be finite and nonnegative")
    size = max(nr, nc)
    u, v, owner, previous = [[0] * (size + 1) for _ in range(4)]
    for i in range(1, size + 1):
        owner[0] = i
        minimum, used = [float("inf")] * (size + 1), [False] * (size + 1)
        column = 0
        while True:
            used[column] = True
            row, delta, next_column = owner[column], float("inf"), 0
            for j in range(1, size + 1):
                if used[j]:
                    continue
                weight = weights[row - 1][j - 1] if row <= nr and j <= nc else 0
                reduced = -weight - u[row] - v[j]
                if reduced < minimum[j]:
                    minimum[j], previous[j] = reduced, column
                if minimum[j] < delta:
                    delta, next_column = minimum[j], j
            for j in range(size + 1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            column = next_column
            if owner[column] == 0:
                break
        while True:
            prior = previous[column]
            owner[column] = owner[prior]
            column = prior
            if column == 0:
                break
    return [(owner[j] - 1, j - 1, weights[owner[j] - 1][j - 1])
            for j in range(1, size + 1) if 0 < owner[j] <= nr and j <= nc
            and weights[owner[j] - 1][j - 1] > 0]


def _one_to_one_result(left, right, al, min_id):
    if not left or not right:
        raise ValueError("one_to_one_v1 requires nonempty translated CDS inventories; empty is unmeasured")
    # Canonical sequence orientation fixes alignment tie-breaking across input swaps.
    left, right = sorted(left), sorted(right)
    if tuple(left) > tuple(right):
        left, right = right, left
    weights = []
    for seq in left:
        row = []
        for other in right:
            first, second = sorted((seq, other))
            identity = _gid(al, first, second)
            if not math.isfinite(identity) or not 0 <= identity <= 100:
                raise ValueError("global identity must be finite and in [0, 100]")
            row.append(identity / 100 if identity >= min_id else 0)
        weights.append(row)
    matches = _maximum_weight_matching(weights)
    total = sum(weight for _, _, weight in matches)
    shared = len(matches)
    mean_id = total / shared if shared else 0
    similarity = total / max(len(left), len(right))
    return shared, mean_id, similarity, 1 - similarity


def pairwise_distances(labels, gbks, min_id=30.0, engine="biopython", metric="legacy_checked", provenance=None):
    _validate_labels(labels)
    if len(labels) != len(gbks):
        raise ValueError("cluster_relate requires one label per input cluster")
    if not math.isfinite(min_id) or not 0 <= min_id <= 100:
        raise ValueError("cluster_relate --min-id must be finite and in [0, 100]")
    if metric not in ("legacy_checked", "one_to_one_v1"):
        raise ValueError("unknown cluster relationship metric")
    if engine not in ("biopython", "pyswrd"):
        raise ValueError("unknown alignment engine")
    clusters = [_genes(p) for p in gbks]
    if metric == "one_to_one_v1" and any(not genes for genes in clusters):
        raise ValueError("one_to_one_v1 requires nonempty translated CDS inventories")
    al = _aligner()
    n = len(clusters)
    # optional pyswrd prefilter of candidate ortholog pairs (fast for large inputs)
    cand = None
    if engine == "pyswrd" and metric == "legacy_checked":
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
    if provenance is not None:
        provenance.update({"requested_engine": engine,
            "effective_engine": "biopython_global_all_pairs" if cand is None else "pyswrd_candidates_biopython_global",
            "prefilter_state": "NOT_USED_BY_CONTRACT" if metric == "one_to_one_v1" else
                "AVAILABLE" if cand is not None else "FALLBACK_ALL_PAIRS" if engine == "pyswrd" else "NOT_REQUESTED"})
    D = [[0.0] * n for _ in range(n)]
    S = [[1.0] * n for _ in range(n)]
    detail = {}
    for ci in range(n):
        for cj in range(ci + 1, n):
            if metric == "one_to_one_v1":
                shared, mean_id, sim, dist = _one_to_one_result(clusters[ci], clusters[cj], al, min_id)
                D[ci][cj] = D[cj][ci] = round(dist, 4)
                S[ci][cj] = S[cj][ci] = round(sim, 4)
                detail[(ci, cj)] = (shared, round(mean_id * 100, 1))
                continue
            forward = _legacy_pair_result(clusters[ci], clusters[cj], al, min_id,
                lambda gi, gj: cand is None or (ci, gi, cj, gj) in cand)
            reverse = _legacy_pair_result(clusters[cj], clusters[ci], al, min_id,
                lambda gj, gi: cand is None or (ci, gi, cj, gj) in cand)
            if not _same_directional_result(forward, reverse):
                raise ValueError(f"cluster_relate held: directional legacy results disagree for "
                                 f"{labels[ci]!r} and {labels[cj]!r}; repeat handling and the "
                                 "scientific metric require a declared contract")
            # Keep the admitted legacy result; do not clip, average or replace the metric.
            shared, mean_id, sim, dist = forward
            D[ci][cj] = D[cj][ci] = round(dist, 4)
            S[ci][cj] = S[cj][ci] = round(sim, 4)
            detail[(ci, cj)] = (shared, round(mean_id * 100, 1))
    return clusters, D, S, detail


# ---- tree + outputs ---------------------------------------------------------------------------
def _validate_distance_matrix(labels, D):
    _validate_labels(labels)
    n = len(labels)
    if not n or len(D) != n or any(len(row) != n for row in D):
        raise ValueError("cluster_relate distance matrix must be nonempty and square, matching labels")
    for i, row in enumerate(D):
        for j, value in enumerate(row):
            try:
                valid = math.isfinite(value) and 0 <= value <= 1
            except (TypeError, ValueError):
                valid = False
            if not valid:
                raise ValueError("cluster_relate distance matrix values must be finite and in [0, 1]")
            if i == j and value != 0:
                raise ValueError("cluster_relate distance matrix diagonal must be zero")
    for i in range(n):
        for j in range(i + 1, n):
            if not math.isclose(D[i][j], D[j][i], rel_tol=1e-12, abs_tol=1e-12):
                raise ValueError("cluster_relate distance matrix must be symmetric")


def upgma_newick(labels, D):
    """Pure-python UPGMA -> Newick (no external tree lib needed)."""
    _validate_distance_matrix(labels, D)
    n = len(labels)
    clusters = {i: (_newick_label(labels[i]), 1) for i in range(n)}   # id -> (newick_str, size)
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
    newick = clusters[active[0]][0] + ";"
    if any(_newick_label(label) != label for label in labels):
        # Verify the complete tree as well: tokenization can depend on neighboring
        # quoted labels, e.g. a trailing backslash before a closing quote.
        _verify_newick_label_roundtrip(newick, labels)
    return newick


def make_dendrogram(labels, D, outdir, title):
    _validate_distance_matrix(labels, D)
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
        f"Least similar input under this descriptive metric: {labels[outgroup]} "
        f"(mean similarity {mean_sim[outgroup]:.2f}).",
        "Distance combines gene-content overlap and global sequence identity (clinker-consistent); "
        "it reflects homology, not identity of the final product.",
    ]
    return "\n\n".join(lines)


def make_pdf(labels, D, S, detail, dendro_png, outdir, title, min_id, metric="legacy_checked"):
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
                       "similarity combines the selected inventory metric and global protein identity).", body),
             Paragraph("Interpretation", H)]
    for para in interpret(labels, D, S, detail).split("\n\n"):
        story.append(Paragraph(para, body))
    story.append(Paragraph("Computational methods", H))
    story.append(Paragraph(
        f"Inputs: {len(labels)} cluster GenBank files. Selected metric: {metric}; threshold {min_id}%. "
        "Global BLOSUM62 alignment with gap -11/-1 supplies protein identity. For one_to_one_v1, "
        "maximum-weight one-to-one matching uses identity divided by 100 and excludes pairs below "
        "threshold; similarity is summed matching weight divided by the larger inventory size. "
        "For legacy_checked, the historical directed best-hit/minimum-inventory result is retained "
        "only after symmetric bounded-result checks. Distance is 1 minus similarity. UPGMA is a "
        "descriptive comparison and establishes neither phylogenetic outgroups nor orthology. "
        "No compound or activity inference follows.", body))
    doc.build(story)
    return str(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Relationship tree + distance matrix from cluster GBKs.")
    ap.add_argument("--gbk", action="append", required=True, metavar="LABEL:cluster.gbk")
    ap.add_argument("--outdir", default="cluster_relate_out")
    ap.add_argument("--title", default="Cluster relationships")
    ap.add_argument("--min-id", type=float, default=30.0)
    ap.add_argument("--engine", choices=["biopython", "pyswrd"], default="biopython")
    ap.add_argument("--metric", choices=["legacy_checked", "one_to_one_v1"], default="legacy_checked")
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args(argv)
    labels, gbks = [], []
    for spec in a.gbk:
        lab, path = spec.split(":", 1); labels.append(lab); gbks.append(path)
    if len(labels) < 2:
        ap.error("cluster_relate requires at least two input clusters")
    try:
        engine_provenance = {}
        clusters, D, S, detail = pairwise_distances(labels, gbks, min_id=a.min_id, engine=a.engine, metric=a.metric, provenance=engine_provenance)
        nwk = upgma_newick(labels, D)
    except ValueError as exc:
        ap.error(str(exc))
    names = ["distance_matrix.csv", "tree.nwk", "dendrogram.png", "comparison_contract.json"]
    if a.pdf:
        names.append("comparison.pdf")
    if any((Path(a.outdir) / name).exists() or (Path(a.outdir) / name).is_symlink() for name in names):
        ap.error("comparison outputs must be fresh")
    from mamey.output_transaction import fresh_output_set
    with fresh_output_set(a.outdir, names) as stage:
        (stage / "comparison_contract.json").write_text(json.dumps({
            "schema": "cluster_relationship_contract_v1", "metric": a.metric,
            "min_identity_pct": a.min_id, **engine_provenance,
            "inventory_counts": dict(zip(labels, map(len, clusters))),
            "normalization": "maximum_inventory_count" if a.metric == "one_to_one_v1" else "minimum_inventory_count",
            "inference_ceiling": "descriptive protein inventory homology; no orthology, compound or activity inference"
        }, indent=2) + "\n", encoding="utf-8")
        # distance matrix CSV
        with open(stage / "distance_matrix.csv", "w", newline="") as fh:
            w = _SafeWriter(fh); w.writerow([""] + labels)
            for i, lab in enumerate(labels):
                w.writerow([lab] + D[i])
        (stage / "tree.nwk").write_text(nwk + "\n")
        dendro = make_dendrogram(labels, D, stage, a.title)
        outs = ["distance_matrix.csv", "tree.nwk", "dendrogram.png", "comparison_contract.json"]
        if a.pdf:
            make_pdf(labels, D, S, detail, dendro, stage, a.title, a.min_id, a.metric); outs.append("comparison.pdf")
    emit(f"[cluster_relate] {len(labels)} clusters -> {', '.join(outs)} in {a.outdir}/", '[cluster_relate] ' + interpret(labels, D, S, detail).split('\n\n')[0], sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
