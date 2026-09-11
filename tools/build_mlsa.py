#!/usr/bin/env python3
"""build_mlsa.py — 5-locus MLSA tree for a whole family's genome set, in one driver.

Tier-1 of the formal Sapote-Mamey two-tier phylogenomics workflow
(see docs/GTOTREE_WORKFLOW.md). MLSA is the right tool for LARGE-N families where a
138-SCG core-genome tree is impractical (Nocardiaceae ~293, Streptomycetaceae ~246,
Pseudonocardiaceae ~156 tips). The MLSA supermatrix is ~9 kb across 5 housekeeping
genes vs ~30k columns for the core-genome set, so IQ-TREE finishes in
minutes-to-an-hour even at hundreds of taxa.

MLSA IS CHEAP — run as many wide-net screens as you like, un-gated. It never needs the
compute-approval preflight; that gate is only for the EXPENSIVE core-genome step. The
output of a screen feeds prune_neighbors_from_tree.py, which emits a bounded (<=60-tip)
panel into build_phylo_panel.py -> plan_gtotree_iqtree.py -> USER APPROVAL ->
GToTree 138-SCG core-genome. Cores are committed only at that last, approved step.

This driver builds the 5 protein-coding loci (atpD/gyrB/recA/rpoB/trpB) via blastp
seeds -> best-ortholog CDS. The project's 6th MLSA locus, 16S rRNA, is NOT built here
(rRNA cannot be blastp-seeded) — it is extracted separately, per docs/phylogenomics.md.

Pipeline:
  1. Prodigal on each genome -> proteome (.faa) + CDS (.ffn)
  2. blastp 5 actinobacterial seed proteins vs each proteome -> best ortholog -> its CDS
  3. MUSCLE-align each locus, trim >50%-gap columns, concatenate -> partitioned supermatrix
  4. IQ-TREE, partitioned, ModelFinder, 1000 UFBoot + 1000 SH-aLRT
  5. (render + sign-off left to the caller; run tools/signoff_check.py on the treefile)

DESIGN — detected, not bundled. Like every external tool in the Sapote-Mamey
companion registry (mamey/data/companion_tools.json), the binaries here are
DISCOVERED at run time, never hardcoded and never required by the offline core:
  * prodigal, muscle, iqtree (iqtree3/iqtree2/iqtree), blastp, makeblastdb
  * resolved from --bin-dir, then $MAMEY_PHYLO_BIN, then PATH (shutil.which).
Seed proteins ship with the bundle at mamey/data/phylo_seeds/*.faa; override with
--seeds-dir. If a binary is missing the driver prints exactly what to install
(`mamey doctor --companions`) and exits non-zero — it does not touch a core run.

CLAIM SAFETY: MLSA strengthens topology; whole-genome ANI still delimits species.
Placements are class-level hypotheses with judgment deferred; "candidate novel" is a
prior, not a rank.

Usage:
  python tools/build_mlsa.py <genomes_dir> <out_dir> [--threads N]
      [--bin-dir DIR] [--seeds-dir DIR]
  (genomes_dir holds *.fna; one may carry an _OUTGROUP suffix in its filename)
"""
import os
import sys
import shutil
import subprocess
import glob
import json
import csv
# Use the bundle's spreadsheet-safe writers for all tabular exports.
try:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ModuleNotFoundError:
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter

from urllib.parse import quote
import math
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

# ---- locus set (5 housekeeping genes; nucleotide CDS concatenated) ------------
LOCI = ["atpD", "gyrB", "recA", "rpoB", "trpB"]

# Seeds ship with the bundle next to this tool: <tier>/mamey/data/phylo_seeds/.
# tools/ and mamey/ are siblings in the tier, so resolve relative to __file__.
_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEEDS_DIR = os.path.normpath(
    os.path.join(_HERE, os.pardir, "mamey", "data", "phylo_seeds"))

# Candidate binary names, in preference order. IQ-TREE 3 ships as `iqtree3`.
_BIN_ALIASES = {
    "prodigal":    ["prodigal"],
    "muscle":      ["muscle"],
    "iqtree":      ["iqtree3", "iqtree2", "iqtree"],
    "blastp":      ["blastp"],
    "makeblastdb": ["makeblastdb"],
}


def resolve_bin(tool, bin_dir=None):
    """Find a companion binary: --bin-dir, then $MAMEY_PHYLO_BIN, then PATH.

    Returns the absolute path or None. Never hardcodes a user-specific location —
    this keeps the driver portable across the run container and any laptop.
    """
    search_dirs = []
    if bin_dir:
        search_dirs.append(bin_dir)
    # MAMEY_PHYLO_BIN is this tool's historical name for the same directory the other
    # phylo drivers call PHYLO_BIN. Accept either so setting one does not silently miss.
    env = os.environ.get("MAMEY_PHYLO_BIN") or os.environ.get("PHYLO_BIN")
    if env:
        search_dirs.extend(env.split(os.pathsep))
    for name in _BIN_ALIASES.get(tool, [tool]):
        for d in search_dirs:
            cand = os.path.join(d, name)
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        found = shutil.which(name)
        if found:
            return found
    return None


