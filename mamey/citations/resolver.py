"""Citation Work Order Resolver.

The resolver keeps citation status explicit and prevents database/comparator
context from being upgraded into verified primary evidence without a DOI/PMID
check.

It emits:
- Citation_Workorder.csv
- Literature_WorkOrder.md
- Citation_Ledger.csv
- CITATION_RESOLUTION_RECEIPT.json
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Any
import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import re

VALID_STATUSES = {
    "verified_method_citation",
    "verified_database_citation",
    "mibig_supplied_unverified_primary",
    "literature_verified_primary",
    "primary_reference_needed",
    "user_supplied_reference",
}

def normalize_status(status: str | None) -> str:
    if not status:
        return "primary_reference_needed"
    if status not in VALID_STATUSES:
        return "primary_reference_needed"
    return status

def gate_status(citation_rows: list[dict]) -> str:
    # AUDIT_374: with zero citation rows, `statuses` is the empty set, so neither
    # membership check below is true and the function fell through to PASS_VERIFIED_PRIMARY
    # -- the single BEST possible gate value -- purely because "any element of the empty set"
    # is vacuously false for both disqualifying statuses. Zero rows means zero claims were
    # checked, which is the opposite of "verified"; it must never outrank a real, partially
    # unverified row set. Route the no-rows case to PASS_STRUCTURE (the same "not fully
    # verified yet" gate already used for unverified/mibig-only evidence) instead.
    if not citation_rows:
        return "PASS_STRUCTURE"
    statuses = {normalize_status(row.get("citation_status")) for row in citation_rows}
    if "primary_reference_needed" in statuses or "mibig_supplied_unverified_primary" in statuses:
        return "PASS_STRUCTURE"
    return "PASS_VERIFIED_PRIMARY"

def _read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))

def _looks_mibig(text: str) -> bool:
    return bool(re.search(r"\bBGC\d{7}", text)) or "mibig" in text.lower()

def _extract_pub_ids(text: str) -> tuple[str, str]:
    pmid_match = re.search(r"(?:PMID|pubmed)[:\s]*([0-9]{5,10})", text, flags=re.I)
    doi_match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+", text)
    return (
        pmid_match.group(1) if pmid_match else "",
        doi_match.group(0) if doi_match else "",
    )

def classify_citation_source(context: str, supplied_status: str | None = None) -> str:
    status = normalize_status(supplied_status)
    if supplied_status:
        return status
    pmid, doi = _extract_pub_ids(context)
    if doi or pmid:
        # ID present but not independently verified by this resolver.
        return "mibig_supplied_unverified_primary" if _looks_mibig(context) else "primary_reference_needed"
    if _looks_mibig(context):
        return "mibig_supplied_unverified_primary"
    if context.strip():
        return "primary_reference_needed"
    return "primary_reference_needed"

def build_citation_rows(
    *,
    gene_evidence_csv: Path | None = None,
    comparator_tracks_csv: Path | None = None,
    lcms_handles_csv: Path | None = None,
    extra_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for row in _read_csv(gene_evidence_csv):
        context = row.get("mibig_context", "")
        if context:
            status = classify_citation_source(context)
            rows.append({
                "source_type": "gene_evidence_mibig_context",
                "entity_id": row.get("locus_tag", ""),
                "node": row.get("node", ""),
                "claim_or_context": context,
                "citation_status": status,
                "pmid": _extract_pub_ids(context)[0],
                "doi": _extract_pub_ids(context)[1],
                "required_action": "verify primary DOI/PMID before upgrading claim" if status != "PASS_VERIFIED_PRIMARY" else "",
                "claim_safety": "comparator_context_not_product_identity",
            })

    for row in _read_csv(comparator_tracks_csv):
        context = " | ".join(str(row.get(k, "")) for k in [
            "comparator_id", "comparator_locus_tag", "comparator_product", "interpretation_scope"
        ]).strip()
        if context:
            status = classify_citation_source(context)
            rows.append({
                "source_type": "comparator_track",
                "entity_id": row.get("query_locus_tag", ""),
                "node": row.get("query_node", ""),
                "claim_or_context": context,
                "citation_status": status,
                "pmid": _extract_pub_ids(context)[0],
                "doi": _extract_pub_ids(context)[1],
                "required_action": "verify comparator primary reference or keep as comparator context",
                "claim_safety": row.get("interpretation_scope", "comparator_context_not_product_identity"),
            })

    for row in _read_csv(lcms_handles_csv):
        context = row.get("expected_chemistry_class", "")
        if context:
            rows.append({
                "source_type": "lcms_handle_registry",
                "entity_id": row.get("locus_tag", ""),
                "node": row.get("node", ""),
                "claim_or_context": context,
                "citation_status": "verified_method_citation",
                "pmid": "",
                "doi": "",
                "required_action": "method guidance registry; cite registry/provenance in docs",
                "claim_safety": row.get("identity_safety_statement", "candidate signal only"),
            })

    for row in extra_rows or []:
        row = dict(row)
        row["citation_status"] = classify_citation_source(str(row.get("claim_or_context", "")), row.get("citation_status"))
        rows.append(row)

    # Deduplicate exact source/entity/context triples while preserving order.
    seen: set[tuple[str, str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row.get("source_type", "")), str(row.get("entity_id", "")), str(row.get("claim_or_context", "")))
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    return deduped

def write_citation_outputs(
    out_dir: Path,
    *,
    gene_evidence_csv: Path | None = None,
    comparator_tracks_csv: Path | None = None,
    lcms_handles_csv: Path | None = None,
    extra_rows: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = build_citation_rows(
        gene_evidence_csv=gene_evidence_csv,
        comparator_tracks_csv=comparator_tracks_csv,
        lcms_handles_csv=lcms_handles_csv,
        extra_rows=extra_rows,
    )
    fieldnames = [
        "source_type", "entity_id", "node", "claim_or_context", "citation_status",
        "pmid", "doi", "required_action", "claim_safety",
    ]
    workorder = out_dir / "Citation_Workorder.csv"
    with workorder.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})

    ledger = out_dir / "Citation_Ledger.csv"
    with ledger.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fieldnames + ["gate_status"])
        writer.writeheader()
        gate = gate_status(rows)
        for row in rows:
            out_row = {field: row.get(field, "") for field in fieldnames}
            out_row["gate_status"] = gate
            writer.writerow(out_row)

    md = out_dir / "Literature_WorkOrder.md"
    lines = [
        "# Literature / Citation Work Order",
        "",
        f"Gate status: **{gate_status(rows)}**",
        "",
        "Do not upgrade comparator context to product identity without primary verification.",
        "",
    ]
    for row in rows:
        lines.append(f"## {row.get('entity_id') or row.get('source_type')}")
        lines.append(f"- **Source type:** {row.get('source_type','')}")
        lines.append(f"- **Context:** {row.get('claim_or_context','')}")
        lines.append(f"- **Citation status:** {row.get('citation_status','')}")
        lines.append(f"- **Required action:** {row.get('required_action','')}")
        lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")

    receipt = {
        "row_count": len(rows),
        "gate_status": gate_status(rows),
        "outputs": {
            "citation_workorder": str(workorder),
            "citation_ledger": str(ledger),
            "literature_workorder": str(md),
        },
    }
    receipt_path = out_dir / "CITATION_RESOLUTION_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return {**receipt["outputs"], "receipt": str(receipt_path)}
