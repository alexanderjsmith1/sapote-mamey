#!/usr/bin/env python3
r"""fetch_reference_cluster — reconstruct a cluster GenBank from the BiG-SCAPE DB or NCBI.

The comparative tools (clinker, cluster_gene_compare, extract_cluster) all consume GBKs, but
there was no first-class way to *get* a reference or cohort cluster as a GBK — the DB->CDS logic
was trapped inside bgc_reference_align (returning internal dicts, not files), so every
comparison against a MIBiG reference or a cohort member meant hand-reconstructing a GBK. This
exposes that as a shared step, and improves on the hand-rolled version: the anchored BiG-SCAPE
DB stores Pfam domains (`hsp`) alongside every CDS (`cds.aa_seq`), so the reconstructed GBK comes
out **annotated** — gene names flow straight into clinker and cluster_gene_compare's label logic.

    fetch_reference_cluster.py \
        --db anchored.db \
        --acc BGC0000877:polyoxin \        # MIBiG or cohort cluster from the DB (repeatable)
        --ncbi MF055656.1:nikkomycin \      # NCBI nucleotide efetch (repeatable)
        --outdir refs/

Produces refs/<label>.gbk (annotated, ready to compare). Capacity/architecture-level: a
reconstructed reference is the characterised cluster's genes; comparison to it is homology.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, sqlite3, sys, urllib.parse, urllib.request
from pathlib import Path

# minimal Pfam accession -> short name map for common BGC domains (falls back to the accession)
PFAM = {
    "PF04055": "radical_SAM", "PF00155": "aminotransferase", "PF00583": "GNAT_acetyltransferase",
    "PF13302": "acetyltransferase", "PF00743": "FMO_monooxygenase", "PF00440": "TetR_regulator",
    "PF00561": "ab_hydrolase", "PF00106": "SDR", "PF13561": "SDR", "PF01408": "oxidoreductase",
    "PF00696": "aa_kinase", "PF02543": "carbamoyltransferase", "PF02786": "carbamoylP_synthase",
    "PF07690": "MFS_transporter", "PF00291": "PLP_enzyme", "PF00202": "aminotransferase_III",
    "PF00483": "nucleotidyltransferase", "PF13439": "glycosyltransferase", "PF00534": "glycosyltransferase",
    "PF00296": "luciferase_monooxygenase", "PF08240": "alcohol_dehydrogenase", "PF00107": "ADH",
    "PF01266": "FAD_oxidoreductase", "PF00990": "GGDEF", "PF00196": "LuxR_regulator",
    "PF03704": "BTAD_regulator", "PF00702": "HAD_hydrolase", "PF13508": "acetyltransferase",
    "PF00501": "AMP_binding", "PF00668": "condensation", "PF00109": "ketosynthase",
    "PF02801": "ketosynthase_C", "PF08659": "KR_domain", "PF00975": "thioesterase",
    "PF13193": "AMP_binding_C", "PF00550": "PP_binding", "PF00733": "asparagine_synthase",
    "PF13471": "lasso_B2_peptidase", "PF05147": "lanthionine_LanC", "PF04738": "lanthionine_LanB",
}


def _pfam_name(acc):
    return PFAM.get(acc, acc)


def ref_from_db(db_path, acc, label):
    """Reconstruct CDS (+ Pfam domains) for a cluster whose gbk.path matches `acc`."""
    c = sqlite3.connect(db_path)
    g = c.execute("SELECT id FROM gbk WHERE path LIKE ?", (f"%{acc}%",)).fetchone()
    if not g:
        c.close()
        raise KeyError(f"{acc} not found in DB gbk.path")
    gid = g[0]
    cds = c.execute(
        "SELECT id, nt_start, nt_stop, strand, aa_seq, orf_num FROM cds "
        "WHERE gbk_id=? ORDER BY nt_start", (gid,)).fetchall()
    genes = []
    for cid, s, e, st, aa, orf in cds:
        doms = c.execute(
            "SELECT accession, bit_score FROM hsp WHERE cds_id=? ORDER BY bit_score DESC",
            (cid,)).fetchall()
        label_gene = _pfam_name(doms[0][0]) if doms else None
        genes.append({"tag": f"{label}_{orf}", "start": int(s), "end": int(e),
                      "strand": 1 if st in (1, "+") else -1, "aa": aa or "",
                      "gene": label_gene, "domains": ",".join(d[0] for d in doms[:3])})
    c.close()
    return genes


def ref_from_ncbi(acc, label, timeout=60):
    """efetch a GenBank nucleotide record and return its CDS features (already annotated)."""
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    import io
    url = ("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" +
           urllib.parse.urlencode({"db": "nucleotide", "id": acc, "rettype": "gb", "retmode": "text"}))
    for _ in range(3):
        try:
            txt = urllib.request.urlopen(url, timeout=timeout).read().decode()
            break
        except Exception:
            import time; time.sleep(3)
    else:
        raise RuntimeError(f"NCBI efetch failed for {acc}")
    genes = []
    for rec in SeqIO.parse(io.StringIO(txt), "genbank"):
        i = 0
        for f in rec.features:
            if f.type == "CDS" and "translation" in f.qualifiers:
                i += 1
                name = (f.qualifiers.get("gene", [None])[0]
                        or (f.qualifiers.get("product", [None])[0] or "")[:30] or None)
                genes.append({"tag": f"{label}_{i}", "start": int(f.location.start),
                              "end": int(f.location.end), "strand": f.location.strand or 1,
                              "aa": f.qualifiers["translation"][0], "gene": name, "domains": ""})
    return genes


def genes_to_gbk(genes, label, outdir):
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    if not genes:
        raise ValueError(f"no CDS reconstructed for {label}")
    span = max(g["end"] for g in genes)
    rec = SeqRecord(Seq("N" * (span + 10)), id=f"{label}", name=label[:16],
                    description=f"{label} reference cluster (reconstructed)")
    rec.annotations["molecule_type"] = "DNA"
    for g in genes:
        f = SeqFeature(FeatureLocation(max(0, g["start"]), g["end"], strand=g["strand"]), type="CDS")
        f.qualifiers["locus_tag"] = [g["tag"]]
        if g.get("gene"):
            f.qualifiers["gene"] = [g["gene"]]
        if g.get("domains"):
            f.qualifiers["sec_met_domain"] = [g["domains"]]
        f.qualifiers["translation"] = [g["aa"]]
        rec.features.append(f)
    p = Path(outdir) / f"{label}.gbk"
    SeqIO.write(rec, str(p), "genbank")
    return str(p), len(genes), sum(1 for g in genes if g.get("gene"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Reconstruct reference cluster GBKs from the BiG-SCAPE DB or NCBI.")
    ap.add_argument("--db", help="anchored BiG-SCAPE DB (for --acc)")
    ap.add_argument("--acc", action="append", default=[], metavar="ACCESSION:label",
                    help="cluster in the DB (MIBiG or cohort), repeatable")
    ap.add_argument("--ncbi", action="append", default=[], metavar="ACCESSION:label",
                    help="NCBI nucleotide accession, repeatable")
    ap.add_argument("--outdir", default="refs")
    a = ap.parse_args(argv)
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    made = []
    for spec in a.acc:
        acc, label = spec.split(":", 1)
        if not a.db:
            emit("[fetch_reference_cluster] --acc needs --db", file=sys.stderr); return 2
        genes = ref_from_db(a.db, acc, label)
        p, n, na = genes_to_gbk(genes, label, a.outdir)
        made.append((label, p, n, na, "DB"))
    for spec in a.ncbi:
        acc, label = spec.split(":", 1)
        genes = ref_from_ncbi(acc, label)
        p, n, na = genes_to_gbk(genes, label, a.outdir)
        made.append((label, p, n, na, "NCBI"))
    for label, p, n, na, src in made:
        emit(f"[fetch_reference_cluster] {label} <- {src}: {n} CDS, {na} annotated -> {p}")
    emit(f"[fetch_reference_cluster] {len(made)} reference GBK(s) ready for "
          f"cluster_gene_compare / clinker / bgc_reference_align.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
