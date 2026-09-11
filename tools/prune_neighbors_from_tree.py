#!/usr/bin/env python3
"""prune_neighbors_from_tree.py — pick each query strain's nearest reference
neighbours from a big MLSA tree, and hand a bounded panel to Codex's panel builder.

Tier-2 bridge of the Sapote-Mamey two-tier phylogenomics workflow
(see docs/GTOTREE_WORKFLOW.md). The tier-1 full-pool MLSA (build_mlsa.py) is CHEAP —
build as many wide-net MLSA screens as you like, un-gated. This tool reads such a
screen and, for every AS-/AJS- query tip, selects its K nearest REFERENCE tips by
patristic distance. The result is a bounded set (queries + neighbours + one outgroup)
that flows into the APPROVAL-GATED heavy step:

    build_mlsa.py (cheap screen)  ->  prune_neighbors_from_tree.py (this tool)
      ->  build_phylo_panel.py  ->  plan_gtotree_iqtree.py  ->  USER APPROVAL
      ->  GToTree 138-SCG core-genome + IQ-TREE   (cores committed only here)

So this tool never runs a tree and never commits cores. It emits a keep-list and,
with --emit-panel-tsv, a manifest in the exact column shape build_phylo_panel.py
consumes (candidate_id, role, source_path, selection_basis, related_query_ids), so
the two-tier screen and Codex's bounded-panel governance are ONE data flow rather
than competing planners.

Codex's release ceiling is 60 total tips (40 default). This tool enforces --max-tips
(default 60): queries and the outgroup are never dropped; if the panel would exceed
the cap, the FARTHEST references are trimmed first (and reported), never a query.

CLAIM SAFETY: neighbour selection is a topology convenience; the species call still
needs whole-genome ANI. "nearest_neighbour_patristic_MLSA" is a selection_basis, not
an identity claim. Class-level hypotheses, judgment deferred.

Usage:
  python tools/prune_neighbors_from_tree.py <mlsa.treefile> [--k 3] [--max-tips 60]
      [--genomes-dir DIR] [--stage-dir DIR] [--emit-panel-tsv PATH]
"""
import sys
import os
import re
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import glob
import shutil
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

# v9.7.374 fix: was AS-/AJS-only. docs/phylogenomics.md names "focal AS/SID genome" as
# this workflow's own convention -- SID is a real, common query-genome category in this
# cohort. A SID-prefixed query tip failed this match and fell into `refs` (the trimmable
# pool), so it was either (a) silently dropped from the panel entirely whenever no other
# query happened to select it among its k-nearest, with ZERO warning and no entry in
# 'trimmed' either -- it simply never appears anywhere in the output -- or (b) miscounted
# as a REFERENCE in the emitted panel TSV, feeding build_phylo_panel.py -> USER APPROVAL ->
# GToTree/IQ-TREE with a real query genome silently excluded or mislabeled. Reproduced live:
# a synthetic SID10815 query tip vanished from build_panel()'s entire output (not kept, not
# trimmed, not referenced by any query) under the original AS-only pattern.
QUERY = re.compile(r'^(AS[-_]\d+|AJS[-_]\d+|SID\d+)', re.I)
OUTGROUP = re.compile(r'OUTGROUP', re.I)
PANEL_CEILING = 60  # Codex GTOTREE_PANEL_SELECTION.md hard release ceiling


class Node:
    __slots__ = ('name', 'length', 'children', 'parent')

    def __init__(self):
        self.name = ''
        self.length = 0.0
        self.children = []
        self.parent = None


