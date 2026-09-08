"""Build logical, exact-locus source-availability tables for report routing.

The availability layer consumes a complete P357-019 discovery catalog plus
explicit collection decisions.  It inventories files only inside collections
selected with ``CONSUME`` and never copies source bytes.  A file is exact-locus
available only when a hash-bound binding row supplies strain, assembly SHA-256,
full node/contig, region ordinal, and region key.  Filename/path matches are
retained as navigation holds and never promoted to exact identity.

All emitted paths are logical ``evidence://`` locators.  Missing source roles
are typed workflow gaps, not biological absence.
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
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable


SCHEMA_VERSION = "sapote-source-availability-v1"
DEFAULT_REQUIRED_ROLES = {
    "ANTISMASH_REGION",
    "LOCUS_MAP",
    "MODE_B_CARD",
    "BLASTP_RECONCILIATION",
}
ALLOWED_DECISIONS = {"CONSUME", "REJECT_WITH_REASON", "SUPERSEDED_WITH_RECEIPT"}
MATERIAL_SUFFIXES = {
    ".csv", ".tsv", ".json", ".md", ".txt", ".xml", ".gbk", ".gbff",
    ".html", ".svg", ".png", ".pdf", ".docx", ".xlsx", ".sqlite", ".db",
    ".nwk", ".tree", ".newick", ".faa", ".fasta", ".zip",
}
REGION_RE = re.compile(r"^region\d{3}$", flags=re.I)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class AvailabilityLimits:
    max_files: int = 200_000
    max_apparent_bytes: int = 50_000_000_000
    max_collection_depth: int = 12


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_tsv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = list(reader.fieldnames or [])
        return fields, [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
        ]


def _write_tsv(path: Path, fields: list[str], rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(
            handle, fieldnames=fields, delimiter="\t", lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _safe_relative(value: str) -> str:
    relative = PurePosixPath(value)
    if relative.is_absolute() or ".." in relative.parts or value in {"", "."}:
        if value == ".":
            return "."
        raise ValueError(f"unsafe collection/file relative path: {value!r}")
    return relative.as_posix()


def _logical_path(root_id: str, relative: str) -> str:
    suffix = "" if relative == "." else f"/{relative}"
    return f"evidence://{root_id}{suffix}"


def _locus_key(row: dict[str, str]) -> str:
    material = "\n".join(
        row[key] for key in (
            "strain", "assembly_sha256", "node_id", "region", "region_key"
        )
    )
    return f"LOCUS_{hashlib.sha256(material.encode('utf-8')).hexdigest()[:20]}"


def _validate_locus(row: dict[str, str], *, where: str) -> dict[str, str]:
    required = {"strain", "assembly_sha256", "node_id", "region", "region_key"}
    missing = sorted(key for key in required if not row.get(key))
    if missing:
        raise ValueError(f"{where} missing exact locus fields: {missing}")
    assembly = row["assembly_sha256"].lower()
    if not SHA256_RE.fullmatch(assembly):
        raise ValueError(f"{where} assembly_sha256 must be 64 lowercase hex characters")
    if not REGION_RE.fullmatch(row["region"]):
        raise ValueError(f"{where} region must use regionNNN form")
    if "/" in row["node_id"] or len(row["node_id"]) < 3:
        raise ValueError(f"{where} node_id is not a full node/contig locator")
    if "/" in row["region_key"]:
        raise ValueError(f"{where} region_key is invalid")
    normalized = dict(row)
    normalized["assembly_sha256"] = assembly
    normalized["region"] = row["region"].lower()
    normalized["locus_key"] = _locus_key(normalized)
    normalized.setdefault("source_scoped_alias", "")
    return normalized


def read_target_loci(path: Path) -> list[dict[str, str]]:
    fields, rows = _read_tsv(path)
    required = {"strain", "assembly_sha256", "node_id", "region", "region_key"}
    if required - set(fields):
        raise ValueError(f"target locus table missing columns: {sorted(required - set(fields))}")
    out = [_validate_locus(row, where=f"target locus row {index}") for index, row in enumerate(rows, 2)]
    keys = [row["locus_key"] for row in out]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate exact locus in target locus table")
    if not out:
        raise ValueError("target locus table is empty")
    return out


def _load_collection_registry(path: Path, expected_sha256: str) -> tuple[dict, str]:
    observed = sha256_file(path)
    if observed != expected_sha256:
        raise ValueError("collection registry SHA-256 mismatch")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "sapote-source-collection-registry-v1":
        raise ValueError("unsupported collection registry schema")
    roles = payload.get("availability_roles")
    if not isinstance(roles, list) or not roles:
        raise ValueError("collection registry requires non-empty availability_roles")
    seen = set()
    for role in roles:
        required = {"source_role", "collection_types", "path_regex"}
        if required - set(role):
            raise ValueError(f"availability role missing fields: {sorted(required - set(role))}")
        if role["source_role"] in seen:
            raise ValueError(f"duplicate availability source_role: {role['source_role']}")
        if not isinstance(role["collection_types"], list) or not role["collection_types"]:
            raise ValueError("availability role collection_types must be non-empty")
        re.compile(role["path_regex"], flags=re.I)
        seen.add(role["source_role"])
    return payload, observed


def _load_catalog_and_decisions(
    *,
    catalog_path: Path,
    expected_catalog_sha256: str,
    decisions_path: Path,
    expected_decisions_sha256: str,
    root_id: str,
) -> tuple[dict, dict[str, dict[str, str]], str, str]:
    catalog_sha = sha256_file(catalog_path)
    decisions_sha = sha256_file(decisions_path)
    if catalog_sha != expected_catalog_sha256:
        raise ValueError("STALE_OR_UNBOUND_CATALOG")
    if decisions_sha != expected_decisions_sha256:
        raise ValueError("STALE_OR_UNBOUND_DECISIONS")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if catalog.get("schema_version") != "sapote-source-discovery-catalog-v1":
        raise ValueError("unsupported source discovery catalog schema")
    if catalog.get("status") != "PASS_COMPLETE":
        raise ValueError("DISCOVERY_CATALOG_NOT_COMPLETE")
    if catalog.get("root_id") != root_id:
        raise ValueError("SOURCE_CATALOG_ROOT_ID_MISMATCH")
    fields, decision_rows = _read_tsv(decisions_path)
    required = {"collection_id", "decision", "reason", "evidence_receipt"}
    if required - set(fields):
        raise ValueError("decision table missing required columns")
    decisions: dict[str, dict[str, str]] = {}
    for row in decision_rows:
        cid = row["collection_id"]
        if not cid or cid in decisions:
            raise ValueError("blank or duplicate collection_id in decisions")
        if row["decision"] not in ALLOWED_DECISIONS:
            raise ValueError(f"invalid collection decision for {cid}")
        if row["decision"] != "CONSUME" and not row["reason"]:
            raise ValueError(f"non-consume decision requires reason for {cid}")
        if row["decision"] == "SUPERSEDED_WITH_RECEIPT" and not row["evidence_receipt"]:
            raise ValueError(f"supersession requires receipt for {cid}")
        decisions[cid] = row
    missing = sorted(
        row["collection_id"] for row in catalog.get("collections", [])
        if row["collection_id"] not in decisions
    )
    if missing:
        raise ValueError(f"MATERIAL_COLLECTION_DECISION_MISSING:{','.join(missing)}")
    return catalog, decisions, catalog_sha, decisions_sha


def _load_bindings(
    paths: Iterable[Path], *, root_id: str, loci_by_key: dict[str, dict[str, str]]
) -> tuple[dict[str, list[dict[str, str]]], list[dict]]:
    by_relative: dict[str, list[dict[str, str]]] = defaultdict(list)
    receipts: list[dict] = []
    required = {
        "root_id", "relative_path", "strain", "assembly_sha256", "node_id",
        "region", "region_key", "source_role",
    }
    for path in paths:
        fields, rows = _read_tsv(path)
        if required - set(fields):
            raise ValueError(f"binding table missing columns: {sorted(required - set(fields))}")
        seen: set[tuple[str, str]] = set()
        for index, row in enumerate(rows, 2):
            if row["root_id"] != root_id:
                raise ValueError(f"binding row {index} root_id mismatch")
            relative = _safe_relative(row["relative_path"])
            locus = _validate_locus(row, where=f"binding row {index}")
            if locus["locus_key"] not in loci_by_key:
                raise ValueError(f"binding row {index} targets an unrequested exact locus")
            key = (relative, row["source_role"])
            if key in seen:
                raise ValueError(f"duplicate binding for {relative}/{row['source_role']}")
            seen.add(key)
            locus["relative_path"] = relative
            locus["source_role"] = row["source_role"]
            by_relative[relative].append(locus)
        receipts.append({
            "logical_path": f"binding://{path.name}",
            "sha256": sha256_file(path),
            "row_count": len(rows),
        })
    return by_relative, receipts


def _role_for_path(relative: str, collection_type: str, roles: list[dict]) -> str:
    matches = [
        role["source_role"] for role in roles
        if collection_type in role["collection_types"]
        and re.search(role["path_regex"], relative, flags=re.I)
    ]
    if len(matches) > 1:
        return "AMBIGUOUS_SOURCE_ROLE_HOLD"
    return matches[0] if matches else "UNCLASSIFIED_SOURCE_FILE"


def _path_locator_matches(relative: str, loci: list[dict[str, str]]) -> tuple[list[str], list[str]]:
    exact_node_region = []
    strain_only = []
    folded = relative.casefold()
    for locus in loci:
        if locus["strain"].casefold() in folded:
            strain_only.append(locus["locus_key"])
        if locus["node_id"].casefold() in folded and locus["region"].casefold() in folded:
            exact_node_region.append(locus["locus_key"])
    return sorted(set(exact_node_region)), sorted(set(strain_only))


def build_source_availability(
    *,
    source_root: Path,
    source_root_id: str,
    source_catalog_path: Path,
    expected_source_catalog_sha256: str,
    source_decisions_path: Path,
    expected_source_decisions_sha256: str,
    collection_registry_path: Path,
    expected_collection_registry_sha256: str,
    target_loci: list[dict[str, str]],
    binding_tables: Iterable[Path] = (),
    required_roles: set[str] | None = None,
    limits: AvailabilityLimits = AvailabilityLimits(),
) -> dict:
    """Inventory consumed files and derive typed strain/locus routing tables."""

    source_root = source_root.resolve(strict=True)
    registry, collection_registry_sha = _load_collection_registry(
        collection_registry_path, expected_collection_registry_sha256
    )
    catalog, decisions, catalog_sha, decisions_sha = _load_catalog_and_decisions(
        catalog_path=source_catalog_path,
        expected_catalog_sha256=expected_source_catalog_sha256,
        decisions_path=source_decisions_path,
        expected_decisions_sha256=expected_source_decisions_sha256,
        root_id=source_root_id,
    )
    normalized_loci = [
        row if row.get("locus_key") else _validate_locus(row, where="target locus")
        for row in target_loci
    ]
    loci_by_key = {row["locus_key"]: row for row in normalized_loci}
    if len(loci_by_key) != len(normalized_loci):
        raise ValueError("duplicate exact target locus")
    bindings, binding_receipts = _load_bindings(
        binding_tables, root_id=source_root_id, loci_by_key=loci_by_key
    )
    roles = registry["availability_roles"]
    registered_roles = {row["source_role"] for row in roles}
    required = set(required_roles or DEFAULT_REQUIRED_ROLES)
    unknown_required = sorted(required - registered_roles)
    if unknown_required:
        raise ValueError(f"required source role absent from registry: {unknown_required}")

    source_rows: list[dict] = []
    source_snapshot: dict[str, str] = {}
    seen_relative: set[str] = set()
    files_seen = 0
    bytes_seen = 0
    for collection in catalog.get("collections", []):
        decision = decisions[collection["collection_id"]]["decision"]
        if decision != "CONSUME":
            continue
        collection_relative = _safe_relative(collection["relative_path"])
        directory = source_root if collection_relative == "." else source_root / collection_relative
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"CONSUMED_COLLECTION_PATH_MISSING:{collection['collection_id']}")
        for dirpath, dirnames, filenames in os.walk(directory):
            current = Path(dirpath)
            depth = len(current.relative_to(directory).parts)
            dirnames[:] = sorted(
                name for name in dirnames
                if name not in {".git", "__pycache__", "node_modules"}
            )
            if depth > limits.max_collection_depth:
                raise ValueError("SOURCE_AVAILABILITY_DEPTH_LIMIT")
            for name in sorted(filenames):
                path = current / name
                if path.is_symlink():
                    raise ValueError(f"SOURCE_SYMLINK_HOLD:{path.name}")
                relative = path.relative_to(source_root).as_posix()
                if relative in seen_relative:
                    continue
                seen_relative.add(relative)
                size = path.stat().st_size
                files_seen += 1
                bytes_seen += size
                if files_seen > limits.max_files:
                    raise ValueError("SOURCE_AVAILABILITY_FILE_LIMIT")
                if bytes_seen > limits.max_apparent_bytes:
                    raise ValueError("SOURCE_AVAILABILITY_BYTE_LIMIT")
                if path.suffix.lower() not in MATERIAL_SUFFIXES:
                    continue
                source_role = _role_for_path(relative, collection["collection_type"], roles)
                digest = sha256_file(path)
                logical = _logical_path(source_root_id, relative)
                exact_bindings = [
                    row for row in bindings.get(relative, [])
                    if row["source_role"] == source_role
                ]
                node_region_matches, strain_matches = _path_locator_matches(relative, normalized_loci)
                if exact_bindings:
                    locator_state = "EXACT_LOCATOR_BINDING_TABLE"
                    matched = sorted(row["locus_key"] for row in exact_bindings)
                    typed_state = "PRESENT_EXACT_LOCATOR_HASH_BOUND"
                elif node_region_matches:
                    locator_state = "PATH_FULL_NODE_REGION_ASSEMBLY_UNBOUND"
                    matched = node_region_matches
                    typed_state = "PRESENT_NODE_REGION_PATH_ASSEMBLY_UNBOUND_HOLD"
                elif strain_matches:
                    locator_state = "PATH_STRAIN_ONLY"
                    matched = strain_matches
                    typed_state = "PRESENT_STRAIN_ONLY_NOT_LOCUS_BOUND"
                else:
                    locator_state = "NO_LOCUS_BINDING"
                    matched = []
                    typed_state = "PRESENT_COLLECTION_ONLY_NOT_LOCUS_BOUND"
                source_file_id = f"SRC_{hashlib.sha256(logical.encode('utf-8')).hexdigest()[:20]}"
                source_rows.append({
                    "source_file_id": source_file_id,
                    "root_id": source_root_id,
                    "collection_id": collection["collection_id"],
                    "collection_type": collection["collection_type"],
                    "source_role": source_role,
                    "logical_path": logical,
                    "sha256": digest,
                    "bytes": size,
                    "collection_decision": decision,
                    "root_status": "DISCOVERY_AND_DECISION_BOUND_REFERENCE_ONLY",
                    "root_authority": "NOT_ESTABLISHED_BY_AVAILABILITY_LAYER",
                    "locator_binding_state": locator_state,
                    "matched_locus_keys": ";".join(matched),
                    "typed_availability_state": typed_state,
                    "_relative_path": relative,
                })
                source_snapshot[relative] = digest
    source_rows.sort(key=lambda row: (row["source_role"], row["logical_path"]))

    all_roles = sorted(registered_roles | required)
    locus_rows: list[dict] = []
    for locus in sorted(normalized_loci, key=lambda row: (row["strain"], row["node_id"], row["region"])):
        for role in all_roles:
            role_rows = [row for row in source_rows if row["source_role"] == role]
            exact = [row for row in role_rows if locus["locus_key"] in row["matched_locus_keys"].split(";") and row["locator_binding_state"] == "EXACT_LOCATOR_BINDING_TABLE"]
            path_only = [row for row in role_rows if locus["locus_key"] in row["matched_locus_keys"].split(";") and row["locator_binding_state"] == "PATH_FULL_NODE_REGION_ASSEMBLY_UNBOUND"]
            strain_only = [row for row in role_rows if locus["locus_key"] in row["matched_locus_keys"].split(";") and row["locator_binding_state"] == "PATH_STRAIN_ONLY"]
            if exact:
                state = "PRESENT_EXACT_LOCATOR_HASH_BOUND"
                selected = exact
            elif path_only:
                state = "PRESENT_NODE_REGION_PATH_ASSEMBLY_UNBOUND_HOLD"
                selected = path_only
            elif strain_only:
                state = "PRESENT_STRAIN_ONLY_NOT_LOCUS_BOUND"
                selected = strain_only
            elif role_rows:
                state = "SOURCE_ROLE_PRESENT_OTHER_OR_UNBOUND"
                selected = []
            else:
                state = "MISSING_SOURCE_ROLE_NOT_BIOLOGICAL_ABSENCE"
                selected = []
            locus_rows.append({
                "locus_key": locus["locus_key"],
                "strain": locus["strain"],
                "assembly_sha256": locus["assembly_sha256"],
                "node_id": locus["node_id"],
                "region": locus["region"],
                "region_key": locus["region_key"],
                "source_scoped_alias": locus.get("source_scoped_alias", ""),
                "source_role": role,
                "availability_state": state,
                "exact_file_count": len(exact),
                "matched_source_file_ids": ";".join(row["source_file_id"] for row in selected),
                "matched_logical_paths": ";".join(row["logical_path"] for row in selected),
                "claim_effect": "ROUTING_ONLY_NOT_BIOLOGICAL_ABSENCE_OR_FUNCTIONAL_CLAIM",
            })

    strain_rows: list[dict] = []
    for strain in sorted({row["strain"] for row in normalized_loci}):
        locus_keys = {row["locus_key"] for row in normalized_loci if row["strain"] == strain}
        for role in all_roles:
            role_locus = [row for row in locus_rows if row["strain"] == strain and row["source_role"] == role]
            exact_keys = {row["locus_key"] for row in role_locus if row["availability_state"] == "PRESENT_EXACT_LOCATOR_HASH_BOUND"}
            if exact_keys == locus_keys:
                state = "PRESENT_ALL_TARGET_LOCI_EXACT"
            elif exact_keys:
                state = "PRESENT_SOME_TARGET_LOCI_EXACT"
            elif any("PRESENT_" in row["availability_state"] or "SOURCE_ROLE_PRESENT" in row["availability_state"] for row in role_locus):
                state = "PRESENT_NOT_EXACT_LOCUS_BOUND"
            else:
                state = "MISSING_SOURCE_ROLE_NOT_BIOLOGICAL_ABSENCE"
            strain_rows.append({
                "strain": strain,
                "source_role": role,
                "target_locus_count": len(locus_keys),
                "exact_locus_count": len(exact_keys),
                "availability_state": state,
                "claim_effect": "WORKFLOW_COVERAGE_ONLY_NOT_BIOLOGICAL_ABSENCE",
            })

    routing_rows: list[dict] = []
    for locus in sorted(normalized_loci, key=lambda row: (row["strain"], row["node_id"], row["region"])):
        relevant = [
            row for row in locus_rows
            if row["locus_key"] == locus["locus_key"] and row["source_role"] in required
        ]
        exact_roles = sorted(row["source_role"] for row in relevant if row["availability_state"] == "PRESENT_EXACT_LOCATOR_HASH_BOUND")
        held_roles = sorted(row["source_role"] for row in relevant if row["availability_state"] not in {"PRESENT_EXACT_LOCATOR_HASH_BOUND", "MISSING_SOURCE_ROLE_NOT_BIOLOGICAL_ABSENCE"})
        missing_roles = sorted(row["source_role"] for row in relevant if row["availability_state"] == "MISSING_SOURCE_ROLE_NOT_BIOLOGICAL_ABSENCE")
        if set(exact_roles) == required:
            route = "READY_COMBINED_DRAFT_SOURCE_BOUND"
        elif exact_roles:
            route = "READY_PRELIMINARY_WITH_TYPED_SOURCE_HOLDS"
        else:
            route = "SKELETON_ONLY_SOURCE_BINDINGS_REQUIRED"
        routing_rows.append({
            "locus_key": locus["locus_key"],
            "strain": locus["strain"],
            "assembly_sha256": locus["assembly_sha256"],
            "node_id": locus["node_id"],
            "region": locus["region"],
            "region_key": locus["region_key"],
            "source_scoped_alias": locus.get("source_scoped_alias", ""),
            "required_roles": ";".join(sorted(required)),
            "exact_roles": ";".join(exact_roles),
            "held_roles": ";".join(held_roles),
            "missing_roles": ";".join(missing_roles),
            "work_route": route,
            "claim_state": "ROUTING_ONLY_NO_BIOLOGICAL_OR_PUBLICATION_PROMOTION",
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "PASS_AVAILABILITY_ROUTING_NOT_SCIENTIFIC_ACCEPTANCE",
        "root_id": source_root_id,
        "source_boundary": {
            "state": "DISCOVERY_AND_DECISIONS_BOUND_REFERENCE_ONLY",
            "authority": "NOT_ESTABLISHED_BY_AVAILABILITY_LAYER",
            "note": "P357-017 source admission remains an independent cut-time gate.",
        },
        "input_hashes": {
            "source_catalog": catalog_sha,
            "source_decisions": decisions_sha,
            "collection_registry": collection_registry_sha,
            "binding_tables": binding_receipts,
        },
        "scan_counts": {
            "files_seen": files_seen,
            "apparent_bytes_seen": bytes_seen,
            "material_file_count": len(source_rows),
            "target_locus_count": len(normalized_loci),
        },
        "required_roles": sorted(required),
        "source_file_rows": source_rows,
        "strain_rows": strain_rows,
        "locus_rows": locus_rows,
        "routing_rows": routing_rows,
        "_source_root": str(source_root),
        "_source_snapshot": source_snapshot,
    }


def verify_source_snapshot(result: dict) -> None:
    root = Path(result["_source_root"])
    for relative, expected in result["_source_snapshot"].items():
        path = root / relative
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"SOURCE_DRIFT_BEFORE_AVAILABILITY_PUBLICATION:{relative}")


def write_source_availability(result: dict, out_root: Path) -> dict:
    if out_root.exists():
        raise FileExistsError(f"output root already exists: {out_root}")
    verify_source_snapshot(result)
    out_root.mkdir(parents=True)
    files = {
        "SOURCE_FILE_CATALOG.tsv": (
            [
                "source_file_id", "root_id", "collection_id", "collection_type", "source_role",
                "logical_path", "sha256", "bytes", "collection_decision", "root_status",
                "root_authority", "locator_binding_state", "matched_locus_keys",
                "typed_availability_state",
            ], result["source_file_rows"]
        ),
        "STRAIN_AVAILABILITY.tsv": (
            ["strain", "source_role", "target_locus_count", "exact_locus_count", "availability_state", "claim_effect"],
            result["strain_rows"],
        ),
        "LOCUS_AVAILABILITY.tsv": (
            [
                "locus_key", "strain", "assembly_sha256", "node_id", "region", "region_key",
                "source_scoped_alias", "source_role", "availability_state", "exact_file_count",
                "matched_source_file_ids", "matched_logical_paths", "claim_effect",
            ], result["locus_rows"]
        ),
        "WORK_ROUTING.tsv": (
            [
                "locus_key", "strain", "assembly_sha256", "node_id", "region", "region_key",
                "source_scoped_alias", "required_roles", "exact_roles", "held_roles",
                "missing_roles", "work_route", "claim_state",
            ], result["routing_rows"]
        ),
    }
    outputs = []
    for name, (fields, rows) in files.items():
        path = out_root / name
        _write_tsv(path, fields, rows)
        outputs.append({"path": name, "sha256": sha256_file(path), "bytes": path.stat().st_size})
    receipt = {
        key: value for key, value in result.items()
        if key not in {"source_file_rows", "strain_rows", "locus_rows", "routing_rows", "_source_root", "_source_snapshot"}
    }
    receipt["outputs"] = outputs
    receipt["source_files_copied"] = 0
    receipt["source_bytes_copied"] = 0
    receipt["scientific_acceptance"] = "NOT_ASSESSED"
    receipt["release_approval"] = "NOT_ASSESSED"
    receipt_path = out_root / "source_availability_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--source-root-id", required=True)
    parser.add_argument("--source-catalog", type=Path, required=True)
    parser.add_argument("--expected-source-catalog-sha256", required=True)
    parser.add_argument("--source-decisions", type=Path, required=True)
    parser.add_argument("--expected-source-decisions-sha256", required=True)
    parser.add_argument("--collection-registry", type=Path, required=True)
    parser.add_argument("--expected-collection-registry-sha256", required=True)
    parser.add_argument("--target-loci", type=Path, required=True)
    parser.add_argument("--binding-table", type=Path, action="append", default=[])
    parser.add_argument("--required-role", action="append", default=[])
    parser.add_argument("--max-files", type=int, default=200_000)
    parser.add_argument("--max-apparent-bytes", type=int, default=50_000_000_000)
    parser.add_argument("--max-collection-depth", type=int, default=12)
    parser.add_argument("--out-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build_source_availability(
        source_root=args.source_root,
        source_root_id=args.source_root_id,
        source_catalog_path=args.source_catalog,
        expected_source_catalog_sha256=args.expected_source_catalog_sha256,
        source_decisions_path=args.source_decisions,
        expected_source_decisions_sha256=args.expected_source_decisions_sha256,
        collection_registry_path=args.collection_registry,
        expected_collection_registry_sha256=args.expected_collection_registry_sha256,
        target_loci=read_target_loci(args.target_loci),
        binding_tables=args.binding_table,
        required_roles=set(args.required_role) if args.required_role else None,
        limits=AvailabilityLimits(
            args.max_files, args.max_apparent_bytes, args.max_collection_depth
        ),
    )
    receipt = write_source_availability(result, args.out_root)
    emit(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
