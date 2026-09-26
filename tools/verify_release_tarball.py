#!/usr/bin/env python3
"""Refuse a release tarball unless it carries exactly the sealed CODE ZIP's files, byte for byte.

The sealed ZIP is the canonical, validated artifact (SEAL_RECEIPT.json). A .tar.gz published beside
it is a repackaging, and no cut gate inspects it: the v9.7.441 GitHub tarball carried 3,294 macOS
AppleDouble (._*) files that Linux tar extracts as real files, which broke pytest collection and
failed --strict-membership. Comparing the tarball to the sealed ZIP lets it inherit the seal's
validation instead of needing its own.

Usage: verify_release_tarball.py <tarball.tar.gz> --zip <sealed CODE zip>
Exit 0 = PASS; 2 = REFUSED (every reason is printed). Standard library only; nothing is extracted.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import posixpath
import re
import shutil
import stat
import sys
import tarfile
import tempfile
import unicodedata
import zipfile
from pathlib import Path

JUNK_NAMES = (".DS_Store",)
JUNK_PARTS = ("__pycache__", ".pytest_cache")


def _stream_sha(stream) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
    return digest.hexdigest()


def check_seal_receipt(receipt: Path, sealed_zip: Path) -> list[str]:
    """Bind the supplied ZIP bytes to an explicit local CODE seal receipt."""
    try:
        data = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"unreadable seal receipt: {type(exc).__name__}: {exc}"]
    if not isinstance(data, dict):
        return ["seal receipt is not a JSON object"]
    problems = []
    if data.get("schema") != "sapote-mamey.local-code-seal.v1":
        problems.append("seal receipt schema is not sapote-mamey.local-code-seal.v1")
    if data.get("status") != "SEALED_LOCAL_CODE" or data.get("tier") != "CODE":
        problems.append("seal receipt does not identify a sealed local CODE tier")
    archive = data.get("archive")
    if not isinstance(archive, dict):
        return problems + ["seal receipt has no archive object"]
    if archive.get("path") != sealed_zip.name:
        problems.append("seal receipt archive filename does not match supplied ZIP")
    expected = archive.get("sha256")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None:
        problems.append("seal receipt archive SHA-256 is missing or malformed")
    else:
        digest = hashlib.sha256()
        with sealed_zip.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected.lower():
            problems.append("supplied ZIP SHA-256 differs from seal receipt")
    expected_bytes = archive.get("bytes")
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes != sealed_zip.stat().st_size:
        problems.append("supplied ZIP byte count differs from seal receipt")
    return problems


def zip_digests(path: Path) -> dict[str, str]:
    digests: dict[str, str] = {}
    with zipfile.ZipFile(path) as z:
        for info in z.infolist():
            if not info.is_dir():
                with z.open(info) as stream:
                    digests[info.filename] = _stream_sha(stream)
    return digests


def _canonical_member_path(name: str, *, directory: bool = False) -> bool:
    path = name[:-1] if directory and name.endswith("/") else name
    return (
        bool(path)
        and not path.startswith("/")
        and "\\" not in path
        and "\x00" not in path
        and re.match(r"^[A-Za-z]:", path) is None
        and posixpath.normpath(path) == path
        and all(part not in ("", ".", "..") for part in path.split("/"))
    )


def check(tarball: Path, sealed_zip: Path) -> list[str]:
    problems: list[str] = []
    with zipfile.ZipFile(sealed_zip) as z:
        infos = z.infolist()
        noncanonical_zip = sorted(i.filename for i in infos
                                  if not _canonical_member_path(i.filename, directory=i.is_dir()))
        if noncanonical_zip:
            return [f"{len(noncanonical_zip)} noncanonical sealed ZIP member path(s), first: "
                    + ", ".join(noncanonical_zip[:5])]
        special_zip = []
        for info in infos:
            kind = stat.S_IFMT((info.external_attr >> 16) & 0xffff)
            allowed = (0, stat.S_IFDIR) if info.is_dir() else (0, stat.S_IFREG)
            if kind not in allowed:
                special_zip.append(info.filename)
        if special_zip:
            return [f"{len(special_zip)} non-regular sealed ZIP member type(s), first: "
                    + ", ".join(sorted(special_zip)[:5])]
        zip_files = {i.filename for i in infos if not i.is_dir()}
        prefix_collisions = []
        for info in infos:
            path = info.filename.rstrip("/") if info.is_dir() else info.filename
            parts = path.split("/")
            for depth in range(1, len(parts) + int(info.is_dir())):
                parent = "/".join(parts[:depth])
                if parent in zip_files:
                    prefix_collisions.append(f"{parent} -> {info.filename}")
        if prefix_collisions:
            return [f"{len(prefix_collisions)} sealed ZIP file/directory collision(s), first: "
                    + ", ".join(prefix_collisions[:5])]
        portable_paths: dict[str, str] = {}
        portable_aliases: set[tuple[str, str]] = set()
        for info in infos:
            path = info.filename.rstrip("/") if info.is_dir() else info.filename
            parts = path.split("/")
            for depth in range(1, len(parts) + 1):
                prefix = "/".join(parts[:depth])
                key = unicodedata.normalize("NFC", unicodedata.normalize("NFC", prefix).casefold())
                prior = portable_paths.setdefault(key, prefix)
                if prior != prefix:
                    portable_aliases.add((prior, prefix))
        if portable_aliases:
            examples = sorted(portable_aliases)
            return [f"{len(examples)} portable sealed ZIP path alias(es), first: "
                    + ", ".join(f"{a} / {b}" for a, b in examples[:5])]
        zip_counts = Counter(i.filename for i in infos)
        allowed_dirs = {i.filename.rstrip("/") for i in infos if i.is_dir()}
    expected = zip_digests(sealed_zip)
    for filename in expected:
        parts = filename.split("/")
        allowed_dirs.update("/".join(parts[:index]) for index in range(1, len(parts)))
    duplicate_zip = sorted(name for name, count in zip_counts.items() if count > 1)
    if duplicate_zip:
        problems.append(
            f"{len(duplicate_zip)} duplicate sealed ZIP member name(s), first: "
            + ", ".join(duplicate_zip[:5]))
    top = tarball.name[: -len(".tar.gz")] if tarball.name.endswith(".tar.gz") else tarball.stem
    expected_top = sealed_zip.stem
    if top != expected_top:
        problems.append(f"tarball bundle name {top!r} differs from sealed ZIP bundle name {expected_top!r}")
    seen: dict[str, str] = {}
    member_names: set[str] = set()
    junk: list[str] = []
    # A faithful repackaging can contain each sealed file, each directory in
    # the ZIP's path tree, and one enclosing bundle directory at most once.
    member_allowance = len(expected) + len(allowed_dirs) + 1
    member_count = 0
    limit_hit = False
    with tarfile.open(tarball, "r|gz") as t:
        for m in t:
            member_count += 1
            # Inspect one excess entry so an existing specific diagnostic
            # (for example, an untracked directory) remains available.
            if member_count > member_allowance + 1:
                problems.append(f"tarball member count exceeds sealed ZIP allowance ({member_allowance})")
                limit_hit = True
                break
            name = m.name[2:] if m.name.startswith("./") else m.name
            if name in member_names:
                problems.append(f"duplicate tar member name: {name}")
                continue
            member_names.add(name)
            head, _, rel = name.partition("/")
            base = name.rsplit("/", 1)[-1]
            if base.startswith("._") or base in JUNK_NAMES or any(p in name.split("/") for p in JUNK_PARTS):
                junk.append(name)
                continue
            if head != top or name.startswith("/") or ".." in name.split("/"):
                problems.append(f"member outside '{top}/': {name}")
                continue
            if m.isdir():
                if m.mode & 0o7022 or (m.mode & 0o500) != 0o500:
                    problems.append(f"unsafe directory mode {m.mode:#o}: {name}")
                directory = rel.rstrip("/")
                canonical = posixpath.normpath(directory) if directory else ""
                if canonical in expected:
                    problems.append(f"directory collides with sealed file: {name}")
                elif directory != canonical or (directory and not _canonical_member_path(directory)):
                    problems.append(f"noncanonical tar directory: {name}")
                elif directory and directory not in allowed_dirs:
                    problems.append(f"untracked tar directory: {name}")
                continue
            if not m.isfile():
                problems.append(f"non-regular member (link/device) not in the sealed ZIP: {name}")
                continue
            if not _canonical_member_path(rel):
                problems.append(f"noncanonical tar file: {name}")
                continue
            if m.mode & 0o7022 or not m.mode & 0o400:
                problems.append(f"unsafe file mode {m.mode:#o}: {name}")
                continue
            with t.extractfile(m) as stream:
                seen[rel] = _stream_sha(stream)
    if junk:
        qualifier = " observed" if limit_hit else ""
        problems.append(f"{len(junk)}{qualifier} junk member(s) (._*, .DS_Store, __pycache__), first: {', '.join(junk[:5])}")
    if limit_hit:
        return problems  # The unscanned tail cannot support missing/difference claims.
    missing = sorted(set(expected) - set(seen))
    extra = sorted(set(seen) - set(expected))
    changed = sorted(k for k in set(seen) & set(expected) if seen[k] != expected[k])
    if missing:
        problems.append(f"{len(missing)} sealed file(s) missing from the tarball, first: {', '.join(missing[:5])}")
    if extra:
        problems.append(f"{len(extra)} file(s) not in the sealed ZIP, first: {', '.join(extra[:5])}")
    if changed:
        problems.append(f"{len(changed)} file(s) differ from the sealed ZIP, first: {', '.join(changed[:5])}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("tarball", type=Path)
    ap.add_argument("--zip", dest="sealed_zip", type=Path, required=True)
    ap.add_argument("--seal-receipt", type=Path, required=True,
                    help="selected local CODE seal receipt binding the supplied ZIP")
    ns = ap.parse_args(argv)
    for p in (ns.tarball, ns.sealed_zip, ns.seal_receipt):
        if not p.is_file():
            print(f"REFUSED: not a file: {p}", file=sys.stderr)
            return 2
    # Both checks must read the same ZIP bytes even if the supplied path changes.
    with tempfile.TemporaryDirectory(prefix=".release_tarball_verify.") as scratch:
        snapshot = Path(scratch) / ns.sealed_zip.name
        try:
            shutil.copyfile(ns.sealed_zip, snapshot)
        except OSError as exc:
            print(f"REFUSED: cannot snapshot supplied ZIP: {exc}", file=sys.stderr)
            return 2
        problems = check_seal_receipt(ns.seal_receipt, snapshot)
        problems.extend(check(ns.tarball, snapshot))
    if problems:
        print(f"release tarball: REFUSED ({ns.tarball.name} vs {ns.sealed_zip.name})")
        for p in problems:
            print(f"  - {p}")
        return 2
    print(f"release tarball: PASS ({ns.tarball.name} carries exactly the files of {ns.sealed_zip.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
