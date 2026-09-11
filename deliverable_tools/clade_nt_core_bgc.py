#!/usr/bin/env python3
"""clade_nt_core_bgc.py — nucleotide core-BGC clock (Sapote-Mamey deliverable tool).

Track N2 of the genus/clade deep-dive apparatus. Protein sequences are frequently byte-identical
between close isolates; this compares the NUCLEOTIDE sequences (including synonymous sites) of the
biosynthetic gene clusters strains share, to expose recent divergence protein identity hides.

Method (faithful to _NOCARDIA_CLADE/nt_core_bgc/REPORT.md):
  1. Per region GBK, core biosynthetic CDS = features with gene_kind in {biosynthetic,
     biosynthetic-additional} OR carrying a sec_met_domain, >=300 bp, in-frame (len % 3 == 0).
  2. Between a strain pair, blastn reciprocal-best-hit (RBH) orthologs (pident>=75, coverage>=0.7).
  3. Length-weighted nt identity = sum(nident) / sum(aln_len) over the RBH ortholog set.
  4. Equal-length gap-free ortholog pairs codon-compared (table 11) for synonymous / non-synonymous.
  Output: per-pair nt identity + SNP/kb + syn/nonsyn, and a groupwise identity matrix.

Post-seal / reader-side. Nucleotide identity is a RELATEDNESS/recency measure over the sampled
loci, NOT a species delimitation and NOT an ANI call. Pairwise cells rest on whichever core BGC
genes each pair shares (different, differently sized gene sets) — read as pairwise relatedness,
not a metric/tree-additive distance matrix. Every number carries its denominator. Judgment deferred.

Usage:
    clade_nt_core_bgc.py --gbk-dir DIR --out OUTDIR [--clade NAME] [--blastn /path/to/blastn]
Region GBKs are grouped into strains by filename prefix (token before the first '.' or '_region').
stdlib + subprocess; region parsing reuses the engine's _gbk_shim (or a local minimal fallback).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import glob
import os
import re
import subprocess
import sys
import tempfile

BLASTN_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/miniconda3/envs/blast/bin/blastn"
MAKEBLASTDB_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/miniconda3/envs/blast/bin/makeblastdb"
PIDENT_MIN = 75.0
COV_MIN = 0.7
MIN_CDS_BP = 300

CLAIM_SAFETY = (
    "Nucleotide core-BGC identity = a relatedness/recency measure over the sampled BGC loci only, "
    "NOT genome-wide ANI and NOT a taxonomic call. Cells rest on different, differently sized "
    "shared-gene sets (not tree-additive). Every number carries its denominator. Judgment deferred."
)

# ---- genetic code (NCBI table 11 sense codons == standard) -------------------------------------
_BASES = "TCAG"
_AAS = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG"
CODON_TABLE = {a + b + c: _AAS[i]
               for i, (a, b, c) in enumerate(
                   (x, y, z) for x in _BASES for y in _BASES for z in _BASES)}


def translate_codon(codon):
    return CODON_TABLE.get(codon.upper(), "X")


# ---- pure nucleotide metrics (unit-tested) -----------------------------------------------------

def nt_identity(a, b):
    """Ungapped identity over the overlap of two aligned same-frame sequences: (nident, aln, id%)."""
    n = min(len(a), len(b))
    ident = sum(1 for i in range(n) if a[i].upper() == b[i].upper())
    pid = 100.0 * ident / n if n else 0.0
    return ident, n, pid


def codon_syn_nonsyn(a, b):
    """Codon-level synonymous / non-synonymous SNP counts over two equal-frame gap-free CDS.
    A differing codon is synonymous if it encodes the same amino acid, else non-synonymous.
    Returns (n_diff_codons, syn, nonsyn)."""
    n = min(len(a), len(b))
    n -= n % 3
    syn = nonsyn = diff = 0
    for i in range(0, n, 3):
        ca, cb = a[i:i + 3].upper(), b[i:i + 3].upper()
        if ca == cb:
            continue
        diff += 1
        if translate_codon(ca) == translate_codon(cb):
            syn += 1
        else:
            nonsyn += 1
    return diff, syn, nonsyn


def weighted_identity(ortholog_pairs):
    """Length-weighted identity over a list of (nident, aln_len). Returns (id%, sum_nident, sum_aln)."""
    tot_id = sum(p[0] for p in ortholog_pairs)
    tot_aln = sum(p[1] for p in ortholog_pairs)
    return (100.0 * tot_id / tot_aln if tot_aln else 0.0), tot_id, tot_aln


# ---- blastn RBH (parsing + selection are pure; the subprocess is mocked in tests) --------------

BLAST_COLS = ["qseqid", "sseqid", "pident", "length", "qlen", "slen", "nident", "bitscore"]

def parse_blast_tab(text, min_pident=PIDENT_MIN, min_cov=COV_MIN):
    """Parse blastn -outfmt '6 <BLAST_COLS>' text -> list of hit dicts passing pident/coverage.
    Coverage = alignment length / min(qlen, slen)."""
    hits = []
    for line in text.splitlines():
        if not line.strip():
            continue
        f = line.split("\t")
        if len(f) < len(BLAST_COLS):
            continue
        try:
            pident = float(f[2]); length = int(f[3])
            qlen = int(f[4]); slen = int(f[5]); nident = int(f[6]); bit = float(f[7])
        except ValueError:
            continue
        cov = length / min(qlen, slen) if min(qlen, slen) else 0.0
        if pident < min_pident or cov < min_cov:
            continue
        hits.append({"q": f[0], "s": f[1], "pident": pident, "length": length,
                     "nident": nident, "bitscore": bit, "cov": cov})
    return hits


def best_hits(hits, key="q", other="s"):
    """Best (max bitscore) subject per query. Returns dict query -> subject."""
    best = {}
    for h in hits:
        k = h[key]
        if k not in best or h["bitscore"] > best[k]["bitscore"]:
            best[k] = {"partner": h[other], "bitscore": h["bitscore"]}
    return {k: v["partner"] for k, v in best.items()}


def reciprocal_best_hits(hits_ab, hits_ba):
    """Reciprocal best hits between two blastn directions. hits_ab = A(query) vs B(db);
    hits_ba = B(query) vs A(db). Returns list of (a_id, b_id) ortholog pairs."""
    fwd = best_hits(hits_ab)          # a -> b
    rev = best_hits(hits_ba)          # b -> a
    pairs = []
    for a, b in fwd.items():
        if rev.get(b) == a:
            pairs.append((a, b))
    return pairs


# ---- core-CDS extraction from region GBKs ------------------------------------------------------

def _load_gbk_reader():
    """Prefer Biopython, then the engine's _gbk_shim, else a tiny local fallback."""
    try:
        from Bio import SeqIO  # type: ignore
        return lambda path: [(r.id, str(r.seq), r.features) for r in SeqIO.parse(path, "genbank")]
    except Exception:
        pass
    try:
        from mamey._gbk_shim import parse_genbank_text  # type: ignore
    except Exception:
        parse_genbank_text = None
    if parse_genbank_text is not None:
        def _read(path):
            with open(path, errors="replace") as fh:
                recs = parse_genbank_text(fh.read())
            return [(r.id, r.seq, r.features) for r in recs]
        return _read
    return None  # caller must degrade gracefully