def read_fasta(p):
    """Minimal FASTA reader -> {id: sequence}. id is the first whitespace token."""
    d, c = {}, None
    with open(p) as fh:
        for line in fh:
            if line.startswith(">"):
                c = line[1:].split()[0]
                d[c] = []
            elif c is not None:
                d[c].append(line.strip())
    return {k: "".join(v) for k, v in d.items()}


def trim_gappy_columns(aln, max_gap_frac=0.5):
    """Drop alignment columns that are >max_gap_frac gaps. Pure; unit-tested.

    aln: {taxon: aligned_seq (equal length)}. Returns {taxon: trimmed_seq}.
    """
    if not aln:
        return {}
    ncol = len(next(iter(aln.values())))
    ntax = len(aln)
    keep = [i for i in range(ncol)
            if sum(aln[t][i] == '-' for t in aln) / ntax <= max_gap_frac]
    return {t: "".join(aln[t][i] for i in keep) for t in aln}


def concat_partitions(trimmed, loci=LOCI):
    """Concatenate per-locus trimmed alignments into a partitioned supermatrix.

    A taxon missing a locus is padded with gaps for that partition's width, so the
    union of taxa across loci is kept. Pure; unit-tested.

    Returns (concat: {taxon: seq}, parts: [(locus, start_1based, end_1based)]).
    """
    present = [L for L in loci if L in trimmed and trimmed[L]]
    all_taxa = sorted(set().union(*[set(trimmed[L]) for L in present])) if present else []
    concat = {t: "" for t in all_taxa}
    parts, pos = [], 1
    for L in present:
        ln = len(next(iter(trimmed[L].values())))
        for t in all_taxa:
            concat[t] += trimmed[L].get(t, "-" * ln)
        parts.append((L, pos, pos + ln - 1))
        pos += ln
    return concat, parts


def write_partition_nexus(parts, path):
    with open(path, "w") as fh:
        fh.write("#nexus\nbegin sets;\n")
        for L, a, b in parts:
            fh.write(f"  charset {L} = {a}-{b};\n")
        fh.write("end;\n")


def _sh(cmd, log=None, **kw):
    """Stop at the first companion failure; preserve diagnostics in the run log."""
    return subprocess.run(cmd, stdout=log or subprocess.DEVNULL,
                          stderr=log or subprocess.DEVNULL, **kw, check=True)


def _checked_fasta(path):
    records, key = {}, None
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                words = line[1:].split()
                if not words or words[0] in records:
                    raise ValueError(f"OUTPUT_INVALID: missing or duplicate FASTA identifier {path}")
                key = words[0]
                records[key] = ""
            elif key is None:
                raise ValueError(f"OUTPUT_INVALID: sequence before FASTA header {path}")
            else:
                records[key] += line
    if not records or any(not seq for seq in records.values()):
        raise ValueError(f"OUTPUT_INVALID: empty FASTA {path}")
    return records


def _write_status(out, status, detail):
    path = os.path.join(out, "run_status.json")
    pending = path + ".tmp"
    with open(pending, "w") as fh:
        json.dump({"status": status, "detail": detail,
                   "scope": "mechanical MLSA build only; judgment deferred"}, fh, indent=2)
        fh.write("\n")
    os.replace(pending, path)



