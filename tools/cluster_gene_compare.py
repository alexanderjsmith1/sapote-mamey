#!/usr/bin/env python3
"""cluster_gene_compare — gene-by-gene comparison of biosynthetic gene clusters.

Takes N cluster GBKs and produces a *substantial* deliverable rather than a bare CSV:

  1. AUTO-ANNOTATION.  Each gene is labelled from its own antiSMASH `sec_met_domain` /
     `gene_functions` / `product` qualifiers; genes with no annotation (e.g. ab-initio
     pyrodigal calls) inherit a label from an annotated ortholog by homology propagation.
     The resolved label is written into each GBK's `/gene` qualifier -> `annotated_gbks/`,
     so `clinker` (and any GBK viewer) shows real gene names automatically.

  2. PAIRWISE GENE ALIGNMENT.  Every gene is aligned to every gene in every other cluster
     (BLOSUM62). Identity is reported on a GLOBAL alignment (matches / alignment length),
     which is what clinker uses and which — unlike local %id over a partial region — does
     not overcount distant/partial homologs. A gene pair is a confident ortholog at
     global identity >= --min-id (default 30). Fast: pairwise protein alignment is ms-scale.

  3. ORTHOLOG GROUPS.  Confident pairs are joined into ortholog groups (single-linkage),
     giving a presence/identity matrix (group x cluster).

  4. DELIVERABLES:
       gene_pairs.csv          every cross-cluster gene pair (global id, coverage, tier)
       ortholog_matrix.csv     ortholog group x cluster, best identity + resolved label
       comparison_heatmap.png  annotated presence/identity heatmap (RGB, viewer-safe)
       annotated_gbks/*.gbk    input GBKs with /gene labels for clinker
       comparison.pdf          heatmap + METHODS + auto-INTERPRETATION (with --pdf)

Methods and interpretation travel WITH the data — no floating tables.

Alignment engine: Bio.Align global (BLOSUM62, gap -11/-1). Optional --engine pyswrd
prefilter for large inputs. Capacity/architecture-level: identity is homology (shared
ancestry), never proof of the same product.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, sys, re
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path


# ----------------------------------------------------------------------------- annotation
def _label_from_qualifiers(f):
    """Best functional label for a CDS feature from antiSMASH/GenBank qualifiers."""
    q = f.qualifiers
    # 1) sec_met_domain: most specific (e.g. 'truD', 'nikJ', 'Asn_synthase', 'LANC_like')
    for sm in q.get("sec_met_domain", []):
        name = sm.split("(")[0].strip()
        if name:
            return name
    # 2) gene_functions: SMCOG description or rule-based biosynthetic label
    for gf in q.get("gene_functions", []):
        m = re.search(r"SMCOG\d+:\s*(.+)", gf)
        if m:
            return m.group(1).strip().rstrip(" (").split("(")[0].strip()[:40]
        m = re.search(r"rule-based-clusters\)\s*([A-Za-z0-9_]+)", gf)
        if m:
            return m.group(1)
    # 3) product, if informative
    for p in q.get("product", []):
        if p and p.lower() not in ("hypothetical protein", "?", "unknown"):
            return p[:40]
    return None


def parse_gbk(path):
    """Return (records, genes) where genes = list of dicts with tag/aa/coords/label."""
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    recs = list(SeqIO.parse(str(path), "genbank"))
    genes = []
    for ri, rec in enumerate(recs):
        for f in rec.features:
            if f.type != "CDS" or "translation" not in f.qualifiers:
                continue
            tag = f.qualifiers.get("locus_tag", f.qualifiers.get("gene", ["orf"]))[0]
            genes.append({
                "rec_i": ri, "feat": f, "tag": tag,
                "start": int(f.location.start), "end": int(f.location.end),
                "aa": f.qualifiers["translation"][0], "label": _label_from_qualifiers(f),
            })
    return recs, genes


# ----------------------------------------------------------------------------- alignment
def _aligner():
    from Bio import Align
    from Bio.Align import substitution_matrices
    a = Align.PairwiseAligner()
    a.substitution_matrix = substitution_matrices.load("BLOSUM62")
    a.open_gap_score = -11
    a.extend_gap_score = -1
    a.mode = "global"          # clinker-consistent identity denominator
    return a


def global_identity(al, s1, s2):
    """clinker-style: matches / (alignment length minus gap/gap columns); + coverage."""
    aln = al.align(s1, s2)[0]
    a, b = aln[0], aln[1]
    length = len(a)
    m = 0
    for x, y in zip(a, b):
        if x == y and x not in "-.":
            m += 1
        elif x == y:
            length -= 1
    gid = 100 * m / length if length else 0
    aligned = sum(1 for x, y in zip(a, b) if x != "-" and y != "-")
    cov = 100 * aligned / max(len(s1), len(s2)) if max(len(s1), len(s2)) else 0
    return gid, cov


def prefilter(clusters, min_id):
    """Optional pyswrd prefilter: returns set of (ci,gi,cj,gj) candidate pairs; None => all."""
    try:
        import pyswrd
    except Exception:
        return None
    flat = [(ci, gi, g["aa"]) for ci, (_, genes) in enumerate(clusters) for gi, g in enumerate(genes)]
    seqs = [x[2] for x in flat]
    keep = set()
    hits = list(pyswrd.search(seqs, seqs, max_evalue=1.0, max_alignments=25))
    for h in hits:
        qi, ti = h.query_index, h.target_index
        if qi == ti:
            continue
        ci, gi, _ = flat[qi]; cj, gj, _ = flat[ti]
        if ci < cj:
            keep.add((ci, gi, cj, gj))
        elif cj < ci:
            keep.add((cj, gj, ci, gi))
    return keep


# ----------------------------------------------------------------------------- grouping
class DSU:
    def __init__(self): self.p = {}
    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def union(self, a, b): self.p[self.find(a)] = self.find(b)


# ----------------------------------------------------------------------------- main compare
def compare(labels, gbks, min_id=30.0, min_cov=0.0, engine="biopython"):
    clusters, recs = [], {}
    for lab, p in zip(labels, gbks):
        r, genes = parse_gbk(p)          # parse ONCE: genes' "feat" point into r's features
        clusters.append((lab, genes)); recs[lab] = r
    al = _aligner()
    cand = prefilter(clusters, min_id) if engine == "pyswrd" else None

    pairs = []           # (ci,gi,cj,gj,gid,cov)
    dsu = DSU()
    n = len(clusters)
    for ci in range(n):
        for cj in range(ci + 1, n):
            gi_list = clusters[ci][1]; gj_list = clusters[cj][1]
            for gi, ga in enumerate(gi_list):
                for gj, gb in enumerate(gj_list):
                    if cand is not None and (ci, gi, cj, gj) not in cand:
                        continue
                    gid, cov = global_identity(al, ga["aa"], gb["aa"])
                    if gid >= min_id and cov >= min_cov:
                        pairs.append((ci, gi, cj, gj, round(gid, 1), round(cov)))
                        dsu.union((ci, gi), (cj, gj))

    # ortholog groups + label propagation (best label in a group wins)
    groups = {}
    for ci, (_, genes) in enumerate(clusters):
        for gi, g in enumerate(genes):
            groups.setdefault(dsu.find((ci, gi)), []).append((ci, gi))
    resolved = {}
    for root, members in groups.items():
        lab = next((clusters[ci][1][gi]["label"] for ci, gi in members
                    if clusters[ci][1][gi]["label"]), None)
        for ci, gi in members:
            resolved[(ci, gi)] = lab or clusters[ci][1][gi]["tag"]

    return clusters, recs, pairs, groups, resolved


# ----------------------------------------------------------------------------- outputs
def write_annotated_gbks(labels, gbks, clusters, recs, resolved, outdir):
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    d = Path(outdir) / "annotated_gbks"; d.mkdir(parents=True, exist_ok=True)
    out = []
    for ci, (lab, genes) in enumerate(clusters):
        gi = 0
        for g in genes:
            g["feat"].qualifiers["gene"] = [resolved[(ci, gi)]]
            gi += 1
        p = d / f"{lab}.gbk"
        SeqIO.write(recs[lab], str(p), "genbank")
        out.append(str(p))
    return out


def write_csvs(labels, clusters, pairs, groups, resolved, outdir):
    op = Path(outdir)
    # gene pairs
    with open(op / "gene_pairs.csv", "w", newline="") as fh:
        w = _SafeWriter(fh)
        w.writerow(["cluster_A", "geneA", "labelA", "cluster_B", "geneB", "labelB",
                    "global_identity_pct", "coverage_pct", "tier"])
        for ci, gi, cj, gj, gid, cov in sorted(pairs, key=lambda x: -x[4]):
            tier = "confident" if gid >= 30 else "twilight"
            w.writerow([labels[ci], clusters[ci][1][gi]["tag"], resolved[(ci, gi)],
                        labels[cj], clusters[cj][1][gj]["tag"], resolved[(cj, gj)],
                        gid, cov, tier])
    # ortholog matrix (group x cluster)
    rows = []
    for root, members in groups.items():
        by = {}
        for ci, gi in members:
            by.setdefault(ci, gi)
        label = resolved[members[0]]
        span = len(set(ci for ci, _ in members))
        rows.append((span, label, by, members))
    rows.sort(key=lambda x: (-x[0], x[1]))
    with open(op / "ortholog_matrix.csv", "w", newline="") as fh:
        w = _SafeWriter(fh)
        w.writerow(["ortholog_group_label", "n_clusters"] + list(labels))
        for span, label, by, members in rows:
            cells = []
            for ci in range(len(labels)):
                cells.append(clusters[ci][1][by[ci]]["tag"] if ci in by else "")
            w.writerow([label, span] + cells)
    return rows


def build_identity_matrix(disp, pairs, n):
    """Build the (ortholog-group x cluster) identity matrix for the comparison heatmap.

    Each cell is the member's % identity to its ortholog group's anchor member (100 on the
    anchor itself). F03 (v9.7.353): a pairwise identity that was never measured is left as
    NaN and its (row, col) coordinate is returned in ``unmeasured`` — it is NEVER back-filled
    with a fabricated number. The previous code substituted 60, which rendered indistinguishably
    from a real measurement and silently entered the figure as data.

    Returns ``(M, unmeasured)`` where ``M`` is a float ndarray (NaN = no measurement / not a
    member of the group) and ``unmeasured`` is the set of cells that ARE group members but whose
    identity-to-anchor was not measured (so a renderer can label them distinctly, e.g. "n/a").
    """
    import numpy as np
    G = len(disp)
    M = np.full((G, n), np.nan)
    pid_lookup = {}
    for ci, gi, cj, gj, gid, cov in pairs:
        pid_lookup[(ci, gi, cj, gj)] = gid
        pid_lookup[(cj, gj, ci, gi)] = gid
    unmeasured = set()
    for gr, (span, label, by, members) in enumerate(disp):
        # anchor = first member; fill identity of each member vs anchor (100 for anchor)
        anchor = members[0]
        for ci, gi in members:
            if (ci, gi) == anchor:
                M[gr, ci] = 100
            else:
                pid = pid_lookup.get((anchor[0], anchor[1], ci, gi))
                if pid is None:
                    # F03: unmeasured — do NOT fabricate a value; leave NaN, flag the cell.
                    unmeasured.add((gr, ci))
                else:
                    M[gr, ci] = pid
    return M, unmeasured


def make_heatmap(labels, clusters, rows, pairs, outdir, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    n = len(labels)
    # identity of each group member to the group's best-annotated anchor cluster
    # build matrix: rows=ortholog groups (present in >=2 clusters first), cols=clusters
    disp = [r for r in rows if r[0] >= 2] + [r for r in rows if r[0] == 1]
    G = len(disp)
    M, unmeasured = build_identity_matrix(disp, pairs, n)
    fig_h = max(3.5, 0.32 * G + 1.2)
    fig, ax = plt.subplots(figsize=(1.6 + 1.15 * n, fig_h), dpi=150)
    cmap = plt.cm.YlGnBu.copy()
    cmap.set_bad(color="#f0f0f0")  # F03: NaN/unmeasured cells render as neutral grey, not a colour on the identity scale
    im = ax.imshow(M, aspect="auto", cmap=cmap, vmin=25, vmax=100)
    ax.set_xticks(range(n)); ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(G))
    ax.set_yticklabels([r[1][:34] for r in disp], fontsize=8)
    for gr in range(G):
        for ci in range(n):
            v = M[gr, ci]
            if not np.isnan(v):
                ax.text(ci, gr, f"{int(v)}", ha="center", va="center", fontsize=7,
                        color="white" if v > 62 else "#222")
            elif (gr, ci) in unmeasured:
                # F03: member present but identity-to-anchor unmeasured — label distinctly,
                # never as a numeric identity.
                ax.text(ci, gr, "n/a", ha="center", va="center", fontsize=6,
                        style="italic", color="#999")
    ax.set_title(title, fontsize=11, pad=10)
    cb = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cb.set_label("% identity to group anchor", fontsize=8)
    ax.set_xlabel("cluster", fontsize=9)
    plt.tight_layout()
    # RGB-on-white flatten (viewer-safe)
    p = Path(outdir) / "comparison_heatmap.png"
    fig.savefig(p, facecolor="white", edgecolor="white")
    plt.close(fig)
    from PIL import Image
    im2 = Image.open(p)
    if im2.mode != "RGB":
        bg = Image.new("RGB", im2.size, "white"); bg.paste(im2, mask=im2.split()[-1] if "A" in im2.mode else None)
        bg.save(p)
    return str(p)


def interpret(labels, clusters, rows):
    """Auto-generate an interpretation paragraph from the ortholog matrix."""
    n = len(labels)
    core = [r for r in rows if r[0] == n]
    partial = [r for r in rows if 2 <= r[0] < n]
    singleton_by = {ci: 0 for ci in range(n)}
    for r in rows:
        if r[0] == 1:
            singleton_by[list(r[2].keys())[0]] += 1
    lines = []
    lines.append(
        f"Across {n} clusters ({', '.join(labels)}), {len(core)} ortholog group(s) are shared by "
        f"all {n} — the conserved core — while {len(partial)} are shared by a subset and the remainder "
        f"are cluster-specific.")
    if core:
        lines.append("Core (all clusters): " + ", ".join(sorted(set(r[1][:30] for r in core))) + ".")
    # which cluster is most divergent (most singletons)
    if singleton_by:
        mx = max(singleton_by, key=singleton_by.get)
        lines.append(
            f"{labels[mx]} carries the most cluster-specific genes ({singleton_by[mx]}), i.e. it is the "
            f"most divergent / most decorated of the set.")
    lines.append(
        "Identity is measured on global protein alignments (clinker-consistent); it reflects homology "
        "(shared ancestry), not identity of the final product. A shared core with divergent periphery is "
        "the signature of related clusters that elaborate a common scaffold differently.")
    return "\n\n".join(lines)


def make_pdf(labels, clusters, rows, heatmap_png, outdir, title, min_id, engine):
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage
    from PIL import Image as PILImage
    styles = getSampleStyleSheet()
    H = ParagraphStyle("H", parent=styles["Heading2"], spaceBefore=10, spaceAfter=4, textColor="#1a3a5a")
    body = ParagraphStyle("B", parent=styles["BodyText"], fontSize=9.5, leading=13)
    p = Path(outdir) / "comparison.pdf"
    doc = SimpleDocTemplate(str(p), pagesize=letter,
                            leftMargin=0.8 * inch, rightMargin=0.8 * inch,
                            topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    story = [Paragraph(title, styles["Title"]), Spacer(1, 6)]
    # figure
    iw, ih = PILImage.open(heatmap_png).size
    w = 6.9 * inch; h = w * ih / iw
    story += [RLImage(heatmap_png, width=w, height=min(h, 8.2 * inch)), Spacer(1, 8)]
    story.append(Paragraph(
        "Figure 1. Gene-by-gene ortholog map. Rows are ortholog groups (labelled by resolved "
        "function); columns are clusters; cells show %% identity to the group anchor. Blank = no "
        "ortholog above the confident threshold.", body))
    # interpretation
    story.append(Paragraph("Interpretation", H))
    for para in interpret(labels, clusters, rows).split("\n\n"):
        story.append(Paragraph(para, body))
    # methods
    story.append(Paragraph("Computational methods", H))
    gcounts = ", ".join(f"{lab} ({len(g)} CDS)" for lab, g in clusters)
    story.append(Paragraph(
        f"Inputs: {len(labels)} cluster GenBank files — {gcounts}. Each CDS was labelled from its "
        f"antiSMASH sec_met_domain / gene_functions / product qualifiers; unannotated CDS inherited a "
        f"label from an annotated ortholog by homology propagation, and the resolved label was written "
        f"to the /gene qualifier of each GenBank record (for clinker display).", body))
    story.append(Paragraph(
        f"Every CDS was aligned to every CDS in every other cluster with a global Needleman-Wunsch "
        f"alignment (BLOSUM62, gap open -11, extend -1; engine: {engine}). Percent identity was computed "
        f"on the global alignment as matches / (alignment length minus gap-gap columns) — the same "
        f"metric clinker uses — which avoids the overcounting that local %%identity over a partial "
        f"aligned region produces. A gene pair was scored a confident ortholog at global identity "
        f">= {min_id}%%. Confident pairs were joined into ortholog groups by single-linkage clustering.", body))
    story.append(Paragraph(
        "Limitations: identity is homology, not product identity; ab-initio (pyrodigal) gene calls have "
        "approximate boundaries; truncated/edge clusters under-report shared genes. Capacity-level "
        "throughout.", body))
    doc.build(story)
    return str(p)


# ----------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(description="Gene-by-gene comparison of BGCs -> CSV + figure + PDF.")
    ap.add_argument("--gbk", action="append", required=True, metavar="LABEL:path.gbk",
                    help="cluster GenBank, repeatable; LABEL is the column name")
    ap.add_argument("--outdir", default="cluster_compare_out")
    ap.add_argument("--title", default="Gene-by-gene cluster comparison")
    ap.add_argument("--min-id", type=float, default=30.0, help="confident-ortholog global identity %%")
    ap.add_argument("--min-cov", type=float, default=0.0)
    ap.add_argument("--engine", choices=["biopython", "pyswrd"], default="biopython",
                    help="pyswrd prefilters candidate pairs for large inputs")
    ap.add_argument("--pdf", action="store_true", help="also emit comparison.pdf (methods + interpretation)")
    a = ap.parse_args(argv)

    labels, gbks = [], []
    for spec in a.gbk:
        lab, path = spec.split(":", 1)
        labels.append(lab); gbks.append(path)
    os.makedirs(a.outdir, exist_ok=True)

    clusters, recs, pairs, groups, resolved = compare(
        labels, gbks, min_id=a.min_id, min_cov=a.min_cov, engine=a.engine)
    ann = write_annotated_gbks(labels, gbks, clusters, recs, resolved, a.outdir)
    rows = write_csvs(labels, clusters, pairs, groups, resolved, a.outdir)
    heat = make_heatmap(labels, clusters, rows, pairs, a.outdir, a.title)
    outs = ["gene_pairs.csv", "ortholog_matrix.csv", os.path.basename(heat),
            f"annotated_gbks/ ({len(ann)} files)"]
    if a.pdf:
        pdf = make_pdf(labels, clusters, rows, heat, a.outdir, a.title, a.min_id, a.engine)
        outs.append(os.path.basename(pdf))
    ncore = sum(1 for r in rows if r[0] == len(labels))
    emit(f'[cluster_gene_compare] {len(labels)} clusters, {len(pairs)} confident gene pairs, {len(rows)} ortholog groups ({ncore} core in all {len(labels)}).', f'[cluster_gene_compare] outputs -> {a.outdir}/: ' + ', '.join(outs), sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
