#!/usr/bin/env python3
"""Extract a marker-co-occurrence candidate region from a supplied raw genome.

Pyrodigal coordinates are converted once from one-based inclusive to zero-based
half-open intervals. The marker threshold is a computational admission rule, not
proof of a complete biosynthetic cluster, compound or activity. Insufficient hits
mean this method did not admit a region, not biological absence. Fresh, contained
output paths are required and supplied input files remain unchanged.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, sys, math
from collections import defaultdict
from pathlib import Path
try:
    from mamey.path_safety import safe_label, contained_output_path
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from mamey.path_safety import safe_label, contained_output_path


def genecall(fna_path):
    """Return (contig, index, zero-based start, exclusive end, strand, protein).

    Pyrodigal uses one-based inclusive gene coordinates; conversion occurs here
    once. Every downstream interval uses the Python slice convention.
    """
    import pyrodigal
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    seqs = [(r.id, str(r.seq)) for r in SeqIO.parse(str(fna_path), "fasta")]
    if len({cid for cid, _ in seqs}) != len(seqs):
        raise ValueError("EXTRACT_IDENTITY_UNVERIFIED: duplicate FASTA record identifiers")
    orf = pyrodigal.GeneFinder(meta=False)
    train = [s for _, s in seqs if len(s) > 20000][:5]
    if train:
        orf.train(*train)
    else:
        orf = pyrodigal.GeneFinder(meta=True)   # tiny/fragmented -> metagenomic mode
    prots = []
    for cid, seq in seqs:
        for i, g in enumerate(orf.find_genes(seq)):
            start, end = int(g.begin) - 1, int(g.end)
            if not 0 <= start < end <= len(seq) or g.strand not in (-1, 1):
                raise ValueError("EXTRACT_COORDINATES_UNVERIFIED: gene outside its source contig")
            prots.append((cid, i + 1, start, end, g.strand, g.translate().rstrip("*")))
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
        if not math.isfinite(idn) or not 0 <= idn <= 100:
            raise ValueError("EXTRACT_ALIGNMENT_UNVERIFIED: identity is not a finite percentage")
        if type(h.target_index) is not int or type(h.query_index) is not int or not 0 <= h.target_index < len(prots) or not 0 <= h.query_index < len(markers):
            raise ValueError("EXTRACT_ALIGNMENT_UNVERIFIED: hit index outside supplied roster")
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
    safe_label(label)
    if type(flank) is not int or flank < 0:
        raise ValueError("flank must be a nonnegative integer")
    cid = cluster["contig"]
    lo_gene = cluster["gene_start"] - flank
    hi_gene = cluster["gene_end"] + flank
    region = [p for p in prots if p[0] == cid and lo_gene <= p[1] <= hi_gene]
    if not region:
        return None
    if any(not 0 <= p[2] < p[3] <= len(seqs[cid]) or p[4] not in (-1, 1) for p in region):
        raise ValueError("EXTRACT_COORDINATES_UNVERIFIED: invalid zero-based source interval")
    nt_lo = max(0, min(p[2] for p in region) - 500)
    nt_hi = min(len(seqs[cid]), max(p[3] for p in region) + 500)
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
        f = SeqFeature(FeatureLocation(s - nt_lo, e - nt_lo, strand=st), type="CDS")
        gidx = global_index[(cid_, gi)]
        lab = idx_label.get(gidx)
        f.qualifiers["locus_tag"] = [f"{label}_{gi}"]
        if lab:
            f.qualifiers["gene"] = [lab]
        f.qualifiers["translation"] = [aa]
        rec.features.append(f)
    return rec, (nt_lo, nt_hi)


def run(genome, markers, label, min_identity=40.0, window=25, min_markers=2, flank=2):
    safe_label(label)
    if not math.isfinite(min_identity) or not 0 <= min_identity <= 100:
        raise ValueError("identity must be a finite percentage")
    if any(type(x) is not int or x < 1 for x in (window, min_markers)) or type(flank) is not int or flank < 0:
        raise ValueError("window/marker count must be positive integers and flank nonnegative")
    if not markers or len({name for name, _ in markers}) != len(markers) or any(not name or not seq for name, seq in markers):
        raise ValueError("marker roster must contain unique nonempty names and sequences")
    prots, seqs = genecall(genome)
    cluster = find_cluster(prots, markers, min_identity=min_identity, window=window)
    present = bool(cluster and cluster["n_markers"] >= min_markers)
    result = {"label": label, "n_genes_called": len(prots), "present": present,
              "n_markers_required": min_markers,
              "coordinate_convention": "zero_based_half_open",
              "gene_call_source_convention": "pyrodigal_one_based_inclusive"}
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
        safe_label(a.label)
        op = Path(a.outdir)
        destinations = [contained_output_path(op, f"{a.label}_extract.json"),
                        contained_output_path(op, f"{a.label}_cluster.gbk")]
        for raw in [op / f"{a.label}_extract.json", op / f"{a.label}_cluster.gbk"]:
            if raw.exists() or raw.is_symlink():
                raise ValueError("output destination must be fresh (including symlinks)")
        if any(p.resolve() in {Path(a.genome).resolve(), Path(a.marker).resolve()} for p in destinations):
            raise ValueError("output destination aliases an input")
    except ValueError as exc:
        ap.error(str(exc))
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    markers = [(r.id, str(r.seq)) for r in SeqIO.parse(a.marker, "fasta")]
    result, rec = run(a.genome, markers, a.label, min_identity=a.min_identity,
                      window=a.window, min_markers=a.min_markers, flank=a.flank)
    import io
    payloads = {destinations[0]: (json.dumps(result, indent=2, allow_nan=False) + "\n").encode()}
    if rec is not None:
        buffer = io.StringIO()
        SeqIO.write(rec, buffer, "genbank")
        payloads[destinations[1]] = buffer.getvalue().encode()
    op.mkdir(parents=True, exist_ok=True)
    from mamey.output_transaction import publish_payloads
    publish_payloads(payloads)
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
