"""Normalized, report-only antiSMASH evidence tables.

The tables in this module preserve antiSMASH module, RiPP precursor, motif,
and RRE-Finder evidence with stable schemas and explicit BGC mapping state.
They are evidence/reporting surfaces only and are not consumed by scoring.
"""
from __future__ import annotations

from dataclasses import asdict
import json
import re
from typing import Any, Iterable

from .parsers import (
    extract_antismash_version,
    extract_cds_features,
    extract_domain_features,
)


SCHEMA_VERSION = "antismash_structured_tables_v2"
REPORT_ONLY_CONTRACT = "REPORT_ONLY_NO_SCORING"
CLAIM_SAFETY = (
    "antiSMASH module, motif, RiPP, and RRE-Finder calls are annotation and "
    "capacity evidence. They do not prove product identity, expression, "
    "production, resistance, bioactivity, novelty, or cross-contig linkage."
)

MODULE_COLUMNS = [
    "row_id", "bgc_id", "mapping_status", "mapping_method", "contig",
    "start", "end", "strand", "evidence_type", "feature_type", "locus_tag",
    "domain", "database", "bitscore", "evalue", "substrate_consensus",
    "prediction_summary", "source_file", "source_schema",
    "source_schema_version", "detail_json", "claim_safety",
]
RIPP_MOTIF_COLUMNS = [
    "row_id", "bgc_id", "mapping_status", "mapping_method", "contig",
    "start", "end", "strand", "evidence_type", "module", "ripp_family",
    "locus_tag", "motif_index", "peptide_class", "peptide_subclass",
    "core_sequence", "leader", "tail", "score", "tool", "source_file",
    "source_schema", "source_schema_version", "detail_json", "claim_safety",
]
MOTIF_COLUMNS = [
    "row_id", "bgc_id", "mapping_status", "mapping_method", "contig",
    "start", "end", "strand", "evidence_type", "feature_type", "locus_tag",
    "motif", "database", "bitscore", "evalue", "source_file",
    "source_schema", "source_schema_version", "qualifiers_json",
    "claim_safety",
]
RREFINDER_COLUMNS = [
    "row_id", "record_id", "contig", "bgc_id", "mapping_status",
    "mapping_method", "protoclusters", "locus_tag", "start", "end", "strand",
    "rre_family", "rre_description", "rrefam_identifier", "evalue",
    "bitscore", "protein_start", "protein_end", "antismash_product_context",
    "source_file", "source_schema", "source_schema_version",
    "antismash_version", "bitscore_cutoff", "minimum_protein_length",
    "claim_safety",
]
HMM_COLUMNS = [
    "row_id", "bgc_id", "mapping_status", "mapping_method", "region_key",
    "locus_tag", "hmm_database", "domain_name", "accession", "description",
    "evalue", "bitscore", "tier1_diagnostic", "source_schema", "claim_safety",
]
TABLE_COLUMNS = {
    "modules": MODULE_COLUMNS,
    "ripp_motifs": RIPP_MOTIF_COLUMNS,
    "motifs": MOTIF_COLUMNS,
    "rrefinder": RREFINDER_COLUMNS,
    "hmm": HMM_COLUMNS,
}


