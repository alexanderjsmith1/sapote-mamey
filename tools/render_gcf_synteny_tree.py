#!/usr/bin/env python3
"""render_gcf_synteny_tree — one gene-cluster family as a tree beside gene-arrow tracks.

Left: the family tree (a Newick file, or the tree BiG-SCAPE stored for a family in its
database). Right: one track per cluster, drawn to a common scale, arrows in coding direction,
coloured by gene role. Dotted lines join homologous genes in neighbouring rows. Tracks are
shifted, and reverse-complemented where needed, so the first type II ketosynthase (t2ks)
gene of every cluster sits on one vertical line pointing right; clusters with no t2ks keep
their raw frame.

    render_gcf_synteny_tree.py --db anchored.db --family 12444 --gbk-dir regions/ \
        --gbk-dir mibig_gbk/ --identity <strain>_2_inventory.csv ... --out fam12444

    render_gcf_synteny_tree.py --newick tree.nwk --gbk LABEL:cluster.gbk ... --out fam

Row labels follow the four-component BGC identity rule, `strain / contig / region / alias`,
copied from one bound package record (`--identity`, the Mamey `*_2_inventory.csv`; the
Source_GBK column binds the region file to its BGC alias). A cohort region with no bound
alias is drawn but labelled `[alias unbound: identity hold]`. Reference clusters (MIBiG
`BGC…` files) are labelled by accession and organism.

Gene roles come only from antiSMASH qualifiers on each CDS (gene_kind, gene_functions,
sec_met_domain) through the fixed keyword table ROLES; every gene's assignment is written to
`<out>_gene_roles.tsv`. Homology comes from `--pairs` (tools/cluster_gene_compare.py
gene_pairs.csv) or, without it, from global BLOSUM62 alignment of neighbouring rows computed
here with the same identity definition. Shared genes are homology, never compound identity;
the figure is a class-level architecture view and defers judgment.
"""
import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re, sqlite3  # noqa: E402
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
from pathlib import Path  # noqa: E402

ROLES = [
    ("Minimal PKS (KS/CLF/ACP)", "#d7191c", re.compile(r"\b(t2ks|t2clf|t2pks2|ketosynthase|chain.length.factor)\b", re.I)),
    ("Cyclase / aromatase / ketoreductase", "#7f0000", re.compile(r"(cyclase|aromatase|TcmN|SnoaL|ketoreductase|\bKR\b|adh_short|Polyketide_cyc)", re.I)),
    ("Glycosyltransferase / sugar biosynthesis", "#1a9641", re.compile(r"(glycos|glyco_tran|DUF1205|NAD_binding_4|Epimerase|dTDP|GDP_Man|DegT_DnrJ|Polysacc_synt|sugar|rhamn)", re.I)),
    ("Regulatory / resistance / transport", "#2c6fbb", re.compile(r"(regulator|transporter|efflux|resistance|ABC transporter|\bMFS\b)", re.I)),
]
OTHER, UNKNOWN = ("Other biosynthetic", "#f5a623"), ("Unknown function", "#ffffff")
ROLE_COLOURS = {name: col for name, col, _ in ROLES}
ROLE_COLOURS[OTHER[0]] = OTHER[1]
ROLE_COLOURS[UNKNOWN[0]] = UNKNOWN[1]
HOLD = "[alias unbound: identity hold]"


def role_of(qualifiers):
    q = qualifiers
    kinds = " ".join(q.get("gene_kind", []))
    text = " ".join(q.get("sec_met_domain", []) + q.get("gene_functions", []) + q.get("product", []))
    for name, _col, rx in ROLES[:3]:
        if rx.search(text):
            return name
    if "regulatory" in kinds or "transport" in kinds or "resistance" in kinds or ROLES[3][2].search(text):
        return ROLES[3][0]
    if "biosynthetic" in kinds:
        return OTHER[0]
    return UNKNOWN[0]


