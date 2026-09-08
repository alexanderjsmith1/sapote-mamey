#!/usr/bin/env python3
"""preflight_zip_hygiene.py — scan a built release ZIP for packaging-hygiene violations.

Motivated by the v9.7.155 candidate-3 external audit, which found `.pytest_cache`
entries in a deliverable ZIP. Root cause: an ad-hoc `zip` command used an
incomplete `-x` exclude set (caught `*.pyc`/`__pycache__` but not `.pytest_cache`).
The canonical builder (tools/make_public_tier.sh) already excludes correctly, and
tests/test_release_zip_hygiene.py guards the builder flags — but neither catches a
hand-built zip. This script is the missing checkable command: run it on ANY zip
before handoff.

Exit 0 = clean. Exit 1 = violations found (prints them). Intended for a release
preflight, CI, or a quick manual check:

    python3 tools/preflight_zip_hygiene.py <path-to-release.zip>

Checks (matching the audit's own method):
  - no .pytest_cache / __pycache__ / *.pyc / *.pyo entries
  - no editor/patch backups (*.orig / *.bak / *.rej / *~) or .DS_Store
  - no unexpected hidden dot-directories at any depth (allow a small known set)
  - no files > 5 MB unless explicitly allowlisted (registry inventories, wheels)
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import re
import sys
import zipfile
from pathlib import Path

CACHE_RE = re.compile(r"(\.pytest_cache|__pycache__|\.pyc$|\.pyo$|\.DS_Store$|\.orig$|\.bak$|\.rej$|~$)")
# Hidden dot-entries that are legitimately shipped at the repo root.
# v9.7.363: `.github` (CI workflows) and `.gitkeep` added for the public GitHub release. A repo with a
# 3,900-test suite and no CI config is not a credible open-source release, and without `.gitignore`
# contributors commit `__pycache__` on their first PR. These are the ONLY hidden entries permitted —
# everything else still fails the gate, which is what caught the `_CANDIDATE_NOTES` dotfiles at .355.
ALLOWED_HIDDEN = {".gitignore", ".github", ".gitkeep", ".gitattributes"}
# Files that are legitimately large (checked by basename suffix/substring).
# v9.7.395: matching is bound to the BASENAME — extension tokens must be a suffix of the final
# path segment, name tokens a substring of it. The prior `tok in name` full-path substring test
# silently exempted ANY oversized entry whose path merely contained a token — a directory named
# `figures.pdf_exports/`, a `report.pdf.zip`, a `registry_inventory_notes/` folder — with no
# ceiling and no reason, inverting the gate's "unexpected large file FAILS" contract.
LARGE_FILE_ALLOW = ("registry_inventory", ".whl", ".xlsx", ".pdf")


def _coarse_large_allow(name: str) -> bool:
    base = name.rstrip("/").rsplit("/", 1)[-1]
    for tok in LARGE_FILE_ALLOW:
        if tok.startswith("."):
            if base.endswith(tok):
                return True
        elif tok in base:
            return True
    return False
LARGE_LIMIT = 5 * 1024 * 1024
# v9.7.361 (R1): the path-bound allowlist FILE is now consulted, closing the .355 gap where
# tools/zip_hygiene_allowlist.{py,tsv} shipped as the sanctioned mechanism for intentionally-large
# files but this gate never read it — two tools, one gate, not connected, so the gate stayed red on
# a file that was already reviewed and declared. Precedence: the coarse suffix/substring tuple above
# first (unchanged, back-compatible), then the path-bound allowlist, which is STRICTER because it
# binds a specific relpath to a declared per-file ceiling and a written reason. An oversized file
# still FAILS unless one of the two permits it, so the gate keeps its teeth.
ALLOWLIST_TSV = Path(__file__).resolve().parent / "zip_hygiene_allowlist.tsv"


def _load_path_allowlist(tsv: Path = ALLOWLIST_TSV) -> dict:
    """Load the path-bound allowlist. Missing/unreadable file -> {} (gate simply stays strict)."""
    try:
        from zip_hygiene_allowlist import load_allowlist  # same tools/ dir
    except Exception:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from zip_hygiene_allowlist import load_allowlist
        except Exception:
            return {}
    try:
        return load_allowlist(tsv)
    except Exception:
        return {}


def _oversized(name: str, size: int, allow: dict) -> bool:
    """True if `name` breaches the size policy. Zip entries have no './' prefix; the allowlist is
    written with one, so both spellings are accepted."""
    if size <= LARGE_LIMIT:
        return False
    if _coarse_large_allow(name):
        return False
    for key in (name, "./" + name.lstrip("./")):
        if key in allow:
            ceiling, _reason = allow[key]
            return size > ceiling      # over its OWN declared ceiling -> still a violation
    return True


def scan(zip_path: Path) -> dict:
    result = {"zip": str(zip_path), "cache": [], "hidden": [], "large": []}
    allow = _load_path_allowlist()
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            name = info.filename
            if CACHE_RE.search(name):
                result["cache"].append(name)
            # hidden dot-entry at any path segment (dir or file), minus allowlist
            segs = [s for s in name.split("/") if s]
            for s in segs:
                if s.startswith(".") and s not in ALLOWED_HIDDEN:
                    result["hidden"].append(name)
                    break
            if _oversized(name, info.file_size, allow):
                result["large"].append(f"{name} ({info.file_size // (1024*1024)} MB)")
    # de-dup while preserving order
    for k in ("cache", "hidden", "large"):
        seen = set()
        result[k] = [x for x in result[k] if not (x in seen or seen.add(x))]
    return result


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        emit("usage: preflight_zip_hygiene.py <release.zip>", file=sys.stderr)
        return 2
    zp = Path(argv[1])
    if not zp.exists():
        emit(f"ERROR: zip not found: {zp}", file=sys.stderr)
        return 2
    r = scan(zp)
    problems = r["cache"] or r["hidden"] or r["large"]
    if not problems:
        emit(f"OK: {zp.name} is clean (no cache / unexpected hidden / oversized entries)")
        return 0
    emit(f"FAIL: {zp.name} has packaging-hygiene violations:")
    if r["cache"]:
        emit(f"  cache/backup artifacts ({len(r['cache'])}): {r['cache'][:10]}")
    if r["hidden"]:
        emit(f"  unexpected hidden entries ({len(r['hidden'])}): {r['hidden'][:10]}")
    if r["large"]:
        emit(f"  oversized files ({len(r['large'])}): {r['large'][:10]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
