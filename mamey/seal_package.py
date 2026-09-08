"""seal_package.py — one final-package validator that runs every QC gate together.

v9.7.125 (audit P0 / "one final sealing layer"). The individual gates already exist —
package validation, workbook populated-sheet gate, Mode B §1–§20 quality gate, locator
reconciliation, claim-safety linter. This composes them into a single pass so a partial
package cannot be called complete: the AS-XXX failure class.

Emits three artifacts into the output dir:
  - DEBUG_RECEIPT.md   — human-readable per-gate summary
  - seal_status.json   — machine-readable overall + per-gate status
  - seal_findings.csv   — one row per finding (gate / bgc / severity / detail)

Exit semantics (F05, v9.7.354 — CHANGED): a blocking gate failure makes the overall status FAIL
and exits 1 BY DEFAULT. Previously the default was report-only (exit 0), which let a real
claim-safety / locator / package FAIL pass silently through an automated cut.
  - default (no flags): blocking FAIL -> overall FAIL, exit 1.
  - --advisory        : report-only, exit 0, with a loud banner on the receipt. For humans
                        inspecting a work-in-progress package.
  - --strict          : always enforces (exit 1); retained for back-compat and overrides
                        --advisory.
Automation that depended on the old exit-0 default must add --advisory.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Make the bundled tools importable (claim_safety_linter, locator_reconciliation live in tools/).
_TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

# AUDIT_374: seal_status.json/seal_findings.csv/DEBUG_RECEIPT.md/figure_reference_
# validation.csv/deliverable_status_table.csv are written straight into the (already-sealed,
# by default -- see packaging.py's MUTABLE_RECEIPT_NAMES comment) package_dir. A crash mid-write
# used to leave whichever file was in flight truncated -- and seal_status.json is the
# machine-readable overall PASS/FAIL/WARN status downstream automation reads. Route every write
# in this module through the same crash-safe tmp+os.replace helpers already used for the
# analogous per-strain workbook/roster writes elsewhere in mamey/ this cut.
from _wbio import atomic_write_text, atomic_open


@dataclass
class GateResult:
    name: str
    status: str            # PASS | WARN | FAIL | SKIP
    blocking: bool         # does a failure here block a strict seal?
    findings: list[dict] = field(default_factory=list)
    detail: str = ""


def _triage_rows(package_dir: Path) -> dict[str, dict]:
    """Map BGC_ID -> triage row from the package triage board (or {})."""
    rows = {}
    boards = sorted(package_dir.glob("*_4_triage_board.csv"))
    if not boards:
        return rows
    try:
        with open(boards[0], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                bid = (row.get("BGC_ID") or "").strip()
                if bid:
                    rows[bid] = dict(row)
    except Exception:
        pass
    return rows


def _gate_package_validate(package_dir: Path) -> GateResult:
    try:
        from mamey.validate import validate_package
        # v9.7.409 (CLAUDE_409_sealpackage_mutation): seal-package is a read-only advisory QC
        # pass whose receipts are written OUTSIDE the package by write_receipts(out_dir). The
        # validate gate must therefore NOT rewrite package_status.json inside the sealed package
        # (which it did unconditionally, mutating it regardless of --out). write_status_receipt=
        # False keeps this gate a pure read; the status is still returned in-memory below.
        res = validate_package(package_dir, enrichment_check=True, write_status_receipt=False)
        status = str(res.get("status", "UNKNOWN"))
        ok = status.startswith("PASS") or status == "MAMEY_COMPLETE"
        return GateResult("package_validate", "PASS" if ok else "FAIL", True,
                          detail=status)
    except Exception as e:
        return GateResult("package_validate", "FAIL", True, detail=f"error: {e}")


def _gate_workbook(package_dir: Path) -> GateResult:
    try:
        from mamey.validate import validate_workbook_content
        xlsx = sorted(package_dir.glob("*_5_workbook.xlsx"))
        if not xlsx:
            return GateResult("workbook_content", "SKIP", False, detail="no workbook")
        res = validate_workbook_content(xlsx[0])
        findings = [{"bgc": "", "severity": "FAIL", "detail": f"{name}: {d['status']}"}
                    for name, d in res.get("sheets", {}).items()
                    if d["status"] != "PASS"]
        return GateResult("workbook_content", res["status"], True,
                          findings=findings, detail=res["status"])
    except Exception as e:
        return GateResult("workbook_content", "FAIL", True, detail=f"error: {e}")


def _gate_mode_b_quality(package_dir: Path, triage: dict) -> GateResult:
    try:
        from mamey.judgment_store import list_complete_bgcs, read_mode_b
        from mamey.mode_b_quality_gate import evaluate_card
    except Exception as e:
        return GateResult("mode_b_quality", "SKIP", False, detail=f"import: {e}")
    bgcs = list_complete_bgcs(package_dir)
    if not bgcs:
        return GateResult("mode_b_quality", "SKIP", False, detail="no filed cards")
    findings = []
    for bid in bgcs:
        card = read_mode_b(package_dir, bid)
        if not card:
            continue
        v = evaluate_card(bid, card)
        if v.tier not in ("FULL",):
            findings.append({"bgc": bid, "severity": "WARN",
                             "detail": f"tier={v.tier} ({v.message})"})
    status = "PASS" if not findings else "WARN"
    return GateResult("mode_b_quality", status, False, findings=findings,
                      detail=f"{len(bgcs)} cards, {len(findings)} below FULL")


def _gate_locator(package_dir: Path, triage: dict) -> GateResult:
    try:
        from mamey.judgment_store import list_complete_bgcs, read_mode_b
        from locator_reconciliation import reconcile_heading_only
    except Exception as e:
        return GateResult("locator_reconciliation", "SKIP", False, detail=f"import: {e}")
    bgcs = list_complete_bgcs(package_dir)
    if not bgcs:
        return GateResult("locator_reconciliation", "SKIP", False, detail="no filed cards")
    if not triage:
        # AUDIT_374: distinguish "no triage board file at all" (legitimate SKIP --
        # surfaced separately as a WARN by _gate_deliverable_status) from "triage board file
        # present but unparseable / zero usable BGC_ID rows" (the corrupt-CSV case already
        # documented in figures_smoke.py::_pick_source -- "a binary-byte parse that produces
        # garbage column names"). The latter must not silently defeat this blocking gate: a
        # wrong/unreadable node mapping is exactly what locator_reconciliation exists to catch
        # ("a wrong node propagates everywhere," per this gate's own comment below).
        boards = sorted(package_dir.glob("*_4_triage_board.csv"))
        if boards:
            return GateResult("locator_reconciliation", "FAIL", True,
                              detail=f"triage board present ({boards[0].name}) but unparseable "
                                     "or missing BGC_ID column -- locator cannot be reconciled")
        return GateResult("locator_reconciliation", "SKIP", False, detail="no triage board")
    try:
        manifest_data = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
        identity_strain = str(manifest_data.get("strain_id") or "").strip()
    except Exception:
        identity_strain = ""
    if not identity_strain:
        return GateResult(
            "locator_reconciliation", "FAIL", True,
            detail="manifest strain_id missing or unreadable -- exact four-part identity cannot be reconciled",
        )
    findings = []
    blocking_hit = False
    for bid in bgcs:
        card = read_mode_b(package_dir, bid)
        if not card:
            continue
        row = dict(triage.get(bid, {}))
        if not row:
            continue
        row["Strain"] = identity_strain
        v = reconcile_heading_only(card, row)
        if v["status"] in ("MISMATCH", "UNPARSEABLE"):
            blocking_hit = True
            findings.append({"bgc": bid, "severity": "FAIL", "detail": v["status"]})
        elif v["status"] == "WARN_region_only":
            findings.append({"bgc": bid, "severity": "WARN", "detail": v["status"]})
    status = "FAIL" if blocking_hit else ("WARN" if findings else "PASS")
    # locator mismatch is blocking in strict mode (a wrong node propagates everywhere)
    return GateResult("locator_reconciliation", status, True, findings=findings,
                      detail=f"{len(bgcs)} cards checked")


def _gate_claim_safety(package_dir: Path) -> GateResult:
    try:
        from mamey.judgment_store import list_complete_bgcs, read_mode_b, _strain_compound_names
        from claim_safety_linter import lint_claim_safety
    except Exception as e:
        return GateResult("claim_safety", "SKIP", False, detail=f"import: {e}")
    bgcs = list_complete_bgcs(package_dir)
    if not bgcs:
        # H3/v9.7.352: a card-less package must not masquerade as "claim-safety verified".
        # The headline claim-safety invariant is never exercised with zero cards, so this is a
        # WARN (surfaced, propagates to overall WARN), not a silent SKIP that reaches PASS.
        return GateResult("claim_safety", "WARN", False,
                          detail="no filed cards — claim-safety invariant not exercised")
    cnames = _strain_compound_names(package_dir) or None
    findings = []
    identity_hit = False
    for bid in bgcs:
        # H3/v9.7.352: per-card guard — one malformed card yields a FAIL row for that card,
        # it does not crash the whole seal (the other cards still evaluate).
        try:
            card = read_mode_b(package_dir, bid)
            if not card:
                continue
            for f in lint_claim_safety(card, compound_names=cnames):
                # v9.7.125b: after AS-XXX batch-1 calibration (0% FP, robust + heuristic), the
                # identity-overclaim rule is FAIL-eligible. The KCB-ceiling rule stays WARN.
                if f.startswith("possible identity overclaim"):
                    identity_hit = True
                    findings.append({"bgc": bid, "severity": "FAIL", "detail": f})
                else:
                    findings.append({"bgc": bid, "severity": "WARN", "detail": f})
        except Exception as e:  # malformed card: fail this card, keep evaluating the rest
            identity_hit = True
            findings.append({"bgc": bid, "severity": "FAIL",
                             "detail": f"card evaluation error: {type(e).__name__}: {e}"})
    status = "FAIL" if identity_hit else ("WARN" if findings else "PASS")
    # blocking=True now: a real compound-identity overclaim should block a strict seal.
    return GateResult("claim_safety", status, True, findings=findings,
                      detail=f"{len(bgcs)} cards, {len(findings)} findings")


def _gate_figure_references(package_dir: Path) -> GateResult:
    """Validate package figures (v9.7.126, audit P1): every figure PNG opens and has its
    companion *_data.csv (the data-only-figure convention), and every figure referenced in a
    markdown report exists on disk. Figures are post-seal supplementary, so this is WARN, not
    a blocking gate — a missing figure should not fail the scientific core."""
    import re as _re
    findings = []
    pngs = sorted(package_dir.glob("*fig*.png"))
    # (a) every figure PNG opens (magic bytes) and has a companion _data.csv
    for png in pngs:
        try:
            with open(png, "rb") as f:
                if f.read(8) != b"\x89PNG\r\n\x1a\n":
                    findings.append({"bgc": "", "severity": "WARN",
                                     "detail": f"{png.name}: not a valid PNG"})
        except Exception as e:
            findings.append({"bgc": "", "severity": "WARN", "detail": f"{png.name}: unreadable ({e})"})
        companion = png.with_name(png.stem + "_data.csv")
        if not companion.exists():
            findings.append({"bgc": "", "severity": "WARN",
                             "detail": f"{png.name}: missing companion {companion.name}"})
    # (b) every figure referenced in a markdown report exists on disk
    on_disk = {p.name for p in pngs}
    for md in sorted(package_dir.glob("*.md")):
        try:
            text = md.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # markdown image refs ![..](name.png) and bare *.png mentions
        # sorted: set iteration order is randomised per process (PYTHONHASHSEED), and these
        # findings are emitted verbatim into seal_findings.csv / seal_status.json /
        # DEBUG_RECEIPT.md / figure_reference_validation.csv — unsorted, two identical runs
        # produce byte-different sealed receipts.
        for ref in sorted(set(_re.findall(r"([A-Za-z0-9_.\-]+\.png)", text))):
            if ref not in on_disk and not (package_dir / ref).exists():
                findings.append({"bgc": "", "severity": "WARN",
                                 "detail": f"{md.name} references missing figure {ref}"})
    status = "PASS" if not findings else "WARN"
    return GateResult("figure_references", status, False, findings=findings,
                      detail=f"{len(pngs)} figures, {len(findings)} issues")


def _gate_deliverable_status(package_dir: Path, gates_so_far: list) -> GateResult:
    """Emit a deliverable-status table (v9.7.126, audit P1): which contracted artifacts are
    present/complete. Reports PASS/PARTIAL/WARN per artifact. Non-blocking: it's a status
    report, not a pass/fail gate (the underlying gates already block where appropriate)."""
    pkg = package_dir
    def _exists(glob_pat):
        return bool(list(pkg.glob(glob_pat)))
    # the 13-item-ish deliverable contract, checked by presence on disk
    checks = [
        ("manifest.json",            _exists("manifest.json")),
        ("triage_board",             _exists("*_4_triage_board.csv")),
        ("inventory",                _exists("*_inventory.csv") or _exists("*_2_inventory.csv")),
        ("workbook",                 _exists("*_workbook.xlsx") or _exists("*_5_workbook.xlsx")),
        ("gene_by_gene_table",       _exists("*_gene_by_gene_all_bgcs.csv")),
        ("judgment_register",        _exists("*_judgment_register.json")),
        ("mode_b_cards",             _exists("judgment/*_mode_b.md") or _exists("*_mode_b.md")),
        ("figures",                  _exists("*fig*.png")),
        ("figure_data_csvs",         _exists("*fig*_data.csv")),
        ("checksums",                _exists("checksums_sha256.txt") or _exists("*checksums*.txt")),
    ]
    findings = []
    for name, present in checks:
        findings.append({"bgc": "", "severity": "PASS" if present else "PARTIAL",
                         "detail": f"{name}: {'present' if present else 'absent'}"})
    # fold in the live gate statuses so the table reflects QC, not just presence
    for g in gates_so_far:
        findings.append({"bgc": "", "severity": g.status,
                         "detail": f"gate:{g.name} = {g.status}"})
    n_absent = sum(1 for _, present in checks if not present)
    status = "PASS" if n_absent == 0 else "WARN"
    return GateResult("deliverable_status", status, False, findings=findings,
                      detail=f"{len(checks)} artifacts, {n_absent} absent")


def seal_package(package_dir: str | Path, strict: bool = False, advisory: bool = False) -> dict:
    """Run all QC gates. Returns the seal result dict (also written to disk by the CLI).

    F05 (v9.7.354): a blocking-gate FAIL now exits NON-ZERO BY DEFAULT. Previously the default
    was report-only (strict=False), so a blocking FAIL — a real claim-safety, locator, or package
    FAIL — exited 0 and could pass silently through an automated cut. Enforcement is now the
    default; ``advisory=True`` (the CLI ``--advisory`` opt-in) restores the old exit-0 report-only
    behavior for humans inspecting a work-in-progress package. ``strict=True`` is retained for
    back-compat and always enforces (it overrides ``advisory``).
    """
    pkg = Path(package_dir)
    from mamey.packaging import PackageContainmentError, _package_files_fail_closed
    try:
        _package_files_fail_closed(pkg)
    except PackageContainmentError as exc:
        enforce = strict or not advisory
        warning = None
        if not enforce:
            warning = ("ADVISORY: blocking FAIL(s) present, exit forced to 0 by --advisory — "
                       "drop --advisory (or add --strict) to enforce (exit 1)")
        return {
            "overall": "FAIL",
            "strict": strict,
            "advisory": advisory,
            "enforced": enforce,
            "non_strict_warning": warning,
            "exit_code": 1 if enforce else 0,
            "package": str(pkg),
            "gates": [{
                "name": "package_containment",
                "status": "FAIL",
                "blocking": True,
                "detail": str(exc),
                "findings": [{"bgc": "", "severity": "FAIL", "detail": str(exc)}],
            }],
        }
    triage = _triage_rows(pkg)

    gates = [
        _gate_package_validate(pkg),
        _gate_workbook(pkg),
        _gate_mode_b_quality(pkg, triage),
        _gate_locator(pkg, triage),
        _gate_claim_safety(pkg),
        _gate_figure_references(pkg),
    ]
    # deliverable-status runs last: it summarizes the other gates plus artifact presence
    gates.append(_gate_deliverable_status(pkg, gates))

    # Overall: FAIL if any blocking gate FAILed; else WARN if any WARN/FAIL; else PASS.
    blocking_fail = any(g.status == "FAIL" and g.blocking for g in gates)
    any_issue = any(g.status in ("WARN", "FAIL") for g in gates)
    if blocking_fail:
        overall = "FAIL"
    elif any_issue:
        overall = "WARN"
    else:
        overall = "PASS"

    # F05 (v9.7.354): enforce by default. A blocking FAIL exits non-zero unless the caller opts
    # into advisory (report-only) mode AND is not in strict mode. `strict` still forces enforcement.
    enforce = strict or not advisory
    exit_code = 1 if (blocking_fail and enforce) else 0

    # Surface a loud banner ONLY when a blocking FAIL is deliberately being demoted to exit 0 by
    # the advisory opt-in — so a real claim-safety/locator/validate FAIL cannot silently pass.
    # (Key name kept as `non_strict_warning` for receipt/CLI back-compat.)
    non_strict_warning = None
    if blocking_fail and not enforce:
        non_strict_warning = ("ADVISORY: blocking FAIL(s) present, exit forced to 0 by --advisory — "
                              "drop --advisory (or add --strict) to enforce (exit 1)")

    return {
        "overall": overall,
        "strict": strict,
        "advisory": advisory,
        "enforced": enforce,
        "non_strict_warning": non_strict_warning,
        "exit_code": exit_code,
        "package": str(pkg),
        "gates": [
            {"name": g.name, "status": g.status, "blocking": g.blocking,
             "detail": g.detail, "findings": g.findings}
            for g in gates
        ],
    }


def write_receipts(result: dict, out_dir: str | Path) -> dict[str, Path]:
    """Write DEBUG_RECEIPT.md, seal_status.json, seal_findings.csv into out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # seal_status.json
    status_path = out / "seal_status.json"
    atomic_write_text(status_path, json.dumps(result, indent=2))

    # seal_findings.csv
    findings_path = out / "seal_findings.csv"
    with atomic_open(findings_path, "w", newline="") as f:
        w = _SafeWriter(f)
        w.writerow(["gate", "bgc", "severity", "detail"])
        for g in result["gates"]:
            for fd in g["findings"]:
                w.writerow([g["name"], fd.get("bgc", ""), fd.get("severity", ""), fd.get("detail", "")])

    # DEBUG_RECEIPT.md
    receipt_path = out / "DEBUG_RECEIPT.md"
    lines = [
        f"# Seal Receipt — {result['package']}",
        "",
        f"**Overall:** {result['overall']}  ·  strict={result['strict']}  ·  exit={result['exit_code']}",
        "",
    ]
    if result.get("non_strict_warning"):
        lines += [f"> ⚠️ **{result['non_strict_warning']}**", ""]
    lines += [
        "| Gate | Status | Blocking | Detail |",
        "|---|---|---|---|",
    ]
    for g in result["gates"]:
        lines.append(f"| {g['name']} | {g['status']} | {g['blocking']} | {g['detail']} |")
    total_findings = sum(len(g["findings"]) for g in result["gates"])
    lines += ["", f"**Total findings:** {total_findings}"]
    if total_findings:
        lines += ["", "## Findings", "", "| Gate | BGC | Severity | Detail |", "|---|---|---|---|"]
        for g in result["gates"]:
            for fd in g["findings"]:
                lines.append(f"| {g['name']} | {fd.get('bgc','')} | {fd.get('severity','')} | {fd.get('detail','')} |")
    atomic_write_text(receipt_path, "\n".join(lines) + "\n")

    return {"receipt": receipt_path, "status": status_path, "findings": findings_path,
            **_write_named_csvs(result, out)}


