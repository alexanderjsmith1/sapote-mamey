#!/usr/bin/env python3
"""zip_hygiene_allowlist.py — a checksum/path-bound allowlist for intentionally-large shipped files. Generic.

The ZIP-size hygiene gate rejects files over a limit (default 5 MB). Some files are legitimately large and
must ship (e.g. a reference corpus). Rather than disable the gate (which then catches nothing), an oversized
file passes ONLY if it is explicitly allowlisted by path, under a declared per-file ceiling, with a reason.
Everything else over the limit still FAILS. This keeps the gate meaningful while permitting known exceptions.

Allowlist file `zip_hygiene_allowlist.tsv`:  relpath \t max_bytes \t reason
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys, pathlib

DEFAULT_LIMIT = 5 * 1024 * 1024  # 5 MB

def load_allowlist(path):
    allow = {}
    p = pathlib.Path(path)
    if not p.exists():
        return allow
    for ln in p.read_text().splitlines():
        if ln.startswith("#") or not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) >= 3:
            allow[parts[0].strip()] = (int(parts[1]), parts[2].strip())
    return allow

def check_oversized(relpath, size_bytes, allow, limit=DEFAULT_LIMIT):
    """Return (ok, reason). ok=True if within limit, or allowlisted under its declared ceiling."""
    if size_bytes <= limit:
        return True, "within limit"
    if relpath in allow:
        ceil, reason = allow[relpath]
        if size_bytes <= ceil:
            return True, f"allowlisted: {reason}"
        return False, f"allowlisted ceiling {ceil} exceeded by {size_bytes}"
    return False, f"{size_bytes} > limit {limit} and not allowlisted"

def main():
    # CLI: scan a dir tree, report oversized non-allowlisted files (exit 2 if any)
    if len(sys.argv) < 2:
        sys.exit("usage: zip_hygiene_allowlist.py <tree_dir> [allowlist.tsv]")
    tree = pathlib.Path(sys.argv[1])
    allow = load_allowlist(sys.argv[2] if len(sys.argv) > 2 else tree / "zip_hygiene_allowlist.tsv")
    bad = []
    for f in tree.rglob("*"):
        if f.is_file():
            rel = "./" + str(f.relative_to(tree))
            ok, why = check_oversized(rel, f.stat().st_size, allow)
            if not ok:
                bad.append((rel, f.stat().st_size, why))
    for rel, sz, why in bad:
        emit(f"OVERSIZED\t{sz}\t{rel}\t{why}")
    emit(f"== {len(bad)} oversized non-allowlisted file(s) ==")
    sys.exit(2 if bad else 0)

if __name__ == "__main__":
    main()
