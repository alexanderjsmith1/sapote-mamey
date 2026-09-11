"""CDDR-PKS report type.

CDDR-PKS = Cluster Deep-Dive Report for directed PKS studies.

This report is the narrative/reporting layer above Directed PKS Study Mode. It
summarizes Pre-Sapote Lite evidence, EFLS linkage status, comparator tracks,
LC-MS handles, citation status, figure QA, background-control branches, and
workbook outputs while preserving claim-safety language.
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass, asdict
import csv
import json

@dataclass(frozen=True)
class CDDRPKSReceipt:
    study_dir: str
    report_md: str
    report_json: str
    status: str
    warning_count: int

def _read_csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))

def _read_json(path: Path):
    if not path.exists():
        return {}
    return json.loads(path.read_text(errors="replace"))

def _safe_count(path: Path) -> int:
    return len(_read_csv(path))

def _table_preview(rows: list[dict], columns: list[str], max_rows: int = 12) -> str:
    if not rows:
        return "_No rows supplied._"
    cols = [c for c in columns if any(c in row for row in rows)]
    if not cols:
        cols = list(rows[0].keys())[:6]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for row in rows[:max_rows]:
        vals = [str(row.get(c, "")).replace("\n", " ")[:120] for c in cols]
        lines.append("| " + " | ".join(vals) + " |")
    if len(rows) > max_rows:
        lines.append(f"| … | {len(rows) - max_rows} additional rows omitted from preview |" + " |" * max(0, len(cols)-2))
    return "\n".join(lines)

def _figure_status_lines(receipt: dict) -> list[str]:
    figures = receipt.get("figure_receipts", []) if isinstance(receipt, dict) else []
    lines = []
    for fig in figures:
        lines.append(f"- **{fig.get('group','?')}**: {fig.get('status','?')} / self-rating {fig.get('self_rating','?')}")
    return lines or ["- No figure receipts found."]

def build_cddr_pks_report(study_dir: Path, out_dir: Path | None = None, report_name: str = "CDDR_PKS_REPORT.md") -> CDDRPKSReceipt:
    """Build a CDDR-PKS report from a directed study output directory."""
    out_dir = out_dir or study_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    receipt = _read_json(study_dir / "DIRECTED_PKS_STUDY_RECEIPT.json")
    gene_rows = _read_csv(study_dir / "pre_sapote_lite" / "gene_evidence_table.csv")
    group_rows = _read_csv(study_dir / "group_machinery_summary.csv")
    efls_rows = _read_csv(study_dir / "efls" / "EFLS_Linkage_Table.csv")
    efls_group_rows = _read_csv(study_dir / "efls" / "EFLS_Group_Assignments.csv")
    comparator_rows = _read_csv(study_dir / "comparators" / "pairwise_domain_table.csv")
    lcms_rows = _read_csv(study_dir / "lcms" / "LCMS_Chemical_Handle.csv")
    citation_rows = _read_csv(study_dir / "citations" / "Citation_Ledger.csv")
    excluded_rows = _read_csv(study_dir / "excluded_bgc_table.csv")

    status = receipt.get("status", "UNKNOWN") if isinstance(receipt, dict) else "UNKNOWN"
    warning_count = 0
    if not gene_rows:
        warning_count += 1
    if not group_rows:
        warning_count += 1
    if not lcms_rows:
        warning_count += 1
    if any("product_identity" in str(row).lower() and "not_product_identity" not in str(row).lower() for row in comparator_rows):
        warning_count += 1

    lines = [
        "# CDDR-PKS — Directed PKS Cluster Deep-Dive Report",
        "",
        "## 1. Stable identity and report status",
        "",
        f"- **Study directory:** `{study_dir}`",
        f"- **Directed study status:** `{status}`",
        f"- **Warning count:** {warning_count}",
        "",
        "## 2. Claim-safety boundary",
        "",
        "Comparator context is not product identity. Functional grouping is not physical linkage. Named-product claims require chemistry/genetics confirmation.",
        "",
        "## 3. Group machinery summary",
        "",
        _table_preview(group_rows, ["set_id", "gene_count", "tier_A", "tier_B", "tier_C", "tier_D", "tier_U", "pks_core_genes", "nrps_genes", "do_not_overlabel_count"]),
        "",
        "## 4. Evidence-gated gene labels",
        "",
        _table_preview(gene_rows, ["set_id", "node", "locus_tag", "source_role", "antiSMASH_domains", "evidence_tier", "allowed_figure_label", "do_not_overlabel_flag"]),
        "",
        "## 5. EFLS linkage interpretation",
        "",
        "### Group assignments",
        "",
        _table_preview(efls_group_rows, ["group_id", "assignment", "pair_count"]),
        "",
        "### Pairwise linkage",
        "",
        _table_preview(efls_rows, ["group_id", "node_a", "node_b", "linkage_class", "score", "rationale"]),
        "",
        "## 6. Comparator tracks",
        "",
        _table_preview(comparator_rows, ["query_locus_tag", "query_node", "comparator_id", "comparator_locus_tag", "comparator_product", "domain_order_similarity", "interpretation_scope"]),
        "",
        "## 7. LC-MS chemical handles",
        "",
        _table_preview(lcms_rows, ["set_id", "node", "locus_tag", "expected_chemistry_class", "polarity", "uv_dad_handle", "identity_safety_statement"]),
        "",
        "## 8. Citation work order status",
        "",
        _table_preview(citation_rows, ["source_type", "entity_id", "node", "citation_status", "gate_status", "required_action", "claim_safety"]),
        "",
        "## 9. Excluded/background-control BGCs",
        "",
        _table_preview(excluded_rows, ["bgc_id", "status", "reason", "reentry_condition"]),
        "",
        "## 10. Figure QA",
        "",
        *_figure_status_lines(receipt if isinstance(receipt, dict) else {}),
        "",
        "## 11. Workbook and machine-readable outputs",
        "",
        f"- **Workbook:** `{receipt.get('workbook', 'not recorded') if isinstance(receipt, dict) else 'not recorded'}`",
        f"- **Receipt:** `{study_dir / 'DIRECTED_PKS_STUDY_RECEIPT.json'}`",
        "",
        "## 12. Recommended next evidence",
        "",
        "1. Use EFLS assignments to decide whether each group remains functional-only or should be escalated as possible split pathway.",
        "2. Resolve citation work-order rows marked `primary_reference_needed` or `mibig_supplied_unverified_primary`.",
        "3. Use LC-MS handles for fraction-level targeted and untargeted checks, but keep all named products at comparator-context level until confirmed.",
    ]

    report_md = out_dir / report_name
    report_md.write_text("\n".join(lines), encoding="utf-8")

    report_json = out_dir / "CDDR_PKS_REPORT_RECEIPT.json"
    report_data = {
        "study_dir": str(study_dir),
        "status": status,
        "warning_count": warning_count,
        "row_counts": {
            "gene_evidence": len(gene_rows),
            "group_machinery": len(group_rows),
            "efls_linkage": len(efls_rows),
            "comparator_tracks": len(comparator_rows),
            "lcms_handles": len(lcms_rows),
            "citation_rows": len(citation_rows),
            "excluded_bgcs": len(excluded_rows),
        },
        "claim_safety": "comparator_context_not_product_identity; functional_grouping_not_physical_linkage",
        "outputs": {
            "report_md": str(report_md),
            "report_json": str(report_json),
        },
    }
    report_json.write_text(json.dumps(report_data, indent=2), encoding="utf-8")

    return CDDRPKSReceipt(
        study_dir=str(study_dir),
        report_md=str(report_md),
        report_json=str(report_json),
        status=status,
        warning_count=warning_count,
    )
