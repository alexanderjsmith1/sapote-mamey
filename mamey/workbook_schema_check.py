#!/usr/bin/env python3
"""
workbook_schema_check.py — Validate a Sapote-Mamey master workbook against schema v1.1.

Usage:
    python workbook_schema_check.py <workbook.xlsx>

Returns JSON with pass/fail per sheet, missing sheets, column mismatches,
and row-count consistency checks. Exit code 0 = PASS, 1 = FAIL.

Both ChatGPT and Claude should run this on receipt before adding data,
and before handoff after modifying data.
"""
try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import sys
import json
import openpyxl

SCHEMA_VERSION = "v1.1"  # matches the FROZEN canonical contract (MASTER_SCHEMA_FROZEN_v1_1.md) and the
                         # master_workbook.py builder (which stamps H3 = "v1.1"). The v1.2 deterministic
                         # additions (D5 Fragment_Rescue_Tiers + Activity_Ref) are NOT part of the frozen
                         # contract and are only checked when explicitly requested (--v12).

# Cohorts at or above this strain count default to the fast structural validation path
# (sheets, headers, row counts, strain coverage) and skip the expensive per-row value
# re-validation, which is the documented >=26-strain timeout. Use --full to force deep checks.
LARGE_COHORT_THRESHOLD = 26

# Allowed Activity_Ref tags (schema v1.2). MUST mirror tools/build_dapr_rescue_sheets.py FRAMEWORK_REFS
# values — Activity_Ref is deterministic and may only contain a tag drawn from the framework map.
FRAMEWORK_ACTIVITY_TAGS = frozenset({
    "VERIFIED aminoglycoside (textbook)", "VERIFIED formicamycin antibacterial",
    "VERIFIED surugamide", "VERIFIED Hood 1979; mSphere 2025",
    "VERIFIED clavulanic acid (S. clavuligerus)", "VERIFIED glycinocin",
    "VERIFIED Boeck 1990; Miao 2006", "VERIFIED spirotetronate", "VERIFIED Parenti 1978",
    "VERIFIED (S. avermitilis PteF)", "VERIFIED Gil 2003", "VERIFIED (S. noursei)",
    "VERIFIED Sakuda 1995", "VERIFIED Caffrey 2016", "VERIFIED Yu 2021 AEM",
    "antifungal-adjacent (cytotoxic)",
    "ROUTED-OUT cytotoxic (anthracycline)", "ROUTED-OUT cytotoxic (diazo)",
    "ROUTED-OUT cytotoxic (indolocarbazole)", "ROUTED-OUT cytotoxic (Hsp90 ansamycin)",
    "ROUTED-OUT cytotoxic (enediyne)", "ROUTED-OUT cytotoxic (aminoquinone)",
    "ROUTED-OUT ecological (siderophore)",
})

# Locked D5 Fragment_Rescue_Tiers columns + tier rule (schema v1.2).
D5_COLUMNS = ["Tier", "strain", "Assembly", "Contigs", "N50", "Frag_Loss",
              "EFLS_Pairs", "RG_GMCI_HIGH", "FLBR_Megasynth", "Recommendation"]


def _expected_tier(n50, efls):
    if n50 >= 1_000_000: return "A"
    if efls < 20: return "D"
    if efls >= 600: return "B"
    return "C"