def parse(text):
    # v9.7.416: bounds-checked reads. See tools/mlsa_outgroup_scan.py::_parse for the same repair --
    # these two share a hand-rolled parser that indexed `s[pos]` unguarded, so an empty or truncated
    # tree raised a bare IndexError naming neither the file nor the reason. Typed ValueError matches
    # tools/tree_bgc_overlay.py::parse_newick, which already got this right.
    s = text.strip().rstrip(';').strip()
    pos = 0
    if not s:
        raise ValueError("no Newick tree to parse (empty or whitespace-only input)")

    def _at(i):
        if i >= len(s):
            raise ValueError("truncated Newick: input ended mid-tree (unbalanced parentheses?)")
        return s[i]

    def pnode():
        nonlocal pos
        n = Node()
        if _at(pos) == '(':
            pos += 1
            while True:
                c = pnode()
                c.parent = n
                n.children.append(c)
                if _at(pos) == ',':
                    pos += 1
                    continue
                if _at(pos) == ')':
                    pos += 1
                    break
                # Neither ',' nor ')': the old loop never advanced -> INFINITE LOOP. Refuse.
                raise ValueError(f"malformed Newick at offset {pos}: expected ',' or ')', "
                                 f"found {_at(pos)!r}")
        start = pos
        while pos < len(s) and s[pos] not in '(),:;':
            pos += 1
        n.name = s[start:pos].strip().strip("'\"")
        if pos < len(s) and s[pos] == ':':
            pos += 1
            start = pos
            while pos < len(s) and s[pos] not in '(),;':
                pos += 1
            try:
                n.length = float(s[start:pos])
            except ValueError:
                n.length = 0.0
        return n
    return pnode()


def leaves(n):
    if not n.children:
        yield n
    for c in n.children:
        yield from leaves(c)


def _depths_and_ancestors(root):
    depth = {}
    parent = {}

    def walk(n, d):
        depth[n] = d
        for c in n.children:
            parent[c] = n
            walk(c, d + c.length)
    walk(root, 0.0)

    def ancestors(n):
        chain = []
        while n is not None:
            chain.append(n)
            n = parent.get(n)
        return chain

    return depth, ancestors


def build_panel(root, k=3, max_tips=PANEL_CEILING):
    """Select a bounded comparator panel from a parsed MLSA tree. Pure; unit-tested.

    Returns a dict:
      {'queries':   [name, ...],
       'outgroups': [name, ...],
       'references': {ref_name: {'related': sorted[query_name,...],
                                 'min_dist': float}},
       'trimmed':   [ref_name, ...]}   # refs dropped to honour max_tips (farthest first)

    Rule: every query and every outgroup is kept. Each query contributes its k
    nearest reference tips. If total tips exceed max_tips, references are removed
    farthest-first (largest min patristic distance to any query) until within cap;
    queries/outgroups are never removed.
    """
    tips = list(leaves(root))
    depth, ancestors = _depths_and_ancestors(root)
    anc = {t: ancestors(t) for t in tips}
    anc_set = {t: set(a) for t, a in anc.items()}

    def dist(a, b):
        for x in anc[a]:
            if x in anc_set[b]:
                return depth[a] + depth[b] - 2 * depth[x]
        return depth[a] + depth[b]

    queries = [t for t in tips if QUERY.match(t.name)]
    refs = [t for t in tips
            if not QUERY.match(t.name) and not OUTGROUP.search(t.name)]
    outg = [t for t in tips if OUTGROUP.search(t.name)]

    references = {}
    for q in queries:
        for r in sorted(refs, key=lambda r: dist(q, r))[:k]:
            d = dist(q, r)
            slot = references.setdefault(r.name, {'related': set(), 'min_dist': d})
            slot['related'].add(q.name)
            slot['min_dist'] = min(slot['min_dist'], d)

    trimmed = []
    fixed = len(queries) + len(outg)   # never trimmable
    # trim farthest references first until queries+outgroups+refs <= max_tips
    order = sorted(references, key=lambda name: references[name]['min_dist'], reverse=True)
    while fixed + len(references) > max_tips and order:
        drop = order.pop(0)
        references.pop(drop, None)
        trimmed.append(drop)

    for slot in references.values():
        slot['related'] = sorted(slot['related'])
    return {
        'queries': sorted(t.name for t in queries),
        'outgroups': sorted(t.name for t in outg),
        'references': references,
        'trimmed': trimmed,
    }


def keep_set(panel):
    return (set(panel['queries']) | set(panel['outgroups'])
            | set(panel['references']))


def _source_path(name, gdir):
    if not gdir:
        return ""
    hit = glob.glob(os.path.join(gdir, name + ".fna"))
    return hit[0] if hit else os.path.join(gdir, name + ".fna")


def write_panel_tsv(panel, path, gdir=None):
    """Emit build_phylo_panel.py's manifest shape: candidate_id, role, source_path,
    selection_basis, related_query_ids. REFERENCE rows carry the two required extra
    fields so the panel builder never has to infer 'nearest'/'type' status."""
    with open(path, "w", newline="") as fh:
        w = _SafeWriter(fh, delimiter="\t")
        w.writerow(["candidate_id", "role", "source_path",
                    "selection_basis", "related_query_ids"])
        for q in panel['queries']:
            w.writerow([q, "QUERY", _source_path(q, gdir), "", ""])
        for r in sorted(panel['references']):
            slot = panel['references'][r]
            w.writerow([r, "REFERENCE", _source_path(r, gdir),
                        "nearest_neighbour_patristic_MLSA",
                        ";".join(slot['related'])])
        for o in panel['outgroups']:
            w.writerow([o, "OUTGROUP", _source_path(o, gdir),
                        "curator_outgroup", ""])


def _arg(argv, flag, default=None):
    return argv[argv.index(flag) + 1] if flag in argv else default


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        sys.stderr.write(__doc__)
        return 2
    tf = argv[0]
    k = int(_arg(argv, '--k', 3))
    max_tips = int(_arg(argv, '--max-tips', PANEL_CEILING))
    gdir = _arg(argv, '--genomes-dir')
    sdir = _arg(argv, '--stage-dir')
    tsv = _arg(argv, '--emit-panel-tsv')

    if max_tips > PANEL_CEILING:
        sys.stderr.write(f"prune: --max-tips {max_tips} exceeds the release ceiling "
                         f"{PANEL_CEILING}; clamping to {PANEL_CEILING}.\n")
        max_tips = PANEL_CEILING

    root = parse(open(tf).read())
    panel = build_panel(root, k=k, max_tips=max_tips)
    keep = keep_set(panel)

    sys.stderr.write(
        f"queries={len(panel['queries'])} refs_kept={len(panel['references'])} "
        f"outgroups={len(panel['outgroups'])} -> panel = {len(keep)} tips "
        f"(k={k}, cap={max_tips})\n")
    if panel['trimmed']:
        sys.stderr.write(f"  trimmed {len(panel['trimmed'])} farthest reference(s) to "
                         f"honour the {max_tips}-tip cap: {panel['trimmed'][:5]}"
                         f"{'...' if len(panel['trimmed']) > 5 else ''}\n")
    if not panel['outgroups']:
        sys.stderr.write("  WARN no _OUTGROUP tip in the MLSA tree — the panel needs "
                         "exactly one curator outgroup before build_phylo_panel.\n")

    for name in sorted(keep):
        emit(name)

    if tsv:
        write_panel_tsv(panel, tsv, gdir)
        sys.stderr.write(f"wrote panel manifest -> {tsv}  "
                         f"(feed to: python tools/build_phylo_panel.py {tsv} <stage>/ "
                         f"--panel-size {len(keep)})\n")

    if gdir and sdir:
        os.makedirs(sdir, exist_ok=True)
        staged = 0
        for name in keep:
            hit = glob.glob(os.path.join(gdir, name + ".fna"))
            if hit:
                shutil.copy(hit[0], os.path.join(sdir, os.path.basename(hit[0])))
                staged += 1
            else:
                sys.stderr.write(f"  WARN no genome for tip {name}\n")
        sys.stderr.write(f"staged {staged}/{len(keep)} genomes into {sdir}\n")
    return 0


if __name__ == "__main__":
    main()