def build_hmm_table(zip_path, bgcs, precomputed_hits=None) -> list[dict[str, Any]]:
    """First-class PFAM (sec_met_domain) + diagnostic TIGRFAM HMM hits.

    These live only in the antiSMASH region GBKs / JSON and were previously not
    surfaced as a standalone table (the module table carries aSDomain/RREFam rows,
    not Pfam/TIGRFAM). Report-only, BGC-mapped via each record's source region GBK.

    precomputed_hits — the Pfam+TIGRFAM hits the run already merged (the CLI stores
        them on antismash_evidence["gbk_pfam_hits"] after its SINGLE record pass).
        When threaded in (is not None), reuse them verbatim; re-extracting here would
        make a SECOND full tigrfam record pass over the JSON — the double-record-pass
        regression guarded by tests/test_record_pass_count.py. Falls back to a fresh
        extract+merge only when nothing was threaded in (direct/standalone callers, or
        a run whose GBK-Pfam extraction failed before the merge).
    """
    from .antismash_evidence import (
        extract_gbk_pfam_hits,
        extract_tigrfam_hits,
        merge_tigrfam_into_pfam_hits,
        _region_key_from_name,
    )
    bgcs = list(bgcs or [])
    region_to_bgc: dict[str, str] = {}
    for bgc in bgcs:
        _, _, region_key = _region_key_from_name(str(_value(bgc, "source_gbk", "") or ""))
        if region_key:
            region_to_bgc.setdefault(region_key, str(_value(bgc, "bgc_id", "")))
    try:
        if precomputed_hits is not None:
            # Reuse the run's already-merged Pfam+TIGRFAM hits (no second record pass).
            merged = precomputed_hits
        else:
            merged = merge_tigrfam_into_pfam_hits(
                extract_gbk_pfam_hits(zip_path), extract_tigrfam_hits(zip_path)
            )
    except Exception as exc:
        # v9.7.371 fix: was a bare swallow. build_hmm_table's OWN caller (build_structured_tables)
        # only appends to parse_errors if build_hmm_table itself raises -- this inner except let
        # build_hmm_table return normally (rows=[]) on a genuine extraction failure, indistinguishable
        # downstream from "this strain genuinely has no PFAM/TIGRFAM hits".
        from . import degradation as _degradation
        _degradation.record("antismash_tables.build_hmm_table.merge", exc, zip_path=str(zip_path))
        merged = {}
    rows: list[dict[str, Any]] = []
    for region_key, hits in (merged or {}).items():
        bgc_id = region_to_bgc.get(region_key, "UNMAPPED")
        mapping_status = "MAPPED" if bgc_id != "UNMAPPED" else "UNMAPPED_NO_REGION_MATCH"
        for hit in hits or []:
            acc = str(hit.get("pfam_acc") or hit.get("tigrfam_acc") or hit.get("accession") or "")
            database = "TIGRFAM" if acc.upper().startswith("TIGR") else ("Pfam" if acc.upper().startswith("PF") else str(hit.get("database") or "HMM"))
            rows.append({
                "bgc_id": bgc_id,
                "mapping_status": mapping_status,
                "mapping_method": "SOURCE_REGION_KEY",
                "region_key": region_key,
                "locus_tag": str(hit.get("locus_tag") or ""),
                "hmm_database": database,
                "domain_name": str(hit.get("domain_name") or ""),
                "accession": acc,
                "description": str(hit.get("description") or ""),
                "evalue": hit.get("evalue", ""),
                "bitscore": hit.get("bitscore", ""),
                "tier1_diagnostic": bool(hit.get("tier1_diagnostic", False)),
                "source_schema": "antismash_sec_met_domain+tigrfam",
                "claim_safety": CLAIM_SAFETY,
            })
    _assign_row_ids("HMM", rows, HMM_COLUMNS)
    return rows


