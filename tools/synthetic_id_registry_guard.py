"""Verify declared test identities against an explicitly bound local metadata registry.

No registry is inferred, copied, or treated as a public/private classification.
CLI output is aggregate/redacted. A portable fixture proves logic only; a clean
snapshot audit does not certify absence from later or unregistered subjects.
CLI contract: one redacted JSON audit record on stderr through standard logging;
stdout remains empty. Exit 0 is a bound-snapshot pass, 1 failure, 2 hold/refusal.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
from pathlib import Path
import re
import sys

_CANONICAL = re.compile(r"(?:AS|AJS)-[0-9]+|PENDING-[A-Z0-9]+")
_REGISTRY_TOKEN = re.compile(
    r"(?<![A-Za-z0-9])(?:AS|AJS)[-_ ]?[0-9]+|"
    r"(?<![A-Za-z0-9])PENDING[-_ ]?[A-Za-z0-9]+", re.I)
_COLUMNS = {"basename", "path", "strain", "strain_id", "id", "sid", "sample_id"}
# These exact existing reference names are a separate disclosure class. Neither
# may be used to declare a synthetic strain or grant a new privacy exemption.
_PUBLIC_REFERENCE_KEYS = {("AS", "48"), ("AJS", "327")}
_MAX_BYTES = 16 * 1024 * 1024


def identity_key(value):
    """Conservative ASCII alias key: dashless/case/zero-padding cannot hide a collision."""
    value = value.upper().replace("_", "-").replace(" ", "")
    match = re.fullmatch(r"(AS|AJS)-?([0-9]+)", value)
    if match:
        return match[1], match[2].lstrip("0") or "0"
    pending = re.fullmatch(r"PENDING-?([A-Z0-9]+)", value)
    if pending:
        return "PENDING", pending[1]
    return (value,)


def _read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > _MAX_BYTES:
        raise ValueError("input must be a bounded regular metadata file")
    return path.read_bytes()


def audit(allowlist, registry=None):
    result = {"schema": "sapote.synthetic-registry-audit.v1", "state": "HOLD",
              "certification_scope": "explicit metadata snapshot only; no disclosure permission",
              "registry_bound": registry is not None, "collisions": [], "issues": []}
    try:
        raw = _read(allowlist)
        result["allowlist_sha256"] = hashlib.sha256(raw).hexdigest()
        entries = [(line_number, line.strip()) for line_number, line in
                   enumerate(raw.decode("utf-8").splitlines(), 1)
                   if line.strip() and not line.lstrip().startswith("#")]
    except (OSError, ValueError, UnicodeError):
        result["issues"].append("ALLOWLIST_UNREADABLE_OR_INVALID")
        return result
    result["entry_count"] = len(entries)
    if not entries:
        result["issues"].append("ALLOWLIST_EMPTY")
    seen, seen_keys = set(), set()
    for line_number, token in entries:
        if not _CANONICAL.fullmatch(token):
            result["issues"].append("ALLOWLIST_NONCANONICAL")
        if token in seen:
            result["issues"].append("ALLOWLIST_DUPLICATE")
        seen.add(token)
        if identity_key(token) in seen_keys:
            result["issues"].append("ALLOWLIST_NORMALIZED_ALIAS_DUPLICATE")
        seen_keys.add(identity_key(token))
        if identity_key(token) in _PUBLIC_REFERENCE_KEYS:
            result["issues"].append("PUBLIC_REFERENCE_IS_NOT_A_SYNTHETIC_STRAIN")
    if registry is None:
        result["issues"].append("REGISTRY_UNBOUND")
        return result
    try:
        raw = _read(registry)
        result["registry_sha256"] = hashlib.sha256(raw).hexdigest()
        # Read only identity/locator metadata, never a referenced genome or path.
        reader = csv.DictReader(raw.decode("utf-8").splitlines(), delimiter="\t")
        fields = reader.fieldnames or []
        if len(set(fields)) != len(fields):
            raise ValueError("duplicate metadata columns")
        columns = [name for name in fields if name.strip().lower() in _COLUMNS]
        if not columns:
            raise ValueError("identity metadata columns absent")
        registry_keys, row_count = set(), 0
        for row in reader:
            row_count += 1
            if None in row or any(row.get(column) is None for column in columns):
                raise ValueError("malformed metadata row")
            for column in columns:
                registry_keys.update(identity_key(match[0]) for match in
                                     _REGISTRY_TOKEN.finditer(row[column]))
        result.update(registry_rows=row_count, registry_identity_count=len(registry_keys))
        if not row_count or not registry_keys:
            result["issues"].append("REGISTRY_EMPTY_OR_NO_IDENTITIES")
            return result
    except (OSError, ValueError, UnicodeError, csv.Error):
        result["issues"].append("REGISTRY_UNREADABLE_OR_INVALID")
        return result
    for line_number, token in entries:
        if identity_key(token) in registry_keys:
            result["collisions"].append({"allowlist_line": line_number,
                                         "identity_sha256": hashlib.sha256(token.encode()).hexdigest(),
                                         "identifier": token})
    if result["collisions"]:
        result["issues"].append("DECLARED_SYNTHETIC_ID_OCCURS_IN_REGISTRY")
    result["state"] = "FAIL" if result["issues"] else "PASS_BOUND_SNAPSHOT"
    return result


def redacted_result(result):
    """The default CLI/report never echoes a matched identity or registry locator."""
    public = dict(result)
    public["collision_count"] = len(public.pop("collisions"))
    return public


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowlist", required=True, type=Path)
    parser.add_argument("--registry", type=Path,
                        help="Explicit local TSV metadata snapshot; never inferred or copied")
    args = parser.parse_args(argv)
    result = audit(args.allowlist, args.registry)
    logger = logging.Logger("sapote.synthetic_id_registry_guard", level=logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    try:
        logger.info(json.dumps(redacted_result(result), sort_keys=True))
    finally:
        handler.close()
    return 0 if result["state"] == "PASS_BOUND_SNAPSHOT" else 2 if result["state"] == "HOLD" else 1


if __name__ == "__main__":
    raise SystemExit(main())
