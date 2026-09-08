#!/usr/bin/env python3
"""check_module_accretion.py — the module-accretion gate (Round 4 Item 6).

Sapote-Mamey grew 53 modules across v9.7.121->158 with zero consolidations until
v9.7.155 (34 versions of pure accretion). This gate makes that pattern visible and
bounded at cut time: a module added to mamey/ must be acknowledged, either by

  (a) a CHANGELOG entry line naming it after `Consolidates:` or `Accretion-justified:`, or
  (b) regenerating MODULE_MANIFEST.txt (`--write`) as a deliberate composing step.

Fail-closed: the comparison baseline is the set of ``mamey/**/*.py`` paths recorded in
the sealed bundle's SOURCE_CHECKSUMS_SHA256.txt. Updating the editable
MODULE_MANIFEST.txt cannot hide a new module from this gate.

Exits non-zero if the current mamey/ module set contains a module not in that sealed
checksum inventory that is NOT justified in the newest CHANGELOG entry. This is the
one-in-one-out discipline as a mechanical check — it does not block adding modules, it
blocks adding them *silently*.

Usage:
  python tools/check_module_accretion.py                 # check against manifest + CHANGELOG
  python tools/check_module_accretion.py --write         # regenerate MODULE_MANIFEST.txt (cut step)
  python tools/check_module_accretion.py --json          # machine-readable report

Mirrors the tools/check_*.py convention: docstring usage, sys.exit(1 on violation).
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import ast
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _safe_walk import safe_walk_files  # v9.7.400: shared unreadable-dir-aware walk

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAMEY = ROOT / "mamey"
MANIFEST = ROOT / "MODULE_MANIFEST.txt"
SOURCE_CHECKSUMS = ROOT / "SOURCE_CHECKSUMS_SHA256.txt"
CHANGELOG = ROOT / "CHANGELOG.md"

_JUSTIFY_RE = re.compile(r"(?:Consolidates|Accretion-justified)\s*:", re.IGNORECASE)


def current_modules() -> tuple[dict[str, str], list[str]]:
    """{relpath: one-line purpose} for every non-cache module under mamey/, plus any directory
    this scan could not descend into.

    v9.7.400: replaced `MAMEY.rglob("*.py")`, which silently swallows a per-directory OSError
    -- a module hidden inside an unreadable mamey/ subdirectory was simply absent from
    `current_modules()`, indistinguishable from "this subtree has no modules." Reproduced live
    against the real pristine script: a brand-new, genuinely unmanifested module placed inside
    a permission-locked mamey/ subdirectory is completely invisible to the gate -- "net +0,
    accretion gate: PASS" -- on a tree that genuinely added an unacknowledged module, exactly
    the pattern this gate exists to make visible. This is the fourth instance of the same
    rglob-silently-swallows-OSError shape found this round (after check_no_brace_paths.py,
    check_duplicate_dict_keys.py, public_release_audit.py), so it reuses the same shared
    tools/_safe_walk.py helper rather than a fifth independent implementation.
    """
    out: dict[str, str] = {}
    paths, unreadable = safe_walk_files(MAMEY, suffix=".py", skip_dirs=frozenset({"__pycache__"}))
    for p in paths:
        rel = str(p.relative_to(ROOT))
        try:
            doc = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or ""
        except Exception:
            doc = ""
        purpose = doc.strip().splitlines()[0][:100] if doc.strip() else "(no docstring)"
        out[rel] = purpose
    return out, unreadable


class SealedBaselineError(ValueError):
    """The sealed checksum inventory is absent, malformed, or ambiguous."""


def manifest_modules() -> set[str]:
    """Return immutable module membership recorded by the sealed checksum list."""
    if not SOURCE_CHECKSUMS.is_file():
        raise SealedBaselineError("SEALED_BASELINE_MISSING: SOURCE_CHECKSUMS_SHA256.txt not found")
    mods = set()
    seen_paths: set[str] = set()
    for line_no, raw in enumerate(
        SOURCE_CHECKSUMS.read_text(encoding="utf-8", errors="strict").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        parts = raw.strip().split(None, 1)
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-fA-F]{64}", parts[0]):
            raise SealedBaselineError(f"SEALED_BASELINE_MALFORMED: line {line_no}")
        rel = parts[1].strip().lstrip("*")
        rel = rel[2:] if rel.startswith("./") else rel
        if rel in seen_paths:
            raise SealedBaselineError(f"SEALED_BASELINE_DUPLICATE: {rel}")
        seen_paths.add(rel)
        path = pathlib.PurePosixPath(rel)
        if len(path.parts) >= 2 and path.parts[0] == "mamey" and path.suffix == ".py":
            mods.add(path.as_posix())
    if not mods:
        raise SealedBaselineError("SEALED_BASELINE_EMPTY: no mamey Python modules recorded")
    return mods


def newest_changelog_entry() -> str:
    """Text of the newest (topmost) '# vX.Y.Z' CHANGELOG entry."""
    if not CHANGELOG.exists():
        return ""
    text = CHANGELOG.read_text(encoding="utf-8")
    # split on top-level version headers; take the first block
    parts = re.split(r"(?m)^#\s+v?\d+\.\d+\.\d+", text)
    # parts[0] is any preamble before the first header; the first real entry is parts[1]
    return parts[1] if len(parts) > 1 else text[:4000]


def justified_modules(entry_text: str) -> set[str]:
    """Module basenames named on a Consolidates:/Accretion-justified: line."""
    justified = set()
    for line in entry_text.splitlines():
        if _JUSTIFY_RE.search(line):
            # collect any *.py token on the line
            for tok in re.findall(r"[\w./]+\.py", line):
                justified.add(pathlib.Path(tok).name)
    return justified


def write_manifest() -> int:
    mods, unreadable = current_modules()
    if unreadable:
        # A manifest baked from an incomplete scan silently omits real modules -- the opposite
        # of a deliberate baseline. Refuse rather than write a manifest that understates what
        # mamey/ actually contains.
        sys.stderr.write(f"ERROR: {len(unreadable)} director{'y' if len(unreadable) == 1 else 'ies'} "
              f"under mamey/ could not be scanned (unreadable); refusing to write an "
              f"incomplete MODULE_MANIFEST.txt: {unreadable}\n")
        return 1
    lines = [
        "# MODULE_MANIFEST.txt — tracked mamey/ module inventory (accretion gate baseline)",
        "# Format: <relpath>\\t<one-line purpose from module docstring>",
        "# Regenerated at cut time by tools/check_module_accretion.py --write.",
        "# The accretion gate fails a cut that ADDS a module not listed here without a",
        "# Consolidates:/Accretion-justified: line in the CHANGELOG entry.",
        "",
    ]
    lines += [f"{rel}\t{purpose}" for rel, purpose in mods.items()]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    emit(f"MODULE_MANIFEST.txt written: {len(mods)} modules")
    return 0


def check(as_json: bool = False) -> int:
    cur, unreadable = current_modules()
    baseline_error = None
    try:
        known = manifest_modules()
    except (OSError, UnicodeError, SealedBaselineError) as exc:
        baseline_error = str(exc)
        known = set()
    added = {m for m in cur if m not in known}
    removed = {m for m in known if m not in cur}
    entry = newest_changelog_entry()
    justified = justified_modules(entry)

    # an added module is a violation unless its basename is justified in the newest entry
    unjustified = sorted(
        m for m in added if pathlib.Path(m).name not in justified
    )

    report = {
        "modules_current": len(cur),
        "modules_in_manifest": len(known),
        "baseline_source": SOURCE_CHECKSUMS.name,
        "baseline_error": baseline_error,
        "added": sorted(added),
        "removed": sorted(removed),
        "justified_in_changelog": sorted(justified),
        "unjustified_additions": unjustified,
        "net_module_delta": len(cur) - len(known),
        "unreadable_directories": unreadable,
    }

    if as_json:
        emit(json.dumps(report, indent=2))
    else:
        emit(f"modules: {len(cur)} current / {len(known)} in manifest "
              f"(net {report['net_module_delta']:+d})")
        if baseline_error:
            sys.stderr.write(f"  ACCRETION GATE FAIL — {baseline_error}\n")
        if removed:
            emit(f"  removed since manifest: {sorted(removed)}")
        if added:
            emit(f"  added since manifest: {sorted(added)}")
        if justified:
            emit(f"  justified in newest CHANGELOG: {sorted(justified)}")
        if unreadable:
            sys.stderr.write(f"  ACCRETION GATE FAIL — {len(unreadable)} director"
                  f"{'y' if len(unreadable) == 1 else 'ies'} under mamey/ could not be scanned "
                  f"(unreadable), so this scan is incomplete and cannot honestly report PASS:\n")
            for d in unreadable:
                sys.stderr.write(f"    - {d}\n")
        if unjustified:
            emit("  ACCRETION GATE FAIL — modules added without a "
                  "Consolidates:/Accretion-justified: line in the newest CHANGELOG entry:")
            for m in unjustified:
                emit(f"    - {m}")
            emit("  Fix: add a 'Accretion-justified: <module.py> — <reason>' (or "
                  "'Consolidates: ...') line to the newest CHANGELOG entry, OR run "
                  "`tools/check_module_accretion.py --write` if this is a deliberate baseline update.")
        if not unjustified and not unreadable and not baseline_error:
            emit("  accretion gate: PASS")

    return 1 if (unjustified or unreadable or baseline_error) else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Module-accretion gate.")
    ap.add_argument("--write", action="store_true",
                    help="Regenerate MODULE_MANIFEST.txt from the current tree (a deliberate cut step).")
    ap.add_argument("--json", action="store_true", help="Machine-readable report.")
    a = ap.parse_args()
    if a.write:
        return write_manifest()
    return check(as_json=a.json)


if __name__ == "__main__":
    raise SystemExit(main())
