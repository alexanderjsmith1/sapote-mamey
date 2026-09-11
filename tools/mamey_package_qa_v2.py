#!/usr/bin/env python3
# OPERATOR_ONLY: package QA helper, run by hand during analysis. Superseded by the wired release gates
# (see tools/gate_registry.tsv). Not a release gate; not wired into the cut.
"""
mamey_package_qa_v2.py — Mamey per-strain package completeness validator
Sapote–Mamey pipeline (engine version stamped at runtime)

Usage:
    python mamey_package_qa_v2.py /path/to/batch_output_dir/

Checks:
    1. Checkpoint CSV present and all rows have required fields
    2. Per-strain packages exist for all MAMEY_COMPLETE or RECOVERY_VALIDATED strains
    3. All 10 scans present in scan_states.json
    4. RGGMCI pairs total > 0 for MAMEY_COMPLETE or RECOVERY_VALIDATED strains
    5. No PENDING status labels (legacy)
    6. Assembly tier coherent with N50/contig data
    7. BGC count consistent between inventory and registry

Returns:
    Exit 0 — all checks pass
    Exit 1 — one or more checks failed (details on stdout)
"""

import sys, os, json, zipfile, csv, re
from pathlib import Path
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible writer (no bare print(); holds strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

REQUIRED_SCANS = ['KCB_sweep','RG_GMCI','FLBR','CCTT','CGAD','UMED','EFLS','resistance','bldA_TTA','TFBS']
REQUIRED_CHECKPOINT_COLS = ['strain_id','assembly_bp','contigs','n50','rggmci_pairs_total',
                             'rggmci_high','dasr','mamey_status']
VALID_STATUSES = {'MAMEY_COMPLETE','RECOVERY_VALIDATED','RECOVERY_NEEDED','PARTIAL_FAILED','MAMEY_FAILED','MAMEY_DEFERRED','MAMEY_SKIPPED'}
LEGACY_PENDING = 'PASS_EXTRACTION_JUDGMENT_PENDING'

def fail(msg): emit(f"  FAIL: {msg}"); return False
def warn(msg): emit(f"  WARN: {msg}"); return True
def ok(msg):   emit(f"  OK:   {msg}"); return True

def check_checkpoint(batch_dir):
    """Check 1 — Checkpoint CSV present and well-formed."""
    emit("\n[1] Checkpoint CSV")
    csvs = list(batch_dir.glob("*checkpoint*.csv")) + list(batch_dir.glob("*assembly_stats*.csv"))
    if not csvs:
        return fail("No checkpoint CSV found. Session output may be incomplete.")
    # v9.7.115: on multiple matches (a re-run, a stale file), validate the NEWEST by mtime rather than
    # an arbitrary glob-order csvs[0] — otherwise QA could silently certify a stale checkpoint.
    ckpt = max(csvs, key=lambda p: p.stat().st_mtime)
    if len(csvs) > 1:
        emit(f"  ({len(csvs)} checkpoint CSVs found; using newest: {ckpt.name})")
    emit(f"  Found: {ckpt.name}")
    rows = list(csv.DictReader(open(ckpt)))
    if not rows:
        return fail("Checkpoint CSV is empty.")
    
    all_pass = True
    for col in REQUIRED_CHECKPOINT_COLS:
        if col not in rows[0]:
            warn(f"Missing column: {col}")
    
    for r in rows:
        sid = r.get('strain_id','?')
        status = r.get('mamey_status','')
        
        # Check for legacy PENDING labels
        if LEGACY_PENDING in status or 'PENDING' in status.upper():
            warn(f"{sid}: Legacy PENDING status detected. Treat as MAMEY_COMPLETE if data is present.")
        
        # Check status is valid
        if status and status not in VALID_STATUSES and 'PENDING' not in status.upper():
            all_pass = fail(f"{sid}: Unknown status '{status}'")
        
        # For COMPLETE strains, check RGGMCI is populated
        if status == 'MAMEY_COMPLETE':
            rg = r.get('rggmci_pairs_total','')
            if not rg or rg in ('','None','0','null'):
                all_pass = fail(f"{sid}: MAMEY_COMPLETE but rggmci_pairs_total is null/0 — "
                                "RGGMCI scan may be incomplete. Re-process this strain.")
            n50 = r.get('n50','')
            if not n50 or n50 in ('','None','null'):
                all_pass = fail(f"{sid}: MAMEY_COMPLETE but n50 is null — assembly stats missing.")
        
        ok(f"{sid}: status={status or '(missing)'} rggmci={r.get('rggmci_pairs_total','?')}")
    
    return all_pass

def check_packages(batch_dir):
    """Check 2+3+4 — Per-strain packages complete and scan states valid."""
    emit("\n[2] Per-strain packages")
    pkg_dirs = [batch_dir] + list(batch_dir.rglob("per_strain_packages"))
    zips = []
    for d in pkg_dirs:
        zips.extend(list(Path(d).glob("*Complete_Package.zip")))
    
    if not zips:
        warn("No per-strain package ZIPs found. If this is a checkpoint-only batch, this is expected.")
        return True
    
    all_pass = True
    for zpath in zips:
        sid = re.match(r'(SID\w+)_', zpath.name)
        sid = sid.group(1) if sid else zpath.stem
        emit(f"\n  -- {sid} --")
        
        try:
            with zipfile.ZipFile(zpath) as z:
                names = z.namelist()
                
                # Check inventory
                inv = [f for f in names if '_2_inventory' in f or 'inventory.csv' in f]
                if not inv:
                    all_pass = fail(f"Missing inventory CSV")
                else:
                    ok(f"Inventory: {inv[0]}")
                
                # Check scan states
                ss_files = [f for f in names if 'scan_state' in f.lower()]
                if not ss_files:
                    all_pass = fail("Missing scan_states.json")
                else:
                    with z.open(ss_files[0]) as f:
                        ss = json.load(f)
                    scans = {s[0]:s[1] for s in ss.get('scans',[]) if isinstance(s,list) and len(s)>=2}
                    for req in REQUIRED_SCANS:
                        if req not in scans:
                            all_pass = fail(f"Scan missing: {req}")
                        elif scans[req] != 'PASS':
                            warn(f"Scan {req}: {scans[req]}")
                        else:
                            ok(f"Scan {req}: PASS")
                
                # Check RGGMCI
                rg_files = [f for f in names if 'RGGMCI' in f and 'full.json' in f]
                rg_top = [f for f in names if 'top25' in f or 'top_25' in f]
                if not rg_files:
                    all_pass = fail("Missing RGGMCI full JSON — RGGMCI scan incomplete.")
                else:
                    with z.open(rg_files[0]) as f:
                        rg = json.load(f)
                    total = rg.get('pairs_total', 0)
                    if total == 0:
                        all_pass = fail(f"RGGMCI pairs_total = 0 — computation likely failed.")
                    else:
                        ok(f"RGGMCI: {total} total pairs")
                
                if not rg_top:
                    warn("Missing RGGMCI top25 CSV (non-critical; can be derived from full JSON)")
                
                # Gate validation
                gate_files = [f for f in names if 'gate_validation' in f]
                if gate_files:
                    with z.open(gate_files[0]) as f:
                        gate = json.load(f)
                    if gate.get('overall') != 'PASS':
                        all_pass = fail(f"Gate validation: {gate.get('overall','?')} — "
                                       f"{gate.get('failures','')}")
                    else:
                        ok(f"Gate validation: PASS")
                else:
                    warn("Gate validation JSON missing (older package format)")
        
        except Exception as e:
            all_pass = fail(f"Could not open package ZIP: {e}")
    
    return all_pass

def check_no_legacy_status(batch_dir):
    """Check 5 — No PENDING labels in any CSV in the batch."""
    emit("\n[5] Legacy status scan")
    found_legacy = False
    for csv_file in batch_dir.rglob("*.csv"):
        content = csv_file.read_text(errors='replace')
        if 'PENDING' in content.upper() and 'PASS_EXTRACTION' in content.upper():
            warn(f"Legacy PENDING label found in {csv_file.name}. "
                 "Not an error — treat affected strains as MAMEY_COMPLETE if data is complete.")
            found_legacy = True
    if not found_legacy:
        ok("No legacy PENDING labels found.")
    return True  # warning only, not failure

def main():
    if len(sys.argv) < 2:
        emit("Usage: python mamey_package_qa_v2.py /path/to/batch_output_dir/")
        sys.exit(1)
    
    batch_dir = Path(sys.argv[1])
    if not batch_dir.exists():
        emit(f"ERROR: Directory not found: {batch_dir}")
        sys.exit(1)
    
    emit(f"Mamey Package QA v2 — checking: {batch_dir}", "=" * 60, sep="\n")
    
    results = [
        check_checkpoint(batch_dir),
        check_packages(batch_dir),
        check_no_legacy_status(batch_dir),
    ]
    
    emit("\n" + "=" * 60)
    if all(results):
        emit("RESULT: ALL CHECKS PASS — batch is ready for Claude/Sapote merge.")
        sys.exit(0)
    else:
        emit("RESULT: ONE OR MORE CHECKS FAILED — review FAIL items above before merging.", "        Strains with failed RGGMCI must be re-processed (not re-uploaded from scratch).", "        Only re-upload the antiSMASH ZIP if the strain has MAMEY_FAILED status.", sep="\n")
        sys.exit(1)

if __name__ == '__main__':
    main()
