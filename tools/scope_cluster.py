#!/usr/bin/env python3
r"""scope_cluster — scope an over-merged antiSMASH region to its TRUE protocluster.

antiSMASH bundles neighbouring protoclusters into one region (a "candidate cluster"), so a
region GBK for a nucleoside BGC can silently include an adjacent saccharide or NRPS cluster.
Comparing or measuring the whole region then over-counts the cluster and can mis-assign genes
to the wrong pathway. (This tool exists because exactly that happened: a glycosyltransferase +
epimerase from a merged saccharide protocluster were briefly read as decoration on a nucleoside
product.)

Given a region GBK and a target category, this uses the region's own `protocluster` /
`cand_cluster` / `proto_core` features to extract just the target cluster's genes, and flags any
that fall in an overlap with a different-category protocluster. No heuristics, no gene-window
guessing — it reads antiSMASH's own boundaries.

    scope_cluster.py --gbk region.gbk --category nucleoside --outdir OUT [--core]

Outputs OUT/<category>_scoped.gbk (the scoped cluster) and OUT/<category>_scope.json (boundary,
genes kept, genes excluded as belonging to neighbours, overlap flags). --core uses the tight
protocluster core span instead of the candidate-cluster neighbourhood. Capacity-level.
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, json, sys
from pathlib import Path


def read_protoclusters(rec):
    """Return list of {kind, category, start, end, core_start, core_end} for proto/cand clusters."""
    out = []
    for f in rec.features:
        if f.type not in ("protocluster", "cand_cluster"):
            continue
        cat = (f.qualifiers.get("category") or f.qualifiers.get("product") or ["?"])[0]
        core = f.qualifiers.get("core_location", [None])[0]
        cs = ce = None
        if core:
            import re
            m = re.search(r"\[(\d+):(\d+)\]", core)
            if m:
                cs, ce = int(m.group(1)), int(m.group(2))
        out.append({"kind": f.type, "category": cat,
                    "start": int(f.location.start), "end": int(f.location.end),
                    "core_start": cs, "core_end": ce})
    return out


def pick_target(protos, category, use_core):
    """Choose the boundary span for the requested category (cand_cluster preferred for extent)."""
    cands = [p for p in protos if category.lower() in p["category"].lower()]
    if not cands:
        raise KeyError(f"no protocluster/cand_cluster with category ~ '{category}'; "
                       f"available: {sorted({p['category'] for p in protos})}")
    # prefer cand_cluster for full extent; protocluster for --core
    if use_core:
        pc = [p for p in cands if p["kind"] == "protocluster" and p["core_start"] is not None]
        if pc:
            p = min(pc, key=lambda x: x["core_end"] - x["core_start"])
            return p["core_start"], p["core_end"], p
        # v9.7.374 (audit lane): --core requested but no matching protocluster carries a
        # parseable core_location. Pre-fix this fell through to the cand_cluster/full-candidates
        # branch below and silently returned the WIDE (non-core) boundary -- for a merged region
        # that can mean the entire multi-protocluster span, re-absorbing exactly the neighbour-
        # cluster genes this tool exists to exclude, with no flag anywhere in the report that
        # --core was requested but not honored. Live-reproduced: a category present only as a
        # protocluster with no core_location (the target span [0:20000] of a [0:40000] merged
        # cand_cluster) returned boundary [0, 40000] under --core -- the WHOLE merged region,
        # wider than even the plain non-core call would give. Fail loud instead: a caller relying
        # on --core for a tight, defensible boundary must not be handed a silently wider one.
        raise KeyError(
            f"--core requested for category ~ '{category}' but no protocluster with a parseable "
            f"core_location was found (candidates: "
            f"{[(p['kind'], p['category']) for p in cands]}). Refusing to silently widen the "
            f"scope to the non-core boundary; drop --core if the wider, non-core extent is "
            f"acceptable for this region."
        )
    cc = [p for p in cands if p["kind"] == "cand_cluster"] or cands
    p = min(cc, key=lambda x: x["end"] - x["start"])   # tightest candidate for the category
    return p["start"], p["end"], p


def other_category_cores(protos, category):
    """Cores of protoclusters whose category differs from the target (for overlap flagging)."""
    out = []
    for p in protos:
        if p["kind"] == "protocluster" and category.lower() not in p["category"].lower() \
                and p["core_start"] is not None:
            out.append((p["category"], p["core_start"], p["core_end"]))
    return out


def scope(rec, category, use_core=False):
    protos = read_protoclusters(rec)
    lo, hi, chosen = pick_target(protos, category, use_core)
    others = other_category_cores(protos, category)
    kept, excluded, overlap = [], [], []
    for f in rec.features:
        if f.type != "CDS" or "translation" not in f.qualifiers:
            continue
        s, e = int(f.location.start), int(f.location.end)
        mid = (s + e) // 2
        lt = f.qualifiers.get("locus_tag", ["?"])[0]
        if not (lo <= mid < hi):
            excluded.append(lt)
            continue
        # in target span; flag if it also sits in another category's protocluster CORE
        in_other = next((c for c, cs, ce in others if cs <= mid < ce), None)
        if in_other:
            overlap.append({"locus_tag": lt, "also_in": in_other})
        kept.append(f)
    return {"category": category, "boundary": [lo, hi], "span_kb": round((hi - lo) / 1000, 1),
            "chosen": chosen, "n_kept": len(kept), "n_excluded": len(excluded),
            "excluded": excluded, "overlap": overlap, "all_protoclusters": protos}, kept, (lo, hi)


def write_scoped_gbk(rec, kept, span, category, label, outdir):
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    lo, hi = span
    sub = rec[lo:hi]
    # keep only CDS features that were kept (rec[lo:hi] re-derives features by coordinate; that's fine)
    sub.id = f"{label}_{category}"[:16]
    sub.name = sub.id
    sub.description = f"{label} {category} cluster (protocluster-scoped from antiSMASH region)"
    sub.annotations["molecule_type"] = "DNA"
    p = Path(outdir) / f"{label}_{category}_scoped.gbk"
    SeqIO.write(sub, str(p), "genbank")
    return str(p)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Scope an over-merged antiSMASH region to its true protocluster.")
    ap.add_argument("--gbk", required=True, help="antiSMASH region GBK (may be over-merged)")
    ap.add_argument("--category", required=True, help="target protocluster category, e.g. nucleoside")
    ap.add_argument("--label", default="cluster", help="label for output filenames / record id")
    ap.add_argument("--core", action="store_true", help="use the tight protocluster core span")
    ap.add_argument("--outdir", default="scope_out")
    a = ap.parse_args(argv)
    try:
        from Bio import SeqIO
    except ImportError:
        from mamey._gbk_shim import SeqIO
    rec = next(SeqIO.parse(a.gbk, "genbank"))
    report, kept, span = scope(rec, a.category, use_core=a.core)
    Path(a.outdir).mkdir(parents=True, exist_ok=True)
    p = write_scoped_gbk(rec, kept, span, a.category, a.label, a.outdir)
    (Path(a.outdir) / f"{a.label}_{a.category}_scope.json").write_text(json.dumps(report, indent=2))
    emit(f"[scope_cluster] {a.label}/{a.category}: boundary {report['boundary']} "
          f"({report['span_kb']} kb), kept {report['n_kept']} CDS, "
          f"excluded {report['n_excluded']} (merged neighbours) -> {p}")
    if report["overlap"]:
        ov = ", ".join(f"{o['locus_tag']}~{o['also_in']}" for o in report["overlap"])
        emit(f"[scope_cluster] overlap flags (in target span but inside another cluster's core): {ov}")
    merged = sorted({p2['category'] for p2 in report['all_protoclusters'] if p2['kind'] == 'protocluster'})
    if len(merged) > 1:
        emit(f"[scope_cluster] region merged {len(merged)} protoclusters: {merged} "
              f"— only the '{a.category}' genes were kept.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