def check_schema_v1_2(wb, results, fast=False):
    """Assert the schema-v1.2 deterministic additions are present and well-formed.

    fast=True keeps the structural checks (sheet presence, locked column headers) but skips the
    per-row value re-validation (tier recomputation, Activity_Ref tag membership), which is the
    expensive part on large cohorts. Row scans use iter_rows() streaming, not random .cell() access.
    """
    errs = []
    names = set(wb.sheetnames)
    # (1) Fragment_Rescue_Tiers (D5) present with locked columns
    if "Fragment_Rescue_Tiers" not in names:
        errs.append("Fragment_Rescue_Tiers (D5) missing")
    else:
        ws = wb["Fragment_Rescue_Tiers"]
        hdr = [str(c.value).strip() if c.value else None for c in ws[1]]
        if hdr[:len(D5_COLUMNS)] != D5_COLUMNS:
            errs.append(f"Fragment_Rescue_Tiers columns != locked v1.2 spec: got {hdr[:len(D5_COLUMNS)]}")
        elif not fast:
            ci = {c: i for i, c in enumerate(hdr)}
            for rn, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
                if not row or row[0] is None:
                    continue
                try:
                    tier = row[ci["Tier"]]; n50 = int(row[ci["N50"]] or 0); efls = int(row[ci["EFLS_Pairs"]] or 0)
                    if tier != _expected_tier(n50, efls):
                        errs.append(f"Fragment_Rescue_Tiers row {rn}: tier {tier} != locked rule ({_expected_tier(n50, efls)})")
                except (KeyError, ValueError, TypeError):
                    pass
    # (2) C1/C2 Activity_Ref present and drawn only from the framework map
    for sheet in ("C1_DAPR_Antibacterial", "C2_DAPR_Antifungal"):
        if sheet not in names:
            continue  # core check already reports DAPR sheet presence
        ws = wb[sheet]
        hdr = [str(c.value).strip() if c.value else None for c in ws[1]]
        if "Activity_Ref" not in hdr:
            errs.append(f"{sheet}: Activity_Ref column missing (schema v1.2)")
            continue
        if fast:
            continue
        col = hdr.index("Activity_Ref")
        for rn, cells in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if col >= len(cells):
                continue
            val = cells[col]
            if val not in (None, "") and val not in FRAMEWORK_ACTIVITY_TAGS:
                errs.append(f"{sheet} row {rn}: Activity_Ref '{val}' not in framework map")
    if errs:
        results["v1_2_errors"] = errs
        results["status"] = "FAIL"
    return results

# Column contract is DERIVED from the live builder's CANONICAL_V1_HEADERS (mamey/master_workbook.py)
# so the validator and the builder cannot drift apart. This is the F5 fix: the hand-copied TitleCase
# specs (inherited from the retired tools/build_master.py one-off) diverged from the builder's
# snake_case output and produced false column_errors on a correctly-built master. master_workbook.py
# does NOT import this module, so the top-level import is safe (no cycle).
#
# Dual-mode import: this file is documented as a bare script
# (`python workbook_schema_check.py <wb.xlsx>`) but also runs as part of the
# package (`python -m mamey.workbook_schema_check`). master_workbook.py uses
# intra-package relative imports (mamey.models, mamey.assembly, …), so it must
# be imported *as* mamey.master_workbook, not as a standalone module. We try the
# package-relative import first; if that fails (bare-script invocation, no parent
# package), we locate the directory that contains the `mamey/` package, put it on
# sys.path, and import via the package path so the inner relative imports resolve.
try:
    from .master_workbook import CANONICAL_V1_HEADERS as _BUILDER_HEADERS
except ImportError:
    import os as _os
    _here = _os.path.dirname(_os.path.abspath(__file__))
    # mamey/ copy run as a script: pkg root is the parent of this file's dir.
    # root-level copy run as a script: pkg root is this file's dir.
    for _root in (_os.path.dirname(_here), _here):
        if _os.path.exists(_os.path.join(_root, "mamey", "master_workbook.py")):
            if _root not in sys.path:
                sys.path.insert(0, _root)
            break
    from mamey.master_workbook import CANONICAL_V1_HEADERS as _BUILDER_HEADERS

# Validation type per sheet — drives only the (non-fatal) per-strain row-count consistency check and
# cohort-size routing. Sheets not listed default to "fixed" (no consistency coupling).
_SHEET_TYPE = {
    "A2_Strain_Registry": "per_strain",
    "A4_Completeness_Audit": "per_strain",
    "B1_BGC_Master": "per_bgc",
    "B4_Cross_Strain_Scans": "per_strain",
    "C1_DAPR_Antibacterial": "leads",
    "C2_DAPR_Antifungal": "leads",
    "D2_RGGMCI_Top_Pairs": "pairs",
    "F1_Ecology_Readiness": "per_strain",
}
# Sheets whose column set is DATA-DYNAMIC (width varies by cohort) — check leading column(s) only.
# B3 = one column per KCB top-hit reference, so its header list is not a fixed contract.
_DYNAMIC_PREFIX = {
    "B3_Known_Cluster_Matrix": ["strain"],
}

def _build_required_sheets():
    # A1_Dashboard is written separately by the builder (not in CANONICAL_V1_HEADERS) -> presence only.
    req = {"A1_Dashboard": {"min_cols": 1, "type": "fixed"}}
    # v9.7.163: B5_BLASTp_Hits is an ADDITIVE optional sheet (external NCBI BLASTp ingest),
    # not part of the frozen v1.1 contract — excluded from the required set so pre-B5 workbooks
    # still validate. It is checked only when present.
    _ADDITIVE = {"B5_BLASTp_Hits"}
    for sheet, headers in _BUILDER_HEADERS.items():
        if sheet in _ADDITIVE:
            continue
        if sheet in _DYNAMIC_PREFIX:
            req[sheet] = {"prefix": _DYNAMIC_PREFIX[sheet], "min_cols": 1,
                          "type": _SHEET_TYPE.get(sheet, "per_strain")}
        else:
            req[sheet] = {"columns": list(headers), "type": _SHEET_TYPE.get(sheet, "fixed")}
    return req

REQUIRED_SHEETS = _build_required_sheets()

# Planned/deferred coded sheets — documented in WORKBOOK_SCHEMA.md, NOT required in the deployed build.
# (Populated on demand: Sapote judgment / per-analysis / handoff sheets. BUILD-next: E3, G1, H3.)
OPTIONAL_SHEETS = [
    "A3_Run_Manifest", "C3_Lead_Tier_Summary", "C4_Strain_Decision_Table", "D3_RGGMCI_Promoted",
    "E1_Mode_B_Index", "E2_Comparative_Pairs", "E3_Megacluster_Registry", "E4_A_Domain_Summary",
    "F1_Ecology_Readiness", "F3_Ecology_Theme_Board", "G1_Literature_Index", "G2_Validation_Roles",
    "G3_Hallucination_Trap_Audit", "H1_Handoff_Log", "H2_Gap_Queue", "H3_Schema_Version",
]

# The sheets the master_workbook.py builder actually emits in a deployed build (the FROZEN v1.1
# contract): the coded A1-H3 set, 25 sheets. Presence of these is what `status: PASS` requires.
# Legacy descriptive names (About, Gene_*, BGC_*, TFBS_Motifs, TIGRFAM_Check, Fragment_Rescue_Tiers,
# Strain_*, Cross_Strain_*) predate the v1.1 coded-scheme migration and are intentionally NOT required;
# their column specs remain in REQUIRED_SHEETS only so that if such a sheet IS present it is still
# checked (the per-sheet loop skips any sheet that is absent).
CANONICAL_REQUIRED = set(REQUIRED_SHEETS)  # the 25 coded sheets the builder emits (auto-derived)

