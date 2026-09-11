"""Portable preservation-first V7 + Mode B BGC report composition.

The builder consumes a completed P357-015 report packet.  It deliberately
does not read the identity or BLASTP SQLite stores again.  Additional evidence
is admitted as content-addressed files beneath caller-configured source roots.
The result is a Markdown dossier ordered from exact/current evidence to
retained historical context.
"""

from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import os
import re
import shutil
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping


JOB_SCHEMA = "sapote-combined-v7-modeb-job-v1"
MANIFEST_SCHEMA = "sapote-combined-v7-modeb-report-v1"
POLICY_SCHEMA = "sapote-combined-report-owner-policy-v1"
P357015_SCHEMA = "sapote_refreshable_bgc_report_v1"
DEFAULT_CLAIM_CEILING = (
    "Sequence architecture, domains, similarity results, structured role evidence, and "
    "cross-locus comparisons can support class-, component-, or pathway-family hypotheses. "
    "They do not establish exact product identity, complete pathway membership, physical "
    "linkage, expression, production, activity, novelty, ecology, stereochemistry, or yield."
)

REQUIRED_SINGLE_ROLES = {
    "P357015_REPORT_MANIFEST",
    "P357015_REPORT_MARKDOWN",
    "P357015_EXACT_IDENTITY_LEDGER",
    "LOCUS_MAP_ASSET",
    "V7_MARKDOWN",
    "MODE_B_MARKDOWN",
    "GENE_ROLE_DISPOSITIONS",
    "OVERMERGE_SPLIT_EVIDENCE",
    "CROSS_CONTIG_RESCUE_EVIDENCE",
    "OWNER_POLICY",
}
LOCUS_SCOPED_ROLES = REQUIRED_SINGLE_ROLES - {"OWNER_POLICY"}
ALLOWED_ADMISSION_STATES = {
    "ADMITTED_EXACT_CURRENT",
    "STRUCTURED_CURRENT",
    "PRESERVED_HISTORICAL",
    "OWNER_POLICY_CURRENT",
}
ROLE_DISPOSITIONS = {"SUPPORTED_CURRENT", "SUPERSEDED", "HOLD_UNRESOLVED"}
SYSTEM_COUNT_STATES = {"OBSERVED_STRUCTURED", "UNRESOLVED", "MISSING_INPUT"}
SEMANTIC_STATES = {
    "CONSISTENT_SINGLE_SYSTEM",
    "MIXED_MULTI_SYSTEM_BUT_CLASS_CONSISTENT",
    "CONTRADICTION_HOLD",
    "INSUFFICIENT_EVIDENCE_HOLD",
}
PRIVATE_PATH = re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\\\Users\\\\)[^\s`\"']+")
LOCATOR_HEADING = re.compile(
    r"^#{1,4}\s+.*?(NODE_[^\s`/]+)\s*/\s*(region\d+)\s*$", re.I | re.M
)