def _value(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _parse_location(value: Any) -> tuple[int | None, int | None, int]:
    """Convert antiSMASH's zero-based half-open location to 1-based inclusive."""
    match = re.search(r"[<\[]?(\d+)\s*:\s*>?(\d+)", str(value or ""))
    if not match:
        return None, None, 0
    start = int(match.group(1)) + 1
    end = int(match.group(2))
    strand_match = re.search(r"\(([+-])\)", str(value or ""))
    strand = -1 if strand_match and strand_match.group(1) == "-" else (
        1 if strand_match else 0
    )
    return start, end, strand


def _same_contig(left: str, right: str) -> bool:
    return str(left or "") == str(right or "")


def _map_interval(
    contig: str,
    start: int | None,
    end: int | None,
    bgcs: Iterable[Any],
) -> tuple[str, str, str, list[Any]]:
    if not contig or start is None or end is None:
        return "UNMAPPED", "UNMAPPED_NO_COORDINATES", "NO_COORDINATE", []
    candidates = [
        bgc for bgc in bgcs
        if _same_contig(contig, _value(bgc, "contig", ""))
        and int(_value(bgc, "start", 0) or 0) <= int(end)
        and int(_value(bgc, "end", 0) or 0) >= int(start)
    ]
    if len(candidates) == 1:
        return (
            str(_value(candidates[0], "bgc_id", "UNMAPPED")),
            "MAPPED",
            "COORDINATE_OVERLAP",
            candidates,
        )
    if len(candidates) > 1:
        return "UNMAPPED", "AMBIGUOUS_MULTIPLE_BGC_OVERLAPS", "COORDINATE_OVERLAP", candidates
    return "UNMAPPED", "UNMAPPED_NO_BGC_OVERLAP", "COORDINATE_OVERLAP", []


def _source_member_map(source_file: str, bgcs: Iterable[Any]) -> tuple[str, str, str]:
    candidates = [
        bgc for bgc in bgcs
        if str(_value(bgc, "source_gbk", "")) == str(source_file or "")
    ]
    if len(candidates) == 1:
        return str(_value(candidates[0], "bgc_id", "UNMAPPED")), "MAPPED", "SOURCE_GBK_MEMBER"
    if len(candidates) > 1:
        return "UNMAPPED", "AMBIGUOUS_SOURCE_GBK", "SOURCE_GBK_MEMBER"
    return "UNMAPPED", "UNMAPPED_NO_BGC_OVERLAP", "SOURCE_GBK_MEMBER"


def _locus_index(cds_features: Iterable[Any]) -> tuple[dict[tuple[str, str], Any], dict[str, list[str]]]:
    direct: dict[tuple[str, str], Any] = {}
    loci_by_contig: dict[str, list[str]] = {}
    for cds in cds_features:
        contig = str(_value(cds, "contig", ""))
        locus = str(_value(cds, "locus_tag", "") or "")
        if not contig or not locus:
            continue
        direct[(contig, locus)] = cds
        loci_by_contig.setdefault(contig, []).append(locus)
    for contig in loci_by_contig:
        loci_by_contig[contig] = sorted(
            set(loci_by_contig[contig]), key=lambda value: (-len(value), value)
        )
    return direct, loci_by_contig


def _resolve_locus(
    record_id: str,
    raw_locus: Any,
    direct: dict[tuple[str, str], Any],
    loci_by_contig: dict[str, list[str]],
) -> Any | None:
    locus = str(raw_locus or "")
    if (record_id, locus) in direct:
        return direct[(record_id, locus)]
    for candidate in loci_by_contig.get(record_id, []):
        if locus.startswith(f"nrpspksdomains_{candidate}_") or locus == candidate:
            return direct.get((record_id, candidate))
    return None


def _coordinates_for_json_row(
    row: dict[str, Any],
    direct: dict[tuple[str, str], Any],
    loci_by_contig: dict[str, list[str]],
) -> tuple[str, int | None, int | None, int, str]:
    contig = str(row.get("record_id") or row.get("contig") or "")
    start = row.get("start")
    end = row.get("end")
    strand = int(row.get("strand") or 0)
    if start is not None and end is not None:
        try:
            return contig, int(start) + 1, int(end), strand, "JSON_COORDINATES"
        except (TypeError, ValueError):
            pass
    location = row.get("location")
    if not location and isinstance(row.get("motif"), dict):
        location = row["motif"].get("location")
    loc_start, loc_end, loc_strand = _parse_location(location)
    if loc_start is not None and loc_end is not None:
        return contig, loc_start, loc_end, loc_strand, "JSON_LOCATION"
    cds = _resolve_locus(
        contig,
        row.get("locus_tag") or row.get("domain_id"),
        direct,
        loci_by_contig,
    )
    if cds is not None:
        return (
            contig,
            int(_value(cds, "start", 0)),
            int(_value(cds, "end", 0)),
            int(_value(cds, "strand", 0) or 0),
            "CDS_LOCUS_COORDINATES",
        )
    return contig, None, None, 0, "NO_COORDINATE"


def _assign_row_ids(prefix: str, rows: list[dict[str, Any]], columns: list[str]) -> None:
    rows.sort(
        key=lambda row: (
            str(row.get("contig", "")),
            int(row.get("start") or 0),
            int(row.get("end") or 0),
            str(row.get("locus_tag", "")),
            str(row.get("evidence_type") or row.get("rre_family") or ""),
            str(row.get("domain") or row.get("motif") or row.get("rrefam_identifier") or ""),
        )
    )
    for index, row in enumerate(rows, 1):
        row["row_id"] = f"{prefix}{index:06d}"
        for column in columns:
            row.setdefault(column, "")


def _module_json_row(
    source: dict[str, Any],
    evidence_type: str,
    bgcs: list[Any],
    direct: dict[tuple[str, str], Any],
    loci_by_contig: dict[str, list[str]],
) -> dict[str, Any]:
    contig, start, end, strand, coordinate_source = _coordinates_for_json_row(
        source, direct, loci_by_contig
    )
    bgc_id, mapping_status, mapping_method, _ = _map_interval(
        contig, start, end, bgcs
    )
    summary_parts = []
    for key in ("consensus_substrate", "product_classes", "products", "starter_units", "elongations"):
        value = source.get(key)
        if value not in (None, "", [], {}):
            rendered = "; ".join(str(item) for item in value) if isinstance(value, list) else str(value)
            summary_parts.append(f"{key}={rendered}")
    return {
        "bgc_id": bgc_id,
        "mapping_status": mapping_status,
        "mapping_method": f"{mapping_method}:{coordinate_source}",
        "contig": contig,
        "start": start if start is not None else "",
        "end": end if end is not None else "",
        "strand": strand,
        "evidence_type": evidence_type,
        "feature_type": str(source.get("module") or evidence_type),
        "locus_tag": str(source.get("locus_tag") or source.get("domain_id") or ""),
        "domain": str(source.get("domain_id") or ""),
        "database": "",
        "bitscore": "",
        "evalue": "",
        "substrate_consensus": str(source.get("consensus_substrate") or ""),
        "prediction_summary": " | ".join(summary_parts),
        "source_file": str(source.get("source") or ""),
        "source_schema": str(source.get("module") or evidence_type),
        "source_schema_version": "",
        "detail_json": _json(source),
        "claim_safety": CLAIM_SAFETY,
    }


def _build_rrefinder_rows(
    evidence_rows: Iterable[dict[str, Any]],
    bgcs: list[Any],
    antismash_version: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen = set()
    for source in evidence_rows or []:
        contig = str(source.get("record_id") or "")
        start, end, strand = _parse_location(source.get("location"))
        key = (
            contig,
            str(source.get("locus_tag") or ""),
            start,
            end,
            str(source.get("rre_family") or ""),
            str(source.get("rrefam_identifier") or ""),
            str(source.get("evalue") or ""),
            str(source.get("bitscore") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        bgc_id, mapping_status, mapping_method, candidates = _map_interval(
            contig, start, end, bgcs
        )
        products = ""
        if len(candidates) == 1:
            products = "; ".join(_value(candidates[0], "products", []) or [])
        out.append({
            "record_id": contig,
            "contig": contig,
            "bgc_id": bgc_id,
            "mapping_status": mapping_status,
            "mapping_method": mapping_method,
            "protoclusters": ";".join(str(v) for v in source.get("protoclusters", []) or []),
            "locus_tag": str(source.get("locus_tag") or ""),
            "start": start if start is not None else "",
            "end": end if end is not None else "",
            "strand": strand,
            "rre_family": str(source.get("rre_family") or ""),
            "rre_description": str(source.get("rre_description") or ""),
            "rrefam_identifier": str(source.get("rrefam_identifier") or ""),
            "evalue": source.get("evalue") if source.get("evalue") is not None else "",
            "bitscore": source.get("bitscore") if source.get("bitscore") is not None else "",
            "protein_start": source.get("protein_start") if source.get("protein_start") is not None else "",
            "protein_end": source.get("protein_end") if source.get("protein_end") is not None else "",
            "antismash_product_context": products,
            "source_file": str(source.get("source") or ""),
            "source_schema": "antismash.modules.rrefinder",
            "source_schema_version": source.get("module_schema_version", ""),
            "antismash_version": antismash_version,
            "bitscore_cutoff": source.get("bitscore_cutoff", ""),
            "minimum_protein_length": source.get("minimum_protein_length", ""),
            "claim_safety": CLAIM_SAFETY,
        })
    _assign_row_ids("RRE", out, RREFINDER_COLUMNS)
    return out


def build_structured_tables(zip_path, evidence, bgcs):
    """Build stable, BGC-aware report tables from antiSMASH JSON and GBKs."""
    bgcs = list(bgcs or [])
    evidence = evidence or {}
    parse_errors: list[dict[str, str]] = []
    try:
        cds_features = extract_cds_features(zip_path)
    except Exception as exc:
        cds_features = []
        parse_errors.append({"surface": "CDS", "error": type(exc).__name__})
    direct, loci_by_contig = _locus_index(cds_features)

    modules: list[dict[str, Any]] = []
    for key, evidence_type in (
        ("nrps_pks_consensus", "NRPS_PKS_CONSENSUS"),
        ("product_class_predictions", "PRODUCT_CLASS_PREDICTION"),
        ("active_site_pairings", "ACTIVE_SITE_PAIRING"),
    ):
        for source in evidence.get(key, []) or []:
            if isinstance(source, dict):
                modules.append(_module_json_row(
                    source, evidence_type, bgcs, direct, loci_by_contig
                ))

    motifs: list[dict[str, Any]] = []
    try:
        for domain_feature in extract_domain_features(zip_path):
            source = asdict(domain_feature)
            bgc_id, mapping_status, mapping_method, _ = _map_interval(
                domain_feature.contig,
                domain_feature.start,
                domain_feature.end,
                bgcs,
            )
            if mapping_status != "MAPPED" and "region" in str(domain_feature.source_file).lower():
                bgc_id, mapping_status, mapping_method = _source_member_map(
                    domain_feature.source_file, bgcs
                )
            if domain_feature.feature_type in {"aSModule", "aSDomain"}:
                modules.append({
                    "bgc_id": bgc_id,
                    "mapping_status": mapping_status,
                    "mapping_method": mapping_method,
                    "contig": domain_feature.contig,
                    "start": domain_feature.start,
                    "end": domain_feature.end,
                    "strand": domain_feature.strand,
                    "evidence_type": domain_feature.feature_type,
                    "feature_type": domain_feature.feature_type,
                    "locus_tag": domain_feature.locus_tag or "",
                    "domain": domain_feature.domain or "",
                    "database": domain_feature.database or "",
                    "bitscore": domain_feature.bitscore if domain_feature.bitscore is not None else "",
                    "evalue": domain_feature.evalue if domain_feature.evalue is not None else "",
                    "substrate_consensus": domain_feature.substrate_consensus,
                    "prediction_summary": "",
                    "source_file": domain_feature.source_file,
                    "source_schema": "GenBank_feature",
                    "source_schema_version": "",
                    "detail_json": _json(source.get("qualifiers", {})),
                    "claim_safety": CLAIM_SAFETY,
                })
            elif domain_feature.feature_type == "CDS_motif":
                motifs.append({
                    "bgc_id": bgc_id,
                    "mapping_status": mapping_status,
                    "mapping_method": mapping_method,
                    "contig": domain_feature.contig,
                    "start": domain_feature.start,
                    "end": domain_feature.end,
                    "strand": domain_feature.strand,
                    "evidence_type": "CDS_MOTIF",
                    "feature_type": domain_feature.feature_type,
                    "locus_tag": domain_feature.locus_tag or "",
                    "motif": domain_feature.domain or "",
                    "database": domain_feature.database or "",
                    "bitscore": domain_feature.bitscore if domain_feature.bitscore is not None else "",
                    "evalue": domain_feature.evalue if domain_feature.evalue is not None else "",
                    "source_file": domain_feature.source_file,
                    "source_schema": "GenBank_feature",
                    "source_schema_version": "",
                    "qualifiers_json": _json(source.get("qualifiers", {})),
                    "claim_safety": CLAIM_SAFETY,
                })
    except Exception as exc:
        parse_errors.append({"surface": "GenBank_domains", "error": type(exc).__name__})

    ripp_motifs: list[dict[str, Any]] = []
    for source in evidence.get("ripp_cores", []) or []:
        if not isinstance(source, dict):
            continue
        contig, start, end, strand, coordinate_source = _coordinates_for_json_row(
            source, direct, loci_by_contig
        )
        bgc_id, mapping_status, mapping_method, _ = _map_interval(
            contig, start, end, bgcs
        )
        motif = source.get("motif") if isinstance(source.get("motif"), dict) else {}
        ripp_motifs.append({
            "bgc_id": bgc_id,
            "mapping_status": mapping_status,
            "mapping_method": f"{mapping_method}:{coordinate_source}",
            "contig": contig,
            "start": start if start is not None else "",
            "end": end if end is not None else "",
            "strand": strand,
            "evidence_type": "RIPP_CORE",
            "module": str(source.get("module") or ""),
            "ripp_family": str(source.get("ripp_family") or ""),
            "locus_tag": str(source.get("locus_tag") or motif.get("locus_tag") or ""),
            "motif_index": source.get("motif_index", ""),
            "peptide_class": str(source.get("peptide_class") or ""),
            "peptide_subclass": str(source.get("peptide_subclass") or ""),
            "core_sequence": str(source.get("core_sequence") or source.get("core") or ""),
            "leader": str(source.get("leader") or ""),
            "tail": str(source.get("tail") or ""),
            "score": motif.get("score", ""),
            "tool": str(motif.get("tool") or ""),
            "source_file": str(source.get("source") or ""),
            "source_schema": str(source.get("module") or "RiPP_motif"),
            "source_schema_version": "",
            "detail_json": _json(motif),
            "claim_safety": CLAIM_SAFETY,
        })

    antismash_version = str(extract_antismash_version(zip_path) or "UNRESOLVED")
    rrefinder = _build_rrefinder_rows(
        evidence.get("rrefinder_hits", []) or [],
        bgcs,
        antismash_version,
    )
    _assign_row_ids("MOD", modules, MODULE_COLUMNS)
    _assign_row_ids("RIP", ripp_motifs, RIPP_MOTIF_COLUMNS)
    _assign_row_ids("MOT", motifs, MOTIF_COLUMNS)

    try:
        # Thread the run's already-merged Pfam+TIGRFAM hits so the HMM table does not
        # trigger a second tigrfam record pass (test_record_pass_count regression).
        hmm = build_hmm_table(zip_path, bgcs, precomputed_hits=evidence.get("gbk_pfam_hits"))
    except Exception as exc:
        hmm = []
        parse_errors.append({"surface": "HMM_pfam_tigrfam", "error": type(exc).__name__})

    counts = {
        "modules": len(modules),
        "ripp_motifs": len(ripp_motifs),
        "motifs": len(motifs),
        "rrefinder": len(rrefinder),
        "hmm": len(hmm),
        "rrefinder_mapped": sum(row["mapping_status"] == "MAPPED" for row in rrefinder),
        "rrefinder_unmapped": sum(row["mapping_status"] != "MAPPED" for row in rrefinder),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "report_only_contract": REPORT_ONLY_CONTRACT,
        "status": (
            "PASS"
            if any(counts[key] for key in ("modules", "ripp_motifs", "motifs", "rrefinder", "hmm"))
            else "NULL_NO_STRUCTURED_ANTISMASH_EVIDENCE"
        ),
        "rrefinder_status": "PASS" if rrefinder else "NULL_NO_RREFINDER_HITS",
        "hmm_status": "PASS" if hmm else "NULL_NO_PFAM_TIGRFAM_HITS",
        "antismash_version": antismash_version,
        "table_columns": TABLE_COLUMNS,
        "counts": counts,
        "parse_errors": parse_errors,
        "modules": modules,
        "ripp_motifs": ripp_motifs,
        "motifs": motifs,
        "rrefinder": rrefinder,
        "hmm": hmm,
        "claim_safety": CLAIM_SAFETY,
    }
