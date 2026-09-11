#!/usr/bin/env python3
"""strain_data_home.py — canonical per-strain data-home resolver for Sapote-Mamey.

A recurring defect class in this workspace is "the data exists but the tool
can't find it": a strain's antiSMASH result ZIP and its sealed Mamey package are
scattered across many folders (`strain_data/<strain>/antiSMASH/`,
top-level `Antismash/`, `mamey_packages/`, `Mamey Complete v*/`), so an
individual tool that only globs one home reports "no data" while the data is
sitting one directory over. This module is the single, shared resolver every
reader-side tool should call instead of ad-hoc globbing.

Public API
----------
    resolve_antismash_zip(strain, root=".") -> str | None
    resolve_mamey_package(strain, root=".")  -> str | None
    strain_data_home(strain, root=".")       -> dict

CLAIM-SAFETY
------------
This is a *file resolver*, not an analysis. It makes no scientific claim of any
kind. It is strictly reader-side and non-mutating: it never writes, moves, or
deletes anything, and it never fabricates a path. Every returned path is a file
that exists on disk *and* (for antiSMASH result ZIPs) has been opened and
verified to contain a top-level antiSMASH JSON member. When a strain's antiSMASH
ZIP or Mamey package cannot be located, the resolver returns ``None`` rather than
guessing — a missing return is an honest "not found here," never a biological or
provenance claim.

Pure standard library only (glob, os, re, zipfile).
"""
from __future__ import annotations

