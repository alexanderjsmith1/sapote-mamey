#!/usr/bin/env python3
"""materialize_strain_data.py — one-time staging tool for the canonical
per-strain data home.

For each AS strain, if the canonical antiSMASH slot
``strain_data/<strain>/antiSMASH/<strain>.zip`` does NOT already exist but
``strain_data_home.resolve_antismash_zip`` finds a valid antiSMASH result ZIP
elsewhere (e.g. flat ``Antismash/<strain>.zip``), this tool COPIES that ZIP into
the canonical slot so every downstream tool can find it in one predictable place.

Safety / claim-safety
---------------------
- COPY only, never move: originals are left exactly where they are.
- Dry-run by DEFAULT: prints what it *would* stage. Pass ``--apply`` to copy.
- Never overwrites an existing canonical slot (already-canonical strains are skipped).
- AS-XXX (contaminated, hard-hold) and AS-XXX (chimeric assembly) are skipped.
- Reader/stager only — makes no scientific claim; it just relocates a copy of a
  file that already exists.

Usage:
    python tools/materialize_strain_data.py            # dry-run, all AS strains
    python tools/materialize_strain_data.py --apply    # actually copy
    python tools/materialize_strain_data.py AS-XXX AS-XXX    # specific strains
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible writer (no bare print(); holds strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

# Make the engine package importable whether run from the bundle root or the
# tools/ dir (mirrors mamey_run.py's local-package-first convention).
_HERE = os.path.dirname(os.path.abspath(__file__))
for _cand in (os.path.dirname(_HERE), _HERE):
    if _cand not in sys.path:
        sys.path.insert(0, _cand)

try:
    from mamey.strain_data_home import resolve_antismash_zip
except Exception:  # pragma: no cover - fallback for flat co-location
    from strain_data_home import resolve_antismash_zip  # type: ignore

# v9.7.371 fix: was a hardcoded literal {"AS-XXX", "AS-XXX"} duplicating mamey/exclusions.py's
# SSOT and missing AS-XXX -- the strain ruled a duplicate/mislabel of SID10815 (the Developer or User ruling
# 2026-08-09). This tool materializes strains into the canonical strain_data/ data home every
# downstream tool trusts; without AS-XXX in the skip set, this tool would happily copy AS-XXX's
# antiSMASH zip into that canonical slot, re-materializing a strain the project has explicitly
# ruled invalid. raw_analysis_excluded() is the documented SSOT accessor for exactly this "raw
# sealed package" consumer scope (== hard_excluded() | raw_assembly_void() == {AS-XXX, AS-XXX,
# AS-XXX}).
try:
    from mamey.exclusions import raw_analysis_excluded
    SKIP_STRAINS = raw_analysis_excluded()
except Exception:  # pragma: no cover - standalone fallback if mamey package unavailable
    raise RuntimeError(
        "cohort exclusions are governed data and are not shipped in the code tier: "
        "install the mamey package, or set MAMEY_OFFICIAL_DATA to a directory "
        "containing exclusions.json"
    )


def discover_as_strains(root: str) -> list[str]:
    """Return the union of AS-* strain IDs visible under the known homes, so the
    tool can stage a strain even when it has no `strain_data/<strain>` dir
    yet (that is precisely the case we want to fix)."""
    strains: set[str] = set()
    asm = os.path.join(root, "strain_data")
    if os.path.isdir(asm):
        for name in os.listdir(asm):
            if name.startswith("AS-") and os.path.isdir(os.path.join(asm, name)):
                strains.add(name)
    flat = os.path.join(root, "Antismash")
    if os.path.isdir(flat):
        for name in os.listdir(flat):
            if name.startswith("AS-") and name.endswith(".zip"):
                strains.add(name[:-4])
    return sorted(strains)


def canonical_slot(root: str, strain: str) -> str:
    return os.path.join(root, "strain_data", strain, "antiSMASH", strain + ".zip")


def materialize(root: str, strains: list[str], apply: bool) -> None:
    staged = skipped_exist = skipped_hold = unresolved = 0
    for strain in strains:
        if strain in SKIP_STRAINS:
            emit(f"  SKIP (hard-hold)   {strain}")
            skipped_hold += 1
            continue
        dest = canonical_slot(root, strain)
        if os.path.exists(dest):
            skipped_exist += 1
            continue  # already canonical; nothing to do
        src = resolve_antismash_zip(strain, root=root)
        if not src:
            emit(f"  UNRESOLVED         {strain}: no valid antiSMASH zip in any home")
            unresolved += 1
            continue
        rel_src = os.path.relpath(src, root)
        rel_dest = os.path.relpath(dest, root)
        if apply:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            # v9.7.374 fix: shutil.copy2(src, dest) writes DIRECTLY to the canonical path. A kill
            # (SIGTERM/disk-full/OSError) partway through leaves a truncated/corrupt file AT dest --
            # and the only completeness check anywhere in this tool is `os.path.exists(dest)` (see
            # the skip branch above), with no size/hash verification. A future run then reports that
            # strain "already canonical" and skips it FOREVER, silently poisoning the canonical slot
            # "every downstream tool can find [data] in one predictable place" trusts (this file's own
            # docstring). Copy to a sibling .tmp in the same destination dir, then os.replace() into
            # place -- the same crash-safe temp+rename discipline tools/_wbio.py already establishes
            # for text/JSON/workbook writes, applied here to a raw file copy: dest only ever appears
            # via one atomic rename of a COMPLETE copy; an interrupted copy leaves only a stray .tmp,
            # never a corrupt file at the canonical path itself.
            tmp = dest + ".tmp"
            try:
                shutil.copy2(src, tmp)
            except BaseException:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise
            os.replace(tmp, dest)
            emit(f"  STAGED             {strain}: {rel_src} -> {rel_dest}")
        else:
            emit(f"  WOULD STAGE        {strain}: {rel_src} -> {rel_dest}")
        staged += 1

    mode = "APPLIED" if apply else "DRY-RUN (no files copied; pass --apply to stage)"
    emit()
    emit(f"== {mode} ==", f"   would stage / staged : {staged}", f"   already canonical    : {skipped_exist}", f"   hard-hold skipped    : {skipped_hold}", f"   unresolved           : {unresolved}", sep="\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("strains", nargs="*",
                    help="specific strain IDs; default = all discovered AS-* strains")
    ap.add_argument("--root", default=".", help="workspace root (default: .)")
    ap.add_argument("--apply", action="store_true",
                    help="actually COPY zips into canonical slots (default: dry-run)")
    args = ap.parse_args()
    strains = args.strains or discover_as_strains(args.root)
    if not strains:
        emit("No AS-* strains discovered under", os.path.abspath(args.root))
        sys.exit(0)
    materialize(args.root, strains, args.apply)
