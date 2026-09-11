#!/usr/bin/env python3
"""Backfill architecture_signature + refresh observed markers/genus into the reference library from antiSMASH zips.

Re-run the reference-panel ledger over a directory of antiSMASH zips and patch the
OBSERVED/COMPUTED fields back into mamey/data/reference_bgc_library.json:

  - architecture_signature  {region, pks_ks, nrps_c, nrps_a, markers, size_kb, edge}
  - found_markers / expected_marker_set   (refreshed from the live T43 scan)
  - found_size_kb
  - genus                   (only if currently UNRESOLVED and the GBK supplies one)

CURATED fields are never touched: class, class_lit, expected_bioactivity(_lit),
core_genes, lit_diagnostic_genes, source_doi, deposit_doi, caveat, ref_role,
kcb_anchor_observed, aliases, marker_set_source.

Entries with no matching zip in the directory are left exactly as-is and reported.
Nothing is fabricated: a signature is only written when its source antiSMASH output
is present.

Usage:
  python tools/backfill_reference_signatures.py <zip_dir> [--lib PATH] [--force] [--dry-run]

  <zip_dir>     directory of antiSMASH .zip outputs (filenames should contain the
                accession, e.g. *_BGC0000082.zip or *_MF055656.zip)
  --lib PATH    library JSON (default: mamey/data/reference_bgc_library.json)
  --force       overwrite an existing architecture_signature (default: fill-missing
                + always refresh markers/size/genus)
  --dry-run     report what would change; write nothing
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, io, json, os, re, sys, zipfile


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        return _json.load(_fh)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reference_panel_ledger import ledger_for_zip  # reuse the canonical extractor

ACC_RE = re.compile(r'BGC\d+|[A-Z]{2}\d{6}')
T43_RE = re.compile(r'T43-[A-Z]+')
CURATED = {  # never overwritten
    "compound", "aliases", "class", "class_lit", "expected_bioactivity",
    "expected_bioactivity_lit", "core_genes", "lit_diagnostic_genes",
    "source_doi", "deposit_doi", "caveat", "ref_role", "kcb_anchor_observed",
    "marker_set_source", "accession", "mibig_accession", "expected_size_kb",
    "domain_motif_concordance", "gene_symbol_concordance", "hard_scan_verdict",
    "source",
}


def acc_from_name(path):
    m = ACC_RE.search(os.path.basename(path))
    return m.group(0) if m else None


def organism_from_zip(zip_path):
    try:
        with zipfile.ZipFile(zip_path) as z:
            gbks = [n for n in z.namelist() if n.endswith(".gbk") and "region" not in n] \
                   or [n for n in z.namelist() if n.endswith(".gbk")]
            if not gbks:
                return None
            txt = io.TextIOWrapper(z.open(gbks[0]), encoding="utf-8", errors="ignore").read()
        m = re.search(r'/organism="([^"]+)"', txt) or re.search(r'ORGANISM\s+([^\n]+)', txt)
        if not m:
            return None
        g = m.group(1).strip().split()[0]
        return None if g.lower() in {"symbiont", "uncultured", "bacterium", "candidatus"} else g
    except Exception:
        return None


def signature_from_row(row):
    markers = sorted(set(T43_RE.findall(row.get("cmp_t43_markers", "") or "")))
    return {
        "region": row["obs_region_type"],
        "pks_ks": int(row["obs_pks_ks"]),
        "nrps_c": int(row["obs_nrps_c"]),
        "nrps_a": int(row["obs_nrps_a"]),
        "markers": markers,
        "size_kb": float(row["obs_size_kb"]),
        "edge": row["obs_edge_status"],
    }, markers, float(row["obs_size_kb"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("zip_dir", help="directory of antiSMASH zips")
    ap.add_argument("--lib", default="mamey/data/reference_bgc_library.json")
    ap.add_argument("--force", action="store_true", help="overwrite existing architecture_signature")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isdir(args.zip_dir):
        sys.exit(f"not a directory: {args.zip_dir}")
    lib = _read_json(args.lib)
    key = next(k for k, v in lib.items() if isinstance(v, list))
    by_acc = {e.get("accession"): e for e in lib[key]}

    zips = sorted(glob.glob(os.path.join(args.zip_dir, "*.zip")))
    patched, filled_sig, refreshed_genus, no_match, multi, diverged = [], [], [], [], [], []
    for zp in zips:
        acc = acc_from_name(zp)
        if not acc or acc not in by_acc:
            no_match.append(os.path.basename(zp))
            continue
        rows = ledger_for_zip(zp)
        if not rows:
            no_match.append(os.path.basename(zp) + " (no BGC parsed)")
            continue
        if len(rows) > 1:
            multi.append(f"{os.path.basename(zp)} ({len(rows)} regions; using region with max size)")
            rows = [max(rows, key=lambda r: float(r["obs_size_kb"]))]
        e = by_acc[acc]
        sig, markers, size_kb = signature_from_row(rows[0])
        had_sig = "architecture_signature" in e
        if (not had_sig) or args.force:
            e["architecture_signature"] = sig
            if not had_sig:
                filled_sig.append(acc)
        # always refresh OBSERVED scan output (idempotent for already-correct entries)
        e["found_markers"] = markers
        # expected_marker_set is CURATED (literature answer key, see marker_set_source);
        # never overwrite it. A scan that diverges from it is reported below, not silently merged.
        if markers != (e.get("expected_marker_set") or []):
            diverged.append(f"{acc}: scan={markers} vs curated expected={e.get('expected_marker_set')}")
        e["found_size_kb"] = size_kb
        if e.get("genus") == "UNRESOLVED":
            g = organism_from_zip(zp)
            if g:
                e["genus"] = g
                refreshed_genus.append(f"{acc}->{g}")
        patched.append(acc)

    have_sig = sum(1 for e in lib[key] if "architecture_signature" in e)
    no_zip = [e.get("accession") for e in lib[key] if e.get("accession") not in {acc_from_name(z) for z in zips}]

    emit(f"library: {args.lib}  ({len(lib[key])} entries)", f"zips scanned: {len(zips)} in {args.zip_dir}", f"entries patched (matched a zip): {len(patched)}", f"  new architecture_signature filled: {len(filled_sig)} {filled_sig or ''}", f"  genus resolved from GBK: {refreshed_genus or 'none'}", sep="\n")
    if diverged:
        emit(f"  scan-vs-curated expected DIVERGENCES (preserved, review): {diverged}")
    if multi:
        emit(f"  multi-region zips (collapsed): {multi}")
    if no_match:
        emit(f"  zips with no library match (ignored): {no_match}")
    emit(f"architecture_signature coverage now: {have_sig}/{len(lib[key])}", f"entries still WITHOUT a local zip (cannot backfill here): {len(no_zip)}", sep="\n")
    if args.dry_run:
        emit("\n--dry-run: no file written.")
        return
    if patched:
        bak = args.lib + ".bak"
        _bak_tmp = bak + ".tmp"
        with open(_bak_tmp, "w", encoding="utf-8") as _f, open(args.lib, encoding="utf-8") as _lib:
            json.dump(json.load(_lib), _f, indent=2)
        os.replace(_bak_tmp, bak)
        _lib_tmp = args.lib + ".tmp"
        with open(_lib_tmp, "w") as _f:
            json.dump(lib, _f, indent=2)
        os.replace(_lib_tmp, args.lib)
        emit(f"\nwrote {args.lib} (backup -> {bak})")
    else:
        emit("\nno matching zips; nothing written.")


if __name__ == "__main__":
    main()
