#!/usr/bin/env python3
"""
bigscape_combined_run.py — Sapote-Mamey BiG-SCAPE combined-run tool

Reconstruct cohort GBK files from a BiG-SCAPE 2 SQLite DB and run a
combined clustering with a new strain's region GBKs.

The problem: BiG-SCAPE 2 clusters within a single run. If you add a
new strain's GBKs to a DB that already has a cohort, the new strain
gets its own run with only intra-strain distances. Cross-strain GCF
assignments require ALL GBKs in one run.

The solution: extract nt_seq + CDS data from the DB, reconstruct
minimal GBK files, and run BiG-SCAPE cluster with:
  --input-dir <new strain's real antiSMASH GBKs>
  --reference-dir <reconstructed cohort GBKs>
  --force-gbk (bypass antiSMASH feature validation on reconstructed files)

Five things that break and their fixes:
  1. LOCUS line: organism names > 16 chars → truncated → BioPython ValueError.
     Fix: use the filename stem (max 16 chars) as the locus name.
  2. 0-based coordinates: DB stores CDS nt_start as 0-based; GenBank format
     is 1-based. BioPython rejects "0..N" as "negative starting position"
     and sets feature.location = None → NoneType.start AttributeError.
     Fix: max(1, nt_start) on every CDS coordinate.
  3. antiSMASH region features: BiG-SCAPE validates candidate_cluster_numbers,
     protoclusters, product qualifiers. Reconstructed GBKs don't have these.
     Fix: omit all antiSMASH features; use --force-gbk (creates synthetic
     region covering the full sequence with product="other").
  4. Mixed real + reconstructed: real antiSMASH GBKs parse fine; reconstructed
     ones need --force-gbk. If mixed in one dir, the real ones get parsed
     normally while --force-gbk handles the reconstructed ones.
     Fix: split into --input-dir (real) + --reference-dir (reconstructed).
  5. Pfam scan time: 98k CDS × 30k HMMs ≈ 30–60 min on 2 cores. Not
     avoidable when GBK hashes differ from originals (BiG-SCAPE deduplicates
     by SHA-256 of file content; reconstructed files hash differently).
     Fix: run on your machine, not in a session-limited environment.

Usage:
    python bigscape_combined_run.py \\
        --db cohort.db \\
        --strain-gbks bigscape_input_AS-XXX/ \\
        --pfam Pfam-A.hmm \\
        --outdir bigscape_combined_out \\
        [--cutoffs 0.3,0.5,0.7] \\
        [--cores 2] \\
        [--exclude-strain AS-XXX]

Requires: BiG-SCAPE 2 (pip install from GitHub), HMMER 3, BioPython.
"""

import argparse
import os
import sqlite3
import subprocess
import sys
import tempfile