def _is_core_cds(feat):
    if getattr(feat, "type", "") != "CDS":
        return False
    q = feat.qualifiers
    kinds = " ".join(q.get("gene_kind", []))
    if any(k in kinds for k in ("biosynthetic", "biosynthetic-additional")):
        return True
    if q.get("sec_met_domain"):
        return True
    return False


def core_cds_from_gbk(path):
    """Return list of (cds_id, nt_seq) for core biosynthetic CDS in a region GBK.
    Returns [] (with a note on stderr) if no GBK reader is available."""
    reader = _load_gbk_reader()
    if reader is None:
        emit("clade_nt_core_bgc: no GBK reader (Bio / _gbk_shim) available", file=sys.stderr)
        return []
    out = []
    idx = 0
    for rec_id, seq, feats in reader(path):
        for feat in feats:
            if not _is_core_cds(feat):
                continue
            nt = feat.extract(seq) if hasattr(feat, "extract") else ""
            if len(nt) < MIN_CDS_BP or len(nt) % 3 != 0:
                continue
            idx += 1
            locus = (feat.qualifiers.get("locus_tag") or feat.qualifiers.get("gene") or
                     [f"{rec_id}_cds{idx}"])[0]
            out.append((locus, nt))
    return out


def strain_of(gbk_path):
    """Strain id from a region-GBK filename (token before '.region' / first '.' / '_region')."""
    b = os.path.basename(gbk_path)
    b = re.sub(r"\.region\d+\.gbk$", "", b, flags=re.I)
    b = re.sub(r"\.gbk$", "", b, flags=re.I)
    b = re.split(r"[._]region", b, flags=re.I)[0]
    return b.split(".")[0]


