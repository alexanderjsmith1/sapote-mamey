"""Recovery/package status semantics.

A package can validate structurally while still representing a recovered or
partial run. This module makes that explicit for merge chats and QA tools.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json

PACKAGE_STATUS_VALUES = (
    "MAMEY_COMPLETE",
    "RECOVERY_VALIDATED",
    "RECOVERY_NEEDED",
    "PARTIAL_FAILED",
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def detect_recovery_marker(package_dir: str | Path) -> str:
    root = Path(package_dir)
    names = {p.name for p in root.rglob("*") if p.is_file()}
    if any(n in names for n in {"RECOVERY_VALIDATED.json", "recovery_validated.json", "recovery_receipt.json"}):
        return "validated"
    if any(n in names for n in {"RECOVERY_NEEDED.json", "recovery_needed.json", "PARTIAL_FAILED.json", "partial_failed.json"}):
        return "needed"
    if any("recovery" in n.lower() for n in names):
        return "present"
    return "none"


def infer_package_status(
    package_dir: str | Path,
    *,
    manifest: dict[str, Any] | None = None,
    validator_status: str | None = None,
) -> str:
    """Infer package_status without hiding recovery semantics.

    Explicit valid manifest package_status wins. Otherwise recovery markers are
    honored before normal validator success.
    """
    root = Path(package_dir)
    manifest = manifest or {}
    explicit = str(manifest.get("package_status") or "").strip()
    if explicit in PACKAGE_STATUS_VALUES:
        return explicit

    recovery_state = detect_recovery_marker(root)
    validator_status = str(validator_status or manifest.get("status") or manifest.get("validator_status") or "").strip()

    if recovery_state == "validated":
        return "RECOVERY_VALIDATED"
    if recovery_state in {"needed", "present"}:
        return "RECOVERY_NEEDED"

    # CORE-P02 (fail-open fix): only assert MAMEY_COMPLETE on an AFFIRMATIVE completion signal — or
    # when no validator status is available at all (the packaging-time seal default; a freshly sealed
    # package with no failure/recovery marker is complete by construction). A NON-EMPTY status that is
    # neither a recognized success nor a literal "FAIL" — e.g. "GATE_FAILED", "INCOMPLETE", "ERROR",
    # or any unknown token — must NOT render a package "complete" it never earned; it fails SAFE to
    # PARTIAL_FAILED (merge_semantics: do_not_merge_as_complete).
    vs = validator_status.upper()
    if not vs:
        return "MAMEY_COMPLETE"
    if vs.startswith(("PASS", "MAMEY_COMPLETE")) or vs in {"OK", "COMPLETE"}:
        return "MAMEY_COMPLETE"
    return "PARTIAL_FAILED"


def package_status_receipt(
    package_dir: str | Path,
    *,
    manifest: dict[str, Any] | None = None,
    validator_status: str | None = None,
    terminal_status: str | None = None,
    issue_count: int | None = None,
) -> dict[str, Any]:
    root = Path(package_dir)
    manifest = manifest or {}
    status = infer_package_status(root, manifest=manifest, validator_status=validator_status)
    _terminal_status = terminal_status or manifest.get("terminal_status") or ""
    _issue_count = issue_count if issue_count is not None else manifest.get("issue_count")
    try:
        _issue_count = int(_issue_count or 0)
    except (TypeError, ValueError):
        _issue_count = 0
    return {
        "schema_version": "package_status_v1",
        "package_status": status,
        "allowed_values": list(PACKAGE_STATUS_VALUES),
        "recovery_marker": detect_recovery_marker(root),
        "validator_status": validator_status or manifest.get("validator_status") or manifest.get("status", ""),
        "terminal_status": _terminal_status,
        "issue_count": _issue_count,
        "merge_semantics": (
            "normal_complete_with_issues" if status == "MAMEY_COMPLETE" and _issue_count else
            "normal_complete" if status == "MAMEY_COMPLETE" else
            "validated_recovery_not_uninterrupted" if status == "RECOVERY_VALIDATED" else
            "requires_recovery_or_manual_review" if status == "RECOVERY_NEEDED" else
            "partial_or_failed_do_not_merge_as_complete"
        ),
    }


def write_package_status_receipt(
    package_dir: str | Path,
    *,
    manifest: dict[str, Any] | None = None,
    validator_status: str | None = None,
    terminal_status: str | None = None,
    issue_count: int | None = None,
) -> Path:
    root = Path(package_dir)
    receipt = package_status_receipt(
        root, manifest=manifest, validator_status=validator_status,
        terminal_status=terminal_status, issue_count=issue_count)
    path = root / "package_status.json"
    # v9.7.371 fix: was a plain write_text(). packaging.py writes manifest.json /
    # checksums_sha256.txt / repro_fingerprint.json in the SAME seal via its own
    # _atomic_write_text() (tmp-sibling + replace) specifically so an interrupted seal never
    # leaves a truncated integrity file (CORE-P04). package_status.json is exactly that class of
    # file -- an interrupted write here leaves it truncated/unreadable, which readers (e.g.
    # widget_deliverable.PackageSource.json()) silently treat as "no status" rather than
    # surfacing the interrupted seal. Duplicated locally (not imported from packaging.py) because
    # packaging.py already imports write_package_status_receipt from this module -- importing
    # back would be circular.
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    tmp.replace(path)
    return path
