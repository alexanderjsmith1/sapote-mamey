#!/usr/bin/env python3
"""extract_cluster — locate and extract a BGC from a RAW genome by its marker genes.

The whole Mamey pipeline starts from antiSMASH ZIPs; there is no way to bring a bare genome
(FASTA) in. This closes that gap and the loop:

    cluster_discovery  -> genome accessions
    extract_cluster    -> THIS: gene-call a genome, find the cluster by marker co-occurrence,
                          emit an annotated GBK (no antiSMASH run needed)
    cluster_gene_compare -> gene-by-gene comparison + deliverable

Given a genome FASTA and one or more diagnostic marker proteins (e.g. a cluster's radical-SAM
signature plus one or two co-conserved genes), it gene-calls with pyrodigal, finds the tightest
window where the markers co-localise, and writes that region (+ flank) as a GenBank file with the
marker genes labelled. It also reports present/absent by a co-occurrence threshold, so it doubles
as the confirmation step for cluster_discovery (a marker hit -> a confirmed carrier).

Capacity/architecture-level: co-occurrence of marker genes is strong evidence the cluster is
present; it is not proof the strain makes the same compound.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, sys
from collections import defaultdict
from pathlib import Path


def genecall(fna_path):
    """pyrodigal gene call -> list of (contig, idx, start, end, strand, aa)."""
    import pyrodigal
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    seqs = [(r.id, str(r.seq)) for r in SeqIO.parse(str(fna_path), "fasta")]
    orf = pyrodigal.GeneFinder(meta=False)
    train = [s for _, s in seqs if len(s) > 20000][:5]
    if train:
        orf.train(*train)
    else:
        orf = pyrodigal.GeneFinder(meta=True)   # tiny/fragmented -> metagenomic mode
    prots = []
    for cid, seq in seqs:
        for i, g in enumerate(orf.find_genes(seq)):
            prots.append((cid, i + 1, g.begin, g.end, g.strand, g.translate().rstrip("*")))
    return prots, dict(seqs)


def find_cluster(prots, markers, min_identity=40.0, window=25):
    """Search markers vs predicted proteins; return the tightest gene window with the most
    distinct markers. Returns dict or None."""
    import pyswrd
    def val(x): return x() if callable(x) else x
    mnames = [n for n, _ in markers]
    mseqs = [s for _, s in markers]
    tseqs = [p[5] for p in prots]
    try:
        hits = list(pyswrd.search(mseqs, tseqs, max_evalue=1e-8, max_alignments=5))
    except RuntimeError as exc:
        # v9.7.410 hostile audit: pyswrd delegates to pyopal, whose wheel may carry no usable SIMD
        # backend for this CPU/build (seen on an arm64 macOS venv). The bare "no supported SIMD
        # backend available" left the operator guessing which tool broke; name it and say what to do.
        if "SIMD" in str(exc):
            raise RuntimeError(
                "EXTRACT_CLUSTER_ALIGNER_UNAVAILABLE: pyswrd/pyopal cannot align on this machine "
                f"({exc}). Install a pyopal wheel built with SSE/AVX/NEON support for this platform, "
                "or run extract_cluster on a machine where `python -c 'import pyopal; "
                "pyopal.Aligner()'` succeeds.") from exc
        raise
    # per (contig) list of (gene_idx, marker_name, identity, prot_index)
    percontig = defaultdict(list)
    for h in hits:
        idn = val(h.result.identity) * 100
        if idn < min_identity:
            continue
        cid, gi, s, e, st, aa = prots[h.target_index]
        percontig[cid].append((gi, mnames[h.query_index], idn, h.target_index))
    best = None
    for cid, lst in percontig.items():
        lst = sorted(lst)
        for gi0, _, _, _ in lst:
            win = [x for x in lst if gi0 <= x[0] < gi0 + window]
            ndistinct = len(set(m for _, m, _, _ in win))
            if best is None or ndistinct > best["n_markers"]:
                best = {"contig": cid, "gene_start": gi0,
                        "gene_end": max(x[0] for x in win),
                        "n_markers": ndistinct,
                        "markers": sorted(set((m, round(max(i for _, mm, i, _ in win if mm == m), 1))
                                              for _, m, _, _ in win)),
                        "hits": win}
    return best


def extract_gbk(prots, seqs, cluster, label, flank=2, marker_labels=None):
    """Extract the cluster region (+ flank genes) as an annotated SeqRecord."""
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    cid = cluster["contig"]
    lo_gene = cluster["gene_start"] - flank
    hi_gene = cluster["gene_end"] + flank
    region = [p for p in prots if p[0] == cid and lo_gene <= p[1] <= hi_gene]
    if not region:
        return None
    nt_lo = max(0, min(p[2] for p in region) - 500)
    nt_hi = max(p[3] for p in region) + 500
    # map prot_index -> marker label
    idx_label = {}
    for gi, mname, idn, pidx in cluster["hits"]:
        idx_label[pidx] = mname
    prot_i = {id(p): i for i, p in enumerate(prots)}  # not used; keep by position
    rec = SeqRecord(Seq(seqs[cid][nt_lo:nt_hi]), id=f"{label}_cluster",
                    name=label[:16], description=f"{label} cluster extracted by marker co-occurrence")
    rec.annotations["molecule_type"] = "DNA"
    # need prot global index to attach marker label; rebuild by identity of tuple
    global_index = {}
    for i, p in enumerate(prots):
        global_index[(p[0], p[1])] = i
    for p in sorted(region, key=lambda x: x[2]):
        cid_, gi, s, e, st, aa = p
        f = SeqFeature(FeatureLocation(max(0, s - nt_lo), e - nt_lo, strand=st), type="CDS")
        gidx = global_index[(cid_, gi)]
        lab = idx_label.get(gidx)
        f.qualifiers["locus_tag"] = [f"{label}_{gi}"]
        if lab:
            f.qualifiers["gene"] = [lab]
        f.qualifiers["translation"] = [aa]
        rec.features.append(f)
    return rec, (nt_lo, nt_hi)


def run(genome, markers, label, min_identity=40.0, window=25, min_markers=2, flank=2):
    prots, seqs = genecall(genome)
    cluster = find_cluster(prots, markers, min_identity=min_identity, window=window)
    present = bool(cluster and cluster["n_markers"] >= min_markers)
    result = {"label": label, "n_genes_called": len(prots), "present": present,
              "n_markers_required": min_markers}
    rec = None
    if cluster:
        result.update({"contig": cluster["contig"], "n_markers_found": cluster["n_markers"],
                       "markers": cluster["markers"]})
        if present:
            out = extract_gbk(prots, seqs, cluster, label, flank=flank)
            if out:
                rec, (lo, hi) = out
                result["region_nt"] = [lo, hi]
                result["region_kb"] = round((hi - lo) / 1000, 1)
                result["n_cds_extracted"] = len(rec.features)
    return result, rec


def main(argv=None):
    ap = argparse.ArgumentParser(description="Locate + extract a BGC from a raw genome by marker genes.")
    ap.add_argument("--genome", required=True, help="genome FASTA (.fna)")
    ap.add_argument("--marker", required=True, help="marker protein FASTA (>=1 diagnostic genes)")
    ap.add_argument("--label", required=True, help="strain label for the output GBK / locus tags")
    ap.add_argument("--min-identity", type=float, default=40.0)
    ap.add_argument("--window", type=int, default=25, help="max genes spanned by the marker window")
    ap.add_argument("--min-markers", type=int, default=2, help="distinct markers to call the cluster present")
    ap.add_argument("--flank", type=int, default=2, help="genes of flank each side of the extracted region")
    ap.add_argument("--outdir", default="extract_cluster_out")
    a = ap.parse_args(argv)
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    markers = [(r.id, str(r.seq)) for r in SeqIO.parse(a.marker, "fasta")]
    result, rec = run(a.genome, markers, a.label, min_identity=a.min_identity,
                      window=a.window, min_markers=a.min_markers, flank=a.flank)
    op = Path(a.outdir); op.mkdir(parents=True, exist_ok=True)
    (op / f"{a.label}_extract.json").write_text(json.dumps(result, indent=2))
    if rec is not None:
        SeqIO.write(rec, str(op / f"{a.label}_cluster.gbk"), "genbank")
    status = "PRESENT" if result["present"] else "absent/insufficient"
    loc = f" @ {result.get('contig','')} {result.get('region_kb','?')}kb" if result["present"] else ""
    emit(f"[extract_cluster] {a.label}: cluster {status}{loc} "
          f"({result.get('n_markers_found', 0)} distinct markers; needed {a.min_markers})")
    if rec is not None:
        emit(f"[extract_cluster] wrote {a.label}_cluster.gbk ({result['n_cds_extracted']} CDS) "
              f"-> ready for cluster_gene_compare.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
