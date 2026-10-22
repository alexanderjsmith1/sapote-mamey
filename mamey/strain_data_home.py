#!/usr/bin/env python3
"""strain_data_home.py — canonical per-strain data-home resolver for Sapote-Mamey.

A recurring defect class in this workspace is "the data exists but the tool
can't find it": a strain's antiSMASH result ZIP and its sealed Mamey package are
scattered across many folders (`strain_data/<strain>/antiSMASH/`,
top-level `Antismash/`, `mamey_packages/`, `Package Outputs v*/`), so an
individual tool that only globs one home reports "no data" while the data is
sitting one directory over. This module is the single, shared resolver every
reader-side tool should call instead of ad-hoc globbing.

Public API
----------
    resolve_antismash_zip(strain, root=".") -> str | None
    resolve_mamey_package(strain, root=".")  -> str | None
    strain_data_home(strain, root=".")       -> dict
    strain_master_root(master=None)          -> str | None
    strain_master_record(data_type, strain=None, master=None) -> dict

A Strain Master (docs/DATA_HOME.md) is a user-chosen folder, named by ``--master`` or the
``SAPOTE_STRAIN_MASTER`` environment variable, never by a path in this source. When one is
configured, ``strain_data_home`` looks there first and then in the legacy homes below.

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
import csv
import json
import fnmatch
from pathlib import Path
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
    "package_home_patterns",
    "package_home_directories",
    "strain_master_root",
    "strain_master_config",
    "strain_master_folders",
    "read_readme_records",
    "read_layout",
    "layout_allows",
    "strain_master_record",
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
      5. ``[*/]_ANTISMASH_CANONICAL/<flavor>/<strain>.zip`` (v9.7.455): one flavor, or several
         byte-identical ones; different flavors return None, since the caller must name one
      6. any ``*<strain>*.zip`` under the sealed-package homes (``mamey_packages/``,
         ``Package Outputs*/``, plus any ``MAMEY_PACKAGE_HOMES`` env globs) that contains
         an antiSMASH result JSON — a *fallback*, tried newest-first by parsed package
         version (a raw result ZIP always outranks it)

    v9.7.399: when *flavor* (``loose``/``relaxed``/``strict``) is given, resolve ONLY from
    the flavor-separated antiSMASH canonical home ``[*/]_ANTISMASH_CANONICAL/<flavor>/<strain>.zip``
    — the directory IS the strictness authority there (regions of different strictness are not
    comparable), so a caller asking for a specific flavor never silently gets the other one. Returns
    ``None`` if no canonical ZIP of that flavor exists, rather than falling back to an unknown-flavor
    home. ``flavor=None`` uses the flavor-agnostic priority order above.

    Returns ``None`` if nothing valid is found — never a fabricated path.
    """
    auth, state = _assembly_authority(strain, root)
    if state["status"] == "AUTHORITY_INVALID":
        return None
    if auth is not None:
        target = _authority_path(auth.get("clean_antismash_zip", ""), root)
        if flavor is not None and auth.get("antismash_flavor") != flavor:
            return None
        return target if target and zip_has_antismash_json(target) else None
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
    # v9.7.455: the flavored canonical home before any package. A genome's identity is its antiSMASH
    # ZIP, so a package must never stand in for a ZIP of record that exists. One flavor (or several
    # byte-identical ones) is returned; different flavors are ambiguous and return None, so the caller
    # names the flavor (strain_data_home lists them under canonical_antismash).
    canon = _canonical_by_flavor(strain, root)
    if canon:
        digests = {_sha_file(p) for p in canon.values()}
        return next(iter(canon.values())) if len(digests) == 1 else None
    # Package-embedded fallback: newest sealed package first, never alphabetical —
    # the old sorted-by-path walk returned the OLDEST seal (v9.7.335 beat v9.7.339).
    fallback = [p for p in _package_zip_index(root) if strain in os.path.basename(p)]
    for path in sorted(set(fallback), key=lambda p: (_package_version_key(p), p), reverse=True):
        if zip_has_antismash_json(path):
            return path
    return None


