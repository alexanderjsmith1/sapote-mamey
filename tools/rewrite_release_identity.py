#!/usr/bin/env python3
"""Rewrite cut-time bundle/build identity without platform-specific ``sed -i``.

Only the three cut-owned source fields are changed here. ``sync_version.py``
remains responsible for propagating those values to the rest of the bundle.
Every input is parsed and validated before any file is replaced.
"""

from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import os
from pathlib import Path
import re
import tempfile


BUNDLE_RE = re.compile(r"^\d+\.\d+\.\d+[a-z]?$", re.ASCII)
STAMP_RE = re.compile(r"^\d{8}v\d+[a-z]$", re.ASCII)


def _replace_once(text: str, pattern: re.Pattern[str], replacement: str, label: str) -> str:
    updated, count = pattern.subn(replacement, text)
    if count != 1:
        raise ValueError(f"{label}: expected exactly one match, observed {count}")
    return updated


def desired_files(root: Path, bundle: str, stamp: str) -> dict[Path, str]:
    pyproject = root / "pyproject.toml"
    build_stamp = root / "BUILD_STAMP.txt"
    tier_manifest = root / "TIER_MANIFEST.txt"
    changelog = root / "CHANGELOG.md"
    for path in (pyproject, build_stamp, tier_manifest):
        if not path.is_file():
            raise FileNotFoundError(path)

    pyproject_text = pyproject.read_text(encoding="utf-8")
    pyproject_text = _replace_once(
        pyproject_text,
        re.compile(
            r'(?ms)(^\[tool\.sapote\]\s*$.*?^bundle_version\s*=\s*")[^"]+("\s*(?:#.*)?$)'
        ),
        rf"\g<1>{bundle}\g<2>",
        "pyproject [tool.sapote].bundle_version",
    )

    build_text = build_stamp.read_text(encoding="utf-8")
    build_text = _replace_once(
        build_text,
        re.compile(r"(?m)^version=[^\r\n]+$"),
        f"version={bundle}",
        "BUILD_STAMP version",
    )
    build_text = _replace_once(
        build_text,
        re.compile(r"(?m)^build=[^\r\n]+$"),
        f"build={stamp}",
        "BUILD_STAMP build",
    )

    tier_text = tier_manifest.read_text(encoding="utf-8")
    tier_text = _replace_once(
        tier_text,
        re.compile(r"(?m)^(# TIER_MANIFEST tier=\S+ version=)\S+( stamp=)\S+$"),
        rf"\g<1>{bundle}\g<2>{stamp}",
        "TIER_MANIFEST header",
    )

    result = {pyproject: pyproject_text, build_stamp: build_text, tier_manifest: tier_text}

    # v9.7.373: the CHANGELOG head build token is cut-owned too, WHEN a CHANGELOG is present. The
    # author writes the entry with a provisional letter before the cut; release_cut computes the FINAL
    # $STAMP from --letter. Left unmanaged, the head build token drifts from BUILD_STAMP (the .372 E-01
    # erratum: head said ...v97372a, stamp was ...v97372b). Anchored with \A so only the TOP entry's
    # token is rewritten; every historical entry carries its own `build …` token and must not be
    # touched. Identity-only fixtures with no CHANGELOG.md (e.g. the release-integrity tests) skip it.
    if changelog.is_file():
        result[changelog] = _replace_once(
            changelog.read_text(encoding="utf-8"),
            re.compile(r"(\A# v[^\n]*?\bbuild )\S+"),
            rf"\g<1>{stamp}",
            "CHANGELOG head build token",
        )
    return result


def atomic_write(path: Path, content: str) -> None:
    mode = path.stat().st_mode
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = Path(handle.name)
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle_version")
    parser.add_argument("build_stamp")
    parser.add_argument("--root", default=".")
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args(argv)

    if not BUNDLE_RE.fullmatch(args.bundle_version):
        parser.error(f"invalid bundle version: {args.bundle_version!r}")
    if not STAMP_RE.fullmatch(args.build_stamp):
        parser.error(f"invalid build stamp: {args.build_stamp!r}")

    root = Path(args.root).resolve()
    desired = desired_files(root, args.bundle_version, args.build_stamp)
    drift = [path for path, content in desired.items() if path.read_text(encoding="utf-8") != content]
    if args.check:
        if drift:
            for path in drift:
                emit(f"DRIFT {path.relative_to(root)}")
            return 1
        emit(f"release identity OK: bundle={args.bundle_version} build={args.build_stamp}")
        return 0

    for path in drift:
        atomic_write(path, desired[path])
        emit(f"updated {path.relative_to(root)}")
    emit(f"release identity written: bundle={args.bundle_version} build={args.build_stamp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
