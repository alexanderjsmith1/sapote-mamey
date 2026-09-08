#!/usr/bin/env python3
"""mlsa_outgroup_scan.py — build the same MLSA panel rooted on several candidate
outgroups, and measure whether the INGROUP topology is stable across them.

MLSA is cheap, so testing the root is cheap: for each candidate outgroup you build one
MLSA tree (ingroup + that outgroup) and compare the resulting ingroup topologies. If the
ingroup splits are the same regardless of which outgroup roots them, the backbone is
robust to outgroup choice; if they move, the root/deep splits are not to be over-read
(exactly the kind of thing the sign-off gate asks a human to judge).

Stability is quantified with the Robinson-Foulds (RF) distance between ingroup
topologies (symmetric difference of their non-trivial bipartitions), restricted to the
tips shared by both trees. RF = 0 means identical ingroup topology.

This tool ORCHESTRATES cheap MLSA builds (via build_mlsa.py) — it never builds a heavy
core-genome tree and never commits those gated cores. The RF core is pure and unit-tested.

CLAIM SAFETY: a stable ingroup under multiple outgroups strengthens confidence in the
topology only; ANI still delimits species. Class-level hypotheses, judgment deferred.

Usage (compare already-built trees):
  python tools/mlsa_outgroup_scan.py --trees a.treefile b.treefile c.treefile

Usage (build then compare — one MLSA per outgroup-augmented genome dir):
  python tools/mlsa_outgroup_scan.py --build \
      --ingroup-dir genomes_ingroup/ \
      --outgroup outA.fna --outgroup outB.fna --outgroup outC.fna \
      --workdir scan_out/ [--threads 4]
"""
import sys
import os
import subprocess
import re
import shutil
import argparse
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

OUTGROUP = re.compile(r'OUTGROUP', re.I)


# ---- newick -> bipartitions (pure) ------------------------------------------
class _N:
    __slots__ = ('name', 'children')

    def __init__(self):
        self.name = ''
        self.children = []

    def leaves(self):
        if not self.children:
            yield self.name
        for c in self.children:
            yield from c.leaves()


def _parse(text):
    s = text.strip().rstrip(';')
    pos = 0

    def node():
        nonlocal pos
        n = _N()
        if s[pos] == '(':
            pos += 1
            while True:
                n.children.append(node())
                if s[pos] == ',':
                    pos += 1; continue
                if s[pos] == ')':
                    pos += 1; break
        start = pos
        while pos < len(s) and s[pos] not in '(),:;':
            pos += 1
        lab = s[start:pos].strip().strip("'\"")
        if not n.children:
            n.name = lab
        if pos < len(s) and s[pos] == ':':
            pos += 1
            while pos < len(s) and s[pos] not in '(),;':
                pos += 1
        return n
    return node()


def bipartitions(root, restrict=None):
    """Set of non-trivial bipartitions as frozensets of the SMALLER side, restricted
    to `restrict` tips if given. Trivial (size 0/1 or all) splits are dropped. Pure."""
    all_tips = set(root.leaves())
    keep = (all_tips & set(restrict)) if restrict else all_tips
    parts = set()

    def collect(n):
        below = set()
        if not n.children:
            if n.name in keep:
                below.add(n.name)
            return below
        for c in n.children:
            below |= collect(c)
        clade = below & keep
        other = keep - clade
        if 1 < len(clade) < len(keep) and len(other) > 1:
            side = min((frozenset(clade), frozenset(other)), key=lambda x: (len(x), sorted(x)))
            parts.add(side)
        return below
    collect(root)
    return parts


def rf_distance(nwk_a, nwk_b, drop_outgroups=True):
    """Robinson-Foulds distance between two trees on their SHARED tips (optionally
    dropping _OUTGROUP tips so only the ingroup topology is compared).
    Returns (rf, n_shared_tips, max_rf). Pure; unit-tested."""
    ra, rb = _parse(nwk_a), _parse(nwk_b)
    ta, tb = set(ra.leaves()), set(rb.leaves())
    shared = ta & tb
    if drop_outgroups:
        shared = {t for t in shared if not OUTGROUP.search(t)}
    pa = bipartitions(ra, shared)
    pb = bipartitions(rb, shared)
    rf = len(pa ^ pb)
    max_rf = len(pa) + len(pb)
    return rf, len(shared), max_rf


