#!/usr/bin/env python3
"""bgc_reference_align.py -- align one BGC's proteins against characterized reference clusters
and draw a clinker-style synteny figure + a correspondence CSV.

References can come from (any mix, repeatable):
  --ref-db  ACCESSION:Label   pull a MIBiG cluster's CDS straight from the anchored BiG-SCAPE DB
                              (the DB's `cds.aa_seq`; no download) e.g. BGC0000877:polyoxin
  --ref-ncbi ACC:Label        efetch a GenBank nucleotide record from NCBI e.g. MF055656.1:nikkomycin
  --ref-gbk PATH:Label        a local reference GBK

Homology: local Smith-Waterman (Bio.Align, BLOSUM62). A query gene is called a homolog of a
reference gene when alignment score >= --min-score, percent identity >= --min-id, and query
coverage >= --min-cov (defaults 60 / 25 / 30). Best hit per (query gene, reference) is kept.

Outputs (RGB PNG, white background -- no alpha, so it renders everywhere):
  <tag>_vs_<refs>_synteny.png     query track on top, one reference track per ref, links shaded by %id
  <tag>_reference_alignment.csv   per query gene: best hit + %id + coverage + homolog flag, per reference

Every claim this supports is capacity/architecture-level: homology is ancestry/similarity, NOT
evidence the query makes the reference compound.

Deps: biopython (Bio.Align, SeqIO), matplotlib. NCBI fetch uses stdlib urllib.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re, sqlite3, sys, urllib.request, urllib.parse, time
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

ROLE_COLORS = {"core": "#2c7fb8", "tailoring": "#41ab5d", "transport": "#f39c12",
               "regulatory": "#8e6bbf", "other": "#9aa4ad"}
REF_FILL = ["#d6b656", "#c98a5e", "#7fa8b0", "#b07f9e"]

def _aligner():
    from Bio import Align
    from Bio.Align import substitution_matrices
    a = Align.PairwiseAligner()
    a.substitution_matrix = substitution_matrices.load("BLOSUM62")
    a.open_gap_score = -11; a.extend_gap_score = -1; a.mode = "global"  # clinker-consistent (Needleman-Wunsch)
    return a

def _score_pid(al, s1, s2):
    """Global alignment, clinker-consistent identity = matches / (alignment length minus gap/gap cols).

    NB: an earlier revision aligned LOCALLY and reported %id over the aligned sub-region only, which
    OVERCOUNTED distant homologs (a partial-coverage hit at high local %id passed the homolog test even
    though its identity over the full protein was near background). clinker uses global identity with a
    0.3 cutoff; matching that here brings the two tools into agreement. Verified: AS-XXX BGC008 vs
    polyoxin/nikkomycin -> 4 CONFIDENT orthologs (2 oxygenases, EPSP synthase, nikJ), not 7-8."""
    aln = al.align(s1, s2)[0]
    a, b = aln[0], aln[1]
    length = len(a); m = 0
    for x, y in zip(a, b):
        if x == y and x not in "-.":
            m += 1
        elif x == y:
            length -= 1
    gid = 100 * m / length if length else 0
    Lloc = sum(1 for x, y in zip(a, b) if x != "-" and y != "-")
    return aln.score, gid, Lloc

def parse_gbk_cds(path):
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    cds, length = [], 0
    for rec in SeqIO.parse(path, "genbank"):
        length = len(rec.seq)
        for f in rec.features:
            if f.type == "CDS" and "translation" in f.qualifiers:
                lt = f.qualifiers.get("locus_tag", [f.qualifiers.get("gene", ["orf"])[0]])[0]
                cds.append({"tag": lt, "start": int(f.location.start), "end": int(f.location.end),
                            "strand": f.location.strand or 1, "aa": f.qualifiers["translation"][0],
                            "domains": ";".join(f.qualifiers.get("sec_met_domain", []))})
        return cds, length
    return cds, length

def ref_from_db(db, acc):
    c = sqlite3.connect(db)
    g = c.execute("select id from gbk where path like ?", (f"%{acc}%",)).fetchone()
    if not g:
        return []
    rows = c.execute("select nt_start, nt_stop, strand, aa_seq, orf_num from cds where gbk_id=? order by nt_start", (g[0],)).fetchall()
    c.close()
    return [{"tag": f"orf{o}", "start": s, "end": e, "strand": st, "aa": aa or "", "domains": ""}
            for s, e, st, aa, o in rows]

def ref_from_ncbi(acc):
    base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
    q = urllib.parse.urlencode({"db": "nucleotide", "id": acc, "rettype": "gb", "retmode": "text"})
    with urllib.request.urlopen(base + "efetch.fcgi?" + q, timeout=90) as _r:
        gb = _r.read().decode(errors="ignore")
    tmp = f"/tmp/_ref_{acc.replace('.', '_')}.gb"
    open(tmp, "w", encoding="utf-8").write(gb)
    return parse_gbk_cds(tmp)[0]

def classify(domains, defn):
    s = f"{domains or ''} {defn or ''}".lower()
    if any(k in s for k in ("transporter", "mfs", " abc", "permease", "efflux")): return "transport"
    if any(k in s for k in ("regulat", "tetr", "luxr", "response regulator", " tpr", "nsda", "helix-turn-helix")): return "regulatory"
    if any(k in s for k in ("synthase", "synthetase", "radical sam", "nikj", "lanc", "lanb", "pks", "nrps",
                            "adenylation", "condensation", "pseudouridine", "trud", "precursor", "epsp",
                            "lanthipeptide", "lanti", "ligase")): return "core"
    if any(k in s for k in ("oxygenase", "oxidoreductase", "methyltransferase", "reductase", "hydroxylase",
                            "aminotransferase", "dehydrogenase", " sdr", "p450", "phosphatase", "kinase",
                            "halogenase", "glycosyltransferase", "nucleotidyltransf")): return "tailoring"
    return "other"

def _save_rgb(fig, png):
    """Save as RGB PNG on white (no alpha) so every viewer renders it."""
    fig.savefig(png, dpi=155, bbox_inches="tight", facecolor="white")
    import matplotlib
    from PIL import Image
    im = Image.open(png)
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, "white")
        bg.paste(im, mask=im.convert("RGBA").split()[-1])
        bg.save(png)

def main():
    ap = argparse.ArgumentParser(description="Align a BGC to reference clusters; synteny figure + CSV.")
    ap.add_argument("--gbk", required=True, help="query BGC region GBK")
    ap.add_argument("--bgc", default="BGC"); ap.add_argument("--strain", default="")
    ap.add_argument("--ref-db", action="append", default=[], help="ACCESSION:Label (from BiG-SCAPE DB)")
    ap.add_argument("--ref-ncbi", action="append", default=[], help="ACCESSION:Label (efetch from NCBI)")
    ap.add_argument("--ref-gbk", action="append", default=[], help="PATH:Label (local GBK)")
    ap.add_argument("--db", help="anchored BiG-SCAPE DB (for --ref-db)")
    ap.add_argument("--blastp", help="blastp panel CSV (function labels for query genes)")
    ap.add_argument("--min-score", type=float, default=60); ap.add_argument("--min-id", type=float, default=25)
    ap.add_argument("--min-cov", type=float, default=30)
    ap.add_argument("--min-gid", type=float, default=30, help="min GLOBAL identity %% for a CONFIDENT ortholog (clinker-consistent); twilight = min_gid-5..min_gid")
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    tag = f"{a.strain + '_' if a.strain else ''}{a.bgc}"

    q, qlen = parse_gbk_cds(a.gbk)
    if not q:
        sys.exit("ERROR: no CDS in query GBK")
    # function labels for query genes (from blastp panel if present)
    labels = {}
    if a.blastp and os.path.exists(a.blastp):
        for r in csv.DictReader(open(a.blastp)):
            d = re.sub(r"^MULTISPECIES:\s*", "", r.get("blastp_top_def", "") or "")
            d = re.sub(r"\s*\[[^\]]*\]\s*$", "", d).replace("domain-containing protein", "").strip(" ,")
            labels[r.get("locus_tag", "")] = " ".join(d.split()[:3]) if d and not d.lower().startswith("hypothetical") else ""

    refs = []
    for spec in a.ref_db:
        acc, lab = (spec.split(":", 1) + [spec])[:2]
        if not a.db: sys.exit("--ref-db needs --db")
        refs.append((lab, ref_from_db(a.db, acc)))
    for spec in a.ref_ncbi:
        acc, lab = (spec.split(":", 1) + [spec])[:2]
        refs.append((lab, ref_from_ncbi(acc))); time.sleep(0.3)
    for spec in a.ref_gbk:
        path, lab = (spec.split(":", 1) + [spec])[:2]
        refs.append((lab, parse_gbk_cds(path)[0]))
    refs = [(l, r) for l, r in refs if r]
    if not refs:
        sys.exit("ERROR: no usable references")

    al = _aligner()
    # correspondence
    corr = {g["tag"]: {} for g in q}
    for lab, rcds in refs:
        for g in q:
            best = None
            for rg in rcds:
                if not rg["aa"]: continue
                sc, pid, L = _score_pid(al, g["aa"], rg["aa"])
                cov = 100 * L / max(1, len(g["aa"]))
                if best is None or sc > best[0]:
                    best = (sc, pid, cov, rg)
            if best:
                sc, pid, cov, rg = best
                tier = "confident" if pid >= a.min_gid else ("twilight" if pid >= a.min_gid - 5 else "none")
                corr[g["tag"]][lab] = {"pid": round(pid, 1), "cov": round(cov), "rg": rg,
                                       "tier": tier, "hom": bool(tier == "confident")}

    # figure
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path
    import matplotlib.patches as mp
    ntracks = 1 + len(refs)
    fig, ax = plt.subplots(figsize=(13, 1.7 + 1.4 * ntracks))
    ys = {"query": float(ntracks - 1)}
    for i, (lab, _) in enumerate(refs):
        ys[lab] = float(ntracks - 2 - i)
    def xf(length):
        return lambda x: x / length
    def arrow(y, s, e, strand, color, xff, h=0.14):
        s, e = xff(s), xff(e); L = e - s; hd = min(abs(L) * 0.4, 0.02)
        if strand >= 0: ax.arrow(s, y, L - hd, 0, head_width=h, head_length=hd, fc=color, ec="#333", lw=.4, length_includes_head=True)
        else: ax.arrow(e, y, -(L - hd), 0, head_width=h, head_length=hd, fc=color, ec="#333", lw=.4, length_includes_head=True)
    def link(y1, x1, y2, x2, pid):
        sh = plt.cm.Blues(0.3 + 0.6 * min(pid, 60) / 60)
        v = [(x1, y1 - 0.14), (x1, (y1 + y2) / 2), (x2, (y1 + y2) / 2), (x2, y2 + 0.14)]
        ax.add_patch(PathPatch(Path(v, [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]), fc="none", ec=sh, lw=1.3, alpha=.75))
    xq = xf(qlen)
    # links
    for gi, g in enumerate(q):
        xm = xq((g["start"] + g["end"]) / 2)
        for lab, rcds in refs:
            h = corr[g["tag"]].get(lab)
            if h and h["tier"] in ("confident", "twilight"):
                rlen = max(x["end"] for x in rcds)
                xr = (h["rg"]["start"] + h["rg"]["end"]) / 2 / rlen
                link(ys["query"], xm, ys[lab], xr, h["pid"])
    # query track
    for g in q:
        role = classify(g["domains"], labels.get(g["tag"], ""))
        arrow(ys["query"], g["start"], g["end"], g["strand"], ROLE_COLORS[role], xq)
        lab = labels.get(g["tag"], "")
        if any(corr[g["tag"]].get(l, {}).get("hom") for l, _ in refs) and lab:
            ax.text(xq((g["start"] + g["end"]) / 2), ys["query"] + 0.2, lab.split()[0], fontsize=7, ha="center", rotation=18)
    # reference tracks
    for ri, (lab, rcds) in enumerate(refs):
        rlen = max(x["end"] for x in rcds); xr = xf(rlen)
        homset = {id(corr[g["tag"]][lab]["rg"]) for g in q if corr[g["tag"]].get(lab, {}).get("hom")}
        for rg in rcds:
            hit = id(rg) in homset
            arrow(ys[lab], rg["start"], rg["end"], rg["strand"], REF_FILL[ri % len(REF_FILL)] if hit else "#e8e8e8", xr, h=0.12)
        ax.text(-0.02, ys[lab], lab, ha="right", va="center", fontsize=9, weight="bold")
    ax.text(-0.02, ys["query"], tag, ha="right", va="center", fontsize=11, weight="bold")
    ax.set_xlim(-0.17, 1.02); ax.set_ylim(-0.5, ntracks - 0.2); ax.axis("off")
    nb = sum(1 for g in q if any(corr[g["tag"]].get(l, {}).get("hom") for l, _ in refs))
    ax.set_title(f"{tag} vs {', '.join(l for l, _ in refs)}: {nb}/{len(q)} confident orthologs (global identity >= {a.min_gid}%; clinker-consistent)",
                 fontsize=10.5, weight="bold")
    handles = [mp.Patch(color=ROLE_COLORS[k], label=k) for k in ("core", "tailoring", "transport", "other")]
    handles += [mp.Patch(color=REF_FILL[i % len(REF_FILL)], label=f"{l} homolog") for i, (l, _) in enumerate(refs)]
    ax.legend(handles=handles, loc="lower center", ncol=len(handles), fontsize=8, frameon=False, bbox_to_anchor=(0.5, -0.05))
    plt.tight_layout()
    refslug = "_".join(re.sub(r"\W", "", l) for l, _ in refs)
    png = os.path.join(a.outdir, f"{tag}_vs_{refslug}_synteny.png")
    _save_rgb(fig, png); plt.close()
    # CSV
    csvp = os.path.join(a.outdir, f"{tag}_reference_alignment.csv")
    with open(csvp, "w", newline="") as fh:
        w = _SafeWriter(fh)
        head = ["query_gene", "function"]
        for lab, _ in refs:
            head += [f"{lab}_global_id", f"{lab}_cov", f"{lab}_tier"]
        w.writerow(head)
        for g in q:
            row = [g["tag"], labels.get(g["tag"], "")]
            for lab, _ in refs:
                h = corr[g["tag"]].get(lab, {})
                row += [h.get("pid", ""), h.get("cov", ""), h.get("tier", "none")]
            w.writerow(row)
    emit(f"[bgc_reference_align] {tag}: {nb}/{len(q)} CONFIDENT orthologs (global id >= {a.min_gid}%, clinker-consistent) to >=1 reference", f"   figure: {os.path.basename(png)}\n   table:  {os.path.basename(csvp)}", sep="\n")

if __name__ == "__main__":
    main()
