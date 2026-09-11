#!/usr/bin/env python3
"""build_cohort_precompute.py — Part A: one cohort-wide table per fact-type (v9.7.224).

Consolidates the per-strain precompute sources under a runs/sources dir into the cohort tables that
Mode B cards and the cross-strain analysis all cite. Deterministic; similarity-level; node·region via
`assembly_locator`. AS-XXX (moss) is expected already-excluded from the sources dir; AS-XXX/AS-XXX are
flagged `co_assembly=True` and held out of rankings. AS-XXX/AS-XXX legitimately lack nrps_prediction —
the command WARNS, does not fail.

This is the engine of `mamey cohort-precompute`; the passthrough tables already carry Strain +
Assembly_Locator, so those are concatenations. The tally's `assembly_locator` is read from
`list_bgcs.json` when present (Part B makes `list-bgcs --json` emit it natively); for pre-Part-B dumps it
is recovered for modular BGCs by joining the domain sources' Assembly_Locator (non-modular BGCs then
carry a blank locator + a warning — regenerate list_bgcs.json post-Part-B to fill them).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, csv, glob, json, os, sys
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


# Co-assembly pairs are cohort-specific data, not shipped in the code tier.
try:
    from mamey.exclusions import official_data_json as _official_data_json
    CO_ASSEMBLY = set(_official_data_json("co_assembly.json", {}).get("strains", []))
except Exception:  # pragma: no cover - standalone use without mamey
    CO_ASSEMBLY = set()


def _strain_dirs(root):
    return sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d))


# v9.7.277: cohort sources are baked into the package at package/cohort_source/. Resolve them
# across the layouts a shared package can arrive in (extracted package = <strain>/cohort_source/;
# raw run output = <strain>/package/cohort_source/), falling back to the legacy strain-root layout.
_SRC_SUBDIRS = ("cohort_source", os.path.join("package", "cohort_source"), "", "package")


def _resolve(d, fname):
    for sub in _SRC_SUBDIRS:
        p = os.path.join(d, sub, fname) if sub else os.path.join(d, fname)
        if os.path.isfile(p):
            return p
    return None


def _resolve_glob(d, pattern):
    for sub in _SRC_SUBDIRS:
        base = os.path.join(d, sub) if sub else d
        hits = sorted(glob.glob(os.path.join(base, pattern)))
        if hits:
            return hits
    return []


def _concat(strain_dirs, fname, out_csv):
    """Passthrough: sources already carry Strain + Assembly_Locator -> concatenate, one header."""
    rows, header = [], None
    for d in strain_dirs:
        p = _resolve(d, fname)
        if not p:
            continue
        with open(p, encoding="utf-8") as fh:
            r = csv.reader(fh)
            h = next(r, None)
            if h and header is None:
                header = h
            for row in r:
                rows.append(row)
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = _SafeWriter(fh)
        if header:
            w.writerow(header)
        w.writerows(rows)
    return len(rows)


def _locus_to_bgc(strain_dir):
    """locus_tag -> (bgc_id, assembly_locator) via the module_summary module_domains field."""
    m = {}
    p = _resolve(strain_dir, "antismash_module_summary_by_bgc.csv")
    if not p:
        return m
    for r in csv.DictReader(open(p, encoding="utf-8")):
        bid = r.get("BGC_ID", ""); loc = r.get("Assembly_Locator", "")
        for tok in (r.get("module_domains", "") or "").replace(";", " ").split():
            mm = tok
            # tokens look like nrpspksdomains_ctg1_79_AMP-binding.1 -> capture ctgN_M
            import re
            g = re.search(r"(ctg\d+_\d+)", mm)
            if g:
                m[g.group(1)] = (bid, loc)
    return m


def build_nrps(strain_dirs, out_csv):
    cols = ["strain", "bgc_id", "node_region", "locus_tag", "domain", "stachelhaus_signature",
            "substrate", "consensus_substrate", "stachelhaus_substrate",
            "prediction_agreement_state", "prediction_disposition", "confidence",
            "substrate_class_or_alts", "provenance"]
    n = 0; warned = []
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols); w.writeheader()
        for d in strain_dirs:
            strain = os.path.basename(d)
            pred = _resolve_glob(d, "*_nrps_prediction.csv")
            if not pred:
                warned.append(strain); continue
            l2b = _locus_to_bgc(d)
            for r in csv.DictReader(open(pred[0], encoding="utf-8")):
                # keep all monomer-selecting domains: NRPS_A (adenylation) + PKS_AT (acyltransferase) = golden set
                lt = r.get("locus_tag", "")
                bid, loc = l2b.get(lt, ("", ""))
                w.writerow({"strain": strain, "bgc_id": bid,
                            "node_region": r.get("record_id", ""), "locus_tag": lt,
                            "domain": r.get("domain_id", ""), "stachelhaus_signature": r.get("signature", ""),
                            "substrate": r.get("substrate", ""),
                            "consensus_substrate": r.get("consensus_substrate", ""),
                            "stachelhaus_substrate": r.get("stachelhaus_substrate", r.get("substrate", "")),
                            "prediction_agreement_state": r.get("prediction_agreement_state", ""),
                            "prediction_disposition": r.get("prediction_disposition", ""),
                            "confidence": r.get("confidence", ""),
                            "substrate_class_or_alts": r.get("class_or_alternatives", ""),
                            "provenance": "antismash_nrps_prediction"})
                n += 1
    if warned:
        emit(f"  WARN: no nrps_prediction for {', '.join(warned)} (legitimate for AS-XXX)", file=sys.stderr)
    return n


def _resistance_coupling(d):
    """bgc_id -> resistance genes for a strain package.

    Prefers a standalone resistance_gene_summary.json; falls back to the
    resistance_gene_summary block already carried in manifest.json (models.py
    injects it), so the COHORT_resistance_signals table fills from a sealed
    gold package alone (closes the v9.7.277 known gap for that table).
    """
    p = _resolve(d, "resistance_gene_summary.json")
    if p:
        return (_read_json(p, encoding="utf-8") or {}).get("bgc_coupling", {}) or {}
    m = _resolve(d, "manifest.json")
    if m:
        rgs = (_read_json(m, encoding="utf-8") or {}).get("resistance_gene_summary", {}) or {}
        return rgs.get("bgc_coupling", {}) or {}
    return {}


def _bgc_entries(d):
    """list-bgcs records for a strain package, for the BGC_FULL_TALLY table.

    Prefers a standalone list_bgcs.json; falls back to the sealed package's
    *_4_triage_board.csv via the engine's canonical builder
    (mamey.package_inspector.bgc_json_list_from_board) — same schema as
    `mamey list-bgcs --json`, no re-run. Closes the v9.7.277 known gap for
    package-only inputs without hand-rolling the mapping here.
    """
    p = _resolve(d, "list_bgcs.json")
    if p:
        return _read_json(p, encoding="utf-8")
    boards = _resolve_glob(d, "*_4_triage_board.csv")
    if not boards:
        return []
    try:
        _root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if _root not in sys.path:
            sys.path.insert(0, _root)
        from mamey.package_inspector import bgc_json_list_from_board
        return bgc_json_list_from_board(boards[0])
    except Exception as e:  # pragma: no cover - defensive
        emit(f"  WARN: could not build BGC list for {os.path.basename(d)} "
              f"from triage board: {e}", file=sys.stderr)
        return []


def build_resistance(strain_dirs, out_csv):
    n = 0
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=["strain", "bgc_id", "resistance_genes", "provenance"])
        w.writeheader()
        for d in strain_dirs:
            strain = os.path.basename(d)
            coupling = _resistance_coupling(d)
            if not coupling:
                continue
            for bid, genes in coupling.items():
                w.writerow({"strain": strain, "bgc_id": bid,
                            "resistance_genes": "; ".join(genes) if isinstance(genes, list) else str(genes),
                            "provenance": "antiSMASH/ARTS resistance scan (similarity-level)"})
                n += 1
    return n


def build_tally(strain_dirs, out_csv, genus_map):
    cols = ["strain", "genus", "bgc_id", "node_id", "assembly_locator", "products", "boundary",
            "ab_score", "af_score", "novelty_auto", "lead_tier", "cctt_triggers", "kcb_top",
            "depth_floor", "standing_rule", "primary_metab", "co_assembly"]
    n = 0; missing_loc = 0
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader()
        for d in strain_dirs:
            strain = os.path.basename(d)
            l2b = {}  # bgc_id -> assembly_locator, from domain sources (modular BGCs)
            for src in ("antismash_module_summary_by_bgc.csv", "ordered_domain_architectures_by_bgc.csv",
                        "domain_role_counts_by_bgc.csv", "domain_safe_unsafe_claims.csv"):
                p = os.path.join(d, src)
                if os.path.isfile(p):
                    for r in csv.DictReader(open(p, encoding="utf-8")):
                        if r.get("BGC_ID") and r.get("Assembly_Locator"):
                            l2b[r["BGC_ID"]] = r["Assembly_Locator"]
            entries = _bgc_entries(d)
            if not entries:
                continue
            for e in entries:
                loc = e.get("assembly_locator") or l2b.get(e.get("bgc_id", ""), "")
                if not loc:
                    missing_loc += 1
                row = dict(e)
                row.update({"strain": strain, "genus": genus_map.get(strain, ""),
                            "assembly_locator": loc, "co_assembly": strain in CO_ASSEMBLY})
                w.writerow(row); n += 1
    if missing_loc:
        emit(f"  WARN: {missing_loc} tally BGCs have no assembly_locator (non-modular, pre-Part-B "
              f"list_bgcs.json) — regenerate list_bgcs.json post-Part-B to fill them", file=sys.stderr)
    return n


def _genus_map():
    """strain -> genus from the bundle's canonical Master_Strain_Table (16S)."""
    m = {}
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tbl = os.path.join(here, "docs", "reference", "Master_Strain_Table_Hymenoptera_2026-07-05.csv")
    if os.path.isfile(tbl):
        for r in csv.DictReader(open(tbl, encoding="utf-8")):
            sid = (r.get("Strain Number", "") or "").strip()
            g = (r.get("Genus (16S)", "") or "").strip().split()[0] if r.get("Genus (16S)") else ""
            if sid:
                m[sid] = g
    else:
        # v9.7.374 fix (AUDIT_374): this literal path does not exist anywhere in the
        # bundle -- `if os.path.isfile(tbl)` was silently False on every real invocation, so
        # build_tally()'s `genus` column has been unconditionally blank for the entire cohort in
        # every COHORT_BGC_FULL_TALLY.csv this tool has ever written, with no signal to the
        # caller. The sibling `missing_loc` check a few lines above this function already WARNs
        # on its own partial-data condition; this one had no equivalent. Warn the same way so a
        # real run surfaces the gap instead of silently shipping an all-blank genus column.
        emit(f"  WARN: canonical Master_Strain_Table not found at {tbl} -- "
              f"'genus' column will be blank for every strain", file=sys.stderr)
    return m


