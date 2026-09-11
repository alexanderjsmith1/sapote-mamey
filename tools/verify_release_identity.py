#!/usr/bin/env python3
"""verify_release_identity.py — fail-closed release identity + LLM bootstrap freshness gate.

Checks that the bundle version, engine version, build stamp, and required LLM
read-proof sentence agree across the source tree and, optionally, every tier ZIP.
This catches the v9.7.139 wrapper/stale-internal failure class before a cut is
published.

v9.7.409 (CLAUDE identity_verify_content lane): this gate historically cross-checked only
version/engine/build STRINGS. A source file could be edited byte-for-byte while every version
string stayed current, and this gate still printed "PASS" — hollow assurance that the tree is
unmodified. It now ALSO folds in the checksum-manifest verdict (tools/check_release_manifest's
checksum_problems: does the tree's content match SOURCE_CHECKSUMS_SHA256.txt?) and surfaces any
mismatch as a DISTINCT `content:` failure. Identity can no longer report verified while content
differs from the manifest. Deterministic and offline: content verification is local sha256 only.

Usage:
  python tools/verify_release_identity.py            # defaults --root to the bundle root
  python tools/verify_release_identity.py --root .
  python tools/verify_release_identity.py --root . --tiers-dir dist/
  python tools/verify_release_identity.py --root . --json
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
from check_release_manifest import checksum_problems as _checksum_problems  # noqa: E402  v9.7.409

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

# v9.7.409: the bundle root, resolved from this file's location, is the sane default --root and the
# fallback when a caller runs the gate from an unrelated cwd. tools/ is one level under the root.
_BUNDLE_ROOT = Path(__file__).resolve().parents[1]

# The three files truth_from_root() must read; their absence is what raised a raw FileNotFoundError
# when --root defaulted to CWD and the gate was run from elsewhere. Used for a clear, early refusal.
_ROOT_MARKERS = ("pyproject.toml", "mamey/__init__.py", "BUILD_STAMP.txt")

READ_PROOF = "The sky is not red, it is blue, just like the ocean."
REQUIRED_TEXT_PROBES = [
    "AGENTS.md", "CLAUDE.md", "README.md", "TAG", "BUILD_STAMP.txt",
    "pyproject.toml", "mamey/__init__.py",
]
OPTIONAL_TEXT_PROBES = []
TEXT_PROBES = REQUIRED_TEXT_PROBES + OPTIONAL_TEXT_PROBES
HANDSHAKE_FILES = ["AGENTS.md", "CLAUDE.md"]


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def truth_from_root(root: Path) -> dict[str, str]:
    pyproject = _read_text(root / "pyproject.toml")
    init = _read_text(root / "mamey" / "__init__.py")
    stamp_txt = _read_text(root / "BUILD_STAMP.txt")
    engine = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', pyproject)
    bundle = re.search(r'(?m)^\s*bundle_version\s*=\s*"([^"]+)"', pyproject)
    init_engine = re.search(r'__version__\s*=\s*"([^"]+)"', init)
    init_bundle = re.search(r'BUNDLE_VERSION\s*=\s*"([^"]+)"', init)
    build = re.search(r'(?m)^build=(\S+)', stamp_txt)
    stamp_bundle = re.search(r'(?m)^version=(\S+)', stamp_txt)
    errs = []
    vals = {
        "engine": engine.group(1) if engine else "",
        "bundle": bundle.group(1) if bundle else "",
        "build": build.group(1) if build else "",
        "init_engine": init_engine.group(1) if init_engine else "",
        "init_bundle": init_bundle.group(1) if init_bundle else "",
        "stamp_bundle": stamp_bundle.group(1) if stamp_bundle else "",
    }
    if vals["engine"] != vals["init_engine"]:
        errs.append(f"pyproject engine {vals['engine']} != mamey.__version__ {vals['init_engine']}")
    if vals["bundle"] != vals["init_bundle"]:
        errs.append(f"pyproject bundle {vals['bundle']} != mamey.BUNDLE_VERSION {vals['init_bundle']}")
    if vals["bundle"] != vals["stamp_bundle"]:
        errs.append(f"pyproject bundle {vals['bundle']} != BUILD_STAMP version {vals['stamp_bundle']}")
    vals["truth_errors"] = errs
    return vals


def _probe_text(name: str, text: str, truth: dict[str, str], where: str) -> list[str]:
    errs: list[str] = []
    bundle = truth["bundle"]
    engine = truth["engine"]
    build = truth["build"]
    if name in HANDSHAKE_FILES and READ_PROOF not in text:
        errs.append(f"{where}:{name}: missing mandatory read-proof sentence")
    if name in TEXT_PROBES:
        # Require all current-source probes to avoid a stale wrapper with old internals.
        if bundle and f"v{bundle}" not in text and f'bundle_version = "{bundle}"' not in text and f"version={bundle}" not in text and f"BUNDLE_VERSION = \"{bundle}\"" not in text:
            errs.append(f"{where}:{name}: does not contain current bundle v{bundle}")
        if engine and name in {"AGENTS.md", "CLAUDE.md", "README.md", "TAG", "BUILD_STAMP.txt", "pyproject.toml", "mamey/__init__.py"}:
            if engine not in text:
                errs.append(f"{where}:{name}: does not contain current engine {engine}")
        # BC2-VRI-01 (v9.7.395): TAG was missing from this membership set. TAG genuinely carries a
        # build stamp (e.g. "build: 20260831v97394a", per its own on-disk format), and this whole
        # module's stated purpose is catching "the v9.7.139 wrapper/stale-internal failure class"
        # — a doc/probe file that still names the current bundle+engine version but has a stale
        # build behind it. Excluding TAG from the build check meant a stale build stamp inside TAG
        # specifically (bundle and engine version both still current) was invisible to this
        # fail-closed gate: reproduced by rolling TAG's build line back to an old stamp while
        # leaving BUILD_STAMP.txt/pyproject.toml/mamey/__init__.py current — the gate still printed
        # "PASS" with exit 0.
        if build and name in {"AGENTS.md", "CLAUDE.md", "README.md", "TAG", "BUILD_STAMP.txt"}:
            if build not in text:
                errs.append(f"{where}:{name}: does not contain current build {build}")
    return errs


def check_tree(root: Path, truth: dict[str, str]) -> list[str]:
    errs: list[str] = []
    for rel in REQUIRED_TEXT_PROBES:
        p = root / rel
        if not p.exists():
            errs.append(f"source:{rel}: missing")
            continue
        errs.extend(_probe_text(rel, _read_text(p), truth, "source"))
    for rel in OPTIONAL_TEXT_PROBES:
        p = root / rel
        if p.exists():
            errs.extend(_probe_text(rel, _read_text(p), truth, "source"))
    errs.extend(truth.get("truth_errors", []))
    return errs


def _zip_read(zf: zipfile.ZipFile, rel: str) -> str | None:
    names = zf.namelist()
    if rel in names:
        return zf.read(rel).decode("utf-8", "replace")

    # Prefer the file under the single top-level package directory. A plain suffix
    # search is ambiguous for common names such as README.md because docs/README.md
    # can also exist; that false-positive ambiguity made valid tier ZIPs look as if
    # their root README.md was missing.
    top_dirs = sorted({n.split("/", 1)[0] for n in names if "/" in n and n.split("/", 1)[0]})
    if len(top_dirs) == 1:
        candidate = f"{top_dirs[0]}/{rel}"
        if candidate in names:
            return zf.read(candidate).decode("utf-8", "replace")

    suffix = "/" + rel
    matches = [n for n in names if n.endswith(suffix)]
    if len(matches) == 1:
        return zf.read(matches[0]).decode("utf-8", "replace")
    return None


def check_tier_zip(path: Path, truth: dict[str, str]) -> list[str]:
    errs: list[str] = []
    if f"v{truth['bundle']}" not in path.name:
        errs.append(f"tier:{path.name}: filename does not contain v{truth['bundle']}")
    try:
        with zipfile.ZipFile(path) as zf:
            for rel in REQUIRED_TEXT_PROBES:
                txt = _zip_read(zf, rel)
                if txt is None:
                    errs.append(f"tier:{path.name}:{rel}: missing")
                    continue
                errs.extend(_probe_text(rel, txt, truth, f"tier:{path.name}"))
            for rel in OPTIONAL_TEXT_PROBES:
                txt = _zip_read(zf, rel)
                if txt is not None:
                    errs.extend(_probe_text(rel, txt, truth, f"tier:{path.name}"))
    except zipfile.BadZipFile as exc:
        errs.append(f"tier:{path.name}: BadZipFile: {exc}")
    return errs


def check_content(root: Path) -> list[str]:
    """Fold the checksum-manifest verdict into the identity gate (v9.7.409).

    Runs tools/check_release_manifest's checksum_problems — does every SOURCE_CHECKSUMS_SHA256.txt
    entry recompute and exist? — and re-emits any finding with a DISTINCT `content:` prefix so it is
    never mistaken for (or masked by) a version-string check. On the pristine tree checksum_problems
    returns [], so identity still passes; if any file's bytes drift while its version strings stay
    current, the mismatch shows up here and flips the verdict to FAIL. Local sha256 only — offline
    and deterministic. A hard failure inside the manifest reader is itself surfaced as a content
    error (fail-closed), never swallowed into a spurious PASS.
    """
    try:
        problems, _stats = _checksum_problems(root)
    except Exception as exc:  # never let a reader crash masquerade as verified content
        return [f"content: could not verify tree against SOURCE_CHECKSUMS_SHA256.txt: {exc!r}"]
    return [f"content: {p}" for p in problems]


def _root_marker_errors(root: Path) -> list[str]:
    """Clear, early refusal when --root does not point at a bundle root (v9.7.409).

    Previously --root defaulted to CWD and truth_from_root() opened pyproject.toml / mamey/__init__.py
    / BUILD_STAMP.txt directly, so running the gate from an unrelated directory raised a raw
    FileNotFoundError with a traceback instead of a usable message. This names exactly what is
    missing and points at the sane default.
    """
    missing = [m for m in _ROOT_MARKERS if not (root / m).exists()]
    if missing:
        return [
            f"root: {root} is not a bundle root — missing {', '.join(missing)}. "
            f"Pass --root pointing at the bundle root (the directory containing pyproject.toml "
            f"and mamey/), or omit --root to use the default ({_BUNDLE_ROOT})."
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(_BUNDLE_ROOT))  # v9.7.409: sane default, not CWD
    ap.add_argument("--tiers-dir", default=None)
    ap.add_argument("--json", action="store_true")
    ns = ap.parse_args(argv)
    root = Path(ns.root).resolve()

    # v9.7.409: refuse clearly if --root is not a bundle root, instead of a raw FileNotFoundError.
    marker_errors = _root_marker_errors(root)
    if marker_errors:
        payload = {"status": "FAIL", "truth": {}, "tier_zips_checked": 0, "errors": marker_errors}
        if ns.json:
            emit(json.dumps(payload, indent=2))
        else:
            emit(f"release identity: FAIL (root {root})")
            for e in marker_errors:
                emit("  FAIL:", e)
        return 2

    truth = truth_from_root(root)
    errors = check_tree(root, truth)
    errors.extend(check_content(root))  # v9.7.409: content must match the checksum manifest
    tier_count = 0
    if ns.tiers_dir:
        for zp in sorted(Path(ns.tiers_dir).glob("*.zip")):
            tier_count += 1
            errors.extend(check_tier_zip(zp, truth))
    payload = {"status": "PASS" if not errors else "FAIL", "truth": truth, "tier_zips_checked": tier_count, "errors": errors}
    if ns.json:
        emit(json.dumps(payload, indent=2))
    else:
        emit(f"release identity: {payload['status']} (bundle v{truth['bundle']} / engine {truth['engine']} · build {truth['build']})")
        for e in errors:
            emit("  FAIL:", e)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
