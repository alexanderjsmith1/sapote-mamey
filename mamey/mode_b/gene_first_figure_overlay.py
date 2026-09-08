"""BGC-summary-only Figure Factory overlay contract for Mode B gene-first v2.

The returned row is additive.  This module never opens or mutates a Figure
Factory source table and refuses every independent evidence consumer plane.
"""

from __future__ import annotations

import csv
try:
    from ..csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

from .gene_first_stage_v2 import (
    IDENTITY_FIELDS,
    StageHold,
    canonical_identity,
    identity_token,
    sha256_file,
)


OVERLAY_SCHEMA = "modeb_figure_factory_bgc_summary_overlay_v2"
AUTHORING_RECEIPT_SCHEMA = "modeb_gene_first_authoring_receipt_v2"
ALLOWED_ACTIONS = {
    "RETAIN_SOURCE_SUMMARY",
    "FLAG_SUMMARY_ONLY",
    "WITHHOLD_SUMMARY_PENDING_BINDING",
    "PROPOSE_SUMMARY_RECLASSIFICATION",
}
PROHIBITED_CONSUMER_PLANES = {
    "GENE",
    "DOMAIN",
    "MODULE",
    "CASSETTE",
    "NEIGHBORHOOD",
    "RAW_EVIDENCE",
}
OVERLAY_FIELDS = (
    "overlay_schema",
    *IDENTITY_FIELDS,
    "consumer_plane",
    "action",
    "source_summary_class",
    "proposed_summary_class",
    "reason_codes",
    "source_summary_locator",
    "source_summary_sha256",
    "stage_id",
    "stage_receipt_sha256",
    "authoring_receipt_sha256",
    "claim_ceiling",
    "overlay_effect_scope",
    "basis_layer",
    "independent_plane_policy",
    "status",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REASON = re.compile(r"^[A-Z][A-Z0-9_]*$")


class OverlayHold(ValueError):
    """Typed summary-overlay refusal."""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _refuse(code: str, detail: str) -> None:
    raise OverlayHold(code, detail)


def _require_sha(value: Any, label: str) -> str:
    normalized = str(value or "").strip().lower()
    if not _SHA256.fullmatch(normalized):
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"{label} is not a SHA-256")
    return normalized


def _portable_locator(value: Any) -> str:
    locator = str(value or "").strip()
    lowered = locator.lower()
    if not locator:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "source summary locator is blank")
    if (
        locator.startswith(("/", "\\"))
        or re.match(r"^[A-Za-z]:[\\/]", locator)
        or lowered.startswith("file://")
        or "/users/" in lowered
        or "\\users\\" in lowered
        or "codex alex 2026" in lowered
    ):
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "source summary locator is not portable")
    path_part = locator.split("://", 1)[-1]
    if ".." in PurePosixPath(path_part.replace("\\", "/")).parts:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "source summary locator traverses a parent")
    return locator


def _reason_codes(value: Any) -> list[str]:
    if isinstance(value, str):
        raw = [item for item in value.split(";") if item]
    elif isinstance(value, (list, tuple)):
        raw = [str(item) for item in value]
    else:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "reason_codes must be a list or semicolon string")
    normalized = sorted({item.strip().upper() for item in raw if item.strip()})
    if any(not _REASON.fullmatch(item) for item in normalized):
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "reason_codes contain an invalid token")
    return normalized


def _overlay_identity(value: Mapping[str, Any], label: str) -> dict[str, str]:
    try:
        return canonical_identity(value)
    except StageHold as exc:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"{label} identity is invalid: {exc.detail}")


