#!/usr/bin/env python3
"""clade_decontam.py — per-contig GC/coverage + blastn-vs-two-refs binning (Sapote-Mamey tool).

Track N1b (decontamination) of the genus/clade deep-dive apparatus. A first-pass decontamination
for an inflated / mixed assembly: assign every contig to the target genus, a suspected contaminant,
or an unknown low-signal bin using three independent signals, then write a cleaned FASTA of the
target-genus bin.

Method (faithful to _NOCARDIA_CLADE/decontam/REPORT.md):
  1. Per contig: GC%%, and coverage parsed from the SPAdes header (NODE_*_length_*_cov_<x>).
  2. blastn (megablast) each contig set vs a CLEAN same-genus reference and a CLEAN suspected-
     contaminant reference; summed bitscore per contig per reference.
  3. Assign by summed bitscore with a >=2x margin and a >=200-bit floor; corroborate with GC/coverage.
     Contigs whose GC is incompatible with the target (e.g. 35%% vs a 68%% target) and that match
     neither reference are binned as an unknown ("low-GC other") organism — flagged, not named.
  4. KEEP = target + GC-compatible-unassigned; write the cleaned target-genus FASTA.

Post-seal / reader-side. Contig assignments are EVIDENCE-BASED BINS, not certainties. Nucleotide
identity is SIMILARITY only; no taxonomic name is asserted beyond "matches the target/contaminant
reference". A bin matching NEITHER reference has UNKNOWN identity — flagged, never named. This is a
first-pass method (production decontam would add CheckM2/GUNC + tetranucleotide binning). Judgment
deferred.

Usage:
    clade_decontam.py --assembly FASTA --ref-target FASTA --ref-contaminant FASTA --out OUTDIR
                      [--target-gc 68] [--gc-tol 8] [--margin 2.0] [--min-bit 200]
                      [--clade NAME] [--blastn /path/to/blastn]
stdlib + subprocess only.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import os
import re
import subprocess
import sys
import tempfile

BLASTN_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/miniconda3/envs/blast/bin/blastn"
MAKEBLASTDB_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/miniconda3/envs/blast/bin/makeblastdb"

CLAIM_SAFETY = (
    "Contig assignments are evidence-based BINS, not certainties; nucleotide identity is similarity "
    "only; a bin matching neither reference has UNKNOWN identity (flagged, not named). First-pass "
    "method, not a production decontam pipeline. Judgment deferred."
)

_COV_RE = re.compile(r"(?:_cov[_=]|cov[_=])([0-9]*\.?[0-9]+)", re.I)


# ---- pure helpers (unit-tested) ----------------------------------------------------------------

def gc_percent(seq):
    seq = seq.upper()
    at_gc = sum(1 for c in seq if c in "ATGC")
    if not at_gc:
        return 0.0
    gc = sum(1 for c in seq if c in "GC")
    return 100.0 * gc / at_gc


def cov_from_header(header):
    """Parse SPAdes-style coverage from a contig header (NODE_1_length_290000_cov_7.9). None if absent."""
    m = _COV_RE.search(header)
    return float(m.group(1)) if m else None


def assign_contig(gc, cov, target_bit, contam_bit, *, target_gc=68.0, gc_tol=8.0,
                  margin=2.0, min_bit=200.0):
    """Assign one contig to a bin from its GC%, coverage (may be None), and summed blastn bitscore
    vs the target and contaminant references. Returns one of:
      'target'                — reference-supported target genus (KEEP)
      'contaminant'           — reference-supported contaminant   (REMOVE)
      'unassigned_target_like'— matches neither ref but GC ~ target (KEEP, GC-only)
      'other_lowGC'           — matches neither ref and GC incompatible with target (REMOVE, unknown)
    Coverage is corroborative only; GC + reference bitscore drive the call (per the report:
    coverage alone cannot split contaminants that overlap in depth)."""
    target_bit = target_bit or 0.0
    contam_bit = contam_bit or 0.0
    strong_t = target_bit >= min_bit and target_bit >= margin * max(contam_bit, 1e-9)
    strong_c = contam_bit >= min_bit and contam_bit >= margin * max(target_bit, 1e-9)
    if strong_t and not strong_c:
        return "target"
    if strong_c and not strong_t:
        return "contaminant"
    # neither reference is decisive -> fall back to GC compatibility with the target
    if abs(gc - target_gc) <= gc_tol:
        return "unassigned_target_like"
    return "other_lowGC"


KEEP_BINS = ("target", "unassigned_target_like")


def bin_contigs(contigs, target_bits, contam_bits, *, target_gc=68.0, gc_tol=8.0,
                margin=2.0, min_bit=200.0):
    """contigs = [(header, seq)]; target_bits/contam_bits = dict contig_id -> summed bitscore.
    contig_id = first whitespace token of the header. Returns list of per-contig row dicts."""
    rows = []
    for header, seq in contigs:
        cid = header.split()[0].lstrip(">")
        gc = gc_percent(seq)
        cov = cov_from_header(header)
        tb = target_bits.get(cid, 0.0)
        cb = contam_bits.get(cid, 0.0)
        assign = assign_contig(gc, cov, tb, cb, target_gc=target_gc, gc_tol=gc_tol,
                               margin=margin, min_bit=min_bit)
        rows.append({"contig": cid, "len": len(seq), "gc": gc, "cov": cov,
                     "target_bit": tb, "contam_bit": cb, "assignment": assign,
                     "keep": assign in KEEP_BINS, "seq": seq})
    return rows


# ---- FASTA + blastn I/O ------------------------------------------------------------------------

def read_fasta(path):
    hdr, seq, out = None, [], []
    with open(path, errors="replace") as fh:
        for line in fh:
            if line.startswith(">"):
                if hdr is not None:
                    out.append((hdr, "".join(seq)))
                hdr = line[1:].rstrip("\n")
                seq = []
            else:
                seq.append(line.strip())
    if hdr is not None:
        out.append((hdr, "".join(seq)))
    return out


def summed_bitscores_vs_ref(assembly_fa, ref_fa, blastn, makeblastdb, tmp):
    """blastn every contig vs a db built from ref_fa; return dict contig_id -> summed bitscore."""
    # A SPACE IN THIS PATH DEFEATS BLAST. `dbp` embedded the user-supplied --ref-target /
    # --ref-contaminant filename; a reference named "AS78 assembly.fasta" made makeblastdb exit 1
    # writing nothing and blastn exit 3 with empty stdout. Before `check=True` (the .415 draft) that
    # parsed as "no hits" and every contig was KEPT on the GC rule alone — a decontamination tool
    # certifying an assembly clean without doing the comparison. With `check=True` the same input now
    # crashes the run instead, which is honest but still a failure the tool causes itself. The db stem
    # is a fixed token inside the temp dir, so the user's filename never reaches a BLAST argument.
    # Reproduced 2026-09-08 with this project's own binaries (BLAST+ 2.16.0).
    dbp = os.path.join(tmp, "ref.db")
    _mk = subprocess.run([makeblastdb, "-in", ref_fa, "-dbtype", "nucl", "-out", dbp],
                         capture_output=True, text=True)
    if _mk.returncode != 0:
        # FAIL CLOSED with the tool's own words, not a bare CalledProcessError: the operator needs
        # makeblastdb's stderr to know whether the reference file, the path or the binary is at fault.
        raise RuntimeError(f"makeblastdb failed (rc={_mk.returncode}) for {ref_fa!r}: "
                           f"{(_mk.stderr or _mk.stdout).strip()[:300]}")
    proc = subprocess.run([blastn, "-query", assembly_fa, "-db", dbp, "-task", "megablast",
                           "-outfmt", "6 qseqid sseqid pident length bitscore", "-evalue", "1e-10",
                           "-max_target_seqs", "5"], capture_output=True, text=True, check=True)
    return parse_summed_bitscores(proc.stdout)


def parse_summed_bitscores(text):
    """Parse blastn -outfmt '6 qseqid sseqid pident length bitscore' -> summed bitscore per qseqid."""
    sums = {}
    for line in text.splitlines():
        f = line.split("\t")
        if len(f) < 5:
            continue
        try:
            bit = float(f[4])
        except ValueError:
            continue
        sums[f[0]] = sums.get(f[0], 0.0) + bit
    return sums


def write_outputs(rows, out_dir, clade="clade"):
    os.makedirs(out_dir, exist_ok=True)
    tsv = os.path.join(out_dir, f"{clade}_contig_bins.tsv")
    with open(tsv, "w") as fh:
        fh.write("contig\tlen\tgc_pct\tcov\ttarget_bit\tcontam_bit\tassignment\tkeep\n")
        for r in rows:
            cov = "" if r["cov"] is None else f"{r['cov']:.2f}"
            fh.write(f"{r['contig']}\t{r['len']}\t{r['gc']:.1f}\t{cov}\t{r['target_bit']:.0f}\t"
                     f"{r['contam_bit']:.0f}\t{r['assignment']}\t{int(r['keep'])}\n")
    clean = os.path.join(out_dir, f"{clade}_target_clean.fna")
    kept_bp = 0
    with open(clean, "w") as fh:
        for r in rows:
            if r["keep"]:
                fh.write(f">{r['contig']}\n{r['seq']}\n")
                kept_bp += r["len"]
    summary = {"n_contigs": len(rows), "n_keep": sum(1 for r in rows if r["keep"]),
               "kept_bp": kept_bp, "removed_bp": sum(r["len"] for r in rows if not r["keep"]),
               "bins_tsv": tsv, "clean_fasta": clean}
    return summary


def run(assembly, ref_target, ref_contaminant, out_dir, clade="clade", target_gc=68.0,
        gc_tol=8.0, margin=2.0, min_bit=200.0, blastn=BLASTN_DEFAULT,
        makeblastdb=MAKEBLASTDB_DEFAULT):
    """Full track: blastn vs both refs, bin every contig, write TSV + cleaned FASTA. Returns dict."""
    if not (os.path.exists(assembly) and os.path.exists(ref_target) and os.path.exists(ref_contaminant)):
        return {"status": "skipped", "note": "assembly / ref-target / ref-contaminant missing"}
    if not (os.path.exists(blastn) or _which(blastn)):
        return {"status": "skipped", "note": f"blastn not found at {blastn}"}
    contigs = read_fasta(assembly)
    tmp = tempfile.mkdtemp(prefix="clade_decontam_")
    target_bits = summed_bitscores_vs_ref(assembly, ref_target, blastn, makeblastdb, tmp)
    contam_bits = summed_bitscores_vs_ref(assembly, ref_contaminant, blastn, makeblastdb, tmp)
    rows = bin_contigs(contigs, target_bits, contam_bits, target_gc=target_gc, gc_tol=gc_tol,
                       margin=margin, min_bit=min_bit)
    summary = write_outputs(rows, out_dir, clade=clade)
    summary["status"] = "ok"
    return summary


def _which(name):
    from shutil import which
    return which(name)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Per-contig GC/cov + blastn-vs-two-refs decontamination")
    ap.add_argument("--assembly", required=True, help="assembly FASTA to clean")
    ap.add_argument("--ref-target", required=True, help="clean same-genus reference FASTA")
    ap.add_argument("--ref-contaminant", required=True, help="clean suspected-contaminant reference FASTA")
    ap.add_argument("--out", required=True)
    ap.add_argument("--clade", default="clade")
    ap.add_argument("--target-gc", type=float, default=68.0, help="expected target-genus GC%% (default 68)")
    ap.add_argument("--gc-tol", type=float, default=8.0, help="GC%% tolerance for GC-only keep (default 8)")
    ap.add_argument("--margin", type=float, default=2.0, help="bitscore margin for a call (default 2x)")
    ap.add_argument("--min-bit", type=float, default=200.0, help="min summed bitscore for a call")
    ap.add_argument("--blastn", default=BLASTN_DEFAULT)
    ap.add_argument("--makeblastdb", default=MAKEBLASTDB_DEFAULT)
    a = ap.parse_args(argv)
    res = run(a.assembly, a.ref_target, a.ref_contaminant, a.out, clade=a.clade,
              target_gc=a.target_gc, gc_tol=a.gc_tol, margin=a.margin, min_bit=a.min_bit,
              blastn=a.blastn, makeblastdb=a.makeblastdb)
    emit(res)
    emit("  " + CLAIM_SAFETY)
    return 0 if res.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
