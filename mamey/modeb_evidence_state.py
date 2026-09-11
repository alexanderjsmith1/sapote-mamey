"""Executable lifecycle for externally escalated Mode B evidence.

The state describes admission into a Mode B card, not whether a search was
requested or a file merely exists. Query emission therefore remains UNBOUND.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

EVIDENCE_STATES = frozenset({
    "UNBOUND", "CONTEXT_ONLY", "ADMITTED", "ABSENT_IN_SCOPE", "SUPERSEDED",
})

_ALLOWED = {
    "UNBOUND": frozenset({"UNBOUND", "CONTEXT_ONLY", "ADMITTED", "ABSENT_IN_SCOPE", "SUPERSEDED"}),
    "CONTEXT_ONLY": frozenset({"CONTEXT_ONLY", "ADMITTED", "SUPERSEDED"}),
    "ADMITTED": frozenset({"ADMITTED", "SUPERSEDED"}),
    "ABSENT_IN_SCOPE": frozenset({"ABSENT_IN_SCOPE", "SUPERSEDED"}),
    "SUPERSEDED": frozenset({"SUPERSEDED"}),
}
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class EvidenceTransitionError(ValueError):
    """Typed fail-closed rejection of an illegal or unbound transition."""

    code = "MODEB_EVIDENCE_TRANSITION_INVALID"


@dataclass(frozen=True)
class EvidenceTransition:
    previous_state: str
    current_state: str
    reason: str
    source_locator: str = ""
    source_sha256: str = ""
    replacement_id: str = ""

    def as_dict(self) -> dict:
        return {"schema_version": "modeb-evidence-transition-1.0", **asdict(self)}


def transition_evidence(current: str, target: str, *, reason: str,
                        source_locator: str = "", source_sha256: str = "",
                        replacement_id: str = "") -> EvidenceTransition:
    """Validate and return one evidence transition; never mutates its source.

    Evidence-bearing states require an immutable source binding. Terminal or
    scope states require a reason. Supersession also requires a replacement or
    withdrawal identifier so disappearance cannot be silent.
    """
    current, target = str(current).upper(), str(target).upper()
    if current not in EVIDENCE_STATES or target not in EVIDENCE_STATES:
        raise EvidenceTransitionError(f"unknown evidence state: {current!r} -> {target!r}")
    if target not in _ALLOWED[current]:
        raise EvidenceTransitionError(f"illegal evidence transition: {current} -> {target}")
    reason = str(reason).strip()
    if not reason:
        raise EvidenceTransitionError("every evidence transition requires a reason")
    source_locator = str(source_locator).strip()
    source_sha256 = str(source_sha256).strip().lower()
    if target in {"CONTEXT_ONLY", "ADMITTED"}:
        if not source_locator or not _SHA256.fullmatch(source_sha256):
            raise EvidenceTransitionError(
                f"{target} requires source_locator and lowercase SHA-256 binding")
    replacement_id = str(replacement_id).strip()
    if target == "SUPERSEDED" and not replacement_id:
        raise EvidenceTransitionError("SUPERSEDED requires replacement_id or withdrawal identifier")
    return EvidenceTransition(current, target, reason, source_locator,
                              source_sha256, replacement_id)
