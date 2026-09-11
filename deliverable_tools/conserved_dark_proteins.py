#!/usr/bin/env python3
"""Conserved reference-dark protein finder — Sapote-Mamey deliverable tool.

Given a set of related strain proteomes + a Pfam scan, find proteins that (a) carry NO Pfam domain
(reference-dark / hypothetical) yet (b) are CONSERVED across strains — candidate novel or
lineage-specific functions worth attention. Each reference-dark ortholog cluster is classified by
conservation scope: PAN_CLADE (all strains), SUBGROUP (a subset), or STRAIN_UNIQUE.

Post-hoc / reader-side: does NOT touch the sealed package, scores, or tiers. Everything here is
class-level CAPACITY only — "conserved dark" means *a conserved protein of unknown function*, never a
functional, structural, or bioactivity claim. Clustering is sequence-SIMILARITY (5-mer Jaccard,
substitution-tolerant), not an identity call. Judgment deferred.

Pipeline
--------
1. Read one `<strain>.faa` per strain (protein FASTA; header token = ORF id) and write a strain-tagged
   proteome (`strain|orf`) for reproducibility.
2. Pfam: either read a supplied `hmmsearch --tblout` (proteins listed there HAVE ≥1 Pfam), or run
   hmmsearch here against a Pfam-A HMM db (`--pfam-hmm`, needs hmmsearch on PATH).
3. Reference-dark = tagged proteins absent from the Pfam-hit set.
4. Collapse exact-duplicate sequences (handles fragmented/redundant assemblies), then single-linkage
   cluster the dark proteins by 5-mer Jaccard >= cutoff (length-banded ±20%).
5. Classify each cluster spanning >= min-strains distinct strains by conservation scope; emit tables +
   a representative FASTA (one per family) for downstream BLAST confirmation of true novelty.

Usage
-----
    conserved_dark_proteins.py --proteomes DIR --pfam-tbl HITS.tbl --out OUTDIR [--cutoff 0.55]
    conserved_dark_proteins.py --proteomes DIR --pfam-hmm Pfam-A.hmm --out OUTDIR   # runs hmmsearch

Outputs: conserved_dark_families.tsv, representatives.faa, conserved_dark_summary.md
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import collections
import glob
import os
import subprocess
import sys

CLAIM_SAFETY = (
    "Conserved reference-dark = a conserved protein of UNKNOWN function (no Pfam domain); class-level "
    "capacity only, NOT a functional/structural/bioactivity claim. Similarity clustering, not identity. "
    "Judgment deferred."
)


# ---- FASTA / Pfam parsing --------------------------------------------------------------------------

def read_faa(path):
    """Yield (header_token, sequence) from a protein FASTA."""
    hdr, seq = None, []
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.startswith(">"):
                if hdr is not None:
                    yield hdr, "".join(seq)
                hdr = line[1:].split()[0]
                seq = []
            else:
                seq.append(line.strip())
    if hdr is not None:
        yield hdr, "".join(seq)


def load_proteomes(proteome_dir):
    """dict (strain, orf) -> sequence, from every <strain>.faa in the dir."""
    prot = {}
    for f in sorted(glob.glob(os.path.join(proteome_dir, "*.faa"))):
        strain = os.path.splitext(os.path.basename(f))[0]
        for hdr, seq in read_faa(f):
            if seq:
                prot[(strain, hdr)] = seq
    return prot


def write_tagged(prot, out_faa):
    with open(out_faa, "w") as o:
        for (strain, orf), seq in prot.items():
            o.write(f">{strain}|{orf}\n{seq}\n")
    return out_faa


def pfam_hit_ids(tbl_path):
    """Set of tagged protein ids (`strain|orf`) that have >=1 Pfam hit, from hmmsearch --tblout."""
    hits = set()
    with open(tbl_path, errors="replace") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            hits.add(line.split()[0])   # target name = the sequence (hmmsearch: models vs seqs)
    return hits


def run_hmmsearch(hmm_db, tagged_faa, out_tbl, cpu=4):
    exe = _which("hmmsearch")
    if not exe:
        raise RuntimeError("hmmsearch not found on PATH; supply --pfam-tbl instead.")
    subprocess.run([exe, "--cpu", str(cpu), "--cut_ga", "--noali", "--tblout", out_tbl,
                    hmm_db, tagged_faa], check=True, stdout=subprocess.DEVNULL)
    return out_tbl


def _which(name):
    from shutil import which
    return which(name)


# ---- similarity clustering (shared logic with the clinker dark-gene ribbons) -----------------------

def _kmers(s, k=5):
    return {s[i:i + k] for i in range(len(s) - k + 1)} if len(s) >= k else {s}


def cluster_by_similarity(items, cutoff=0.55):
    """items: list of (key, sequence). Single-linkage cluster by 5-mer Jaccard >= cutoff, length-banded
    (±20%). Returns list of clusters, each a list of keys."""
    seqs = [s for _, s in items]
    ks = [_kmers(s) for s in seqs]
    ln = [len(s) for s in seqs]
    n = len(items)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    order = sorted(range(n), key=lambda i: ln[i])
    for a in range(n):
        i = order[a]
        for b in range(a + 1, n):
            j = order[b]
            if ln[j] - ln[i] > 0.20 * ln[j]:
                break
            inter = len(ks[i] & ks[j])
            if inter and inter / len(ks[i] | ks[j]) >= cutoff:
                parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i in range(n):
        groups[find(i)].append(items[i][0])
    return list(groups.values())


# ---- scope classification --------------------------------------------------------------------------

def scope_label(strains_in_cluster, all_strains):
    n = len(strains_in_cluster)
    if n >= len(all_strains):
        return "PAN_CLADE"
    if n == 1:
        return "STRAIN_UNIQUE"
    return "SUBGROUP"


# ---- driver ----------------------------------------------------------------------------------------

def _families_at(reps, by_seq, dark, all_strains, cutoff, min_strains):
    """Cluster the unique dark reps at one similarity cutoff → list of conserved-dark family dicts."""
    tag_strain = lambda t: t.split("|", 1)[0]
    rep_to_tags = {tags[0]: tags for tags in by_seq.values()}
    fam = []
    for cl in cluster_by_similarity(reps, cutoff=cutoff):
        tags = [t for rep in cl for t in rep_to_tags.get(rep, [rep])]
        strains = sorted({tag_strain(t) for t in tags})
        if len(strains) < min_strains:
            continue
        rep = max(cl, key=lambda t: len(dark[t]))
        fam.append(dict(rep=rep, seq=dark[rep], strains=strains, n_members=len(tags),
                        members=sorted(tags), scope=scope_label(strains, all_strains)))
    fam.sort(key=lambda f: (-len(f["strains"]), -f["n_members"]))
    return fam


def run(proteome_dir, out_dir, pfam_tbl=None, pfam_hmm=None, cutoffs=(0.40, 0.55, 0.70), min_strains=2):
    """Find conserved reference-dark proteins at 2-3 similarity thresholds (a sensitivity sweep).
    The MIDDLE cutoff is the headline; a threshold_sensitivity table shows how family counts move."""
    os.makedirs(out_dir, exist_ok=True)
    cutoffs = sorted(set(cutoffs))
    prot = load_proteomes(proteome_dir)
    all_strains = sorted({s for s, _ in prot})
    tagged = write_tagged(prot, os.path.join(out_dir, "all_proteomes.faa"))

    if pfam_tbl is None:
        if pfam_hmm is None:
            raise SystemExit("supply --pfam-tbl (precomputed) or --pfam-hmm (to run hmmsearch)")
        pfam_tbl = run_hmmsearch(pfam_hmm, tagged, os.path.join(out_dir, "pfam_hits.tbl"))
    hits = pfam_hit_ids(pfam_tbl)

    # reference-dark = no Pfam hit; collapse exact-duplicate sequences (redundant/fragmented ORFs)
    dark = {}
    for (strain, orf), seq in prot.items():
        tag = f"{strain}|{orf}"
        if tag not in hits:
            dark[tag] = seq
    by_seq = collections.defaultdict(list)
    for tag, seq in dark.items():
        by_seq[seq].append(tag)
    reps = [(tags[0], seq) for seq, tags in by_seq.items()]

    # sweep cutoffs
    per_cutoff = {}
    for c in cutoffs:
        fam = _families_at(reps, by_seq, dark, all_strains, c, min_strains)
        per_cutoff[c] = fam
        scopes = collections.Counter(f["scope"] for f in fam)
        with open(os.path.join(out_dir, f"conserved_dark_families_c{c:.2f}.tsv"), "w") as o:
            o.write("family\tscope\tn_strains\tstrains\tn_members\trep_len\trep_id\n")
            for i, f in enumerate(fam, 1):
                o.write(f"CD{i:04d}\t{f['scope']}\t{len(f['strains'])}\t{';'.join(f['strains'])}\t"
                        f"{f['n_members']}\t{len(f['seq'])}\t{f['rep']}\n")

    primary = cutoffs[len(cutoffs) // 2]   # middle stringency = headline
    pfam = per_cutoff[primary]
    with open(os.path.join(out_dir, "representatives.faa"), "w") as o:
        for i, f in enumerate(pfam, 1):
            o.write(f">CD{i:04d} c{primary} {f['scope']} strains={';'.join(f['strains'])}\n{f['seq']}\n")

    # member roster for the headline cutoff (family -> every member protein, not just the rep) — lets
    # downstream flagging (e.g. BGC-overlap) work at member level, not rep-only.
    with open(os.path.join(out_dir, "conserved_dark_members_c%.2f.tsv" % primary), "w") as o:
        o.write("family\tscope\tn_strains\tn_members\tmember_id\tis_rep\n")
        for i, f in enumerate(pfam, 1):
            for tag in f.get("members", [f["rep"]]):
                o.write(f"CD{i:04d}\t{f['scope']}\t{len(f['strains'])}\t{f['n_members']}\t"
                        f"{tag}\t{'1' if tag == f['rep'] else '0'}\n")

    with open(os.path.join(out_dir, "threshold_sensitivity.tsv"), "w") as o:
        o.write("cutoff\tn_conserved_dark_families\tn_pan_clade\tn_subgroup\tprimary\n")
        for c in cutoffs:
            sc = collections.Counter(f["scope"] for f in per_cutoff[c])
            o.write(f"{c:.2f}\t{len(per_cutoff[c])}\t{sc['PAN_CLADE']}\t{sc['SUBGROUP']}\t"
                    f"{'*' if c == primary else ''}\n")

    sc = collections.Counter(f["scope"] for f in pfam)
    with open(os.path.join(out_dir, "conserved_dark_summary.md"), "w") as o:
        o.write("# Conserved reference-dark proteins\n\n")
        o.write(f"- Proteomes: {len(all_strains)} strains ({', '.join(all_strains)}); {len(prot)} proteins\n")
        o.write(f"- Reference-dark (no Pfam): {len(dark)} ({len(reps)} unique sequences)\n")
        o.write(f"- Similarity thresholds swept: {', '.join(f'{c:.2f}' for c in cutoffs)} "
                f"(headline = {primary:.2f})\n\n")
        o.write("| 5-mer Jaccard cutoff | conserved-dark families | PAN_CLADE | SUBGROUP |\n")
        o.write("|---|---|---|---|\n")
        for c in cutoffs:
            s = collections.Counter(f["scope"] for f in per_cutoff[c])
            star = " (headline)" if c == primary else ""
            o.write(f"| {c:.2f}{star} | {len(per_cutoff[c])} | {s['PAN_CLADE']} | {s['SUBGROUP']} |\n")
        o.write(f"\nHeadline ({primary:.2f}): **{len(pfam)}** conserved-dark families — PAN_CLADE "
                f"{sc['PAN_CLADE']}, SUBGROUP {sc['SUBGROUP']}. BLAST `representatives.faa` to confirm "
                f"true novelty (vs Pfam-missed knowns).\n\n> {CLAIM_SAFETY}\n")
    emit(f"conserved-dark: headline c{primary} -> {len(pfam)} families "
          f"(PAN_CLADE {sc['PAN_CLADE']}, SUBGROUP {sc['SUBGROUP']}); swept {cutoffs} -> {out_dir}")
    return per_cutoff


def main(argv=None):
    ap = argparse.ArgumentParser(description="Find conserved reference-dark (no-Pfam) proteins across strains.")
    ap.add_argument("--proteomes", required=True, help="dir of <strain>.faa protein FASTAs")
    ap.add_argument("--pfam-tbl", help="hmmsearch --tblout of the proteomes vs Pfam-A")
    ap.add_argument("--pfam-hmm", help="Pfam-A HMM db (runs hmmsearch here if --pfam-tbl absent)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cutoffs", default="0.40,0.55,0.70",
                    help="comma-separated 5-mer Jaccard thresholds to sweep (middle = headline)")
    ap.add_argument("--min-strains", type=int, default=2)
    a = ap.parse_args(argv)
    cutoffs = tuple(float(x) for x in a.cutoffs.split(",") if x.strip())
    run(a.proteomes, a.out, pfam_tbl=a.pfam_tbl, pfam_hmm=a.pfam_hmm,
        cutoffs=cutoffs, min_strains=a.min_strains)


if __name__ == "__main__":
    main()
