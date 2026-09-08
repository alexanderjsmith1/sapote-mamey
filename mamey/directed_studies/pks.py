"""Directed PKS Study Mode.

This module wires Pre-Sapote Lite gene evidence into the directed PKS study
outputs and figure renderer.
"""

from __future__ import annotations

from pathlib import Path
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
from dataclasses import dataclass, asdict
from typing import Iterable

from mamey.pre_sapote.lite import run_pre_sapote_lite
from mamey.figures.locus_renderer_v2 import render_locus_map_v2
from mamey.efls import write_efls_outputs
from mamey.lcms.handle_registry import write_lcms_handles
from mamey.workbooks.directed_study_workbook import write_directed_study_workbook
from mamey.comparators.antismash_ingest import compare_query_to_comparator
from mamey.citations.resolver import write_citation_outputs
from mamey.directed_studies.cddr_pks import build_cddr_pks_report

@dataclass(frozen=True)
class DirectedPKSStudySpec:
    study_id: str
    groups: dict[str, list[str]]
    excluded_bgcs: dict[str, str]
    figure_quality_gate: float = 9.0
    comparator_gene_table: str | None = None

def load_study_spec(path: Path) -> DirectedPKSStudySpec:
    data = json.loads(path.read_text(encoding="utf-8"))
    return DirectedPKSStudySpec(
        study_id=data.get("study_id", "directed_pks_study"),
        groups={k: list(v) for k, v in data.get("groups", {}).items()},
        excluded_bgcs=dict(data.get("excluded_bgcs") or data.get("excluded") or {}),
        figure_quality_gate=float(data.get("figure_quality_gate", 9.0)),
        comparator_gene_table=data.get("comparator_gene_table"),
    )

def _read_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="") as handle:
        return list(csv.DictReader(handle))

def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path

def group_machinery_summary(gene_evidence_csv: Path, out_csv: Path) -> Path:
    rows = _read_rows(gene_evidence_csv)
    summary: dict[str, dict[str, int]] = {}
    for row in rows:
        if "set_id" not in row:
            raise ValueError(
                f"{gene_evidence_csv}: gene-evidence CSV is missing the required 'set_id' column "
                f"(columns present: {sorted(row)}). group_machinery_summary expects a Pre-Sapote Lite "
                f"gene-evidence CSV; check the input source.")
        set_id = row["set_id"]
        summary.setdefault(set_id, {
            "gene_count": 0,
            "tier_A": 0,
            "tier_B": 0,
            "tier_C": 0,
            "tier_D": 0,
            "tier_U": 0,
            "pks_core_genes": 0,
            "nrps_genes": 0,
            "do_not_overlabel_count": 0,
        })
        s = summary[set_id]
        s["gene_count"] += 1
        tier = row.get("evidence_tier", "U")
        if f"tier_{tier}" in s:
            s[f"tier_{tier}"] += 1
        role = row.get("source_role", "").lower()
        if "pks" in role:
            s["pks_core_genes"] += 1
        if "nrps" in role or "adenylation" in role:
            s["nrps_genes"] += 1
        if str(row.get("do_not_overlabel_flag", "")).lower() == "true":
            s["do_not_overlabel_count"] += 1
    out_rows = [{"set_id": k, **v} for k, v in sorted(summary.items())]
    return _write_csv(out_csv, out_rows, [
        "set_id", "gene_count", "tier_A", "tier_B", "tier_C", "tier_D", "tier_U",
        "pks_core_genes", "nrps_genes", "do_not_overlabel_count"
    ])

def excluded_bgc_table(excluded_bgcs: dict[str, str], out_csv: Path) -> Path:
    rows = [
        {
            "bgc_id": bgc_id,
            "status": "excluded_background_control",
            "reason": reason,
            "reentry_condition": "re-enter only if chemistry/activity maps back to this BGC",
        }
        for bgc_id, reason in sorted(excluded_bgcs.items())
    ]
    return _write_csv(out_csv, rows, ["bgc_id", "status", "reason", "reentry_condition"])

def write_summary_md(spec: DirectedPKSStudySpec, out_dir: Path, figure_receipts: list[dict]) -> Path:
    lines = [
        f"# Directed PKS Study — {spec.study_id}",
        "",
        "## Scope",
        "",
        "This study consumes Pre-Sapote Lite evidence-gated gene labels before generating directed PKS outputs.",
        "",
        "## Groups",
        "",
    ]
    for set_id, nodes in spec.groups.items():
        lines.append(f"- **{set_id}:** {', '.join(nodes)}")
    lines += [
        "",
        "## Excluded/background BGCs",
        "",
    ]
    if spec.excluded_bgcs:
        for bgc, reason in spec.excluded_bgcs.items():
            lines.append(f"- **{bgc}:** {reason}")
    else:
        lines.append("- None supplied.")
    lines += [
        "",
        "## Figure receipts",
        "",
    ]
    for receipt in figure_receipts:
        lines.append(f"- **{receipt['group']}**: {receipt['status']} / self-rating {receipt['self_rating']}")
    lines += [
        "",
        "## Claim rule",
        "",
        "Comparator context is not product identity. Functional grouping is not physical linkage.",
    ]
    path = out_dir / "DIRECTED_PKS_STUDY_SUMMARY.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path

