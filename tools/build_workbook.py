#!/usr/bin/env python3
"""build_workbook.py — canonical master-workbook build orchestrator.

Runs the full post-extraction build sequence in the correct order so the deterministic
schema-v1.2 additions (D5 Fragment_Rescue_Tiers + C1/C2 Activity_Ref) regenerate on EVERY
build, not manually. Designed so that adding more genomes is a single command.

Sequence:
  1. build_master.py        (base workbook from banked per-strain data)        [optional, --build-master]
  2. add_xstrain_sheets.py  (cross-strain overlay sheets)                      [optional, --add-xstrain]
  3. build_dapr_rescue_sheets.py  (D5 + Activity_Ref, deterministic)          [ALWAYS]
  4. workbook_schema_check.py     (schema validation incl. v1.2 checks)        [ALWAYS unless --skip-validate]

Steps 1-2 are the user's build scripts (paths passed in); steps 3-4 ship with the bundle and
always run. If you only pass --workbook, it refreshes the deterministic sheets + validates an
existing workbook.

Usage:
  python tools/build_workbook.py --workbook master.xlsx \
      [--build-master path/to/build_master.py] [--add-xstrain path/to/add_xstrain_sheets.py] \
      [--skip-validate]
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, os, subprocess, sys, json

HERE = os.path.dirname(os.path.abspath(__file__))
DAPR_RESCUE = os.path.join(HERE, "build_dapr_rescue_sheets.py")
BUILD_MASTER = os.path.join(HERE, "build_master.py")
ADD_XSTRAIN  = os.path.join(HERE, "add_xstrain_sheets.py")
APPLY_BOARDS = os.path.join(HERE, "apply_dapr_boards.py")
LEAD_BOARD   = os.path.join(HERE, "lead_board.py")
BGC_MARKERS  = os.path.join(HERE, "build_bgc_markers.py")
DEEP_DATA    = os.path.join(HERE, "build_deep_data.py")
CHITINASE    = os.path.join(HERE, "build_chitinase_screen.py")
SACCHARIDE   = os.path.join(HERE, "build_saccharide_triage.py")
TFBS         = os.path.join(HERE, "build_tfbs_profile.py")
PRIORITY     = os.path.join(HERE, "build_priority_leads.py")
COHORT_DEF   = os.path.join(os.path.dirname(HERE), "cohort")
SCHEMA_CHECK = os.path.join(os.path.dirname(HERE), "mamey", "workbook_schema_check.py")


def run(label, cmd):
    emit(f"\n[build_workbook] {label}: {' '.join(cmd)}")
    r = subprocess.run(cmd)
    if r.returncode != 0:
        sys.exit(f"[build_workbook] FAILED at: {label} (exit {r.returncode})")


def validate_workbook(path, *, allow_schema_issues=False):
    """Run the deployed schema gate, including v1.2, and fail closed by default."""
    emit("\n[build_workbook] 6/6 schema validation")
    command = [sys.executable, SCHEMA_CHECK, "--v12", path]
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        report = json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        detail = result.stdout[-400:] or result.stderr[-400:] or "no validator output"
        raise SystemExit(f"[build_workbook] schema validator returned non-JSON output: {detail}") from exc

    v12 = report.get("v1_2_errors") or []
    core = bool(report.get("sheets_missing") or report.get("column_errors") or report.get("consistency_errors"))
    status_failed = report.get("status") != "PASS"
    process_failed = result.returncode != 0
    emit(f"  v1.2 deterministic additions (D5 + Activity_Ref): {'FAIL' if v12 else 'PASS'}")
    for error in v12:
        emit(f"    - {error}")
    emit(f"  core coded-schema match: {'FAIL' if core or status_failed else 'PASS'}")

    failed = process_failed or status_failed or core or bool(v12)
    if failed and not allow_schema_issues:
        raise SystemExit(
            "[build_workbook] FAILED at schema validation; use --allow-schema-issues only for an "
            "explicit diagnostic build that will not be shipped"
        )
    if failed:
        emit("[build_workbook] WARNING: schema issues explicitly admitted for a diagnostic-only build.")
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workbook", required=True, help="master workbook path")
    ap.add_argument("--build-master", nargs="?", const=BUILD_MASTER, help="build_master.py (default: bundled)")
    ap.add_argument("--add-xstrain", nargs="?", const=ADD_XSTRAIN, help="add_xstrain_sheets.py (default: bundled)")
    ap.add_argument("--banked-dir", default=COHORT_DEF, help="cohort banked-JSON dir (default: bundle/cohort)")
    ap.add_argument("--full", action="store_true", help="full rebuild: bundled build_master + add_xstrain + DAPR boards")
    ap.add_argument("--skip-validate", action="store_true")
    ap.add_argument(
        "--allow-schema-issues",
        action="store_true",
        help="diagnostic-only escape hatch: report schema failures without failing the command",
    )
    a = ap.parse_args()
    # --full => use bundled builders + banked-dir + restore DAPR boards
    if a.full:
        a.build_master = a.build_master or BUILD_MASTER
        a.add_xstrain = a.add_xstrain or ADD_XSTRAIN
        # Bank deep data + markers FIRST, so build_master/add_xstrain populate the deep sheets from
        # filled JSON. (On a fresh cohort deep_data.json starts empty; banking after the sheet build
        # would leave BGC_Scan_Profile / Domain_Architecture / Gene_Domain_Hits empty.)
        run("1z/6 full deep_data bank", [sys.executable, DEEP_DATA, a.banked_dir])
        run("1a/6 per-BGC marker bank", [sys.executable, BGC_MARKERS, a.banked_dir])

    if a.build_master:
        run("2/6 base build", [sys.executable, a.build_master, "--banked-dir", a.banked_dir, "--out", a.workbook])
    if a.add_xstrain:
        run("3/6 cross-strain overlays", [sys.executable, a.add_xstrain, "--banked-dir", a.banked_dir, "--out", a.workbook])
    # restore Sapote-layer DAPR boards if the cohort ships them (only meaningful on a full rebuild)
    if a.full and os.path.exists(os.path.join(a.banked_dir, "c1_dapr_antibacterial.csv")):
        run("4/6 restore DAPR boards", [sys.executable, APPLY_BOARDS, a.workbook, "--cohort", a.banked_dir])
    # always — the deterministic schema-v1.2 additions
    run("5/6 D5 + Activity_Ref (deterministic)", [sys.executable, DAPR_RESCUE, a.workbook])
    if a.full:
        run("5c/6 Chitinase ecology screen", [sys.executable, CHITINASE, "--workbook", a.workbook, "--banked-dir", a.banked_dir])
        run("5d/6 Saccharide triage", [sys.executable, SACCHARIDE, "--workbook", a.workbook, "--banked-dir", a.banked_dir])
        run("5e/6 TFBS regulator profile", [sys.executable, TFBS, "--workbook", a.workbook, "--banked-dir", a.banked_dir])
        run("5b/6 Lead_Board (per-strain ranked leads + primmet guard)", [sys.executable, LEAD_BOARD, "--workbook", a.workbook, "--banked-dir", a.banked_dir])
        run("5f/6 Priority leads", [sys.executable, PRIORITY, "--workbook", a.workbook, "--out-dir", os.path.dirname(a.workbook)])
    # Validation is a release gate. A build must not print "done" after a failed or
    # malformed validator result unless the operator explicitly requests a diagnostic-only run.
    if not a.skip_validate:
        validate_workbook(a.workbook, allow_schema_issues=a.allow_schema_issues)
    emit("\n[build_workbook] done.")


if __name__ == "__main__":
    main()