def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        sys.stderr.write(__doc__)
        return 2
    gdir, out = os.path.abspath(argv[0]), os.path.abspath(argv[1])
    threads = argv[argv.index("--threads") + 1] if "--threads" in argv else "4"
    bin_dir = argv[argv.index("--bin-dir") + 1] if "--bin-dir" in argv else None
    seeds_dir = (argv[argv.index("--seeds-dir") + 1]
                 if "--seeds-dir" in argv else DEFAULT_SEEDS_DIR)

    seeds_dir = os.path.abspath(seeds_dir)

    # Resolve companions up front; fail clearly (never silently) if one is absent.
    bins = {t: resolve_bin(t, bin_dir) for t in _BIN_ALIASES}
    missing = [t for t, p in bins.items() if p is None]
    if missing:
        sys.stderr.write(
            "build_mlsa: missing companion tool(s): " + ", ".join(missing) + "\n"
            "  These are DETECTED, not bundled. Install the phylogenomics env, e.g.:\n"
            "    conda create -n phylo -c conda-forge -c bioconda "
            "prodigal muscle iqtree blast -y\n"
            "  then re-run, or pass --bin-dir <dir> / set $MAMEY_PHYLO_BIN.\n"
            "  See `mamey doctor --companions` and docs/GTOTREE_WORKFLOW.md.\n")
        return 3
    bins = {t: os.path.abspath(p) for t, p in bins.items()}
    for L in LOCI:
        if not os.path.isfile(os.path.join(seeds_dir, L + ".faa")):
            sys.stderr.write(f"build_mlsa: seed {L}.faa not found in {seeds_dir}\n")
            return 3

    # An existing run is evidence, not a cache. Require a fresh output directory so
    # a successful tool cannot accidentally consume a previous partial product.
    if os.path.lexists(out) and (os.path.islink(out) or not os.path.isdir(out)
                                or os.listdir(out)):
        sys.stderr.write("build_mlsa: REFUSED output must be a new or empty directory\n")
        return 4
    genomes = sorted(glob.glob(os.path.join(gdir, "*.fna")))
    if not genomes:
        sys.stderr.write(f"build_mlsa: no *.fna genomes in {gdir}\n")
        return 4
    os.makedirs(out, exist_ok=True)
    for d in ("proteomes", "cds", "blastdb", "loci", "aln"):
        os.mkdir(os.path.join(out, d))
    with open(os.path.join(out, "mlsa.log"), "w") as log:
        def say(m):
            emit(m)
            log.write(m + "\n")
            log.flush()
        _write_status(out, "IN_PROGRESS", "Companion tools running")
        say(f"=== MLSA: {len(genomes)} genomes from {gdir} ===")
        try:
            _run_pipeline(genomes, out, seeds_dir, bins, threads, log, say)
        except (subprocess.CalledProcessError, OSError, ValueError) as exc:
            detail = f"BUILD_FAILED: {type(exc).__name__}: {exc}"
            if isinstance(exc, subprocess.CalledProcessError):
                detail = f"TOOL_FAILURE: {exc.cmd[0]} exit {exc.returncode}"
                if exc.stderr:
                    log.write(str(exc.stderr) + "\n")
            say(detail)
            _write_status(out, "FAILED", detail)
            return 6
        _write_status(out, "COMPLETE", "All invoked tools succeeded and outputs validated")
    return 0


def _taxon_tag(genome):
    # Reversible escaping keeps whitespace/Newick punctuation out of FASTA IDs.
    # A mapping sidecar retains the exact input filename; ordinary IDs are unchanged.
    return quote(os.path.splitext(os.path.basename(genome))[0], safe="._-")