def reconstruct_gbks(db_path: str, outdir: str, exclude_strain: str = "") -> int:
    """Reconstruct minimal GBK files from a BiG-SCAPE 2 SQLite DB.

    Returns the number of GBK files written.

    Each reconstructed file contains:
      - LOCUS line (filename-derived, max 16 chars)
      - source feature with /organism="."
      - CDS features with 1-based coordinates, /locus_tag, /gene_kind, /translation
      - ORIGIN with the nucleotide sequence

    No antiSMASH features (region, cand_cluster, protocluster) — the
    --force-gbk flag handles creating synthetic regions at runtime.
    """
    os.makedirs(outdir, exist_ok=True)

    db = sqlite3.connect(db_path)
    cur = db.cursor()

    # Build exclusion filter
    if exclude_strain:
        where = f"WHERE path NOT LIKE '%{exclude_strain}%'"
    else:
        where = ""

    cur.execute(f"SELECT id, path, nt_seq FROM gbk {where}")
    gbks = cur.fetchall()
    sys.stdout.write((f"[reconstruct] {len(gbks)} GBKs to reconstruct from {db_path}") + "\n")

    written = 0
    for i, (gbk_id, path, nt_seq) in enumerate(gbks):
        fname = os.path.basename(path)
        outpath = os.path.join(outdir, fname)

        cur.execute(
            "SELECT nt_start, nt_stop, strand, aa_seq, gene_kind, orf_num "
            "FROM cds WHERE gbk_id=? ORDER BY nt_start",
            (gbk_id,),
        )
        cdss = cur.fetchall()

        seqlen = len(nt_seq) if nt_seq else 0
        # Safe locus name: filename stem, max 16 chars, no spaces
        locus_name = fname.replace(".gbk", "").replace(".", "_")[:16]

        with open(outpath, "w") as f:
            f.write(
                f"LOCUS       {locus_name:<16s} {seqlen:>11d} bp"
                f"    DNA     linear   UNK 01-JAN-2026\n"
            )
            f.write(f"DEFINITION  {fname}\n")
            f.write(f"ACCESSION   .\n")
            f.write(f"VERSION     .\n")
            f.write("FEATURES             Location/Qualifiers\n")
            f.write(f"     source          1..{seqlen}\n")
            f.write(f'                     /organism="."\n')

            for nt_start, nt_stop, strand, aa_seq, gene_kind, orf_num in cdss:
                # Fix #2: 0-based → 1-based coordinates
                start = max(1, nt_start)
                stop = max(1, nt_stop)
                if strand == 1:
                    loc = f"{start}..{stop}"
                else:
                    loc = f"complement({start}..{stop})"
                f.write(f"     CDS             {loc}\n")
                f.write(f'                     /locus_tag="cds_{orf_num}"\n')
                if gene_kind:
                    f.write(f'                     /gene_kind="{gene_kind}"\n')
                if aa_seq:
                    f.write(f'                     /translation="{aa_seq}"\n')

            f.write("ORIGIN\n")
            if nt_seq:
                for j in range(0, len(nt_seq), 60):
                    chunk = nt_seq[j : j + 60]
                    parts = " ".join(
                        [chunk[k : k + 10] for k in range(0, len(chunk), 10)]
                    )
                    f.write(f"{j+1:>9d} {parts}\n")
            f.write("//\n")

        written += 1
        if (i + 1) % 500 == 0:
            sys.stdout.write((f"  {i + 1}/{len(gbks)} reconstructed...") + "\n")

    db.close()
    sys.stdout.write((f"[reconstruct] wrote {written} GBK files → {outdir}") + "\n")
    return written


