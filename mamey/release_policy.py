"""Local release decisions and read-only cohort privacy admission.

Release metadata is not permission to distribute a software/data archive.
Identifier spelling never supplies public authority.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

POLICY_VERSION = "sapote_release_policy_v1"


@dataclass(frozen=True)
class ReleaseDecision:
    strain_id: str
    release: str = "PRIVATE"
    privacy_tier: str = "PRIVATE_DEFAULT"
    assignment_state: str = "DEFAULT"
    reason: str = "no_public_authority"
    authority_sha256: str = ""
    refused: bool = False
    policy_version: str = POLICY_VERSION

    def __post_init__(self):
        if not str(self.strain_id).strip() or self.release not in {"PUBLIC", "PRIVATE"}:
            raise ValueError("RELEASE_DECISION_INVALID")
        if self.refused and self.release != "PRIVATE":
            raise ValueError("RELEASE_DECISION_REFUSAL_CONFLICT")

    def to_dict(self):
        return asdict(self)


def load_bound_profile(path):
    """Read a profile without allowing a changed file to acquire the old digest."""
    from .privacy_profile import PrivacyProfileError, load_privacy_profile
    source = Path(path)
    before = source.read_bytes()
    profile = load_privacy_profile(source)
    if source.read_bytes() != before:
        raise PrivacyProfileError("PRIVACY_PROFILE_CHANGED_DURING_READ")
    return profile, hashlib.sha256(before).hexdigest()


def resolve_run_release(strain_id, override=None, privacy_profile=None):
    """Keep omission distinct from PRIVATE so exact public profiles remain usable."""
    from .dedup_and_guard import resolve_release
    if privacy_profile:
        from .privacy_profile import resolve_profile_privacy
        profile, digest = load_bound_profile(privacy_profile)
        result = resolve_profile_privacy(strain_id, profile, override=override)
        return ReleaseDecision(
            str(strain_id), result.release, result.tier_id,
            result.assignment_state, result.reason, digest,
            result.reason == "public_override_refused_by_profile",
        )
    release, refused = resolve_release(strain_id, override)
    requested = str(override or "").strip().upper()
    reason = ("public_override_refused_by_guard" if refused else
              "operator_public_override" if requested == "PUBLIC" else
              "operator_private_override" if requested == "PRIVATE" else
              "no_public_authority")
    return ReleaseDecision(str(strain_id), release, "OPERATOR" if requested else "PRIVATE_DEFAULT",
                           "EXPLICIT" if requested else "DEFAULT", reason, refused=refused)


def package_release_policy(package, fallback_id, *, profile=None, profile_sha256=""):
    """Read privacy metadata before opening a cohort's scientific payload.

    Preserve recorded legacy labels; they do not authorize a new public figure.
    Folder names may be display aliases and are never exact public assignments.
    Returned holds contain reason codes, not private input values.
    """
    package = Path(package)
    sources = [package / "manifest.json", package / "manifest_short.json"]
    sources.extend(sorted(package.glob("*_1_intake.json")))
    records, errors = [], []
    for path in sources:
        if not path.exists():
            continue
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("not an object")
        except (OSError, ValueError):
            errors.append("privacy_metadata_unreadable")
            continue
        records.append(value)
    return resolve_package_privacy_records(records, fallback_id, profile=profile,
                                           profile_sha256=profile_sha256, unreadable=bool(errors))


def resolve_package_privacy_records(records, fallback_id, *, profile=None,
                                    profile_sha256="", unreadable=False):
    """Same admission for directory readers and immutable ZIP-backed readers."""
    identities = {str(r["strain_id"]) for r in records if r.get("strain_id")}
    releases = {str(r["release"]).strip().upper() for r in records if r.get("release")}
    exact_id = next(iter(identities)) if len(identities) == 1 else None
    recorded = next(iter(releases)) if len(releases) == 1 else "UNRESOLVED"
    result = {"strain_id": exact_id or str(fallback_id), "recorded_release": recorded,
              "effective_release": "PRIVATE", "privacy_reason": "missing_release_authority",
              "privacy_assignment_state": "HOLD", "authority_sha256": profile_sha256}
    if unreadable:
        result["privacy_reason"] = "privacy_metadata_unreadable"
        return result
    if len(identities) != 1:
        result["privacy_reason"] = "identity_conflict" if identities else "identity_not_recorded"
        return result
    if len(releases) != 1 or recorded not in {"PRIVATE", "PUBLIC"}:
        result["privacy_reason"] = "release_conflict" if releases else "release_not_recorded"
        return result
    if recorded == "PRIVATE":
        result.update(privacy_reason="recorded_private", privacy_assignment_state="RECORDED")
        return result
    decisions = [r["release_decision"] for r in records if r.get("release_decision") is not None]
    if any(not isinstance(d, dict) for d in decisions):
        result["privacy_reason"] = "release_decision_invalid"
        return result
    if decisions and len({json.dumps(d, sort_keys=True) for d in decisions}) != 1:
        result["privacy_reason"] = "release_decision_conflict"
        return result
    if decisions:
        decision = decisions[0]
        if (decision.get("strain_id") != exact_id or decision.get("release") != recorded
                or decision.get("refused") is True):
            result["privacy_reason"] = "release_decision_conflict"
            return result
    if profile is not None:
        from .privacy_profile import resolve_profile_privacy
        resolved = resolve_profile_privacy(exact_id, profile)
        result.update(effective_release=resolved.release, privacy_reason=resolved.reason,
                      privacy_assignment_state=resolved.assignment_state)
        return result
    if decisions:
        decision = decisions[0]
        reason = decision.get("reason")
        authorized = reason == "operator_public_override" or (
            reason == "exact_public_assignment"
            and isinstance(decision.get("authority_sha256"), str)
            and len(decision["authority_sha256"]) == 64
            and all(c in "0123456789abcdef" for c in decision["authority_sha256"])
        )
        if decision.get("policy_version") == POLICY_VERSION and authorized and decision.get("refused") is False:
            result.update(effective_release="PUBLIC", privacy_reason=reason,
                          privacy_assignment_state=decision.get("assignment_state", "EXPLICIT"),
                          authority_sha256=decision.get("authority_sha256", ""))
            return result
    result["privacy_reason"] = "legacy_public_requires_exact_authority"
    return result
