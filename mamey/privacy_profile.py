"""Portable, user-owned strain privacy profiles.

This module deliberately separates a user's named access tier from Mamey's
binary package release flag. A profile can express any number of named tiers,
while existing consumers continue to receive only ``PUBLIC`` or ``PRIVATE``.
A non-public named tier is always PRIVATE at the package boundary.

Profiles are local operator configuration, never a source of biological
evidence. Missing assignments use a required non-public default tier, so a
newly added strain cannot become public by shape or prefix.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any


class PrivacyProfileError(ValueError):
    """Raised for an invalid or unsafe privacy profile."""


@dataclass(frozen=True)
class PrivacyResolution:
    tier_id: str
    release: str
    assignment_state: str
    reason: str


@dataclass(frozen=True)
class PrivacyProfile:
    profile_id: str
    default_tier: str
    public_tiers: frozenset[str]
    tiers: frozenset[str]
    assignments: dict[str, str]


@dataclass(frozen=True)
class PublicExportIdentifier:
    """One operator-declared literal that must not enter a public tree."""

    identifier_id: str
    literal: str


@dataclass(frozen=True)
class PublicExportAllowance:
    """A source-bound content-only exception for one declared private literal."""

    identifier_id: str
    relative_path: str
    sha256: str
    reason: str
    purpose: str
    state: str


@dataclass(frozen=True)
class PublicExportPolicy:
    """Portable folder/export controls owned by the same privacy-profile contract.

    The profile remains operator configuration, not scientific evidence or
    publication authority.  This policy augments, but never weakens, the
    built-in public-export protections.
    """

    excluded_root_names: frozenset[str]
    excluded_relative_paths: frozenset[str]
    private_identifiers: tuple[PublicExportIdentifier, ...]
    allowlisted_occurrences: tuple[PublicExportAllowance, ...]


# A staging directory may occur below docs/ or another user root.  Treating the
# name as a path component closes that class without hard-coding a workspace.
_DEFAULT_PUBLIC_EXCLUDED_ROOT_NAMES = frozenset({"future_improvements"})
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_ALLOWANCE_PURPOSE_CONTENT_ONLY_EXCEPTION = "CONTENT_ONLY_EXCEPTION"
_ALLOWANCE_ACTIVE_STATE = "ACTIVE"
_ALLOWANCE_FIELDS = frozenset({"identifier_id", "relative_path", "sha256", "reason", "purpose", "state"})
_PUBLIC_EXPORT_POLICY_FIELDS = frozenset({
    "exclude_root_names", "exclude_relative_paths", "private_identifiers", "allowlisted_occurrences",
})


def _reject_duplicate_object_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Decode profile objects without silently overwriting duplicate policy keys."""
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PrivacyProfileError(f"privacy profile contains duplicate object key: {key}")
        result[key] = value
    return result


