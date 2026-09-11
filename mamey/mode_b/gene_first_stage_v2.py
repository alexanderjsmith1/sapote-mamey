"""Content-addressed staging for the Mode B gene-first v2 candidate.

This module validates compact outputs produced elsewhere.  It deliberately does
not run BLAST, HMM searches, cassette detectors, or workspace discovery.
"""

from __future__ import annotations

import contextlib
import csv
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence


# GF3-1 (v2r3, V4 SS4): the roster digest is now coordinate-sensitive, which changes
# content identity — so the stage schema is bumped. v2 and v2.1 receipts are never
# silently mixed: loading a stage sealed under another schema refuses with a typed
# schema hold (not a tamper accusation) before any other receipt comparison.
SCHEMA_VERSION = "modeb_gene_first_stage_v2.1"
IDENTITY_SCHEMA = "modeb_gene_first_stage_identity_v2"
CONTEXT_SCHEMA = "modeb_gene_first_locus_context_v2"

CANONICAL_CHANNELS = (
    "nr",
    "clustered_nr",
    "local_swissprot",
    "mibig",
    "domain",
    "cassette",
    "neighborhood",
)
ALIGNMENT_CHANNELS = ("nr", "clustered_nr", "local_swissprot")
CHANNEL_ALIASES = {
    "clusterednr": "clustered_nr",
    "swissprot": "local_swissprot",
}

MAPPED_STATES = {
    "BOUND",
    "NO_BOUND_HIT",
    "NOT_RUN",
    "RUNNING_NOT_YET_INGESTED",
    "INGEST_GAP",
    "PROVENANCE_HOLD",
    "NOT_APPLICABLE",
    "REGISTRY_ONLY_NOT_EXECUTED",
}
PRODUCER_STATES = {
    "COMPLETE",
    "NO_HIT_COMPLETE",
    "NOT_RUN",
    "RUNNING",
    "INGEST_GAP",
    "PROVENANCE_HOLD",
    "NOT_APPLICABLE",
    "REGISTRY_ONLY",
}
COMPLETENESS_STATES = {"EXACT_LOCUS_COMPLETE", "PARTIAL", "NOT_APPLICABLE"}
PARTIAL_STATES = {
    "COMPLETE",
    "PARTIAL_5P",
    "PARTIAL_3P",
    "PARTIAL_BOTH",
    "INTERNAL_STOP",
    "UNKNOWN",
}
BOUNDARY_PROXIMITY_STATES = {
    "INTERIOR",
    "EDGE_PROXIMAL",
    "FULL_CONTIG",
    "POSITION_UNKNOWN",
    "NOT_APPLICABLE",
}
BGC_BOUNDARY_STATES = {"INTERIOR", "EDGE", "FULL_CONTIG", "UNKNOWN"}
ASSEMBLY_FRAGMENTATION_TIERS = {
    "CLOSED",
    "CONTIGUOUS",
    "DRAFT",
    "FRAGMENTED",
    "HIGHLY_FRAGMENTED",
    "UNKNOWN",
}
DETECTOR_WINDOW_STATES = {
    "WHOLE_REGION",
    "DETECTOR_WINDOW",
    "BOUNDARY_CONTEXT_EXTENSION",
    "UNRESOLVED",
}
FRAGMENT_CEILING_STATES = {"CLEAR", "TRIPPED", "UNKNOWN"}

IDENTITY_FIELDS = ("strain", "full_node", "region", "bgc_alias", "exact_identity")
ROSTER_FIELDS = (
    *IDENTITY_FIELDS,
    "membership",
    "locus_tag",
    "gene_order",
    "cds_start",
    "cds_end",
    "strand",
    "protein_length_aa",
    "protein_sha256",
    "antismash_role",
    "gene_kind",
    "partial_state",
    "boundary_proximity",
    "source_locator",
    "source_sha256",
)
PRODUCER_FIELDS = (
    "producer_id",
    "channel",
    "producer_state",
    "completeness",
    "tool_name",
    "tool_version",
    "parameter_fingerprint",
    "query_roster_sha256",
    "database_id",
    "database_version",
    "database_sha256",
    "output_locator",
    "output_sha256",
    "output_bytes",
    "receipt_sha256",
    "threads_used",
    "resource_policy_id",
    "started_utc",
    "finished_utc",
    "duration_seconds",
)
EVIDENCE_FIELDS = (
    *IDENTITY_FIELDS,
    "channel",
    "observation_scope",
    "locus_tag",
    "mapped_state",
    "source_state",
    "query_sha256",
    "hit_rank",
    "subject_accession",
    "subject_name",
    "subject_organism",
    "pct_identity",
    "pct_positives",
    "query_coverage",
    "aligned_length",
    "evalue",
    "bitscore",
    "functional_family_id",
    "evidence_label",
    "claim_note",
    "source_locator",
    "source_sha256",
    "producer_id",
    "producer_receipt_sha256",
    "database_id",
    "database_version",
    "database_sha256",
)

