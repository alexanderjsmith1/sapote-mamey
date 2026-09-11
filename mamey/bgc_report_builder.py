#!/usr/bin/env python3
"""Build refreshable exact-identity BGC evidence reports from SQLite inputs.

The first tranche emits Markdown/JSON/TSV only.  It does not render, infer a
named metabolite, merge BLASTP channels, or convert a historical BGC ordinal
into an authoritative identity key.
"""

from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import argparse
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
import sqlite3
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


SCHEMA_VERSION = "sapote_refreshable_bgc_report_v1"
PRIVATE_PREFIXES = ("AJS-", "PENDING-")  # v9.7.409 N1: AS- is PUBLIC per GOVERNANCE_DECISIONS.json GOV-001 (PI decision 2026-07-06); matches cli.py
CLAIM_CEILING = (
    "Architecture, sequence identity, comparator topology, and reference literature can support "
    "pathway-family or component-capacity hypotheses. They do not establish exact product identity, "
    "a complete pathway, cross-contig physical linkage, expression, production, activity, novelty, "
    "ecology, stereochemistry, yield, or organism identity."
)


def _captured_at(value: str | None) -> tuple[str, str]:
    if value is None:
        return datetime.now(timezone.utc).isoformat(), "RUNTIME_CLOCK_NOT_BYTE_REPRODUCIBLE"
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--captured-at-utc must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(), "CALLER_BOUND_REPRODUCIBLE_TIMESTAMP"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _input_paths(args: argparse.Namespace) -> list[Path]:
    paths = [
        args.identity_db,
        args.source_discovery_catalog,
        args.source_discovery_decisions,
    ]
    paths.extend(
        path for path in (
            args.blastp_reconciliation,
            args.modeb_ledger,
            args.literature_json,
    ) if path is not None
    )
    paths.extend(args.locus_project)
    collection_registry = getattr(args, "source_collection_registry", None)
    if collection_registry is not None:
        paths.append(collection_registry)
    paths.extend(getattr(args, "source_availability_binding_table", []) or [])
    unique = {str(path.resolve()): path for path in paths}
    return [unique[key] for key in sorted(unique)]


def _source_discovery_preflight(args: argparse.Namespace) -> dict:
    """Compute the P357-019 gate inside the report-emission boundary.

    Callers cannot waive this gate with a fabricated PASS dictionary.  The
    catalog and decision bytes are also included in the ordinary input
    snapshot, so the existing postflight hash comparison detects mutation.
    """
    try:
        from .workspace_source_discovery import validate_report_source_preflight
    except ImportError:
        try:
            from mamey.workspace_source_discovery import validate_report_source_preflight
        except ImportError as exc:
            try:
                from workspace_source_discovery import validate_report_source_preflight
            except ImportError:
                raise ValueError(
                    "P357-019 workspace_source_discovery is required before report emission"
                ) from exc
    required_types = getattr(args, "required_collection_type", None)
    if (
        not isinstance(required_types, list)
        or not required_types
        or any(not isinstance(item, str) or not item for item in required_types)
    ):
        raise ValueError("Report emission requires non-empty required collection types")
    result = validate_report_source_preflight(
        catalog_path=Path(args.source_discovery_catalog),
        expected_catalog_sha256=args.expected_source_discovery_catalog_sha256,
        decisions_path=Path(args.source_discovery_decisions),
        expected_decisions_sha256=args.expected_source_discovery_decisions_sha256,
        strain_key=args.strain,
        required_collection_types=set(required_types),
    )
    if result.get("status") != "PASS_SOURCE_DISCOVERY_AND_DECISIONS_BOUND":
        reason = result.get("reason_code", "UNSPECIFIED_SOURCE_DISCOVERY_FAILURE")
        raise ValueError(f"SOURCE_DISCOVERY_PREFLIGHT_FAILED:{reason}")
    return result


def _source_availability_configuration(args: argparse.Namespace) -> dict | None:
    """Return a complete optional availability configuration or fail closed."""

    names = (
        "source_availability_root",
        "source_availability_root_id",
        "source_collection_registry",
        "expected_source_collection_registry_sha256",
    )
    values = {name: getattr(args, name, None) for name in names}
    if not any(values.values()):
        return None
    missing = sorted(name for name, value in values.items() if not value)
    if missing:
        raise ValueError(f"Incomplete source availability configuration: {', '.join(missing)}")
    return values


def _build_source_availability(
    args: argparse.Namespace, identity_rows: list[dict]
) -> dict | None:
    config = _source_availability_configuration(args)
    if config is None:
        return None
    try:
        from .source_availability import build_source_availability
    except ImportError:
        try:
            from mamey.source_availability import build_source_availability
        except ImportError:
            from source_availability import build_source_availability

    targets = []
    for row in identity_rows:
        region_ids = [value for value in row["source_region_ids"].split(";") if value]
        if not region_ids:
            raise ValueError(
                f"Source availability requires an exact region ordinal for {row['region_key']}"
            )
        for region_id in region_ids:
            targets.append({
                "strain": row["strain"],
                "assembly_sha256": row["assembly_sha256"],
                "node_id": row["node_id"],
                "region": region_id,
                "region_key": row["region_key"],
                "source_scoped_alias": row["aliases"],
            })
    return build_source_availability(
        source_root=Path(config["source_availability_root"]),
        source_root_id=config["source_availability_root_id"],
        source_catalog_path=Path(args.source_discovery_catalog),
        expected_source_catalog_sha256=args.expected_source_discovery_catalog_sha256,
        source_decisions_path=Path(args.source_discovery_decisions),
        expected_source_decisions_sha256=args.expected_source_discovery_decisions_sha256,
        collection_registry_path=Path(config["source_collection_registry"]),
        expected_collection_registry_sha256=config[
            "expected_source_collection_registry_sha256"
        ],
        target_loci=targets,
        binding_tables=getattr(args, "source_availability_binding_table", []) or [],
        required_roles=set(getattr(args, "required_source_role", []) or []) or None,
    )