def run_directed_pks_study(source_csv: Path, spec: DirectedPKSStudySpec, out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    pre_dir = out_dir / "pre_sapote_lite"
    pre_outputs = run_pre_sapote_lite(source_csv, spec.groups, pre_dir)
    gene_evidence = Path(pre_outputs["gene_evidence_table"])

    group_summary = group_machinery_summary(gene_evidence, out_dir / "group_machinery_summary.csv")
    excluded = excluded_bgc_table(spec.excluded_bgcs, out_dir / "excluded_bgc_table.csv")
    efls_outputs = write_efls_outputs(gene_evidence, out_dir / "efls")

    figures_dir = out_dir / "figures"
    figure_receipts = []
    for group in spec.groups:
        preflight = render_locus_map_v2(gene_evidence, group, figures_dir, f"{spec.study_id}_{group}_locus_map")
        figure_receipts.append(asdict(preflight))

    figure_receipt_path = out_dir / "figure_quality_receipts.json"
    figure_receipt_path.write_text(json.dumps(figure_receipts, indent=2), encoding="utf-8")
    lcms_outputs = write_lcms_handles(gene_evidence, out_dir / "lcms")

    comparator_tracks_csv: Path | None = None
    comparator_outputs: dict[str, str] = {}
    if spec.comparator_gene_table:
        comparator_gene_table = Path(spec.comparator_gene_table)
        if comparator_gene_table.exists():
            comparator_dir = out_dir / "comparators"
            comparator_dir.mkdir(parents=True, exist_ok=True)
            comparator_tracks_csv = compare_query_to_comparator(gene_evidence, comparator_gene_table, comparator_dir)
            comparator_outputs["pairwise_domain_table"] = str(comparator_tracks_csv)

    citation_outputs = write_citation_outputs(
        out_dir / "citations",
        gene_evidence_csv=gene_evidence,
        comparator_tracks_csv=comparator_tracks_csv,
        lcms_handles_csv=Path(lcms_outputs["lcms_csv"]),
    )

    summary = write_summary_md(spec, out_dir, figure_receipts)
    workbook_path = write_directed_study_workbook(
        out_dir / f"{spec.study_id}_directed_study_workbook.xlsx",
        study_id=spec.study_id,
        gene_evidence_csv=gene_evidence,
        group_machinery_csv=group_summary,
        efls_linkage_csv=Path(efls_outputs["linkage_table"]),
        efls_fragments_csv=Path(efls_outputs["fragment_summary"]),
        comparator_tracks_csv=comparator_tracks_csv,
        lcms_handles_csv=Path(lcms_outputs["lcms_csv"]),
        citation_workorder_csv=Path(citation_outputs["citation_workorder"]),
        figure_receipt_json=figure_receipt_path,
        excluded_bgc_csv=excluded,
    )
    receipt = {
        "study_id": spec.study_id,
        "gene_evidence_table": str(gene_evidence),
        "group_machinery_summary": str(group_summary),
        "excluded_bgc_table": str(excluded),
        "efls_outputs": efls_outputs,
        "lcms_outputs": lcms_outputs,
        "comparator_outputs": comparator_outputs,
        "citation_outputs": citation_outputs,
        "summary_md": str(summary),
        "workbook": str(workbook_path),
        "figure_receipts": figure_receipts,
        # v9.7.374 fix: all() over an empty figure_receipts list is vacuously True in Python, so a
        # study spec with an empty (or all-empty-group) `groups` mapping produced zero figures and
        # was still reported READY -- a completion status with nothing actually gated. Require at
        # least one figure receipt before READY is reachable.
        "status": "READY" if figure_receipts and all(r["self_rating"] >= spec.figure_quality_gate for r in figure_receipts) else "NEEDS_REVIEW",
    }
    receipt_path = out_dir / "DIRECTED_PKS_STUDY_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    cddr_receipt = build_cddr_pks_report(out_dir, out_dir / "reports")
    receipt["cddr_pks_report"] = str(cddr_receipt.report_md)
    receipt["cddr_pks_receipt"] = str(cddr_receipt.report_json)
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt
