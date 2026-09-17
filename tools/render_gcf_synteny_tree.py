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
`BGC…` files) are labelled by accession and organism. Reference-layer files, i.e. files whose
name starts with a `--reference-prefix` (default `SID_`, `TYPE_`) or that follow the
`<genome stem>__<region file>` convention, are reference rows too: labelled by layer, organism
and accession, never given a package identity hold (they have no Mamey package by design).

Labels are wrapped onto two lines and the figure is widened to the longest label, so a full
four-component identity is never clipped. A family above `--max-tips` is drawn as a pruned
view: every query (non-reference) and MIBiG member is kept and the reference members nearest
to the `--focal` rows by tree distance fill the remainder; the title and caption say so.

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
    ("Halogenase / oxidative tailoring", "#8e44ad", re.compile(r"(halogenase|Trp_halog|FAD.dependent halogen|\bTrp_halogenase\b|PhyH|TauD|2OG-FeII|p450|cytochrome P450|monooxygenase|dioxygenase)", re.I)),
    ("Regulatory / resistance / transport", "#2c6fbb", re.compile(r"(regulator|transporter|efflux|resistance|ABC transporter|\bMFS\b)", re.I)),
]
OTHER, UNKNOWN = ("Other biosynthetic", "#f5a623"), ("Unknown function", "#ffffff")
ROLE_COLOURS = {name: col for name, col, _ in ROLES}
ROLE_COLOURS[OTHER[0]] = OTHER[1]
ROLE_COLOURS[UNKNOWN[0]] = UNKNOWN[1]
HOLD = "[alias unbound: identity hold]"
REFERENCE_PREFIXES = ("SID_", "TYPE_")     # cohort reference layers staged with a layer prefix
LABEL_PT = 6.8                              # row-label font size; the figure width is derived from it


def definition_organism(path):
    """Organism from the GBK DEFINITION line when ORGANISM is '.' (web-run antiSMASH GBKs of references)."""
    try:
        with open(path, encoding="utf-8", errors="replace") as h:
            text = h.read(4000)
    except OSError:
        return ""
    m = re.search(r"^DEFINITION\s+(.+?)(?=^\S)", text, re.M | re.S)
    if not m:
        return ""
    d = " ".join(m.group(1).split())
    d = re.sub(r"^\S+\.\d+\s+", "", d)
    d = re.sub(r"\s*(,)?\s*(complete|whole genome|plasmid|chromosome|contig|scaffold).*$", "", d, flags=re.I)
    return d.strip(" ,.")


def layer_identity(basename, organism, prefixes=REFERENCE_PREFIXES):
    """Reference-layer row -> label without a package identity hold; None when the file is not a layer file."""
    org = organism if organism and organism != "." else ""
    for pre in prefixes:
        if basename.startswith(pre):
            layer = pre.rstrip("_")
            m = re.match(r"^" + re.escape(pre) + r"(.+)\.(region\d+)\.gbk$", basename)
            stem, region = (m.group(1), m.group(2)) if m else (basename, "")
            acc = re.search(r"(?:^|_)((?:NZ_|NC_)?[A-Z]{1,6}\d{5,}\.\d+)$", stem)
            acc = acc.group(1) if acc else ""
            name = org or stem[: len(stem) - len(acc)].replace("_", " ").strip()
            return {"label": f"{layer} {name}  {acc} {region}".replace("  ", " ").strip(), "strain": "", "contig": acc or stem,
                    "region": region, "alias": "", "hold": "", "reference": True, "layer": layer}
    if "__" in basename:
        stem, rest = basename.split("__", 1)
        m = re.match(r"^(.+)\.(region\d+)\.gbk$", rest)
        acc, region = (m.group(1), m.group(2)) if m else (rest, "")
        return {"label": f"REF {org or stem.replace('_', ' ')}  {acc} {region}".strip(), "strain": "", "contig": acc,
                "region": region, "alias": "", "hold": "", "reference": True, "layer": "REF"}
    return None


def wrap_label(label):
    """`strain / contig / region / alias` -> two lines; long reference labels split at the double space."""
    parts = label.split(" / ")
    if len(parts) == 4:
        return f"{parts[0]} / {parts[1]}\n{parts[2]} / {parts[3]}"
    if len(label) > 48 and "  " in label:
        a, b = label.split("  ", 1)
        return f"{a}\n{b.strip()}"
    return label


def prune_to(tree, keep):
    for t in list(tree.get_terminals()):
        if t.name not in keep:
            tree.prune(t)
    return tree


def pruned_keep(tree, label_of, max_tips, focal_prefixes, is_reference):
    """Tips to keep for a family above max_tips: all query and MIBiG tips, then the references nearest the focal tips."""
    tips = [t.name for t in tree.get_terminals()]
    keep = {t for t in tips if not is_reference(label_of[t]) or re.match(r"^BGC\d+", label_of[t])}
    focal = [t for t in tips if any(label_of[t].startswith(p + "_") for p in focal_prefixes)] or [t for t in tips if not is_reference(label_of[t])]
    refs = [t for t in tips if t not in keep]
    if len(keep) < max_tips and refs and focal:
        term = {t.name: t for t in tree.get_terminals()}
        dist = {t: min(tree.distance(term[t], term[f]) for f in focal) for t in refs}
        for t in sorted(refs, key=lambda r: dist[r]):
            if len(keep) >= max_tips:
                break
            keep.add(t)
    return keep


