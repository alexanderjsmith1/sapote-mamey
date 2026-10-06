#!/usr/bin/env python3
"""Compare translated CDSs using global protein identity and single-link homology groups.

The groups may contain paralogs and transitive links; they do not establish orthology.
All copies are retained in homology_matrix.csv and homology_members.csv. The legacy
ortholog_matrix.csv filename is an identical compatibility alias, with homology headers.
Original GenBank qualifiers remain intact. Inferred display labels are recorded separately
as mamey_homology_label, with group provenance; conflicting source labels remain explicit.
The heatmap uses one deterministic representative per cluster/group, not copy-count evidence.
Outputs require fresh destinations. No compound, activity or functional assignment follows.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, sys, re, math, json
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path
from mamey.path_safety import safe_label, contained_output_path


# ----------------------------------------------------------------------------- annotation
def _label_from_qualifiers(f):
    """Best functional label for a CDS feature from antiSMASH/GenBank qualifiers."""
    q = f.qualifiers
    if q.get("gene"):
        return q["gene"][0]
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
    s1, s2 = sorted((s1, s2))  # canonical orientation preserves input-swap tie behavior
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
    for label in labels:
        safe_label(label)
    if len(labels) != len(gbks) or len({lab.casefold() for lab in labels}) != len(labels):
        raise ValueError("one unique, case-insensitive safe label is required per input")
    if any(not math.isfinite(x) or not 0 <= x <= 100 for x in (min_id, min_cov)):
        raise ValueError("identity and coverage thresholds must be finite percentages")
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

    # Thresholded single-link homology groups retain all copies and label conflicts.
    groups = {}
    for ci, (_, genes) in enumerate(clusters):
        for gi, g in enumerate(genes):
            groups.setdefault(dsu.find((ci, gi)), []).append((ci, gi))
    resolved = {}
    for members in groups.values():
        source_labels = sorted({clusters[ci][1][gi]["label"] for ci, gi in members
                                if clusters[ci][1][gi]["label"]})
        group_label = source_labels[0] if len(source_labels) == 1 else (
            "CONFLICT: " + " | ".join(source_labels) if source_labels else None)
        for ci, gi in members:
            gene = clusters[ci][1][gi]
            gene["homology_source_labels"] = source_labels
            gene["homology_method"] = f"thresholded_single_link_homology; min_identity_pct={min_id}; min_coverage_pct={min_cov}; engine={engine}; orthology_not_established; source_labels="
            resolved[(ci, gi)] = group_label or gene["tag"]

    return clusters, recs, pairs, groups, resolved


# ----------------------------------------------------------------------------- outputs
def write_annotated_gbks(labels, gbks, clusters, recs, resolved, outdir):
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    for label in labels:
        safe_label(label)
    d = Path(outdir) / "annotated_gbks"
    if d.is_symlink():
        raise ValueError("annotated_gbks must not be a symlink")
    paths = [contained_output_path(d, lab, ".gbk") for lab, _ in clusters]
    if any(p.exists() or p.is_symlink() for p in paths):
        raise ValueError("annotated GenBank outputs must be fresh")
    d.mkdir(parents=True, exist_ok=True)
    out = []
    for ci, ((lab, genes), p) in enumerate(zip(clusters, paths)):
        for gi, gene in enumerate(genes):
            gene["feat"].qualifiers["mamey_homology_label"] = [resolved[(ci, gi)]]
            gene["feat"].qualifiers["mamey_homology_meta"] = [
                gene.get("homology_method", "thresholded_single_link_homology; orthology_not_established; source_labels=")
                + json.dumps(gene.get("homology_source_labels", []), ensure_ascii=True)]
        with p.open("x", encoding="utf-8") as handle:
            SeqIO.write(recs[lab], handle, "genbank")
        out.append(str(p))
    return out


def write_csvs(labels, clusters, pairs, groups, resolved, outdir):
    op = Path(outdir)
    # gene pairs
    with open(op / "gene_pairs.csv", "x", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        w.writerow(["cluster_A", "geneA", "labelA", "cluster_B", "geneB", "labelB",
                    "global_identity_pct", "coverage_pct", "tier"])
        for ci, gi, cj, gj, gid, cov in sorted(pairs, key=lambda x: -x[4]):
            tier = "confident" if gid >= 30 else "twilight"
            w.writerow([labels[ci], clusters[ci][1][gi]["tag"], resolved[(ci, gi)],
                        labels[cj], clusters[cj][1][gj]["tag"], resolved[(cj, gj)],
                        gid, cov, tier])
    rows = []
    for members in groups.values():
        members = sorted(members, key=lambda m: (labels[m[0]], clusters[m[0]][1][m[1]]["tag"], m[1]))
        by = {}
        for ci, gi in members:
            by.setdefault(ci, gi)  # heatmap representative only; full roster below
        label = resolved[members[0]]
        rows.append((len(by), label, by, members))
    rows.sort(key=lambda x: (-x[0], x[1], [(labels[c], clusters[c][1][g]["tag"], g) for c,g in x[3]]))
    for name in ("homology_matrix.csv", "ortholog_matrix.csv"):
        with (op / name).open("x", newline="", encoding="utf-8") as fh:
            w = _SafeWriter(fh)
            w.writerow(["homology_group", "homology_group_label", "n_clusters"] + list(labels))
            for number, (span, label, by, members) in enumerate(rows, 1):
                cells = [json.dumps([clusters[ci][1][gi]["tag"] for c, gi in members if c == ci])
                         for ci in range(len(labels))]
                w.writerow([f"HG{number:05d}", label, span] + cells)
    with (op / "homology_members.csv").open("x", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        w.writerow(["homology_group", "cluster", "record_index", "gene_index", "locus_tag",
                    "start_zero_based", "end_exclusive", "source_label", "group_display_label"])
        for number, (_, label, _, members) in enumerate(rows, 1):
            for ci, gi in members:
                g = clusters[ci][1][gi]
                w.writerow([f"HG{number:05d}", labels[ci], g["rec_i"], gi, g["tag"],
                            g["start"], g["end"], g["label"] or "", label])
    return rows


def build_identity_matrix(disp, pairs, n):
    """Build the (homology-group x cluster) identity matrix for the comparison heatmap.

    Each cell is the member's % identity to its homology group's anchor member (100 on the
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
            if by and by.get(ci) != gi:
                continue
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
    # build matrix: rows=homology groups (present in >=2 clusters first), cols=clusters
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
        f"Across {n} clusters ({', '.join(labels)}), {len(core)} homology group(s) are shared by "
        f"all {n} — the conserved core — while {len(partial)} are shared by a subset and the remainder "
        f"are cluster-specific.")
    if core:
        lines.append("Core (all clusters): " + ", ".join(sorted(set(r[1][:30] for r in core))) + ".")
    if singleton_by:
        mx = max(singleton_by, key=singleton_by.get)
        lines.append(f"{labels[mx]} has the largest count of groups found only in that input "
                     f"({singleton_by[mx]}). This count is not an evolutionary divergence estimate.")
    lines.append("Thresholded single-link groups can include paralogs and transitive connections. "
                 "No orthology, compound or activity inference follows. The figure displays one "
                 "representative per cluster/group; CSVs retain all copies and conflicting labels.")
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
        "Figure 1. Gene-by-gene homology map. Rows are homology groups (labelled by resolved "
        "display labels); columns are clusters; cells show representative identity to the group anchor. Blank = no "
        "admitted member or an unmeasured anchor pair; neither is biological absence.", body))
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
        f"label from an annotated homolog by homology propagation, and the inferred label was recorded separately "
        f"in /mamey_homology_label, with /mamey_homology_meta; original /gene remains intact.", body))
    story.append(Paragraph(
        f"Every CDS was aligned to every CDS in every other cluster with a global Needleman-Wunsch "
        f"alignment (BLOSUM62, gap open -11, extend -1; engine: {engine}). Percent identity was computed "
        f"on the global alignment as matches / (alignment length minus gap-gap columns) — the same "
        f"metric clinker uses — which avoids the overcounting that local %%identity over a partial "
        f"aligned region produces. A gene pair was scored a threshold-admitted homolog at global identity "
        f">= {min_id}%%. Confident pairs were joined into homology groups by single-linkage clustering.", body))
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
    ap.add_argument("--min-id", type=float, default=30.0, help="homology admission global identity percent")
    ap.add_argument("--min-cov", type=float, default=0.0)
    ap.add_argument("--engine", choices=["biopython", "pyswrd"], default="biopython",
                    help="pyswrd prefilters candidate pairs for large inputs")
    ap.add_argument("--pdf", action="store_true", help="also emit comparison.pdf (methods + interpretation)")
    a = ap.parse_args(argv)

    labels, gbks = [], []
    for spec in a.gbk:
        lab, path = spec.split(":", 1)
        labels.append(lab); gbks.append(path)
    try:
        for lab in labels:
            safe_label(lab)
        if len({lab.casefold() for lab in labels}) != len(labels):
            raise ValueError("labels collide ignoring case")
        root = Path(a.outdir)
        names = ["gene_pairs.csv", "homology_matrix.csv", "ortholog_matrix.csv", "homology_members.csv",
                 "comparison_heatmap.png"] + (["comparison.pdf"] if a.pdf else [])
        if any((root / name).is_symlink() for name in names):
            raise ValueError("comparison output must not be a symlink")
        outputs = [contained_output_path(root, name) for name in names]
        if (root / "annotated_gbks").exists() or (root / "annotated_gbks").is_symlink():
            raise ValueError("annotated_gbks output directory must be fresh")
        if any(p.exists() or p.is_symlink() for p in outputs):
            raise ValueError("all comparison outputs must be fresh")
    except ValueError as exc:
        ap.error(str(exc))

    clusters, recs, pairs, groups, resolved = compare(
        labels, gbks, min_id=a.min_id, min_cov=a.min_cov, engine=a.engine)
    names.extend(f"annotated_gbks/{lab}.gbk" for lab in labels)
    from mamey.output_transaction import fresh_output_set
    with fresh_output_set(a.outdir, names) as stage:
        ann = write_annotated_gbks(labels, gbks, clusters, recs, resolved, stage)
        rows = write_csvs(labels, clusters, pairs, groups, resolved, stage)
        heat = make_heatmap(labels, clusters, rows, pairs, stage, a.title)
        outs = ["gene_pairs.csv", "homology_matrix.csv", "homology_members.csv", "ortholog_matrix.csv", os.path.basename(heat),
                f"annotated_gbks/ ({len(ann)} files)"]
        if a.pdf:
            pdf = make_pdf(labels, clusters, rows, heat, stage, a.title, a.min_id, a.engine)
            outs.append(os.path.basename(pdf))
    ncore = sum(1 for r in rows if r[0] == len(labels))
    emit(f'[cluster_gene_compare] {len(labels)} clusters, {len(pairs)} confident gene pairs, {len(rows)} homology groups ({ncore} core in all {len(labels)}).', f'[cluster_gene_compare] outputs -> {a.outdir}/: ' + ', '.join(outs), sep="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
