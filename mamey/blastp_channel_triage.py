"""Fail-closed post-seal comparison of distinct ``nr`` and ``clustered_nr`` evidence.

This module is intentionally a sidecar contract.  It does not alter package scoring,
ingestion, or reports, and it never promotes one channel over the other.  Callers must
provide an exact BGC identity map and an immutable-source receipt; alias-only or
default-source comparisons are refused before an output is written.
"""
from __future__ import annotations

import contextlib
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter  # v9.7.409 export-injection: CSV formula-cell guard
except ImportError:  # module loaded by file path without a parent package (tests do this)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter
import hashlib
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


CHANNELS = ("nr", "clustered_nr")
HIT_REQUIRED_COLUMNS = (
    "strain",
    "bgc_id",
    "gene",
    "hit_rank",
    "subject_acc",
    "channel",
    "source_file_sha256",
)
IDENTITY_REQUIRED_COLUMNS = ("strain", "full_node", "region", "bgc_alias")
PROVENANCE_REQUIRED_COLUMNS = (
    "channel",
    "source_file_sha256",
    "source_locator",
    "source_bytes",
    "source_label",
)
OUTPUT_COLUMNS = (
    "strain",
    "full_node",
    "region",
    "bgc_alias",
    "locus_tag",
    "triage_state",
    "nr_rank1_rows",
    "clustered_nr_rank1_rows",
    "nr_subject_acc",
    "nr_pct_identity",
    "nr_query_coverage",
    "nr_source_label",
    "nr_source_locator",
    "nr_source_file_sha256",
    "nr_source_bytes",
    "clustered_nr_subject_acc",
    "clustered_nr_pct_identity",
    "clustered_nr_query_coverage",
    "clustered_nr_source_label",
    "clustered_nr_source_locator",
    "clustered_nr_source_file_sha256",
    "clustered_nr_source_bytes",
    "engineering_note",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ContractError(ValueError):
    """The comparison inputs are insufficiently bound for a safe triage."""


def _clean(value: object | None) -> str:
    return str(value or "").strip()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _input_binding(path: Path) -> dict[str, object]:
    return {"name": path.name, "sha256": _sha256_file(path), "bytes": path.stat().st_size}


def _read_table(path: str | Path) -> tuple[list[dict[str, str]], tuple[str, ...]]:
    source = Path(path)
    try:
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            delimiter = "\t" if source.suffix.lower() == ".tsv" else ","
            reader = csv.DictReader(handle, delimiter=delimiter)
            if not reader.fieldnames:
                raise ContractError(f"{source.name}: missing header row")
            headers = tuple(_clean(header) for header in reader.fieldnames)
            return [dict(row) for row in reader], headers
    except OSError as exc:
        raise ContractError(f"cannot read {source.name}: {exc}") from exc


def _require_columns(headers: tuple[str, ...], required: tuple[str, ...], label: str) -> None:
    missing = [column for column in required if column not in headers]
    if missing:
        raise ContractError(f"{label}: missing required columns {', '.join(missing)}")


def _source_sha(value: object | None, label: str) -> str:
    result = _clean(value).lower()
    if not _SHA256_RE.fullmatch(result):
        raise ContractError(f"{label}: source_file_sha256 must be a 64-character SHA-256")
    return result


def _positive_int(value: object | None, label: str) -> int:
    raw = _clean(value)
    try:
        result = int(raw)
    except ValueError as exc:
        raise ContractError(f"{label}: expected a positive integer, got {raw!r}") from exc
    if result < 1:
        raise ContractError(f"{label}: expected a positive integer, got {raw!r}")
    return result


def _portable_locator(value: object | None, label: str) -> str:
    locator = _clean(value).replace("\\", "/")
    if not locator:
        raise ContractError(f"{label}: source_locator is required")
    if locator.startswith("/") or re.match(r"^[A-Za-z]:/", locator):
        raise ContractError(f"{label}: source_locator must be portable and relative")
    parts = PurePosixPath(locator).parts
    if ".." in parts:
        raise ContractError(f"{label}: source_locator must not contain parent traversal")
    return locator


def _identity_map(rows: list[dict[str, str]], headers: tuple[str, ...]) -> dict[tuple[str, str], dict[str, str]]:
    _require_columns(headers, IDENTITY_REQUIRED_COLUMNS, "identity map")
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        values = {column: _clean(row.get(column)) for column in IDENTITY_REQUIRED_COLUMNS}
        if not all(values.values()):
            raise ContractError(f"identity map row {row_number}: complete four-part BGC identity is required")
        key = (values["strain"], values["bgc_alias"])
        if key in result:
            raise ContractError(
                f"identity map row {row_number}: duplicate alias mapping for {values['strain']}/{values['bgc_alias']}"
            )
        result[key] = values
    if not result:
        raise ContractError("identity map: no identity rows")
    return result


def _provenance_map(rows: list[dict[str, str]], headers: tuple[str, ...]) -> dict[tuple[str, str], dict[str, str]]:
    _require_columns(headers, PROVENANCE_REQUIRED_COLUMNS, "provenance receipt")
    result: dict[tuple[str, str], dict[str, str]] = {}
    for row_number, row in enumerate(rows, start=2):
        channel = _clean(row.get("channel"))
        if channel not in CHANNELS:
            raise ContractError(f"provenance receipt row {row_number}: unsupported channel {channel!r}")
        sha = _source_sha(row.get("source_file_sha256"), f"provenance receipt row {row_number}")
        values = {
            "source_label": _clean(row.get("source_label")),
            "source_locator": _portable_locator(row.get("source_locator"), f"provenance receipt row {row_number}"),
            "source_bytes": str(_positive_int(row.get("source_bytes"), f"provenance receipt row {row_number}")),
        }
        if not values["source_label"]:
            raise ContractError(f"provenance receipt row {row_number}: source_label is required; no default is allowed")
        key = (channel, sha)
        if key in result:
            raise ContractError(f"provenance receipt row {row_number}: duplicate channel/source SHA binding")
        result[key] = values
    if not result:
        raise ContractError("provenance receipt: no provenance rows")
    return result


def _validated_hits(
    rows: list[dict[str, str]], headers: tuple[str, ...], identities: dict[tuple[str, str], dict[str, str]]
) -> tuple[dict[tuple[str, str, str, str, str], dict[str, list[dict[str, str]]]], int]:
    _require_columns(headers, HIT_REQUIRED_COLUMNS, "hits table")
    grouped: dict[tuple[str, str, str, str, str], dict[str, list[dict[str, str]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    ignored_non_rank1 = 0
    for row_number, row in enumerate(rows, start=2):
        strain = _clean(row.get("strain"))
        bgc_alias = _clean(row.get("bgc_id"))
        locus_tag = _clean(row.get("gene"))
        channel = _clean(row.get("channel"))
        subject_acc = _clean(row.get("subject_acc"))
        if not all((strain, bgc_alias, locus_tag, channel, subject_acc)):
            raise ContractError(f"hits table row {row_number}: strain, bgc_id, gene, channel, and subject_acc are required")
        if channel not in CHANNELS:
            raise ContractError(f"hits table row {row_number}: unsupported channel {channel!r}")
        hit_rank = _positive_int(row.get("hit_rank"), f"hits table row {row_number}")
        source_sha = _source_sha(row.get("source_file_sha256"), f"hits table row {row_number}")
        identity = identities.get((strain, bgc_alias))
        if identity is None:
            raise ContractError(
                f"hits table row {row_number}: no complete identity-map row for {strain}/{bgc_alias}; refusing alias-only grouping"
            )
        cleaned = {
            "subject_acc": subject_acc,
            "pct_identity": _clean(row.get("pct_identity")),
            "query_coverage": _clean(row.get("query_coverage")),
            "source_file_sha256": source_sha,
            "hit_rank": str(hit_rank),
        }
        key = (
            identity["strain"],
            identity["full_node"],
            identity["region"],
            identity["bgc_alias"],
            locus_tag,
        )
        grouped[key][channel].append(cleaned)
        if hit_rank != 1:
            ignored_non_rank1 += 1
    if not grouped:
        raise ContractError("hits table: no hit rows")
    return grouped, ignored_non_rank1


def _evidence_cells(
    prefix: str, record: dict[str, str] | None, provenance: dict[tuple[str, str], dict[str, str]]
) -> dict[str, str]:
    cells = {
        f"{prefix}_subject_acc": "",
        f"{prefix}_pct_identity": "",
        f"{prefix}_query_coverage": "",
        f"{prefix}_source_label": "",
        f"{prefix}_source_locator": "",
        f"{prefix}_source_file_sha256": "",
        f"{prefix}_source_bytes": "",
    }
    if record is None:
        return cells
    cells.update(
        {
            f"{prefix}_subject_acc": record["subject_acc"],
            f"{prefix}_pct_identity": record["pct_identity"],
            f"{prefix}_query_coverage": record["query_coverage"],
            f"{prefix}_source_file_sha256": record["source_file_sha256"],
        }
    )
    receipt = provenance.get((prefix, record["source_file_sha256"]))
    if receipt:
        cells.update(
            {
                f"{prefix}_source_label": receipt["source_label"],
                f"{prefix}_source_locator": receipt["source_locator"],
                f"{prefix}_source_bytes": receipt["source_bytes"],
            }
        )
    return cells


def _classify(
    channel_rows: dict[str, list[dict[str, str]]], provenance: dict[tuple[str, str], dict[str, str]]
) -> tuple[str, str, dict[str, dict[str, str] | None], dict[str, int]]:
    rank1 = {channel: [row for row in channel_rows.get(channel, []) if row["hit_rank"] == "1"] for channel in CHANNELS}
    counts = {channel: len(rank1[channel]) for channel in CHANNELS}
    selected: dict[str, dict[str, str] | None] = {channel: None for channel in CHANNELS}

    for channel in CHANNELS:
        if rank1[channel]:
            if len(rank1[channel]) == 1:
                selected[channel] = rank1[channel][0]
    if any(count > 1 for count in counts.values()):
        return (
            "HOLD_AMBIGUOUS_RANK1",
            "Multiple rank-1 rows in one channel; that channel was not selected.",
            selected,
            counts,
        )
    if any(channel_rows.get(channel) and not rank1[channel] for channel in CHANNELS):
        return (
            "HOLD_MISSING_RANK1",
            "A represented channel has no rank-1 row; no comparison was made.",
            selected,
            counts,
        )

    missing_provenance = [
        channel
        for channel in CHANNELS
        if selected[channel] and (channel, selected[channel]["source_file_sha256"]) not in provenance
    ]
    if missing_provenance:
        return (
            "HOLD_MISSING_PROVENANCE",
            "A rank-1 row lacks an explicit immutable-source receipt; no channel conclusion was made.",
            selected,
            counts,
        )

    nr = selected["nr"]
    clustered = selected["clustered_nr"]
    if nr and clustered:
        if nr["source_file_sha256"] == clustered["source_file_sha256"]:
            return (
                "HOLD_SHARED_SOURCE_ARTIFACT",
                "Both channels bind the same source SHA-256; independence is not established.",
                selected,
                counts,
            )
        if nr["subject_acc"] == clustered["subject_acc"]:
            return (
                "CONCORDANT_SUBJECT_ACCESSION",
                "Rank-1 accessions match; this is not a cross-channel identity or biological conclusion.",
                selected,
                counts,
            )
        return (
            "DISAGREE_DIFFERENT_SUBJECT_ACCESSION",
            "Rank-1 accessions differ; retain both channels and route for review without choosing a winner.",
            selected,
            counts,
        )
    if nr:
        return "ONLY_NR", "Only nr has a rank-1 row; absence is not evidence of equivalence.", selected, counts
    if clustered:
        return (
            "ONLY_CLUSTERED_NR",
            "Only clustered_nr has a rank-1 row; absence is not evidence of equivalence.",
            selected,
            counts,
        )
    return "HOLD_NO_CHANNEL_EVIDENCE", "No rank-1 evidence exists for either supported channel.", selected, counts


def build_triage(
    hits_path: str | Path, identity_map_path: str | Path, provenance_path: str | Path
) -> tuple[list[dict[str, str]], dict[str, Any]]:
    """Validate the three explicit contracts and return typed engineering triage rows.

    The returned rows preserve both channels.  They do not score, merge, reconstruct, or
    adjudicate a BGC, protein function, or biological claim.
    """
    hits = Path(hits_path)
    identity_map = Path(identity_map_path)
    provenance = Path(provenance_path)
    identity_rows, identity_headers = _read_table(identity_map)
    provenance_rows, provenance_headers = _read_table(provenance)
    hit_rows, hit_headers = _read_table(hits)
    identities = _identity_map(identity_rows, identity_headers)
    receipts = _provenance_map(provenance_rows, provenance_headers)
    grouped, ignored_non_rank1 = _validated_hits(hit_rows, hit_headers, identities)

    output: list[dict[str, str]] = []
    for key in sorted(grouped):
        state, note, selected, rank1_counts = _classify(grouped[key], receipts)
        strain, full_node, region, bgc_alias, locus_tag = key
        row: dict[str, str] = {
            "strain": strain,
            "full_node": full_node,
            "region": region,
            "bgc_alias": bgc_alias,
            "locus_tag": locus_tag,
            "triage_state": state,
            "nr_rank1_rows": str(rank1_counts["nr"]),
            "clustered_nr_rank1_rows": str(rank1_counts["clustered_nr"]),
            "engineering_note": note,
        }
        row.update(_evidence_cells("nr", selected["nr"], receipts))
        row.update(_evidence_cells("clustered_nr", selected["clustered_nr"], receipts))
        output.append(row)

    state_counts = dict(sorted(Counter(row["triage_state"] for row in output).items()))
    receipt: dict[str, Any] = {
        "schema_version": "blastp-channel-triage-v1",
        "input_bindings": {
            "hits": _input_binding(hits),
            "identity_map": _input_binding(identity_map),
            "provenance": _input_binding(provenance),
        },
        "rows": {
            "input_hit_rows": len(hit_rows),
            "non_rank1_input_rows_not_compared": ignored_non_rank1,
            "triage_rows": len(output),
        },
        "triage_state_counts": state_counts,
        "contract": {
            "exact_identity_required": True,
            "source_label_default_allowed": False,
            "supported_channels": list(CHANNELS),
            "cross_channel_winner_selected": False,
            "scope": "Typed engineering triage only; no score, merge, scientific adjudication, or source mutation.",
        },
    }
    return output, receipt


def _atomic_write(path: Path, text: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temporary_name, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(temporary_name)
        raise


def run_triage(
    hits_path: str | Path, identity_map_path: str | Path, provenance_path: str | Path, out_dir: str | Path
) -> dict[str, Any]:
    """Write a new triage table and receipt without modifying any input or package file."""
    out = Path(out_dir)
    output_path = out / "blastp_channel_triage.tsv"
    receipt_path = out / "blastp_channel_triage_receipt.json"
    if output_path.exists() or receipt_path.exists():
        raise FileExistsError("refusing to overwrite existing triage outputs; use a new --out directory")
    rows, receipt = build_triage(hits_path, identity_map_path, provenance_path)
    out.mkdir(parents=True, exist_ok=True)
    import io

    buffer = io.StringIO(newline="")
    writer = _SafeDictWriter(buffer, fieldnames=OUTPUT_COLUMNS, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows({column: row.get(column, "") for column in OUTPUT_COLUMNS} for row in rows)
    table_text = buffer.getvalue()
    _atomic_write(output_path, table_text)
    receipt["output"] = {
        "triage_table": {
            "name": output_path.name,
            "sha256": _sha256_file(output_path),
            "bytes": output_path.stat().st_size,
        }
    }
    _atomic_write(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return {
        "triage_table": receipt["output"]["triage_table"],
        "receipt": {"name": receipt_path.name, "sha256": _sha256_file(receipt_path), "bytes": receipt_path.stat().st_size},
        "triage_state_counts": receipt["triage_state_counts"],
    }