def _canonical_by_flavor(strain: str, root: str) -> dict:
    """{flavor: path} of valid ZIPs in ``[*/]_ANTISMASH_CANONICAL/<flavor>/<strain>.zip``, flavor order strict, relaxed, loose."""
    out = {}
    for fl in ("strict", "relaxed", "loose"):
        for pat in (os.path.join(root, "_ANTISMASH_CANONICAL", fl, strain + ".zip"),
                    os.path.join(root, "*", "_ANTISMASH_CANONICAL", fl, strain + ".zip")):
            hit = next((p for p in sorted(glob.glob(pat)) if os.path.isfile(p) and zip_has_antismash_json(p)), None)
            if hit:
                out[fl] = hit
                break
    return out


def _sha_file(path: str) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


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

# Sealed-package homes, searched recursively. ``Package Outputs*`` (no version suffix
# required) also covers flat per-strain homes that superseded the versioned folders;
# requiring the ``v*`` suffix made the resolver silently prefer older seals (verified
# field failure, 2026-09-01). Additional workspace-specific homes come from the
# ``MAMEY_PACKAGE_HOMES`` environment variable (``os.pathsep``-separated glob patterns,
# absolute or root-relative) — the engine source stays free of workspace locators.
_PACKAGE_HOMES = ("mamey_packages", "Package Outputs*")


def _package_homes() -> tuple[str, ...]:
    """Built-in homes, then the ``package_homes`` of the master named by SAPOTE_STRAIN_MASTER
    (resolved against that master), then ``MAMEY_PACKAGE_HOMES``."""
    extra = os.environ.get("MAMEY_PACKAGE_HOMES", "")
    homes = list(_PACKAGE_HOMES)
    homes += [h for h in _master_package_homes() if h not in homes]
    for h in extra.split(os.pathsep):
        h = h.strip()
        if h:
            homes.append(h)
    return tuple(homes)


def package_home_patterns() -> tuple[str, ...]:
    """Neutral built-ins first, then explicit custom patterns in declared order."""
    return _package_homes()


def package_home_directories(root: str = ".") -> tuple[str, ...]:
    """Existing selected home directories; no implicit legacy-name discovery."""
    result = []; seen = set()
    for pattern in _package_homes():
        for directory in _matched_homes(root, pattern):
            if not os.path.isdir(directory):
                continue
            try:
                state = os.stat(directory); key = (state.st_dev, state.st_ino)
            except OSError:
                key = ("realpath", os.path.realpath(directory))
            if key not in seen:
                seen.add(key); result.append(directory)
    return tuple(result)


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
    # glob ("Package Outputs*") and an explicitly configured case-variant entry
    # (neutral example: "PACKAGE OUTPUTS") can resolve the SAME physical directory under two path strings, and
    # os.path.realpath does not canonicalize case — so a string-keyed walk double-indexes
    # every package (the newest ZIP then shadows itself into superseded_packages).
    # Inode identity is filesystem-honest for case twins, symlinks, and hardlinks alike.
    seen_dirs: set = set()
    seen_files: set = set()
    for home in homes:
        for home_dir in _matched_homes(root, home):
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
                if home in _PACKAGE_HOMES:
                    _dirnames[:] = [d for d in _dirnames if "archive" not in d.casefold() and "excluded" not in d.casefold()]
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


def _package_engine_key(path: str):
    m = re.search(r"_engine(\d+)\.(\d+)\.(\d+)_", os.path.basename(path))
    return tuple(map(int, m.groups())) if m else (-1, -1, -1)


def resolve_mamey_package(strain: str, root: str = ".", flavor: str | None = None) -> str | None:
    """Return the newest (highest-version) sealed Mamey package ZIP for
    *strain*, searching the known package homes.

    Recognised names (both historical spellings):
      ``<strain>_SapoteMamey_v*_..._Complete_Package.zip``
      ``<strain>_Mamey_v*_..._Complete_Package.zip``

    Homes searched (recursively): ``mamey_packages/``, ``Package Outputs*/``, plus any
    ``MAMEY_PACKAGE_HOMES`` environment globs (``os.pathsep``-separated).
    With an owner authority row, admitted assembly metrics use engine then bundle
    version. Without a row, highest parsed bundle version wins; ties use path sort.
    Returns ``None`` if no package is found — never a fabricated path.
    """
    auth, state = _assembly_authority(strain, root)
    if state["status"] == "AUTHORITY_INVALID":
        return None
    if auth is not None:
        target = _authority_path(auth.get("clean_package", ""), root)
        if auth.get("clean_package", "").strip():
            return target if target and _manifest_matches_authority(target, strain, auth, flavor) else None
    found = _strain_packages(strain, root, flavor=flavor)
    if auth is not None:
        found = [p for p in found if _manifest_matches_authority(p, strain, auth, flavor)]
    if not found:
        return None
    # Owner-matched assembly metrics permit engine-first ordering; legacy discovery stays bundle-first.
    if auth is not None:
        return max(found, key=lambda p: (_package_engine_key(p), _package_version_key(p), p))
    return max(found, key=lambda p: (_package_version_key(p), p))


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


