"""Release-level Legacy Feature Matrix Gate.

This module prevents hard-won workflow features from disappearing silently across
Sapote-Mamey releases. It can create a default matrix, validate a supplied
matrix, and write a receipt suitable for release QA.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json

Status = Literal["active", "renamed", "superseded", "missing", "needs_test", "deferred"]
Priority = Literal["P0", "P1", "P2"]

@dataclass(frozen=True)
class LegacyFeature:
    legacy_feature: str
    priority: Priority
    source_doc: str
    original_section_or_version: str
    current_status: Status
    current_module_or_doc: str
    current_test: str
    risk_if_missing: str
    recovery_action: str

P0_FEATURES = [
    "Run Controller",
    "Triage First Board",
    "Lead Priority vs Claim Confidence",
    "LC-MS Chemical Handle",
    "Default Complete Package",
    "Executable Completeness Gate",
    "LMPKS",
    "FLBR",
    "UMED",
    "CCTT",
    "CGAD",
    "CCSM / Universal Comparison Schema",
    "Project Memory Snapshot",
    "Output Options Menu / Combo Meals",
    "Literature Deep Dive",
    "PDF/figure design standards",
    "Pre-Sapote Lite",
    "Directed PKS Study Mode",
    "Figure Renderer v2",
    "EFLS Rewire",
    "Comparator antiSMASH Ingestor",
    "Directed Study Workbook",
    "Citation Work Order Resolver",
    "Dual-LLM Handoff Receipt",
]

DEFAULT_FEATURES = [
    LegacyFeature("Run Controller", "P0", "Sapote v8.9.3 white paper", "§0", "active", "mamey/cli.py", "run/validate/seal-package smoke", "Modules can be skipped or run out of order.", "Keep run controller in CLI/release docs."),
    LegacyFeature("Triage First Board", "P0", "Sapote v8.9.3 white paper", "§0.6", "active", "Mamey triage outputs", "mode-b/triage coverage tests", "Top wet-lab actions can be buried.", "Keep lead board before dense BGC pages."),
    LegacyFeature("Lead Priority vs Claim Confidence", "P0", "Sapote v8.9.3 white paper", "§0.6 / claim calibration", "active", "claim_safety_gate + reports", "test_claim_safety_ci_gate", "Priority and evidence certainty collapse into overclaim.", "Keep separate fields and claim-safety lint."),
    LegacyFeature("LC-MS Chemical Handle", "P0", "Sapote v8.9.3 white paper", "§0.7 / §46", "active", "mamey/lcms/handle_registry.py", "test_lcms_handle_registry_outputs_bench_guidance", "Reports lack bench-actionable chemistry guidance.", "Maintain registry and directed-study LCMS sheet."),
    LegacyFeature("Default Complete Package", "P0", "Sapote v8.9.3 white paper", "§0.12", "active", "packaging/release reports", "package QA/seal tests", "Runs ship incomplete deliverables.", "Keep package manifest/checksums and package QA."),
    LegacyFeature("Executable Completeness Gate", "P0", "Sapote v8.9.3 white paper", "§30.11.1", "active", "tools/mamey_package_qa_v2.py", "package QA focused tests", "Narrated completeness can hide omissions.", "Keep executable diff/receipt gates."),
    LegacyFeature("LMPKS", "P0", "Methods/white paper", "§42", "active", "mamey source scans", "LMPKS/FLBR scan tests", "Large modular PKS fragments are deprioritized.", "Keep zero-KCB rescue triggers."),
    LegacyFeature("FLBR", "P0", "Sapote v8.9.3 white paper", "§51", "active", "fragment rescue docs/modules", "FLBR scan tests", "Megasynthase fragments missed.", "Keep fragment rescue rows and reports."),
    LegacyFeature("UMED", "P0", "Sapote v8.9.3 white paper", "§52", "active", "UMED docs/modules", "UMED scan tests", "Maturation enzyme gaps are missed.", "Keep UMED receipt/report."),
    LegacyFeature("CCTT", "P0", "Sapote v8.9.3 white paper", "§43", "active", "CCTT registry/docs", "CCTT tests", "Cryptic-class triggers are missed.", "Keep CCTT trigger rows."),
    LegacyFeature("CGAD", "P0", "Sapote v8.9.3 white paper", "§44", "active", "CGAD docs/modules", "CGAD tests", "Chitin/glycan defense signals missed.", "Keep CGAD scope and reports."),
    LegacyFeature("CCSM / Universal Comparison Schema", "P0", "Methods/white paper", "§41", "active", "cross-strain outputs", "cross-strain normalization checks", "Cross-run comparisons become invalid.", "Keep UCS/evidence-grade documentation."),
    LegacyFeature("Project Memory Snapshot", "P0", "Methods report", "§40", "active", "session close/open docs", "memory snapshot checks", "Context disappears across sessions.", "Keep JSON/MD session state output."),
    LegacyFeature("Output Options Menu / Combo Meals", "P0", "Sapote v8.9.3 white paper", "§54", "active", "docs/output menu", "docs presence check", "Users cannot discover capabilities.", "Keep menu/docs updated."),
    LegacyFeature("Literature Deep Dive", "P0", "Sapote v8.9.3 white paper", "§21", "active", "literature workorder docs", "citation/literature tests", "Citation workflows lose accuracy-first behavior.", "Keep depth dial and verification statuses."),
    LegacyFeature("PDF/figure design standards", "P0", "Methods report", "§30", "active", "figure gates + docs", "figure preflight tests", "Unreadable/non-publication figures ship.", "Keep 9/10 gate and vector outputs."),
    LegacyFeature("Pre-Sapote Lite", "P0", "v9.7.138 research", "new", "active", "mamey/pre_sapote/lite.py", "test_pre_sapote_lite_blocks_unsupported_labels_and_renderer_ready", "Weak labels appear in figures.", "Keep required before directed-study figures."),
    LegacyFeature("Directed PKS Study Mode", "P0", "v9.7.138 research", "new", "active", "mamey/directed_studies/pks.py", "test_directed_pks_*", "PKS fragments lack coherent study wrapper.", "Keep CLI and receipt outputs."),
    LegacyFeature("Figure Renderer v2", "P0", "v9.7.138 research", "new", "active", "mamey/figures/locus_renderer_v2.py", "renderer preflight tests", "Low-quality locus maps ship.", "Keep SVG/PNG/preflight."),
    LegacyFeature("EFLS Rewire", "P0", "v9.7.138 research", "new", "active", "mamey/efls.py", "test_efls_outputs_linkage_tables", "Functional groups are over-merged.", "Keep linkage classes and NODE_11 guard."),
    LegacyFeature("Comparator antiSMASH Ingestor", "P0", "v9.7.138 research", "new", "active", "mamey/comparators/antismash_ingest.py", "test_comparator_antismash_ingest_parses_gbk_domains_and_deduplicates", "Comparator analysis remains manual/inconsistent.", "Keep GBK/domain parser and deduplication."),
    LegacyFeature("Directed Study Workbook", "P0", "v9.7.138 research", "new", "active", "mamey/workbooks/directed_study_workbook.py", "test_directed_study_workbook_full_output", "Directed-study outputs are hard to audit/merge.", "Keep 11-sheet workbook."),
    LegacyFeature("Citation Work Order Resolver", "P0", "v9.7.138 research", "new", "active", "mamey/citations/resolver.py", "test_citation_resolver_outputs_workorder_and_pass_structure", "Unverified references look verified.", "Keep PASS_STRUCTURE gate."),
    LegacyFeature("Dual-LLM Handoff Receipt", "P0", "v9.7.138 research", "new", "active", "mamey/llm_handoff.py", "test_llm_handoff_receipt_scans_start_files", "ChatGPT/Claude instructions are not proven loaded.", "Keep start-file inventory and handshake receipt."),
]

FIELDNAMES = [
    "legacy_feature", "priority", "source_doc", "original_section_or_version",
    "current_status", "current_module_or_doc", "current_test",
    "risk_if_missing", "recovery_action",
]

def default_legacy_rows() -> list[dict]:
    return [asdict(feature) for feature in DEFAULT_FEATURES]

def write_default_legacy_matrix(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = default_legacy_rows()
    # v9.7.401 (BC2): was a direct write to `path`. Reproduced live: an interrupted write
    # (crash, disk full, kill -9) left the real destination file itself -- not a .tmp sibling --
    # truncated to 2 of 24 rows, on disk where a caller expects the committed matrix. This is the
    # SAME crash-safety gap this codebase already fixed once, for the exact same reason, in this
    # module's own sibling writes three lines below (findings_csv/report/receipt in
    # write_legacy_gate_outputs()) and in output_checklist.py's v9.7.371 fix ("an interrupted
    # write here would seal a truncated file as if it were valid -- the checksum step never sees
    # the half-written state to catch it"). Not a silent-false-PASS bug like this round's
    # rglob-family finds -- validate_legacy_rows() DOES fail loudly on the truncated matrix's
    # missing P0 rows -- but matrix_path.exists() being True on the truncated file means a
    # subsequent run won't regenerate it without an explicit create_default=True, leaving the
    # release QA step stuck failing against what looks like tampering rather than corruption.
    _tmp = path.with_name(path.name + ".tmp")
    with _tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    _tmp.replace(path)
    return path

def read_legacy_matrix(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))

def validate_legacy_rows(rows: list[dict]) -> list[str]:
    by_feature = {row.get("legacy_feature"): row for row in rows}
    failures = []
    for feature in P0_FEATURES:
        row = by_feature.get(feature)
        if row is None:
            failures.append(f"missing P0 legacy feature: {feature}")
            continue
        status = row.get("current_status")
        if status not in {"active", "renamed", "superseded", "missing", "needs_test", "deferred"}:
            failures.append(f"P0 feature {feature} has invalid current_status={status!r}")
        if status in {"missing", "needs_test"} and not row.get("recovery_action"):
            failures.append(f"P0 feature {feature} lacks recovery_action")
        if not row.get("current_module_or_doc"):
            failures.append(f"P0 feature {feature} lacks current_module_or_doc")
        if not row.get("current_test"):
            failures.append(f"P0 feature {feature} lacks current_test")
    return failures

def write_legacy_gate_outputs(matrix_path: Path, out_dir: Path, create_default: bool = False) -> dict[str, str | int | list[str]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    if create_default or not matrix_path.exists():
        write_default_legacy_matrix(matrix_path)
    rows = read_legacy_matrix(matrix_path)
    failures = validate_legacy_rows(rows)
    status = "PASS" if not failures else "FAIL"

    findings_csv = out_dir / "LEGACY_FEATURE_GATE_FINDINGS.csv"
    _findings_tmp = findings_csv.with_name(findings_csv.name + ".tmp")
    with _findings_tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=["status", "finding"])
        writer.writeheader()
        if failures:
            for failure in failures:
                writer.writerow({"status": "FAIL", "finding": failure})
        else:
            writer.writerow({"status": "PASS", "finding": "all P0 legacy features accounted for"})
    _findings_tmp.replace(findings_csv)

    report = out_dir / "LEGACY_FEATURE_GATE_REPORT.md"
    lines = [
        "# Legacy Feature Matrix Gate",
        "",
        f"Status: **{status}**",
        f"Matrix: `{matrix_path}`",
        f"Rows: {len(rows)}",
        "",
    ]
    if failures:
        lines.append("## Failures")
        for failure in failures:
            lines.append(f"- {failure}")
    else:
        lines.append("All P0 legacy features are accounted for with current module/doc and test references.")
    _report_tmp = report.with_name(report.name + ".tmp")
    _report_tmp.write_text("\n".join(lines), encoding="utf-8")
    _report_tmp.replace(report)

    receipt = {
        "status": status,
        "matrix": str(matrix_path),
        "row_count": len(rows),
        "failure_count": len(failures),
        "failures": failures,
        "outputs": {
            "findings_csv": str(findings_csv),
            "report": str(report),
        }
    }
    receipt_path = out_dir / "LEGACY_FEATURE_GATE_RECEIPT.json"
    _receipt_tmp = receipt_path.with_name(receipt_path.name + ".tmp")
    _receipt_tmp.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    _receipt_tmp.replace(receipt_path)
    return {**receipt["outputs"], "receipt": str(receipt_path), "status": status, "failure_count": len(failures), "failures": failures}