def read_cluster(path):
    """Genes of one region GBK, anchored on the first t2ks gene and oriented so it points right."""
    try:
        from Bio import SeqIO  # type: ignore
    except ImportError:  # biopython is optional: the bundled shim reads antiSMASH region GBKs
        from mamey._gbk_shim import SeqIO  # type: ignore
    rec = next(SeqIO.parse(path, "genbank"))
    genes = []
    for f in rec.features:
        if f.type != "CDS":
            continue
        q = f.qualifiers
        name = (q.get("locus_tag") or q.get("gene") or q.get("protein_id") or ["?"])[0]
        is_ks = any(re.match(r"\s*t2ks\b", d, re.I) for d in q.get("sec_met_domain", []))
        genes.append({"id": name, "start": int(f.location.start), "end": int(f.location.end),
                      "strand": f.location.strand or 1, "role": role_of(q), "ks": is_ks,
                      "aa": (q.get("translation") or [""])[0]})
    length = len(rec.seq)
    ks = next((g for g in genes if g["ks"]), None)
    flipped = bool(ks and ks["strand"] < 0)
    if flipped:
        for g in genes:
            g["start"], g["end"], g["strand"] = length - g["end"], length - g["start"], -g["strand"]
    anchor = (ks["start"] + ks["end"]) / 2 if ks else 0
    organism = rec.annotations.get("organism") or rec.description or ""
    return {"length": length, "genes": genes, "anchor": anchor, "flipped": flipped, "organism": organism, "path": path}


def split_region_name(basename):
    """`<strain>_<contig>.region<NNN>.gbk` -> (strain, contig, region); MIBiG `BGC…gbk` -> (acc, '', '')."""
    stem = re.sub(r"\.gbk$", "", basename)
    if re.match(r"^BGC\d+", stem):
        return stem.split(".")[0], "", ""
    m = re.match(r"^(.+?)_((?:NODE|contig|scaffold|tig|k\d+)_.+)\.(region\d+)$", stem, re.I)
    if m:
        return m.group(1), m.group(2), m.group(3)
    m = re.match(r"^(.+)\.(region\d+)$", stem)
    if m:
        return "", m.group(1), m.group(2)
    return "", stem, ""


def load_identity(paths):
    """Source_GBK basename -> (strain-free record) from Mamey *_2_inventory.csv files."""
    bound = {}
    for p in paths:
        with open(p, encoding="utf-8", newline="") as h:
            for r in csv.DictReader(h):
                src = os.path.basename((r.get("Source_GBK") or "").strip())
                if src:
                    bound[src] = {"alias": (r.get("BGC_ID") or "").strip(), "contig": (r.get("Contig") or "").strip(),
                                  "region": (r.get("antiSMASH_Region") or r.get("Region") or "").strip(), "file": p}
    return bound


def row_identity(basename, bound):
    strain, contig, region = split_region_name(basename)
    if not contig:                                   # reference cluster
        return {"label": strain, "strain": "", "contig": "", "region": "", "alias": "", "hold": "", "reference": True}
    key = basename[len(strain) + 1:] if strain and basename.startswith(strain + "_") else basename
    rec = bound.get(key) or bound.get(basename)
    if rec and rec["alias"]:
        if rec["contig"] and rec["contig"] != contig:
            hold = f"contig mismatch: package {rec['contig']} vs file {contig}"
            return {"label": f"{strain} / {contig} / {region} / {HOLD}", "strain": strain, "contig": contig, "region": region, "alias": "", "hold": hold, "reference": False}
        return {"label": f"{strain} / {contig} / {region} / {rec['alias']}", "strain": strain, "contig": contig, "region": region, "alias": rec["alias"], "hold": "", "reference": False}
    return {"label": f"{strain} / {contig} / {region} / {HOLD}", "strain": strain, "contig": contig, "region": region, "alias": "", "hold": "no bound package record for this region file", "reference": False}


