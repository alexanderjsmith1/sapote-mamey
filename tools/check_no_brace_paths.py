#!/usr/bin/env python3
"""check_no_brace_paths.py — fail if any shipped path contains a '{' or '}' (W2).

The bundle once shipped a directory literally named
'{analyses,deep_dives,reports,incoming_figures}' because a `mkdir` brace expansion
ran in a shell (sh/dash) that doesn't expand braces. This check makes that class of
mistake fail the build instead of shipping.

    python3 tools/check_no_brace_paths.py [ROOT]   # default ROOT = bundle root

Exit 0 if clean, 1 if any path contains a brace (or the tree could not be fully scanned).
"""
import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _safe_walk import safe_walk_files  # v9.7.400: shared unreadable-dir-aware walk

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parent.parent


def main() -> int:
    paths, unreadable = safe_walk_files(ROOT, include_dirs=True)
    bad = [str(p.relative_to(ROOT)) for p in paths if "{" in p.name or "}" in p.name]
    failed = False
    if bad:
        failed = True
        emit("BRACE-PATH CHECK FAILED — these paths look like an unexpanded mkdir:")
        for b in bad:
            emit("  " + b)
    if unreadable:
        failed = True
        sys.stderr.write("BRACE-PATH CHECK COULD NOT FULLY SCAN — these directories were unreadable, so "
              "their contents are UNVERIFIED, not confirmed brace-free:\n")
        for u in unreadable:
            sys.stderr.write("  " + u + "\n")
    if not failed:
        emit("brace-path check OK — no '{' or '}' in any shipped path")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
