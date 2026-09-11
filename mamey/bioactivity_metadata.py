"""Typed, claim-safe bioactivity metadata admission.

This module owns the portable metadata contract.  It deliberately records
metadata state separately from an observation and from the permitted use of
that record.  It does not score, rank, or attribute an observation to a BGC.
"""

from __future__ import annotations

from copy import deepcopy
import re
from typing import Any, Mapping


SCHEMA_VERSION = "bioactivity_metadata_v1"
METADATA_STATES = frozenset({
    "NOT_SUPPLIED", "SUPPLIED_UNKNOWN", "MEASURED_NEGATIVE", "MEASURED_POSITIVE",
    "BIOACTIVITY_LEGACY_SHAPE_HOLD", "LEGACY_UNTYPED_CONTEXT",
})
OBSERVATION_STATES = frozenset({"NOT_OBSERVED", "UNKNOWN", "NEGATIVE", "POSITIVE"})
USAGE_SCOPES = frozenset({"PRODUCTION", "EXAMPLE_ONLY"})
LEGACY_SHAPE_WHITELIST = {
    "LEGACY-V0-STRING": frozenset(),
    "LEGACY-V0-DICT": frozenset({"status", "targets", "compound_linkage"}),
    "LEGACY-V0-DICT-COMPACT": frozenset({"status", "targets"}),
}
_LOCATOR_PATTERN = re.compile(r"^(?:[A-Za-z][A-Za-z0-9+.-]*://)?[A-Za-z0-9][A-Za-z0-9._/-]*$")


class BioactivityMetadataError(ValueError):
    """Typed, non-biological metadata admission error."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def not_supplied() -> dict[str, Any]:
    """Return a fresh canonical absence-of-metadata object."""
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata_state": "NOT_SUPPLIED",
        "observation_state": "NOT_OBSERVED",
        "usage_scope": "PRODUCTION",
        "assays": [],
        "compound_linkage": "NOT_ESTABLISHED",
        "warnings": [],
    }


def validate_receipt_locator(locator: str) -> str:
    """Validate portability grammar only; privacy policy is a separate gate."""
    if not isinstance(locator, str) or not locator or locator.strip() != locator:
        raise BioactivityMetadataError("BIOACTIVITY_LOCATOR_HOLD", "locator must be a nonempty trimmed string")
    if (locator.startswith(("/", "~", "\\")) or re.match(r"^[A-Za-z]:", locator)
            or ".." in locator.split("/") or any(ord(ch) < 32 for ch in locator)
            or not _LOCATOR_PATTERN.fullmatch(locator)):
        raise BioactivityMetadataError("BIOACTIVITY_LOCATOR_HOLD", "locator is not a portable structural locator")
    return locator


def _assert_keys(value: Mapping[str, Any]) -> None:
    required = {"schema_version", "metadata_state", "observation_state", "usage_scope", "assays", "compound_linkage"}
    allowed = required | {"receipt_locator", "warnings"}
    if not required.issubset(value) or not set(value).issubset(allowed):
        raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", "unrecognized metadata keys")


def _validate_canonical(value: Mapping[str, Any]) -> dict[str, Any]:
    _assert_keys(value)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", "unknown schema version")
    result = deepcopy(dict(value))
    for key, accepted in (("metadata_state", METADATA_STATES), ("observation_state", OBSERVATION_STATES), ("usage_scope", USAGE_SCOPES)):
        if result.get(key) not in accepted:
            raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", f"unknown {key}")
    if not isinstance(result["assays"], list):
        raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", "assays must be a list")
    if result["metadata_state"] == "NOT_SUPPLIED" and result["assays"]:
        raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", "NOT_SUPPLIED cannot carry assays")
    if result["usage_scope"] == "EXAMPLE_ONLY":
        raise BioactivityMetadataError("BIOACTIVITY_EXAMPLE_ONLY_HOLD", "example-only metadata is not admitted to production")
    if result.get("receipt_locator") is not None:
        result["receipt_locator"] = validate_receipt_locator(result["receipt_locator"])
    result.setdefault("warnings", [])
    return result


def _normalize_legacy_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    keys = frozenset(value)
    if keys not in (LEGACY_SHAPE_WHITELIST["LEGACY-V0-DICT"], LEGACY_SHAPE_WHITELIST["LEGACY-V0-DICT-COMPACT"]):
        raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", "legacy dictionary keys are not whitelisted")
    target = value.get("targets", "")
    if not isinstance(target, str):
        raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", "legacy targets must be a string")
    return {
        "schema_version": SCHEMA_VERSION,
        "metadata_state": "LEGACY_UNTYPED_CONTEXT" if target else "NOT_SUPPLIED",
        "observation_state": "UNKNOWN" if target else "NOT_OBSERVED",
        "usage_scope": "PRODUCTION",
        "assays": [{"legacy_targets": target}] if target else [],
        "compound_linkage": "NOT_ESTABLISHED",
        "warnings": ["LEGACY_SHAPE_NORMALIZED"],
    }


def normalize_bioactivity(value: Any = None) -> dict[str, Any]:
    """Normalize only canonical values and three exact legacy shapes.

    Anything else receives the finite legacy-shape hold; no bounded-object
    recovery, key guessing, or named assay default is permitted.
    """
    if value is None:
        return not_supplied()
    if isinstance(value, Mapping) and "schema_version" in value:
        return _validate_canonical(value)
    if isinstance(value, str):
        if value == "":
            result = not_supplied()
            result["warnings"] = ["LEGACY_EMPTY_STRING_NORMALIZED"]
            return result
        return {
            "schema_version": SCHEMA_VERSION,
            "metadata_state": "LEGACY_UNTYPED_CONTEXT",
            "observation_state": "UNKNOWN",
            "usage_scope": "PRODUCTION",
            "assays": [{"legacy_context": value}],
            "compound_linkage": "NOT_ESTABLISHED",
            "warnings": ["LEGACY_SCALAR_NORMALIZED"],
        }
    if isinstance(value, Mapping):
        return _normalize_legacy_dict(value)
    raise BioactivityMetadataError("BIOACTIVITY_LEGACY_SHAPE_HOLD", "unrecognized legacy object")


def display_text(value: Any) -> str:
    """Return claim-safe text for current user-facing consumers."""
    meta = normalize_bioactivity(value)
    state = meta["metadata_state"]
    if state == "NOT_SUPPLIED":
        return "Bioactivity metadata was not supplied; no assay target or outcome is assumed."
    if state == "LEGACY_UNTYPED_CONTEXT":
        return "Legacy bioactivity context is retained without an admitted observation or BGC linkage."
    return f"Bioactivity metadata state: {state}; observations remain strain-level context only."