def _hash_snapshot(paths: Iterable[Path]) -> dict[str, str]:
    snapshot: dict[str, str] = {}
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(path)
        snapshot[str(path.resolve())] = sha256_file(path)
    return snapshot


def read_tsv(path: Path | None) -> list[dict[str, str]]:
    if path is None:
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _one(rows: list[sqlite3.Row], description: str) -> sqlite3.Row:
    if len(rows) != 1:
        raise ValueError(f"Expected exactly one {description}; found {len(rows)}")
    return rows[0]


def resolve_regions(
    connection: sqlite3.Connection,
    strain: str,
    aliases: list[str],
    region_keys: list[str],
) -> list[sqlite3.Row]:
    resolved: list[sqlite3.Row] = []
    for region_key in region_keys:
        resolved.append(_one(connection.execute(
            "SELECT * FROM region_summary WHERE strain=? AND region_key=?", (strain, region_key)
        ).fetchall(), f"region key {region_key!r} for {strain}"))
    for alias in aliases:
        resolved.append(_one(connection.execute(
            """
            SELECT rs.* FROM region_summary rs
            JOIN aliases a ON a.region_key=rs.region_key
            WHERE rs.strain=? AND a.alias_value=?
            """, (strain, alias)
        ).fetchall(), f"alias {alias!r} for {strain}"))
    if not resolved:
        resolved = connection.execute(
            "SELECT * FROM region_summary WHERE strain=? ORDER BY node_id,region_key", (strain,)
        ).fetchall()
    unique: dict[str, sqlite3.Row] = {row["region_key"]: row for row in resolved}
    return list(unique.values())


def _display_path(
    path: Path,
    release: str,
    logical_sources: dict[str, str] | None = None,
) -> str:
    logical_sources = logical_sources or {}
    logical_id = logical_sources.get(str(path.resolve()))
    if logical_id:
        return f"evidence://{logical_id}"
    return path.name if release == "PUBLIC" else str(path)


def _path_visibility(path: Path, release: str, logical_sources: dict[str, str] | None = None) -> str:
    if (logical_sources or {}).get(str(path.resolve())):
        return "LOGICAL_SOURCE_ID"
    return "BASENAME_ONLY" if release == "PUBLIC" else "INTERNAL_PATH"


def load_literature(
    path: Path | None,
    selected_numbers: set[int],
    release: str,
    logical_sources: dict[str, str] | None = None,
) -> tuple[list[dict], dict | None]:
    if path is None:
        return [], None
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    selected = [row for row in records if int(row.get("record_number", 0)) in selected_numbers]
    return selected, {
        "path": _display_path(path, release, logical_sources),
        "path_visibility": _path_visibility(path, release, logical_sources),
        "sha256": sha256_file(path),
        "selected": sorted(selected_numbers),
    }


def _domain_rows(connection: sqlite3.Connection, region_key: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT d.*,g.locus_tag FROM domains d
        LEFT JOIN genes g ON g.gene_key=d.gene_key
        WHERE d.region_key=? ORDER BY d.start_region_record_relative,d.domain_key
        """, (region_key,)
    ).fetchall()


def _gene_rows(connection: sqlite3.Connection, region_key: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT g.*,m.start_region_record_relative,m.end_region_record_relative,
               group_concat(DISTINCT d.label) AS domains
        FROM gene_region_membership m JOIN genes g ON g.gene_key=m.gene_key
        LEFT JOIN domains d ON d.gene_key=g.gene_key AND d.region_key=m.region_key
        WHERE m.region_key=? GROUP BY g.gene_key
        ORDER BY m.start_region_record_relative,m.end_region_record_relative,g.locus_tag
        """, (region_key,)
    ).fetchall()


def _alias_rows(connection: sqlite3.Connection, region_key: str) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT * FROM aliases WHERE region_key=? ORDER BY alias_type,alias_value", (region_key,)
    ).fetchall()


