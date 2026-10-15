"""Apply a PENDANT_LEDGER_<genus>.tsv (from estimate_placeholder_pendants.py) to a gappa graft.

In a gappa graft, a query's pendant is the path from its attachment point on a reference edge to its tip. When
several queries sit on one edge, gappa can share part of that path: two queries become a cherry whose stem and tip
branches sum to each pendant. A shared stem and terminal branch can together equal the placement default.

For every query-only subtree (all tips queries, hanging off a reference edge) that holds a ledger query:
- the target path for each tip is its RAxML-NG estimate if it is in the ledger, else its current path, which is kept;
- the shared segments are scaled by k = min(target / current path) over the tips;
- each tip branch is then set so its path equals its target exactly. The choice of k keeps every branch >= 0.

A ledger query whose current path is not the 0.105361 default is refused, because it would mean the ledger and the
graft come from different runs.
"""
import csv
import sys

PH = 0.1053605157


def load(path):
    return {r["query"]: float(r["raxml_ng_pendant"]) for r in csv.DictReader(open(path), delimiter="\t")}


def apply(graft, ledger, is_query):
    est = load(ledger) if isinstance(ledger, str) else ledger
    if not est:
        return 0
    parent = {c: p for p in graft.find_clades() for c in p.clades}
    names = {t.name for t in graft.get_terminals()}
    missing = set(est) - names
    if missing:
        sys.exit(f"PENDANT_LEDGER_QUERY_NOT_IN_GRAFT: {sorted(missing)[:3]}")

    def query_only(c):
        return all(is_query(t.name) for t in c.get_terminals())

    roots = []
    for c in graft.find_clades():
        if c is graft.root or not query_only(c):
            continue
        p = parent.get(c)
        if p is None or not query_only(p):
            roots.append(c)
    done = 0
    for r in roots:
        tips = r.get_terminals()
        if not any(t.name in est for t in tips):
            continue
        path = {t.name: sum(x.branch_length or 0.0 for x in [r] + r.get_path(t)[:]) if t is not r
                else (r.branch_length or 0.0) for t in tips}
        # r.get_path(t) excludes r and includes t
        for t in tips:
            if t.name in est and abs(path[t.name] - PH) > 1e-5:
                sys.exit(f"PENDANT_LEDGER_MISMATCH: {t.name} pendant path {path[t.name]:.6f} is not the EPA-ng default")
        target = {t.name: est.get(t.name, path[t.name]) for t in tips}
        k = min(target[n] / path[n] if path[n] > 0 else 1.0 for n in target)
        if r.is_terminal():
            r.branch_length = target[r.name]
        else:
            for c in [r] + [x for x in r.find_clades() if x is not r and not x.is_terminal()]:
                c.branch_length = (c.branch_length or 0.0) * k
            for t in tips:
                above = sum(x.branch_length or 0.0 for x in [r] + r.get_path(t)[:-1])
                t.branch_length = max(0.0, target[t.name] - above)
        done += sum(1 for t in tips if t.name in est)
    return done