def group_gbks_by_strain(gbk_dir):
    d = {}
    for p in sorted(glob.glob(os.path.join(gbk_dir, "*.gbk"))):
        d.setdefault(strain_of(p), []).append(p)
    return d


def _write_fasta(seqs, path):
    with open(path, "w") as fh:
        for sid, nt in seqs:
            fh.write(f">{sid}\n{nt}\n")


def _blastn_dir(query_fa, db_fa, blastn, makeblastdb, tmp):
    """Run blastn query_fa vs a db built from db_fa. Returns parsed passing hits."""
    dbp = os.path.join(tmp, os.path.basename(db_fa) + ".db")
    subprocess.run([makeblastdb, "-in", db_fa, "-dbtype", "nucl", "-out", dbp],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    fmt = "6 " + " ".join(BLAST_COLS)
    proc = subprocess.run([blastn, "-query", query_fa, "-db", dbp, "-outfmt", fmt,
                           "-max_target_seqs", "5", "-evalue", "1e-5"],
                          capture_output=True, text=True, check=True)
    return parse_blast_tab(proc.stdout)


def pair_nt_identity(seqs_a, seqs_b, blastn=BLASTN_DEFAULT, makeblastdb=MAKEBLASTDB_DEFAULT):
    """RBH nt identity + syn/nonsyn between two strains' core-CDS sets. seqs_{a,b} = [(id,nt)].
    Returns dict with n_ortho, aln_bp, nt_id%, snp_per_kb, syn, nonsyn."""
    if not seqs_a or not seqs_b:
        return {"n_ortho": 0, "aln_bp": 0, "nt_id": 0.0, "snp_per_kb": 0.0, "syn": 0, "nonsyn": 0}
    by_a = dict(seqs_a); by_b = dict(seqs_b)
    tmp = tempfile.mkdtemp(prefix="clade_ntcore_")
    fa_a = os.path.join(tmp, "a.fna"); fa_b = os.path.join(tmp, "b.fna")
    _write_fasta(seqs_a, fa_a); _write_fasta(seqs_b, fa_b)
    hits_ab = _blastn_dir(fa_a, fa_b, blastn, makeblastdb, tmp)
    hits_ba = _blastn_dir(fa_b, fa_a, blastn, makeblastdb, tmp)
    rbh = reciprocal_best_hits(hits_ab, hits_ba)
    ortho_pairs, syn_t, nonsyn_t = [], 0, 0
    # nident/aln come from the A->B direction hit for each RBH pair
    ab_index = {(h["q"], h["s"]): h for h in hits_ab}
    for a_id, b_id in rbh:
        h = ab_index.get((a_id, b_id))
        if not h:
            continue
        ortho_pairs.append((h["nident"], h["length"]))
        sa, sb = by_a.get(a_id, ""), by_b.get(b_id, "")
        if sa and sb and len(sa) == len(sb):
            _, syn, nonsyn = codon_syn_nonsyn(sa, sb)
            syn_t += syn; nonsyn_t += nonsyn
    pid, tot_id, tot_aln = weighted_identity(ortho_pairs)
    snp_per_kb = 1000.0 * (tot_aln - tot_id) / tot_aln if tot_aln else 0.0
    return {"n_ortho": len(ortho_pairs), "aln_bp": tot_aln, "nt_id": pid,
            "snp_per_kb": snp_per_kb, "syn": syn_t, "nonsyn": nonsyn_t}


def run(gbk_dir, out_dir, clade="clade", blastn=BLASTN_DEFAULT, makeblastdb=MAKEBLASTDB_DEFAULT):
    """Full track: group GBKs by strain, extract core CDS, all-vs-all pairwise RBH nt identity,
    write groupwise matrix + long-form pairs. Returns a result dict."""
    groups = group_gbks_by_strain(gbk_dir)
    if len(groups) < 2:
        return {"status": "skipped", "note": f"need >=2 strains of region GBKs, found {len(groups)}"}
    core = {}
    for strain, paths in groups.items():
        seqs = []
        for p in paths:
            seqs.extend(core_cds_from_gbk(p))
        core[strain] = seqs
    if any(len(s) == 0 for s in core.values()) and all(len(s) == 0 for s in core.values()):
        return {"status": "skipped", "note": "no core CDS extracted (GBK reader missing?)"}
    os.makedirs(out_dir, exist_ok=True)
    strains = sorted(core)
    cells = {}
    long_path = os.path.join(out_dir, f"{clade}_nt_core_pairs.tsv")
    with open(long_path, "w") as fh:
        fh.write("strain_a\tstrain_b\tn_ortho\taln_bp\tnt_id_pct\tsnp_per_kb\tsyn\tnonsyn\n")
        for i, a in enumerate(strains):
            for b in strains[i + 1:]:
                r = pair_nt_identity(core[a], core[b], blastn=blastn, makeblastdb=makeblastdb)
                cells[(a, b)] = r["nt_id"]; cells[(b, a)] = r["nt_id"]
                fh.write(f"{a}\t{b}\t{r['n_ortho']}\t{r['aln_bp']}\t{r['nt_id']:.2f}\t"
                         f"{r['snp_per_kb']:.1f}\t{r['syn']}\t{r['nonsyn']}\n")
    mat_path = os.path.join(out_dir, f"{clade}_nt_core_matrix.tsv")
    with open(mat_path, "w") as fh:
        fh.write("strain\t" + "\t".join(strains) + "\n")
        for a in strains:
            row = ["100.00" if a == b else
                   (f"{cells[(a, b)]:.2f}" if (a, b) in cells else "") for b in strains]
            fh.write(a + "\t" + "\t".join(row) + "\n")
    return {"status": "ok", "n_strains": len(strains), "matrix": mat_path, "pairs": long_path,
            "core_cds_per_strain": {s: len(core[s]) for s in strains}}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Nucleotide core-BGC clock (RBH nt identity + syn/nonsyn)")
    ap.add_argument("--gbk-dir", required=True, help="dir of antiSMASH region GBKs (strain-prefixed)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--clade", default="clade")
    ap.add_argument("--blastn", default=BLASTN_DEFAULT)
    ap.add_argument("--makeblastdb", default=MAKEBLASTDB_DEFAULT)
    a = ap.parse_args(argv)
    res = run(a.gbk_dir, a.out, clade=a.clade, blastn=a.blastn, makeblastdb=a.makeblastdb)
    emit(res)
    emit("  " + CLAIM_SAFETY)
    return 0 if res.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