def _emit_version_and_manifest(out_dir, counts, n_strains):
    """Save-data protocol: a fresh chat must be able to validate the store on load. VERSION.json carries
    provenance + row counts; MANIFEST.csv carries per-file rows+bytes for an integrity check."""
    import json, csv as _csv, datetime, hashlib
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ver = eng = "?"
    try:
        for line in open(os.path.join(here, "BUILD_STAMP.txt"), encoding="utf-8"):
            if line.startswith("version="):
                ver = line.split("=", 1)[1].strip()
    except Exception:
        pass
    manifest = []
    for fn in counts:
        p = os.path.join(out_dir, fn)
        b = os.path.getsize(p) if os.path.exists(p) else 0
        manifest.append({"file": fn, "rows": counts[fn], "bytes": b})
    with open(os.path.join(out_dir, "MANIFEST.csv"), "w", newline="", encoding="utf-8") as fh:
        w = _SafeDictWriter(fh, fieldnames=["file", "rows", "bytes"]); w.writeheader(); w.writerows(manifest)
    json.dump({"layer": "cohort_precompute", "bundle_version": ver,
               "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "n_strains": n_strains, "tables": counts,
               "join_key": "assembly_locator ({contig} {region}); BGC_ID is NOT portable across runs"},
              open(os.path.join(out_dir, "VERSION.json"), "w"), indent=2)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Part A: consolidate per-strain precompute sources into cohort tables.")
    ap.add_argument("--runs-dir", required=True, help="dir of <strain>/ source subdirs (cohort_sources)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    sd = _strain_dirs(a.runs_dir)
    gm = _genus_map()
    counts = {
        "COHORT_module_architecture_by_bgc.csv": _concat(sd, "antismash_module_summary_by_bgc.csv", os.path.join(a.out, "COHORT_module_architecture_by_bgc.csv")),
        "COHORT_domain_architecture_by_bgc.csv": _concat(sd, "ordered_domain_architectures_by_bgc.csv", os.path.join(a.out, "COHORT_domain_architecture_by_bgc.csv")),
        "COHORT_domain_roles_by_bgc.csv": _concat(sd, "domain_role_counts_by_bgc.csv", os.path.join(a.out, "COHORT_domain_roles_by_bgc.csv")),
        "COHORT_domain_claim_ceiling_by_bgc.csv": _concat(sd, "domain_safe_unsafe_claims.csv", os.path.join(a.out, "COHORT_domain_claim_ceiling_by_bgc.csv")),
        "COHORT_nrps_adomain_substrates.csv": build_nrps(sd, os.path.join(a.out, "COHORT_nrps_adomain_substrates.csv")),
        "COHORT_resistance_signals_by_bgc.csv": build_resistance(sd, os.path.join(a.out, "COHORT_resistance_signals_by_bgc.csv")),
        "COHORT_BGC_FULL_TALLY.csv": build_tally(sd, os.path.join(a.out, "COHORT_BGC_FULL_TALLY.csv"), gm),
    }
    _emit_version_and_manifest(a.out, counts, len(sd))
    for k, v in counts.items():
        emit(f"  {k}: {v} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