def run_bigscape(
    input_dir: str,
    reference_dir: str,
    outdir: str,
    pfam_path: str,
    cutoffs: str = "0.3,0.5,0.7",
    cores: int = 2,
) -> int:
    """Run BiG-SCAPE 2 cluster with input + reference dirs.

    Fix #3 + #4: --force-gbk bypasses antiSMASH validation on reconstructed
    reference GBKs while real antiSMASH GBKs in input_dir parse normally.
    """
    cmd = [
        "bigscape",
        "cluster",
        "--input-dir",
        input_dir,
        "--reference-dir",
        reference_dir,
        "--output-dir",
        outdir,
        "--pfam-path",
        pfam_path,
        "--gcf-cutoffs",
        cutoffs,
        "--include-singletons",
        "--include-gbk",
        "*",
        "--force-gbk",
        "--cores",
        str(cores),
        "--no-trees",
    ]
    sys.stdout.write((f"[bigscape] running: {' '.join(cmd)}") + "\n")
    sys.stdout.write((f"[bigscape] Fix #5 note: Pfam scan on ~100k CDS may take 30–60 min.") + "\n")
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="Reconstruct cohort GBKs from a BiG-SCAPE DB and run "
        "a combined clustering with a new strain.",
        epilog="BiG-SCAPE combined-run tool. Five-fix GBK reconstruction.",
    )
    parser.add_argument(
        "--db", required=True, help="BiG-SCAPE 2 SQLite DB with the existing cohort"
    )
    parser.add_argument(
        "--strain-gbks",
        required=True,
        help="Dir containing the new strain's real antiSMASH region GBKs "
        "(from `tools/bigscape_prep.py` or antiSMASH output)",
    )
    parser.add_argument("--pfam", required=True, help="Path to Pfam-A.hmm (pressed)")
    parser.add_argument(
        "--outdir", required=True, help="Output dir for BiG-SCAPE results"
    )
    parser.add_argument(
        "--cutoffs", default="0.3,0.5,0.7", help="GCF distance cutoffs (default: 0.3,0.5,0.7)"
    )
    parser.add_argument(
        "--cores", type=int, default=2, help="CPU cores for BiG-SCAPE (default: 2)"
    )
    parser.add_argument(
        "--exclude-strain",
        default="",
        help="Strain prefix to exclude from DB reconstruction "
        "(e.g. 'AS-XXX' if it's already in the DB from a prior single-strain run)",
    )
    parser.add_argument(
        "--reconstruct-only",
        action="store_true",
        help="Only reconstruct GBKs, don't run BiG-SCAPE",
    )
    parser.add_argument(
        "--ref-dir",
        default="",
        help="Pre-existing dir of reconstructed cohort GBKs (skip reconstruction)",
    )
    args = parser.parse_args()

    # Step 1: Reconstruct cohort GBKs
    if args.ref_dir:
        ref_dir = args.ref_dir
        n = len([f for f in os.listdir(ref_dir) if f.endswith(".gbk")])
        sys.stdout.write((f"[skip reconstruct] using {n} GBKs from {ref_dir}") + "\n")
    else:
        ref_dir = os.path.join(args.outdir, "_reconstructed_cohort_gbks")
        n = reconstruct_gbks(args.db, ref_dir, exclude_strain=args.exclude_strain)

    if args.reconstruct_only:
        sys.stdout.write((f"[done] {n} GBKs reconstructed → {ref_dir}") + "\n")
        return 0

    # Step 2: Count input GBKs
    n_input = len(
        [f for f in os.listdir(args.strain_gbks) if f.endswith(".gbk")]
    )
    sys.stdout.write((f"[input] {n_input} new strain GBKs in {args.strain_gbks}") + "\n")
    sys.stdout.write((f"[ref]   {n} reconstructed cohort GBKs in {ref_dir}") + "\n")
    sys.stdout.write((f"[total] {n_input + n} GBKs for combined clustering") + "\n")

    # Step 3: Run BiG-SCAPE
    rc = run_bigscape(
        input_dir=args.strain_gbks,
        reference_dir=ref_dir,
        outdir=args.outdir,
        pfam_path=args.pfam,
        cutoffs=args.cutoffs,
        cores=args.cores,
    )

    if rc == 0:
        # Find the output DB
        out_db = os.path.join(args.outdir, os.path.basename(args.outdir) + ".db")
        if os.path.exists(out_db):
            sys.stdout.write((f"[done] combined DB → {out_db}") + "\n")
            # Quick stats
            db = sqlite3.connect(out_db)
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM gbk")
            sys.stdout.write((f"  total GBKs: {cur.fetchone()[0]}") + "\n")
            cur.execute("SELECT COUNT(*) FROM bgc_record")
            sys.stdout.write((f"  total BGC records: {cur.fetchone()[0]}") + "\n")
            cur.execute("SELECT COUNT(*) FROM distance")
            sys.stdout.write((f"  total distances: {cur.fetchone()[0]}") + "\n")
            cur.execute("SELECT COUNT(*) FROM family")
            sys.stdout.write((f"  total families: {cur.fetchone()[0]}") + "\n")
            db.close()
        sys.stdout.write((f"\n[next] Run Sapote-Mamey tools on the combined DB:") + "\n")
        sys.stdout.write((f"  python tools/bigscape_cross_strain.py --db {out_db} --out cross_strain_GCFs.tsv") + "\n")
        sys.stdout.write((f"  python tools/bigscape_known_novel.py --db {out_db} --out known_vs_novel.tsv") + "\n")
        sys.stdout.write((f"  python tools/bigscape_ingest_to_mamey.py --db {out_db} --package <pkg> --strain <ID>") + "\n")
    else:
        sys.stdout.write((f"[FAIL] BiG-SCAPE exited with code {rc}") + "\n")

    return rc


if __name__ == "__main__":
    sys.exit(main())