def strain_data_home(strain: str, root: str = ".", flavor: str | None = None,
                     master: str | None = None) -> dict:
    """Return the canonical data-home descriptor for *strain*:

        {
          "strain":               <strain>,
          "antismash_zip":        <path or None>,
          "mamey_package":        <path or None>,
          "superseded_packages":  [older package paths the newest one outranked],
          "canonical_dir":        "strain_data/<strain>",
          "strain_master":        None, or what the Strain Master holds,
          "antismash_source_kind": strain_master | raw_result | canonical_<flavor> | package_embedded
                                  | AMBIGUOUS_FLAVOR | None,
          "canonical_antismash":  {flavor: path} found in the flavored canonical home,
          "resolved_from":        {"antismash_zip": "strain_master" | "legacy" | None, ...},
        }

    Strain Master first: when *master* (or ``SAPOTE_STRAIN_MASTER``) names a master, a
    README-registered antiSMASH ZIP or sealed package in that master's folder for the kind wins,
    and the legacy homes are the fallback. With no master configured, every legacy key is
    resolved exactly as before and ``strain_master`` is None.

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
    auth, authority_state = _assembly_authority(strain, root)
    if auth is not None:
        authority_state = {**authority_state, "status": "MATCHED_ASSEMBLY_METRICS" if newest else "SUPERSEDED_ASSEMBLY_OR_MISSING",
                           "reason": "Owner-nominated package or matching metrics; metrics are not sequence-hash proof" if newest else "No admitted package; disagreeing, missing or unreadable candidates refused"}
    legacy_zip = resolve_antismash_zip(strain, root=root, flavor=flavor)
    held = _master_strain_files(strain, master, flavor)
    zip_path = (held or {}).get("antismash_zip") or legacy_zip
    canonical = _canonical_by_flavor(strain, root)
    if zip_path is None:
        kind = "AMBIGUOUS_FLAVOR" if len(canonical) > 1 and flavor is None else None
    elif held and zip_path == held.get("antismash_zip"):
        kind = "strain_master"
    elif zip_path in canonical.values():
        kind = "canonical_" + next(fl for fl, p in canonical.items() if p == zip_path)
    elif "Complete_Package" in os.path.basename(zip_path) or any(
            os.path.realpath(zip_path).startswith(os.path.realpath(d) + os.sep) for d in package_home_directories(root)):
        kind = "package_embedded"
    else:
        kind = "raw_result"
    pkg_path = (held or {}).get("mamey_package") or newest
    return {
        "searched_homes": list(_package_homes()),
        "assembly_authority": authority_state,
        "strain": strain,
        "antismash_zip": zip_path,
        "mamey_package": pkg_path,
        "superseded_packages": sorted(older, key=lambda p: (_package_version_key(p), p)),
        "canonical_dir": os.path.join("strain_data", strain),
        "strain_master": held,
        "antismash_source_kind": kind,
        "canonical_antismash": canonical,
        "resolved_from": {
            "antismash_zip": None if zip_path is None else ("strain_master" if held and zip_path == held.get("antismash_zip") else "legacy"),
            "mamey_package": None if pkg_path is None else ("strain_master" if held and pkg_path == held.get("mamey_package") else "legacy"),
        },
    }


def _matched_homes(root: str, home: str) -> list[str]:
    """Built-in homes match case-insensitively; archives and excluded variants do not compete."""
    if home not in _PACKAGE_HOMES:
        return glob.glob(os.path.join(root, home))
    try:
        return [str(p) for p in sorted(Path(root).iterdir())
                if p.is_dir() and fnmatch.fnmatchcase(p.name.casefold(), home.casefold())
                and "archive" not in p.name.casefold() and "excluded" not in p.name.casefold()]
    except OSError:
        return []


def _assembly_authority(strain: str, root: str) -> tuple[dict | None, dict]:
    """Read the current owner table each time; mutable authority is never cached."""
    configured = os.environ.get("SAPOTE_ASSEMBLY_AUTHORITY")
    path = Path(configured or "OFFICIAL_DATA/ASSEMBLY_AUTHORITY.tsv")
    if not path.is_absolute():
        path = Path(root) / path
    if not path.exists() and not configured:
        return None, {"status": "NOT_CONFIGURED", "reason": "No assembly-authority table present"}
    try:
        with path.open(newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh, delimiter="\t")
            required = {"strain", "authoritative_contigs", "authoritative_genome_bp", "clean_package", "clean_antismash_zip"}
            if not required <= set(reader.fieldnames or []):
                raise ValueError("assembly-authority headers missing")
            rows = list(reader)
        seen = set()
        for row in rows:
            sid = row.get("strain", "").strip()
            if not sid or sid in seen or None in row or any(v is None for v in row.values()):
                raise ValueError("duplicate strain or malformed row")
            seen.add(sid)
            if int(row["authoritative_contigs"]) <= 0 or int(row["authoritative_genome_bp"]) <= 0:
                raise ValueError("assembly metrics must be positive")
        matches = [row for row in rows if row["strain"].strip() == strain]
        return (matches[0] if matches else None), {"status": "OWNER_ROW" if matches else "NO_ROW", "reason": str(path)}
    except (OSError, ValueError, TypeError) as exc:
        return None, {"status": "AUTHORITY_INVALID", "reason": f"{type(exc).__name__}: {exc}"}


def _authority_path(value: str, root: str) -> str | None:
    if not value.strip():
        return None
    p = Path(value)
    if not p.is_absolute():
        p = Path(root) / p
    return str(p) if p.exists() else None


def _manifest_matches_authority(path: str, strain: str, authority: dict, flavor: str | None) -> bool:
    try:
        p = Path(path)
        if p.is_dir():
            mp = p / "manifest.json"
            if not mp.is_file():
                mp = p / "package/manifest.json"
            manifest = json.loads(mp.read_text())
        else:
            with zipfile.ZipFile(p) as zf:
                names = [n for n in zf.namelist() if n in ("manifest.json", "package/manifest.json") or n.endswith("/package/manifest.json")]
                if len(names) != 1:
                    return False
                manifest = json.loads(zf.read(names[0]))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("assembly"), dict):
            return False
        asm = manifest["assembly"]
        return (manifest.get("strain") == strain
                and int(asm.get("contigs", -1)) == int(authority["authoritative_contigs"])
                and int(asm.get("genome_bp", -1)) == int(authority["authoritative_genome_bp"])
                and (flavor is None or manifest.get("antismash_profile") == flavor))
    except (OSError, ValueError, TypeError, zipfile.BadZipFile):
        return False


# ---------------------------------------------------------------------------------------------
# Strain Master, reader side (docs/DATA_HOME.md). Writing, init and the self-check live in
# mamey/strain_master.py. Nothing here writes. The master root comes from the caller or from
# SAPOTE_STRAIN_MASTER; this source names no path.
# ---------------------------------------------------------------------------------------------
STRAIN_MASTER_ENV = "SAPOTE_STRAIN_MASTER"
STRAIN_MASTER_CONFIG = "strain_master.json"
STRAIN_MASTER_SCHEMA = "sapote.strain-master.v1"
STRAIN_MASTER_TOP_README = "00 README.md"
RECORD_HEADER = "| File | SHA-256 | Copied from | What it is |"
SUPERSEDED_MARKER = "`Superseded/` holds"
_RECORD_ROW = re.compile(r"^\| `([^`]+)` \| `([0-9a-f]{64})` \|(.*)$")
_NUMBERED = re.compile(r"^\d\d ")
_TEXT_SUFFIXES = (".tsv", ".csv", ".txt", ".md", ".json")
_FLAVORS = ("strict", "relaxed", "loose")

# The standard layout (docs/DATA_HOME.md): numbered areas, then the only subfolders each area may
# hold. "*" means one folder per item (per tree, per figure family, per paper). Every area may also
# hold Superseded/ and its README. "Source tables" holds copied records; "Built" holds tables a
# script generates from them. A new master gets this as its LAYOUT.md; the self-check enforces it.
STRAIN_MASTER_LAYOUT = (
    ("00 Inbox", "Submissions waiting for, or after, verification by a second reviewer.", (
        ("Done", "Accepted and imported submissions: SUBMISSION.md, MANIFEST.tsv, VERIFICATION.md."),
        ("Returned", "Returned submissions, with the reasons."),
        ("*", "One folder per open submission."))),
    ("01 Strains", "Which isolates belong to which study, and their records as deposited.", (
        ("Source tables", "Copied records (strain metadata, hosts, exclusions, rulings), never edited here."),
        ("Figure rosters", "Strain lists behind each figure."),
        ("Built", "Tables a script builds from the source tables; never edited by hand."))),
    ("02 Bioassays", "Bioassay data from plate reader to figure.", (
        ("Raw plate reader", "Plate-reader files exactly as exported."),
        ("Plate maps", "Which sample sits in which well."),
        ("Readings", "Readings joined to plate maps."),
        ("Figure data", "The data each bioassay figure plots."),
        ("Rulings", "Decisions on how readings are scored."),
        ("Scripts", "Scripts that build readings and figure data."),
        ("Audit", "Checks of readings against the raw files."))),
    ("03 Genomes", "Genome-level identity of the isolates.", (
        ("Source tables", "Copied records: genome inventory, reference registries, 16S provenance."),
        ("16S rRNA", "16S rRNA gene identity to the closest type strains, with run receipts."),
        ("TYGS dDDH", "Digital DNA-DNA hybridization to the closest type strains (TYGS)."),
        ("ANI", "Average nucleotide identity to the closest public and type-strain genomes."))),
    ("04 Gene clusters", "Biosynthetic gene cluster results.", (
        ("Source tables", "Copied records: cohort denominators and other cluster-level registries."),
        ("antiSMASH", "antiSMASH result ZIPs named <strain>.zip; a genome's identity is the SHA-256 of its ZIP. "
                      "Flavor-specific results go in strict/, relaxed/ or loose/."),
        ("Mamey packages", "Sealed Mamey Complete_Package ZIPs, copied as sealed; never extracted or edited here."),
        ("Mode B cards", "Authored Mode B cards, each with its verify-modeb result."),
        ("BLASTp evidence", "Raw BLASTp Hit Table CSV or XML2 files, as downloaded."),
        ("Gap rescue", "gap-rescue screen outputs, one run of record per genome. A screen, not adjudicated."),
        ("BiG-SLiCE", "BiG-SLiCE family tables, one subfolder per run."),
        ("BiG-SCAPE", "BiG-SCAPE gene cluster family tables."),
        ("Conserved regions", "Regions conserved in public genomes without a characterized relative."),
        ("Protein space", "Protein-family ordination tables, one subfolder per run."))),
    ("05 Trees", "Complete trees: IQ-TREE report, log, consensus tree and ML tree.", (
        ("Source tables", "Copied records: tree strain and tip metadata, outgroup registry."),
        ("*", "One folder per tree."))),
    ("06 Figures", "Figure data and renders from a sealed route.", (
        ("*", "One folder per figure family."),)),
    ("07 Papers", "The current version of each paper; earlier versions in Superseded/.", (
        ("ToC", "Thesis table of contents."), ("Fact sheets", "Facts staged for each paper."),
        ("Rulings", "Rulings, each written once."), ("Glossary", "Terms used in the papers."),
        ("Scripts", "Scripts that check the papers against the data."), ("*", "One folder per paper."))),
)
STRAIN_MASTER_LAYOUT_FILE = "LAYOUT.md"
STRAIN_MASTER_INBOX = "00 Inbox"
STRAIN_MASTER_LEDGER = "INBOX_LEDGER.tsv"
STRAIN_MASTER_CHANGELOG = "CHANGELOG.md"
_LAYOUT_ROW = re.compile(r"^\| `([^`]+)` \| (file|area|folder) \|")

# Where each kind of Mamey output lands. A master's strain_master.json may override any entry.
STRAIN_MASTER_KINDS = {
    "antismash_zip": "04 Gene clusters/antiSMASH",
    "mamey_package": "04 Gene clusters/Mamey packages",
    "modeb_card": "04 Gene clusters/Mode B cards",
    "blastp_evidence": "04 Gene clusters/BLASTp evidence",
    "gap_rescue": "04 Gene clusters/Gap rescue",
}


_LAYOUT_BULLET = re.compile(r"^- `([^`]+)`")


def read_layout(path: str) -> dict | None:
    """The allowed entries of a LAYOUT.md: ``{"files": set | None, "areas": {area: {"folders",
    "files"}}}``, or None when the file is absent. Two forms are read: a table
    (``| `path` | file/area/folder | what |``, written by ``strain-master init``) and a list of
    folders (``- `area` `` / ``- `area/sub` ``). A list names folders only, so ``files`` is None
    and files are not layout-checked."""
    try:
        with open(path, encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return None
    files: set = set()
    areas: dict = {}
    if not any(_LAYOUT_ROW.match(ln.strip()) for ln in lines):
        for line in lines:
            m = _LAYOUT_BULLET.match(line.strip())
            if m:
                area, _, rest = m.group(1).strip("/").partition("/")
                spec = areas.setdefault(area, {"folders": set(), "files": set()})
                if rest:
                    spec["folders"].add(rest.split("/")[0])
        return {"files": None, "areas": areas}
    for line in lines:
        m = _LAYOUT_ROW.match(line.strip())
        if not m:
            continue
        p, kind = m.group(1).strip("/"), m.group(2)
        area, _, rest = p.partition("/")
        if kind == "area":
            areas.setdefault(area, {"folders": set(), "files": set()})
        elif kind == "folder" and rest:
            areas.setdefault(area, {"folders": set(), "files": set()})["folders"].add(rest)
        elif kind == "file" and rest:
            areas.setdefault(area, {"folders": set(), "files": set()})["files"].add(rest)
        elif kind == "file":
            files.add(p)
    return {"files": files, "areas": areas}


def layout_allows(layout: dict, folder: str) -> bool:
    """True when the area and area subfolder of *folder* are allowed (deeper levels are free)."""
    parts = folder.strip("/").split("/")
    area = layout["areas"].get(parts[0])
    if area is None:
        return False
    return len(parts) == 1 or parts[1] == "Superseded" or parts[1] in area["folders"] or "*" in area["folders"]


def _master_candidate(master: str | None) -> tuple[str | None, str | None]:
    """(what the caller or environment named, existing absolute directory or None).
    ``master=""`` switches the master off for this call."""
    if master == "":
        return None, None
    given = master if master is not None else os.environ.get(STRAIN_MASTER_ENV, "").strip() or None
    if not given:
        return None, None
    path = os.path.abspath(os.path.expanduser(given))
    return given, (path if os.path.isdir(path) else None)


def strain_master_root(master: str | None = None) -> str | None:
    """The configured Strain Master as an absolute directory, or None (not set, or not a folder)."""
    return _master_candidate(master)[1]


def strain_master_config(root: str, path: str | None = None) -> dict:
    """The master's settings: defaults, overlaid by ``strain_master.json`` when present (or by
    *path*, to preview settings before adopting them). Raises ValueError for an unreadable file
    or a different schema; never guesses."""
    cfg = {"schema": STRAIN_MASTER_SCHEMA, "name": os.path.basename(os.path.normpath(root)),
           "raw_stores": [], "folders": dict(STRAIN_MASTER_KINDS),
           "checksum_readmes": ["**/README.md"], "coverage_exempt": [], "direct_store": False,
           "record_homes": [], "package_homes": []}
    path = path or os.path.join(root, STRAIN_MASTER_CONFIG)
    if not os.path.isfile(path):
        return cfg
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{STRAIN_MASTER_CONFIG} unreadable: {type(exc).__name__}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema") != STRAIN_MASTER_SCHEMA:
        raise ValueError(f"{STRAIN_MASTER_CONFIG} schema is not {STRAIN_MASTER_SCHEMA}")
    for key in ("name", "raw_stores", "checksum_readmes", "coverage_exempt", "direct_store", "record_homes",
                "package_homes"):
        if key in data:
            cfg[key] = data[key]
    cfg["folders"].update(data.get("folders") or {})
    return cfg


def _master_package_homes() -> list[str]:
    """Absolute package-home paths from the environment-named master's settings; [] when unset or unreadable."""
    root = _master_candidate(None)[1]
    if root is None:
        return []
    try:
        homes = strain_master_config(root).get("package_homes") or []
    except ValueError:
        return []
    return [os.path.normpath(h if os.path.isabs(h) else os.path.join(root, h)) for h in homes]


