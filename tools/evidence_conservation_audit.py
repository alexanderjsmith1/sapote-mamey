#!/usr/bin/env python3
"""Evidence-conservation auditor — finds the 'present in source, dropped in package' bug class.

All defects found in the 2026-06-10 session shared one shape: high-value biosynthetic
evidence present in the raw antiSMASH output that was silently NOT propagated into the
sealed Mamey package. Contract/schema tests cannot catch this (output is well-formed,
just missing information). This auditor catches it mechanically, WITHOUT knowing what
any strain produces.

DESIGN LESSON (why naive auditing fails): most strong evidence in a genome is
housekeeping (FtsZ, ribosomal proteins, central metabolism) that the package SHOULD
drop. A raw "did every hit survive?" check produced 261 meaningless flags and buried
the one real signal (AHBA). The auditor therefore compares ONLY biosynthetically-
diagnostic evidence, per module, and uses LOCUS-level presence checks (not bare string
matching, which false-positives on product labels).

Coverage (each is a module whose diagnostic payload was checked for conservation):
  1. detection.tigrfam       — diagnostic TIGRFAM accessions (AHBA/ene_KS/etc.)
  2. modules.nrps_pks        — A-domain substrate (consensus) predictions
  3. modules.active_site_finder — catalytic-residue / stereochem calls
  4. modules.t2pks / terpene — product-class predictions
  5. modules.{lanthi,lasso,sacti,thio}peptides — RiPP core-peptide sequences

NOT yet covered (honest gaps — a bug in these would NOT be caught):
  - cluster_compare / clusterblast detail (similarity bulk, lower diagnostic value)
  - pfam2go (GO terms — largely duplicate Pfam), genefunctions
Extend MODULE CHECKS below as new diagnostic types are needed.

Usage:
    python3 tools/evidence_conservation_audit.py <raw_antismash.json> <package_evidence.json>
Exit non-zero if any diagnostic category shows a drop.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import json, sys

try:
    import os as _os, sys as _sys
    _sys.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from mamey.antismash_evidence import DIAGNOSTIC_TIGRFAM as _DT
    DIAGNOSTIC_TIGRFAM = set(_DT)
except Exception:
    DIAGNOSTIC_TIGRFAM = {"TIGR01454","TIGR03604","TIGR03828","TIGR04186"}
DIAGNOSTIC_SUBSTRATES = {"Hpg","Dhpg","Dpg","AHBA","OH-Orn","bOH-Tyr","Bht","pip","Aad"}


def _records(raw): return raw.get("records", [])


def _token_in_blob(token, blob):
    """v9.7.115: word-bounded containment, not a bare substring. The gate verifies an evidence token
    survived into the package JSON; a SHORT diagnostic token (e.g. the NRPS substrate 'pip') would
    bare-substring-match inside unrelated words ('equipped', 'pipeline') and FALSELY report the
    evidence as conserved when its real record was dropped. Bounding by non-alphanumerics (so the
    token sits at a JSON value/word boundary) closes that false-conservation hole. Distinctive tokens
    (accessions, long names) are unaffected — they already only matched at boundaries."""
    import re as _re
    return bool(_re.search(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % _re.escape(str(token)), blob))


def _count_in_blob(token, blob):
    """Word-bounded occurrence COUNT, not just boolean presence. Needed where the same diagnostic
    token can legitimately appear at more than one locus in the raw evidence (e.g. the same TIGRFAM
    accession hit in two distinct BGCs) -- a boolean `token in blob` check only asks "does this
    string appear ANYWHERE in the package," which is satisfied by a single surviving occurrence even
    when every OTHER occurrence of the same token was dropped. Counting closes that gap without
    needing to parse the package's own JSON structure (this auditor deliberately treats the package
    as an opaque blob -- see the module docstring)."""
    import re as _re
    return len(_re.findall(r"(?<![A-Za-z0-9])%s(?![A-Za-z0-9])" % _re.escape(str(token)), blob))


def check_tigrfam(raw, pkg_blob):
    """v9.7.401 (BC2): was a bare `acc not in pkg_blob` boolean-presence check -- silently
    contradicting this module's own stated design principle ("uses LOCUS-level presence checks, not
    bare string matching"). Reproduced live: the SAME diagnostic accession hit at two distinct loci
    in raw (two separate BGCs both showing e.g. TIGR01454), with the package retaining only ONE of
    the two -- the boolean check found the accession string present (from the surviving hit) and
    reported "2/2 conserved," completely missing that the other locus's hit was dropped. This is the
    identical false-conservation shape the v9.7.115 (NRPS substrates) and v9.7.374 (RiPP cores) fixes
    already closed for their own checks; check_tigrfam -- arguably the most consequential of the five
    (TIGRFAM diagnostics is the evidence class behind this tool's own motivating AHBA incident) --
    was never fixed the same way. Counting occurrences (via `_count_in_blob`) rather than boolean
    presence catches an aggregate shortfall even without per-locus JSON structure to inspect."""
    seen=set(); dropped=set()
    raw_counts: dict[str, int] = {}
    for rec in _records(raw):
        for h in rec.get("modules",{}).get("antismash.detection.tigrfam",{}).get("hits",[]):
            acc=h.get("identifier") or h.get("domain")
            if acc in DIAGNOSTIC_TIGRFAM:
                seen.add(f"{acc}@{h.get('locus_tag')}")
                raw_counts[acc] = raw_counts.get(acc, 0) + 1
    for acc, n_raw in raw_counts.items():
        n_pkg = _count_in_blob(acc, pkg_blob)
        if n_pkg < n_raw:
            dropped.add(f"{acc}: {n_raw - n_pkg} of {n_raw} occurrence(s) missing from package")
    return "TIGRFAM diagnostics", len(seen), dropped


def check_nrps_substrates(raw, pkg_blob):
    seen=0; dropped=[]
    for rec in _records(raw):
        for dom,val in rec.get("modules",{}).get("antismash.modules.nrps_pks",{}).get("consensus",{}).items():
            if val in DIAGNOSTIC_SUBSTRATES:
                seen+=1
                if not _token_in_blob(val, pkg_blob): dropped.append(f"{val} @ {dom}")
    return "NRPS diagnostic substrates", seen, dropped


def check_active_site(raw, pkg_blob):
    # Catalytic-residue / stereochemistry calls. This is all-or-nothing: either the
    # package carries active-site evidence or it does not. Report seen=1 (the category)
    # with the pairing count in the message, so kept/seen math stays honest.
    n_pairings=0
    for rec in _records(raw):
        n_pairings += len(rec.get("modules",{}).get("antismash.modules.active_site_finder",{}).get("pairings",[]))
    if n_pairings==0: return "active-site / stereochem calls", 0, []
    present = "active site" in pkg_blob.lower() or "active_site" in pkg_blob.lower()
    dropped = [] if present else [f"all {n_pairings} active-site/stereochem pairings absent from package"]
    return "active-site / stereochem calls", 1, dropped


def check_product_class(raw, pkg_blob):
    # t2pks/terpene product_classes predictions. Check the distinctive prediction
    # strings (e.g. 'pentangular polyphenol'), not the bare module name.
    seen=[]; dropped=[]
    for rec in _records(raw):
        for mod in ("antismash.modules.t2pks","antismash.modules.terpene"):
            pp=rec.get("modules",{}).get(mod,{}).get("protocluster_predictions",{})
            for pc in _collect_product_classes(pp):
                seen.append(pc)
                if not _token_in_blob(pc, pkg_blob): dropped.append(f"{pc}")
    return "product-class predictions (t2pks/terpene)", len(seen), dropped


def _collect_product_classes(pp):
    out=[]
    if isinstance(pp,dict):
        for v in pp.values():
            if isinstance(v,dict):
                for pc in v.get("product_classes",[]):
                    if isinstance(pc,str): out.append(pc)
                out += _collect_product_classes(v)
    return out


def check_ripp_cores(raw, pkg_blob):
    # RiPP core-peptide sequences + subclass — the actual product backbone, the
    # single most diagnostic item for a lanthi/lasso/sacti/thiopeptide BGC.
    # motifs is a dict keyed by locus → list of dicts carrying 'core'.
    seen=0; dropped=[]
    for rec in _records(raw):
        for modname in ("lanthipeptides","lassopeptides","sactipeptides","thiopeptides"):
            motifs=rec.get("modules",{}).get(f"antismash.modules.{modname}",{}).get("motifs",{})
            if not isinstance(motifs,dict): continue
            for locus,mlist in motifs.items():
                for mt in (mlist if isinstance(mlist,list) else [mlist]):
                    if not isinstance(mt,dict): continue
                    core=mt.get("core") or mt.get("core_sequence") or ""
                    if core:
                        seen+=1
                        # v9.7.374: was a bare `core not in pkg_blob` substring check -- the exact
                        # false-conservation shape the v9.7.115 fix closed for NRPS substrates ('pip'
                        # bare-matching inside 'pipeline'). A short RiPP core peptide (a handful of
                        # residues is biologically normal) can bare-substring-match inside an unrelated
                        # locus tag or other field and be reported "conserved" even when the record was
                        # entirely dropped from the package. Use the same word-bounded check already
                        # used by check_nrps_substrates/check_product_class.
                        if not _token_in_blob(core, pkg_blob):
                            dropped.append(f"{modname} {mt.get('peptide_subclass','')} core @ {locus}")
    return "RiPP core-peptide sequences", seen, dropped


CHECKS = [check_tigrfam, check_nrps_substrates, check_active_site,
          check_product_class, check_ripp_cores]


def audit(raw_path, pkg_path):
    with open(raw_path, encoding='utf-8') as fh:
        raw = json.load(fh)
    with open(pkg_path, encoding='utf-8') as fh:
        pkg_blob = json.dumps(json.load(fh))
    emit("=== EVIDENCE CONSERVATION AUDIT ===", f"raw:     {raw_path}", f"package: {pkg_path}\n", sep="\n")
    failed=False; ran=0
    for chk in CHECKS:
        name, seen, dropped = chk(raw, pkg_blob)
        if seen==0:
            emit(f"[ -- ] {name}: none present in raw (nothing to conserve)")
            continue
        ran+=1
        n_drop = len(dropped) if isinstance(dropped,(list,set)) else dropped
        if n_drop: failed=True
        status = "OK" if not n_drop else "DROPPED"
        kept = seen - n_drop
        emit(f"[{status:7s}] {name}: {kept}/{seen} conserved")
        for d in list(dropped)[:8]:
            emit(f"            lost: {d}")
    emit(f"\nCategories checked with content: {ran}/{len(CHECKS)}")
    emit("RESULT:", "FAIL — diagnostic evidence dropped" if failed else "PASS")
    return 1 if failed else 0


if __name__ == "__main__":
    import argparse
    # v9.7.87 P2-args: accept named --raw / --package flags (the documented invocation was wrong
    # and only a bare 2-positional form worked). The positional form is kept for backward compat.
    ap = argparse.ArgumentParser(
        description="Evidence-conservation auditor: finds 'present in source, dropped in package' drops.")
    ap.add_argument("--raw", help="raw antiSMASH evidence JSON (source of truth)")
    ap.add_argument("--package", help="sealed Mamey package manifest/JSON to audit")
    ap.add_argument("positional", nargs="*",
                    help="legacy form: <raw_evidence.json> <package.json>")
    args = ap.parse_args()

    raw_path = args.raw
    pkg_path = args.package
    if raw_path is None and pkg_path is None and len(args.positional) == 2:
        raw_path, pkg_path = args.positional
    if not raw_path or not pkg_path:
        ap.error("provide both --raw <evidence.json> and --package <package.json> "
                 "(or two positional paths: <raw_evidence.json> <package.json>)")
    sys.exit(audit(raw_path, pkg_path))