class ExcludedSubject(RuntimeError):
    """Raised only by direct callers that request exception-based exclusion."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path.name}")
    return payload


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames:
            raise ValueError(f"TSV header required: {path.name}")
        return list(reader)


def _write_tsv(path: Path, rows: Iterable[Mapping[str, object]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(rows)


def _safe_relative(value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or not value or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"Non-portable relative path: {value!r}")
    return path


def _resolve_sources(job: dict, roots: Mapping[str, Path]) -> tuple[dict[str, dict], dict[str, str]]:
    descriptors = job.get("sources")
    if not isinstance(descriptors, list) or not descriptors:
        raise ValueError("Job requires a non-empty sources array")
    resolved: dict[str, dict] = {}
    snapshot: dict[str, str] = {}
    for descriptor in descriptors:
        if not isinstance(descriptor, dict):
            raise ValueError("Every source descriptor must be an object")
        source_id = descriptor.get("source_id", "")
        role = descriptor.get("role", "")
        if not source_id or source_id in resolved:
            raise ValueError(f"Missing or duplicate source_id: {source_id!r}")
        if descriptor.get("admission_state") not in ALLOWED_ADMISSION_STATES:
            raise ValueError(f"Source {source_id} has an unadmitted state")
        logical_uri = descriptor.get("logical_uri", "")
        if not logical_uri.startswith("evidence://") or PRIVATE_PATH.search(logical_uri):
            raise ValueError(f"Source {source_id} requires a portable evidence:// logical URI")
        root_id = descriptor.get("root_id", "")
        if root_id not in roots:
            raise ValueError(f"Unknown source root {root_id!r} for {source_id}")
        root = Path(roots[root_id]).resolve(strict=True)
        relative = _safe_relative(str(descriptor.get("relative_path", "")))
        path = (root / relative).resolve(strict=True)
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Source escapes configured root: {source_id}") from exc
        if not path.is_file():
            raise ValueError(f"Source is not a file: {source_id}")
        expected_bytes = descriptor.get("bytes")
        if not isinstance(expected_bytes, int) or path.stat().st_size != expected_bytes:
            raise ValueError(f"Source byte-count mismatch: {source_id}")
        expected_sha = str(descriptor.get("sha256", ""))
        observed_sha = sha256_file(path)
        if observed_sha != expected_sha:
            raise ValueError(f"Source SHA-256 mismatch: {source_id}")
        resolved[source_id] = {**descriptor, "path": path, "role": role}
        snapshot[source_id] = observed_sha
    return resolved, snapshot


def _group_by_role(sources: Mapping[str, dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for source in sources.values():
        grouped[source["role"]].append(source)
    missing = sorted(REQUIRED_SINGLE_ROLES - set(grouped))
    if missing:
        raise ValueError(f"Missing required source roles: {', '.join(missing)}")
    duplicates = sorted(role for role in REQUIRED_SINGLE_ROLES if len(grouped[role]) != 1)
    if duplicates:
        raise ValueError(f"Required source roles must occur exactly once: {', '.join(duplicates)}")
    return grouped


def _identity_tuple(identity: Mapping[str, object]) -> tuple[str, str, str, str, str]:
    fields = ("subject_id", "assembly_sha256", "node_id", "region_id", "exact_region_key")
    values = tuple(str(identity.get(field, "")) for field in fields)
    if any(not value for value in values):
        raise ValueError(f"Exact identity requires {', '.join(fields)}")
    if not values[2].startswith("NODE_"):
        raise ValueError("Exact node_id must use the full NODE_* identifier")
    if not re.fullmatch(r"region\d+", values[3], flags=re.I):
        raise ValueError("Exact region_id must be regionNNN")
    if not re.fullmatch(r"[0-9a-f]{64}", values[1]):
        raise ValueError("assembly_sha256 must be a lowercase SHA-256")
    return values


def _validate_source_identities(grouped: Mapping[str, list[dict]], identity: dict) -> None:
    expected = _identity_tuple(identity)
    for role in LOCUS_SCOPED_ROLES | {"PER_GENE_CHANNEL_TABLE"}:
        for source in grouped.get(role, []):
            if _identity_tuple(source.get("identity", {})) != expected:
                raise ValueError(f"Exact locator mismatch in source role {role}")


def _extract_section(source: dict) -> tuple[str, dict]:
    text = source["path"].read_text(encoding="utf-8")
    start_anchor = source.get("start_anchor")
    end_anchor = source.get("end_anchor")
    if not start_anchor or not end_anchor:
        raise ValueError(f"Preserved source {source['source_id']} requires start/end anchors")
    if text.count(start_anchor) != 1 or text.count(end_anchor) != 1:
        raise ValueError(f"Preservation anchors must be unique in {source['source_id']}")
    start = text.index(start_anchor)
    end = text.index(end_anchor, start + len(start_anchor))
    if end <= start:
        raise ValueError(f"Preservation anchors are reversed in {source['source_id']}")
    selected = text[start:end].rstrip() + "\n"
    selected_sha = sha256_text(selected)
    if selected_sha != source.get("selected_sha256"):
        raise ValueError(f"Preserved substring SHA-256 mismatch: {source['source_id']}")
    return selected, {
        "source_id": source["source_id"],
        "role": source["role"],
        "logical_uri": source["logical_uri"],
        "source_sha256": source["sha256"],
        "selected_sha256": selected_sha,
        "start_anchor": start_anchor,
        "end_anchor": end_anchor,
    }


def _verify_predecessor(grouped: Mapping[str, list[dict]], identity: dict) -> tuple[str, dict]:
    manifest_source = grouped["P357015_REPORT_MANIFEST"][0]
    report_source = grouped["P357015_REPORT_MARKDOWN"][0]
    identity_source = grouped["P357015_EXACT_IDENTITY_LEDGER"][0]
    manifest = _load_json(manifest_source["path"])
    expected = _identity_tuple(identity)
    if manifest.get("schema_version") != P357015_SCHEMA:
        raise ValueError("Combined report requires a P357-015 report manifest")
    if manifest.get("strain") != expected[0] or expected[4] not in manifest.get("region_keys", []):
        raise ValueError("P357-015 manifest does not cover the requested exact locus")
    output_hashes = {row.get("path"): row.get("sha256") for row in manifest.get("outputs", [])}
    for source in (report_source, identity_source):
        if output_hashes.get(source["path"].name) != source["sha256"]:
            raise ValueError(f"P357-015 output is not bound by its manifest: {source['source_id']}")
    matches = []
    for row in _read_tsv(identity_source["path"]):
        source_region_ids = set(filter(None, row.get("source_region_ids", "").split(";")))
        if (
            row.get("strain") == expected[0]
            and row.get("assembly_sha256") == expected[1]
            and row.get("node_id") == expected[2]
            and expected[3] in source_region_ids
            and row.get("region_key") == expected[4]
        ):
            matches.append(row)
    if len(matches) != 1 or matches[0].get("identity_state") != "EXACT_SEQUENCE_COORDINATE_BOUND":
        raise ValueError("P357-015 exact identity ledger lacks one authoritative locus row")
    section, receipt = _extract_section(report_source)
    return section, {"manifest_sha256": manifest_source["sha256"], **receipt}


def _validate_mode_b(text: str, identity: dict) -> None:
    if "MODE B TEMPLATE" in text.upper():
        raise ValueError("FOREIGN_MODE_B_TEMPLATE_MARKER")
    headings = LOCATOR_HEADING.findall(text)
    if len(headings) != 1:
        raise ValueError("MODE_B_REQUIRES_EXACTLY_ONE_LOCATOR_HEADING")
    node, region = headings[0]
    if node != identity["node_id"] or region.lower() != identity["region_id"].lower():
        raise ValueError("MODE_B_TEMPLATE_LOCATOR_MISMATCH")
    full_locators = set(re.findall(r"(NODE_[^\s`/]+)\s*/\s*(region\d+)", text, flags=re.I))
    if full_locators != {(identity["node_id"], identity["region_id"])}:
        raise ValueError("FOREIGN_COMPACT_BGC_CARD_PRESENT")


def _require_columns(rows: list[dict[str, str]], required: set[str], role: str) -> None:
    if not rows:
        raise ValueError(f"{role} requires at least one typed row")
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError(f"{role} missing columns: {', '.join(missing)}")


def _row_matches_identity(row: Mapping[str, str], identity: dict) -> bool:
    return all(row.get(field) == identity[field] for field in (
        "assembly_sha256", "node_id", "region_id", "exact_region_key"
    ))


def _load_channel_rows(sources: list[dict], identity: dict) -> list[dict[str, str]]:
    required = {
        "assembly_sha256", "node_id", "region_id", "exact_region_key", "gene_id", "channel",
        "top_hit_label", "accession", "pct_identity", "query_coverage", "evidence_state",
        "sequence_binding_state", "source_logical_uri", "source_sha256",
    }
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for source in sources:
        channel = source.get("channel", "")
        if not channel:
            raise ValueError("Every per-gene table descriptor must declare one channel")
        rows = _read_tsv(source["path"])
        _require_columns(rows, required, "PER_GENE_CHANNEL_TABLE")
        for row in rows:
            if not _row_matches_identity(row, identity):
                raise ValueError("Foreign locator in per-gene channel table")
            if row["channel"] != channel:
                raise ValueError(f"Mixed channels in independently declared {channel} table")
            if not row["source_logical_uri"].startswith("evidence://") or not re.fullmatch(
                r"[0-9a-f]{64}", row["source_sha256"]
            ):
                raise ValueError("Per-gene row lacks content-addressed evidence provenance")
            key = (row["gene_id"], row["channel"])
            if key in seen:
                raise ValueError(f"Duplicate gene/channel row: {key[0]}/{key[1]}")
            seen.add(key)
            for field in ("pct_identity", "query_coverage"):
                if row[field]:
                    value = float(row[field])
                    if value < 0 or value > 100:
                        raise ValueError(f"{field} outside 0-100 for {key[0]}/{key[1]}")
            out.append(row)
    return sorted(out, key=lambda row: (row["channel"], row["gene_id"]))


def _load_role_rows(source: dict, identity: dict) -> list[dict[str, str]]:
    required = {
        "assembly_sha256", "node_id", "region_id", "exact_region_key", "gene_id",
        "current_role", "inherited_role", "disposition", "support_state", "claim_ceiling",
    }
    rows = _read_tsv(source["path"])
    _require_columns(rows, required, "GENE_ROLE_DISPOSITIONS")
    seen = set()
    for row in rows:
        if not _row_matches_identity(row, identity):
            raise ValueError("Foreign locator in gene-role dispositions")
        if row["gene_id"] in seen:
            raise ValueError(f"Duplicate gene-role row: {row['gene_id']}")
        seen.add(row["gene_id"])
        if row["disposition"] not in ROLE_DISPOSITIONS:
            raise ValueError(f"Unknown gene-role disposition: {row['disposition']}")
        if row["disposition"] == "SUPERSEDED" and row["current_role"] == row["inherited_role"]:
            raise ValueError("SUPERSEDED role requires a changed current role")
        if row["disposition"] == "HOLD_UNRESOLVED" and row["current_role"]:
            raise ValueError("HOLD_UNRESOLVED must not promote a current named role")
    return rows


def _load_overmerge_rows(source: dict, identity: dict) -> tuple[list[dict[str, str]], int | None]:
    required = {
        "assembly_sha256", "node_id", "region_id", "exact_region_key", "system_count_state",
        "system_count", "block_id", "block_class", "boundary_start_gene", "boundary_end_gene",
        "boundary_start_nt", "boundary_end_nt", "evidence_state", "reason_code",
        "source_logical_uri", "source_sha256",
    }
    rows = _read_tsv(source["path"])
    _require_columns(rows, required, "OVERMERGE_SPLIT_EVIDENCE")
    states = set()
    counts = set()
    blocks = set()
    for row in rows:
        if not _row_matches_identity(row, identity):
            raise ValueError("FAIL_FOREIGN_OVERMERGE_LOCATOR")
        state = row["system_count_state"]
        if state not in SYSTEM_COUNT_STATES:
            raise ValueError(f"Unknown system_count_state: {state}")
        states.add(state)
        if not row["source_logical_uri"].startswith("evidence://") or not re.fullmatch(
            r"[0-9a-f]{64}", row["source_sha256"]
        ):
            raise ValueError("Overmerge row lacks content-addressed evidence provenance")
        if state == "OBSERVED_STRUCTURED":
            if not row["system_count"] or not row["block_id"]:
                raise ValueError("Observed overmerge rows require count and block ID")
            if not ((row["boundary_start_gene"] and row["boundary_end_gene"]) or
                    (row["boundary_start_nt"] and row["boundary_end_nt"])):
                raise ValueError("Observed blocks require gene or coordinate boundaries")
            counts.add(int(row["system_count"]))
            blocks.add(row["block_id"])
        elif row["system_count"]:
            raise ValueError("Typed missingness cannot carry a system count")
    if len(states) != 1 or len(counts) > 1:
        raise ValueError("Overmerge evidence has inconsistent structured states")
    count = next(iter(counts), None)
    if count is not None and count != len(blocks):
        raise ValueError("Structured system count does not equal unique block count")
    return rows, count


def _load_rescue_rows(source: dict, identity: dict) -> list[dict[str, str]]:
    sides = ["left", "right"]
    required = {
        *(f"{side}_{field}" for side in sides for field in (
            "assembly_sha256", "node_id", "region_id", "exact_region_key"
        )),
        "candidate_family", "rggmci_state", "comparator_evidence_state",
        "expert_adjudication_state", "physical_join_state", "claim_ceiling",
        "source_logical_uri", "source_sha256",
    }
    rows = _read_tsv(source["path"])
    _require_columns(rows, required, "CROSS_CONTIG_RESCUE_EVIDENCE")
    for row in rows:
        exact_side = any(all(row[f"{side}_{field}"] == identity[field] for field in (
            "assembly_sha256", "node_id", "region_id", "exact_region_key"
        )) for side in sides)
        if not exact_side:
            raise ValueError("Rescue row does not bind the requested exact locus")
        if not row["source_logical_uri"].startswith("evidence://") or not re.fullmatch(
            r"[0-9a-f]{64}", row["source_sha256"]
        ):
            raise ValueError("Rescue row lacks content-addressed evidence provenance")
        if not row["physical_join_state"] or not row["expert_adjudication_state"]:
            raise ValueError("Rescue evidence must separate adjudication and physical join states")
    return rows


def _semantic_state(role_rows: list[dict[str, str]], overmerge_rows: list[dict[str, str]], count: int | None) -> str:
    if any(row["support_state"] == "CURRENT_CLASS_CONTRADICTION" for row in role_rows):
        return "CONTRADICTION_HOLD"
    if any(row["system_count_state"] != "OBSERVED_STRUCTURED" for row in overmerge_rows):
        return "INSUFFICIENT_EVIDENCE_HOLD"
    if count == 1:
        return "CONSISTENT_SINGLE_SYSTEM"
    if count and count > 1:
        return "MIXED_MULTI_SYSTEM_BUT_CLASS_CONSISTENT"
    return "INSUFFICIENT_EVIDENCE_HOLD"


def _md(value: object) -> str:
    return str(value or "—").replace("|", "/").replace("\n", " ")


def _render_report(
    identity: dict,
    claim_ceiling: str,
    map_name: str,
    current_section: str,
    overmerge_rows: list[dict[str, str]],
    rescue_rows: list[dict[str, str]],
    channel_rows: list[dict[str, str]],
    role_rows: list[dict[str, str]],
    mode_b_section: str,
    v7_section: str,
    semantic_state: str,
) -> str:
    locator = f"{identity['node_id']} / {identity['region_id']}"
    lines = [
        f"# {identity['subject_id']} — preliminary combined V7 + Mode B BGC report",
        "",
        f"**Exact locator:** `{locator}`  ",
        f"**Assembly SHA-256:** `{identity['assembly_sha256']}`  ",
        f"**Exact region key:** `{identity['exact_region_key']}`  ",
        f"**Semantic state:** `{semantic_state}`  ",
        "**Status:** `DRAFT_CURRENT_SNAPSHOT_WITH_RETAINED_HISTORICAL_CONTEXT`",
        "",
        f"> {claim_ceiling}",
        "",
        "## Locus map",
        "",
        f"![Exact-locus gene and domain map](assets/{map_name})",
        "",
        "## Current exact-locus synthesis",
        "",
        current_section.rstrip(),
        "",
        "## Structured within-locus overmerge and split state",
        "",
        "| State | Count | Block | Class signal | Boundary genes | Boundary nt | Evidence | Reason |",
        "|---|---:|---|---|---|---|---|---|",
    ]
    for row in overmerge_rows:
        lines.append(
            f"| `{_md(row['system_count_state'])}` | {_md(row['system_count'])} | "
            f"`{_md(row['block_id'])}` | {_md(row['block_class'])} | "
            f"{_md(row['boundary_start_gene'])}–{_md(row['boundary_end_gene'])} | "
            f"{_md(row['boundary_start_nt'])}–{_md(row['boundary_end_nt'])} | "
            f"`{_md(row['evidence_state'])}` | `{_md(row['reason_code'])}` |"
        )
    lines.extend([
        "",
        "## Cross-contig rescue candidates",
        "",
        "These candidates are independent of within-locus system counts. A held physical join does not erase a claim-capped comparison candidate.",
        "",
        "| Paired exact locator | Candidate family | RGGMCI | Comparator | Expert adjudication | Physical join |",
        "|---|---|---|---|---|---|",
    ])
    for row in rescue_rows:
        pair = (
            f"{row['left_node_id']} / {row['left_region_id']} ↔ "
            f"{row['right_node_id']} / {row['right_region_id']}"
        )
        lines.append(
            f"| `{_md(pair)}` | {_md(row['candidate_family'])} | `{_md(row['rggmci_state'])}` | "
            f"`{_md(row['comparator_evidence_state'])}` | `{_md(row['expert_adjudication_state'])}` | "
            f"`{_md(row['physical_join_state'])}` |"
        )
    lines.extend([
        "",
        "## Current per-gene similarity evidence by channel",
        "",
        "nr and ClusteredNR remain separate views. ClusteredNR similarity is not nr identity; no cross-channel best hit is synthesized.",
        "",
        "| Channel | Gene | Top label | Accession | Identity % | Query coverage % | Evidence state | Query binding |",
        "|---|---|---|---|---:|---:|---|---|",
    ])
    for row in channel_rows:
        lines.append(
            f"| `{_md(row['channel'])}` | `{_md(row['gene_id'])}` | {_md(row['top_hit_label'])} | "
            f"`{_md(row['accession'])}` | {_md(row['pct_identity'])} | {_md(row['query_coverage'])} | "
            f"`{_md(row['evidence_state'])}` | `{_md(row['sequence_binding_state'])}` |"
        )
    if not channel_rows:
        lines.append("| — | — | — | — | — | — | `CHANNEL_NOT_CONSUMED` | `NOT_A_BIOLOGICAL_NEGATIVE` |")
    lines.extend([
        "",
        "## Current gene-role dispositions",
        "",
        "| Gene | Current structured role | Inherited role | Disposition | Support state |",
        "|---|---|---|---|---|",
    ])
    for row in role_rows:
        lines.append(
            f"| `{_md(row['gene_id'])}` | {_md(row['current_role'])} | {_md(row['inherited_role'])} | "
            f"`{_md(row['disposition'])}` | `{_md(row['support_state'])}` |"
        )
    lines.extend([
        "",
        "## Retained Mode B scientific sections",
        "",
        "> Retained text is historical context. The disposition table above controls any named gene role that changed or remains unresolved.",
        "",
        mode_b_section.rstrip(),
        "",
        "## Preserved V7 literature and context",
        "",
        "> This section is preserved from its content-addressed source. Literature routing does not prove that a pathway occurs at this locus.",
        "",
        v7_section.rstrip(),
        "",
        "## Provenance and holds",
        "",
        "Every source is resolved from a configured root, bound by logical URI, byte count, and SHA-256. Missing or held evidence is not biological absence.",
        "",
        "## Claim boundary",
        "",
        claim_ceiling,
        "",
    ])
    return "\n".join(lines)


def _private_path_scan(texts: Mapping[str, str]) -> None:
    hits = {name: PRIVATE_PATH.findall(text) for name, text in texts.items() if PRIVATE_PATH.search(text)}
    if hits:
        raise ValueError("PRIVATE_PATH_IN_COMBINED_REPORT_INPUT_OR_OUTPUT:" + ",".join(sorted(hits)))


def build(job: dict, source_roots: Mapping[str, Path], output_root: Path) -> dict:
    if job.get("schema_version") != JOB_SCHEMA:
        raise ValueError(f"Unsupported combined-report job schema: {job.get('schema_version')!r}")
    identity = job.get("identity", {})
    _identity_tuple(identity)
    if output_root.exists():
        raise FileExistsError(f"Output root already exists: {output_root}")
    sources, preflight = _resolve_sources(job, source_roots)
    grouped = _group_by_role(sources)
    _validate_source_identities(grouped, identity)

    policy = _load_json(grouped["OWNER_POLICY"][0]["path"])
    if policy.get("schema_version") != POLICY_SCHEMA:
        raise ValueError("Unsupported owner policy schema")
    excluded = set(policy.get("excluded_subjects", []))
    if identity["subject_id"] in excluded:
        return {
            "schema_version": MANIFEST_SCHEMA,
            "status": "EXCLUDED_NO_OUTPUT",
            "subject_id": identity["subject_id"],
            "reason_code": "OWNER_POLICY_EXCLUSION",
        }

    current_section, current_receipt = _verify_predecessor(grouped, identity)
    v7_section, v7_receipt = _extract_section(grouped["V7_MARKDOWN"][0])
    mode_b_section, mode_b_receipt = _extract_section(grouped["MODE_B_MARKDOWN"][0])
    _validate_mode_b(mode_b_section, identity)
    channel_rows = _load_channel_rows(grouped.get("PER_GENE_CHANNEL_TABLE", []), identity)
    role_rows = _load_role_rows(grouped["GENE_ROLE_DISPOSITIONS"][0], identity)
    overmerge_rows, system_count = _load_overmerge_rows(grouped["OVERMERGE_SPLIT_EVIDENCE"][0], identity)
    rescue_rows = _load_rescue_rows(grouped["CROSS_CONTIG_RESCUE_EVIDENCE"][0], identity)
    semantic_state = _semantic_state(role_rows, overmerge_rows, system_count)
    if semantic_state not in SEMANTIC_STATES:
        raise AssertionError(semantic_state)
    claim_ceiling = str(job.get("claim_ceiling") or DEFAULT_CLAIM_CEILING)

    map_source = grouped["LOCUS_MAP_ASSET"][0]
    map_name = f"locus_map{map_source['path'].suffix.lower()}"
    report_name = str(job.get("report_name") or "combined_v7_modeb_report.md")
    if Path(report_name).name != report_name or not report_name.endswith(".md"):
        raise ValueError("report_name must be a portable Markdown basename")
    report_text = _render_report(
        identity, claim_ceiling, map_name, current_section, overmerge_rows, rescue_rows,
        channel_rows, role_rows, mode_b_section, v7_section, semantic_state,
    )
    _private_path_scan({
        "current_section": current_section,
        "mode_b_section": mode_b_section,
        "v7_section": v7_section,
        "report": report_text,
    })

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = output_root.with_name(f".{output_root.name}.staging-{uuid.uuid4().hex}")
    if staging.exists():
        raise FileExistsError(staging)
    staging.mkdir()
    try:
        assets = staging / "assets"
        assets.mkdir()
        map_output = assets / map_name
        shutil.copyfile(map_source["path"], map_output)
        if sha256_file(map_output) != map_source["sha256"]:
            raise ValueError("Copied locus map hash mismatch")
        report_path = staging / report_name
        report_path.write_text(report_text, encoding="utf-8")

        channel_fields = [
            "assembly_sha256", "node_id", "region_id", "exact_region_key", "gene_id", "channel",
            "top_hit_label", "accession", "pct_identity", "query_coverage", "evidence_state",
            "sequence_binding_state", "source_logical_uri", "source_sha256",
        ]
        role_fields = [
            "assembly_sha256", "node_id", "region_id", "exact_region_key", "gene_id",
            "current_role", "inherited_role", "disposition", "support_state", "claim_ceiling",
        ]
        overmerge_fields = list(overmerge_rows[0])
        rescue_fields = list(rescue_rows[0])
        channel_path = staging / "per_gene_channel_evidence.tsv"
        role_path = staging / "gene_role_dispositions.tsv"
        overmerge_path = staging / "overmerge_split_evidence.tsv"
        rescue_path = staging / "cross_contig_rescue_candidates.tsv"
        _write_tsv(channel_path, channel_rows, channel_fields)
        _write_tsv(role_path, role_rows, role_fields)
        _write_tsv(overmerge_path, overmerge_rows, overmerge_fields)
        _write_tsv(rescue_path, rescue_rows, rescue_fields)

        preservation = {
            "schema_version": "sapote-combined-report-preservation-receipt-v1",
            "status": "PASS_BYTE_AND_SUBSTRING_HASH_BOUND",
            "p357015_current_section": current_receipt,
            "mode_b_section": mode_b_receipt,
            "v7_section": v7_receipt,
            "locus_map": {
                "logical_uri": map_source["logical_uri"],
                "source_sha256": map_source["sha256"],
                "copied_sha256": sha256_file(map_output),
            },
        }
        semantic = {
            "schema_version": "sapote-combined-report-semantic-receipt-v1",
            "status": semantic_state,
            "system_count": system_count,
            "role_dispositions": {state: sum(row["disposition"] == state for row in role_rows) for state in sorted(ROLE_DISPOSITIONS)},
            "claim_ceiling": claim_ceiling,
        }
        exclusion = {
            "schema_version": "sapote-combined-report-exclusion-receipt-v1",
            "status": "PASS_SUBJECT_NOT_EXCLUDED",
            "policy_logical_uri": grouped["OWNER_POLICY"][0]["logical_uri"],
            "policy_sha256": grouped["OWNER_POLICY"][0]["sha256"],
        }
        receipt_paths = []
        for name, payload in (
            ("preservation_receipt.json", preservation),
            ("semantic_consistency_receipt.json", semantic),
            ("owner_exclusion_receipt.json", exclusion),
        ):
            path = staging / name
            path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            receipt_paths.append(path)

        postflight = {source_id: sha256_file(source["path"]) for source_id, source in sources.items()}
        if postflight != preflight:
            raise ValueError("INPUT_SOURCE_DRIFT_BEFORE_COMBINED_REPORT_PUBLICATION")

        primary_outputs = [
            report_path, map_output, channel_path, role_path, overmerge_path, rescue_path, *receipt_paths,
        ]
        single_limit = int(policy.get("single_file_event_bytes", 100_000_000))
        cumulative_limit = int(policy.get("cumulative_event_bytes", 500_000_000))
        size_rows = [{
            "relative_path": path.relative_to(staging).as_posix(),
            "bytes": path.stat().st_size,
            "single_file_event": "YES" if path.stat().st_size >= single_limit else "NO",
        } for path in primary_outputs]
        size_path = staging / "generated_file_size_ledger.tsv"
        _write_tsv(size_path, size_rows, ["relative_path", "bytes", "single_file_event"])
        cumulative = sum(int(row["bytes"]) for row in size_rows)

        manifest_targets = [*primary_outputs, size_path]
        artifact_manifest_path = staging / "ARTIFACT_MANIFEST.tsv"
        artifact_rows = [{
            "relative_path": path.relative_to(staging).as_posix(),
            "role": "GENERATED_COMBINED_REPORT_ARTIFACT",
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
            "state": "PROPOSAL_NOT_ACCEPTED_NOT_INTEGRATED",
        } for path in manifest_targets]
        _write_tsv(
            artifact_manifest_path, artifact_rows,
            ["relative_path", "role", "sha256", "bytes", "state"],
        )
        combined_manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "status": "DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED",
            "identity": identity,
            "semantic_state": semantic_state,
            "source_snapshot_gate": "PASS_PREFLIGHT_POSTFLIGHT_HASH_MATCH",
            "source_bindings": [{
                "source_id": source["source_id"],
                "role": source["role"],
                "logical_uri": source["logical_uri"],
                "sha256": source["sha256"],
                "bytes": source["bytes"],
                "admission_state": source["admission_state"],
                **({"channel": source["channel"]} if source.get("channel") else {}),
            } for source in sorted(sources.values(), key=lambda item: item["source_id"])],
            "artifact_manifest": {
                "path": artifact_manifest_path.name,
                "sha256": sha256_file(artifact_manifest_path),
                "rows": len(artifact_rows),
            },
            "generated_size": {
                "primary_files": len(size_rows),
                "primary_bytes": cumulative,
                "single_file_event": any(row["single_file_event"] == "YES" for row in size_rows),
                "cumulative_event": cumulative >= cumulative_limit,
                "bookkeeping_exclusion": ["ARTIFACT_MANIFEST.tsv", "combined_report_manifest.json"],
            },
            "claim_ceiling": claim_ceiling,
        }
        combined_manifest_path = staging / "combined_report_manifest.json"
        combined_manifest_path.write_text(
            json.dumps(combined_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.replace(staging, output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return combined_manifest


def build_from_path(job_path: Path, source_roots: Mapping[str, Path], output_root: Path) -> dict:
    return build(_load_json(job_path), source_roots, output_root)