def strain_master_folders(root: str) -> list[str]:
    """Data-type folders: each numbered top folder (``NN Name``) and its direct subfolders,
    as ``/``-joined paths relative to *root*. The inbox, ``Superseded`` and hidden folders are skipped."""
    out: list[str] = []
    for top in sorted(os.listdir(root)):
        if not _NUMBERED.match(top) or top == STRAIN_MASTER_INBOX or not os.path.isdir(os.path.join(root, top)):
            continue
        out.append(top)
        for sub in sorted(os.listdir(os.path.join(root, top))):
            if sub.startswith(".") or sub == "Superseded" or not os.path.isdir(os.path.join(root, top, sub)):
                continue
            out.append(top + "/" + sub)
    return out


def read_readme_records(readme: str) -> list[dict]:
    """Rows of a folder README's record table, above any ``Superseded/`` section:
    ``| `file` | `sha256` | copied from | what it is |``."""
    try:
        with open(readme, encoding="utf-8") as fh:
            text = fh.read().split(SUPERSEDED_MARKER)[0]
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        m = _RECORD_ROW.match(line.strip())
        if m:
            cells = [c.strip() for c in m.group(3).rstrip("|").split(" | ")]
            rows.append({"file": m.group(1), "sha256": m.group(2),
                         "origin": cells[0] if cells else "", "what": " | ".join(cells[1:]).strip()})
    return rows