def _load_profile_json(profile_path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(profile_path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_object_keys)
    except OSError as exc:
        raise PrivacyProfileError(f"cannot read privacy profile {profile_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PrivacyProfileError(f"privacy profile is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise PrivacyProfileError("privacy profile must be a JSON object")
    return raw


def _text(value: Any, field: str) -> str:
    result = str(value or "").strip()
    if not result:
        raise PrivacyProfileError(f"privacy profile requires non-empty {field}")
    return result


def _relative_path(value: Any, field: str) -> str:
    result = _text(value, field)
    if "\\" in result or "\x00" in result:
        raise PrivacyProfileError(f"{field} must use portable POSIX separators without NUL")
    candidate = Path(result)
    if candidate.is_absolute() or ".." in candidate.parts or result in {".", ""}:
        raise PrivacyProfileError(f"{field} must be a non-empty relative path without '..'")
    return candidate.as_posix()


def _root_name(value: Any, field: str) -> str:
    result = _text(value, field)
    if "/" in result or "\\" in result or result in {".", ".."}:
        raise PrivacyProfileError(f"{field} must be a single directory name")
    return result


def load_public_export_policy(path: str | Path | None = None) -> PublicExportPolicy:
    """Load optional public-export controls from a privacy-profile v1 file.

    A missing profile retains the safe built-in future-improvements exclusion.
    When supplied, the file must be a valid privacy profile; a partial or
    alternate policy file is rejected rather than interpreted heuristically.
    """
    if path is None:
        return PublicExportPolicy(_DEFAULT_PUBLIC_EXCLUDED_ROOT_NAMES, frozenset(), (), ())
    profile_path = Path(path)
    raw = _load_profile_json(profile_path)
    if raw.get("schema_version") != "sapote_privacy_profile_v1":
        raise PrivacyProfileError("public export policy requires sapote_privacy_profile_v1")
    controls = raw.get("public_export_policy", {})
    if not isinstance(controls, dict):
        raise PrivacyProfileError("public_export_policy must be an object when supplied")
    unknown_controls = set(controls) - _PUBLIC_EXPORT_POLICY_FIELDS
    if unknown_controls:
        raise PrivacyProfileError(
            "public_export_policy contains unknown field(s): " + ", ".join(sorted(unknown_controls))
        )

    root_names = set(_DEFAULT_PUBLIC_EXCLUDED_ROOT_NAMES)
    supplied_root_names = controls.get("exclude_root_names", [])
    if not isinstance(supplied_root_names, list):
        raise PrivacyProfileError("public_export_policy.exclude_root_names must be a list")
    root_names.update(_root_name(value, "public_export_policy.exclude_root_names entry") for value in supplied_root_names)

    supplied_paths = controls.get("exclude_relative_paths", [])
    if not isinstance(supplied_paths, list):
        raise PrivacyProfileError("public_export_policy.exclude_relative_paths must be a list")
    relative_paths = frozenset(_relative_path(value, "public_export_policy.exclude_relative_paths entry") for value in supplied_paths)

    raw_identifiers = controls.get("private_identifiers", [])
    if not isinstance(raw_identifiers, list):
        raise PrivacyProfileError("public_export_policy.private_identifiers must be a list")
    identifiers: list[PublicExportIdentifier] = []
    identifiers_by_id: set[str] = set()
    literals: set[str] = set()
    for row in raw_identifiers:
        if not isinstance(row, dict):
            raise PrivacyProfileError("each public_export_policy.private_identifiers row must be an object")
        identifier_id = _text(row.get("identifier_id"), "public_export_policy.private_identifiers identifier_id")
        literal = _text(row.get("literal"), "public_export_policy.private_identifiers literal")
        if "\n" in literal or "\r" in literal:
            raise PrivacyProfileError("public_export_policy private identifier literals must be single-line")
        if identifier_id in identifiers_by_id or literal in literals:
            raise PrivacyProfileError("duplicate public_export_policy private identifier id or literal")
        identifiers_by_id.add(identifier_id)
        literals.add(literal)
        identifiers.append(PublicExportIdentifier(identifier_id, literal))

    raw_allowances = controls.get("allowlisted_occurrences", [])
    if not isinstance(raw_allowances, list):
        raise PrivacyProfileError("public_export_policy.allowlisted_occurrences must be a list")
    allowances: list[PublicExportAllowance] = []
    seen_allowances: set[tuple[str, str]] = set()
    for row in raw_allowances:
        if not isinstance(row, dict):
            raise PrivacyProfileError("each public_export_policy.allowlisted_occurrences row must be an object")
        unexpected = set(row) - _ALLOWANCE_FIELDS
        missing = _ALLOWANCE_FIELDS - set(row)
        if unexpected or missing:
            details = []
            if missing:
                details.append("missing " + ", ".join(sorted(missing)))
            if unexpected:
                details.append("unknown " + ", ".join(sorted(unexpected)))
            raise PrivacyProfileError("invalid allowlisted occurrence fields: " + "; ".join(details))
        identifier_id = _text(row.get("identifier_id"), "public_export_policy.allowlisted_occurrences identifier_id")
        relative_path = _relative_path(row.get("relative_path"), "public_export_policy.allowlisted_occurrences relative_path")
        digest = _text(row.get("sha256"), "public_export_policy.allowlisted_occurrences sha256")
        reason = _text(row.get("reason"), "public_export_policy.allowlisted_occurrences reason")
        purpose = _text(row.get("purpose"), "public_export_policy.allowlisted_occurrences purpose")
        state = _text(row.get("state"), "public_export_policy.allowlisted_occurrences state")
        if identifier_id not in identifiers_by_id:
            raise PrivacyProfileError("allowlisted occurrence references an undeclared private identifier")
        if not _SHA256_RE.fullmatch(digest):
            raise PrivacyProfileError("allowlisted occurrence sha256 must be lowercase SHA-256")
        if purpose != _ALLOWANCE_PURPOSE_CONTENT_ONLY_EXCEPTION:
            raise PrivacyProfileError(
                "allowlisted occurrence purpose must be " + _ALLOWANCE_PURPOSE_CONTENT_ONLY_EXCEPTION
            )
        if state != _ALLOWANCE_ACTIVE_STATE:
            raise PrivacyProfileError("allowlisted occurrence state must be " + _ALLOWANCE_ACTIVE_STATE)
        key = (identifier_id, relative_path)
        if key in seen_allowances:
            raise PrivacyProfileError("duplicate public_export_policy allowlisted occurrence")
        seen_allowances.add(key)
        allowances.append(PublicExportAllowance(identifier_id, relative_path, digest, reason, purpose, state))

    return PublicExportPolicy(frozenset(root_names), relative_paths, tuple(identifiers), tuple(allowances))


def load_privacy_profile(path: str | Path) -> PrivacyProfile:
    """Load a version-1 profile and fail closed on ambiguous assignments."""
    profile_path = Path(path)
    raw = _load_profile_json(profile_path)
    if raw.get("schema_version") != "sapote_privacy_profile_v1":
        raise PrivacyProfileError("privacy profile schema_version must be sapote_privacy_profile_v1")
    profile_id = _text(raw.get("profile_id"), "profile_id")
    rows = raw.get("tiers")
    if not isinstance(rows, list) or not rows:
        raise PrivacyProfileError("privacy profile requires a non-empty tiers list")
    tier_ids: set[str] = set()
    public_tiers: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise PrivacyProfileError("each privacy tier must be an object")
        tier_id = _text(row.get("tier_id"), "tier_id")
        if tier_id in tier_ids:
            raise PrivacyProfileError(f"duplicate privacy tier_id: {tier_id}")
        tier_ids.add(tier_id)
        if row.get("public_export") is True:
            public_tiers.add(tier_id)
    default_tier = _text(raw.get("default_tier"), "default_tier")
    if default_tier not in tier_ids:
        raise PrivacyProfileError("default_tier is not declared in tiers")
    if default_tier in public_tiers:
        raise PrivacyProfileError("default_tier must be non-public so unassigned strains fail closed")
    assignments: dict[str, str] = {}
    assignment_rows = raw.get("strain_assignments", [])
    if not isinstance(assignment_rows, list):
        raise PrivacyProfileError("strain_assignments must be a list")
    for row in assignment_rows:
        if not isinstance(row, dict):
            raise PrivacyProfileError("each strain assignment must be an object")
        strain_id = _text(row.get("strain_id"), "strain_id")
        tier_id = _text(row.get("tier_id"), "tier_id")
        if tier_id not in tier_ids:
            raise PrivacyProfileError(f"assignment for {strain_id!r} uses unknown tier {tier_id!r}")
        if strain_id in assignments:
            raise PrivacyProfileError(f"duplicate exact strain assignment: {strain_id}")
        assignments[strain_id] = tier_id
    return PrivacyProfile(profile_id, default_tier, frozenset(public_tiers), frozenset(tier_ids), assignments)


def resolve_profile_privacy(strain_id: str, profile: PrivacyProfile, *, override: str | None = None) -> PrivacyResolution:
    """Resolve one exact strain ID without inferring privacy from its spelling."""
    strain = _text(strain_id, "strain_id")
    tier_id = profile.assignments.get(strain, profile.default_tier)
    explicit = strain in profile.assignments
    public = tier_id in profile.public_tiers
    requested = str(override or "").strip().upper()
    if requested not in {"", "PUBLIC", "PRIVATE"}:
        raise PrivacyProfileError("release override must be PUBLIC, PRIVATE, or omitted")
    if requested == "PRIVATE":
        return PrivacyResolution(tier_id, "PRIVATE", "EXACT" if explicit else "DEFAULT", "operator_private_override")
    if requested == "PUBLIC" and not public:
        return PrivacyResolution(tier_id, "PRIVATE", "EXACT" if explicit else "DEFAULT", "public_override_refused_by_profile")
    return PrivacyResolution(tier_id, "PUBLIC" if public else "PRIVATE", "EXACT" if explicit else "DEFAULT", "exact_public_assignment" if public and explicit else "nonpublic_profile_tier")
