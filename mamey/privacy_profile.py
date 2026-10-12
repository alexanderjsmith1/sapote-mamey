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

from contextlib import contextmanager
from dataclasses import dataclass, field
import hashlib
import json
import os
import stat
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
class PublicExportFileHold:
    """One built-in unresolved-provenance file; never a private-identity classifier."""

    hold_id: str
    parent: str
    glob: str
    sha256: str
    relative_path_sha256: str


@dataclass(frozen=True)
class PublicExportFileBinding:
    hold_id: str
    relative_path: str
    sha256: str
    identity: tuple[int, ...]


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
    # No JSON/profile override: operator configuration cannot remove built-in holds.
    file_holds: tuple[PublicExportFileHold, ...] = field(default_factory=lambda: _DEFAULT_PUBLIC_FILE_HOLDS)


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


# Source-bound default, with identity-bearing basename represented only by its path digest.
# Public reference spelling is not publication authority for the derived answer-key.
_DEFAULT_PUBLIC_FILE_HOLDS = (
    PublicExportFileHold(
        "WH-ANSWER-KEY-01", "Wheelhouse/validations", "*.json",
        "a8d4eb2ef9dedc2be8cbc2fc58fc2c4de8aa59f286421dafb7c8311595ac8bb4",
        "e87f2963c548b881adb9d52b6ed384563fc0305c7dab42562d77efdd468df726",
    ),
)
PUBLIC_FILE_HOLD_RECEIPT = "PUBLIC_EXPORT_FILE_HOLDS.json"


def _file_hold_root(root: str | Path) -> Path:
    root = Path(root)
    if root.is_symlink():
        raise PrivacyProfileError("FILE_HOLD_ROOT_SYMLINK")
    try:
        resolved = root.resolve(strict=True)
        if not resolved.is_dir():
            raise PrivacyProfileError("FILE_HOLD_ROOT_NOT_DIRECTORY")
        return resolved
    except OSError as exc:
        raise PrivacyProfileError("FILE_HOLD_ROOT_UNREADABLE") from exc


def _file_hold_path(root: Path, relative: str, *, directory: bool = False) -> Path:
    relative = _relative_path(relative, "file hold relative path")
    current = root
    try:
        if not stat.S_ISDIR(root.lstat().st_mode) or root.resolve(strict=True) != root:
            raise PrivacyProfileError("FILE_HOLD_ROOT_IDENTITY_DRIFT")
        parts = Path(relative).parts
        for index, part in enumerate(parts):
            current = current / part
            info = current.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise PrivacyProfileError("FILE_HOLD_SYMLINK")
            if index < len(parts) - 1 or directory:
                if not stat.S_ISDIR(info.st_mode):
                    raise PrivacyProfileError("FILE_HOLD_NOT_DIRECTORY")
            elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise PrivacyProfileError("FILE_HOLD_NOT_SINGLE_REGULAR_FILE")
        if not current.resolve(strict=True).is_relative_to(root):
            raise PrivacyProfileError("FILE_HOLD_OUTSIDE_ROOT")
    except OSError as exc:
        raise PrivacyProfileError("FILE_HOLD_PATH_UNREADABLE") from exc
    return current


def _file_hold_identity(info: os.stat_result) -> tuple[int, ...]:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns)


@dataclass(frozen=True)
class PublicFileHoldDirectory:
    fd: int
    root_fd: int
    root: Path
    # Each tuple binds a component to its still-open parent and child descriptors.
    links: tuple[tuple[int, str, int, tuple[int, int]], ...]


def _directory_identity(info: os.stat_result) -> tuple[int, int]:
    if not stat.S_ISDIR(info.st_mode):
        raise PrivacyProfileError("FILE_HOLD_NOT_DIRECTORY")
    return info.st_dev, info.st_ino


def verify_public_file_hold_directory(anchor: PublicFileHoldDirectory) -> None:
    """Check lexical admission against retained descriptors; never follow replacement links."""
    try:
        if _directory_identity(anchor.root.lstat()) != _directory_identity(os.fstat(anchor.root_fd)):
            raise PrivacyProfileError("FILE_HOLD_ROOT_IDENTITY_DRIFT")
        for parent_fd, name, child_fd, expected in anchor.links:
            if (_directory_identity(os.stat(name, dir_fd=parent_fd, follow_symlinks=False)) != expected
                    or _directory_identity(os.fstat(child_fd)) != expected):
                raise PrivacyProfileError("FILE_HOLD_PARENT_IDENTITY_DRIFT")
    except OSError as exc:
        raise PrivacyProfileError("FILE_HOLD_DIRECTORY_UNREADABLE") from exc