def _strain_pattern(strain: str):
    """The strain ID as a whole token: X-10 does not match X-102, X-10a or X-10-2."""
    return re.compile(r"(?<![A-Za-z0-9])" + re.escape(strain) + r"(?![A-Za-z0-9]|-\d)")


def _match_data_type(data_type: str, folders: list[str], kinds: dict) -> list[str]:
    if data_type in kinds:
        return [kinds[data_type]]
    norm = data_type.strip().strip("/").casefold()
    hits = []
    for f in folders:
        last = f.rsplit("/", 1)[-1]
        if norm in (f.casefold(), last.casefold(), _NUMBERED.sub("", last).casefold()):
            hits.append(f)
    return hits


def _raw_store_lookup(strain: str, store: str, root: str, flavor: str | None) -> dict:
    path = os.path.normpath(store if os.path.isabs(store) else os.path.join(root, store))
    if not os.path.isdir(path):
        return {"root": store, "status": "MISSING"}
    home = strain_data_home(strain, root=path, flavor=flavor, master="")
    flavors = (flavor,) if flavor else _FLAVORS
    canonical = {fl: resolve_antismash_zip(strain, root=path, flavor=fl) for fl in flavors}
    return {"root": store, "status": "SEARCHED", "antismash_zip": home["antismash_zip"],
            "mamey_package": home["mamey_package"],
            "canonical_antismash": {fl: p for fl, p in canonical.items() if p}}