def _verify_authoring_receipt(
    path: str | Path,
    *,
    expected_identity: Mapping[str, str],
    expected_stage_id: str,
    expected_stage_receipt_sha256: str,
    expected_authoring_receipt_sha256: str,
) -> None:
    receipt_path = Path(path)
    if not receipt_path.is_file():
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt file is missing")
    if sha256_file(receipt_path) != expected_authoring_receipt_sha256:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt SHA does not match")
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"authoring receipt is unreadable: {exc}")
    if not isinstance(receipt, dict) or receipt.get("schema_version") != AUTHORING_RECEIPT_SCHEMA:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt schema is invalid")
    raw_identity = receipt.get("identity")
    if not isinstance(raw_identity, dict) or _overlay_identity(raw_identity, "authoring receipt") != expected_identity:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt identity conflicts")
    if receipt.get("identity_token") != identity_token(expected_identity):
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt identity token conflicts")
    if receipt.get("stage_id") != expected_stage_id:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt stage ID conflicts")
    if receipt.get("stage_receipt_sha256") != expected_stage_receipt_sha256:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt stage SHA conflicts")
    token = identity_token(expected_identity)
    expected_member_names = {
        "nr_clustered_nr_disagreement": f"{token}__nr_vs_clustered_nr_disagreement.tsv",
        "important_genes": f"{token}__important_genes_v2.tsv",
        "locus_diagnostics": f"{token}__locus_diagnostics.json",
        "authoring_packet": f"{token}__authoring_packet.json",
    }
    raw_members = receipt.get("members")
    if not isinstance(raw_members, list) or not all(isinstance(item, dict) for item in raw_members):
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt members are invalid")
    members = {str(item.get("role", "")): item for item in raw_members}
    if set(members) != set(expected_member_names) or len(members) != len(raw_members):
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt member roles are incomplete")
    for role, expected_name in expected_member_names.items():
        member = members[role]
        if member.get("name") != expected_name:
            _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"authoring member name conflicts for {role}")
        expected_sha = _require_sha(member.get("sha256"), f"authoring member {role} SHA")
        try:
            expected_bytes = int(member.get("bytes"))
        except (TypeError, ValueError):
            _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"authoring member {role} byte count is invalid")
        member_path = receipt_path.parent / expected_name
        if not member_path.is_file():
            _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"authoring member is missing: {expected_name}")
        if member_path.stat().st_size != expected_bytes or sha256_file(member_path) != expected_sha:
            _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"authoring member changed: {expected_name}")
    authoring_id = _require_sha(receipt.get("authoring_id"), "authoring receipt authoring_id")
    receipt_basis = {
        "schema_version": AUTHORING_RECEIPT_SCHEMA,
        "identity": dict(expected_identity),
        "identity_token": identity_token(expected_identity),
        "stage_id": expected_stage_id,
        "stage_receipt_sha256": expected_stage_receipt_sha256,
        "members": raw_members,
    }
    expected_authoring_id = hashlib.sha256(
        json.dumps(
            receipt_basis,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    if authoring_id != expected_authoring_id:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "authoring receipt content ID conflicts")


def build_summary_overlay(
    decision: Mapping[str, Any],
    authoring_receipt_path: str | Path,
) -> dict[str, str]:
    """Validate and copy one receipt-bound BGC-summary overlay proposal."""

    plane = str(decision.get("consumer_plane", "")).strip().upper()
    if plane != "BGC_SUMMARY":
        if plane in PROHIBITED_CONSUMER_PLANES:
            _refuse(
                "MODEB_GF2_OVERLAY_CONSUMER_REFUSED",
                f"Mode B overlay cannot feed independent {plane} evidence",
            )
        _refuse("MODEB_GF2_OVERLAY_CONSUMER_REFUSED", f"unsupported consumer plane: {plane!r}")
    identity = _overlay_identity(decision, "overlay decision")
    action = str(decision.get("action", "")).strip().upper()
    if action not in ALLOWED_ACTIONS:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"invalid overlay action: {action!r}")
    source_class = str(decision.get("source_summary_class", "")).strip()
    proposed_class = str(decision.get("proposed_summary_class", "")).strip()
    if not source_class:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "source summary class is blank")
    reasons = _reason_codes(decision.get("reason_codes", []))
    if action == "PROPOSE_SUMMARY_RECLASSIFICATION":
        if not proposed_class or proposed_class == source_class:
            _refuse(
                "MODEB_GF2_OVERLAY_BINDING_HOLD",
                "reclassification requires a distinct proposed summary class",
            )
        if not reasons:
            _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "reclassification requires reason codes")
    else:
        if proposed_class:
            _refuse(
                "MODEB_GF2_OVERLAY_BINDING_HOLD",
                "only a reclassification proposal may carry a proposed class",
            )
        if action in {"FLAG_SUMMARY_ONLY", "WITHHOLD_SUMMARY_PENDING_BINDING"} and not reasons:
            _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", f"{action} requires reason codes")
    claim_ceiling = str(decision.get("claim_ceiling", "")).strip()
    if not claim_ceiling:
        _refuse("MODEB_GF2_OVERLAY_BINDING_HOLD", "claim ceiling is blank")
    stage_id = _require_sha(decision.get("stage_id"), "stage_id")
    stage_receipt_sha256 = _require_sha(
        decision.get("stage_receipt_sha256"), "stage_receipt_sha256"
    )
    authoring_receipt_sha256 = _require_sha(
        decision.get("authoring_receipt_sha256"), "authoring_receipt_sha256"
    )
    _verify_authoring_receipt(
        authoring_receipt_path,
        expected_identity=identity,
        expected_stage_id=stage_id,
        expected_stage_receipt_sha256=stage_receipt_sha256,
        expected_authoring_receipt_sha256=authoring_receipt_sha256,
    )
    return {
        "overlay_schema": OVERLAY_SCHEMA,
        **{field: identity[field] for field in IDENTITY_FIELDS},
        "consumer_plane": "BGC_SUMMARY",
        "action": action,
        "source_summary_class": source_class,
        "proposed_summary_class": proposed_class,
        "reason_codes": ";".join(reasons),
        "source_summary_locator": _portable_locator(decision.get("source_summary_locator")),
        "source_summary_sha256": _require_sha(
            decision.get("source_summary_sha256"), "source_summary_sha256"
        ),
        "stage_id": stage_id,
        "stage_receipt_sha256": stage_receipt_sha256,
        "authoring_receipt_sha256": authoring_receipt_sha256,
        "claim_ceiling": claim_ceiling,
        "overlay_effect_scope": "BGC_SUMMARY_ONLY",
        # V4 §13 / three-layer model: an overlay is a Layer-B (exact-locus) artifact; it can
        # never carry a Layer-C (cohort/population) claim class.
        "basis_layer": "B",
        "independent_plane_policy": "GENE_DOMAIN_MODULE_CASSETTE_NEIGHBORHOOD_RAW_EVIDENCE_UNCHANGED",
        "status": "OWNER_REVIEW_CANDIDATE_NOT_APPLIED",
    }


