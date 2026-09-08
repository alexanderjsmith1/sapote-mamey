#!/usr/bin/env python3
"""Portable logical-source resolution for refreshable report builds."""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Mapping


CONFIG_SCHEMA = "sapote_evidence_root_config_v1"
MANIFEST_SCHEMA = "sapote_portable_source_manifest_v1"
ROOT_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
SOURCE_DISCOVERY_PASS = "PASS_SOURCE_DISCOVERY_AND_DECISIONS_BOUND"


class EvidenceRootError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EvidenceRootError(f"Expected JSON object: {path}")
    return payload


def _safe_relative(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value:
        raise EvidenceRootError(f"Unsafe portable relative path: {value!r}")
    return path


def logical_locator(root_id: str, relative_path: str) -> str:
    """Return a host-path-free locator owned by the configured evidence-root contract."""
    if not ROOT_RE.fullmatch(root_id):
        raise EvidenceRootError(f"Invalid root ID: {root_id!r}")
    relative = _safe_relative(relative_path)
    suffix = relative.as_posix()
    return f"evidence://{root_id}" if suffix == "." else f"evidence://{root_id}/{suffix}"


def resolve_roots(
    config: dict,
    config_path: Path,
    cli_roots: Mapping[str, str] | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Path]:
    if config.get("schema_version") != CONFIG_SCHEMA or not isinstance(config.get("roots"), dict):
        raise EvidenceRootError("Invalid evidence-root configuration")
    cli_roots = cli_roots or {}
    environ = os.environ if environ is None else environ
    unknown = sorted(set(cli_roots) - set(config["roots"]))
    if unknown:
        raise EvidenceRootError(f"CLI overrides undeclared roots: {unknown}")
    roots: dict[str, Path] = {}
    for root_id, item in config["roots"].items():
        if not ROOT_RE.fullmatch(root_id):
            raise EvidenceRootError(f"Invalid root ID: {root_id!r}")
        configured = item.get("path") if isinstance(item, dict) else item
        if not isinstance(configured, str):
            raise EvidenceRootError(f"Root {root_id!r} lacks a path")
        env_key = f"SAPOTE_EVIDENCE_ROOT_{root_id.upper()}"
        if root_id in cli_roots:
            raw, explicit = cli_roots[root_id], True
        elif env_key in environ:
            raw, explicit = environ[env_key], True
        else:
            raw, explicit = configured, False
        candidate = Path(raw)
        if explicit and not candidate.is_absolute():
            raise EvidenceRootError(f"Override for {root_id!r} must be absolute")
        if not candidate.is_absolute():
            candidate = config_path.parent / candidate
        roots[root_id] = candidate.resolve()
    return roots


def resolve_sources(
    manifest: dict,
    roots: Mapping[str, Path],
    release: str,
) -> tuple[dict[str, Path], dict]:
    if manifest.get("schema_version") != MANIFEST_SCHEMA or not isinstance(manifest.get("sources"), list):
        raise EvidenceRootError("Invalid portable source manifest")
    resolved: dict[str, Path] = {}
    receipt_rows: list[dict] = []
    seen: set[str] = set()
    for row in sorted(manifest["sources"], key=lambda item: item.get("logical_source_id", "")):
        logical_id = row.get("logical_source_id")
        if not isinstance(logical_id, str) or not logical_id or logical_id in seen:
            raise EvidenceRootError(f"Missing or duplicate logical source ID: {logical_id!r}")
        seen.add(logical_id)
        root_id = row.get("root_id")
        required = bool(row.get("required", True))
        if root_id not in roots:
            if required:
                raise EvidenceRootError(f"Required root is unbound: {root_id!r}")
            receipt_rows.append({**row, "state": "CHANNEL_NOT_CONSUMED"})
            continue
        relative = _safe_relative(str(row.get("relative_path", "")))
        root = roots[root_id]
        path = (root / Path(*relative.parts)).resolve()
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise EvidenceRootError(f"Resolved source escapes root: {logical_id}") from exc
        if not path.is_file():
            if required:
                raise EvidenceRootError(f"Required source is missing: {logical_id}")
            receipt_rows.append({**row, "state": "CHANNEL_NOT_CONSUMED"})
            continue
        observed_hash = sha256_file(path)
        observed_bytes = path.stat().st_size
        if observed_hash != row.get("sha256"):
            raise EvidenceRootError(f"Source hash mismatch: {logical_id}")
        if row.get("bytes") is not None and observed_bytes != row["bytes"]:
            raise EvidenceRootError(f"Source byte-count mismatch: {logical_id}")
        if release == "PUBLIC" and row.get("release_class") != "PUBLIC":
            raise EvidenceRootError(f"PUBLIC build cannot consume internal source {logical_id}")
        resolved[logical_id] = path
        receipt_rows.append({**row, "state": "RESOLVED_HASH_VERIFIED"})
    return resolved, {
        "schema_version": "sapote_portable_resolution_receipt_v1",
        "status": "PASS_PREFLIGHT",
        "sources": receipt_rows,
    }


def resolve_output(roots: Mapping[str, Path], root_id: str, relative_path: str) -> Path:
    if root_id not in roots:
        raise EvidenceRootError(f"Output root is unbound: {root_id!r}")
    relative = _safe_relative(relative_path)
    root = roots[root_id]
    output = (root / Path(*relative.parts)).resolve()
    try:
        output.relative_to(root)
    except ValueError as exc:
        raise EvidenceRootError("Output path escapes configured root") from exc
    return output


def require_source_discovery_preflight(
    *,
    source_manifest: dict,
    resolved_sources: Mapping[str, Path],
    spec: dict,
    strain_keys: list[str],
) -> dict:
    """Require P357-019 discovery/decision PASS before any report write.

    The catalog and decision table are ordinary content-addressed sources in the
    portable manifest.  This function derives their expected hashes from that
    manifest instead of trusting caller-supplied path metadata.
    """
    policy = spec.get("source_discovery_preflight")
    if not isinstance(policy, dict):
        raise EvidenceRootError("Build spec lacks required source_discovery_preflight")
    catalog_id = policy.get("catalog_source_id")
    decisions_id = policy.get("decisions_source_id")
    required_types = policy.get("required_collection_types")
    if not isinstance(catalog_id, str) or not catalog_id:
        raise EvidenceRootError("source_discovery_preflight lacks catalog_source_id")
    if not isinstance(decisions_id, str) or not decisions_id:
        raise EvidenceRootError("source_discovery_preflight lacks decisions_source_id")
    if (
        not isinstance(required_types, list)
        or not required_types
        or any(not isinstance(item, str) or not item for item in required_types)
    ):
        raise EvidenceRootError(
            "source_discovery_preflight.required_collection_types must be a non-empty string array"
        )
    if not strain_keys or any(not isinstance(item, str) or not item for item in strain_keys):
        raise EvidenceRootError("source discovery preflight requires explicit strain keys")

    rows = {
        row.get("logical_source_id"): row
        for row in source_manifest.get("sources", [])
        if isinstance(row, dict)
    }
    for logical_id in (catalog_id, decisions_id):
        if logical_id not in rows or logical_id not in resolved_sources:
            raise EvidenceRootError(
                f"Required source-discovery input did not resolve: {logical_id}"
            )
        expected = rows[logical_id].get("sha256")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise EvidenceRootError(
                f"Source-discovery input lacks a valid manifest SHA-256: {logical_id}"
            )

    try:
        from .workspace_source_discovery import validate_report_source_preflight
    except ImportError:
        try:
            from workspace_source_discovery import validate_report_source_preflight
        except ImportError as exc:
            raise EvidenceRootError(
                "P357-019 workspace_source_discovery is required before report emission"
            ) from exc

    results = []
    for strain in sorted(set(strain_keys)):
        try:
            result = validate_report_source_preflight(
                catalog_path=resolved_sources[catalog_id],
                expected_catalog_sha256=rows[catalog_id]["sha256"],
                decisions_path=resolved_sources[decisions_id],
                expected_decisions_sha256=rows[decisions_id]["sha256"],
                strain_key=strain,
                required_collection_types=set(required_types),
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise EvidenceRootError(
                f"SOURCE_DISCOVERY_PREFLIGHT_INVALID:{strain}:{exc}"
            ) from exc
        if result.get("status") != SOURCE_DISCOVERY_PASS:
            reason = result.get("reason_code", "UNSPECIFIED_SOURCE_DISCOVERY_FAILURE")
            raise EvidenceRootError(f"SOURCE_DISCOVERY_PREFLIGHT_FAILED:{strain}:{reason}")
        results.append(result)
    return {
        "schema_version": "sapote_report_source_preflight_receipt_v1",
        "status": SOURCE_DISCOVERY_PASS,
        "catalog_source_id": catalog_id,
        "catalog_sha256": rows[catalog_id]["sha256"],
        "decisions_source_id": decisions_id,
        "decisions_sha256": rows[decisions_id]["sha256"],
        "required_collection_types": sorted(set(required_types)),
        "strain_results": results,
        "scientific_acceptance": "NOT_ASSESSED",
        "release_approval": "NOT_ASSESSED",
    }