def strain_master_record(data_type: str, strain: str | None = None, master: str | None = None,
                         flavor: str | None = None, scan_limit: int = 50_000_000) -> dict:
    """Where *data_type* lives in the Strain Master, and what its README records.

    *data_type* is a folder name (``ANI``, ``Mode B cards``), a path (``03 Genomes/ANI``) or an
    output kind (``mamey_package``). With *strain*, also returns the registered files whose name
    or description carries the strain ID, the registered text tables that mention it, files on
    disk with the ID that the README does not list, and, when the master holds nothing for the
    strain, what each configured raw store holds. Status is one of NOT_CONFIGURED,
    MASTER_NOT_FOUND, CONFIG_INVALID, NO_SUCH_TYPE, AMBIGUOUS, FOUND or NOT_IN_MASTER.
    Reader only; a missing record is "not found here", never a scientific absence.
    """
    given, root = _master_candidate(master)
    out: dict = {"master": root or given, "data_type": data_type, "strain": strain}
    if given is None:
        return {**out, "status": "NOT_CONFIGURED",
                "reason": f"no master given and {STRAIN_MASTER_ENV} is not set"}
    if root is None:
        return {**out, "status": "MASTER_NOT_FOUND", "reason": "not a folder"}
    try:
        cfg = strain_master_config(root)
    except ValueError as exc:
        return {**out, "status": "CONFIG_INVALID", "reason": str(exc)}
    folders = strain_master_folders(root)
    hits = _match_data_type(data_type, folders, cfg["folders"])
    if not hits:
        return {**out, "status": "NO_SUCH_TYPE", "known_types": folders}
    if len(hits) > 1:
        return {**out, "status": "AMBIGUOUS", "candidates": hits}
    folder = hits[0]
    readme = os.path.join(root, folder, "README.md")
    records = read_readme_records(readme)
    out.update(folder=folder, readme=folder + "/README.md" if os.path.isfile(readme) else None,
               records=records)
    if strain is None:
        return {**out, "status": "FOUND"}
    pat = _strain_pattern(strain)
    named = [r for r in records if pat.search(r["file"]) or pat.search(r["what"])]
    mentioning = []
    for r in records:
        p = os.path.join(root, folder, r["file"])
        if r in named or not r["file"].endswith(_TEXT_SUFFIXES) or not os.path.isfile(p):
            continue
        if os.path.getsize(p) > scan_limit:
            mentioning.append({"file": r["file"], "lines": None, "note": "larger than the scan limit; not read"})
            continue
        with open(p, encoding="utf-8", errors="replace") as fh:
            n = sum(1 for line in fh if pat.search(line))
        if n:
            mentioning.append({"file": r["file"], "lines": n})
    listed = {r["file"] for r in records}
    folder_abs = os.path.join(root, folder)
    unregistered = sorted(f for f in os.listdir(folder_abs)
                          if os.path.isfile(os.path.join(folder_abs, f)) and pat.search(f) and f not in listed)
    out.update(strain_records=named, files_mentioning=mentioning, unregistered=unregistered)
    if named or mentioning:
        return {**out, "status": "FOUND"}
    out["raw_stores"] = [_raw_store_lookup(strain, s, root, flavor) for s in cfg["raw_stores"]]
    return {**out, "status": "NOT_IN_MASTER"}