_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
# GF3-2 (v2r2, V4 SS3.1): identity semantics converge on the shipped owner,
# mamey/mode_b/gene_first_explore.py. Region inputs normalize to region%03d; BGC
# aliases uppercase and require 3-4 digits; NODE_-prefixed tokens must carry the
# complete anti-shortening grammar (the HARD estate node-naming rule). Refusal, not
# substitution, remains the rule for unsafe characters (candidate-stricter, per V4).
_REGION_INPUT = re.compile(r"^region[_ -]?([0-9]{1,4})$", re.IGNORECASE)
_BGC_ALIAS = re.compile(r"^BGC[0-9]{3,4}$")
_NODE_ANTI_SHORTENING = re.compile(r"^NODE_[0-9]+_length_[0-9]+_cov_[0-9.]+$", re.IGNORECASE)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_PRODUCER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_PLACEHOLDER_LOCUS_TAGS = {
    "_nolocus",
    "nolocus",
    "unknown",
    "unknown_gene",
    "na",
    "n/a",
    "none",
    "missing",
}
_PLACEHOLDER_IDENTITY_COMPONENTS = {
    "unknown",
    "na",
    "n/a",
    "none",
    "missing",
    "node",
    "contig",
    "region",
    "bgc",
}


class StageHold(ValueError):
    """Typed fail-closed exception raised before a stage seal is written."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class LoadedStage:
    stage_dir: Path
    identity: dict[str, str]
    identity_token: str
    gene_roster: tuple[dict[str, str], ...]
    evidence: tuple[dict[str, str], ...]
    producer_receipts: tuple[dict[str, str], ...]
    locus_context: dict[str, Any]
    stage_receipt: dict[str, Any]
    stage_receipt_sha256: str
    query_roster_sha256: str


def _hold(code: str, detail: str) -> None:
    raise StageHold(code, detail)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _require_sha256(value: str, label: str) -> str:
    normalized = value.strip().lower()
    if not _SHA256.fullmatch(normalized):
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"{label} is not a lowercase SHA-256")
    return normalized


def _portable_locator(value: str, label: str) -> str:
    locator = value.strip()
    if not locator:
        _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} is blank")
    lowered = locator.lower()
    if (
        locator.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:[\\/]", locator)
        or lowered.startswith("file://")
        or "/users/" in lowered
        or "\\users\\" in lowered
        or "codex alex 2026" in lowered
    ):
        _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} is not a portable locator")
    path_part = locator.split("://", 1)[-1]
    if ".." in PurePosixPath(path_part.replace("\\", "/")).parts:
        _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} contains parent traversal")
    return locator


def _normalize_identity_component(field: str, value: str) -> str:
    """GF3-2 (v2r2): normalize mutually expressible spellings to the shipped
    gene_first_explore canonical form so one physical locus can never seal under
    two content-addressed identities (region7 vs region007 -- the V3 SSR join-debt
    finding). Non-normalizable values refuse; nothing is repaired by guesswork."""
    if field == "region":
        match = _REGION_INPUT.fullmatch(value)
        if match is None:
            _hold("MODEB_GF2_IDENTITY_HOLD", f"region must normalize to region###: {value!r}")
        return "region%03d" % int(match.group(1))
    if field == "bgc_alias":
        upper = value.upper()
        if not _BGC_ALIAS.fullmatch(upper):
            _hold("MODEB_GF2_IDENTITY_HOLD", f"BGC alias must be BGC### or BGC####: {value!r}")
        return upper
    return value


def canonical_identity(raw: Mapping[str, Any]) -> dict[str, str]:
    identity: dict[str, str] = {}
    for field in IDENTITY_FIELDS[:-1]:
        value = str(raw.get(field, "")).strip()
        if not value:
            _hold("MODEB_GF2_IDENTITY_HOLD", f"missing {field}")
        if value.lower() in _PLACEHOLDER_IDENTITY_COMPONENTS:
            _hold("MODEB_GF2_IDENTITY_HOLD", f"placeholder {field}: {value!r}")
        value = _normalize_identity_component(field, value)
        if not _SAFE_COMPONENT.fullmatch(value) or "__" in value:
            _hold("MODEB_GF2_IDENTITY_HOLD", f"unsafe {field}: {value!r}")
        identity[field] = value
    node = identity["full_node"]
    if node.upper().startswith("NODE_") and not _NODE_ANTI_SHORTENING.fullmatch(node):
        _hold(
            "MODEB_GF2_IDENTITY_HOLD",
            "shortened or malformed NODE token is prohibited "
            "(complete NODE_<n>_length_<n>_cov_<x> grammar required)",
        )
    if len(node) < 5:
        _hold("MODEB_GF2_IDENTITY_HOLD", "full node-or-contig identifier is shortened")
    expected = " / ".join(identity[field] for field in IDENTITY_FIELDS[:-1])
    supplied = str(raw.get("exact_identity", "")).strip()
    if supplied and supplied != expected:
        parts = [part.strip() for part in supplied.split(" / ")]
        normalized_supplied = supplied
        if len(parts) == 4:
            # A non-normalizable supplied part falls through to the conflict hold below.
            with contextlib.suppress(StageHold):
                normalized_supplied = " / ".join(
                    _normalize_identity_component(field, part)
                    for field, part in zip(IDENTITY_FIELDS[:-1], parts)
                )
        if normalized_supplied != expected:
            _hold("MODEB_GF2_IDENTITY_HOLD", "exact_identity conflicts with its components")
    identity["exact_identity"] = expected
    return identity


def identity_token(identity: Mapping[str, Any]) -> str:
    canonical = canonical_identity(identity)
    token = "__".join(canonical[field] for field in IDENTITY_FIELDS[:-1])
    if len(token.encode("utf-8")) > 180:
        _hold("MODEB_GF2_IDENTITY_HOLD", "complete identity token exceeds the portable filename limit")
    return token


def normalize_channel(value: str) -> tuple[str, str | None]:
    raw = value.strip().lower()
    normalized = CHANNEL_ALIASES.get(raw, raw)
    if normalized not in CANONICAL_CHANNELS:
        _hold("MODEB_GF2_CHANNEL_HOLD", f"unknown or collapsed channel: {value!r}")
    return normalized, raw if raw != normalized else None


def _read_json(path: Path, expected_type: type = dict) -> Any:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"cannot read JSON member {path.name}: {exc}")
    if not isinstance(value, expected_type):
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"{path.name} has the wrong JSON type")
    return value


def _read_tsv(path: Path, required_fields: Sequence[str]) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            header = reader.fieldnames or []
            if len(header) != len(set(header)):
                _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"{path.name} has duplicate headers")
            missing = [field for field in required_fields if field not in header]
            if missing:
                _hold(
                    "MODEB_GF2_STAGE_MEMBER_HOLD",
                    f"{path.name} is missing fields: {', '.join(missing)}",
                )
            rows = [
                {key: (value or "").strip() for key, value in row.items() if key is not None}
                for row in reader
            ]
    except StageHold:
        raise
    except (OSError, UnicodeError, csv.Error) as exc:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"cannot read TSV member {path.name}: {exc}")
    if not rows:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"{path.name} contains no data rows")
    return rows


def _require_identity_row(row: Mapping[str, str], identity: Mapping[str, str], label: str) -> None:
    for field in IDENTITY_FIELDS:
        if row.get(field, "") != identity[field]:
            _hold("MODEB_GF2_IDENTITY_HOLD", f"{label} conflicts at {field}")


def _parse_int(value: str, label: str, *, minimum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"{label} is not an integer")
    if minimum is not None and number < minimum:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"{label} must be at least {minimum}")
    return number


def _parse_float(value: str, label: str, *, minimum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} is not numeric")
    if not math.isfinite(number):
        _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} is not finite")
    if minimum is not None and number < minimum:
        _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} must be at least {minimum}")
    return number


def _validate_identity_member(path: Path) -> dict[str, str]:
    raw = _read_json(path)
    if raw.get("schema_version") != IDENTITY_SCHEMA:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"unsupported identity schema in {path.name}")
    identity = canonical_identity(raw)
    supplied_token = str(raw.get("identity_token", "")).strip()
    if supplied_token and supplied_token != identity_token(identity):
        _hold("MODEB_GF2_IDENTITY_HOLD", "identity_token conflicts with the complete identity")
    for locator_field, sha_field in (
        ("source_package_locator", "source_package_sha256"),
        ("region_source_locator", "region_source_sha256"),
    ):
        _portable_locator(str(raw.get(locator_field, "")), locator_field)
        _require_sha256(str(raw.get(sha_field, "")), sha_field)
    return identity


def _validate_roster(
    rows: list[dict[str, str]], identity: Mapping[str, str]
) -> list[dict[str, str]]:
    seen_tags: set[str] = set()
    seen_orders: set[int] = set()
    validated: list[tuple[int, dict[str, str]]] = []
    for row_number, row in enumerate(rows, start=2):
        label = f"gene roster row {row_number}"
        _require_identity_row(row, identity, label)
        membership = row["membership"]
        if membership not in {"EXACT_REGION", "BOUNDARY_CONTEXT_ONLY"}:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} has invalid membership")
        locus_tag = row["locus_tag"]
        if not locus_tag or locus_tag.lower() in _PLACEHOLDER_LOCUS_TAGS:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} has a placeholder locus tag")
        if not _SAFE_COMPONENT.fullmatch(locus_tag):
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} has an unsafe locus tag")
        if locus_tag in seen_tags:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"duplicate locus tag: {locus_tag}")
        gene_order = _parse_int(row["gene_order"], f"{label} gene_order", minimum=1)
        if gene_order in seen_orders:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"duplicate gene order: {gene_order}")
        start = _parse_int(row["cds_start"], f"{label} cds_start", minimum=0)
        end = _parse_int(row["cds_end"], f"{label} cds_end", minimum=1)
        if end <= start:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} has non-increasing coordinates")
        if row["strand"] not in {"+", "-"}:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} has invalid strand")
        _parse_int(row["protein_length_aa"], f"{label} protein_length_aa", minimum=1)
        _require_sha256(row["protein_sha256"], f"{label} protein_sha256")
        if not row["antismash_role"] or not row["gene_kind"]:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} lacks explicit source roles")
        if row["partial_state"] not in PARTIAL_STATES:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} has invalid partial_state")
        if row["boundary_proximity"] not in BOUNDARY_PROXIMITY_STATES:
            _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} has invalid boundary_proximity")
        _portable_locator(row["source_locator"], f"{label} source_locator")
        _require_sha256(row["source_sha256"], f"{label} source_sha256")
        seen_tags.add(locus_tag)
        seen_orders.add(gene_order)
        validated.append((gene_order, row))
    return [row for _, row in sorted(validated, key=lambda item: item[0])]


def query_roster_sha256(
    identity: Mapping[str, Any], gene_roster: Iterable[Mapping[str, str]]
) -> str:
    canonical = canonical_identity(identity)
    ordered = sorted(gene_roster, key=lambda row: int(row["gene_order"]))
    lines = [canonical["exact_identity"]]
    # GF3-1 (v2r3): an unchanged protein can be reassigned different physical
    # coordinates, strand, or roster membership after a boundary or source change —
    # the digest must see that, or a stale stage silently reuses. Deterministic field
    # order per V4 SS4: gene_order / locus_tag / cds_start / cds_end / strand /
    # membership / protein_sha256.
    lines.extend(
        "\t".join(
            (
                str(row["gene_order"]),
                row["locus_tag"],
                str(row["cds_start"]),
                str(row["cds_end"]),
                row["strand"],
                row["membership"],
                row["protein_sha256"].lower(),
            )
        )
        for row in ordered
    )
    return _sha256_bytes(("\n".join(lines) + "\n").encode("utf-8"))


def _validate_producers(
    rows: list[dict[str, str]],
    roster_digest: str,
    *,
    max_threads: int | None,
) -> tuple[dict[str, dict[str, str]], list[dict[str, str]]]:
    producers: dict[str, dict[str, str]] = {}
    aliases: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        label = f"producer receipt row {row_number}"
        producer_id = row["producer_id"]
        if not _PRODUCER_ID.fullmatch(producer_id):
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} has invalid producer_id")
        if producer_id in producers:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"duplicate producer_id: {producer_id}")
        channel, legacy = normalize_channel(row["channel"])
        if legacy:
            aliases.append(
                {
                    "member": "producer_receipts",
                    "row": str(row_number),
                    "from": legacy,
                    "to": channel,
                }
            )
        row["channel"] = channel
        if row["producer_state"] not in PRODUCER_STATES:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} has invalid producer_state")
        if row["completeness"] not in COMPLETENESS_STATES:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} has invalid completeness")
        for field in (
            "tool_name",
            "tool_version",
            "parameter_fingerprint",
            "database_id",
            "database_version",
            "resource_policy_id",
        ):
            if not row[field]:
                _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} has blank {field}")
        if _require_sha256(row["query_roster_sha256"], f"{label} query_roster_sha256") != roster_digest:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} uses a different query roster")
        for field in ("database_sha256", "output_sha256", "receipt_sha256"):
            _require_sha256(row[field], f"{label} {field}")
        _portable_locator(row["output_locator"], f"{label} output_locator")
        _parse_int(row["output_bytes"], f"{label} output_bytes", minimum=0)
        threads = _parse_int(row["threads_used"], f"{label} threads_used", minimum=0)
        if max_threads is not None and threads > max_threads:
            _hold(
                "MODEB_GF2_PRODUCER_HOLD",
                f"{label} records {threads} threads above policy maximum {max_threads}",
            )
        if row["duration_seconds"]:
            _parse_float(row["duration_seconds"], f"{label} duration_seconds", minimum=0.0)
        producers[producer_id] = row
    covered = {row["channel"] for row in producers.values()}
    missing = sorted(set(CANONICAL_CHANNELS) - covered)
    if missing:
        _hold("MODEB_GF2_PRODUCER_HOLD", f"missing producer receipts for: {', '.join(missing)}")
    return producers, aliases


def _validate_bound_alignment(row: Mapping[str, str], label: str) -> None:
    for field in (
        "hit_rank",
        "subject_accession",
        "subject_name",
        "pct_identity",
        "pct_positives",
        "query_coverage",
        "aligned_length",
        "evalue",
        "bitscore",
    ):
        if not row[field]:
            _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} lacks {field}")
    _parse_int(row["hit_rank"], f"{label} hit_rank", minimum=1)
    for field in ("pct_identity", "pct_positives", "query_coverage"):
        value = _parse_float(row[field], f"{label} {field}", minimum=0.0)
        if value > 100.0:
            _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} {field} exceeds 100")
    _parse_int(row["aligned_length"], f"{label} aligned_length", minimum=1)
    _parse_float(row["evalue"], f"{label} evalue", minimum=0.0)
    _parse_float(row["bitscore"], f"{label} bitscore", minimum=0.0)


def _validate_evidence(
    rows: list[dict[str, str]],
    identity: Mapping[str, str],
    roster: Sequence[Mapping[str, str]],
    producers: Mapping[str, Mapping[str, str]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    roster_by_tag = {row["locus_tag"]: row for row in roster}
    aliases: list[dict[str, str]] = []
    observed: dict[tuple[str, str], list[dict[str, str]]] = {}
    channel_rows: dict[str, int] = {channel: 0 for channel in CANONICAL_CHANNELS}
    validated: list[dict[str, str]] = []
    for row_number, row in enumerate(rows, start=2):
        label = f"evidence row {row_number}"
        _require_identity_row(row, identity, label)
        channel, legacy = normalize_channel(row["channel"])
        if legacy:
            aliases.append(
                {
                    "member": "evidence_observations",
                    "row": str(row_number),
                    "from": legacy,
                    "to": channel,
                }
            )
        row["channel"] = channel
        channel_rows[channel] += 1
        scope = row["observation_scope"]
        if scope not in {"GENE", "BGC"}:
            _hold("MODEB_GF2_CHANNEL_HOLD", f"{label} has invalid observation_scope")
        if row["mapped_state"] not in MAPPED_STATES:
            _hold("MODEB_GF2_CHANNEL_HOLD", f"{label} has invalid mapped_state")
        if not row["source_state"]:
            _hold("MODEB_GF2_CHANNEL_HOLD", f"{label} lacks lossless source_state")
        if not row["claim_note"]:
            _hold("MODEB_GF2_CHANNEL_HOLD", f"{label} lacks a claim ceiling note")
        _portable_locator(row["source_locator"], f"{label} source_locator")
        _require_sha256(row["source_sha256"], f"{label} source_sha256")
        producer = producers.get(row["producer_id"])
        if producer is None:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} references no admitted producer")
        if producer["channel"] != channel:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} producer channel conflicts")
        if row["producer_receipt_sha256"] != producer["receipt_sha256"]:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} producer receipt SHA conflicts")
        if row["source_locator"] != producer["output_locator"]:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} source locator conflicts with producer output")
        if row["source_sha256"] != producer["output_sha256"]:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} source SHA conflicts with producer output")
        for field in ("database_id", "database_version", "database_sha256"):
            if row[field] != producer[field]:
                _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} producer database field {field} conflicts")
        mapped_state = row["mapped_state"]
        producer_state = producer["producer_state"]
        if mapped_state == "BOUND" and producer_state != "COMPLETE":
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} BOUND row lacks a complete producer")
        if mapped_state == "NO_BOUND_HIT" and producer_state not in {"COMPLETE", "NO_HIT_COMPLETE"}:
            _hold("MODEB_GF2_PRODUCER_HOLD", f"{label} no-hit state lacks a completed producer")
        expected_gap_producer_states = {
            "NOT_RUN": "NOT_RUN",
            "RUNNING_NOT_YET_INGESTED": "RUNNING",
            "INGEST_GAP": "INGEST_GAP",
            "PROVENANCE_HOLD": "PROVENANCE_HOLD",
            "NOT_APPLICABLE": "NOT_APPLICABLE",
            "REGISTRY_ONLY_NOT_EXECUTED": "REGISTRY_ONLY",
        }
        expected_producer_state = expected_gap_producer_states.get(mapped_state)
        if expected_producer_state is not None and producer_state != expected_producer_state:
            _hold(
                "MODEB_GF2_PRODUCER_HOLD",
                f"{label} {mapped_state} conflicts with producer state {producer_state}",
            )
        if scope == "GENE":
            locus_tag = row["locus_tag"]
            roster_row = roster_by_tag.get(locus_tag)
            if roster_row is None:
                _hold("MODEB_GF2_GENE_ROSTER_HOLD", f"{label} references an unknown locus tag")
            query_sha = _require_sha256(row["query_sha256"], f"{label} query_sha256")
            if query_sha != roster_row["protein_sha256"]:
                _hold("MODEB_GF2_QUERY_HASH_HOLD", f"{label} query differs from canonical protein")
            observed.setdefault((channel, locus_tag), []).append(row)
        else:
            if row["locus_tag"] or row["query_sha256"]:
                _hold("MODEB_GF2_CHANNEL_HOLD", f"{label} BGC row carries gene-only fields")
        if mapped_state == "BOUND" and channel in ALIGNMENT_CHANNELS:
            if scope != "GENE":
                _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} alignment result is not gene scoped")
            _validate_bound_alignment(row, label)
        if mapped_state == "BOUND" and channel not in ALIGNMENT_CHANNELS:
            if not row["evidence_label"]:
                _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} lacks evidence_label")
            if channel == "mibig" and not row["subject_accession"]:
                _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{label} MIBiG relation lacks reference accession")
        validated.append(row)

    for channel in CANONICAL_CHANNELS:
        if channel_rows[channel] == 0:
            _hold("MODEB_GF2_CHANNEL_HOLD", f"required channel has no explicit state: {channel}")
    for channel in ALIGNMENT_CHANNELS:
        for locus_tag in roster_by_tag:
            gene_rows = observed.get((channel, locus_tag), [])
            if not gene_rows:
                _hold(
                    "MODEB_GF2_CHANNEL_HOLD",
                    f"{channel} lacks an explicit state for locus tag {locus_tag}",
                )
            states = {row["mapped_state"] for row in gene_rows}
            if "BOUND" in states:
                if states != {"BOUND"}:
                    _hold("MODEB_GF2_CHANNEL_HOLD", f"{channel}/{locus_tag} mixes BOUND and gap states")
                ranks = [int(row["hit_rank"]) for row in gene_rows]
                if len(ranks) != len(set(ranks)) or 1 not in ranks:
                    _hold("MODEB_GF2_BOUND_ROW_HOLD", f"{channel}/{locus_tag} lacks unique rank 1")
            elif len(gene_rows) != 1:
                _hold("MODEB_GF2_CHANNEL_HOLD", f"{channel}/{locus_tag} has multiple typed gaps")
    return validated, aliases


def _validate_context(path: Path, identity: Mapping[str, str]) -> dict[str, Any]:
    context = _read_json(path)
    if context.get("schema_version") != CONTEXT_SCHEMA:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"unsupported context schema in {path.name}")
    context_identity = canonical_identity(context)
    if context_identity != identity:
        _hold("MODEB_GF2_IDENTITY_HOLD", "locus context identity conflicts")
    if context.get("bgc_boundary_state") not in BGC_BOUNDARY_STATES:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "invalid bgc_boundary_state")
    if context.get("assembly_fragmentation_tier") not in ASSEMBLY_FRAGMENTATION_TIERS:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "invalid assembly_fragmentation_tier")
    if context.get("detector_window_state") not in DETECTOR_WINDOW_STATES:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "invalid detector_window_state")
    if context.get("canonical_fragment_ceiling_state") not in FRAGMENT_CEILING_STATES:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "invalid canonical_fragment_ceiling_state")
    if context.get("canonical_fragment_ceiling_owner") != "mamey.fragment_ceiling":
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "canonical fragment ceiling owner is not bound")
    if not str(context.get("canonical_fragment_ceiling_reason", "")).strip():
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "canonical fragment ceiling reason is blank")
    start = _parse_int(str(context.get("region_start", "")), "region_start", minimum=0)
    end = _parse_int(str(context.get("region_end", "")), "region_end", minimum=1)
    contig_length = _parse_int(str(context.get("contig_length", "")), "contig_length", minimum=1)
    if end <= start or end > contig_length:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "locus context interval is invalid")
    _portable_locator(str(context.get("source_locator", "")), "locus context source_locator")
    _require_sha256(str(context.get("source_sha256", "")), "locus context source_sha256")
    return context


def _expected_member_paths(stage_dir: Path) -> dict[str, Path]:
    token = stage_dir.name
    return {
        "identity": stage_dir / f"{token}__identity.json",
        "gene_roster": stage_dir / f"{token}__gene_roster.tsv",
        "evidence_observations": stage_dir / f"{token}__evidence_observations.tsv",
        "locus_context": stage_dir / f"{token}__locus_context.json",
        "producer_receipts": stage_dir / f"{token}__producer_receipts.tsv",
    }


def _load_and_validate_members(
    stage_dir: Path,
    *,
    max_threads: int | None,
    allow_receipt: bool = False,
) -> tuple[
    dict[str, str],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    dict[str, Any],
    str,
    list[dict[str, str]],
    dict[str, Path],
]:
    if not stage_dir.is_dir():
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "stage directory does not exist")
    paths = _expected_member_paths(stage_dir)
    missing = [path.name for path in paths.values() if not path.is_file()]
    if missing:
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", f"missing stage members: {', '.join(missing)}")
    allowed_names = {path.name for path in paths.values()}
    if allow_receipt:
        allowed_names.add(f"{stage_dir.name}__stage_receipt.json")
    unexpected = sorted(entry.name for entry in stage_dir.iterdir() if entry.name not in allowed_names)
    if unexpected:
        _hold(
            "MODEB_GF2_STAGE_TAMPER_HOLD" if allow_receipt else "MODEB_GF2_STAGE_MEMBER_HOLD",
            f"unexpected stage members: {', '.join(unexpected)}",
        )
    identity = _validate_identity_member(paths["identity"])
    token = identity_token(identity)
    if stage_dir.name != token:
        _hold("MODEB_GF2_IDENTITY_HOLD", "stage directory is not the complete identity token")
    roster = _validate_roster(_read_tsv(paths["gene_roster"], ROSTER_FIELDS), identity)
    roster_digest = query_roster_sha256(identity, roster)
    producers, producer_aliases = _validate_producers(
        _read_tsv(paths["producer_receipts"], PRODUCER_FIELDS),
        roster_digest,
        max_threads=max_threads,
    )
    evidence, evidence_aliases = _validate_evidence(
        _read_tsv(paths["evidence_observations"], EVIDENCE_FIELDS),
        identity,
        roster,
        producers,
    )
    context = _validate_context(paths["locus_context"], identity)
    aliases = sorted(
        producer_aliases + evidence_aliases,
        key=lambda row: (row["member"], int(row["row"]), row["from"], row["to"]),
    )
    return (
        identity,
        roster,
        evidence,
        list(producers.values()),
        context,
        roster_digest,
        aliases,
        paths,
    )


def _member_records(paths: Mapping[str, Path]) -> list[dict[str, Any]]:
    return [
        {
            "role": role,
            "name": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for role, path in sorted(paths.items())
    ]


def _stage_basis(
    identity: Mapping[str, str],
    members: Sequence[Mapping[str, Any]],
    roster_digest: str,
    aliases: Sequence[Mapping[str, str]],
    max_threads: int | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "identity": dict(identity),
        "identity_token": identity_token(identity),
        "canonical_channels": list(CANONICAL_CHANNELS),
        "query_roster_sha256": roster_digest,
        "legacy_alias_normalizations": list(aliases),
        "thread_policy_max": max_threads,
        "members": list(members),
    }


def seal_stage(
    stage_dir: str | Path,
    *,
    max_threads: int | None = None,
    sealed_utc: str | None = None,
) -> dict[str, Any]:
    """Validate an existing exact-locus directory and add one stage receipt.

    All member and policy validation finishes before the exclusive receipt write.
    The caller prepares the five compact members; this function runs no producer.
    """

    directory = Path(stage_dir)
    if max_threads is not None and max_threads < 1:
        _hold("MODEB_GF2_PRODUCER_HOLD", "max_threads must be positive when supplied")
    receipt_path = directory / f"{directory.name}__stage_receipt.json"
    if receipt_path.exists():
        _hold("MODEB_GF2_OUTPUT_REFUSED", f"stage receipt already exists: {receipt_path.name}")
    (
        identity,
        roster,
        evidence,
        producers,
        _context,
        roster_digest,
        aliases,
        paths,
    ) = _load_and_validate_members(directory, max_threads=max_threads, allow_receipt=False)
    members = _member_records(paths)
    basis = _stage_basis(identity, members, roster_digest, aliases, max_threads)
    stage_id = _sha256_bytes(_canonical_json_bytes(basis))
    receipt = {
        **basis,
        "stage_id": stage_id,
        "sealed_utc": sealed_utc or datetime.now(timezone.utc).isoformat(),
        "counts": {
            "genes": len(roster),
            "evidence_rows": len(evidence),
            "producer_receipts": len(producers),
        },
        "authority_ceiling": "ENGINEERING_CANDIDATE_STAGE_ONLY_JUDGMENT_DEFERRED",
        "self_excluding_receipt": True,
    }
    payload = json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    try:
        with receipt_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        _hold("MODEB_GF2_OUTPUT_REFUSED", f"stage receipt already exists: {receipt_path.name}")
    except OSError as exc:
        _hold("MODEB_GF2_OUTPUT_REFUSED", f"could not write stage receipt: {exc}")
    return receipt


def load_sealed_stage(stage_dir: str | Path) -> LoadedStage:
    """Revalidate a sealed stage and reject any changed retained member."""

    directory = Path(stage_dir)
    receipt_path = directory / f"{directory.name}__stage_receipt.json"
    if not receipt_path.is_file():
        _hold("MODEB_GF2_STAGE_MEMBER_HOLD", "stage receipt is missing")
    receipt = _read_json(receipt_path)
    receipt_schema = receipt.get("schema_version")
    if receipt_schema != SCHEMA_VERSION:
        _hold(
            "MODEB_GF2_STAGE_MEMBER_HOLD",
            f"stage receipt schema {receipt_schema!r} does not match this engine's "
            f"{SCHEMA_VERSION!r} — v2 and v2.1 stages are never mixed; re-stage the locus",
        )
    max_threads = receipt.get("thread_policy_max")
    if max_threads is not None and (not isinstance(max_threads, int) or max_threads < 1):
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "receipt thread policy is invalid")
    (
        identity,
        roster,
        evidence,
        producers,
        context,
        roster_digest,
        aliases,
        paths,
    ) = _load_and_validate_members(directory, max_threads=max_threads, allow_receipt=True)
    members = _member_records(paths)
    expected_members = receipt.get("members")
    if expected_members != members:
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "sealed member name, byte count, or hash changed")
    basis = _stage_basis(identity, members, roster_digest, aliases, max_threads)
    expected_stage_id = _sha256_bytes(_canonical_json_bytes(basis))
    if receipt.get("stage_id") != expected_stage_id:
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "stage ID does not match the sealed content")
    for field in (
        "schema_version",
        "identity",
        "identity_token",
        "canonical_channels",
        "query_roster_sha256",
        "legacy_alias_normalizations",
        "thread_policy_max",
    ):
        if receipt.get(field) != basis[field]:
            _hold("MODEB_GF2_STAGE_TAMPER_HOLD", f"receipt field changed: {field}")
    expected_counts = {
        "genes": len(roster),
        "evidence_rows": len(evidence),
        "producer_receipts": len(producers),
    }
    if receipt.get("counts") != expected_counts:
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "receipt counts do not match retained members")
    if receipt.get("authority_ceiling") != "ENGINEERING_CANDIDATE_STAGE_ONLY_JUDGMENT_DEFERRED":
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "receipt authority ceiling changed")
    if receipt.get("self_excluding_receipt") is not True:
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "receipt self-exclusion marker changed")
    sealed_utc = receipt.get("sealed_utc")
    if not isinstance(sealed_utc, str):
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "receipt sealed_utc is missing")
    try:
        datetime.fromisoformat(sealed_utc.replace("Z", "+00:00"))
    except ValueError:
        _hold("MODEB_GF2_STAGE_TAMPER_HOLD", "receipt sealed_utc is invalid")
    return LoadedStage(
        stage_dir=directory,
        identity=identity,
        identity_token=directory.name,
        gene_roster=tuple(roster),
        evidence=tuple(evidence),
        producer_receipts=tuple(producers),
        locus_context=context,
        stage_receipt=receipt,
        stage_receipt_sha256=sha256_file(receipt_path),
        query_roster_sha256=roster_digest,
    )


__all__ = [
    "ALIGNMENT_CHANNELS",
    "CANONICAL_CHANNELS",
    "CHANNEL_ALIASES",
    "CONTEXT_SCHEMA",
    "EVIDENCE_FIELDS",
    "IDENTITY_FIELDS",
    "IDENTITY_SCHEMA",
    "LoadedStage",
    "MAPPED_STATES",
    "PRODUCER_FIELDS",
    "ROSTER_FIELDS",
    "SCHEMA_VERSION",
    "StageHold",
    "canonical_identity",
    "identity_token",
    "load_sealed_stage",
    "normalize_channel",
    "query_roster_sha256",
    "seal_stage",
    "sha256_file",
]
