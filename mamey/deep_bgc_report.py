"""Portable, fail-closed deep BGC report builder."""
from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path
from typing import Any

from .csv_safety import SafeDictWriter
from .exact_identity import ExactLocusIdentityError, exact_locus_display


class DeepBGCReportError(ValueError):
    """Raised before output when identity, gene slice, or evidence is unsafe."""


def _cell(value: object) -> str:
    return str(value).replace("|", "\\|")


IDENTITY_KEYS = ("strain", "full_node_or_contig", "region", "bgc_alias")


def _identity(record: dict[str, Any]) -> tuple[dict[str, str], str]:
    ident = {key: str(record.get(key, "")).strip() for key in IDENTITY_KEYS}
    try:
        display = exact_locus_display(*(ident[key] for key in IDENTITY_KEYS))
    except ExactLocusIdentityError as exc:
        raise DeepBGCReportError(str(exc)) from exc
    return ident, display


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_locus(path: Path) -> tuple[dict[str, Any], dict[str, str], str]:
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise DeepBGCReportError("locus record must be a JSON object")
    identity, display = _identity(record)
    genes = record.get("genes")
    if not isinstance(genes, list) or not genes:
        raise DeepBGCReportError("canonical genes must be a non-empty list")
    declared = record.get("canonical_gene_count")
    if not isinstance(declared, int) or declared != len(genes):
        raise DeepBGCReportError("gene-slice mismatch: canonical_gene_count differs from genes")
    seen: set[str] = set()
    last_start = -1
    for gene in genes:
        if not isinstance(gene, dict):
            raise DeepBGCReportError("every canonical gene must be an object")
        gene_id = str(gene.get("gene_id", "")).strip()
        if not gene_id or gene_id in seen:
            raise DeepBGCReportError("canonical gene_id is missing or duplicated")
        seen.add(gene_id)
        try:
            start, end = int(gene["start"]), int(gene["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise DeepBGCReportError(f"invalid coordinates for {gene_id}") from exc
        if start < 1 or end < start or start < last_start:
            raise DeepBGCReportError(f"invalid or unordered coordinates for {gene_id}")
        if gene.get("strand") not in {"+", "-"}:
            raise DeepBGCReportError(f"invalid strand for {gene_id}")
        last_start = start
    boundary = record.get("boundary")
    if not isinstance(boundary, dict) or boundary.get("status") not in {
        "COMPLETE", "PARTIAL", "OVERMERGED_SUSPECTED", "UNRESOLVED"
    }:
        raise DeepBGCReportError("boundary.status is missing or unsupported")
    return record, identity, display


def _load_evidence(path: Path | None, identity: dict[str, str], genes: dict[str, dict[str, Any]]) -> tuple[list[dict[str, str]], int, int]:
    """Return the admitted rows and how many had their protein hash actually compared.

    Protein hashes are compared only when the locus record supplies one, which is
    the documented contract. The caller records the resulting binding state on the
    receipt so a reader can tell a hash-bound report from an identity-bound one.
    """
    if path is None:
        return [], 0, 0
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    hash_checked = 0
    hash_unverifiable = 0
    for row in rows:
        supplied = {key: str(row.get(key, "")).strip() for key in IDENTITY_KEYS}
        if supplied != identity:
            raise DeepBGCReportError("evidence exact identity mismatch; alias-only matching is forbidden")
        gene_id = str(row.get("gene_id", "")).strip()
        if gene_id not in genes:
            raise DeepBGCReportError(f"evidence gene {gene_id!r} is outside canonical gene slice")
        expected = str(genes[gene_id].get("protein_sha256", "")).strip()
        observed = str(row.get("protein_sha256", "")).strip()
        if expected and observed != expected:
            raise DeepBGCReportError(f"protein hash mismatch for {gene_id}")
        if expected:
            hash_checked += 1
        elif observed:
            # Evidence supplied a protein hash but the canonical gene carries none to
            # check it against. Admission is unchanged (documented optional-hash contract),
            # but the claimed hash could not be verified, so surface it on the receipt.
            hash_unverifiable += 1
    return rows, hash_checked, hash_unverifiable


def _locus_svg(record: dict[str, Any], display: str) -> str:
    genes = record["genes"]
    lo, hi = min(int(g["start"]) for g in genes), max(int(g["end"]) for g in genes)
    span = max(1, hi - lo)
    width = 980
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="180" viewBox="0 0 {width} 180">',
             '<rect width="100%" height="100%" fill="white"/>',
             f'<text x="20" y="28" font-family="sans-serif" font-size="15" font-weight="bold">{html.escape(display)}</text>',
             '<line x1="30" y1="105" x2="950" y2="105" stroke="#555" stroke-width="2"/>']
    palette = {"core": "#0F766E", "tailoring": "#D97706", "transport": "#2563EB", "regulation": "#7C3AED"}
    for gene in genes:
        start, end = int(gene["start"]), int(gene["end"])
        x1 = 30 + 900 * (start - lo) / span
        x2 = 30 + 900 * (end - lo) / span
        color = palette.get(str(gene.get("role", "")).lower(), "#64748B")
        if gene["strand"] == "+":
            points = f"{x1:.1f},88 {max(x1, x2-10):.1f},88 {x2:.1f},105 {max(x1, x2-10):.1f},122 {x1:.1f},122"
        else:
            points = f"{x2:.1f},88 {min(x2, x1+10):.1f},88 {x1:.1f},105 {min(x2, x1+10):.1f},122 {x2:.1f},122"
        parts.append(f'<polygon points="{points}" fill="{color}" stroke="#334155"/>')
        parts.append(f'<text x="{(x1+x2)/2:.1f}" y="145" text-anchor="middle" font-family="sans-serif" font-size="9">{html.escape(str(gene["gene_id"]))}</text>')
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


def _binding_state(genes: dict[str, dict[str, Any]], evidence: list[dict[str, str]], hash_checked: int, hash_unverifiable: int) -> dict[str, Any]:
    """Describe how strongly the admitted evidence is bound to the canonical slice.

    Admission is unchanged: hashes are compared only when the locus record supplies
    one. This records whether that comparison actually happened, so "hash-bound
    receipt" can be checked rather than assumed by a downstream consumer.
    """
    with_hash = sum(1 for gene in genes.values() if str(gene.get("protein_sha256", "")).strip())
    if not evidence:
        state = "NO_EVIDENCE_SUPPLIED"
    elif hash_checked == len(evidence):
        state = "PROTEIN_HASH_BOUND"
    elif hash_checked:
        state = "PARTIALLY_PROTEIN_HASH_BOUND"
    else:
        state = "EXACT_IDENTITY_BOUND_ONLY"
    return {
        "state": state,
        "canonical_genes_total": len(genes),
        "canonical_genes_carrying_hash": with_hash,
        "evidence_rows_total": len(evidence),
        "evidence_rows_hash_compared": hash_checked,
        "evidence_rows_hash_unverifiable": hash_unverifiable,
    }


def build_deep_report(locus_json: Path, output_dir: Path, evidence_tsv: Path | None = None) -> dict[str, Any]:
    record, identity, display = load_and_validate_locus(locus_json)
    genes = {str(g["gene_id"]): g for g in record["genes"]}
    evidence, evidence_hash_checked, evidence_hash_unverifiable = _load_evidence(evidence_tsv, identity, genes)
    output_dir.mkdir(parents=True, exist_ok=True)
    roster = output_dir / "GENE_ROSTER.tsv"
    fields = ["strain", "full_node_or_contig", "region", "bgc_alias", "gene_id", "start", "end", "strand", "role", "product", "domains", "protein_sha256"]
    with roster.open("w", newline="", encoding="utf-8") as handle:
        writer = SafeDictWriter(handle, delimiter="\t", fieldnames=fields)
        writer.writeheader()
        for gene in record["genes"]:
            row = dict(identity, **{key: gene.get(key, "") for key in fields if key not in identity})
            row["domains"] = "; ".join(gene.get("domains", []))
            writer.writerow(row)
    locus_map = output_dir / "LOCUS_MAP.svg"
    locus_map.write_text(_locus_svg(record, display), encoding="utf-8")
    boundary = record["boundary"]
    components = record.get("comparator_components", [])
    lines = [f"# {display}", "", "## Claim ceiling", "",
             str(record.get("claim_ceiling", "Class-level biosynthetic hypothesis only; product identity and activity are unresolved.")), "",
             "## Boundary assessment", "", f"Status: **{boundary['status']}**. {boundary.get('note', '')}", ""]
    if "whole_region_matched_cds" in record and "whole_region_total_cds" in record:
        matched, total = int(record["whole_region_matched_cds"]), int(record["whole_region_total_cds"])
        if total < 1 or matched < 0 or matched > total:
            raise DeepBGCReportError("invalid whole-region CDS fraction")
        lines += [f"Whole-region comparator fraction: **{matched}/{total} ({100*matched/total:.1f}%)**.", ""]
    if components:
        lines += ["Coherent matched components are reported separately from the whole-region denominator; this preserves boundary uncertainty and does not resolve product identity.", "", "| Component | CDS | Core completeness | Gene order |", "|---|---:|---|---|"]
        for comp in components:
            lines.append(f"| {_cell(comp.get('name','unresolved'))} | {comp.get('matched_cds','?')}/{comp.get('local_total_cds','?')} | {_cell(comp.get('core_completeness','unresolved'))} | {_cell(comp.get('gene_order','unresolved'))} |")
        lines.append("")
    lines += ["## Gene and domain architecture", "", "| Gene | Coordinates | Strand | Role | Product | Domains |", "|---|---:|:---:|---|---|---|"]
    for gene in record["genes"]:
        lines.append(f"| {_cell(gene['gene_id'])} | {gene['start']}-{gene['end']} | {gene['strand']} | {_cell(gene.get('role','unresolved'))} | {_cell(gene.get('product','unresolved'))} | {_cell('; '.join(gene.get('domains', [])) or 'not supplied')} |")
    lines += ["", "## Evidence channels", "", f"Bound evidence rows: **{len(evidence)}**. Missing channels remain workflow gaps and are not negative findings.", "", "## Comparator interpretation", "", "MIBiG and other reference matches are navigation evidence. A family-level interpretation requires coherent core biosynthetic architecture and supporting context, not an isolated match.", ""]
    report = output_dir / "DEEP_BGC_REPORT.md"
    report.write_text("\n".join(lines), encoding="utf-8")
    receipt = {
        "schema": "sapote.deep_bgc_report.receipt.v1", "exact_locus": display,
        "identity": identity, "canonical_gene_count": len(genes), "evidence_row_count": len(evidence),
        "boundary_status": boundary["status"], "inputs": {"locus_json": {"name": locus_json.name, "sha256": _sha256(locus_json)}},
        "protein_hash_binding": _binding_state(genes, evidence, evidence_hash_checked, evidence_hash_unverifiable),
        "outputs": {}
    }
    if evidence_tsv:
        receipt["inputs"]["evidence_tsv"] = {"name": evidence_tsv.name, "sha256": _sha256(evidence_tsv)}
    for path in (report, roster, locus_map):
        receipt["outputs"][path.name] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
    receipt_path = output_dir / "REPORT_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt
