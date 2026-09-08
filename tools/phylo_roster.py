#!/usr/bin/env python3
"""phylo_roster.py — number the strains in a tree or panel, and edit them by number.

The hand-curation primitive for the two-tier phylogenomics workflow. A curator builds
a tree only after hand-picking its members; this tool makes that loop fast:

  1. Print a STABLE, NUMBERED roster of every tip (from a treefile) or every row (from
     a build_phylo_panel.py panel TSV), with role / genus / related-query / host.
  2. Accept `--remove "30,31,36"` and emit the edited panel TSV (and a keep-list), so
     the curator says "remove 30, 31, 36" and the exact strains are dropped — no guessing.

Numbering is 1-based and deterministic: tree tips in newick leaf order (the order they
stack in the figure), panel rows in file order. Re-print after every edit so the numbers
always match what the curator is looking at.

QUERY rows (AS-/AJS-) are the reason the tree exists; removing one is allowed (the curator
is in charge) but is flagged loudly so an AS strain is never dropped by a mis-typed number.

CLAIM SAFETY: this is panel bookkeeping only. Membership is not a species-identity claim;
class-level hypotheses, judgment deferred.

Usage:
  python tools/phylo_roster.py --tree fam.treefile [--strain-table hosts.csv]
  python tools/phylo_roster.py --panel panel.tsv
  python tools/phylo_roster.py --panel panel.tsv --remove "30,31,36" --out panel_v2.tsv
  python tools/phylo_roster.py --tree fam.treefile --remove "5,9" --out keep_list.txt
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
import argparse
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

QUERY = re.compile(r'^(AS[-_]\d+|AJS[-_]\d+)', re.I)
OUTGROUP = re.compile(r'OUTGROUP', re.I)
PANEL_COLS = ["candidate_id", "role", "source_path",
              "selection_basis", "related_query_ids"]


# ---- newick (tips in leaf order) --------------------------------------------
def tree_tips(text):
    """Tip labels in newick leaf order. Tolerant single-pass reader."""
    s = text.strip().rstrip(';')
    tips, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c in '(,':
            # a tip starts if the next char is not '(' (i.e. not a clade open)
            j = i + 1
            if j < n and s[j] not in '()':
                k = j
                while k < n and s[k] not in '(),:;':
                    k += 1
                lab = s[j:k].strip().strip("'\"")
                if lab:
                    tips.append(lab)
                i = k
                continue
        i += 1
    return tips


def _role(label):
    if OUTGROUP.search(label):
        return "OUTGROUP"
    if QUERY.match(label):
        return "QUERY"
    return "REFERENCE"


def _genus(label):
    tok = label.split('_')[0]
    return tok if re.match(r'^[A-Z][a-z]+$', tok) else ""


# ---- roster building --------------------------------------------------------
def roster_from_tips(tips, hosts=None):
    """[{index, label, role, genus, related, host}] from tree tips. Pure."""
    hosts = hosts or {}
    out = []
    for i, t in enumerate(tips, 1):
        out.append({"index": i, "label": t, "role": _role(t),
                    "genus": _genus(t), "related": "",
                    "host": hosts.get(t, "")})
    return out


def roster_from_panel(rows, hosts=None):
    """[{index, label, role, genus, related, host}] from panel TSV rows. Pure."""
    hosts = hosts or {}
    out = []
    for i, r in enumerate(rows, 1):
        lab = r.get("candidate_id", "")
        out.append({"index": i, "label": lab,
                    "role": r.get("role", "") or _role(lab),
                    "genus": _genus(lab),
                    "related": r.get("related_query_ids", ""),
                    "host": hosts.get(lab, "")})
    return out


def parse_removals(spec):
    """'30,31,36' or '30 31 36' -> sorted unique [30,31,36]. Pure."""
    if not spec:
        return []
    nums = re.split(r'[,\s]+', spec.strip())
    return sorted({int(x) for x in nums if x})


def apply_removals(roster, indices):
    """Return (kept, removed, warnings). Removing a QUERY is allowed but warned. Pure."""
    idx = set(indices)
    valid = {r["index"] for r in roster}
    warnings = [f"index {i} not in roster (1..{len(roster)})" for i in idx if i not in valid]
    kept = [r for r in roster if r["index"] not in idx]
    removed = [r for r in roster if r["index"] in idx]
    for r in removed:
        if r["role"] == "QUERY":
            warnings.append(f"index {r['index']} is a QUERY ({r['label']}) — "
                            f"removing an AS/AJS strain from its own tree")
    return kept, removed, warnings


def format_roster(roster):
    """Aligned, numbered text block. Pure (returns a string)."""
    w = max((len(r["label"]) for r in roster), default=10)
    lines = [f"{'#':>3}  {'role':<10} {'label':<{w}}  genus / host / related-query"]
    for r in roster:
        extra = " / ".join(x for x in (r["genus"], r["host"], r["related"]) if x)
        lines.append(f"{r['index']:>3}  {r['role']:<10} {r['label']:<{w}}  {extra}")
    return "\n".join(lines)


# ---- io ---------------------------------------------------------------------
def load_hosts(path):
    """Optional strain-table/crosswalk: any CSV with a label-ish column + host-ish
    column. Maps {label: host}. Recognises newick_label/candidate_id/strain and
    host/ecology_source/genus_label."""
    if not path:
        return {}
    with open(path, newline='') as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return {}
    cols = rows[0].keys()
    labcol = next((c for c in ("newick_label", "candidate_id", "strain", "label") if c in cols), None)
    hostcol = next((c for c in ("host", "ecology_source", "source", "genus_label") if c in cols), None)
    if not labcol or not hostcol:
        return {}
    return {r[labcol]: r[hostcol] for r in rows if r.get(labcol)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="numbered roster + remove-by-number")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument('--tree')
    g.add_argument('--panel')
    ap.add_argument('--strain-table', help='optional CSV to enrich with host/source')
    ap.add_argument('--remove', help='indices to drop, e.g. "30,31,36"')
    ap.add_argument('--out', help='edited panel TSV (with --panel) or keep-list (with --tree)')
    args = ap.parse_args(argv)

    hosts = load_hosts(args.strain_table)
    panel_rows = None
    if args.tree:
        roster = roster_from_tips(tree_tips(open(args.tree).read()), hosts)
    else:
        panel_rows = list(csv.DictReader(open(args.panel), delimiter='\t'))
        roster = roster_from_panel(panel_rows, hosts)

    emit(format_roster(roster))
    emit(f"\n{len(roster)} entries "
          f"({sum(r['role']=='QUERY' for r in roster)} QUERY, "
          f"{sum(r['role']=='REFERENCE' for r in roster)} REFERENCE, "
          f"{sum(r['role']=='OUTGROUP' for r in roster)} OUTGROUP)")

    if not args.remove:
        return 0

    kept, removed, warnings = apply_removals(roster, parse_removals(args.remove))
    for w in warnings:
        sys.stderr.write(f"  WARN {w}\n")
    sys.stderr.write(f"removed {len(removed)}: "
                     f"{[r['label'] for r in removed]}\n")

    if args.out:
        if panel_rows is not None:
            keep_labels = {r["label"] for r in kept}
            with open(args.out, 'w', newline='') as fh:
                w = _SafeDictWriter(fh, fieldnames=panel_rows[0].keys(), delimiter='\t')
                w.writeheader()
                for row in panel_rows:
                    if row.get("candidate_id") in keep_labels:
                        w.writerow(row)
            sys.stderr.write(f"wrote edited panel -> {args.out} ({len(kept)} rows)\n")
        else:
            with open(args.out, 'w') as fh:
                for r in kept:
                    fh.write(r["label"] + "\n")
            sys.stderr.write(f"wrote keep-list -> {args.out} ({len(kept)} tips)\n")
    else:
        emit("\n(edited roster — pass --out to write it)")
        emit(format_roster([dict(r, index=i) for i, r in enumerate(kept, 1)]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
