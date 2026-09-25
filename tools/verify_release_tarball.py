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
import hashlib
import sys
import tarfile
import zipfile
from pathlib import Path

JUNK_NAMES = (".DS_Store",)
JUNK_PARTS = ("__pycache__", ".pytest_cache")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def zip_digests(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as z:
        return {i.filename: _sha(z.read(i)) for i in z.infolist() if not i.is_dir()}


def check(tarball: Path, sealed_zip: Path) -> list[str]:
    problems: list[str] = []
    expected = zip_digests(sealed_zip)
    top = tarball.name[: -len(".tar.gz")] if tarball.name.endswith(".tar.gz") else tarball.stem
    seen: dict[str, str] = {}
    junk: list[str] = []
    with tarfile.open(tarball, "r:gz") as t:
        for m in t.getmembers():
            name = m.name[2:] if m.name.startswith("./") else m.name
            head, _, rel = name.partition("/")
            base = name.rsplit("/", 1)[-1]
            if base.startswith("._") or base in JUNK_NAMES or any(p in name.split("/") for p in JUNK_PARTS):
                junk.append(name)
                continue
            if head != top or name.startswith("/") or ".." in name.split("/"):
                problems.append(f"member outside '{top}/': {name}")
                continue
            if m.isdir():
                continue
            if not m.isfile():
                problems.append(f"non-regular member (link/device) not in the sealed ZIP: {name}")
                continue
            seen[rel] = _sha(t.extractfile(m).read())
    if junk:
        problems.append(f"{len(junk)} junk member(s) (._*, .DS_Store, __pycache__), first: {', '.join(junk[:5])}")
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
    ns = ap.parse_args(argv)
    for p in (ns.tarball, ns.sealed_zip):
        if not p.is_file():
            print(f"REFUSED: not a file: {p}", file=sys.stderr)
            return 2
    problems = check(ns.tarball, ns.sealed_zip)
    if problems:
        print(f"release tarball: REFUSED ({ns.tarball.name} vs {ns.sealed_zip.name})")
        for p in problems:
            print(f"  - {p}")
        return 2
    print(f"release tarball: PASS ({ns.tarball.name} carries exactly the files of {ns.sealed_zip.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
