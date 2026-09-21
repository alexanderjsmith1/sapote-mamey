#!/usr/bin/env python3
"""Render exact-identity BiG-SCAPE widgets and integrate them into HTML reports.

Adaptive family labels use three deterministic modes: compact strain-plus-alias
labels for small families, collision-managed strain labels for medium families,
and focal labels plus hover/click details for dense families. Report integration
fails closed before writing if any selected locus lacks its authoritative alias.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import math
import re
from collections import defaultdict
from pathlib import Path

CLAIM_CEILING = (
    "GCF membership and direct edge distance are run- and cutoff-specific "
    "region-similarity context only; they do not establish pathway completeness, "
    "a shared or exact product, expression, production, activity, novelty, "
    "enrichment, host adaptation, or physical cross-contig linkage."
)
START_MARKER = "<!-- BIGSCAPE_REPORT_INTEGRATION_START -->"
END_MARKER = "<!-- BIGSCAPE_REPORT_INTEGRATION_END -->"
MIBIG_SUMMARY_START = "<!-- MIBIG_IDENTITY_SUMMARY_START -->"
MIBIG_SUMMARY_END = "<!-- MIBIG_IDENTITY_SUMMARY_END -->"
MIBIG_CONTEXT_START = "<!-- MIBIG_COMPARATOR_CONTEXT_START -->"
MIBIG_CONTEXT_END = "<!-- MIBIG_COMPARATOR_CONTEXT_END -->"
NOT_VERIFIED = "not verified in current evidence"
CLASS_UNAVAILABLE = "not available in bound MIBiG class source"
VERIFIED_EVIDENCE = "VERIFIED_PRIMARY_LITERATURE"
UNVERIFIED_EVIDENCE = "NOT_VERIFIED_CURRENT_EVIDENCE"
COMPARATOR_CAUTION = (
    "Characterized comparator context. These MIBiG fields describe the characterized "
    "comparator only and do not predict activity or mechanism for the focal locus."
)
COMPONENT_CLAIM_CEILING = (
    "Component-aware match density and core-marker presence support pathway-family context only. "
    "They do not establish exact product, pathway boundaries, completeness, expression, production, "
    "activity, mechanism, novelty, or release eligibility."
)
VOCABULARY_PATH = Path(__file__).resolve().parents[1] / "mamey" / "data" / "bigscape_class_vocabulary.json"


def read(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def safe_json(value):
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True).replace("</", "<\\/")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mibig_classes(json_dir, accessions):
    root = Path(json_dir)
    if not root.is_dir():
        raise ValueError("MIBIG_CONTEXT_GATE: --mibig-json-dir must be a directory")
    classes = {}
    sources = []
    for accession in sorted(accessions):
        source = root / f"{accession}.json"
        if not source.is_file():
            classes[accession] = CLASS_UNAVAILABLE
            continue
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"MIBIG_CONTEXT_GATE: unreadable JSON for {accession}: {error}") from error
        if payload.get("accession") != accession:
            raise ValueError(f"MIBIG_CONTEXT_GATE: accession mismatch for {accession}")
        labels = []
        for entry in (payload.get("biosynthesis") or {}).get("classes") or []:
            broad = str(entry.get("class") or "").strip()
            subtype = str(entry.get("subclass") or "").strip()
            label = broad
            if subtype and subtype.casefold() != "unknown":
                label = f"{broad} ({subtype})" if broad else subtype
            if label and label not in labels:
                labels.append(label)
        classes[accession] = "; ".join(labels) if labels else CLASS_UNAVAILABLE
        sources.append({
            "accession": accession,
            "file": source.name,
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
        })
    return classes, sources


def _curated_comparator_context(path):
    if not path:
        return {}, None
    source = Path(path)
    required = {
        "mibig_accession", "mibig_biosynthetic_class", "activity_category",
        "activity_verification_status", "mechanism_or_target", "mechanism_verification_status",
        "evidence_status", "pmid", "pmcid", "doi", "primary_literature_title", "source_url",
        "citation_identifiers", "citation_links", "evidence_locator", "hold_reason",
        "provenance_source", "provenance_sha256", "curator", "reviewed_at",
    }
    rows = read(source)
    if not rows or not required.issubset(rows[0]):
        raise ValueError("MIBIG_CONTEXT_GATE: curated context table has an incomplete schema")
    admitted = {}
    for row in rows:
        accession = row["mibig_accession"].strip()
        if not re.fullmatch(r"BGC\d{7}", accession):
            raise ValueError("MIBIG_CONTEXT_GATE: invalid MIBiG accession in curated context")
        activity_status = row["activity_verification_status"].strip()
        mechanism_status = row["mechanism_verification_status"].strip()
        if activity_status not in {VERIFIED_EVIDENCE, UNVERIFIED_EVIDENCE} or mechanism_status not in {
            VERIFIED_EVIDENCE, UNVERIFIED_EVIDENCE
        }:
            raise ValueError(f"MIBIG_CONTEXT_GATE: invalid field-level status for {accession}")
        activity = row["activity_category"].strip()
        mechanism = row["mechanism_or_target"].strip()
        for value, status, field in (
            (activity, activity_status, "activity_category"),
            (mechanism, mechanism_status, "mechanism_or_target"),
        ):
            if status == VERIFIED_EVIDENCE and (not value or value == NOT_VERIFIED):
                raise ValueError(f"MIBIG_CONTEXT_GATE: verified {field} is empty for {accession}")
            if status == UNVERIFIED_EVIDENCE and value != NOT_VERIFIED:
                raise ValueError(f"MIBIG_CONTEXT_GATE: unverified {field} contains a claim for {accession}")
        expected_evidence = (
            "ACTIVITY_AND_MECHANISM_VERIFIED_PRIMARY_LITERATURE"
            if activity_status == mechanism_status == VERIFIED_EVIDENCE
            else "ACTIVITY_VERIFIED_MECHANISM_NOT_VERIFIED"
            if activity_status == VERIFIED_EVIDENCE
            else UNVERIFIED_EVIDENCE
        )
        if row["evidence_status"].strip() != expected_evidence:
            raise ValueError(f"MIBIG_CONTEXT_GATE: inconsistent evidence status for {accession}")
        required_values = (
            "mibig_biosynthetic_class", "pmid", "primary_literature_title", "source_url",
            "citation_identifiers", "citation_links", "evidence_locator", "provenance_source",
            "provenance_sha256", "curator", "reviewed_at",
        )
        if not all(row[field].strip() for field in required_values):
            raise ValueError(f"MIBIG_CONTEXT_GATE: evidence row for {accession} lacks provenance")
        if (activity_status == UNVERIFIED_EVIDENCE or mechanism_status == UNVERIFIED_EVIDENCE) and not row["hold_reason"].strip():
            raise ValueError(f"MIBIG_CONTEXT_GATE: unresolved row for {accession} lacks a hold reason")
        hashes = [value.strip().lower() for value in row["provenance_sha256"].split("|") if value.strip()]
        sources = [value.strip() for value in row["provenance_source"].split("|") if value.strip()]
        if len(hashes) != len(sources) or any(not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes):
            raise ValueError(f"MIBIG_CONTEXT_GATE: invalid provenance binding for {accession}")
        for locator, expected_hash in zip(sources, hashes):
            locator_path = Path(locator)
            if locator_path.is_absolute() or ".." in locator_path.parts:
                raise ValueError(f"MIBIG_CONTEXT_GATE: unsafe provenance locator for {accession}")
            evidence_file = (source.parent / locator_path).resolve()
            try:
                evidence_file.relative_to(source.parent.resolve())
            except ValueError as error:
                raise ValueError(f"MIBIG_CONTEXT_GATE: provenance locator escapes table root for {accession}") from error
            if not evidence_file.is_file() or sha256(evidence_file) != expected_hash:
                raise ValueError(f"MIBIG_CONTEXT_GATE: missing or hash-mismatched evidence file for {accession}")
        links = [value.strip() for value in row["citation_links"].split("|") if value.strip()]
        if not links or any(not re.fullmatch(r"https?://[^\s]+", link) for link in links):
            raise ValueError(f"MIBIG_CONTEXT_GATE: unsafe or missing primary-literature link for {accession}")
        source_links = [value.strip() for value in row["source_url"].split("|") if value.strip()]
        if source_links != links:
            raise ValueError(f"MIBIG_CONTEXT_GATE: source and citation links differ for {accession}")
        pmids = [value.strip() for value in row["pmid"].split("|") if value.strip()]
        if len(pmids) != len(links) or any(not re.fullmatch(r"\d+", value) for value in pmids):
            raise ValueError(f"MIBIG_CONTEXT_GATE: invalid PMID binding for {accession}")
        normalized = {
            "mibig_biosynthetic_class": row["mibig_biosynthetic_class"].strip(),
            "activity_category": activity,
            "activity_verification_status": activity_status,
            "mechanism_or_target": mechanism,
            "mechanism_verification_status": mechanism_status,
            "evidence_status": expected_evidence,
            "pmid": pmids,
            "pmcid": [value.strip() for value in row["pmcid"].split("|") if value.strip()],
            "doi": [value.strip() for value in row["doi"].split("|") if value.strip()],
            "primary_literature_title": row["primary_literature_title"].strip(),
            "source_url": source_links,
            "citation_identifiers": [
                value.strip() for value in row["citation_identifiers"].split("|") if value.strip()
            ],
            "citation_links": links,
            "evidence_locator": row["evidence_locator"].strip(),
            "hold_reason": row["hold_reason"].strip(),
            "provenance_source": sources,
            "provenance_sha256": hashes,
            "curator": row["curator"].strip(),
            "reviewed_at": row["reviewed_at"].strip(),
        }
        if accession in admitted and admitted[accession] != normalized:
            raise ValueError(f"MIBIG_CONTEXT_GATE: conflicting curated rows for {accession}")
        admitted[accession] = normalized
    return admitted, {
        "file": source.name,
        "sha256": sha256(source),
        "bytes": source.stat().st_size,
        "rows": len(admitted),
        "activity_verified_rows": sum(
            row["activity_verification_status"] == VERIFIED_EVIDENCE for row in admitted.values()
        ),
        "mechanism_verified_rows": sum(
            row["mechanism_verification_status"] == VERIFIED_EVIDENCE for row in admitted.values()
        ),
    }


def _component_context(path):
    if not path:
        return {}, None
    source = Path(path)
    required = {
        "complete_identity", "mibig_accession", "whole_region_matched_cds",
        "whole_region_total_cds", "coherent_block_start_gene_order",
        "coherent_block_end_gene_order", "coherent_block_matched_cds",
        "local_component_denominator", "local_component_hit_fraction",
        "matched_cds_outside_selected_block", "gene_order_status",
        "core_completeness_status", "component_interpretation", "segmentation_hold",
        "evidence_source", "evidence_sha256", "claim_ceiling",
    }
    rows = read(source)
    if not rows or not required.issubset(rows[0]):
        raise ValueError("MIBIG_COMPONENT_GATE: component table has an incomplete schema")
    admitted = {}
    for row in rows:
        identity = row["complete_identity"].strip()
        parts = [part.strip() for part in identity.split(" / ")]
        accession = row["mibig_accession"].strip()
        if len(parts) != 4 or any(not part or part == "UNRESOLVED_BGC_ALIAS" for part in parts):
            raise ValueError("MIBIG_COMPONENT_GATE: incomplete locus identity")
        if not re.fullmatch(r"BGC\d{7}", accession):
            raise ValueError("MIBIG_COMPONENT_GATE: invalid MIBiG accession")
        try:
            whole_matched = int(row["whole_region_matched_cds"])
            whole_total = int(row["whole_region_total_cds"])
            block_start = int(row["coherent_block_start_gene_order"])
            block_end = int(row["coherent_block_end_gene_order"])
            block_matched = int(row["coherent_block_matched_cds"])
            local_total = int(row["local_component_denominator"])
            outside = int(row["matched_cds_outside_selected_block"])
            local_fraction = float(row["local_component_hit_fraction"])
        except ValueError as error:
            raise ValueError("MIBIG_COMPONENT_GATE: component counts must be numeric") from error
        if not (
            0 < whole_matched <= whole_total
            and 1 <= block_start <= block_end <= whole_total
            and local_total == block_end - block_start + 1
            and 0 < block_matched <= local_total
            and outside == whole_matched - block_matched >= 0
            and abs(local_fraction - block_matched / local_total) <= 0.000001
        ):
            raise ValueError("MIBIG_COMPONENT_GATE: inconsistent whole-region or component metrics")
        if row["component_interpretation"].strip() != "COMPONENT_SUPPORTED_PATHWAY_FAMILY_CONTEXT_ONLY":
            raise ValueError("MIBIG_COMPONENT_GATE: component interpretation exceeds the allowed vocabulary")
        if row["claim_ceiling"].strip() != COMPONENT_CLAIM_CEILING:
            raise ValueError("MIBIG_COMPONENT_GATE: claim ceiling mismatch")
        locator = Path(row["evidence_source"].strip())
        expected_hash = row["evidence_sha256"].strip().lower()
        if locator.is_absolute() or ".." in locator.parts or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
            raise ValueError("MIBIG_COMPONENT_GATE: unsafe evidence binding")
        evidence = (source.parent / locator).resolve()
        try:
            evidence.relative_to(source.parent.resolve())
        except ValueError as error:
            raise ValueError("MIBIG_COMPONENT_GATE: evidence locator escapes table root") from error
        if not evidence.is_file() or sha256(evidence) != expected_hash:
            raise ValueError("MIBIG_COMPONENT_GATE: missing or hash-mismatched evidence file")
        normalized = {
            "whole_matched": whole_matched, "whole_total": whole_total,
            "block_start": block_start, "block_end": block_end,
            "block_matched": block_matched, "local_total": local_total,
            "local_fraction": local_fraction, "outside": outside,
            "gene_order_status": row["gene_order_status"].strip(),
            "core_completeness_status": row["core_completeness_status"].strip(),
            "component_interpretation": row["component_interpretation"].strip(),
            "segmentation_hold": row["segmentation_hold"].strip(),
        }
        if not all(normalized[field] for field in (
            "gene_order_status", "core_completeness_status", "segmentation_hold"
        )):
            raise ValueError("MIBIG_COMPONENT_GATE: statuses must be explicit")
        key = (identity, accession)
        if key in admitted and admitted[key] != normalized:
            raise ValueError("MIBIG_COMPONENT_GATE: conflicting component rows")
        admitted[key] = normalized
    return admitted, {"file": source.name, "sha256": sha256(source), "bytes": source.stat().st_size, "rows": len(admitted)}


def _citation_html(context, accession_exists=False):
    if not context:
        exact = UNVERIFIED_EVIDENCE if accession_exists else "NO_ADMITTED_MIBIG_COMPARATOR"
        return _status_badge("—", exact, "unresolved" if accession_exists else "absent")
    identifiers = context["citation_identifiers"]
    links = context["citation_links"]
    rendered = []
    for index, link in enumerate(links):
        label = identifiers[index] if index < len(identifiers) else link
        rendered.append(
            f'<a href="{html.escape(link, quote=True)}" rel="noopener noreferrer">{html.escape(label)}</a>'
        )
    if len(identifiers) > len(links):
        rendered.extend(html.escape(value) for value in identifiers[len(links):])
    return "; ".join(rendered)


def _status_badge(label, exact_status, kind):
    return (
        f'<span class="mibig-status {html.escape(kind, quote=True)}" '
        f'data-evidence-status="{html.escape(exact_status, quote=True)}" '
        f'aria-label="{html.escape(exact_status, quote=True)}" '
        f'title="{html.escape(exact_status, quote=True)}">{html.escape(label)}</span>'
    )


def _context_field_html(value, field_status):
    if field_status == VERIFIED_EVIDENCE:
        return html.escape(value)
    return _status_badge("—", UNVERIFIED_EVIDENCE, "unresolved")


def _overall_status_html(context, accession_exists=False):
    if not context:
        if accession_exists:
            return _status_badge("Comparator context unresolved", UNVERIFIED_EVIDENCE, "unresolved")
        return _status_badge("No admitted comparator", "NO_ADMITTED_MIBIG_COMPARATOR", "absent")
    evidence = context["evidence_status"]
    if evidence == "ACTIVITY_AND_MECHANISM_VERIFIED_PRIMARY_LITERATURE":
        return _status_badge("Activity + mechanism verified", evidence, "verified")
    if evidence == "ACTIVITY_VERIFIED_MECHANISM_NOT_VERIFIED":
        return _status_badge("Activity verified; mechanism unresolved", evidence, "partial")
    return _status_badge("Comparator context unresolved", evidence, "unresolved")


def enhance_mibig_summary(source_html, mibig_json_dir, curated_context_path=None, component_context_path=None):
    if MIBIG_CONTEXT_START in source_html or MIBIG_CONTEXT_END in source_html:
        raise ValueError("MIBIG_CONTEXT_GATE: report already contains comparator-context fields")
    if source_html.count(MIBIG_SUMMARY_START) != 1 or source_html.count(MIBIG_SUMMARY_END) != 1:
        raise ValueError("MIBIG_CONTEXT_GATE: exactly one MIBiG identity summary block is required")
    start = source_html.index(MIBIG_SUMMARY_START)
    end = source_html.index(MIBIG_SUMMARY_END, start) + len(MIBIG_SUMMARY_END)
    block = source_html[start:end]
    tables = list(re.finditer(r"<table>.*?</table>", block, flags=re.DOTALL | re.IGNORECASE))
    if len(tables) != 1:
        raise ValueError("MIBIG_CONTEXT_GATE: exactly one MIBiG summary table is required")
    table = tables[0].group(0)
    rows = re.findall(r"<tr>.*?</tr>", table, flags=re.DOTALL | re.IGNORECASE)
    if len(rows) < 2:
        raise ValueError("MIBIG_CONTEXT_GATE: MIBiG summary table has no data rows")
    header_cells = re.findall(r"<th>(.*?)</th>", rows[0], flags=re.DOTALL | re.IGNORECASE)
    if header_cells[:3] != ["Rank", "Complete identity", "Comparator"]:
        raise ValueError("MIBIG_CONTEXT_GATE: unexpected MIBiG summary columns")
    parsed = []
    accessions = set()
    for row in rows[1:]:
        cells = re.findall(r"<td>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE)
        if len(cells) != len(header_cells):
            raise ValueError("MIBIG_CONTEXT_GATE: malformed MIBiG summary row")
        match = re.search(r"\bBGC\d{7}\b", re.sub(r"<[^>]+>", "", cells[2]))
        accession = match.group(0) if match else ""
        if accession:
            accessions.add(accession)
        parsed.append((cells, accession))
    classes, class_sources = _mibig_classes(mibig_json_dir, accessions)
    curated, curated_source = _curated_comparator_context(curated_context_path)
    components, component_source = _component_context(component_context_path)
    extra_headers = [
        "MIBiG biosynthetic class", "Reported activity category", "Reported mechanism or target",
        "Evidence status", "Primary literature", "Coherent component", "Architecture / segmentation",
    ]
    ordered_headers = header_cells[:3] + extra_headers + header_cells[3:]
    new_rows = ["<tr>" + "".join(f"<th>{value}</th>" for value in ordered_headers) + "</tr>"]
    class_bound = 0
    context_bound = 0
    activity_verified = 0
    mechanism_verified = 0
    any_verified = 0
    no_comparator = 0
    comparator_unresolved = 0
    component_bound = 0
    for cells, accession in parsed:
        identity = html.unescape(re.sub(r"<[^>]+>", "", cells[1])).strip()
        class_label = classes.get(accession, CLASS_UNAVAILABLE)
        if accession and class_label != CLASS_UNAVAILABLE:
            class_bound += 1
        context = curated.get(accession)
        if context:
            context_bound += 1
            if context["mibig_biosynthetic_class"] != class_label:
                raise ValueError(f"MIBIG_CONTEXT_GATE: class mismatch for {accession}")
            activity_is_verified = context["activity_verification_status"] == VERIFIED_EVIDENCE
            mechanism_is_verified = context["mechanism_verification_status"] == VERIFIED_EVIDENCE
            activity_verified += int(activity_is_verified)
            mechanism_verified += int(mechanism_is_verified)
            any_verified += int(activity_is_verified or mechanism_is_verified)
            comparator_unresolved += int(not activity_is_verified and not mechanism_is_verified)
            appended = f"<td>{html.escape(class_label)}</td>"
            appended += f'<td>{_context_field_html(context["activity_category"], context["activity_verification_status"])}</td>'
            appended += f'<td>{_context_field_html(context["mechanism_or_target"], context["mechanism_verification_status"])}</td>'
            appended += f"<td>{_overall_status_html(context)}</td>"
        else:
            no_comparator += int(not accession)
            comparator_unresolved += int(bool(accession))
            appended = f"<td>{html.escape(class_label) if accession else '—'}</td>"
            appended += f'<td>{_status_badge("—", "NO_ADMITTED_MIBIG_COMPARATOR" if not accession else UNVERIFIED_EVIDENCE, "absent" if not accession else "unresolved")}</td>'
            appended += f'<td>{_status_badge("—", "NO_ADMITTED_MIBIG_COMPARATOR" if not accession else UNVERIFIED_EVIDENCE, "absent" if not accession else "unresolved")}</td>'
            appended += f"<td>{_overall_status_html(None, bool(accession))}</td>"
        appended += f"<td>{_citation_html(context, bool(accession))}</td>"
        component = components.get((identity, accession))
        if component:
            component_bound += 1
            pct = 100 * component["local_fraction"]
            component_text = (
                f'{component["block_matched"]}/{component["local_total"]} matched in genes '
                f'{component["block_start"]}–{component["block_end"]} ({pct:.1f}%); '
                f'{component["whole_matched"]}/{component["whole_total"]} retained for the whole region'
            )
            architecture_text = (
                f'{component["core_completeness_status"]}; {component["segmentation_hold"]}. '
                'Merged flanks depress the whole-region fraction; component evidence does not raise product certainty.'
            )
            appended += f'<td data-component-status="{html.escape(component["gene_order_status"], quote=True)}">{html.escape(component_text)}</td>'
            appended += f'<td data-component-claim="{html.escape(component["component_interpretation"], quote=True)}">{html.escape(architecture_text)}</td>'
        else:
            badge = _status_badge("—", "NO_COMPONENT_INTERPRETATION_ADMITTED", "absent")
            appended += f"<td>{badge}</td><td>{badge}</td>"
        original_lead = "".join(f"<td>{cell}</td>" for cell in cells[:3])
        original_metrics = "".join(f"<td>{cell}</td>" for cell in cells[3:])
        new_rows.append("<tr>" + original_lead + appended + original_metrics + "</tr>")
    new_table = '<div class="mibig-table-wrap"><table class="mibig-comparator-table">' + "".join(new_rows) + "</table></div>"
    caution = (
        f'{MIBIG_CONTEXT_START}<style>.mibig-status{{display:inline-block;border-radius:999px;padding:.15rem .5rem;font-size:.78rem;font-weight:700;white-space:nowrap}}'
        '.mibig-status.verified{background:#dcefe5;color:#155c3f}.mibig-status.partial{background:#fff1c9;color:#71520a}'
        '.mibig-status.unresolved{background:#f3e7df;color:#7a4025}.mibig-status.absent{background:#eceff0;color:#4f5d61}'
        '.mibig-table-wrap{max-width:100%;overflow-x:auto;border:1px solid #d6dddd;background:#fff}'
        '.mibig-comparator-table{min-width:1880px;margin:0}.mibig-comparator-table th:nth-child(n+4):nth-child(-n+10){background:#0b7a75}'
        '.mibig-comparator-table td:nth-child(n+4):nth-child(-n+10){background:#f6faf8}</style>'
        f'<p class="caution mibig-comparator-context"><strong>'
        f'{html.escape(COMPARATOR_CAUTION)}</strong> Activity, mechanism/target, and primary-literature '
        f'fields remain <code>{html.escape(NOT_VERIFIED)}</code> unless admitted from a provenance-bearing '
        'curated table. A dash means that the specific field is unresolved. '
        '<em>No admitted comparator</em> is distinct from a characterized comparator whose activity or mechanism remains unresolved.'
        ' When an admitted coherent-component row is present, the original whole-region match count remains visible; '
        'the local denominator is an additional gene-order view for an overmerged region, with a boundary hold and no increase in product certainty.'
        f'</p>{MIBIG_CONTEXT_END}'
    )
    replacement = caution + new_table
    enhanced_block = block[:tables[0].start()] + replacement + block[tables[0].end():]
    output = source_html[:start] + enhanced_block + source_html[end:]
    receipt = {
        "status": "PASS",
        "rows": len(parsed),
        "unique_comparators": len(accessions),
        "class_bound_rows": class_bound,
        "class_unavailable_rows": len(parsed) - class_bound,
        "context_bound_rows": context_bound,
        "verified_context_rows": any_verified,
        "activity_verified_context_rows": activity_verified,
        "mechanism_verified_context_rows": mechanism_verified,
        "not_verified_context_rows": len(parsed) - any_verified,
        "no_admitted_comparator_rows": no_comparator,
        "comparator_context_unresolved_rows": comparator_unresolved,
        "class_sources": class_sources,
        "curated_context_source": curated_source,
        "component_context_source": component_source,
        "component_bound_rows": component_bound,
        "claim_ceiling": COMPARATOR_CAUTION,
    }
    return output, receipt


def label_mode(node_count):
    if node_count <= 3:
        return "SMALL_COMPACT_STRAIN_ALIAS"
    if node_count <= 8:
        return "MEDIUM_COLLISION_MANAGED_STRAIN"
    return "DENSE_FOCAL_LABEL_HOVER_CLICK"


def load_class_vocabulary(path=VOCABULARY_PATH):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = payload.get("entries") or []
    codes = [entry.get("code") for entry in entries]
    required = {"code", "full_name", "plain_language_meaning", "source_basis", "claim_ceiling"}
    if not entries or any(not code for code in codes) or len(codes) != len(set(codes)):
        raise ValueError("CLASS_GLOSSARY_GATE: vocabulary codes must be present and unique")
    if any(not required.issubset(entry) for entry in entries):
        raise ValueError("CLASS_GLOSSARY_GATE: every code requires a complete glossary entry")
    return payload


def _complete_identity_gate(rows, family_ids=None):
    selected = [row for row in rows if family_ids is None or str(row["family_id"]) in family_ids]
    unresolved = []
    for row in selected:
        parts = [
            str(row.get("strain", "")).strip(), str(row.get("full_node_or_contig", "")).strip(),
            str(row.get("region", "")).strip(), str(row.get("bgc_alias", "")).strip(),
        ]
        expected = " / ".join(parts)
        if (
            row.get("identity_status") != "COMPLETE"
            or any(not value for value in parts)
            or parts[-1] == "UNRESOLVED_BGC_ALIAS"
            or row.get("locus_display_with_hold") != expected
        ):
            unresolved.append(row)
    if unresolved:
        families = sorted({str(row["family_id"]) for row in unresolved})
        raise ValueError(
            f"EXACT_ALIAS_GATE: {len(unresolved)} selected records in families "
            f"{','.join(families)} lack authoritative BGC aliases"
        )
    return selected


def _boundary_state(row):
    value = row.get("boundary_state", "")
    if value:
        return value
    edge = str(row.get("contig_edge", ""))
    return "CONTIG_EDGE" if edge == "1" else "INTERIOR" if edge == "0" else "UNRESOLVED"


def family_payloads(membership, summaries, direct_edges=None, focal_strain="", family_ids=None, strict=True):
    rows = read(membership) if isinstance(membership, (str, Path)) else list(membership)
    summary_rows = read(summaries) if isinstance(summaries, (str, Path)) else list(summaries)
    edge_rows = [] if not direct_edges else read(direct_edges) if isinstance(direct_edges, (str, Path)) else list(direct_edges)
    selected_ids = None if family_ids is None else {str(value) for value in family_ids}
    if strict:
        rows = _complete_identity_gate(rows, selected_ids)
    elif selected_ids is not None:
        rows = [row for row in rows if str(row["family_id"]) in selected_ids]
    summary_by_id = {str(row["family_id"]): row for row in summary_rows}
    vocabulary = load_class_vocabulary()
    glossary_by_code = {entry["code"]: entry for entry in vocabulary["entries"]}
    by_family = defaultdict(list)
    for row in rows:
        by_family[str(row["family_id"])].append(row)
    edges_by_family = defaultdict(list)
    for row in edge_rows:
        edges_by_family[str(row["family_id"])].append(row)
    payloads = []
    for family_id, family_rows in sorted(by_family.items(), key=lambda item: int(item[0])):
        summary = summary_by_id.get(family_id, {})
        if selected_ids is not None and family_id not in selected_ids:
            continue
        if focal_strain and not any(row["strain"] == focal_strain for row in family_rows):
            continue
        nodes = []
        for row in sorted(family_rows, key=lambda value: (value["strain"], int(value["record_id"]))):
            nodes.append({
                "record_id": int(row["record_id"]),
                "strain": row["strain"],
                "alias": row["bgc_alias"],
                "compact_label": f"{row['strain']} {row['bgc_alias']}",
                "identity": row["locus_display_with_hold"],
                "identity_status": row["identity_status"],
                "genus": row.get("genus", "UNRESOLVED"),
                "host": row.get("host_as_deposited", "UNRESOLVED"),
                "host_group": row.get("host_group", "other"),
                "product": row.get("product", ""),
                "boundary_state": _boundary_state(row),
            })
        record_ids = {node["record_id"] for node in nodes}
        edges = []
        for row in edges_by_family.get(family_id, []):
            source = int(row["record_a_id"])
            target = int(row["record_b_id"])
            if source in record_ids and target in record_ids:
                edges.append({
                    "source": source,
                    "target": target,
                    "distance": float(row["distance"]),
                    "jaccard": float(row.get("jaccard") or 0),
                    "adjacency": float(row.get("adjacency") or 0),
                    "dss": float(row.get("dss") or 0),
                })
        cutoff = str(summary.get("cutoff") or family_rows[0].get("cutoff") or "UNRESOLVED")
        class_code = summary.get("class_code") or ""
        if class_code not in glossary_by_code:
            raise ValueError(f"CLASS_GLOSSARY_GATE: displayed code {class_code or 'BLANK'} has no unique entry")
        reviewed_code = summary.get("reviewed_subtype_code") or ""
        reviewed_glossary = None
        if reviewed_code:
            fields = {
                "code": reviewed_code,
                "full_name": summary.get("reviewed_subtype_full_name") or "",
                "plain_language_meaning": summary.get("reviewed_subtype_plain_language_meaning") or "",
                "source_basis": summary.get("reviewed_subtype_source_basis") or "",
                "claim_ceiling": summary.get("reviewed_subtype_claim_ceiling") or "",
            }
            if any(not value for value in fields.values()):
                raise ValueError(f"REVIEWED_SUBTYPE_GATE: incomplete glossary for {reviewed_code}")
            reviewed_glossary = fields
        payloads.append({
            "family_id": int(family_id),
            "cutoff": cutoff,
            "gcf_label": summary.get("gcf_label") or f"GCF_{int(family_id):04d}",
            "bin_label": summary.get("bin_label") or family_rows[0].get("bin_label", "UNRESOLVED"),
            "class_code": class_code,
            "class_nickname": glossary_by_code[class_code]["full_name"],
            "class_glossary": glossary_by_code[class_code],
            "full_glossary": vocabulary["entries"],
            "reviewed_subtype_code": reviewed_code,
            "reviewed_subtype_glossary": reviewed_glossary,
            "products": summary.get("products", ""),
            "label_mode": label_mode(len(nodes)),
            "focal_strain": focal_strain,
            "nodes": nodes,
            "edges": edges,
            "claim_ceiling": CLAIM_CEILING,
        })
    if selected_ids is not None:
        missing = sorted(selected_ids - {str(payload["family_id"]) for payload in payloads})
        if missing:
            raise ValueError(f"FAMILY_SELECTION_GATE: unavailable for focal strain: {','.join(missing)}")
    return payloads


CSS = """
.bigscape-report-integration{margin:34px 0}.bigscape-family-widget{background:#fff;border:1px solid #d7dfdf;border-radius:10px;padding:16px;margin:16px 0;box-shadow:0 2px 12px #0001}.bigscape-family-widget h3{margin:0 0 5px;color:#075d60}.bigscape-meta,.bigscape-claim,.bigscape-mode{font-size:13px;color:#52656a}.bigscape-family-widget svg{display:block;width:100%;height:auto;min-height:430px;background:#f8faf8;border:1px solid #dce4e2;border-radius:8px;margin:12px 0}.bigscape-edge{stroke:#8da1a2;stroke-opacity:.48}.bigscape-node{cursor:pointer}.bigscape-node circle{stroke:#fff;stroke-width:2}.bigscape-node text{font-size:12px;font-weight:700;fill:#17333b;paint-order:stroke;stroke:#fff;stroke-width:4px;stroke-linejoin:round}.bigscape-leader{stroke:#8da1a2;stroke-width:1}.bigscape-detail{min-height:52px;padding:10px 12px;background:#eef5f3;border-left:4px solid #087b7a;font-size:13px;line-height:1.45;overflow-wrap:anywhere}.bigscape-tip{position:fixed;z-index:50;display:none;max-width:480px;white-space:pre-wrap;background:#17373c;color:#fff;padding:9px 11px;border-radius:6px;pointer-events:none;font-size:12px;line-height:1.35}.bigscape-claim{margin-bottom:0}.bigscape-mode code{background:#edf1f0;padding:2px 5px;border-radius:4px}.bigscape-class-legend{border-top:1px solid #d7dfdf;margin-top:12px;padding-top:10px;font-size:13px;line-height:1.45}.bigscape-class-legend p{margin:4px 0}.bigscape-glossary{margin-top:9px}.bigscape-glossary table{font-size:12px}.bigscape-glossary th,.bigscape-glossary td{vertical-align:top}.bigscape-subtype{margin-top:8px;padding-left:10px;border-left:3px solid #d49a1f}@media(max-width:720px){.bigscape-family-widget svg{min-height:360px}}
""".strip()

JS = r"""
(function(){
const NS='http://www.w3.org/2000/svg';
const COLORS={bee:'#f28e2b',wasp:'#8e63ce',bee_or_wasp:'#e5b13d',ant:'#2a9d8f',other:'#9aa6b2'};
function el(tag,attrs,text){const x=document.createElementNS(NS,tag);Object.entries(attrs||{}).forEach(([k,v])=>x.setAttribute(k,v));if(text!==undefined)x.textContent=text;return x}
function tip(box,event,text){const t=box.closest('.bigscape-report-integration').querySelector('.bigscape-tip');if(!text){t.style.display='none';return}t.textContent=text;t.style.display='block';t.style.left=Math.min(event.clientX+12,window.innerWidth-500)+'px';t.style.top=Math.min(event.clientY+12,window.innerHeight-190)+'px'}
function detail(box,text){box.querySelector('.bigscape-detail').textContent=text}
function spreadLabels(items,minY,maxY,gap){items.sort((a,b)=>a.y-b.y);let cursor=minY;items.forEach(x=>{x.ly=Math.max(x.y,cursor);cursor=x.ly+gap});if(items.length&&items[items.length-1].ly>maxY){const shift=items[items.length-1].ly-maxY;items.forEach(x=>x.ly-=shift)}for(let i=items.length-2;i>=0;i--){if(items[i].ly>items[i+1].ly-gap)items[i].ly=items[i+1].ly-gap}}
function render(box){
 const d=JSON.parse(box.dataset.payload),svg=box.querySelector('svg'),W=960,H=500,cx=480,cy=245,r=d.label_mode.startsWith('DENSE')?185:165;
 svg.innerHTML='';const pos={};d.nodes.forEach((n,i)=>{const a=2*Math.PI*i/d.nodes.length-Math.PI/2;pos[n.record_id]={x:cx+r*Math.cos(a),y:cy+r*Math.sin(a),node:n}});
 d.edges.forEach(e=>{const a=pos[e.source],b=pos[e.target];if(!a||!b)return;const line=el('line',{x1:a.x,y1:a.y,x2:b.x,y2:b.y,class:'bigscape-edge','stroke-width':Math.max(1,3.4-3*e.distance)});const txt=`GCF ${d.family_id} · ${d.class_code}${d.reviewed_subtype_code?' · '+d.reviewed_subtype_code:''}; cutoff ${d.cutoff}\nDirect BiG-SCAPE edge distance ${e.distance.toFixed(4)}\n${a.node.identity}\n${b.node.identity}`;line.append(el('title',{},txt));line.onmousemove=ev=>tip(box,ev,txt);line.onmouseleave=()=>tip(box,null,null);line.onclick=()=>detail(box,txt);svg.append(line)});
 const medium=[];
 d.nodes.forEach(n=>{const p=pos[n.record_id];if(d.label_mode.startsWith('MEDIUM'))medium.push({node:n,x:p.x,y:p.y,side:p.x<cx?'left':'right'})});
 if(medium.length){spreadLabels(medium.filter(x=>x.side==='left'),52,H-52,25);spreadLabels(medium.filter(x=>x.side==='right'),52,H-52,25)}
 d.nodes.forEach(n=>{const p=pos[n.record_id],g=el('g',{class:'bigscape-node'}),c=el('circle',{cx:p.x,cy:p.y,r:12,fill:COLORS[n.host_group]||COLORS.other,stroke:n.boundary_state==='CONTIG_EDGE'?'#c15b3a':'#fff','stroke-width':n.boundary_state==='CONTIG_EDGE'?4:2});const info=`${n.identity}\nGCF ${d.family_id} · ${d.class_code}${d.reviewed_subtype_code?' · '+d.reviewed_subtype_code:''}; cutoff ${d.cutoff}\n${d.class_nickname}\n${n.genus}; host ${n.host}\nBoundary ${n.boundary_state}\n${n.product||'product unresolved'}\n${d.claim_ceiling}`;c.append(el('title',{},info));g.append(c);let shown='';if(d.label_mode.startsWith('SMALL'))shown=n.compact_label;else if(d.label_mode.startsWith('MEDIUM'))shown=n.strain;else if(n.strain===d.focal_strain)shown=n.compact_label;
   if(shown){let tx=p.x+17,ty=p.y+4,anchor='start';if(d.label_mode.startsWith('MEDIUM')){const m=medium.find(x=>x.node.record_id===n.record_id),left=m.side==='left';tx=left?180:780;ty=m.ly;anchor=left?'end':'start';g.append(el('line',{x1:p.x,y1:p.y,x2:tx+(left?8:-8),y2:ty-4,class:'bigscape-leader'}))}g.append(el('text',{x:tx,y:ty,'text-anchor':anchor},shown))}
   g.onmousemove=ev=>tip(box,ev,info);g.onmouseleave=()=>tip(box,null,null);g.onclick=()=>detail(box,info);svg.append(g)});
 detail(box,`Select a node or edge. ${d.nodes.length} loci; ${d.edges.length} direct distance records.`)
}
document.querySelectorAll('.bigscape-family-widget[data-payload]').forEach(render);
})();
""".strip()


def _widget_html(payload):
    encoded = html.escape(safe_json(payload), quote=True)
    mode_text = {
        "SMALL_COMPACT_STRAIN_ALIAS": "Small family: every node shows compact strain plus BGC alias.",
        "MEDIUM_COLLISION_MANAGED_STRAIN": "Medium family: strain labels are separated into collision-managed side columns.",
        "DENSE_FOCAL_LABEL_HOVER_CLICK": "Dense family: only the focal strain is labeled; every locus remains available by hover or click.",
    }[payload["label_mode"]]
    class_display = payload["class_code"]
    if payload["reviewed_subtype_code"]:
        class_display += f' · {payload["reviewed_subtype_code"]}'
    glossary = payload["class_glossary"]
    visible_legend = (
        '<div class="bigscape-class-legend" aria-label="Network class legend">'
        f'<p><strong>{html.escape(glossary["code"])} means {html.escape(glossary["full_name"])}</strong></p>'
        f'<p>{html.escape(glossary["plain_language_meaning"])}</p>'
        f'<p><strong>Source basis.</strong> {html.escape(glossary["source_basis"])}</p>'
        f'<p><strong>Class claim ceiling.</strong> {html.escape(glossary["claim_ceiling"])}</p>'
    )
    if payload["reviewed_subtype_glossary"]:
        subtype = payload["reviewed_subtype_glossary"]
        visible_legend += (
            '<div class="bigscape-subtype">'
            f'<p><strong>Reviewed subtype {html.escape(subtype["code"])} means {html.escape(subtype["full_name"])}</strong></p>'
            f'<p>{html.escape(subtype["plain_language_meaning"])}</p>'
            f'<p><strong>Source basis.</strong> {html.escape(subtype["source_basis"])}</p>'
            f'<p><strong>Subtype claim ceiling.</strong> {html.escape(subtype["claim_ceiling"])}</p></div>'
        )
    rows = "".join(
        '<tr>'
        f'<td><code>{html.escape(entry["code"])}</code></td>'
        f'<td>{html.escape(entry["full_name"])}</td>'
        f'<td>{html.escape(entry["plain_language_meaning"])}</td>'
        f'<td>{html.escape(entry["source_basis"])}</td>'
        f'<td>{html.escape(entry["claim_ceiling"])}</td>'
        '</tr>'
        for entry in payload["full_glossary"]
    )
    visible_legend += (
        '<details class="bigscape-glossary"><summary>Open the full BiG-SCAPE class glossary</summary>'
        '<table><thead><tr><th>Code</th><th>Full name</th><th>Plain-language meaning</th><th>Source basis</th><th>Claim ceiling</th></tr></thead>'
        f'<tbody>{rows}</tbody></table></details></div>'
    )
    return (
        f'<article class="bigscape-family-widget" data-payload="{encoded}">'
        f'<h3>GCF {payload["family_id"]} · {html.escape(class_display)}</h3>'
        f'<p class="bigscape-meta">{html.escape(payload["class_nickname"])} · cutoff {html.escape(payload["cutoff"])} · '
        f'{len(payload["nodes"])} loci · {html.escape(payload["bin_label"])} · '
        f'{len(payload["edges"])} direct distance records</p>'
        f'<p class="bigscape-mode"><code>{payload["label_mode"]}</code> {mode_text}</p>'
        '<svg viewBox="0 0 960 500" role="img" aria-label="Interactive BiG-SCAPE family network"></svg>'
        '<div class="bigscape-detail" aria-live="polite"></div>'
        f'{visible_legend}'
        f'<p class="bigscape-claim"><strong>Claim ceiling.</strong> {html.escape(CLAIM_CEILING)}</p>'
        '</article>'
    )


def report_section(payloads, focal_strain):
    body = "".join(_widget_html(payload) for payload in payloads)
    return (
        f"{START_MARKER}<style>{CSS}</style>"
        f'<section class="bigscape-report-integration"><h2>BiG-SCAPE cross-strain family context</h2>'
        f'<p>This section places selected complete-identity loci from {html.escape(focal_strain)} into '
        'their run- and cutoff-specific GCF neighborhoods. Node hover and click detail preserve the complete '
        '<code>strain / full node-or-contig / region / BGC alias</code> identity.</p>'
        f"{body}<div class=\"bigscape-tip\"></div></section><script>{JS}</script>{END_MARKER}"
    )


def integrate_report_html(
    report_html, out_path, membership, summaries, direct_edges, focal_strain, family_ids,
    mibig_json_dir=None, curated_comparator_context=None, comparator_component_context=None,
):
    payloads = family_payloads(
        membership, summaries, direct_edges, focal_strain=focal_strain,
        family_ids=family_ids, strict=True,
    )
    if not payloads:
        raise ValueError(f"REPORT_INTEGRATION_GATE: no selected families for {focal_strain}")
    source = Path(report_html).read_text(encoding="utf-8")
    mibig_receipt = None
    if curated_comparator_context and not mibig_json_dir:
        raise ValueError("MIBIG_CONTEXT_GATE: curated context requires --mibig-json-dir")
    if mibig_json_dir:
        source, mibig_receipt = enhance_mibig_summary(
            source, mibig_json_dir, curated_comparator_context, comparator_component_context,
        )
    section = report_section(payloads, focal_strain)
    if START_MARKER in source or END_MARKER in source:
        raise ValueError("REPORT_INTEGRATION_GATE: report already contains an integration block")
    anchor = "<h2>Claim ceiling</h2>"
    if anchor not in source:
        raise ValueError("REPORT_INTEGRATION_GATE: claim ceiling insertion anchor not found")
    output = source.replace(anchor, section + anchor, 1)
    Path(out_path).write_text(output, encoding="utf-8")
    return {
        "status": "PASS",
        "out_locator": Path(out_path).name,
        "strain": focal_strain,
        "families": [payload["family_id"] for payload in payloads],
        "label_modes": [payload["label_mode"] for payload in payloads],
        "nodes": sum(len(payload["nodes"]) for payload in payloads),
        "direct_edges": sum(len(payload["edges"]) for payload in payloads),
        "claim_ceiling": CLAIM_CEILING,
        "mibig_comparator_context": mibig_receipt,
    }


def _strain_network(membership, pairwise):
    rows = read(membership)
    pairs = read(pairwise)
    by_strain = defaultdict(set)
    metadata = {}
    for row in rows:
        by_strain[row["strain"]].add(int(row["family_id"]))
        metadata[row["strain"]] = {
            "genus": row.get("genus", "UNRESOLVED"),
            "host": row.get("host_as_deposited", "UNRESOLVED"),
            "group": row.get("host_group", "other"),
        }
    nodes = []
    for index, strain in enumerate(sorted(by_strain)):
        angle = 2 * math.pi * index / max(1, len(by_strain))
        nodes.append({
            "id": strain, **metadata[strain], "gcf_count": len(by_strain[strain]),
            "x": 500 + 300 * math.cos(angle), "y": 360 + 300 * math.sin(angle),
        })
    edges = [
        {
            "a": row["strain_a"], "b": row["strain_b"],
            "shared": int(row["shared_gcf_count"]), "jaccard": float(row["jaccard"]),
        }
        for row in pairs if int(row["shared_gcf_count"])
    ]
    payload = html.escape(safe_json({"nodes": nodes, "edges": edges}), quote=True)
    return f"""<!doctype html><html><head><meta charset=utf-8><title>Labeled strain network</title><style>{CSS}body{{font:14px system-ui;margin:20px;background:#f5f4ee;color:#17333b}}</style></head><body><h1>Labeled strain GCF-sharing network</h1><p>{html.escape(CLAIM_CEILING)}</p><pre data-payload="{payload}">Portable strain network data are embedded for downstream rendering.</pre></body></html>"""


def build(
    membership, summary, pairwise, outdir, direct_edges=None, focal_strain="",
    require_complete_alias=False, family_ids=None,
):
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    payloads = family_payloads(
        membership, summary, direct_edges, focal_strain=focal_strain,
        family_ids=family_ids, strict=require_complete_alias,
    )
    family_page = (
        f"<!doctype html><html><head><meta charset=utf-8><title>Labeled GCF network explorer</title>"
        f"<style>{CSS}body{{font:14px system-ui;margin:20px;background:#f5f4ee;color:#17333b}}</style>"
        f"</head><body><h1>Labeled cross-strain GCF explorer</h1><div class=\"bigscape-report-integration\">"
        + "".join(_widget_html(payload) for payload in payloads)
        + f'<div class="bigscape-tip"></div></div><script>{JS}</script></body></html>'
    )
    (out / "GCF_NETWORK_EXPLORER.html").write_text(family_page, encoding="utf-8")
    (out / "STRAIN_SHARING_NETWORK.html").write_text(_strain_network(membership, pairwise), encoding="utf-8")
    counts = defaultdict(int)
    for payload in payloads:
        counts[payload["label_mode"]] += 1
    return {
        "status": "PASS",
        "families": len(payloads),
        "family_nodes": sum(len(payload["nodes"]) for payload in payloads),
        "direct_edges": sum(len(payload["edges"]) for payload in payloads),
        "label_mode_counts": dict(counts),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--membership", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--pairwise", required=True)
    parser.add_argument("--direct-edges")
    parser.add_argument("--out", required=True)
    parser.add_argument("--focal-strain", default="")
    parser.add_argument("--require-complete-alias", action="store_true")
    parser.add_argument("--report-html")
    parser.add_argument("--report-out")
    parser.add_argument("--strain")
    parser.add_argument("--family-id", action="append", default=[])
    parser.add_argument("--mibig-json-dir")
    parser.add_argument("--curated-comparator-context")
    parser.add_argument("--comparator-component-context")
    parser.add_argument("--report-receipt-out")
    args = parser.parse_args(argv)
    try:
        result = build(
            args.membership, args.summary, args.pairwise, args.out,
            args.direct_edges, args.focal_strain or args.strain or "",
            args.require_complete_alias or bool(args.report_html),
            args.family_id or None,
        )
        if args.report_html:
            if not (args.report_out and args.strain and args.direct_edges and args.family_id):
                raise ValueError(
                    "REPORT_INTEGRATION_GATE: --report-out, --strain, --direct-edges, and --family-id are required"
                )
            result["report_integration"] = integrate_report_html(
                args.report_html, args.report_out, args.membership, args.summary,
                args.direct_edges, args.strain, args.family_id,
                args.mibig_json_dir, args.curated_comparator_context,
                args.comparator_component_context,
            )
            if args.report_receipt_out:
                Path(args.report_receipt_out).write_text(
                    json.dumps(result["report_integration"], indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
    except ValueError as error:
        raise SystemExit(str(error))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
