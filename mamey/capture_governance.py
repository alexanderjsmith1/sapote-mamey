"""Bounded invocation-local exclusions; JSON receipts store digests, never capabilities."""
from dataclasses import dataclass
import hashlib
import json
import os
import warnings

from .intake_session import CapturedIntakeHold, encode


@dataclass(frozen=True)
class GovernanceCapture:
    _payload: bytes
    _binding: bytes
    _strict_error: str | None

    def binding(self):
        return json.loads(self._binding)

    def read(self, *, strict=False):
        if strict and self._strict_error:
            raise ValueError(self._strict_error)
        if not strict and self._strict_error:
            warnings.warn("Captured exclusions: " + self._strict_error +
                          "; non-strict access uses the recorded selected value.",
                          RuntimeWarning, stacklevel=2)
        data = json.loads(self._payload)
        if strict:
            ids = data.get("hard_excluded")
            if not isinstance(ids, list) or any(not isinstance(value, str) or not value.strip()
                    or value != value.strip() for value in ids):
                raise ValueError("hard_excluded must be a list of non-empty strain identifiers")
        # Each accessor gets its own mapping; no shared mutable configuration is returned.
        return data


def capture(maximum):
    from . import exclusions
    candidates = exclusions._candidate_json_paths()
    probes = []
    default = encode(exclusions._DEFAULT)
    if len(default) > maximum:
        raise CapturedIntakeHold("CAPTURED_GOVERNANCE_BYTE_BUDGET")
    strict_error = None
    for path in candidates:
        row = {"path": str(path.absolute()), "state": "MISSING", "sha256": None, "bytes": None}
        if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise CapturedIntakeHold("CAPTURED_GOVERNANCE_PATH_REFUSED")
        if path.is_file():
            try:
                with path.open("rb") as stream:
                    payload = stream.read(maximum + 1)
            except OSError as exc:
                row.update(state="READ_FAILED", error_type=type(exc).__name__)
                strict_error = "exclusion source is unreadable or malformed"
            else:
                if len(payload) > maximum:
                    raise CapturedIntakeHold("CAPTURED_GOVERNANCE_BYTE_BUDGET")
                row.update(sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))
                try:
                    data = json.loads(payload)
                except (UnicodeError, ValueError):
                    row["state"] = "PARSE_FAILED"
                    strict_error = "exclusion source is unreadable or malformed"
                else:
                    if isinstance(data, dict):
                        row["state"] = "JSON_OBJECT"
                        probes.append(row)
                        metadata = {"schema": "sapote.captured-exclusions.v1", "state": "FILE_CAPTURED",
                                    "selected": row, "probes": probes,
                                    "default_sha256": hashlib.sha256(default).hexdigest(), "strict_error": strict_error}
                        return GovernanceCapture(payload, encode(metadata), strict_error)
                    row["state"] = "NON_OBJECT"
                    strict_error = "exclusion source is unreadable or malformed"
        elif path.exists():
            row["state"] = "NOT_REGULAR"
            strict_error = "bound exclusion source is missing"
        probes.append(row)
    if strict_error is None and (os.environ.get("MAMEY_OFFICIAL_DATA") or os.environ.get("MAMEY_DATA_ROOT")
                                or any(path.parent.is_dir() for path in candidates)):
        strict_error = "bound exclusion source is missing"
    metadata = {"schema": "sapote.captured-exclusions.v1", "state": "MODULE_DEFAULT",
                "selected": None, "probes": probes, "default_sha256": hashlib.sha256(default).hexdigest(),
                "strict_error": strict_error}
    return GovernanceCapture(default, encode(metadata), strict_error)
