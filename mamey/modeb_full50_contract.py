"""Resolve and identify the canonical 50-section Mode-B contract.

Four modules in this bundle refuse to run unless handed a contract carrying exactly
sections 1..50: :mod:`mamey.evidence_disagreements`,
:mod:`mamey.cohort_enzyme_neighborhoods`, :mod:`mamey.structured_domain_motif_extension`
and ``tools/cohort_tailoring/build_atlas.py``.  Three of them obtain the requirement text by
regex-parsing markdown table rows out of a file **whose path the operator supplies at run
time**, pinned by a sha256 that the *same* configuration supplies.

That pin is self-certifying: it proves the file has not changed since the config was
written, not *which* contract it is.  Any markdown table with fifty rows numbered 1..50
satisfies every existing check.

This module does not change that, and deliberately so.  The consumers are contract-agnostic
by design -- several test fixtures drive them with generic synthetic contracts
("Generic fixture requirement 7") to exercise the plumbing without asserting scientific
content.  Forcing canonical identity inside the library would break those fixtures and
would confuse "this run used the project's contract" with "this module works".

What was missing is the ability to *tell the difference*.  ``identify()`` answers that in one
call, so a caller that cares can record which contract a run actually bound.

Nothing here admits evidence or makes a biological claim.  A section requirement is a scope
statement for what a Mode-B section must address; judgment deferred.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

__all__ = [
    "CONTRACT_PATH",
    "ROW",
    "SECTION_NUMBERS",
    "canonical_contract",
    "canonical_requirements",
    "canonical_sha256",
    "parse_requirements",
    "identify",
    "CANONICAL",
    "NON_CANONICAL",
    "MALFORMED",
]

CONTRACT_PATH = Path(__file__).resolve().parent / "data" / "mode_b" / "modeb_full50_contract.json"

#: The exact expression the consumers use.  Copied deliberately: if the engine's parse
#: changes, the guards over this module must fail rather than quietly diverge.
ROW = re.compile(r'^\| (\d+) \| (.*?) \|$', re.M)

SECTION_NUMBERS = frozenset(range(1, 51))

CANONICAL = "CANONICAL"
NON_CANONICAL = "NON_CANONICAL"
MALFORMED = "MALFORMED"


def canonical_contract() -> dict:
    """The frozen contract object shipped in this bundle."""
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def canonical_requirements() -> dict[int, str]:
    """``{section_number: requirement}`` for the fifty canonical sections."""
    return {s["section_number"]: s["requirement"] for s in canonical_contract()["sections"]}


def canonical_sha256() -> str:
    """sha256 of the source document the canonical rows were copied from.

    This is the hash of ``docs/MODEB_50_SECTION_CONTRACT_CANDIDATE.md`` recorded at freeze
    time -- not the hash of the JSON artifact itself.
    """
    return canonical_contract()["source_document"]["sha256"]


def parse_requirements(text: str) -> dict[int, str]:
    """Parse contract text exactly as the consumers do."""
    return {int(n): v.strip() for n, v in ROW.findall(text)}


def identify(requirements: dict[int, str] | str) -> dict:
    """Classify a contract against the canonical one.

    Accepts either raw contract text or an already-parsed mapping.  Returns a dict with:

    ``state``
        ``CANONICAL`` (shape and every requirement match), ``NON_CANONICAL`` (correct
        1..50 shape, but at least one requirement differs) or ``MALFORMED`` (not 1..50).
    ``canonical_source_sha256``
        the recorded source-document hash, for the caller's receipt.
    ``differing_sections``
        sorted section numbers whose text differs; empty unless ``NON_CANONICAL``.
    ``missing`` / ``unexpected``
        sorted section numbers, populated only when ``MALFORMED``.

    This never raises on contract content and never blocks a run.  It reports.  A caller
    that wants to refuse a non-canonical contract can do so on the returned ``state``,
    which keeps that policy at the call site where it belongs.
    """
    parsed = parse_requirements(requirements) if isinstance(requirements, str) else dict(requirements)
    canon = canonical_requirements()
    out = {
        "canonical_source_sha256": canonical_sha256(),
        "differing_sections": [],
        "missing": [],
        "unexpected": [],
    }
    present = set(parsed)
    if present != SECTION_NUMBERS:
        out["state"] = MALFORMED
        out["missing"] = sorted(SECTION_NUMBERS - present)
        out["unexpected"] = sorted(present - SECTION_NUMBERS)
        return out
    differing = sorted(n for n in SECTION_NUMBERS if parsed[n] != canon[n])
    out["state"] = CANONICAL if not differing else NON_CANONICAL
    out["differing_sections"] = differing
    return out


def digest(path: Path | str) -> str:
    """sha256 of a file, for callers recording which contract they bound."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