def write_summary_overlay(
    decision: Mapping[str, Any],
    authoring_receipt_path: str | Path,
    output_root: str | Path,
) -> Path:
    """Write one additive TSV after validating the whole decision and target."""

    row = build_summary_overlay(decision, authoring_receipt_path)
    root = Path(output_root)
    if not root.is_dir():
        _refuse("MODEB_GF2_OUTPUT_REFUSED", "output root must already exist")
    token = identity_token(row)
    path = root / f"{token}__figure_factory_bgc_summary_overlay.tsv"
    if path.exists():
        _refuse("MODEB_GF2_OUTPUT_REFUSED", f"overlay output exists: {path.name}")
    try:
        with path.open("x", encoding="utf-8", newline="") as handle:
            writer = _SafeDictWriter(handle, delimiter="\t", fieldnames=list(OVERLAY_FIELDS))
            writer.writeheader()
            writer.writerow(row)
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        _refuse("MODEB_GF2_OUTPUT_REFUSED", f"overlay output exists: {path.name}")
    return path


__all__ = [
    "ALLOWED_ACTIONS",
    "OVERLAY_FIELDS",
    "OVERLAY_SCHEMA",
    "OverlayHold",
    "PROHIBITED_CONSUMER_PLANES",
    "build_summary_overlay",
    "write_summary_overlay",
]