def _run_pipeline(genomes, out, seeds_dir, bins, threads, log, say):
    with open(os.path.join(out, "taxon_map.tsv"), "w", newline="") as fh:
        writer = _SafeWriter(fh, delimiter="\t")
        writer.writerow(["taxon", "input_filename"])
        writer.writerows((_taxon_tag(g), os.path.basename(g)) for g in genomes)
    # 1. prodigal -> proteome + cds
    for i, g in enumerate(genomes, 1):
        tag = _taxon_tag(g)
        faa = os.path.join(out, "proteomes", tag + ".faa")
        ffn = os.path.join(out, "cds", tag + ".ffn")
        _sh([bins["prodigal"], "-i", g, "-a", faa, "-d", ffn, "-p", "single", "-q"], log=log)
        proteins = _checked_fasta(faa)
        cds = _checked_fasta(ffn)
        if set(proteins) != set(cds):
            raise ValueError("OUTPUT_INVALID: proteome/CDS identifiers disagree")
        if i % 25 == 0:
            say(f"  prodigal {i}/{len(genomes)}")
    say("prodigal done")

    # 2. blastp seeds -> best ortholog CDS
    loci_seqs = {L: {} for L in LOCI}
    report = []
    tags = [_taxon_tag(g) for g in genomes]
    dbdir = os.path.join(out, "blastdb")
    for L in LOCI:
        shutil.copyfile(os.path.join(seeds_dir, L + ".faa"),
                        os.path.join(dbdir, "seed_" + L + ".faa"))
    for i, tag in enumerate(tags, 1):
        faa = os.path.join(out, "proteomes", tag + ".faa")
        ffn = os.path.join(out, "cds", tag + ".ffn")
        ffn_seqs = _checked_fasta(ffn)
        # BLAST parses database names itself. Use safe relative names in an
        # explicit cwd; output directories and genome labels may contain spaces.
        dbp = f"db{i:06d}"
        staged = f"input{i:06d}.faa"
        shutil.copyfile(faa, os.path.join(dbdir, staged))
        _sh([bins["makeblastdb"], "-in", staged, "-dbtype", "prot", "-out", dbp],
            log=log, cwd=dbdir)
        for L in LOCI:
            proc = subprocess.run(
                [bins["blastp"], "-query", "seed_" + L + ".faa",
                 "-db", dbp, "-outfmt", "6 sseqid pident length evalue bitscore",
                 "-max_target_seqs", "1", "-num_threads", threads],
                capture_output=True, text=True, check=True, cwd=dbdir)
            if proc.stderr:
                log.write(proc.stderr + "\n")
            r = proc.stdout.strip()
            if not r:
                report.append((tag, L, "NA", "NA", "NO_HIT"))
                continue
            rows = [line.split("\t") for line in r.splitlines()]
            try:
                for row in rows:
                    if len(row) != 5 or not all(math.isfinite(float(x)) for x in row[1:]):
                        raise ValueError("invalid BLAST row")
                    if not 0 <= float(row[1]) <= 100 or float(row[2]) <= 0 or any(
                            float(x) < 0 for x in row[3:]):
                        raise ValueError("invalid BLAST metrics")
                best = max(rows, key=lambda row: float(row[4]))
            except ValueError as exc:
                raise ValueError("OUTPUT_INVALID: malformed BLAST result") from exc
            sid, pid = best[:2]
            if sid not in ffn_seqs:
                raise ValueError(f"OUTPUT_INVALID: BLAST subject {sid} missing from CDS")
            loci_seqs[L][tag] = ffn_seqs[sid]
            report.append((tag, L, pid, str(len(ffn_seqs[sid])), "HIT"))
        if i % 25 == 0:
            say(f"  blastp {i}/{len(tags)}")
    for L in LOCI:
        with open(os.path.join(out, "loci", L + ".fna"), "w") as fh:
            for tag in tags:
                if tag in loci_seqs[L]:
                    fh.write(f">{tag}\n{loci_seqs[L][tag]}\n")
        say(f"  loci/{L}.fna: {len(loci_seqs[L])}/{len(tags)} taxa")
    with open(os.path.join(out, "loci_report.tsv"), "w") as fh:
        fh.write("taxon\tlocus\tseed_pident\tcds_len\tstatus\n")
        for r in report:
            fh.write("\t".join(r) + "\n")

    # 3. align + trim + concat
    trimmed = {}
    for L in LOCI:
        inp = os.path.join(out, "loci", L + ".fna")
        alnf = os.path.join(out, "aln", L + ".aln.fna")
        if not loci_seqs[L]:
            say(f"  {L}: no hits in successful BLAST searches; alignment not attempted")
            continue
        _sh([bins["muscle"], "-align", inp, "-output", alnf], log=log)
        aln = _checked_fasta(alnf)
        if set(aln) != set(loci_seqs[L]) or len({len(seq) for seq in aln.values()}) != 1:
            raise ValueError("OUTPUT_INVALID: alignment taxa or widths disagree")
        trimmed[L] = trim_gappy_columns(aln, 0.5)
        if not all(trimmed[L].values()):
            raise ValueError("OUTPUT_INVALID: alignment has no retained columns")
        say(f"  {L}: {len(next(iter(aln.values())))} -> "
            f"{len(next(iter(trimmed[L].values())))} cols, {len(aln)} taxa")

    concat, parts = concat_partitions(trimmed)
    if not parts or not concat:
        raise ValueError("NO_USABLE_DATA: no partitions from successful searches")
    sm = os.path.join(out, "aln", "supermatrix.fasta")
    with open(sm, "w") as fh:
        for t in sorted(concat):
            fh.write(f">{t}\n{concat[t]}\n")
    partf = os.path.join(out, "aln", "partitions.nex")
    write_partition_nexus(parts, partf)
    total = parts[-1][2] if parts else 0
    say(f"supermatrix: {total} bp, {len(concat)} taxa, {len(parts)} partitions")

    # 4. IQ-TREE, partitioned. Nucleotide loci -> let ModelFinder pick DNA models
    #    (do NOT pass protein -mset LG/WAG/JTT here; that errors on nucleotide data).
    pre = os.path.join(out, "tree")
    say("IQ-TREE (partitioned, nucleotide MFP)...")
    _sh([bins["iqtree"], "-s", sm, "-p", partf, "-m", "MFP",
         "-B", "1000", "-alrt", "1000", "-seed", "12345", "-T", threads,
         "-redo", "-pre", pre], log=log)
    if not os.path.isfile(pre + ".treefile") or os.path.getsize(pre + ".treefile") == 0:
        raise ValueError("OUTPUT_INVALID: IQ-TREE produced no nonempty treefile")
    say(f"TREE_OK -> {pre}.treefile")
    say("  now run: python tools/signoff_check.py " + pre + ".treefile")


if __name__ == "__main__":
    sys.exit(main())