def family_from_db(db_path, family_id, gbk_dirs):
    db = sqlite3.connect(db_path)
    row = db.execute("select newick from family where id=?", (family_id,)).fetchone()
    if not row or not row[0]:
        raise SystemExit(f"family {family_id}: no tree stored in {db_path}")
    members = {}
    for rid, path in db.execute("select r.id, g.path from bgc_record_family bf join bgc_record r on r.id=bf.record_id "
                                "join gbk g on g.id=r.gbk_id where bf.family_id=?", (family_id,)):
        base = os.path.basename(path)
        local = next((os.path.join(d, base) for d in gbk_dirs if os.path.isfile(os.path.join(d, base))), None)
        if not local:
            raise SystemExit(f"family {family_id}: member {base} not found under {gbk_dirs}")
        members[str(rid)] = local
    return row[0], members


def align_identity(a, b, aligner):
    if not a or not b:
        return 0.0
    aln = aligner.align(a, b)[0]
    matches = sum(1 for x, y in zip(*aln) if x == y and x != "-")
    return 100.0 * matches / max(1, len(aln[0]))


def adjacent_pairs(clusters, order, min_id):
    from Bio import Align
    from Bio.Align import substitution_matrices
    al = Align.PairwiseAligner(mode="global", open_gap_score=-11, extend_gap_score=-1)
    al.substitution_matrix = substitution_matrices.load("BLOSUM62")
    pairs = {}
    for i in range(len(order) - 1):
        A, B = order[i], order[i + 1]
        hits = []
        for ga in clusters[A]["genes"]:
            for gb in clusters[B]["genes"]:
                pid = align_identity(ga["aa"], gb["aa"], al)
                if pid >= min_id:
                    hits.append((ga["id"], gb["id"], pid))
        pairs[(A, B)] = hits
    return pairs


def load_pairs(path, min_id):
    pairs = {}
    with open(path, encoding="utf-8", newline="") as h:
        for r in csv.DictReader(h):
            pid = float(r["global_identity_pct"])
            if pid < min_id:
                continue
            pairs.setdefault((r["cluster_A"], r["cluster_B"]), []).append((r["geneA"], r["geneB"], pid))
            pairs.setdefault((r["cluster_B"], r["cluster_A"]), []).append((r["geneB"], r["geneA"], pid))
    return pairs


