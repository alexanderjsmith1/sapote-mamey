#!/usr/bin/env python3
"""gen_tier_doc.py — generate the tier/release explainer FROM the release-state record. Generic.

Fixes stale hand-maintained docs (TIER_SET_EXPLAINER carried v9.7.319 / a 5-tier / 1353-file description long
after the engine moved on). Instead of editing prose, generate the doc from the authoritative version fields so
it is always current by construction.

Reads engine + bundle version from `mamey/__init__.py` (or --engine/--bundle overrides) and the file count from
a checksums file (--checksums), then emits the explainer markdown to stdout.

  gen_tier_doc.py --pkg <engine_tree>/mamey/__init__.py --checksums <tree>/SOURCE_CHECKSUMS_SHA256.txt
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse, re, sys, pathlib

def read_versions(pkg_init):
    txt = pathlib.Path(pkg_init).read_text()
    eng = re.search(r'__version__\s*=\s*["\']([^"\']+)', txt)
    bun = re.search(r'BUNDLE_VERSION\s*=\s*["\']([^"\']+)', txt)
    return (eng.group(1) if eng else "?", bun.group(1) if bun else "?")

def count_files(checksums):
    if not checksums:
        return None
    n = 0
    for ln in open(checksums):
        if ln.strip():
            n += 1
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg", help="path to mamey/__init__.py")
    ap.add_argument("--engine"); ap.add_argument("--bundle")
    ap.add_argument("--checksums")
    a = ap.parse_args()

    if a.pkg:
        eng, bun = read_versions(a.pkg)
    else:
        eng, bun = a.engine or "?", a.bundle or "?"
    nfiles = count_files(a.checksums)

    emit(f"# Sapote-Mamey — tier & release explainer (generated)\n", f"> Generated from the release-state record by `gen_tier_doc.py` — do not edit by hand.\n", f"- **Bundle version:** {bun}", f"- **Engine version:** {eng}", sep="\n")
    if nfiles is not None:
        emit(f"- **Sealed source files:** {nfiles}")
    emit()
    emit("## Tiers\n", "- **Tier 1 — Mamey** (Python): deterministic extraction. antiSMASH ZIP → sealed JSON/CSV/XLSX package + manifest.", "- **Tier 2 — Sapote-slim** / **Tier 3 — Sapote full**: LLM judgment protocols (Markdown), not executable code.", "\nEngine motto: **deterministic extraction, judgment deferred.** Outputs are class-level hypotheses with", "mandatory claim-safety language — never structural/bioactivity claims.", sep="\n")

if __name__ == "__main__":
    main()