@contextmanager
def public_file_hold_directory(root: str | Path, relative: str = "", *, root_fd: int | None = None):
    """Retain ordinary directory descriptors beneath an admitted root for one operation."""
    root = _file_hold_root(root)
    if (not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW")
            or any(function not in os.supports_dir_fd for function in (os.open, os.stat, os.unlink))
            or os.stat not in os.supports_follow_symlinks):
        raise PrivacyProfileError("FILE_HOLD_NO_DIRECTORY_FD_SUPPORT")
    parts = Path(_relative_path(relative, "file hold directory")).parts if relative else ()
    descriptors = []
    try:
        expected_root = _directory_identity(root.lstat())
        first = os.dup(root_fd) if root_fd is not None else os.open(
            root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        descriptors.append(first)
        if _directory_identity(os.fstat(first)) != expected_root:
            raise PrivacyProfileError("FILE_HOLD_ROOT_IDENTITY_DRIFT")
        current, links = first, []
        for name in parts:
            before = _directory_identity(os.stat(name, dir_fd=current, follow_symlinks=False))
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            descriptors.append(child)
            if (_directory_identity(os.fstat(child)) != before
                    or _directory_identity(os.stat(name, dir_fd=current, follow_symlinks=False)) != before):
                raise PrivacyProfileError("FILE_HOLD_PARENT_IDENTITY_DRIFT")
            links.append((current, name, child, before))
            current = child
        anchor = PublicFileHoldDirectory(current, first, root, tuple(links))
        verify_public_file_hold_directory(anchor)
        yield anchor
    except OSError as exc:
        raise PrivacyProfileError("FILE_HOLD_DIRECTORY_UNREADABLE") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def public_file_hold_entry_identity(directory_fd: int, name: str) -> tuple[int, ...]:
    try:
        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PrivacyProfileError("FILE_HOLD_NOT_SINGLE_REGULAR_FILE")
        return _file_hold_identity(info)
    except OSError as exc:
        raise PrivacyProfileError("FILE_HOLD_PATH_UNREADABLE") from exc


@contextmanager
def _open_public_file_hold(root: Path, relative: str):
    """Open and recheck one exact regular leaf relative to retained parent descriptors."""
    relative = _relative_path(relative, "file hold relative path")
    parent = Path(relative).parent.as_posix()
    name = Path(relative).name
    try:
        with public_file_hold_directory(root, "" if parent == "." else parent) as anchor:
            before = public_file_hold_entry_identity(anchor.fd, name)
            descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=anchor.fd)
            with os.fdopen(descriptor, "rb") as stream:
                if _file_hold_identity(os.fstat(stream.fileno())) != before:
                    raise PrivacyProfileError("FILE_HOLD_IDENTITY_DRIFT")
                yield stream, before
                if _file_hold_identity(os.fstat(stream.fileno())) != before:
                    raise PrivacyProfileError("FILE_HOLD_IDENTITY_DRIFT")
            verify_public_file_hold_directory(anchor)
            if public_file_hold_entry_identity(anchor.fd, name) != before:
                raise PrivacyProfileError("FILE_HOLD_IDENTITY_DRIFT")
    except OSError as exc:
        raise PrivacyProfileError("FILE_HOLD_READ_FAILED") from exc


def hash_public_file_hold(root: Path, relative: str) -> tuple[str, tuple[int, ...]]:
    """Stream any-size candidate without buffering unrelated JSON payloads."""
    digest = hashlib.sha256()
    with _open_public_file_hold(root, relative) as (stream, identity):
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest(), identity


def read_public_file_hold(root: Path, relative: str, *, max_bytes: int = 65536) -> tuple[bytes, tuple[int, ...]]:
    """Bound decoding input for the small generated receipt, never for candidate files."""
    with _open_public_file_hold(root, relative) as (stream, identity):
        data = stream.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise PrivacyProfileError("FILE_HOLD_RECEIPT_TOO_LARGE")
    return data, identity