def _write_named_csvs(result: dict, out: Path) -> dict[str, Path]:
    """Emit the two audit-named package-level CSVs (v9.7.126):
    figure_reference_validation.csv and deliverable_status_table.csv. These mirror the
    relevant gate findings as standalone, discoverable artifacts (zero issue rows = clean)."""
    paths: dict[str, Path] = {}
    by_gate = {g["name"]: g for g in result["gates"]}

    fig = by_gate.get("figure_references")
    if fig is not None:
        p = out / "figure_reference_validation.csv"
        with atomic_open(p, "w", newline="") as f:
            w = _SafeWriter(f)
            w.writerow(["severity", "detail"])
            for fd in fig["findings"]:
                w.writerow([fd.get("severity", ""), fd.get("detail", "")])
            if not fig["findings"]:
                w.writerow(["PASS", "all figures valid with companion data CSVs; no missing references"])
        paths["figure_csv"] = p

    deliv = by_gate.get("deliverable_status")
    if deliv is not None:
        p = out / "deliverable_status_table.csv"
        with atomic_open(p, "w", newline="") as f:
            w = _SafeWriter(f)
            w.writerow(["artifact_or_gate", "status"])
            for fd in deliv["findings"]:
                detail = fd.get("detail", "")
                w.writerow([detail, fd.get("severity", "")])
        paths["deliverable_csv"] = p

    return paths
