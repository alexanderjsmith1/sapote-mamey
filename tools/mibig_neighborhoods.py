#!/usr/bin/env python3
"""mibig_neighborhoods.py — cluster MIBiG reference domains of one family into "neighborhoods", pick one
representative each, and (optionally) assign AS-strain domains to the nearest neighborhood.

the Developer or User 2026-08-10 design: "run trees for mibig proteins to build neighborhoods, then make a tree with 1
representative from each neighborhood along with my AS strains, then make appropriate trees with each AS strain
protein in the correct neighborhood." Two-level scheme: coarse overview (reps + AS) -> focused per-neighborhood.

Steps: muscle-align the family's MIBiG domains -> FastTree (fast scaffold) -> single-linkage cluster tips at a
patristic-distance threshold = neighborhoods -> medoid representative per neighborhood. Deterministic.

Outputs (strain_data/_NEIGHBORHOODS_2026-08-10/<FAM>/):
  <FAM>_neighborhoods.tsv   tip, neighborhood_id, is_rep, metabolite, accession
  <FAM>_reps.faa            one representative sequence per neighborhood (for the overview + as anchor set)
  <FAM>_mibig.treefile      the MIBiG scaffold tree (newick)

Usage: Tools/bin/python3 Tools/mibig_neighborhoods.py --faa "<MIBiG_KS.faa>" --fam KS --thresh 1.2
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, re, subprocess, sys, tempfile
import os
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # bundle root for `import mamey` (v9.7.367 A10)
from mamey.workspace_root import workspace_root

ROOT = str(workspace_root())
PHYLO_BIN = f"{ROOT}/miniconda3/envs/phylo/bin"
OUT = f"{ROOT}/strain_data/_NEIGHBORHOODS_2026-08-10"


def _meta(tip):
    m = re.match(r'MIBiG__(BGC\d+)__(.+?)__', tip)
    return (m.group(2), m.group(1)) if m else ("", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faa", required=True)
    ap.add_argument("--fam", required=True)
    ap.add_argument("--thresh", type=float, default=1.5,
                    help="max within-neighborhood tip-to-tip diameter (complete-linkage clade cut)")
    ap.add_argument("--from-tree", default=None, help="reuse an existing FastTree newick (skip muscle/FastTree)")
    a = ap.parse_args()
    env = dict(os.environ); env["PATH"] = PHYLO_BIN + ":" + env.get("PATH", "")
    od = os.path.join(OUT, a.fam); os.makedirs(od, exist_ok=True)
    from Bio import Phylo
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO

    tree = a.from_tree or os.path.join(od, f"{a.fam}_mibig.treefile")
    if not a.from_tree:
        aln = os.path.join(od, f"{a.fam}_mibig.aln.faa")
        if subprocess.call(["muscle", "-align", a.faa, "-output", aln], env=env,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) != 0:
            emit("muscle failed"); return 1
        with open(tree, "w") as fh:
            if subprocess.call(["FastTree", "-lg", aln], env=env, stdout=fh, stderr=subprocess.DEVNULL) != 0:
                emit("FastTree failed"); return 1

    t = Phylo.read(tree, "newick"); t.ladderize()
    tips = t.get_terminals()
    names = [x.name for x in tips]
    ti = {x: i for i, x in enumerate(tips)}
    # pairwise patristic distances
    dist = {}
    for i in range(len(tips)):
        for j in range(i + 1, len(tips)):
            d = t.distance(tips[i], tips[j])
            dist[(i, j)] = dist[(j, i)] = d
    # COMPLETE-LINKAGE clade cut: maximal subtrees whose internal diameter <= thresh (avoids single-linkage chaining)
    def diam(clade):
        lv = clade.get_terminals()
        if len(lv) < 2:
            return 0.0
        ii = [ti[x] for x in lv]
        return max(dist[(x, y)] for x in ii for y in ii if x < y)
    clusters = []
    def rec(cl):
        if diam(cl) <= a.thresh:
            clusters.append([ti[x] for x in cl.get_terminals()])
        else:
            for c in cl.clades:
                rec(c)
    rec(t.root)
    # medoid representative per cluster (min total distance to clustermates; singletons = self)
    order = sorted(clusters, key=lambda c: -len(c))
    rows, reps = [], []
    for nid, members in enumerate(order, 1):
        if len(members) == 1:
            rep = members[0]
        else:
            rep = min(members, key=lambda m: sum(dist.get((m, o), 0) for o in members if o != m))
        for m in members:
            metab, acc = _meta(names[m])
            rows.append((names[m], f"{a.fam}_N{nid:02d}", "yes" if m == rep else "", metab, acc))
        reps.append(names[rep])
    # write outputs
    seqd = {r.id: str(r.seq) for r in SeqIO.parse(a.faa, "fasta")}
    with open(os.path.join(od, f"{a.fam}_neighborhoods.tsv"), "w") as fh:
        fh.write("tip\tneighborhood\tis_rep\tmetabolite\taccession\n")
        for r in rows:
            fh.write("\t".join(r) + "\n")
    with open(os.path.join(od, f"{a.fam}_reps.faa"), "w") as fh:
        for rn in reps:
            if rn in seqd:
                fh.write(f">{rn}\n{seqd[rn]}\n")
    emit(f'{a.fam}: {len(tips)} MIBiG domains -> {len(order)} neighborhoods (thresh {a.thresh}); {len(reps)} representatives.', f'  reps -> {od}/{a.fam}_reps.faa ; membership -> {od}/{a.fam}_neighborhoods.tsv', sep="\n")
    # neighborhood size histogram (top)
    sizes = sorted((len(m) for m in order), reverse=True)
    emit("  neighborhood sizes (top 10):", sizes[:10])
    emit("Class-level reference clustering; homology, not activity/production; judgment deferred.")


if __name__ == "__main__":
    sys.exit(main())