def inspect_public_file_holds(root: str | Path, policy: PublicExportPolicy, *,
                              require_source_match: bool) -> tuple[tuple[PublicExportFileBinding, ...], frozenset[str]]:
    """Preflight every selector. Missing namespace is explicit minimal-source absence."""
    root = _file_hold_root(root)
    bindings = []
    present = set()
    seen_ids, seen_paths, seen_identities = set(), set(), set()
    for hold in policy.file_holds:
        if (not hold.hold_id or hold.hold_id in seen_ids
                or not _SHA256_RE.fullmatch(hold.sha256)
                or not _SHA256_RE.fullmatch(hold.relative_path_sha256)
                or not hold.glob or any(x in hold.glob for x in ("/", "\\", "**", "\x00"))):
            raise PrivacyProfileError("FILE_HOLD_INVALID_SELECTOR")
        seen_ids.add(hold.hold_id)
        parent_relative = _relative_path(hold.parent, "file hold parent")
        parent = root / parent_relative
        if not parent.exists() and not parent.is_symlink():
            # A missing namespace is allowed, but any existing ancestor must still be ordinary.
            ancestor = Path(parent_relative).parent
            while ancestor.as_posix() != ".":
                candidate = root / ancestor
                if candidate.exists() or candidate.is_symlink():
                    _file_hold_path(root, ancestor.as_posix(), directory=True)
                    break
                ancestor = ancestor.parent
            continue
        parent = _file_hold_path(root, parent_relative, directory=True)
        present.add(hold.hold_id)
        matches = []
        for candidate in sorted(parent.glob(hold.glob)):
            relative = candidate.relative_to(root).as_posix()
            sha, identity = hash_public_file_hold(root, relative)
            locator = hashlib.sha256(relative.encode("utf-8")).hexdigest()
            # Stage audit catches the original locator even if its content was modified.
            if sha == hold.sha256 or (not require_source_match and locator == hold.relative_path_sha256):
                matches.append(PublicExportFileBinding(hold.hold_id, relative, sha, identity))
        if require_source_match:
            if len(matches) != 1:
                raise PrivacyProfileError("FILE_HOLD_SOURCE_MATCH_COUNT")
            if hashlib.sha256(matches[0].relative_path.encode("utf-8")).hexdigest() != hold.relative_path_sha256:
                raise PrivacyProfileError("FILE_HOLD_SOURCE_LOCATOR_DRIFT")
        for match in matches:
            identity = match.identity[:2]
            if match.relative_path in seen_paths or identity in seen_identities:
                raise PrivacyProfileError("FILE_HOLD_DUPLICATE_SELECTION")
            seen_paths.add(match.relative_path)
            seen_identities.add(identity)
            bindings.append(match)
    return tuple(bindings), frozenset(present)


def resolve_public_file_holds(root: str | Path, policy: PublicExportPolicy) -> tuple[PublicExportFileBinding, ...]:
    return inspect_public_file_holds(root, policy, require_source_match=True)[0]


def public_file_hold_receipt(bindings: tuple[PublicExportFileBinding, ...]) -> dict[str, Any]:
    return {
        "schema": "sapote.public_export_file_holds.v1",
        "disposition": "PUBLIC_EXPORT_HOLD_UNRESOLVED_AUTHORITY",
        "records": sorted(({
            "hold_id": item.hold_id,
            "source_sha256": item.sha256,
            "relative_path_sha256": hashlib.sha256(item.relative_path.encode("utf-8")).hexdigest(),
        } for item in bindings), key=lambda item: item["hold_id"]),
    }


def load_public_file_hold_receipt(root: Path) -> dict[str, Any]:
    data, _ = read_public_file_hold(root, PUBLIC_FILE_HOLD_RECEIPT)
    try:
        document = json.loads(data, object_pairs_hook=_reject_duplicate_object_keys)
    except (UnicodeError, json.JSONDecodeError, PrivacyProfileError) as exc:
        # A supplied duplicate key may itself contain sensitive text; never echo it.
        raise PrivacyProfileError("FILE_HOLD_RECEIPT_UNREADABLE") from exc
    return document


