#!/usr/bin/env python3
"""Run the BGC report builder from portable logical-source configuration."""

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
import json
import os
import shutil
import sys
import uuid
from pathlib import Path, PurePosixPath

try:
    from . import bgc_report_builder as report_builder
    from .evidence_roots import (
        EvidenceRootError, load_json, logical_locator, require_source_discovery_preflight,
        resolve_output, resolve_roots, resolve_sources,
    )
except ImportError:
    import bgc_report_builder as report_builder
    from evidence_roots import (
        EvidenceRootError, load_json, logical_locator, require_source_discovery_preflight,
        resolve_output, resolve_roots, resolve_sources,
    )


SPEC_SCHEMA = "sapote_bgc_report_build_spec_v2"
RECOVERY_SCHEMA = "sapote_report_publication_recovery_receipt_v1"
RECOVERY_RECEIPT_NAME = "publication_recovery_receipt.json"


class ReportPublicationError(OSError):
    """Typed publication failure with a path-redacted machine recovery receipt."""

    def __init__(self, receipt: dict):
        self.receipt = receipt
        super().__init__(
            f"REPORT_PUBLICATION_FAILED:{receipt['recovery_locator']}:"
            f"{receipt['next_action']}"
        )


def _parse_root_override(values: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--evidence-root values must be ROOT_ID=/absolute/path")
        root_id, path = value.split("=", 1)
        if root_id in out:
            raise ValueError(f"Duplicate --evidence-root override: {root_id}")
        out[root_id] = path
    return out


def run(config_path: Path, manifest_path: Path, spec_path: Path, root_overrides: dict[str, str]) -> dict:
    config = load_json(config_path)
    manifest = load_json(manifest_path)
    spec = load_json(spec_path)
    if spec.get("schema_version") != SPEC_SCHEMA:
        raise ValueError("Invalid report build spec schema")
    roots = resolve_roots(config, config_path, cli_roots=root_overrides)
    release = spec.get("release", "INTERNAL")
    resolved, portable_receipt = resolve_sources(manifest, roots, release)
    source_preflight_receipt = require_source_discovery_preflight(
        source_manifest=manifest,
        resolved_sources=resolved,
        spec=spec,
        strain_keys=[spec["strain"]],
    )
    source_ids = spec.get("source_ids", {})

    def one(role: str, required: bool = False) -> Path | None:
        logical_id = source_ids.get(role)
        if logical_id is None:
            if required:
                raise ValueError(f"Build spec lacks required source role {role}")
            return None
        if logical_id not in resolved:
            raise ValueError(f"Source role {role} did not resolve: {logical_id}")
        return resolved[logical_id]

    locus_ids = source_ids.get("locus_projects", [])
    if not isinstance(locus_ids, list):
        raise ValueError("source_ids.locus_projects must be an array")
    locus_projects = [resolved[logical_id] for logical_id in locus_ids]
    output = spec.get("output", {})
    output_root_id = output.get("root_id", "")
    output_relative_path = output.get("relative_path", "")
    out_root = resolve_output(roots, output_root_id, output_relative_path)
    if out_root.exists():
        raise FileExistsError(f"Final output root already exists: {out_root}")
    out_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root = out_root.with_name(f".{out_root.name}.staging-{uuid.uuid4().hex}")
    configured_output_root = roots[output_root_id]
    try:
        staging_relative = staging_root.resolve().relative_to(configured_output_root).as_posix()
    except ValueError as exc:
        raise EvidenceRootError("Staging path escapes configured output root") from exc
    logical_by_path = {str(path.resolve()): logical_id for logical_id, path in resolved.items()}
    args = argparse.Namespace(
        identity_db=one("identity_db", required=True),
        strain=spec["strain"],
        alias=list(spec.get("aliases", [])),
        region_key=list(spec.get("region_keys", [])),
        blastp_reconciliation=one("blastp_reconciliation"),
        expected_blastp_channel=list(spec.get("expected_blastp_channels", [])),
        modeb_ledger=one("modeb_ledger"),
        literature_json=one("literature_json"),
        literature_record_number=list(spec.get("literature_record_numbers", [])),
        locus_project=locus_projects,
        release=release,
        captured_at_utc=spec.get("captured_at_utc"),
        out_root=staging_root,
        logical_source_by_resolved_path=logical_by_path,
        portable_resolution_receipt=portable_receipt,
        source_discovery_catalog=resolved[spec["source_discovery_preflight"]["catalog_source_id"]],
        expected_source_discovery_catalog_sha256=source_preflight_receipt["catalog_sha256"],
        source_discovery_decisions=resolved[spec["source_discovery_preflight"]["decisions_source_id"]],
        expected_source_discovery_decisions_sha256=source_preflight_receipt["decisions_sha256"],
        required_collection_type=list(source_preflight_receipt["required_collection_types"]),
    )
    try:
        result = report_builder.build(args)
    except Exception:
        # v97396 fix: this except clause used to also wrap the os.replace() below, so ANY
        # failure -- including one AFTER build() had already succeeded -- deleted staging_root.
        # Here build() itself is what failed, so staging_root may hold a genuinely partial
        # report; cleaning it up is correct.
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise
    # Build succeeded: publication failure must preserve the completed bytes and surface one
    # governed logical recovery location without disclosing a machine path.
    try:
        os.replace(staging_root, out_root)
    except Exception as exc:
        recovery_locator = logical_locator(output_root_id, staging_relative)
        receipt_relative = (PurePosixPath(staging_relative) / RECOVERY_RECEIPT_NAME).as_posix()
        receipt = {
            "schema_version": RECOVERY_SCHEMA,
            "status": "RECOVERY_REQUIRED_PUBLICATION_FAILED",
            "recovery_locator": recovery_locator,
            "target_locator": logical_locator(output_root_id, output_relative_path),
            "receipt_locator": logical_locator(output_root_id, receipt_relative),
            "completed_staging_preserved": True,
            "next_action": "RESOLVE_DESTINATION_THEN_RETRY_ATOMIC_PUBLICATION",
            "error_type": type(exc).__name__,
            "error_errno": getattr(exc, "errno", None),
            "error_message_redacted": True,
            "engineering_status": "RECOVERY_CANDIDATE_NOT_INTEGRATED_OR_RELEASED",
        }
        receipt_path = staging_root / RECOVERY_RECEIPT_NAME
        receipt["receipt_file_state"] = "WRITTEN_IN_PRESERVED_STAGING"
        try:
            receipt_path.write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        except OSError:
            receipt["receipt_file_state"] = "WRITE_FAILED_TYPED_RECEIPT_RETAINED_IN_EXCEPTION"
        raise ReportPublicationError(receipt) from None
    return {"report_manifest": result, "portable_resolution_receipt": portable_receipt}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-root-config", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--build-spec", type=Path, required=True)
    parser.add_argument("--evidence-root", action="append", default=[])
    args = parser.parse_args()
    try:
        result = run(
            args.evidence_root_config,
            args.source_manifest,
            args.build_spec,
            _parse_root_override(args.evidence_root),
        )
    except ReportPublicationError as exc:
        sys.stderr.write(str(json.dumps(exc.receipt, indent=2, sort_keys=True)) + "\n")
        return 2
    emit(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