def role_of(qualifiers):
    q = qualifiers
    kinds = " ".join(q.get("gene_kind", []))
    text = " ".join(q.get("sec_met_domain", []) + q.get("gene_functions", []) + q.get("product", []))
    for name, _col, rx in ROLES[:4]:
        if rx.search(text):
            return name
    if "regulatory" in kinds or "transport" in kinds or "resistance" in kinds or ROLES[4][2].search(text):
        return ROLES[4][0]
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


def pfam_by_protein(db_path, gbk_basename, _cache={}):
    """aa sequence -> set of Pfam accessions for one region file, from a BiG-SCAPE cds/hsp scan (prefilter only)."""
    key = (db_path, gbk_basename)
    if key not in _cache:
        db = sqlite3.connect(db_path); out = {}
        for aa, acc in db.execute("select c.aa_seq, h.accession from cds c join gbk g on g.id=c.gbk_id left join hsp h on h.cds_id=c.id where g.path like ?",
                                  ("%/" + gbk_basename,)):
            out.setdefault(aa or "", set())
            if acc:
                out[aa or ""].add(acc)
        db.close(); _cache[key] = out
    return _cache[key]


def adjacent_pairs(clusters, order, min_id, prefilter_db=None):
    """Homology links between neighbouring rows: BLOSUM62 global identity of every gene pair.
    With prefilter_db (a BiG-SCAPE database) only candidate pairs are aligned: length ratio >= min_id/100 (exact: identity
    over the alignment length cannot exceed min/max length) and a shared Pfam accession in the scan, or neither gene has one.
    The returned dict carries the candidate/total counts under the key "_stats"."""
    from Bio import Align
    from Bio.Align import substitution_matrices
    al = Align.PairwiseAligner(mode="global", open_gap_score=-11, extend_gap_score=-1)
    al.substitution_matrix = substitution_matrices.load("BLOSUM62")
    ratio = min_id / 100.0
    pairs, n_cand, n_all = {}, 0, 0
    for i in range(len(order) - 1):
        A, B = order[i], order[i + 1]
        pfA = pfam_by_protein(prefilter_db, os.path.basename(clusters[A]["path"])) if prefilter_db else {}
        pfB = pfam_by_protein(prefilter_db, os.path.basename(clusters[B]["path"])) if prefilter_db else {}
        hits = []
        for ga in clusters[A]["genes"]:
            da = pfA.get(ga["aa"], set())
            for gb in clusters[B]["genes"]:
                n_all += 1
                if prefilter_db:
                    la, lb = len(ga["aa"]), len(gb["aa"])
                    if not la or not lb or min(la, lb) / max(la, lb) < ratio:
                        continue
                    dbb = pfB.get(gb["aa"], set())
                    if (da or dbb) and not (da & dbb):
                        continue
                n_cand += 1
                pid = align_identity(ga["aa"], gb["aa"], al)
                if pid >= min_id:
                    hits.append((ga["id"], gb["id"], pid))
        pairs[(A, B)] = hits
    pairs["_stats"] = (n_cand, n_all)
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
    longest = max(max(len(x) for x in wrap_label(labels[t]["label"]).split("\n")) for t in tips)
    label_in = longest * LABEL_PT * 0.56 / 72.0 + 0.25       # inches the longest label line needs
    track_in, tree_in = 4.0 + span / 9000.0, 1.2
    W = tree_in + label_in + track_in
    fig = plt.figure(figsize=(W, 1.8 + n * 0.5 + 0.9))
    fr_t = tree_in / W
    ax_t = fig.add_axes([0.01, 0.10, fr_t - 0.01, 0.82]); ax_g = fig.add_axes([fr_t, 0.10, 1.0 - fr_t - 0.01, 0.82], sharey=ax_t)
    lab_units = label_in / track_in                          # label region in track units, left of x = 0
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
        ax_g.text(-0.01, y, wrap_label(lab["label"]), ha="right", va="center", fontsize=LABEL_PT, linespacing=1.15,
                  color="#202124" if lab["reference"] else "#bb0000")
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
    ax_g.set_xlim(-lab_units, 1.01); ax_g.set_ylim(-0.7, n - 0.3)
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
    ap.add_argument("--reference-prefix", action="append", default=None, help="file-name prefix of a cohort reference layer (default SID_, TYPE_)")
    ap.add_argument("--max-tips", type=int, default=0, help="above this many members draw a pruned view (0 = never prune)")
    ap.add_argument("--prefilter-db", default=None, help="BiG-SCAPE database whose Pfam scan restricts which gene pairs are aligned (defaults to --db)")
    ap.add_argument("--focal", action="append", default=[], help="strain prefix whose rows anchor the pruned view (repeatable)")
    ap.add_argument("--out", required=True, help="output stem")
    a = ap.parse_args(argv)
    prefixes = tuple(a.reference_prefix) if a.reference_prefix else REFERENCE_PREFIXES
    if a.prefilter_db is None and a.db:
        a.prefilter_db = a.db
    if a.prefilter_db == "none":
        a.prefilter_db = None
    is_reference = lambda base: re.match(r"^BGC\d+", base) is not None or layer_identity(base, "", prefixes) is not None
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
    missing = [t.name for t in tree.get_terminals() if t.name not in gbks]
    if missing:
        raise SystemExit(f"tips without a cluster file: {missing}")
    n_total = len(tree.get_terminals())
    pruned_note = ""
    if a.max_tips and n_total > a.max_tips:
        keep = pruned_keep(tree, label_of, a.max_tips, a.focal, is_reference)
        prune_to(tree, keep)
        pruned_note = f" [pruned view: {len(keep)} of {n_total} members]"
    tree.ladderize()
    clusters = {t.name: read_cluster(gbks[t.name]) for t in tree.get_terminals()}
    bound = load_identity(a.identity)
    labels = {}
    for t in tree.get_terminals():
        base = label_of[t.name]
        org = clusters[t.name]["organism"]
        org = org if org and org != "." else definition_organism(gbks[t.name])
        ident = layer_identity(base, org, prefixes)
        if ident is None:
            ident = row_identity(base, bound)
            ident["layer"] = "MIBiG" if ident["reference"] else "query"
            if ident["reference"]:
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
        pairs = adjacent_pairs(clusters, order, a.min_id, a.prefilter_db)
    n_cand, n_all = pairs.pop("_stats", (0, 0))
    out = Path(a.out)
    n_links = render(tree, clusters, labels, pairs, out, a.title + pruned_note, a.min_id)
    with open(str(out) + "_gene_roles.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeWriter(h, delimiter="\t", lineterminator="\n"); w.writerow(["row", "gene", "start", "end", "strand", "role", "track_flipped"])
        for t in order:
            for g in clusters[t]["genes"]:
                w.writerow([labels[t]["label"], g["id"], g["start"], g["end"], g["strand"], g["role"], clusters[t]["flipped"]])
    with open(str(out) + "_rows.tsv", "w", encoding="utf-8", newline="") as h:
        w = _SafeDictWriter(h, fieldnames=["tip", "file", "label", "strain", "contig", "region", "alias", "identity_hold", "reference", "organism", "layer"], delimiter="\t", lineterminator="\n")
        w.writeheader()
        for t in order:
            L = labels[t]
            w.writerow({"tip": t, "file": label_of[t], "layer": L.get("layer", ""), "label": L["label"], "strain": L["strain"], "contig": L["contig"], "region": L["region"],
                        "alias": L["alias"], "identity_hold": L["hold"], "reference": L["reference"], "organism": clusters[t]["organism"]})
    holds = sum(1 for t in order if labels[t]["hold"])
    src = f"BiG-SCAPE family {a.family} tree from {os.path.basename(a.db)}" if a.db else f"tree {os.path.basename(a.newick)}"
    pruned_cap = (f"; {pruned_note.strip(' []')} (every query and MIBiG member kept; reference members nearest to the focal rows by tree distance fill the rest)"
                  if pruned_note else "")
    cap = (f"Gene-cluster family figure. Left: {src}; tip order is ladderized{pruned_cap}. Right: one track per cluster, drawn to a common scale (10 kb bar), "
           f"arrows in the coding direction; each track is shifted, and reverse-complemented where needed, so its first ketosynthase (t2ks) gene sits on one vertical "
           f"line pointing right. Row labels are strain / contig / region / BGC alias copied from the bound package inventory; {holds} row(s) carry an identity hold "
           f"because no bound alias exists. MIBiG reference clusters are labelled by accession and organism; cohort reference-layer rows by layer, organism and accession. Arrow colours are gene roles read from antiSMASH qualifiers "
           f"through a fixed keyword table; the per-gene assignment is in {out.name}_gene_roles.tsv. Dotted lines join genes in neighbouring rows with global alignment "
           f"identity of at least {a.min_id:g} % ({n_links} links; " + ("from the supplied gene_pairs table" if a.pairs else "computed here, BLOSUM62 global") + "), "
           f"darker for higher identity" + (f"; alignment was computed for the {n_cand} of {n_all} neighbouring gene pairs whose lengths allow the identity "
           f"threshold and that share a Pfam domain in the BiG-SCAPE scan, or both lack one" if a.prefilter_db and not a.pairs else "") +
           f". Shared genes are homology, not compound identity; region boundaries are antiSMASH calls and contig-edge regions may be truncated. "
           f"Class-level architecture only; judgment deferred.")
    Path(str(out) + "_caption.txt").write_text(cap + "\n", encoding="utf-8")
    emit(f"[render_gcf_synteny_tree] {len(order)} clusters, {n_links} links, {holds} identity holds -> {out}.png/.pdf")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