def render(tree, clusters, labels, pairs, out, title, min_id):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrow, Patch
    tips = [t.name for t in tree.get_terminals()]
    n = len(tips)
    left_ext = max(clusters[t]["anchor"] for t in tips)
    right_ext = max(clusters[t]["length"] - clusters[t]["anchor"] for t in tips)
    span = left_ext + right_ext
    off = {t: left_ext - clusters[t]["anchor"] for t in tips}
    scale = 1.0 / span
    fig = plt.figure(figsize=(5.0 + span / 9000.0, 1.8 + n * 0.5 + 0.9))
    ax_t = fig.add_axes([0.02, 0.10, 0.15, 0.82]); ax_g = fig.add_axes([0.18, 0.10, 0.81, 0.82], sharey=ax_t)
    ax_t.axis("off"); ax_g.axis("off")
    depths = tree.depths(); xmax = max(depths.values()) or 1.0
    ypos = {t: n - 1 - i for i, t in enumerate(tree.get_terminals())}
    for cl in tree.get_nonterminals(order="postorder"):
        ypos[cl] = sum(ypos[c] for c in cl.clades) / len(cl.clades)
    for cl in tree.get_nonterminals():
        x = depths[cl] / xmax
        for c in cl.clades:
            ax_t.plot([x, x], [ypos[cl], ypos[c]], color="#222", lw=1.0)
            ax_t.plot([x, depths[c] / xmax], [ypos[c], ypos[c]], color="#222", lw=1.0)
    ax_t.set_xlim(-0.02, 1.02); ax_t.set_ylim(-0.7, n - 0.3)
    ytip = {t.name: ypos[t] for t in tree.get_terminals()}
    for t in tips:
        y = ytip[t]; lab = labels[t]
        ax_g.text(-0.005, y, lab["label"], ha="right", va="center", fontsize=6.8, color="#202124" if lab["reference"] else "#bb0000")
        for g in clusters[t]["genes"]:
            x0, x1 = (g["start"] + off[t]) * scale, (g["end"] + off[t]) * scale
            w = x1 - x0; head = min(0.006, 0.5 * w)      # never a zero-length arrow: it degenerates into a flat line
            args = (x0, y, w) if g["strand"] >= 0 else (x1, y, -w)
            ax_g.add_patch(FancyArrow(*args, 0, width=0.32, head_width=0.42, head_length=head, length_includes_head=True,
                                      fc=ROLE_COLOURS[g["role"]], ec="#333", lw=0.4))
    n_links = 0
    for i in range(n - 1):
        A, B = tips[i], tips[i + 1]
        gA = {g["id"]: g for g in clusters[A]["genes"]}; gB = {g["id"]: g for g in clusters[B]["genes"]}
        for ga, gb, pid in pairs.get((A, B), []):
            if ga in gA and gb in gB:
                xa = ((gA[ga]["start"] + gA[ga]["end"]) / 2 + off[A]) * scale
                xb = ((gB[gb]["start"] + gB[gb]["end"]) / 2 + off[B]) * scale
                ax_g.plot([xa, xb], [ytip[A] - 0.22, ytip[B] + 0.22], ls=(0, (1.5, 1.5)), lw=0.6, color="#444", alpha=min(1.0, 0.35 + pid / 100))
                n_links += 1
    ax_g.set_xlim(-0.30, 1.01); ax_g.set_ylim(-0.7, n - 0.3)
    ax_g.plot([0.0, 10000 * scale], [-0.55, -0.55], color="#222", lw=1.2)
    ax_g.text(10000 * scale / 2, -0.68, "10 kb", ha="center", va="top", fontsize=7)
    fig.legend(handles=[Patch(facecolor=c, edgecolor="#333", label=k) for k, c in ROLE_COLOURS.items()], loc="lower center", ncol=3, fontsize=7.5, frameon=False, bbox_to_anchor=(0.6, 0.0))
    fig.suptitle(title, fontsize=11, x=0.02, ha="left")
    fig.savefig(str(out) + ".png", dpi=200); fig.savefig(str(out) + ".pdf"); plt.close(fig)
    return n_links


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--newick"); ap.add_argument("--db"); ap.add_argument("--family", type=int)
    ap.add_argument("--gbk", action="append", default=[], help="LABEL:path.gbk (with --newick)")
    ap.add_argument("--gbk-dir", action="append", default=[], help="folders searched for family member files (with --db)")
    ap.add_argument("--map", action="append", default=[], help="tipid=label (with --newick)")
    ap.add_argument("--identity", action="append", default=[], help="Mamey *_2_inventory.csv binding region files to BGC aliases")
    ap.add_argument("--pairs", help="gene_pairs.csv from cluster_gene_compare.py; omitted: neighbouring rows are aligned here")
    ap.add_argument("--min-id", type=float, default=30.0)
    ap.add_argument("--title", default="Gene-cluster family: tree and gene architecture")
    ap.add_argument("--out", required=True, help="output stem")
    a = ap.parse_args(argv)
    from Bio import Phylo
    from io import StringIO
    if a.db:
        newick, members = family_from_db(a.db, a.family, a.gbk_dir)
        tree = Phylo.read(StringIO(newick), "newick")
        gbks = {rid: p for rid, p in members.items()}
        label_of = {rid: os.path.basename(p) for rid, p in members.items()}
    else:
        tree = Phylo.read(a.newick, "newick")
        idmap = dict(m.split("=", 1) for m in a.map)
        gbks = dict(g.split(":", 1) for g in a.gbk)
        label_of = {}
        for t in tree.get_terminals():
            t.name = idmap.get(t.name, t.name)
            label_of[t.name] = os.path.basename(gbks.get(t.name, ""))
        gbks = {t.name: gbks[t.name] for t in tree.get_terminals() if t.name in gbks}
    tree.ladderize()
    missing = [t.name for t in tree.get_terminals() if t.name not in gbks]
    if missing:
        raise SystemExit(f"tips without a cluster file: {missing}")
    clusters = {t.name: read_cluster(gbks[t.name]) for t in tree.get_terminals()}
    bound = load_identity(a.identity)
    labels = {}
    for t in tree.get_terminals():
        ident = row_identity(label_of[t.name], bound)
        if ident["reference"]:
            org = clusters[t.name]["organism"]
            ident["label"] = f"{ident['label']}  {org}".strip()
        labels[t.name] = ident
    order = [t.name for t in tree.get_terminals()]
    if a.pairs:
        pairs = load_pairs(a.pairs, a.min_id)
        # --pairs rows are keyed by the labels cluster_gene_compare was given; accept either tip ids or file stems
        alias = {}
        for t in order:
            alias[t] = t; alias[re.sub(r"\.gbk$", "", label_of[t])] = t
        pairs = {(alias.get(k[0], k[0]), alias.get(k[1], k[1])): v for k, v in pairs.items()}
    else:
        pairs = adjacent_pairs(clusters, order, a.min_id)
    out = Path(a.out)
    n_links = render(tree, clusters, labels, pairs, out, a.title, a.min_id)
    with open(str(out) + "_gene_roles.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeWriter(h, delimiter="\t", lineterminator="\n"); w.writerow(["row", "gene", "start", "end", "strand", "role", "track_flipped"])
        for t in order:
            for g in clusters[t]["genes"]:
                w.writerow([labels[t]["label"], g["id"], g["start"], g["end"], g["strand"], g["role"], clusters[t]["flipped"]])
    with open(str(out) + "_rows.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=["tip", "file", "label", "strain", "contig", "region", "alias", "identity_hold", "reference", "organism"], delimiter="\t", lineterminator="\n")
        w.writeheader()
        for t in order:
            L = labels[t]
            w.writerow({"tip": t, "file": label_of[t], "label": L["label"], "strain": L["strain"], "contig": L["contig"], "region": L["region"],
                        "alias": L["alias"], "identity_hold": L["hold"], "reference": L["reference"], "organism": clusters[t]["organism"]})
    holds = sum(1 for t in order if labels[t]["hold"])
    src = f"BiG-SCAPE family {a.family} tree from {os.path.basename(a.db)}" if a.db else f"tree {os.path.basename(a.newick)}"
    cap = (f"Gene-cluster family figure. Left: {src}; tip order is ladderized. Right: one track per cluster, drawn to a common scale (10 kb bar), "
           f"arrows in the coding direction; each track is shifted, and reverse-complemented where needed, so its first ketosynthase (t2ks) gene sits on one vertical "
           f"line pointing right. Row labels are strain / contig / region / BGC alias copied from the bound package inventory; {holds} row(s) carry an identity hold "
           f"because no bound alias exists. Reference clusters are labelled by accession and organism. Arrow colours are gene roles read from antiSMASH qualifiers "
           f"through a fixed keyword table; the per-gene assignment is in {out.name}_gene_roles.tsv. Dotted lines join genes in neighbouring rows with global alignment "
           f"identity of at least {a.min_id:g} % ({n_links} links; " + ("from the supplied gene_pairs table" if a.pairs else "computed here, BLOSUM62 global") + "), "
           f"darker for higher identity. Shared genes are homology, not compound identity; region boundaries are antiSMASH calls and contig-edge regions may be truncated. "
           f"Class-level architecture only; judgment deferred.")
    Path(str(out) + "_caption.txt").write_text(cap + "\n", encoding="utf-8")
    emit(f"[render_gcf_synteny_tree] {len(order)} clusters, {n_links} links, {holds} identity holds -> {out}.png/.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
