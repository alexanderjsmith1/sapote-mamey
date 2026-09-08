#!/usr/bin/env python3
"""mamey_intake.py — one-command intake for Mamey package outputs.

Default behavior when Mamey packages arrive: initialize a banked dir from scratch if none exists,
auto-derive each strain's WGS accession, ingest every package, then build the deep-data bank, the
per-BGC marker bank, the Lead_Board, and the master workbook FROM SCRATCH (no existing workbook
required). Prints an intake summary. A fresh chat with the bundle + one package runs only this.

Usage:
  python tools/mamey_intake.py --packages <dir-or-parent> [<dir2> ...] \
      --banked-dir <dir> --workbook <out.xlsx>

--packages may be individual package dirs OR a parent dir to scan recursively for snapshots.
--banked-dir is created/initialized if absent (use a PRIVATE dir for unpublished AS- strains).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, glob, json, os, re, subprocess, sys


def _read_json(_path, *, encoding="utf-8"):
    """P3b: context-managed JSON read; closes the handle a bare open() leaked."""
    import json as _json
    with open(_path, encoding=encoding) as _fh:
        _d = _json.load(_fh)
    # v9.7.400: a Project_Memory_Snapshot may be an alias STUB pointing at manifest.json
    # (the pre-.400 snapshot duplicated the whole manifest; see mamey/snapshot_alias.py).
    if (isinstance(_d, dict) and _d.get("alias_of") and "source_scans" not in _d
            and "Project_Memory_Snapshot" in os.path.basename(str(_path))):
        _mp = os.path.join(os.path.dirname(str(_path)) or ".", str(_d["alias_of"]))
        if os.path.isfile(_mp):
            with open(_mp, encoding=encoding) as _fh:
                return _json.load(_fh)
    return _d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _wbio import atomic_dump_json
HERE = os.path.dirname(os.path.abspath(__file__))

# empty banked structures (schema-matched) — written only if a file is absent
INIT = {
    "bgc_data.json":   {"strains": {}, "bgcs": []},
    "gene_data.json":  {"scan_agg": {}, "tfbs": {}, "substrates": [], "ripp": [], "domain_arch": []},
    "deep_data.json":  {"domain_hits": [], "active_sites": [], "class_pred": [],
                        "bgc_profile": [], "rggmci": {}, "rggmci_pairs": []},
    "rggmci_full.json": {}, "tigrfam.json": {}, "bgc_markers.json": {}, "strains.json": [],
}

def init_banked(banked):
    os.makedirs(banked, exist_ok=True)
    created = []
    for fn, empty in INIT.items():
        p = os.path.join(banked, fn)
        if not os.path.exists(p):
            atomic_dump_json(empty, p, indent=None); created.append(fn)
    return created

def find_snapshots(paths):
    """Each package dir -> its snapshot. Accept package dirs or a parent to scan."""
    snaps = {}
    for root in paths:
        for sp in glob.glob(os.path.join(root, "**", "*Project_Memory_Snapshot.json"), recursive=True):
            sid = re.search(r"SID\d+|AS-?\d+", os.path.basename(sp))
            sid = sid.group(0) if sid else os.path.basename(os.path.dirname(sp))
            if sid not in snaps:
                snaps[sid] = sp
    return snaps

def _load_accession_map(path):
    """Return {strain: accession} from CSV/TSV/JSON. No guessing."""
    if not path:
        return {}
    import csv
    if path.endswith(".json"):
        d = _read_json(path)
        return {str(k): str(v) for k, v in (d.items() if isinstance(d, dict) else [])}
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t" if path.endswith(".tsv") else ","))
    out = {}
    for r in rows:
        sid = r.get("strain") or r.get("strain_id") or r.get("sid")
        acc = r.get("ww") or r.get("wgs") or r.get("accession") or r.get("assembly_accession")
        if sid and acc:
            out[str(sid)] = str(acc)
    return out

def derive_ww(snap, accession_map=None):
    """Resolve WGS/assembly accession from explicit metadata only; never fabricate from contig names."""
    s = _read_json(snap)
    sid = s.get("strain_id") or os.path.basename(os.path.dirname(snap))
    if accession_map and sid in accession_map:
        return accession_map[sid]
    for key in ("ww", "wgs", "wgs_accession", "accession", "assembly_accession", "gca", "gcf"):
        val = s.get(key)
        if val:
            return str(val)
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--packages", nargs="+", required=True)
    ap.add_argument("--banked-dir", required=True)
    ap.add_argument("--workbook", required=True)
    ap.add_argument("--no-workbook", action="store_true", help="bank only; skip workbook build")
    ap.add_argument("--accession-map", default=None, help="CSV/TSV/JSON mapping strain -> explicit accession/WW; required when snapshots lack accession metadata")
    a = ap.parse_args()

    created = init_banked(a.banked_dir)
    if created:
        emit(f"[init] fresh banked dir created ({len(created)} files): {a.banked_dir}")

    snaps = find_snapshots(a.packages)
    accession_map = _load_accession_map(a.accession_map)
    banked = set(_read_json(os.path.join(a.banked_dir, "bgc_data.json"))["strains"])
    todo = {sid: sp for sid, sp in snaps.items() if sid not in banked}
    emit(f"[discover] {len(snaps)} package(s) found; {len(todo)} new to bank "
          f"({len(snaps)-len(todo)} already banked)")

    for sid, sp in sorted(todo.items()):
        ww = derive_ww(sp, accession_map)
        if not ww:
            emit(f"  ! {sid}: no explicit accession/WW in snapshot or --accession-map — SKIPPED (no fabricated accession)"); continue
        pkg = os.path.dirname(sp)
        r = subprocess.run([sys.executable, os.path.join(HERE, "ingest_package.py"),
                            "--package", pkg, "--ww", ww, "--merge", "--banked-dir", a.banked_dir],
                           capture_output=True, text=True)
        line = (r.stdout.strip().splitlines() or [r.stderr.strip()[-120:]])[-1]
        emit(f"  + {sid} [{ww}] {line}")

    if a.no_workbook:
        n = len(_read_json(os.path.join(a.banked_dir, "bgc_data.json"))["strains"])
        emit(f"[done] banked dir now holds {n} strains (workbook skipped)"); return

    emit("[build] generating workbook from scratch (deep bank -> marker bank -> Lead_Board)...")
    env=dict(os.environ, MAMEY_PACKAGES=os.pathsep.join(os.path.abspath(p) for p in a.packages))
    r = subprocess.run([sys.executable, os.path.join(HERE, "build_workbook.py"),
                        "--workbook", a.workbook, "--banked-dir", a.banked_dir, "--full"],
                       capture_output=True, text=True, env=env)
    for ln in r.stdout.strip().splitlines()[-6:]:
        emit("   ", ln)
    if r.returncode != 0:
        emit("   ! build error:", r.stderr.strip()[-300:])

    # intake summary
    bgc = _read_json(os.path.join(a.banked_dir, "bgc_data.json"))
    emit(f"\n=== INTAKE SUMMARY ===\n  strains: {len(bgc['strains'])} | BGCs: {len(bgc['bgcs'])}", f"  workbook: {a.workbook}", f"  banked-dir: {a.banked_dir}", sep="\n")
    if any(re.match(r'AS-?\d+', s) for s in bgc['strains']):
        emit("  NOTE: AS- strains present — keep this banked dir PRIVATE; never ship in a public release.")

if __name__ == "__main__":
    main()
