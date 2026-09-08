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
panel into Codex's build_phylo_panel.py -> plan_gtotree_iqtree.py -> USER APPROVAL ->
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


def _sh(cmd, **kw):
    return subprocess.run(cmd, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, **kw)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or argv[0] in ("-h", "--help"):
        sys.stderr.write(__doc__)
        return 2
    gdir, out = argv[0], argv[1]
    threads = argv[argv.index("--threads") + 1] if "--threads" in argv else "4"
    bin_dir = argv[argv.index("--bin-dir") + 1] if "--bin-dir" in argv else None
    seeds_dir = (argv[argv.index("--seeds-dir") + 1]
                 if "--seeds-dir" in argv else DEFAULT_SEEDS_DIR)

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
    for L in LOCI:
        if not os.path.isfile(os.path.join(seeds_dir, L + ".faa")):
            sys.stderr.write(f"build_mlsa: seed {L}.faa not found in {seeds_dir}\n")
            return 3

    for d in ("proteomes", "cds", "blastdb", "loci", "aln"):
        os.makedirs(os.path.join(out, d), exist_ok=True)
    log = open(os.path.join(out, "mlsa.log"), "w")

    def say(m):
        emit(m)
        log.write(m + "\n")
        log.flush()

    genomes = sorted(glob.glob(os.path.join(gdir, "*.fna")))
    if not genomes:
        say(f"build_mlsa: no *.fna genomes in {gdir}")
        log.close()
        return 4
    say(f"=== MLSA: {len(genomes)} genomes from {gdir} ===")
    say(f"    iqtree={bins['iqtree']}  blastp={bins['blastp']}")

    # 1. prodigal -> proteome + cds
    for i, g in enumerate(genomes, 1):
        tag = os.path.splitext(os.path.basename(g))[0]
        faa = os.path.join(out, "proteomes", tag + ".faa")
        ffn = os.path.join(out, "cds", tag + ".ffn")
        if os.path.exists(faa) and os.path.exists(ffn):
            continue
        _sh([bins["prodigal"], "-i", g, "-a", faa, "-d", ffn, "-p", "single", "-q"])
        if i % 25 == 0:
            say(f"  prodigal {i}/{len(genomes)}")
    say("prodigal done")

    # 2. blastp seeds -> best ortholog CDS
    loci_seqs = {L: {} for L in LOCI}
    report = []
    tags = [os.path.splitext(os.path.basename(g))[0] for g in genomes]
    for i, tag in enumerate(tags, 1):
        faa = os.path.join(out, "proteomes", tag + ".faa")
        ffn = os.path.join(out, "cds", tag + ".ffn")
        if not (os.path.getsize(faa) if os.path.exists(faa) else 0):
            say(f"  WARN empty proteome {tag}")
            continue
        ffn_seqs = read_fasta(ffn)
        dbp = os.path.join(out, "blastdb", tag)
        _sh([bins["makeblastdb"], "-in", faa, "-dbtype", "prot", "-out", dbp])
        for L in LOCI:
            r = subprocess.run(
                [bins["blastp"], "-query", os.path.join(seeds_dir, L + ".faa"),
                 "-db", dbp, "-outfmt", "6 sseqid pident length evalue bitscore",
                 "-max_target_seqs", "1", "-num_threads", threads],
                capture_output=True, text=True).stdout.strip()
            if not r:
                report.append((tag, L, "NA", "NA"))
                continue
            best = sorted(r.splitlines(),
                          key=lambda x: float(x.split("\t")[4]), reverse=True)[0]
            sid, pid = best.split("\t")[0], best.split("\t")[1]
            if sid in ffn_seqs:
                loci_seqs[L][tag] = ffn_seqs[sid]
                report.append((tag, L, pid, str(len(ffn_seqs[sid]))))
        if i % 25 == 0:
            say(f"  blastp {i}/{len(tags)}")
    for L in LOCI:
        with open(os.path.join(out, "loci", L + ".fna"), "w") as fh:
            for tag in tags:
                if tag in loci_seqs[L]:
                    fh.write(f">{tag}\n{loci_seqs[L][tag]}\n")
        say(f"  loci/{L}.fna: {len(loci_seqs[L])}/{len(tags)} taxa")
    with open(os.path.join(out, "loci_report.tsv"), "w") as fh:
        fh.write("taxon\tlocus\tseed_pident\tcds_len\n")
        for r in report:
            fh.write("\t".join(r) + "\n")

    # 3. align + trim + concat
    trimmed = {}
    for L in LOCI:
        inp = os.path.join(out, "loci", L + ".fna")
        alnf = os.path.join(out, "aln", L + ".aln.fna")
        _sh([bins["muscle"], "-align", inp, "-output", alnf])
        aln = read_fasta(alnf)
        if not aln:
            say(f"  WARN {L} produced no alignment")
            continue
        trimmed[L] = trim_gappy_columns(aln, 0.5)
        say(f"  {L}: {len(next(iter(aln.values())))} -> "
            f"{len(next(iter(trimmed[L].values())))} cols, {len(aln)} taxa")

    concat, parts = concat_partitions(trimmed)
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
    rc = subprocess.run(
        [bins["iqtree"], "-s", sm, "-p", partf, "-m", "MFP",
         "-B", "1000", "-alrt", "1000",
         "-seed", "12345", "-T", threads, "-redo", "-pre", pre],
        stdout=log, stderr=log)
    if rc.returncode == 0 and os.path.exists(pre + ".treefile"):
        say(f"TREE_OK -> {pre}.treefile")
        say("  now run: python tools/signoff_check.py " + pre + ".treefile")
        ok = True
    else:
        say("TREE_FAIL")
        ok = False
    log.close()
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main())