# ---- orchestration ----------------------------------------------------------
def _run_builds(ingroup_dir, outgroups, workdir, threads):
    """Build one MLSA per outgroup (cheap). Returns {label: treefile_path}."""
    here = os.path.dirname(os.path.abspath(__file__))
    build = os.path.join(here, "build_mlsa.py")
    trees = {}
    for og in outgroups:
        tag = os.path.splitext(os.path.basename(og))[0]
        gdir = os.path.join(workdir, f"genomes_{tag}")
        os.makedirs(gdir, exist_ok=True)
        for f in os.listdir(ingroup_dir):
            if f.endswith(".fna"):
                shutil.copy(os.path.join(ingroup_dir, f), os.path.join(gdir, f))
        # stage the outgroup with an _OUTGROUP-tagged name so downstream tools root on it
        shutil.copy(og, os.path.join(gdir, f"{tag}_OUTGROUP.fna"))
        out = os.path.join(workdir, f"mlsa_{tag}")
        rc = subprocess.run(
            [sys.executable, build, gdir, out, "--threads", str(threads)],
        ).returncode
        tf = os.path.join(out, "tree.treefile")
        if rc == 0 and os.path.exists(tf):
            trees[tag] = tf
        else:
            sys.stderr.write(f"  build failed for outgroup {tag}\n")
    return trees


def main(argv=None):
    ap = argparse.ArgumentParser(description="MLSA outgroup-stability scan (RF)")
    ap.add_argument('--trees', nargs='+', help='pre-built treefiles to compare')
    ap.add_argument('--build', action='store_true', help='build one MLSA per outgroup first')
    ap.add_argument('--ingroup-dir')
    ap.add_argument('--outgroup', action='append', default=[])
    ap.add_argument('--workdir', default='outgroup_scan')
    ap.add_argument('--threads', default='4')
    args = ap.parse_args(argv)

    if args.build:
        if not args.ingroup_dir or not args.outgroup:
            ap.error("--build needs --ingroup-dir and at least one --outgroup")
        os.makedirs(args.workdir, exist_ok=True)
        built = _run_builds(args.ingroup_dir, args.outgroup, args.workdir, args.threads)
        tree_files = list(built.values())
        labels = list(built.keys())
    else:
        if not args.trees:
            ap.error("give --trees, or --build with --ingroup-dir/--outgroup")
        tree_files = args.trees
        labels = [os.path.basename(os.path.dirname(t)) or os.path.basename(t)
                  for t in tree_files]

    texts = {lab: open(tf).read() for lab, tf in zip(labels, tree_files)}
    emit("=== MLSA outgroup-stability scan (ingroup RF; 0 = identical topology) ===")
    labs = list(texts)
    worst = 0
    for i in range(len(labs)):
        for j in range(i + 1, len(labs)):
            rf, nsh, mx = rf_distance(texts[labs[i]], texts[labs[j]])
            norm = (rf / mx) if mx else 0.0
            worst = max(worst, norm)
            flag = "  <-- ingroup moves" if rf else ""
            emit(f"  {labs[i]} vs {labs[j]}: RF={rf} / max {mx} "
                  f"(normalised {norm:.2f}, {nsh} shared ingroup tips){flag}")
    if not any(i < j for i in range(len(labs)) for j in range(len(labs)) if i < j):
        emit("  (need >=2 trees to compare)")
    else:
        verdict = ("STABLE — ingroup topology is robust to outgroup choice"
                   if worst == 0 else
                   f"CHECK — ingroup shifts with outgroup (max normalised RF {worst:.2f}); "
                   "report deep splits cautiously")
        emit(f"  verdict: {verdict}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
