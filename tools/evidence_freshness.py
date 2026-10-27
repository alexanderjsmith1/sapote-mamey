#!/usr/bin/env python3
"""Read-only, explicit-file byte freshness and declared dependency audit.

This adapter never refreshes expected hashes or marks Mode B evidence CURRENT.
Dependencies are operator declarations, not independently proved consumption.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = "sapote-mamey.evidence-freshness.v1"
UNITS = {"artifact", "locus", "gene", "strain", "run", "cohort"}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def bounded_digest(path, limit):
    """Hash at most limit payload bytes from one selected descriptor."""
    h, used = hashlib.sha256(), 0
    with Path(path).open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if stat.S_ISREG(opened.st_mode) and opened.st_size <= limit:
            while used < limit:
                block = stream.read(min(1024 * 1024, limit - used))
                if not block:
                    break
                h.update(block)
                used += len(block)
        ended = os.fstat(stream.fileno())
    return h.hexdigest(), used, opened, ended


def stat_signature(observation):
    return (observation.st_dev, observation.st_ino, observation.st_size,
            observation.st_mtime_ns, observation.st_ctime_ns)


def identity_owner(bundle):
    """Load only the existing stdlib identity owner; no package startup/import."""
    path = Path(bundle).resolve() / "mamey" / "exact_identity.py"
    spec = importlib.util.spec_from_file_location("_freshness_identity_owner", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # required by dataclass annotation lookup
    source_bytes = path.read_bytes()
    # Execute the inspected owner directly rather than SourceFileLoader's cache-writing
    # path; read-only behavior must not depend on an environment flag from the caller.
    exec(compile(source_bytes, str(path), "exec"), module.__dict__)
    return module, {"path": str(path), "sha256": hashlib.sha256(source_bytes).hexdigest()}


def audit(manifest, base, *, bundle=None, max_file_bytes=20_000_000,
          max_total_bytes=100_000_000):
    """Audit listed files only. Hold states do not mutate any source or baseline."""
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported manifest schema")
    if any(type(value) is not int or value < 1 for value in (max_file_bytes, max_total_bytes)):
        raise ValueError("byte budgets must be positive integers")
    items = manifest.get("artifacts")
    if not isinstance(items, list) or not items:
        raise ValueError("artifacts must be a nonempty explicit list")
    nodes = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            raise ValueError("every artifact requires a nonblank id")
        if item["id"] in nodes:
            raise ValueError("duplicate artifact id")
        if not isinstance(item.get("path"), str) or not item["path"].strip():
            raise ValueError("every artifact requires an explicit path")
        if item.get("unit") not in UNITS:
            raise ValueError("unit must be explicit and admitted")
        expected = item.get("sha256", "")
        if not isinstance(expected, str) or (expected and not re.fullmatch(r"[0-9a-fA-F]{64}", expected)):
            raise ValueError("sha256 must be empty or 64 hex digits")
        deps = item.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps) or len(set(deps)) != len(deps):
            raise ValueError("depends_on must be an explicit list without duplicates")
        nodes[item["id"]] = item
    order, visiting, visited = [], set(), set()

    def visit(key):
        if key not in nodes:
            raise ValueError("unknown dependency id")
        if key in visiting:
            raise ValueError("dependency cycle")
        if key in visited:
            return
        visiting.add(key)
        for dep in nodes[key]["depends_on"]:
            visit(dep)
        visiting.remove(key)
        visited.add(key)
        order.append(key)

    for key in nodes:
        visit(key)
    owner, owner_binding = identity_owner(bundle) if bundle else (None, None)
    result, cache, total = {}, {}, 0
    for key in order:
        item = nodes[key]
        path = Path(item["path"])
        path = path if path.is_absolute() else Path(base) / path
        row = {"id": key, "path": str(path.absolute()), "resolved_path": str(path.resolve()), "expected_sha256": item.get("sha256", "").lower(),
               "source_revision": item.get("source_revision", ""), "unit": item["unit"],
               "identity": item.get("identity"), "depends_on": item["depends_on"],
               "observed_sha256": "", "bytes": None, "read_bytes": 0}
        row["identity_state"] = "NOT_LOCUS_SCOPED"
        if item.get("identity") is not None or item["unit"] in {"locus", "gene"}:
            if owner is None:
                row["identity_state"] = "UNVERIFIED_OWNER_NOT_SELECTED"
            else:
                ident = item.get("identity")
                if not isinstance(ident, dict):
                    row["identity_state"] = "IDENTITY_HOLD"
                else:
                    try:
                        row["exact_locus"] = owner.exact_locus_from_mapping(ident.get("strain"), ident)
                        row["identity_state"] = "VALIDATED_BY_NATIVE_DISPLAY_OWNER"
                    except owner.ExactLocusIdentityError:
                        row["identity_state"] = "IDENTITY_HOLD"
        try:
            st = path.stat()
            if not stat.S_ISREG(st.st_mode):
                row["direct_state"] = "NOT_REGULAR_FILE"
            elif st.st_size > max_file_bytes:
                row["direct_state"] = "UNVERIFIED_FILE_BUDGET"
                row["bytes"] = st.st_size
            else:
                row["bytes"] = st.st_size
                cache_key = str(path.resolve())
                if cache_key not in cache:
                    if total + st.st_size > max_total_bytes:
                        row["direct_state"] = "UNVERIFIED_TOTAL_BUDGET"
                    else:
                        remaining = max_total_bytes - total
                        observed, used, opened, ended = bounded_digest(path, min(max_file_bytes, remaining))
                        row["read_bytes"] = used
                        row["bytes"] = ended.st_size
                        total += used
                        # Common-change detection is not an immutable snapshot guarantee.
                        after = path.stat()
                        if not stat.S_ISREG(opened.st_mode):
                            row["direct_state"] = "NOT_REGULAR_FILE"
                        elif max(opened.st_size, ended.st_size) > max_file_bytes:
                            row["direct_state"] = "UNVERIFIED_FILE_BUDGET"
                        elif max(opened.st_size, ended.st_size) > remaining:
                            row["direct_state"] = "UNVERIFIED_TOTAL_BUDGET"
                        elif (stat_signature(st) != stat_signature(opened)
                              or stat_signature(opened) != stat_signature(ended)
                              or stat_signature(ended) != stat_signature(after)
                              or ended.st_size != used):
                            row["direct_state"] = "UNVERIFIED_CHANGED_DURING_READ"
                        else:
                            cache[cache_key] = (observed, stat_signature(ended))
                if cache_key in cache:
                    observed, fingerprint = cache[cache_key]
                    if stat_signature(st) != fingerprint:
                        row["direct_state"] = "UNVERIFIED_CHANGED_SINCE_HASH"
                    else:
                        row["observed_sha256"] = observed
                        row["direct_state"] = ("UNVERIFIED_BASELINE" if not row["expected_sha256"] else
                            "HASH_MATCH" if row["observed_sha256"] == row["expected_sha256"] else "CHANGED")
        except FileNotFoundError:
            row["direct_state"] = "MISSING_FILE"
        except OSError as exc:
            row["direct_state"] = "UNREADABLE_FILE"
            row["error_type"] = type(exc).__name__
        row["metadata_state"] = "DECLARED" if isinstance(row["source_revision"], str) and row["source_revision"].strip() else "UNVERIFIED_REVISION"
        row["blocking_ancestors"] = sorted({x for dep in item["depends_on"] for x in
            ([dep] if result[dep]["state"] != "CURRENT_BYTES" else []) + result[dep]["blocking_ancestors"]})
        if row["direct_state"] != "HASH_MATCH":
            row["state"] = "HOLD_DIRECT"
        elif row["metadata_state"] != "DECLARED" or row["identity_state"] in {"IDENTITY_HOLD", "UNVERIFIED_OWNER_NOT_SELECTED"}:
            row["state"] = "HOLD_METADATA"
        elif row["blocking_ancestors"]:
            row["state"] = "INVALIDATED_DEPENDENCY"
        else:
            row["state"] = "CURRENT_BYTES"
        result[key] = row
    rows = [result[key] for key in nodes]
    return {"schema": SCHEMA, "status": "PASS_BYTES_AND_DECLARED_DEPENDENCIES" if all(r["state"] == "CURRENT_BYTES" for r in rows) else "HOLD",
            "artifacts": rows, "counts": dict(Counter(r["state"] for r in rows)),
            "hashed_bytes": total, "identity_owner": owner_binding,
            "budget_scope": "Actual listed-artifact payload bytes read/hashed, including discarded attempts; excludes manifest and identity-owner code reads.",
            "claim_ceiling": "Listed byte pins and declared dependencies only; no scientific freshness, actual-consumption proof, complete roster, sequence binding, release or adoption."}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--bundle", type=Path, help="Read the native exact-identity owner for locus/gene metadata")
    ap.add_argument("--max-file-bytes", type=int, default=20_000_000)
    ap.add_argument("--max-total-bytes", type=int, default=100_000_000)
    args = ap.parse_args(argv)
    if args.max_file_bytes < 1 or args.max_total_bytes < 1:
        ap.error("byte budgets must be positive")
    try:
        manifest_bytes = args.manifest.read_bytes()
        manifest = json.loads(manifest_bytes)
        result = audit(manifest, args.manifest.resolve().parent, bundle=args.bundle,
                       max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes)
        result["manifest"] = {"path": str(args.manifest.resolve()), "sha256": hashlib.sha256(manifest_bytes).hexdigest()}
    except (ValueError, OSError, TypeError, AttributeError) as exc:
        print(json.dumps({"schema": SCHEMA, "status": "INVALID_INPUT", "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "PASS_BYTES_AND_DECLARED_DEPENDENCIES" else 1


if __name__ == "__main__":
    raise SystemExit(main())