import glob
import os
import re
import zipfile
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible writer (no bare print(); holds strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

__all__ = [
    "clear_strain_data_cache",
    "resolve_antismash_zip",
    "resolve_mamey_package",
    "strain_data_home",
    "zip_has_antismash_json",
]


def zip_has_antismash_json(zip_path: str) -> bool:
    """True iff *zip_path* is a readable ZIP that contains a top-level antiSMASH
    RESULT JSON — a member ending in ``.json`` that is NOT under an ``input/``
    directory (antiSMASH echoes the submitted GBK/JSON into ``input/``; that is
    not a result). Validation is by *opening* the archive and inspecting member
    names, never by matching the filename alone."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            for name in zf.namelist():
                if not name.endswith(".json"):
                    continue
                # Reject the echoed submission: any .json living under an
                # `input/` directory at any depth (antiSMASH stores the
                # submitted GBK/JSON there). A genuine result json does not.
                if "/input/" in name or name.split("/")[0] == "input":
                    continue
                return True
    except Exception:
        return False
    return False


def resolve_antismash_zip(strain: str, root: str = ".", flavor: str | None = None) -> str | None:
    """Return the path to the first existing antiSMASH RESULT ZIP for *strain*,
    searching the known homes in priority order and validating each candidate by
    opening it and confirming a top-level antiSMASH JSON member is present.

    Priority order (first validated hit wins):
      1. ``strain_data/<strain>/antiSMASH/<strain>.zip``   (canonical home)
      2. ``strain_data/<strain>/antiSMASH/*.zip``          (canonical dir, any name)
      3. ``Antismash/<strain>.zip``                             (flat top-level home)
      4. ``Antismash/**/<strain>.zip``                     (nested under the top-level home)
      5. any ``*<strain>*.zip`` under the sealed-package homes (``mamey_packages/``,
         ``Mamey Complete*/``, plus any ``MAMEY_PACKAGE_HOMES`` env globs) that contains
         an antiSMASH result JSON — a *fallback*, tried newest-first by parsed package
         version (a raw result ZIP always outranks it)

    v9.7.399: when *flavor* (``loose``/``relaxed``/``strict``) is given, resolve ONLY from
    the flavor-separated antiSMASH canonical home ``[*/]_ANTISMASH_CANONICAL/<flavor>/<strain>.zip``
    — the directory IS the strictness authority there (regions of different strictness are not
    comparable), so a caller asking for a specific flavor never silently gets the other one. Returns
    ``None`` if no canonical ZIP of that flavor exists, rather than falling back to an unknown-flavor
    home. ``flavor=None`` preserves the flavor-agnostic priority order below byte-for-byte.

    Returns ``None`` if nothing valid is found — never a fabricated path.
    """
    if flavor is not None:
        for pat in (
            os.path.join(root, "_ANTISMASH_CANONICAL", flavor, strain + ".zip"),
            os.path.join(root, "*", "_ANTISMASH_CANONICAL", flavor, strain + ".zip"),
        ):
            for path in sorted(glob.glob(pat)):
                if os.path.isfile(path) and zip_has_antismash_json(path):
                    return path
        return None
    patterns = [
        os.path.join(root, "strain_data", strain, "antiSMASH", strain + ".zip"),
        os.path.join(root, "strain_data", strain, "antiSMASH", "*.zip"),
        os.path.join(root, "Antismash", strain + ".zip"),
        os.path.join(root, "Antismash", "**", strain + ".zip"),
    ]
    for pat in patterns:
        recursive = "**" in pat
        for path in sorted(glob.glob(pat, recursive=recursive)):
            if not os.path.isfile(path):
                continue
            if zip_has_antismash_json(path):
                return path
    # Package-embedded fallback: newest sealed package first, never alphabetical —
    # the old sorted-by-path walk returned the OLDEST seal (v9.7.335 beat v9.7.339).
    fallback = [p for p in _package_zip_index(root) if strain in os.path.basename(p)]
    for path in sorted(set(fallback), key=lambda p: (_package_version_key(p), p), reverse=True):
        if zip_has_antismash_json(path):
            return path
    return None


# Matches e.g. 9.7.339 in ..._SapoteMamey_v9.7.339_engine1.9.119_Complete_Package.zip
_VER_RE = re.compile(r"_(?:SapoteMamey|Mamey)_v(\d+)\.(\d+)\.(\d+)_")

# v9.7.399: the antiSMASH detection strictness token stamped into the package filename since
# v9.7.398 (``..._engine<VER>_<flavor>_Complete_Package.zip``). Packages sealed before .398 have
# no token, so ``_package_flavor`` returns None for them — a specific flavor request never matches
# an unknown-flavor package (honest: it cannot prove the flavor from the name alone).
_PKG_FLAVOR_RE = re.compile(r"_engine[0-9][0-9A-Za-z.\-]*_(strict|relaxed|loose)_Complete_Package\.zip$")


def _package_flavor(basename: str) -> str | None:
    """Return the strictness flavor stamped in a Complete_Package filename, or None."""
    m = _PKG_FLAVOR_RE.search(basename)
    return m.group(1) if m else None

# Sealed-package homes, searched recursively. ``Mamey Complete*`` (no version suffix
# required) also covers flat per-strain homes that superseded the versioned folders;
# requiring the ``v*`` suffix made the resolver silently prefer older seals (verified
# field failure, 2026-09-01). Additional workspace-specific homes come from the
# ``MAMEY_PACKAGE_HOMES`` environment variable (``os.pathsep``-separated glob patterns,
# absolute or root-relative) — the engine source stays free of workspace locators.
_PACKAGE_HOMES = ("mamey_packages", "Mamey Complete*")


def _package_homes() -> tuple[str, ...]:
    extra = os.environ.get("MAMEY_PACKAGE_HOMES", "")
    homes = list(_PACKAGE_HOMES)
    for h in extra.split(os.pathsep):
        h = h.strip()
        if h:
            homes.append(h)
    return tuple(homes)


# One estate walk per (root, homes) instead of a recursive glob per call: package homes
# can hold hundreds of extracted package trees (measured 11.6 s PER resolution on a real
# workspace before this cache; ~milliseconds after). Long-lived processes that add new
# package ZIPs mid-run can call clear_strain_data_cache().
_ESTATE_CACHE: dict = {}


def clear_strain_data_cache() -> None:
    """Drop the cached package-home walk (call after adding/moving package ZIPs)."""
    _ESTATE_CACHE.clear()


def _package_zip_index(root: str) -> list[str]:
    """All ``*.zip`` file paths under the package homes for *root*, walked once and cached."""
    homes = _package_homes()
    key = (os.path.abspath(root), homes)
    cached = _ESTATE_CACHE.get(key)
    if cached is not None:
        return cached
    zips: list[str] = []
    # Dedup by (st_dev, st_ino): on case-insensitive filesystems (macOS APFS) a built-in
    # glob ("Mamey Complete*") and a case-variant MAMEY_PACKAGE_HOMES entry ("MAMEY
    # COMPLETE") resolve the SAME physical directory under two path strings, and
    # os.path.realpath does not canonicalize case — so a string-keyed walk double-indexes
    # every package (the newest ZIP then shadows itself into superseded_packages).
    # Inode identity is filesystem-honest for case twins, symlinks, and hardlinks alike.
    seen_dirs: set = set()
    seen_files: set = set()
    for home in homes:
        for home_dir in glob.glob(os.path.join(root, home)):
            if not os.path.isdir(home_dir):
                continue
            try:
                st = os.stat(home_dir)
                dir_id = (st.st_dev, st.st_ino)
            except OSError:
                # Inode identity unavailable (permission blip, racing rename,
                # unreadable mount): degrade to realpath-string identity rather than
                # dropping the whole home — an unindexed package resolves as missing
                # or lets an older seal win freshness, which is a wrong answer; the
                # fallback's worst case is one case-twin double-walk of this entry.
                dir_id = ("realpath", os.path.realpath(home_dir))
            if dir_id in seen_dirs:
                continue
            seen_dirs.add(dir_id)
            for dirpath, _dirnames, filenames in os.walk(home_dir):
                for fn in filenames:
                    if fn.endswith(".zip"):
                        path = os.path.join(dirpath, fn)
                        try:
                            fst = os.stat(path)
                            file_id = (fst.st_dev, fst.st_ino)
                        except OSError:
                            # Same degradation for a single unstat-able ZIP: keep it
                            # indexed under realpath identity instead of silently
                            # erasing a sealed package from the estate.
                            file_id = ("realpath", os.path.realpath(path))
                        if file_id in seen_files:
                            continue
                        seen_files.add(file_id)
                        zips.append(path)
    _ESTATE_CACHE[key] = zips
    return zips


def _package_version_key(path: str):
    """Sort key extracting the (major, minor, patch) bundle version from a
    Complete_Package filename; unparseable names sort lowest."""
    m = _VER_RE.search(os.path.basename(path))
    if not m:
        return (-1, -1, -1)
    return tuple(int(g) for g in m.groups())


def resolve_mamey_package(strain: str, root: str = ".", flavor: str | None = None) -> str | None:
    """Return the newest (highest-version) sealed Mamey Complete package ZIP for
    *strain*, searching the known package homes.

    Recognised names (both historical spellings):
      ``<strain>_SapoteMamey_v*_..._Complete_Package.zip``
      ``<strain>_Mamey_v*_..._Complete_Package.zip``

    Homes searched (recursively): ``mamey_packages/``, ``Mamey Complete*/``, plus any
    ``MAMEY_PACKAGE_HOMES`` environment globs (``os.pathsep``-separated).
    "Newest" = highest parsed bundle version; ties fall back to path sort.
    Returns ``None`` if no package is found — never a fabricated path.
    """
    found = _strain_packages(strain, root, flavor=flavor)
    if not found:
        return None
    # Prefer highest version; break ties deterministically by path.
    return sorted(found, key=lambda p: (_package_version_key(p), p))[-1]


def _strain_packages(strain: str, root: str, flavor: str | None = None) -> list[str]:
    """Every recognised Complete_Package ZIP for *strain* across the package homes
    (cached estate walk; both historical name spellings). When *flavor* is given, keep
    only packages whose filename carries that strictness token (v9.7.398+ names); a
    flavor request therefore never returns an unknown-flavor (pre-.398) package."""
    import fnmatch

    name_globs = (
        strain + "_SapoteMamey_v*_*Complete_Package.zip",
        strain + "_Mamey_v*_*Complete_Package.zip",
    )
    out: set[str] = set()
    for path in _package_zip_index(root):
        base = os.path.basename(path)
        if any(fnmatch.fnmatch(base, ng) for ng in name_globs):
            if flavor is not None and _package_flavor(base) != flavor:
                continue
            out.add(path)
    return sorted(out)


def strain_data_home(strain: str, root: str = ".", flavor: str | None = None) -> dict:
    """Return the canonical data-home descriptor for *strain*:

        {
          "strain":               <strain>,
          "antismash_zip":        <path or None>,
          "mamey_package":        <path or None>,
          "superseded_packages":  [older package paths the newest one outranked],
          "canonical_dir":        "strain_data/<strain>",
        }

    ``canonical_dir`` is the intended per-strain home (see
    ``tools/materialize_strain_data.py``); it is reported as a relative path even
    when it does not yet exist on disk. ``antismash_zip`` / ``mamey_package`` are
    ``None`` where unresolved — no path is ever fabricated.
    ``superseded_packages`` is the freshness receipt: every other sealed package
    found for the strain, oldest-first, so a consumer (or an operator reading
    logs) can see exactly which stale seals were skipped. Additive key; empty
    list when at most one package exists.
    """
    newest = resolve_mamey_package(strain, root=root, flavor=flavor)
    older: set[str] = set()
    if newest is not None:
        older = {p for p in _strain_packages(strain, root, flavor=flavor) if p != newest}
    return {
        "strain": strain,
        "antismash_zip": resolve_antismash_zip(strain, root=root, flavor=flavor),
        "mamey_package": newest,
        "superseded_packages": sorted(older, key=lambda p: (_package_version_key(p), p)),
        "canonical_dir": os.path.join("strain_data", strain),
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Resolve a strain's canonical data home.")
    ap.add_argument("strains", nargs="+", help="strain IDs, e.g. AS-XXX AS-XXX")
    ap.add_argument("--root", default=".", help="workspace root (default: .)")
    args = ap.parse_args()
    for s in args.strains:
        emit(json.dumps(strain_data_home(s, root=args.root), indent=1))