def _master_strain_files(strain: str, master: str | None, flavor: str | None) -> dict | None:
    """README-registered antiSMASH ZIP and newest sealed package for *strain* in the master, or None
    when no master is configured. Registered means listed in that folder's README record table."""
    given, root = _master_candidate(master)
    if given is None:
        return None
    if root is None:
        return {"root": given, "status": "MASTER_NOT_FOUND", "antismash_zip": None, "mamey_package": None}
    try:
        cfg = strain_master_config(root)
    except ValueError as exc:
        return {"root": root, "status": "CONFIG_INVALID", "reason": str(exc),
                "antismash_zip": None, "mamey_package": None}
    zdir = os.path.join(root, cfg["folders"]["antismash_zip"], *([flavor] if flavor else []))
    zname = strain + ".zip"
    zpath = os.path.join(zdir, zname)
    zip_hit = (zpath if any(r["file"] == zname for r in read_readme_records(os.path.join(zdir, "README.md")))
               and os.path.isfile(zpath) and zip_has_antismash_json(zpath) else None)
    pdir = os.path.join(root, cfg["folders"]["mamey_package"])
    globs = (strain + "_SapoteMamey_v*_*Complete_Package.zip", strain + "_Mamey_v*_*Complete_Package.zip")
    pkgs = [os.path.join(pdir, r["file"]) for r in read_readme_records(os.path.join(pdir, "README.md"))
            if any(fnmatch.fnmatch(r["file"], g) for g in globs)
            and (flavor is None or _package_flavor(r["file"]) == flavor)
            and os.path.isfile(os.path.join(pdir, r["file"]))]
    pkg_hit = max(pkgs, key=lambda p: (_package_version_key(p), p)) if pkgs else None
    return {"root": root, "status": "SEARCHED", "antismash_zip": zip_hit, "mamey_package": pkg_hit}


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Resolve a strain's canonical data home.")
    ap.add_argument("strains", nargs="+", help="strain IDs, e.g. AS-XXX AS-XXX")
    ap.add_argument("--root", default=".", help="workspace root (default: .)")
    ap.add_argument("--master", default=None, help=f"Strain Master (default: ${STRAIN_MASTER_ENV})")
    ap.add_argument("--type", default=None, help="data type to look up in the master, e.g. ANI or mamey_package")
    args = ap.parse_args()
    for s in args.strains:
        result = (strain_master_record(args.type, strain=s, master=args.master) if args.type
                  else strain_data_home(s, root=args.root, master=args.master))
        emit(json.dumps(result, indent=1))