def public_file_hold_findings(root: str | Path, policy: PublicExportPolicy) -> list[str]:
    """Read-only stage checks. Source-to-stage derivation supplies independent omission proof."""
    try:
        root = _file_hold_root(root)
        found, present = inspect_public_file_holds(root, policy, require_source_match=False)
        if found:
            return ["PUBLIC_PROVENANCE_HOLD_SHIPS: " + item.hold_id for item in found]
        receipt_path = root / PUBLIC_FILE_HOLD_RECEIPT
        if not receipt_path.exists() and not receipt_path.is_symlink():
            return ["FILE_HOLD_RECEIPT_MISSING"] if present else []
        receipt = load_public_file_hold_receipt(root)
        expected = {hold.hold_id: {"hold_id": hold.hold_id, "source_sha256": hold.sha256,
                    "relative_path_sha256": hold.relative_path_sha256} for hold in policy.file_holds}
        if (not isinstance(receipt, dict)
                or set(receipt) != {"schema", "disposition", "records"}
                or receipt["schema"] != "sapote.public_export_file_holds.v1"
                or receipt["disposition"] != "PUBLIC_EXPORT_HOLD_UNRESOLVED_AUTHORITY"
                or not isinstance(receipt["records"], list)):
            raise PrivacyProfileError("FILE_HOLD_RECEIPT_INVALID")
        seen = set()
        for record in receipt["records"]:
            if not isinstance(record, dict):
                raise PrivacyProfileError("FILE_HOLD_RECEIPT_INVALID")
            key = record.get("hold_id")
            if not isinstance(key, str) or not key or key not in expected:
                raise PrivacyProfileError("FILE_HOLD_RECEIPT_INVALID")
            if key in seen or record != expected[key]:
                raise PrivacyProfileError("FILE_HOLD_RECEIPT_INVALID")
            seen.add(key)
        if not present.issubset(seen):
            raise PrivacyProfileError("FILE_HOLD_RECEIPT_INCOMPLETE")
        return []
    except (OSError, RuntimeError, PrivacyProfileError) as exc:
        return [str(exc) if isinstance(exc, PrivacyProfileError) else "FILE_HOLD_CHECK_UNREADABLE"]


def verify_public_file_hold_omissions(source: str | Path, stage: str | Path,
                                      policy: PublicExportPolicy) -> tuple[frozenset[str], list[str]]:
    """Bind declared omissions independently to the current immutable source."""
    try:
        source, stage = _file_hold_root(source), _file_hold_root(stage)
        if (source == stage or source.is_relative_to(stage) or stage.is_relative_to(source)
                or _file_hold_identity(source.stat())[:2] == _file_hold_identity(stage.stat())[:2]):
            raise PrivacyProfileError("FILE_HOLD_ROOTS_OVERLAP")
        bindings = resolve_public_file_holds(source, policy)
        receipt_path = stage / PUBLIC_FILE_HOLD_RECEIPT
        if not bindings:
            if receipt_path.exists() or receipt_path.is_symlink():
                raise PrivacyProfileError("FILE_HOLD_UNEXPECTED_RECEIPT")
            return frozenset(), []
        if load_public_file_hold_receipt(stage) != public_file_hold_receipt(bindings):
            raise PrivacyProfileError("FILE_HOLD_SOURCE_RECEIPT_MISMATCH")
        for item in bindings:
            path = stage / item.relative_path
            if path.exists() or path.is_symlink():
                raise PrivacyProfileError("FILE_HOLD_OMISSION_NOT_APPLIED")
            # Missing whole parents are not a substitute for the declared single-file hold.
            parent = Path(item.relative_path).parent
            policy_removed_parent = (
                any(part in policy.excluded_root_names for part in parent.parts)
                or any(item.relative_path.startswith(relative + "/")
                       for relative in policy.excluded_relative_paths)
            )
            if (stage / parent).exists() or (stage / parent).is_symlink() or not policy_removed_parent:
                _file_hold_path(stage, parent.as_posix(), directory=True)
        findings = public_file_hold_findings(stage, policy)
        if findings:
            return frozenset(), findings
        return frozenset(item.relative_path for item in bindings), []
    except (OSError, RuntimeError, PrivacyProfileError) as exc:
        return frozenset(), [str(exc) if isinstance(exc, PrivacyProfileError) else "FILE_HOLD_PROOF_UNREADABLE"]


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