def _call_rows(connection: sqlite3.Connection, region_key: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT rc.*,s.archive_sha256,s.antismash_version,s.embedded_assembly_sha256
        FROM region_calls rc JOIN sources s ON s.source_id=rc.source_id
        WHERE rc.region_key=? ORDER BY rc.profile,rc.region_id
        """, (region_key,)
    ).fetchall()


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return connection.execute(
        "SELECT count(*) FROM sqlite_master WHERE type IN ('table','view') AND name=?", (table,)
    ).fetchone()[0] == 1


def _profile_context(
    connection: sqlite3.Connection,
    strain: str,
    assembly_sha256: str,
    node_id: str,
    selected_calls: list[sqlite3.Row],
) -> dict:
    """Separate archive availability from whether a profile called this locus.

    This prevents a loose-only region call from being misreported as a missing
    relaxed run when the exact same assembly was in fact analyzed in relaxed.
    """
    selected_profiles = sorted({row["profile"] for row in selected_calls})
    if _table_exists(connection, "sources"):
        source_rows = connection.execute(
            """
            SELECT source_id,profile,archive_sha256,antismash_version
            FROM sources WHERE strain=? AND embedded_assembly_sha256=?
            ORDER BY profile,archive_sha256,source_id
            """,
            (strain, assembly_sha256),
        ).fetchall()
        profile_counts = Counter(row["profile"] for row in source_rows)
        ambiguous = sorted(profile for profile, count in profile_counts.items() if count != 1)
        if ambiguous:
            raise ValueError(
                f"Ambiguous exact-assembly profile sources for {strain}: {', '.join(ambiguous)}"
            )
        versions = sorted({row["antismash_version"] for row in source_rows})
        if len(versions) > 1:
            raise ValueError(
                f"Mixed antiSMASH versions on exact assembly for {strain}: {', '.join(versions)}"
            )
        available_profiles = sorted(profile_counts)
    else:
        # Compatibility path for minimal fixtures made before source receipts
        # were required. It cannot claim archive-level availability.
        source_rows = []
        versions = []
        available_profiles = selected_profiles

    node_call_rows = connection.execute(
        """
        SELECT rc.profile,rc.region_id,rc.region_key,r.region_record_start,r.region_record_end,
               r.sequence_sha256,rc.products_json,rc.contig_edge
        FROM region_calls rc JOIN regions r ON r.region_key=rc.region_key
        WHERE r.strain=? AND r.assembly_sha256=? AND r.node_id=?
        ORDER BY rc.profile,r.region_record_start,r.region_record_end,rc.region_key
        """,
        (strain, assembly_sha256, node_id),
    ).fetchall()
    node_called_profiles = sorted({row["profile"] for row in node_call_rows})
    required = {"loose", "relaxed"}
    available_set = set(available_profiles)
    selected_set = set(selected_profiles)
    node_set = set(node_called_profiles)
    missing_archives = sorted(required - available_set)

    if missing_archives:
        state = "MISSING_PROFILE_ARCHIVE_NOT_BIOLOGICAL_ABSENCE"
    elif required.issubset(selected_set):
        state = "EXACT_REGION_PAIR_PRESENT"
    elif required.issubset(node_set):
        state = "EXACT_NODE_PAIR_PRESENT_BOUNDARY_DIFFERENCE"
    elif selected_set == {"loose"} or node_set == {"loose"}:
        state = "LOOSE_ONLY_CALL_EXACT_ASSEMBLY_COUNTERPART_PRESENT"
    elif selected_set == {"relaxed"} or node_set == {"relaxed"}:
        state = "RELAXED_ONLY_CALL_EXACT_ASSEMBLY_COUNTERPART_PRESENT"
    else:
        state = "EXACT_ASSEMBLY_PAIR_PRESENT_CALL_CORRESPONDENCE_UNRESOLVED"
    return {
        "available_profiles": available_profiles,
        "selected_profiles": selected_profiles,
        "node_called_profiles": node_called_profiles,
        "missing_archives": missing_archives,
        "antismash_versions": versions,
        "node_calls": [dict(row) for row in node_call_rows],
        "state": state,
    }


def _profile_delta_rows(
    connection: sqlite3.Connection,
    region_key: str,
    profile_context: dict,
) -> list[dict]:
    out: list[dict] = []
    for profile in ("strict", "relaxed", "loose"):
        archive_present = profile in profile_context["available_profiles"]
        node_calls = [row for row in profile_context["node_calls"] if row["profile"] == profile]
        selected_calls = [row for row in node_calls if row["region_key"] == region_key]
        total_calls = 0
        if archive_present and _table_exists(connection, "sources"):
            total_calls = connection.execute(
                """
                SELECT count(*) FROM region_calls rc JOIN sources s ON s.source_id=rc.source_id
                WHERE s.strain=(SELECT strain FROM regions WHERE region_key=?)
                  AND s.embedded_assembly_sha256=(SELECT assembly_sha256 FROM regions WHERE region_key=?)
                  AND s.profile=?
                """,
                (region_key, region_key, profile),
            ).fetchone()[0]
        call_state = (
            "SELECTED_REGION_CALLED" if selected_calls
            else "NODE_CALLED_DIFFERENT_REGION_KEY" if node_calls
            else "NODE_NOT_CALLED_PROFILE_ARCHIVE_PRESENT" if archive_present
            else "PROFILE_ARCHIVE_NOT_BOUND"
        )
        out.append({
            "region_key": region_key,
            "profile": profile,
            "archive_present": str(archive_present).lower(),
            "total_archive_region_calls": total_calls,
            "node_call_count": len(node_calls),
            "selected_region_call_count": len(selected_calls),
            "call_state": call_state,
            "node_region_keys": ";".join(sorted({row["region_key"] for row in node_calls})),
            "node_region_ids": ";".join(sorted({row["region_id"] for row in node_calls})),
            "node_boundaries": ";".join(
                f"{row['region_record_start']}-{row['region_record_end']}" for row in node_calls
            ),
            "products_json": json.dumps(
                [json.loads(row["products_json"]) for row in node_calls], sort_keys=True
            ),
            "contig_edge_states": ";".join(sorted({row["contig_edge"] for row in node_calls})),
            "claim_effect": "Profile sensitivity only; never biological presence/absence",
        })
    return out


def _blastp_rows(
    all_rows: list[dict[str, str]],
    strain: str,
    node: str,
    genes: Iterable[sqlite3.Row | dict],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Bind BLASTP rows to exact locus-tag + protein-hash + length identity.

    Strain and node select candidates only. They are never sufficient for
    admission because the same node label or BGC ordinal can occur elsewhere.
    """
    exact = {
        str(gene["locus_tag"]): (str(gene["protein_sha256"]), int(gene["aa_length"]))
        for gene in genes
    }
    admitted: list[dict[str, str]] = []
    rejected: list[dict[str, str]] = []
    for row in all_rows:
        if row.get("strain") != strain or row.get("exact_node_id") != node:
            continue
        locus = row.get("gene_id", "")
        if locus not in exact:
            rejected.append({**row, "rejection_reason": "OUTSIDE_EXACT_REGION_LOCUS_SET"})
            continue
        expected_hash, expected_length = exact[locus]
        observed_hash = row.get("current_protein_sha256", "")
        if observed_hash != expected_hash:
            raise ValueError(
                f"BLASTP exact-current protein hash mismatch for {strain}/{node}/{locus}"
            )
        try:
            observed_length = int(row.get("current_aa_length", ""))
        except ValueError as exc:
            raise ValueError(
                f"BLASTP exact-current amino-acid length is invalid for {strain}/{node}/{locus}"
            ) from exc
        if observed_length != expected_length:
            raise ValueError(
                f"BLASTP exact-current amino-acid length mismatch for {strain}/{node}/{locus}"
            )
        admitted.append(row)
    return admitted, rejected


def _channel_summary(
    rows: list[dict[str, str]],
    region_key: str,
    node: str,
    expected_query_count: int,
    expected_channels: Iterable[str],
) -> list[dict]:
    by_channel: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_channel[row.get("channel", "UNKNOWN")].append(row)
    out: list[dict] = []
    channels = sorted(set(by_channel) | set(expected_channels))
    for channel in channels:
        items = by_channel.get(channel, [])
        gene_ids = [item.get("gene_id", "") for item in items]
        duplicate_genes = sorted(gene for gene, count in Counter(gene_ids).items() if gene and count != 1)
        if duplicate_genes:
            raise ValueError(
                f"Duplicate BLASTP reconciliation rows in {channel} for {node}: {', '.join(duplicate_genes)}"
            )
        states = Counter(item.get("gate_state", "UNKNOWN") for item in items)
        sequence_states = Counter(item.get("sequence_binding_state", "UNKNOWN") for item in items)
        explicit_source_states = {
            item.get("channel_source_state", "") for item in items
            if item.get("channel_source_state", "")
        }
        if len(explicit_source_states) > 1:
            raise ValueError(
                f"Mixed BLASTP channel source states in {channel} for {node}: "
                + ", ".join(sorted(explicit_source_states))
            )
        source_state = next(iter(explicit_source_states), "LEGACY_SOURCE_STATE_UNRECORDED")
        sequence_binding_held = any(
            state != "BOUND_EXACT_SUBMITTED_QUERY_SHA256" for state in sequence_states
        )
        represented = len(set(gene_ids) - {""})
        missing = max(expected_query_count - represented, 0)
        if source_state == "MISSING_CHANNEL_SOURCE":
            channel_state = "CHANNEL_SOURCE_MISSING_HOLD"
        elif not items:
            channel_state = "CHANNEL_NOT_CONSUMED"
        elif missing:
            channel_state = "CURRENT_SNAPSHOT_PARTIAL_DENOMINATOR_HOLD"
        elif any(not key.startswith("PASS") for key in states) or sequence_binding_held:
            channel_state = "CURRENT_SNAPSHOT_COMPLETE_DENOMINATOR_WITH_HOLDS"
        else:
            channel_state = "CURRENT_SNAPSHOT_COMPLETE_DENOMINATOR"
        out.append({
            "region_key": region_key,
            "node_id": node,
            "channel": channel,
            "expected_query_count": expected_query_count,
            "query_row_count": len(items),
            "represented_query_count": represented,
            "missing_query_count": missing,
            "pass_row_count": sum(value for key, value in states.items() if key.startswith("PASS")),
            "hold_row_count": sum(value for key, value in states.items() if not key.startswith("PASS")),
            "gate_states_json": json.dumps(states, sort_keys=True),
            "sequence_binding_states_json": json.dumps(sequence_states, sort_keys=True),
            "channel_source_state": source_state,
            "channel_state": channel_state,
        })
    return out


def _project_index(
    paths: Iterable[Path], release: str, logical_sources: dict[str, str] | None = None
) -> list[dict]:
    out: list[dict] = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        identity = payload.get("identity", {}) if isinstance(payload, dict) else {}
        if not identity and isinstance(payload.get("data"), dict):
            identity = payload["data"].get("identity", {}) or {}
        node = (
            identity.get("node_id") or identity.get("node")
            or payload.get("node_id") or payload.get("contig")
        )
        if not node:
            raise ValueError(f"Locus project lacks exact node identity: {path}")
        out.append({
            "path": _display_path(path, release, logical_sources),
            "resolved_path_internal": str(path.resolve()),
            "path_visibility": _path_visibility(path, release, logical_sources),
            "sha256": sha256_file(path),
            "identity": identity,
        })
    return out


def _bind_projects(
    projects: list[dict],
    strain: str,
    assembly_sha256: str,
    node: str,
    calls: Iterable[sqlite3.Row | dict],
) -> list[dict]:
    candidates = [project for project in projects if (project["identity"].get("node") or project["identity"].get("node_id")) == node]
    bound: list[dict] = []
    call_rows = list(calls)
    for project in candidates:
        identity = project["identity"]
        if identity.get("strainId") != strain:
            raise ValueError(f"Locus project strain mismatch for {node}")
        if identity.get("assemblySha256") != assembly_sha256:
            raise ValueError(f"Locus project assembly mismatch for {strain}/{node}")
        profile = identity.get("profile")
        region_id = identity.get("antiSmashRegion")
        region_gbk_sha256 = identity.get("regionGbkSha256")
        archive_sha256 = identity.get("archiveSha256")
        version = identity.get("antiSmashVersion")
        matches = [
            row for row in call_rows
            if row["profile"] == profile
            and row["region_id"] == region_id
            and row["region_gbk_sha256"] == region_gbk_sha256
            and row["archive_sha256"] == archive_sha256
            and row["antismash_version"] == version
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Locus project does not bind exactly one source call for {strain}/{node}: {project['path']}"
            )
        bound.append(project)
    return bound


def build(args: argparse.Namespace) -> dict:
    if args.release == "PUBLIC" and args.strain.startswith(PRIVATE_PREFIXES):
        raise ValueError(f"PUBLIC export refused for private-prefix strain {args.strain}")
    source_preflight = _source_discovery_preflight(args)
    if args.out_root.exists():
        raise FileExistsError(f"Output root already exists: {args.out_root}")
    input_paths = _input_paths(args)
    preflight_hashes = _hash_snapshot(input_paths)
    captured_at_utc, timestamp_state = _captured_at(getattr(args, "captured_at_utc", None))
    logical_sources = getattr(args, "logical_source_by_resolved_path", {})

    connection = sqlite3.connect(args.identity_db)
    connection.row_factory = sqlite3.Row
    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Identity database integrity check failed")
    regions = resolve_regions(connection, args.strain, args.alias, args.region_key)
    if not regions:
        raise ValueError(f"No regions resolved for {args.strain}")
    blastp_all = read_tsv(args.blastp_reconciliation)
    modeb_all = read_tsv(args.modeb_ledger)
    modeb_by_region: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in modeb_all:
        modeb_by_region[row.get("region_key", "")].append(row)
    duplicates = sorted(key for key, rows in modeb_by_region.items() if key and len(rows) != 1)
    if duplicates:
        raise ValueError(f"Mode B ledger has duplicate region keys: {', '.join(duplicates)}")
    literature, literature_source = load_literature(
        args.literature_json, set(args.literature_record_number), args.release, logical_sources
    )
    projects = _project_index(args.locus_project, args.release, logical_sources)

    identity_rows: list[dict] = []
    channel_rows: list[dict] = []
    rejected_blastp_rows: list[dict] = []
    profile_delta_rows: list[dict] = []
    missing_rows: list[dict] = []
    section_rows: list[dict] = []
    used_project_paths: set[str] = set()
    report: list[str] = [
        f"# {args.strain} — refreshable exact-identity BGC evidence report",
        "",
        f"**Release view:** `{args.release}`  ",
        f"**Builder schema:** `{SCHEMA_VERSION}`  ",
        f"**Status:** `DRAFT_CURRENT_SNAPSHOT_WITH_EXPLICIT_HOLDS`",
        "",
        f"> {CLAIM_CEILING}",
        "",
        "## Scope and identity rule",
        "",
        "Protein/CDS hashes plus exact assembly, node and region coordinates are authoritative. "
        "BGC ordinals and historical ranks are source-system aliases only.",
    ]

    for ordinal, region in enumerate(regions, start=1):
        region_key = region["region_key"]
        node = region["node_id"]
        genes = _gene_rows(connection, region_key)
        domains = _domain_rows(connection, region_key)
        aliases = _alias_rows(connection, region_key)
        calls = _call_rows(connection, region_key)
        profile_context = _profile_context(
            connection, args.strain, region["assembly_sha256"], node, calls
        )
        locus_profile_rows = _profile_delta_rows(connection, region_key, profile_context)
        profile_delta_rows.extend(locus_profile_rows)
        blastp, rejected_blastp = _blastp_rows(blastp_all, args.strain, node, genes)
        for rejected in rejected_blastp:
            rejected_blastp_rows.append({"region_key": region_key, "node_id": node, **rejected})
        summaries = _channel_summary(
            blastp, region_key, node, len(genes), args.expected_blastp_channel
        )
        modeb_rows = modeb_by_region.get(region_key, [])
        channel_rows.extend(summaries)
        alias_text = ", ".join(f"{row['alias_value']} [{row['alias_state']}]" for row in aliases) or "none"
        source_region_ids = sorted({row["region_id"] for row in calls})
        user_locator = f"{node} / {','.join(source_region_ids) or 'REGION_ID_UNRESOLVED'}"
        profile_set = profile_context["selected_profiles"]
        project_refs = _bind_projects(projects, args.strain, region["assembly_sha256"], node, calls)
        used_project_paths.update(item["resolved_path_internal"] for item in project_refs)

        identity_rows.append({
            "region_key": region_key,
            "strain": args.strain,
            "assembly_sha256": region["assembly_sha256"],
            "node_id": node,
            "sequence_sha256": connection.execute("SELECT sequence_sha256 FROM regions WHERE region_key=?", (region_key,)).fetchone()[0],
            "coordinate_frame": connection.execute("SELECT coordinate_frame FROM regions WHERE region_key=?", (region_key,)).fetchone()[0],
            "profiles": ";".join(profile_set),
            "assembly_profiles_available": ";".join(profile_context["available_profiles"]),
            "node_called_profiles": ";".join(profile_context["node_called_profiles"]),
            "antismash_versions": ";".join(profile_context["antismash_versions"]),
            "profile_comparison_state": profile_context["state"],
            "source_region_ids": ";".join(source_region_ids),
            "user_locator": user_locator,
            "gene_count": len(genes),
            "domain_count": len(domains),
            "aliases": alias_text,
            "identity_state": "EXACT_SEQUENCE_COORDINATE_BOUND",
        })

        report.extend([
            "",
            f"## Locus {ordinal}: `{user_locator}`",
            "",
            f"- Exact region key: `{region_key}`",
            f"- Assembly SHA-256: `{region['assembly_sha256']}`",
            f"- Exact-assembly profile archives available: `{', '.join(profile_context['available_profiles']) or 'none'}`",
            f"- Profiles that called this exact node: `{', '.join(profile_context['node_called_profiles']) or 'none'}`",
            f"- Profiles bound to this exact region key: `{', '.join(profile_set) or 'none'}`",
            f"- Source region IDs: `{', '.join(source_region_ids) or 'none'}`",
            f"- Historical/source aliases: {alias_text}",
            f"- CDS/domain counts: **{len(genes)} / {len(domains)}**",
            "",
            "### Loose–relaxed status",
            "",
        ])
        profile_state = profile_context["state"]
        report.append(f"Profile comparison state: `{profile_state}`")
        report.append("")
        if profile_state == "EXACT_REGION_PAIR_PRESENT":
            report.append("Loose and relaxed both call this exact sequence-and-coordinate region key.")
        elif profile_state == "EXACT_NODE_PAIR_PRESENT_BOUNDARY_DIFFERENCE":
            report.append(
                "Loose and relaxed both call this exact node, but not as the same region key. "
                "Boundary/merge/split correspondence must be computed before interpreting the delta."
            )
        elif profile_state == "LOOSE_ONLY_CALL_EXACT_ASSEMBLY_COUNTERPART_PRESENT":
            report.append(
                "Both exact-assembly profile archives are present, but this node is called only in loose. "
                "This is a profile-sensitivity delta, not biological absence."
            )
        elif profile_state == "RELAXED_ONLY_CALL_EXACT_ASSEMBLY_COUNTERPART_PRESENT":
            report.append(
                "Both exact-assembly profile archives are present, but this node is called only in relaxed. "
                "This requires correspondence review and is not biological absence."
            )
        elif profile_context["missing_archives"]:
            missing = profile_context["missing_archives"]
            report.append(
                f"Only `{', '.join(profile_context['available_profiles']) or 'no'}` exact-assembly archive profile evidence is present. Missing archive profile(s): "
                f"`{', '.join(missing)}`. This is a run/input gap, not biological absence."
            )
            missing_rows.append({
                "region_key": region_key, "evidence_type": "ANTISMASH_PROFILE",
                "request": f"Bind exact-assembly {'/'.join(missing)} counterpart(s)",
                "state": profile_state, "claim_effect": "No loose-relaxed absence inference",
            })
        else:
            report.append(
                "Both exact-assembly archives are available, but call correspondence remains unresolved. "
                "No profile-specific interpretation is admitted."
            )

        report.extend([
            "",
            "| Profile | Archive region count | Node calls | Exact-region calls | Call state |",
            "|---|---:|---:|---:|---|",
        ])
        for delta in locus_profile_rows:
            report.append(
                f"| `{delta['profile']}` | {delta['total_archive_region_calls']} | "
                f"{delta['node_call_count']} | {delta['selected_region_call_count']} | "
                f"`{delta['call_state']}` |"
            )

        report.extend(["", "### Exact gene and domain architecture", "", "| Gene | Coordinates | Strand | aa | Protein SHA-256 | Domains | Functions |", "|---|---:|:---:|---:|---|---|---|"])
        for gene in genes:
            functions = (gene["gene_functions"] or gene["product"] or "unclassified / no exact function admitted").replace("|", "/")
            report.append(
                f"| `{gene['locus_tag']}` | {gene['start_region_record_relative']}–{gene['end_region_record_relative']} | "
                f"{gene['strand']} | {gene['aa_length']} | `{gene['protein_sha256']}` | "
                f"{(gene['domains'] or '—').replace('|','/')} | {functions} |"
            )
        if project_refs:
            report.extend(["", "Locus/widget projects bound to this node:"])
            report.extend(f"- `{item['path']}` — SHA-256 `{item['sha256']}`" for item in project_refs)
        else:
            missing_rows.append({
                "region_key": region_key, "evidence_type": "LOCUS_WIDGET",
                "request": "Provide exact-node locus/domain project JSON", "state": "NOT_CONSUMED",
                "claim_effect": "No claim that displayed map matches this exact locus",
            })

        report.extend(["", "### Mode B current interpretation and evidence delta", ""])
        if modeb_rows:
            modeb = modeb_rows[0]
            report.extend([
                f"- Identity binding: `{modeb.get('identity_binding_state', 'UNKNOWN')}`",
                f"- Update disposition: `{modeb.get('update_disposition', 'UNKNOWN')}`",
                f"- Current family/component hypothesis: {modeb.get('current_family_capacity_hypothesis', 'not supplied')}",
                f"- Changed evidence: {modeb.get('changed_evidence', 'not supplied')}",
                f"- Leading alternatives: {modeb.get('leading_alternatives', 'not supplied')}",
                f"- Holds: {modeb.get('holds', 'not supplied')}",
                f"- Ceiling: {modeb.get('claim_ceiling', CLAIM_CEILING)}",
            ])
            modeb_state = "CURRENT_MODE_B_DELTA_BOUND"
        else:
            report.append("No exact-region Mode B current/delta row was supplied; interpretation remains unrefreshed.")
            modeb_state = "MODE_B_DELTA_NOT_CONSUMED"
            missing_rows.append({
                "region_key": region_key,
                "evidence_type": "MODE_B_CURRENT_DELTA",
                "request": "Provide one exact-region Mode B current/delta ledger row",
                "state": modeb_state,
                "claim_effect": "Report may show extraction evidence but no refreshed Mode B interpretation",
            })

        report.extend(["", "### BLASTP evidence by channel", ""])
        if summaries:
            report.extend(["| Channel | Expected | Represented | Missing | PASS | HOLD | State |", "|---|---:|---:|---:|---:|---:|---|"])
            for summary in summaries:
                report.append(
                    f"| `{summary['channel']}` | {summary['expected_query_count']} | "
                    f"{summary['represented_query_count']} | {summary['missing_query_count']} | "
                    f"{summary['pass_row_count']} | "
                    f"{summary['hold_row_count']} | `{summary['channel_state']}` |"
                )
                if summary["channel_state"] in {"CHANNEL_NOT_CONSUMED", "CHANNEL_SOURCE_MISSING_HOLD"}:
                    missing_rows.append({
                        "region_key": region_key,
                        "evidence_type": "BLASTP_CHANNEL",
                        "request": f"Provide exact-query reconciliation for {summary['channel']}",
                        "state": summary["channel_state"],
                        "claim_effect": "Channel-specific evidence unavailable; not a biological negative",
                    })
            if any("UNBOUND" in row.get("sequence_binding_state", "") for row in blastp):
                missing_rows.append({
                    "region_key": region_key, "evidence_type": "BLASTP_QUERY_RECEIPT",
                    "request": "Recover submitted query FASTA/per-query hashes for every consumed result channel",
                    "state": "HOLD_SUBMISSION_RECEIPT_MISSING",
                    "claim_effect": "Similarity rows remain sequence-unbound overlays",
                })
            if rejected_blastp:
                report.append(
                    f"\n{len(rejected_blastp)} candidate BLASTP row(s) were quarantined outside the exact locus denominator."
                )
        else:
            report.append("No BLASTP reconciliation rows were consumed for this exact node.")
            missing_rows.append({
                "region_key": region_key, "evidence_type": "BLASTP_CHANNELS",
                "request": "Provide channel-separated exact-query reconciliation",
                "state": "CHANNEL_NOT_CONSUMED", "claim_effect": "No BLASTP interpretation",
            })

        section_inputs = [sha256_file(args.identity_db)]
        if args.blastp_reconciliation:
            section_inputs.append(sha256_file(args.blastp_reconciliation))
        if args.modeb_ledger:
            section_inputs.append(sha256_file(args.modeb_ledger))
        section_rows.extend([
            {
                "section_key": f"{region_key}:identity_architecture", "region_key": region_key,
                "currentness_state": "CURRENT_SNAPSHOT_BOUND", "input_sha256s_json": json.dumps(section_inputs),
                "identity_gate": "PASS_EXACT_SEQUENCE_COORDINATE_BOUND",
                "staleness_trigger": "assembly/node/region/gene/domain source hash changes",
                "claim_ceiling": CLAIM_CEILING,
            },
            {
                "section_key": f"{region_key}:profile_comparison", "region_key": region_key,
                "currentness_state": profile_state, "input_sha256s_json": json.dumps(section_inputs),
                "identity_gate": "PASS_CURRENT_ARCHIVE_ONLY",
                "staleness_trigger": "new exact profile archive admitted",
                "claim_ceiling": CLAIM_CEILING,
            },
            {
                "section_key": f"{region_key}:blastp", "region_key": region_key,
                "currentness_state": "CURRENT_SNAPSHOT_BOUND_WITH_HOLDS" if summaries else "CHANNEL_NOT_CONSUMED",
                "input_sha256s_json": json.dumps(section_inputs),
                "identity_gate": "QUERY_RECEIPT_HOLD" if blastp else "NOT_ASSESSED",
                "staleness_trigger": "new BLASTP receipt or reconciliation hash",
                "claim_ceiling": CLAIM_CEILING,
            },
            {
                "section_key": f"{region_key}:mode_b_delta", "region_key": region_key,
                "currentness_state": modeb_state, "input_sha256s_json": json.dumps(section_inputs),
                "identity_gate": "PASS_EXACT_REGION_ROW" if modeb_rows else "NOT_ASSESSED",
                "staleness_trigger": "identity, BLASTP, profile comparison, comparator or Mode B ledger hash changes",
                "claim_ceiling": CLAIM_CEILING,
            },
        ])

    unused_projects = sorted(
        project["resolved_path_internal"] for project in projects
        if project["resolved_path_internal"] not in used_project_paths
    )
    if unused_projects:
        raise ValueError(f"Locus project does not target a selected exact region: {', '.join(unused_projects)}")

    report.extend(["", "## Literature evidence", ""])
    if literature:
        report.append(
            "The records below were explicitly selected by record number. Selection is a routing decision, not proof that the paper's pathway occurs in these loci."
        )
        report.extend(["", "| Record | Class | Citation | Evidence scope |", "|---:|---|---|---|"])
        for row in literature:
            citation = f"{row.get('title','')} (PMID {row.get('pmid','—')}; DOI {row.get('doi','—')})".replace("|", "/")
            report.append(f"| {row.get('record_number')} | `{row.get('record_class')}` | {citation} | {row.get('evidence_scope','')} |")
        lit_state = "EXPLICIT_ROUTING_CANDIDATES_NOT_BGC_ADMITTED"
    else:
        report.append("No literature record was explicitly selected for these exact loci.")
        lit_state = "LITERATURE_NOT_CONSUMED"
    section_rows.append({
        "section_key": "report:literature", "region_key": "REPORT",
        "currentness_state": lit_state,
        "input_sha256s_json": json.dumps([literature_source["sha256"]] if literature_source else []),
        "identity_gate": "REQUIRES_LOCUS_ASSERTION_LEDGER",
        "staleness_trigger": "literature ledger or assertion mapping changes", "claim_ceiling": CLAIM_CEILING,
    })
    report.extend([
        "", "## Required next evidence", "",
        "The machine-readable missing-evidence table is the governing request queue. Missing evidence is never interpreted as biological absence.",
        "", "## Claim boundary", "", CLAIM_CEILING, "",
    ])

    availability_result = _build_source_availability(args, identity_rows)
    report_text = "\n".join(report)
    postflight_hashes = _hash_snapshot(input_paths)
    if postflight_hashes != preflight_hashes:
        drifted = sorted(
            path for path in set(preflight_hashes) | set(postflight_hashes)
            if preflight_hashes.get(path) != postflight_hashes.get(path)
        )
        raise ValueError(f"Input source drift before publication: {', '.join(drifted)}")
    # All input parsing and identity/provenance gates above complete before any
    # output path is created. A later tranche will add staging+atomic publish.
    availability_receipt = None
    if availability_result is not None:
        try:
            from .source_availability import write_source_availability
        except ImportError:
            try:
                from mamey.source_availability import write_source_availability
            except ImportError:
                from source_availability import write_source_availability
        availability_receipt = write_source_availability(availability_result, args.out_root)
    else:
        args.out_root.mkdir(parents=True, exist_ok=False)
    report_path = args.out_root / f"{args.strain}_refreshable_bgc_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    identity_path = args.out_root / "exact_identity_ledger.tsv"
    write_tsv(identity_path, identity_rows, [
        "region_key", "strain", "assembly_sha256", "node_id", "user_locator", "sequence_sha256", "coordinate_frame",
        "profiles", "assembly_profiles_available", "node_called_profiles", "antismash_versions",
        "profile_comparison_state", "source_region_ids", "gene_count", "domain_count", "aliases", "identity_state",
    ])
    channels_path = args.out_root / "blastp_channel_summary.tsv"
    write_tsv(channels_path, channel_rows, [
        "region_key", "node_id", "channel", "expected_query_count", "query_row_count",
        "represented_query_count", "missing_query_count", "pass_row_count", "hold_row_count",
        "gate_states_json", "sequence_binding_states_json", "channel_source_state", "channel_state",
    ])
    profile_delta_path = args.out_root / "profile_call_comparison.tsv"
    write_tsv(profile_delta_path, profile_delta_rows, [
        "region_key", "profile", "archive_present", "total_archive_region_calls", "node_call_count",
        "selected_region_call_count", "call_state", "node_region_keys", "node_region_ids",
        "node_boundaries", "products_json", "contig_edge_states", "claim_effect",
    ])
    rejected_blastp_path = args.out_root / "blastp_rejected_rows.tsv"
    write_tsv(rejected_blastp_path, rejected_blastp_rows, [
        "region_key", "node_id", "strain", "source_system_alias", "exact_node_id", "channel",
        "gene_id", "current_aa_length", "current_protein_sha256", "observed_positive_aa_lengths",
        "source_row_count", "gate_state", "reason", "sequence_binding_state", "rejection_reason",
    ])
    missing_path = args.out_root / "missing_evidence_requests.tsv"
    write_tsv(missing_path, missing_rows, ["region_key", "evidence_type", "request", "state", "claim_effect"])
    sections_path = args.out_root / "section_evidence_snapshot_ledger.tsv"
    write_tsv(sections_path, section_rows, [
        "section_key", "region_key", "currentness_state", "input_sha256s_json", "identity_gate",
        "staleness_trigger", "claim_ceiling",
    ])
    connection.close()

    portable_receipt_path = None
    portable_receipt = getattr(args, "portable_resolution_receipt", None)
    if portable_receipt is not None:
        portable_receipt_path = args.out_root / "portable_source_resolution_receipt.json"
        portable_receipt_path.write_text(
            json.dumps(portable_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )

    input_manifest = {
        "identity_db": {
            "path": _display_path(args.identity_db, args.release, logical_sources),
            "path_visibility": _path_visibility(args.identity_db, args.release, logical_sources),
            "sha256": sha256_file(args.identity_db),
        },
        "blastp_reconciliation": ({
            "path": _display_path(args.blastp_reconciliation, args.release, logical_sources),
            "path_visibility": _path_visibility(args.blastp_reconciliation, args.release, logical_sources),
            "sha256": sha256_file(args.blastp_reconciliation),
        } if args.blastp_reconciliation else None),
        "modeb_ledger": ({
            "path": _display_path(args.modeb_ledger, args.release, logical_sources),
            "path_visibility": _path_visibility(args.modeb_ledger, args.release, logical_sources),
            "sha256": sha256_file(args.modeb_ledger),
        } if args.modeb_ledger else None),
        "literature": literature_source,
        "locus_projects": [
            {key: value for key, value in item.items() if key not in {"resolved_path_internal", "identity"}}
            for item in projects
        ],
        "expected_blastp_channels": sorted(set(args.expected_blastp_channel)),
    }
    outputs = [
        report_path, identity_path, channels_path, profile_delta_path, rejected_blastp_path,
        missing_path, sections_path,
    ]
    if portable_receipt_path is not None:
        outputs.append(portable_receipt_path)
    if availability_receipt is not None:
        outputs.extend(
            args.out_root / name for name in (
                "SOURCE_FILE_CATALOG.tsv",
                "STRAIN_AVAILABILITY.tsv",
                "LOCUS_AVAILABILITY.tsv",
                "WORK_ROUTING.tsv",
                "source_availability_receipt.json",
            )
        )
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "status": "DRAFT_BUILT_NOT_ACCEPTED_NOT_INTEGRATED",
        "captured_at_utc": captured_at_utc,
        "timestamp_state": timestamp_state,
        "strain": args.strain,
        "release": args.release,
        "region_keys": [row["region_key"] for row in identity_rows],
        "inputs": input_manifest,
        "source_snapshot_gate": {
            "state": "PASS_PREFLIGHT_POSTFLIGHT_HASH_MATCH",
            "artifact_count": len(preflight_hashes),
            "sha256_by_source": {
                (
                    f"evidence://{logical_sources[path]}" if path in logical_sources
                    else path if args.release == "INTERNAL"
                    else Path(path).name
                ): digest
                for path, digest in preflight_hashes.items()
            },
        },
        "source_discovery_preflight_receipt": source_preflight,
        "source_availability_preflight_receipt": availability_receipt,
        "outputs": [{"path": path.name, "sha256": sha256_file(path), "bytes": path.stat().st_size} for path in outputs],
        "claim_ceiling": CLAIM_CEILING,
        "holds": sorted({row["state"] for row in missing_rows}),
    }
    manifest_path = args.out_root / "report_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--identity-db", type=Path, required=True)
    parser.add_argument("--strain", required=True)
    parser.add_argument("--alias", action="append", default=[])
    parser.add_argument("--region-key", action="append", default=[])
    parser.add_argument("--blastp-reconciliation", type=Path)
    parser.add_argument("--expected-blastp-channel", action="append", default=[])
    parser.add_argument("--modeb-ledger", type=Path)
    parser.add_argument("--literature-json", type=Path)
    parser.add_argument("--literature-record-number", action="append", type=int, default=[])
    parser.add_argument("--locus-project", action="append", type=Path, default=[])
    parser.add_argument("--release", choices=["INTERNAL", "PUBLIC"], default="INTERNAL")
    parser.add_argument("--captured-at-utc", help="Fixed ISO-8601 timestamp for byte-reproducible manifests")
    parser.add_argument("--source-discovery-catalog", type=Path, required=True)
    parser.add_argument("--expected-source-discovery-catalog-sha256", required=True)
    parser.add_argument("--source-discovery-decisions", type=Path, required=True)
    parser.add_argument("--expected-source-discovery-decisions-sha256", required=True)
    parser.add_argument("--required-collection-type", action="append", required=True)
    parser.add_argument("--source-availability-root", type=Path)
    parser.add_argument("--source-availability-root-id")
    parser.add_argument("--source-collection-registry", type=Path)
    parser.add_argument("--expected-source-collection-registry-sha256")
    parser.add_argument("--source-availability-binding-table", type=Path, action="append", default=[])
    parser.add_argument("--required-source-role", action="append", default=[])
    parser.add_argument("--out-root", type=Path, required=True)
    args = parser.parse_args()
    # AUDIT_374: build() writes report.md/TSVs/manifest.json sequentially straight into
    # args.out_root with no staging — a crash partway through (disk full, kill, permission error)
    # leaves a partial, manifest-less directory on disk, and the FileExistsError guard at the top
    # of build() then blocks any retry into the same target. report_from_spec.py already avoids
    # this by building into a uuid-suffixed staging sibling and os.replace()-ing it into place only
    # on success; mirror that same pattern here so main()'s direct/CLI call path gets the identical
    # protection, not just the report_from_spec.py-mediated one.
    final_out_root = args.out_root
    if final_out_root.exists():
        raise FileExistsError(f"Output root already exists: {final_out_root}")
    staging_root = final_out_root.with_name(f".{final_out_root.name}.staging-{uuid.uuid4().hex}")
    args.out_root = staging_root
    try:
        manifest = build(args)
        os.replace(staging_root, final_out_root)
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise
    emit(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
