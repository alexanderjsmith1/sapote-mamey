#!/usr/bin/env python3
"""bgc_figures.py -- per-BGC figure set for Sapote-Mamey deliverables.

Emits up to three figures for one BGC, plus the underlying data CSV for each (so every
figure is reproducible and auditable, not a black box):

  fig1 locus map        <- region GBK (gene coords/strand) + blastp panel (function labels)
  fig2 GCF novelty      <- anchored BiG-SCAPE DB (nearest-neighbour GCF distances)
  fig3 per-gene BLASTp  <- blastp panel (pct_identity per gene, labelled by function)

Design notes:
  - No dashed/dotted reference lines and no "marker" call-outs (clean, publication-style).
  - Genes are labelled by function (from the BLASTp top-def, else the antiSMASH domain, else
    the locus tag) rather than g1/g2/g3.
  - Every figure writes a sibling *_data.csv.
  - fig1 needs only the region GBK; fig2 needs --db; fig3 needs --blastp. Missing inputs are
    skipped with a note, so the tool degrades gracefully.

Deps: matplotlib, dna_features_viewer (fig1), Bio (GBK parse), sqlite3/csv/re (stdlib).

Usage:
  python bgc_figures.py --bgc BGC008 --strain AS-XXX \
      --gbk NODE_162_..._region001.gbk \
      --blastp BGC008_online_blastp.csv \
      --db cohort.db --mibig-index mibig_reference_index.bacterial.json \
      --outdir figs/
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, os, re, sqlite3, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter


def _save_rgb(fig, png):
    """Save RGB PNG on white (no alpha) so it renders in every viewer."""
    import matplotlib.pyplot as plt
    fig.savefig(png, dpi=150, bbox_inches="tight", facecolor="white")
    try:
        from PIL import Image
        im = Image.open(png)
        if im.mode in ("RGBA", "LA", "P"):
            bg = Image.new("RGB", im.size, "white")
            bg.paste(im, mask=im.convert("RGBA").split()[-1]); bg.save(png)
    except Exception:
        pass

ROLE_COLORS = {"core": "#2c7fb8", "tailoring": "#41ab5d", "transport": "#f39c12",
               "regulatory": "#8e6bbf", "other": "#9aa4ad"}

def classify(domains, defn):
    s = f"{domains or ''} {defn or ''}".lower()
    if any(k in s for k in ("transporter", "mfs", " abc", "permease", "efflux", "secretion")):
        return "transport"
    if any(k in s for k in ("regulat", "tetr", "luxr", "sigma factor", "response regulator",
                            " tpr", "nsda", " xre", "marr", "sarp", "helix-turn-helix")):
        return "regulatory"
    if any(k in s for k in ("ketosynth", " pks", "nrps", "condensation", "adenylation",
                            "amp-binding", "lanc", "lanb", "radical sam", "synthase",
                            "synthetase", "pseudouridine", "trud", "precursor", "dehydratase",
                            "epsp", " ligase", "nikj", "lanti", "lanthipeptide", "lasso",
                            "microcin", "thiopeptide", "bacteriocin", "ripp")):
        return "core"
    if any(k in s for k in ("oxygenase", "oxidoreductase", "methyltransferase", "reductase",
                            "hydroxylase", "halogenase", "glycosyltransferase", "aminotransferase",
                            "dehydrogenase", " sdr", "p450", "cytochrome", "phosphatase",
                            "kinase", "acetyltransferase", "decarboxylase", "monooxygenase",
                            "epimerase", "hydrolase", "nucleotidyltransf")):
        return "tailoring"
    return "other"

def short_label(defn, domains, lt):
    d = (defn or "").strip()
    d = re.sub(r"^MULTISPECIES:\s*", "", d)
    d = re.sub(r"\s*\[[^\]]*\]\s*$", "", d)          # strip trailing [organism]
    d = d.replace("domain-containing protein", "").strip(" ,")
    if not d or d.lower().startswith("hypothetical") or d.upper() == "NO_HIT":
        if domains:
            return domains.split(";")[0].split(",")[0].strip() or lt
        return lt
    return " ".join(d.split()[:4])

def load_blastp(path):
    if not path or not os.path.exists(path):
        return {}
    out = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            lt = (r.get("locus_tag") or "").strip()
            if not lt:
                continue
            pid = r.get("pct_identity") or r.get("pct_similarity") or ""
            try:
                pid = float(pid)
            except ValueError:
                pid = None
            out[lt] = {"defn": r.get("blastp_top_def", ""), "domains": r.get("antismash_domains", ""),
                       "pid": pid, "aa": r.get("aa_length", ""), "evalue": r.get("evalue", "")}
    return out

def parse_gbk(path):
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    genes = []
    for rec in SeqIO.parse(path, "genbank"):
        length = len(rec.seq)
        for f in rec.features:
            if f.type == "CDS":
                lt = f.qualifiers.get("locus_tag", ["?"])[0]
                genes.append({"lt": lt, "start": int(f.location.start), "end": int(f.location.end),
                              "strand": f.location.strand or 1,
                              "domains": ";".join(f.qualifiers.get("sec_met_domain", []))})
        return genes, length          # first record = the region
    return genes, 0

def fig_locus(genes, blastp, title, png, data_csv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mp
    from dna_features_viewer import GraphicFeature, GraphicRecord
    length = max(g["end"] for g in genes)
    feats, rows = [], []
    for g in genes:
        bp = blastp.get(g["lt"], {})
        lbl = short_label(bp.get("defn"), bp.get("domains") or g["domains"], g["lt"])
        role = classify(bp.get("domains") or g["domains"], bp.get("defn"))
        feats.append(GraphicFeature(start=g["start"], end=g["end"], strand=g["strand"],
                                    label=lbl, color=ROLE_COLORS[role]))
        rows.append([g["lt"], g["start"], g["end"], g["strand"], bp.get("aa", ""), role, lbl,
                     (bp.get("domains") or g["domains"])])
    rec = GraphicRecord(sequence_length=length, features=feats)
    fig, ax = plt.subplots(1, figsize=(12, 3.2))
    rec.plot(ax=ax)
    ax.set_title(title, fontsize=11, weight="bold")
    present = [r for r in ROLE_COLORS if any(row[5] == r for row in rows)]
    ax.legend(handles=[mp.Patch(color=ROLE_COLORS[r], label=r) for r in present],
              loc="lower center", ncol=len(present), fontsize=8, frameon=False,
              bbox_to_anchor=(0.5, -0.35))
    plt.tight_layout(); _save_rgb(fig, png); plt.close()
    with open(data_csv, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        w.writerow(["locus_tag", "start", "end", "strand", "aa", "role", "function_label", "antismash_domains"])
        w.writerows(rows)

def _canon(loc):
    m = re.match(r"(NODE_\d+_length_\d+).*?\.(region\d+)", loc or "", re.I)
    return f"{m.group(1)}.{m.group(2)}" if m else loc

def _mibig_names(index_path):
    if not index_path or not os.path.exists(index_path):
        return {}
    import json
    try:
        with open(index_path, encoding="utf-8") as _fh:
            data = json.load(_fh)
        entries = data["entries"] if isinstance(data, dict) and "entries" in data else data
        return {e["accession"]: (e.get("compounds") or ["?"])[0] for e in entries}
    except Exception:
        return {}

def fig_novelty(db, strain, gbk_base, mibig_index, title, png, data_csv, topn=6):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = _mibig_names(mibig_index)
    c = sqlite3.connect(db)
    want = _canon(f"{strain}_{gbk_base}").split(f"{strain}_", 1)[-1] if strain else _canon(gbk_base)
    rid = None
    for _id, path in c.execute("select br.id, g.path from bgc_record br join gbk g on g.id=br.gbk_id where br.record_type='region'"):
        b = os.path.basename(path)
        if strain and not b.startswith(strain + "_"):
            continue
        if _canon(b).endswith(want):
            rid = _id; break
    if rid is None:
        emit(f"[bgc_figures] fig2 skipped: BGC not found in DB for {strain} {gbk_base}")
        return False
    nbrs = []
    for a, b, d in c.execute("select record_a_id, record_b_id, distance from distance where record_a_id=? or record_b_id=?", (rid, rid)):
        other = b if a == rid else a
        p = c.execute("select g.path from bgc_record br join gbk g on g.id=br.gbk_id where br.id=?", (other,)).fetchone()
        if not p:
            continue
        bb = os.path.basename(p[0])
        if bb.upper().startswith("BGC"):
            acc = bb.split(".")[0]; label = f"{names.get(acc, acc)} (MIBiG)"; kind = "MIBiG"
        else:
            label = f"{bb.split('_')[0]} (cohort)"; kind = "cohort"
        nbrs.append((d, label, kind, bb))
    c.close()
    nbrs.sort(key=lambda x: x[0])
    top = nbrs[:topn]
    fig, ax = plt.subplots(figsize=(9, 3.4))
    for y, (d, lab, kind, _b) in enumerate(top):
        col = ROLE_COLORS["core"] if kind == "cohort" else "#7f8c8d"
        ax.hlines(y, 0, d, color=col, lw=2, alpha=.7); ax.plot(d, y, "o", color=col, ms=9)
        ax.text(d + 0.006, y, f"{d:.3f}", va="center", fontsize=9)
    ax.set_yticks(range(len(top))); ax.set_yticklabels([t[1] for t in top], fontsize=9)
    ax.set_xlim(0, 1.0); ax.set_xlabel("BiG-SCAPE GCF distance  (0 identical .. 1 maximal)")
    ax.set_title(title, fontsize=11, weight="bold")
    plt.tight_layout(); _save_rgb(fig, png); plt.close()
    with open(data_csv, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh); w.writerow(["neighbour", "kind", "gcf_distance", "gbk"])
        for d, lab, kind, bb in nbrs:
            w.writerow([lab, kind, f"{d:.4f}", bb])
    return True

def fig_blastp(blastp, genes_order, title, png, data_csv):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    labels, ids, rows = [], [], []
    for lt in genes_order:
        bp = blastp.get(lt)
        if not bp:
            continue
        lbl = short_label(bp.get("defn"), bp.get("domains"), lt)
        pid = bp.get("pid") or 0
        labels.append(lbl); ids.append(pid)
        rows.append([lt, lbl, bp.get("pid") if bp.get("pid") is not None else "NO_HIT",
                     bp.get("defn", ""), bp.get("evalue", "")])
    if not labels:
        emit("[bgc_figures] fig3 skipped: no blastp panel rows"); return False
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.7), 3.8))
    ax.bar(range(len(labels)), ids, color=ROLE_COLORS["core"])
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("BLASTp % identity to nearest nr homolog"); ax.set_ylim(0, 100)
    ax.set_title(title, fontsize=10.5, weight="bold")
    plt.tight_layout(); _save_rgb(fig, png); plt.close()
    with open(data_csv, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh); w.writerow(["locus_tag", "function_label", "pct_identity", "blastp_top_def", "evalue"])
        w.writerows(rows)
    return True

def main():
    ap = argparse.ArgumentParser(description="Per-BGC figure set (locus map / GCF novelty / BLASTp) + data CSVs.")
    ap.add_argument("--gbk", required=True, help="region GBK for the BGC (gene coords)")
    ap.add_argument("--bgc", default="BGC", help="BGC label for titles/filenames")
    ap.add_argument("--strain", default="", help="strain id (for DB lookup + titles)")
    ap.add_argument("--blastp", help="blastp panel CSV (enables fig3 + function labels)")
    ap.add_argument("--db", help="anchored BiG-SCAPE DB (enables fig2)")
    ap.add_argument("--mibig-index", help="mibig_reference_index.bacterial.json (compound names in fig2)")
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    tag = f"{a.strain + '_' if a.strain else ''}{a.bgc}"
    genes, length = parse_gbk(a.gbk)
    if not genes:
        sys.exit("ERROR: no CDS parsed from GBK")
    blastp = load_blastp(a.blastp)
    node = re.sub(r"\.gbk$", "", os.path.basename(a.gbk))
    made = []
    p1 = os.path.join(a.outdir, f"{tag}_fig1_locus.png")
    fig_locus(genes, blastp, f"{tag}  ({node}, {length/1000:.1f} kb)", p1, p1.replace(".png", "_data.csv"))
    made.append(p1)
    if a.db:
        p2 = os.path.join(a.outdir, f"{tag}_fig2_gcf_novelty.png")
        if fig_novelty(a.db, a.strain, os.path.basename(a.gbk), a.mibig_index,
                       f"{tag}: nearest GCF neighbours", p2, p2.replace(".png", "_data.csv")):
            made.append(p2)
    if blastp:
        p3 = os.path.join(a.outdir, f"{tag}_fig3_blastp.png")
        if fig_blastp(blastp, [g["lt"] for g in genes], f"{tag}: per-gene BLASTp identity", p3, p3.replace(".png", "_data.csv")):
            made.append(p3)
    emit(f"[bgc_figures] {tag}: wrote {len(made)} figure(s) + data CSVs -> {a.outdir}")
    for m in made:
        emit(f"   {os.path.basename(m)}  |  {os.path.basename(m).replace('.png','_data.csv')}")

if __name__ == "__main__":
    main()