def validate(path, mode="auto", check_v12=False):
    results = {
        "file": path,
        "schema_version": SCHEMA_VERSION,
        "validation_mode": mode,
        "status": "PASS",
        "sheets_found": 0,
        "sheets_missing": [],
        "sheets_extra": [],
        "column_errors": [],
        "consistency_errors": [],
        "warnings": [],
    }

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        results["status"] = "FAIL"
        results["error"] = f"Cannot open workbook: {e}"
        return results

    # SCHEMA-P04: everything from here to the final close must run under try/finally so the
    # read_only zip handle is released even if a malformed workbook raises mid-validation.
    try:
        found = set(wb.sheetnames)
        expected = CANONICAL_REQUIRED  # what the deployed v1.1 builder emits

        results["sheets_found"] = len(found & expected)
        results["sheets_missing"] = sorted(expected - found)
        results["sheets_extra"] = sorted(found - expected - set(OPTIONAL_SHEETS))

        # F2 guard: a per-strain Mamey workbook (Strain_Summary / BGC_Inventory / RGGMCI_* …) shares none
        # of the coded master sheets. Don't report a misleading "0 found / FAIL" as if it were an empty
        # master — say plainly that this validator is master-only.
        if results["sheets_found"] == 0:
            results["status"] = "FAIL"
            results["error"] = ("No canonical master sheets found — this validator targets the master "
                                "workbook (coded A1-H3 scheme). Per-strain Mamey workbooks are not validated "
                                "by this tool.")
            results["sheets_present"] = sorted(found)
            return results

        if results["sheets_missing"]:
            results["status"] = "FAIL"

        # Determine cohort size cheaply (streamed) to pick the validation path.
        strain_n = 0
        if "A2_Strain_Registry" in found:
            for row in wb["A2_Strain_Registry"].iter_rows(min_row=2, max_col=1, values_only=True):
                if row[0]:
                    strain_n += 1
        results["strain_count"] = strain_n
        fast = (mode == "fast") or (mode == "auto" and strain_n >= LARGE_COHORT_THRESHOLD)
        results["validation_path"] = "fast-structural" if fast else "full-deep"
        if fast:
            results["warnings"].append(
                f"Fast structural validation used ({strain_n} strains >= {LARGE_COHORT_THRESHOLD}): "
                f"sheets, headers, row counts and strain coverage are checked; per-row value re-validation "
                f"(tier recomputation, Activity_Ref membership, A2<->B1 orphan scan) is skipped. Use --full to force.")

        strain_counts = {}

        for sheet_code, spec in REQUIRED_SHEETS.items():
            if sheet_code not in found:
                continue

            ws = wb[sheet_code]
            # SCHEMA-P03: in read_only mode openpyxl returns None for max_row/max_column when a
            # writer omits the stored <dimension>. `None + 1` / `None - 1` crashed the validator
            # (and, pre-P04, leaked the handle). Force a dimension scan, then floor at 0.
            if ws.max_row is None or ws.max_column is None:
                try:
                    ws.calculate_dimension(force=True)
                except Exception:
                    pass
            max_col = ws.max_column or 0
            max_row = ws.max_row or 0
            headers = [ws.cell(1, c).value for c in range(1, max_col + 1)]
            headers = [str(h).strip() if h else None for h in headers]
            headers_clean = [h for h in headers if h]
            data_rows = max_row - 1 if max_row > 1 else 0

            if "columns" in spec:
                expected_cols = spec["columns"]
                actual_cols = headers_clean[:len(expected_cols)]
                mismatches = []
                for i, (exp, act) in enumerate(zip(expected_cols, actual_cols)):
                    if exp.lower() != (act or "").lower():
                        mismatches.append({"position": i + 1, "expected": exp, "actual": act})
                if len(actual_cols) < len(expected_cols):
                    for i in range(len(actual_cols), len(expected_cols)):
                        mismatches.append({"position": i + 1, "expected": expected_cols[i], "actual": "MISSING"})
                if mismatches:
                    results["column_errors"].append({"sheet": sheet_code, "mismatches": mismatches})
                    results["status"] = "FAIL"
            elif "prefix" in spec:
                pre = spec["prefix"]
                actual_cols = headers_clean[:len(pre)]
                mismatches = []
                for i, (exp, act) in enumerate(zip(pre, actual_cols)):
                    if exp.lower() != (act or "").lower():
                        mismatches.append({"position": i + 1, "expected": exp, "actual": act})
                if len(actual_cols) < len(pre):
                    for i in range(len(actual_cols), len(pre)):
                        mismatches.append({"position": i + 1, "expected": pre[i], "actual": "MISSING"})
                if mismatches:
                    results["column_errors"].append({"sheet": sheet_code, "mismatches": mismatches})
                    results["status"] = "FAIL"
                if "min_cols" in spec and len(headers_clean) < spec["min_cols"]:
                    results["column_errors"].append({
                        "sheet": sheet_code,
                        "error": f"Expected >={spec['min_cols']} columns, found {len(headers_clean)}"})
                    results["status"] = "FAIL"
            elif "min_cols" in spec:
                if len(headers_clean) < spec["min_cols"]:
                    results["column_errors"].append({
                        "sheet": sheet_code,
                        "error": f"Expected ≥{spec['min_cols']} columns, found {len(headers_clean)}"
                    })

            if spec["type"] == "per_strain" and data_rows > 0:
                strain_counts[sheet_code] = data_rows

        # Consistency: per_strain sheets should have same row count
        per_strain_sheets = {k: v for k, v in strain_counts.items()
                              if REQUIRED_SHEETS.get(k, {}).get("type") == "per_strain"}
        if len(set(per_strain_sheets.values())) > 1:
            results["consistency_errors"].append({
                "error": "Per-strain sheet row counts differ",
                "counts": per_strain_sheets
            })
            results["warnings"].append("Row count mismatch across per-strain sheets — some strains may be missing from some sheets")

        # Check B1_BGC_Master strain set matches A2 (deep cross-check; skipped in fast mode)
        if not fast and "A2_Strain_Registry" in found and "B1_BGC_Master" in found:
            a2_strains = {str(row[0]).strip() for row in wb["A2_Strain_Registry"].iter_rows(min_row=2, max_col=1, values_only=True) if row[0]}
            b1_strains = {str(row[0]).strip() for row in wb["B1_BGC_Master"].iter_rows(min_row=2, max_col=1, values_only=True) if row[0]}
            orphan_a2 = a2_strains - b1_strains
            orphan_b1 = b1_strains - a2_strains
            if orphan_a2:
                results["consistency_errors"].append({
                    "error": "Strains in A2 but not in B1",
                    "strains": sorted(orphan_a2)
                })
            if orphan_b1:
                results["consistency_errors"].append({
                    "error": "Strains in B1 but not in A2",
                    "strains": sorted(orphan_b1)
                })

        # Schema v1.2 deterministic-additions check (D5 + Activity_Ref) — opt-in only; not part of the
        # frozen v1.1 contract, so a correct v1.1 master must not FAIL on its absence.
        if check_v12:
            check_schema_v1_2(wb, results, fast=fast)
    finally:
        wb.close()

    if results["column_errors"]:
        results["status"] = "FAIL"
    # WB-02 (v9.7.338 verdict-changing): the A2<->B1 orphan cross-check and the per-strain
    # row-count-mismatch check append to consistency_errors but previously never set
    # status=FAIL — only column/sheet errors flipped it. A structurally-broken master (a strain
    # present in A2_Strain_Registry but dropped from B1_BGC_Master, or per-strain sheets with
    # differing row counts) therefore validated as PASS/exit 0. Fail on any consistency error.
    if results.get("consistency_errors"):
        results["status"] = "FAIL"

    return results


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    mode = "auto"
    check_v12 = False
    if "--fast" in args: mode = "fast"; args.remove("--fast")
    if "--full" in args: mode = "full"; args.remove("--full")
    if "--v12" in args: check_v12 = True; args.remove("--v12")
    if not args:
        emit("Usage: python workbook_schema_check.py [--fast|--full] [--v12] <workbook.xlsx>", "  default 'auto': cohorts >= %d strains use the fast structural path." % LARGE_COHORT_THRESHOLD, "  --v12: additionally require the (non-frozen) v1.2 D5 Fragment_Rescue_Tiers + Activity_Ref additions.", sep="\n")
        sys.exit(1)

    result = validate(args[0], mode=mode, check_v12=check_v12)
    emit(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] == "PASS" else 1)
