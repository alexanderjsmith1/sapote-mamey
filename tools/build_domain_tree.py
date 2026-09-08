#!/usr/bin/env python3
"""build_domain_tree.py — the ONLY sanctioned way to build a BGC-machinery domain tree (VGP-399).

Mirrors tools/build_tree.sh for the domain lane: declare intent in DOMAIN_TREE_SPEC.json, then this
runner extracts → stages (dedup/length/min-tips gates) → aligns+infers (approval-gated) → runs the
outgroup-aware sanity gate → writes the Mode-B summary TSV. A FAILing tree is never rendered; there
is no argument to skip the gate.

Usage:
  build_domain_tree.py <DOMAIN_TREE_SPEC.json> [--threads N] [--skip-inference]

--skip-inference stops after staging (spec/extraction/staging validation without CPU).
Claim-safety: class-level homology context; judgment deferred; no structure/activity/HGT claims.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # bundle root for `import mamey`


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--skip-inference", action="store_true",
                    help="validate spec + extraction + staging only (no CPU)")
    a = ap.parse_args(argv)

    from mamey import domain_tree as DT
    try:
        spec = DT.load_spec(a.spec)
    except DT.DomainTreeError as e:
        sys.stderr.write(f"REFUSED: {e}\n"); return 2

    cls, outdir = spec["domain_class"], Path(spec["outdir"])
    if cls in DT.MODULE_CORE_CLASSES:
        from mamey.ks_phylogeny import extract_module_core_domains
        res = extract_module_core_domains(spec["gbk_dir"], classes=(cls,))
        doms = [{**d, "strain": res["strain"]} for d in res["domains"]]
    else:
        from mamey.tailoring_extract import extract_tailoring_enzymes   # card 2/3
        res = extract_tailoring_enzymes(spec["gbk_dir"], families=(cls,))
        doms = res["enzymes"]
    try:
        staged = DT.stage_domains(doms, cls, outdir, min_tips=int(spec.get("min_tips", DT.MIN_TIPS)))
    except DT.DomainTreeError as e:
        sys.stderr.write(f"REFUSED: {e}\n"); return 2
    emit(f"[stage] {staged['n_staged']} staged ({staged['n_dedup']} dedup, "
          f"{staged['n_short_excluded']} short-excluded, {staged['n_long_flagged']} long-flagged) "
          f"-> {os.path.basename(staged['fasta'])}")
    if a.skip_inference:
        sys.stderr.write("[stop] --skip-inference: staging validated; no CPU run.\n"); return 0
    try:
        tre = DT.build_tree(staged["fasta"], outdir, spec["approved_by"], threads=a.threads)
    except DT.DomainTreeError as e:
        sys.stderr.write(f"REFUSED: {e}\n"); return 2
    ok, msg = DT.gate_tree(tre, outgroup=spec.get("outgroup"),
                           require_outgroup=not spec.get("allow_no_outgroup", False))
    emit(msg)
    if not ok:
        sys.stderr.write("REFUSED: tree_sanity_check FAILED — not rendering; fix the offender and rebuild "
              "(no skip argument exists).\n")
        return 2
    summary = DT.write_summary(
        [{"domain_class": cls, "strain": d.get("strain", ""),
          "node": d.get("node", ""), "tip": ""} for d in doms], outdir, cls)
    emit(f"[ok] gated tree: {tre}\n[ok] summary: {summary}\n"
          f"Claim-safety: class-level homology context; judgment deferred.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
