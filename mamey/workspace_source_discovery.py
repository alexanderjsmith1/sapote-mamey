"""Bounded workspace source discovery and report-preflight gate.

This module discovers evidence collections; it does not admit them as current
evidence.  A downstream report must bind the catalog bytes and record an
explicit consume/reject/supersession decision for every material collection
that can contain the requested strain.
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
import time
from dataclasses import asdict, dataclass
from pathlib import Path


ALLOWED_DECISIONS = {"CONSUME", "REJECT_WITH_REASON", "SUPERSEDED_WITH_RECEIPT"}
NOISE_DIRECTORIES = {".git", "__pycache__", "node_modules", ".DS_Store"}
MATERIAL_SUFFIXES = {".csv", ".tsv", ".json", ".md", ".docx", ".pdf", ".xlsx", ".html", ".svg", ".gbk", ".sqlite"}
MAX_COVERAGE_SOURCE_BYTES = 8_000_000


@dataclass(frozen=True)
class ScanLimits:
    max_depth: int = 6
    max_files: int = 100_000
    max_apparent_bytes: int = 20_000_000_000
    max_seconds: float = 60.0


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_collection_registry(path: Path) -> tuple[dict, str]:
    payload = _load_json(path)
    if payload.get("schema_version") != "sapote-source-collection-registry-v1":
        raise ValueError("unsupported collection registry schema")
    rules = payload.get("rules")
    if not isinstance(rules, list) or not rules:
        raise ValueError("collection registry requires non-empty rules")
    seen = set()
    for rule in rules:
        required = {"collection_type", "directory_regex", "material_file_regex"}
        missing = required - set(rule)
        if missing:
            raise ValueError(f"collection rule missing fields: {sorted(missing)}")
        if rule["collection_type"] in seen:
            raise ValueError(f"duplicate collection_type: {rule['collection_type']}")
        re.compile(rule["directory_regex"])
        re.compile(rule["material_file_regex"])
        if rule.get("root_segment_regex"):
            re.compile(rule["root_segment_regex"])
        if rule.get("strain_regex"):
            re.compile(rule["strain_regex"])
        coverage_parser = rule.get("coverage_parser", "NONE")
        if coverage_parser not in {"NONE", "DELIMITED_COLUMN"}:
            raise ValueError(f"unsupported coverage_parser: {coverage_parser}")
        if coverage_parser == "DELIMITED_COLUMN" and not rule.get("coverage_column"):
            raise ValueError("DELIMITED_COLUMN requires coverage_column")
        seen.add(rule["collection_type"])
    return payload, sha256_file(path)


def _collection_id(collection_type: str, relative_path: str) -> str:
    digest = hashlib.sha256(f"{collection_type}\n{relative_path}".encode("utf-8")).hexdigest()
    return f"COLL_{digest[:20]}"


def _match_rule(relative_dir: str, filenames: list[str], rules: list[dict]) -> dict | None:
    for rule in rules:
        if not re.search(rule["directory_regex"], relative_dir, flags=re.I):
            continue
        file_pattern = re.compile(rule["material_file_regex"], flags=re.I)
        if any(file_pattern.search(name) for name in filenames):
            return rule
    return None


def _collection_anchor(relative_dir: str, rule: dict) -> str:
    """Collapse nested evidence folders to the registered collection root."""

    segment_regex = rule.get("root_segment_regex")
    if not segment_regex:
        return relative_dir
    pattern = re.compile(segment_regex, flags=re.I)
    parts = relative_dir.split("/")
    for index, part in enumerate(parts):
        if pattern.fullmatch(part):
            return "/".join(parts[: index + 1])
    return relative_dir


def _extract_strains(relative_dir: str, filenames: list[str], strain_regex: str) -> list[str]:
    if not strain_regex:
        return []
    pattern = re.compile(strain_regex, flags=re.I)
    found = set()
    for value in [relative_dir, *filenames]:
        for match in pattern.finditer(value):
            found.add(match.group(0).upper().replace("_", "-"))
    return sorted(found)


def _extract_strains_from_registered_content(
    directory: Path,
    filenames: list[str],
    rule: dict,
    strain_regex: str,
) -> tuple[list[str], str]:
    """Extract bounded strain coverage only when a registry rule names the parser."""

    if rule.get("coverage_parser", "NONE") != "DELIMITED_COLUMN":
        return [], "NOT_REQUESTED"
    column = rule["coverage_column"]
    file_pattern = re.compile(rule["material_file_regex"], flags=re.I)
    strain_pattern = re.compile(strain_regex, flags=re.I) if strain_regex else None
    found = set()
    parsed_files = 0
    for name in filenames:
        if not file_pattern.search(name):
            continue
        path = directory / name
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_COVERAGE_SOURCE_BYTES:
            return sorted(found), "HOLD_COVERAGE_SOURCE_TOO_LARGE"
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, delimiter=delimiter)
                if column not in (reader.fieldnames or []):
                    return sorted(found), "HOLD_COVERAGE_COLUMN_MISSING"
                for row in reader:
                    value = (row.get(column) or "").strip()
                    if not value:
                        continue
                    if strain_pattern:
                        match = strain_pattern.fullmatch(value)
                        if not match:
                            continue
                        value = match.group(0)
                    found.add(value.upper().replace("_", "-"))
            parsed_files += 1
        except (OSError, UnicodeError, csv.Error):
            return sorted(found), "HOLD_COVERAGE_PARSE_ERROR"
    return sorted(found), ("PARSED_REGISTERED_CONTENT" if parsed_files else "HOLD_COVERAGE_SOURCE_NOT_FOUND")


def build_source_catalog(
    *,
    root: Path,
    root_id: str,
    collection_registry_path: Path,
    expected_collection_registry_sha256: str,
    limits: ScanLimits = ScanLimits(),
) -> dict:
    """Metadata-first census.  No collection becomes authoritative here."""

    root = root.resolve(strict=True)
    registry, registry_sha256 = load_collection_registry(collection_registry_path)
    if registry_sha256 != expected_collection_registry_sha256:
        raise ValueError("collection registry SHA-256 mismatch")
    rules = registry["rules"]
    started = time.monotonic()
    root_depth = len(root.parts)
    files_seen = 0
    directories_seen = 0
    apparent_bytes = 0
    pruned_depth = 0
    collection_rows: dict[tuple[str, str], dict] = {}
    truncation_reason = ""

    for dirpath, dirnames, filenames in os.walk(root):
        directory = Path(dirpath)
        depth = len(directory.parts) - root_depth
        dirnames[:] = sorted(name for name in dirnames if name not in NOISE_DIRECTORIES)
        filenames = sorted(name for name in filenames if name != ".DS_Store")
        if depth > limits.max_depth:
            pruned_depth += 1
            dirnames[:] = []
            continue
        directories_seen += 1
        if time.monotonic() - started > limits.max_seconds:
            truncation_reason = "TRUNCATED_TIME_LIMIT"
            break
        local_files = []
        local_bytes = 0
        for name in filenames:
            path = directory / name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            files_seen += 1
            apparent_bytes += size
            local_files.append(name)
            local_bytes += size
            if files_seen > limits.max_files:
                truncation_reason = "TRUNCATED_FILE_LIMIT"
                break
            if apparent_bytes > limits.max_apparent_bytes:
                truncation_reason = "TRUNCATED_BYTE_LIMIT"
                break
        if truncation_reason:
            break
        relative = directory.relative_to(root).as_posix() or "."
        rule = _match_rule(relative, local_files, rules)
        material = any(Path(name).suffix.lower() in MATERIAL_SUFFIXES for name in local_files)
        if rule or (material and depth <= registry.get("unclassified_max_depth", 2)):
            collection_type = rule["collection_type"] if rule else "UNCLASSIFIED_MATERIAL"
            collection_relative = _collection_anchor(relative, rule) if rule else relative
            strain_regex = rule.get("strain_regex", registry.get("default_strain_regex", "")) if rule else registry.get("default_strain_regex", "")
            strains = _extract_strains(relative, local_files, strain_regex)
            coverage_state = "PATH_AND_FILENAME_ONLY"
            if rule:
                content_strains, coverage_state = _extract_strains_from_registered_content(
                    directory, local_files, rule, strain_regex
                )
                strains = sorted(set(strains) | set(content_strains))
            key = (collection_type, collection_relative)
            if key not in collection_rows:
                collection_rows[key] = {
                    "collection_id": _collection_id(collection_type, collection_relative),
                    "collection_type": collection_type,
                    "relative_path": collection_relative,
                    "file_count_at_directory": 0,
                    "apparent_bytes_at_directory": 0,
                    "strain_keys_observed": strains,
                    "strain_count": len(strains),
                    "coverage_extraction_state": coverage_state,
                    "classification_state": "REGISTERED_SIGNATURE" if rule else "UNCLASSIFIED_MATERIAL_REVIEW_REQUIRED",
                    "authority_state": "DISCOVERED_NOT_ADMITTED",
                    "generation_state": "UNRESOLVED",
                }
            row = collection_rows[key]
            row["file_count_at_directory"] += len(local_files)
            row["apparent_bytes_at_directory"] += local_bytes
            row["strain_keys_observed"] = sorted(set(row["strain_keys_observed"]) | set(strains))
            row["strain_count"] = len(row["strain_keys_observed"])
            if row["coverage_extraction_state"] != coverage_state:
                row["coverage_extraction_state"] = ";".join(
                    sorted(set(row["coverage_extraction_state"].split(";")) | {coverage_state})
                )

    status = "PASS_COMPLETE" if not truncation_reason and pruned_depth == 0 else (truncation_reason or "TRUNCATED_DEPTH_LIMIT")
    collections = list(collection_rows.values())
    collections.sort(key=lambda row: (row["collection_type"], row["relative_path"]))
    return {
        "schema_version": "sapote-source-discovery-catalog-v1",
        "status": status,
        "root_id": root_id,
        "root_display": f"evidence://{root_id}",
        "collection_registry_sha256": registry_sha256,
        "scan_limits": asdict(limits),
        "scan_counts": {
            "directories_seen": directories_seen,
            "files_seen": files_seen,
            "apparent_bytes_seen": apparent_bytes,
            "depth_pruned_directory_count": pruned_depth,
            "collection_count": len(collections),
        },
        "collections": collections,
        "non_claims": [
            "Discovery does not confer source authority or current-evidence admission.",
            "Discovery does not establish product identity, production, activity, novelty, physical linkage, release, or publication readiness.",
        ],
    }


def write_catalog(catalog: dict, json_path: Path, tsv_path: Path) -> dict:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    fields = [
        "collection_id", "collection_type", "relative_path", "file_count_at_directory",
        "apparent_bytes_at_directory", "strain_keys_observed", "strain_count",
        "coverage_extraction_state", "classification_state", "authority_state", "generation_state",
    ]
    with tsv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in catalog["collections"]:
            out = dict(row)
            out["strain_keys_observed"] = ";".join(out["strain_keys_observed"])
            writer.writerow(out)
    return {
        "catalog_json_sha256": sha256_file(json_path),
        "catalog_tsv_sha256": sha256_file(tsv_path),
        "status": catalog["status"],
        "collection_count": len(catalog["collections"]),
    }


def _load_decisions(path: Path) -> dict[str, dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"collection_id", "decision", "reason", "evidence_receipt"}
        if required - set(reader.fieldnames or []):
            raise ValueError("decision table missing required columns")
        rows = {}
        for row in reader:
            cid = row["collection_id"].strip()
            if not cid or cid in rows:
                raise ValueError("blank or duplicate collection_id in decisions")
            row = {key: (value or "").strip() for key, value in row.items()}
            if row["decision"] not in ALLOWED_DECISIONS:
                raise ValueError(f"invalid decision for {cid}")
            if row["decision"] != "CONSUME" and not row["reason"]:
                raise ValueError(f"non-consume decision requires reason for {cid}")
            if row["decision"] == "SUPERSEDED_WITH_RECEIPT" and not row["evidence_receipt"]:
                raise ValueError(f"supersession requires receipt for {cid}")
            rows[cid] = row
    return rows


def validate_report_source_preflight(
    *,
    catalog_path: Path,
    expected_catalog_sha256: str,
    decisions_path: Path,
    expected_decisions_sha256: str,
    strain_key: str,
    required_collection_types: set[str],
) -> dict:
    if sha256_file(catalog_path) != expected_catalog_sha256:
        return {"status": "FAIL", "reason_code": "STALE_OR_UNBOUND_CATALOG"}
    if sha256_file(decisions_path) != expected_decisions_sha256:
        return {"status": "FAIL", "reason_code": "STALE_OR_UNBOUND_DECISIONS"}
    catalog = _load_json(catalog_path)
    if catalog.get("status") != "PASS_COMPLETE":
        return {"status": "FAIL", "reason_code": "DISCOVERY_CATALOG_NOT_COMPLETE"}
    decisions = _load_decisions(decisions_path)
    relevant = []
    for row in catalog.get("collections", []):
        strains = set(row.get("strain_keys_observed") or [])
        if not strains or strain_key.upper() in strains:
            relevant.append(row)
    missing_decisions = [row["collection_id"] for row in relevant if row["collection_id"] not in decisions]
    if missing_decisions:
        return {
            "status": "FAIL",
            "reason_code": "MATERIAL_COLLECTION_DECISION_MISSING",
            "missing_collection_ids": missing_decisions,
        }
    consumed_types = {
        row["collection_type"] for row in relevant
        if decisions[row["collection_id"]]["decision"] == "CONSUME"
    }
    for collection_type in required_collection_types:
        same_type = [row for row in relevant if row["collection_type"] == collection_type]
        if len(same_type) <= 1:
            continue
        consumed = [row for row in same_type if decisions[row["collection_id"]]["decision"] == "CONSUME"]
        unresolved = [
            row["collection_id"] for row in same_type
            if decisions[row["collection_id"]]["decision"] not in {"CONSUME", "SUPERSEDED_WITH_RECEIPT"}
        ]
        if len(consumed) != 1 or unresolved:
            return {
                "status": "FAIL",
                "reason_code": "PARALLEL_GENERATION_UNRESOLVED",
                "collection_type": collection_type,
                "unresolved_collection_ids": unresolved,
            }
    missing_required = sorted(required_collection_types - consumed_types)
    if missing_required:
        return {
            "status": "FAIL",
            "reason_code": "REQUIRED_COLLECTION_TYPE_NOT_CONSUMED",
            "missing_collection_types": missing_required,
        }
    return {
        "status": "PASS_SOURCE_DISCOVERY_AND_DECISIONS_BOUND",
        "reason_code": "ALL_MATERIAL_COLLECTIONS_DISPOSITIONED",
        "catalog_sha256": expected_catalog_sha256,
        "decisions_sha256": expected_decisions_sha256,
        "strain_key": strain_key,
        "relevant_collection_count": len(relevant),
        "consumed_collection_types": sorted(consumed_types),
        "scientific_acceptance": "NOT_ASSESSED",
        "release_approval": "NOT_ASSESSED",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("root", type=Path)
    scan.add_argument("--root-id", required=True)
    scan.add_argument("--collection-registry", type=Path, required=True)
    scan.add_argument("--expected-collection-registry-sha256", required=True)
    scan.add_argument("--out-json", type=Path, required=True)
    scan.add_argument("--out-tsv", type=Path, required=True)
    scan.add_argument("--max-depth", type=int, default=6)
    scan.add_argument("--max-files", type=int, default=100_000)
    scan.add_argument("--max-apparent-bytes", type=int, default=20_000_000_000)
    scan.add_argument("--max-seconds", type=float, default=60.0)
    gate = sub.add_parser("gate-report")
    gate.add_argument("--catalog", type=Path, required=True)
    gate.add_argument("--expected-catalog-sha256", required=True)
    gate.add_argument("--decisions", type=Path, required=True)
    gate.add_argument("--expected-decisions-sha256", required=True)
    gate.add_argument("--strain", required=True)
    gate.add_argument("--require", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "scan":
        catalog = build_source_catalog(
            root=args.root,
            root_id=args.root_id,
            collection_registry_path=args.collection_registry,
            expected_collection_registry_sha256=args.expected_collection_registry_sha256,
            limits=ScanLimits(args.max_depth, args.max_files, args.max_apparent_bytes, args.max_seconds),
        )
        result = write_catalog(catalog, args.out_json, args.out_tsv)
    else:
        result = validate_report_source_preflight(
            catalog_path=args.catalog,
            expected_catalog_sha256=args.expected_catalog_sha256,
            decisions_path=args.decisions,
            expected_decisions_sha256=args.expected_decisions_sha256,
            strain_key=args.strain,
            required_collection_types=set(args.require),
        )
    emit(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 3


if __name__ == "__main__":
    raise SystemExit(main())
