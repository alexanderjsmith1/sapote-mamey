#!/usr/bin/env python3
"""clade_ani.py — fastANI all-vs-all + sign-off species-boundary calls (Sapote-Mamey deliverable tool).

Track N1 of the genus/clade deep-dive apparatus. Given a directory of genome FASTAs (one per
strain / comparator), run fastANI all-vs-all, and emit:
  * <clade>_ani_matrix.tsv       — square all-vs-all ANI matrix (row=query, col=ref)
  * <clade>_nearest_named.tsv    — per query strain: nearest NAMED type genome + its ANI + boundary flag
  * <clade>_ani_pairs.tsv        — long-form pairwise ANI + boundary flag + mapped/total fragments

Post-seal / reader-side: does NOT touch the sealed package, scores, or tiers. fastANI reports
genome-wide NUCLEOTIDE identity over shared regions; this is a *relatedness* measure, NOT a formal
species designation. Sign-off boundary rule (master's-student gate):
  * ANI >= 96%  -> same_species        (confidently within-species)
  * 94-96%      -> BOUNDARY_indeterminate  (within ~1% of the 95% cutoff — DO NOT call)
  * ANI < 94%   -> candidate_distinct_species
NEVER quote core-SCG amino-acid identity (AAI) as if it were nucleotide ANI. Judgment deferred.

Usage:
    clade_ani.py --genomes DIR --out OUTDIR [--clade NAME]
                 [--fastani /path/to/fastANI] [--queries AS-XXX,AS-XXX,...]
stdlib + subprocess only.
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

FASTANI_DEFAULT = os.environ.get("SAPOTE_WORKSPACE_ROOT", os.getcwd()) + "/miniconda3/envs/phylo/bin/fastANI"
FASTA_EXTS = (".fna", ".fa", ".fasta", ".fna.gz")  # gz not passed to fastANI, but listed for glob

CLAIM_SAFETY = (
    "fastANI = genome-wide NUCLEOTIDE identity over shared regions; a relatedness measure, NOT a "
    "formal species call. ANI>=96% same species; 94-96% boundary/indeterminate; <94% candidate "
    "distinct species. Never quote AAI as ANI. Judgment deferred."
)

# ---- sign-off boundary rule --------------------------------------------------------------------

def boundary_flag(ani):
    """Sign-off species-boundary label for an ANI value (percent, 0-100), or None if no alignment."""
    if ani is None:
        return "no_alignment"
    if ani >= 96.0:
        return "same_species(>=96%)"
    if ani >= 94.0:
        return "BOUNDARY_indeterminate(94-96%)"
    return "candidate_distinct_species(<94%)"


# ---- strain-id vs named-type heuristic ---------------------------------------------------------

_QUERY_RE = re.compile(r"^(AS-?\d+|SID\d+|AJS-?\d+|PENDING-)", re.I)

def is_named_type(label, queries=None):
    """A genome is a NAMED type/comparator anchor unless it is one of our query strain ids
    (AS-####, SID####, ...). An explicit --queries list overrides the prefix heuristic."""
    if queries:
        return label not in queries
    return not _QUERY_RE.match(label)


def _label(path):
    b = os.path.basename(path)
    for ext in (".fna.gz", ".fasta", ".fna", ".fa"):
        if b.lower().endswith(ext):
            return b[: -len(ext)]
    return os.path.splitext(b)[0]


# ---- fastANI I/O -------------------------------------------------------------------------------

def parse_fastani(text_or_path):
    """Parse fastANI output (query<TAB>ref<TAB>ANI<TAB>mapped<TAB>total). Returns
    dict[(query_label, ref_label)] = {"ani": float, "mapped": int, "total": int}, keyed by
    file BASENAME label (extension stripped). Accepts a path or raw text."""
    if os.path.sep in str(text_or_path) or os.path.exists(str(text_or_path)):
        with open(text_or_path) as fh:
            text = fh.read()
    else:
        text = text_or_path
    out = {}
    for line in text.splitlines():
        line = line.rstrip("\n")
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        q, r = _label(parts[0]), _label(parts[1])
        try:
            ani = float(parts[2])
        except ValueError:
            continue
        mapped = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else None
        total = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else None
        out[(q, r)] = {"ani": ani, "mapped": mapped, "total": total}
    return out


def build_matrix(pairs, labels):
    """Square matrix rows[q][r] = ani (or None). Diagonal forced to 100.0."""
    mat = {q: {r: None for r in labels} for q in labels}
    for q in labels:
        mat[q][q] = 100.0
    for (q, r), d in pairs.items():
        if q in mat and r in mat[q]:
            mat[q][r] = d["ani"]
    return mat


def nearest_named(pairs, labels, queries=None):
    """For each QUERY label, nearest NAMED type genome by ANI. Returns list of dict rows."""
    named = [l for l in labels if is_named_type(l, queries)]
    rows = []
    for q in labels:
        if is_named_type(q, queries):
            continue  # only report for query strains
        best_ref, best_ani = None, None
        for r in named:
            d = pairs.get((q, r)) or pairs.get((r, q))
            if not d:
                continue
            if best_ani is None or d["ani"] > best_ani:
                best_ref, best_ani = r, d["ani"]
        rows.append({"strain": q, "nearest_named": best_ref, "ani": best_ani,
                     "flag": boundary_flag(best_ani)})
    return rows


def run_fastani(genomes_dir, out_dir, fastani_bin=FASTANI_DEFAULT):
    """Run fastANI all-vs-all over the genome FASTAs in genomes_dir. Returns the raw output path,
    or None if fastANI is missing / no genomes. Never raises for the expected failures."""
    genomes = sorted(
        p for p in glob.glob(os.path.join(genomes_dir, "*"))
        if p.lower().endswith((".fna", ".fa", ".fasta"))
    )
    if len(genomes) < 2:
        emit(f"clade_ani: need >=2 genome FASTAs in {genomes_dir}, found {len(genomes)}",
              file=sys.stderr)
        return None
    if not (os.path.exists(fastani_bin) or _which(fastani_bin)):
        emit(f"clade_ani: fastANI not found at {fastani_bin}", file=sys.stderr)
        return None
    os.makedirs(out_dir, exist_ok=True)
    lst = os.path.join(out_dir, "_genomes.txt")
    with open(lst, "w") as fh:
        fh.write("\n".join(genomes) + "\n")
    raw = os.path.join(out_dir, "fastani_allvall.tsv")
    cmd = [fastani_bin, "--ql", lst, "--rl", lst, "-o", raw]
    emit("  $ " + " ".join(cmd))
    proc = subprocess.run(cmd)
    if proc.returncode != 0 or not os.path.exists(raw):
        emit(f"clade_ani: fastANI exited {proc.returncode}", file=sys.stderr)
        return None
    return raw


def _which(name):
    from shutil import which
    return which(name)


def write_tables(pairs, out_dir, clade="clade", queries=None):
    """Write the three TSVs. Returns dict of paths."""
    os.makedirs(out_dir, exist_ok=True)
    labels = sorted({l for pr in pairs for l in pr})
    mat = build_matrix(pairs, labels)
    m_path = os.path.join(out_dir, f"{clade}_ani_matrix.tsv")
    with open(m_path, "w") as fh:
        fh.write("strain\t" + "\t".join(labels) + "\n")
        for q in labels:
            fh.write(q + "\t" + "\t".join(
                "" if mat[q][r] is None else f"{mat[q][r]:.2f}" for r in labels) + "\n")

    p_path = os.path.join(out_dir, f"{clade}_ani_pairs.tsv")
    with open(p_path, "w") as fh:
        fh.write("query\tref\tani\tflag\tmapped_frags\ttotal_frags\n")
        for (q, r), d in sorted(pairs.items()):
            if q == r:
                continue
            fh.write(f"{q}\t{r}\t{d['ani']:.2f}\t{boundary_flag(d['ani'])}\t"
                     f"{d.get('mapped','')}\t{d.get('total','')}\n")

    n_path = os.path.join(out_dir, f"{clade}_nearest_named.tsv")
    rows = nearest_named(pairs, labels, queries)
    with open(n_path, "w") as fh:
        fh.write("strain\tnearest_named\tani\tsignoff_flag\n")
        for row in rows:
            ani = "" if row["ani"] is None else f"{row['ani']:.2f}"
            fh.write(f"{row['strain']}\t{row['nearest_named'] or ''}\t{ani}\t{row['flag']}\n")
    return {"matrix": m_path, "pairs": p_path, "nearest": n_path,
            "n_boundary": sum(1 for r in rows if r["flag"].startswith("BOUNDARY"))}


def run(genomes_dir, out_dir, clade="clade", fastani_bin=FASTANI_DEFAULT, queries=None):
    """Full track: run fastANI, parse, write tables. Returns a result dict (status/paths/metrics)."""
    queries = [q.strip() for q in queries.split(",")] if isinstance(queries, str) else queries
    raw = run_fastani(genomes_dir, out_dir, fastani_bin=fastani_bin)
    if not raw:
        return {"status": "skipped", "note": "fastANI missing or <2 genome FASTAs"}
    pairs = parse_fastani(raw)
    res = write_tables(pairs, out_dir, clade=clade, queries=queries)
    res["status"] = "ok"
    res["n_pairs"] = len([1 for (q, r) in pairs if q != r])
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(description="fastANI all-vs-all + sign-off boundary calls")
    ap.add_argument("--genomes", required=True, help="dir of genome FASTAs (.fna/.fa/.fasta)")
    ap.add_argument("--out", required=True, help="output dir")
    ap.add_argument("--clade", default="clade", help="clade name (output filename prefix)")
    ap.add_argument("--fastani", default=FASTANI_DEFAULT, help="fastANI binary")
    ap.add_argument("--queries", default=None,
                    help="comma list of query strain ids (else AS-/SID prefix heuristic)")
    a = ap.parse_args(argv)
    res = run(a.genomes, a.out, clade=a.clade, fastani_bin=a.fastani, queries=a.queries)
    emit(res)
    emit("  " + CLAIM_SAFETY)
    return 0 if res.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
