#!/usr/bin/env python3
"""check_registry_ids_unique.py — fail if registry inventory IDs collide.

A duplicate registry ID is not harmless: dict keyed loaders silently overwrite one
entry. This gate catches the MMK-CCTT-015 class before release.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, collections, csv, json, sys
from pathlib import Path


def _ids(path: Path) -> list[str]:
    # Fail-closed (v9.7.374): an unrecognized extension, a missing file, or a CSV with no `id`
    # column used to fall through to `return []` here -- indistinguishable downstream from "this
    # registry legitimately has zero entries." main() then printed "registry IDs unique (0 IDs)"
    # and exited 0, silently reporting PASS on a file this gate never actually parsed. Raise
    # instead, so main() can turn it into a loud, exit-1 finding.
    if not path.is_file():
        raise FileNotFoundError(f"registry file not found: {path}")
    if path.suffix.lower() == ".json":
        d = json.loads(path.read_text(encoding="utf-8"))
        entries = d if isinstance(d, list) else d.get("entries", d.get("inventory", []))
        return [e.get("id") for e in entries if isinstance(e, dict) and e.get("id")]
    if path.suffix.lower() == ".csv":
        # v97395 fix: schema was checked via `rows[0]`, so a CSV with zero DATA rows never had
        # its columns checked at all -- regardless of whether it had a real header. A completely
        # empty (0-byte) file reproduced the exact silent "return [] -> main() prints 0 IDs,
        # exit 0" shape the v9.7.374 fix above was written to eliminate, one edge case later.
        # `reader.fieldnames` reflects the header (or None for an unparsed/empty file)
        # independent of row count, so use it instead of the first data row.
        reader = csv.DictReader(path.open(encoding="utf-8"))
        rows = list(reader)
        if reader.fieldnames is None:
            raise ValueError(f"{path}: CSV has no header row (empty or unreadable file)")
        if "id" not in reader.fieldnames:
            raise ValueError(f"{path}: CSV has no 'id' column (columns: {list(reader.fieldnames)})")
        return [r.get("id") for r in rows if r.get("id")]
    raise ValueError(f"{path}: unsupported registry format {path.suffix!r} (expected .json or .csv)")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", default=["bundle_support/registry_inventory_v1.9.4.json"])
    ns = ap.parse_args(argv)
    failed = False
    for name in ns.paths:
        path = Path(name)
        try:
            ids = _ids(path)
        except Exception as e:
            failed = True
            emit(f"REGISTRY CHECK ERROR for {path}: {e}")
            continue
        dup = {k: v for k, v in collections.Counter(ids).items() if v > 1}
        if dup:
            failed = True
            emit(f"REGISTRY ID DUPLICATES in {path}: {dup}")
        else:
            emit(f"registry IDs unique: {path} ({len(ids)} IDs)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
