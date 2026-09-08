#!/usr/bin/env python3
"""check_release_manifest.py — verify the bundle's integrity artifacts against the tree itself.

v9.7.251. Recommended by the v9.7.250 release check, which found that **all five governance gates and
`release-qa` pass on a bundle whose checksum manifest fails on 128 files, whose tier manifest contradicts
its own build stamp, and which lists two files it does not contain.**

`verify_release_identity.py` checks that version / engine / build agree *with each other*. Nothing
recomputed a checksum or walked the manifest. This does.

Three assertions, all against the real tree:

  1. every `SOURCE_CHECKSUMS_SHA256.txt` entry recomputes to its recorded digest
  2. every entry names a file that exists (a manifest that references absent files is broken,
     regardless of whether the content mattered)
  3. `TIER_MANIFEST.txt`'s `stamp=` equals `BUILD_STAMP.txt`'s `build=`

Ordering note, learned the hard way: the checksum manifest must be regenerated **as the last step of a
cut, after any redaction**. A hand-zipped working tree carries whatever manifest was last written — which
is how a v9.7.233 checksum file shipped inside a v9.7.250 artifact.

Exit 0 = the artifacts describe the tree. Non-zero = they do not.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import hashlib
import pathlib
import re
import stat
import sys
from pathlib import PurePosixPath, PureWindowsPath

SKIP_SELF = {"SOURCE_CHECKSUMS_SHA256.txt"}


def _digest(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class _UnsafeChecksumTarget(ValueError):
    """A manifest record does not identify an admitted regular in-root file."""


def _checksum_target(root: pathlib.Path, rel: str) -> tuple[pathlib.Path, str]:
    """Validate *rel* before returning its regular, non-symlink target.

    Manifest records are untrusted input.  Apply portable lexical checks first,
    then walk every existing component with ``lstat`` so neither a leaf symlink
    nor a symlinked parent can redirect the verifier outside the release root.
    """
    portable = rel.replace("\\", "/")
    logical = PurePosixPath(portable)
    if (
        "\x00" in portable
        or logical.is_absolute()
        or PureWindowsPath(portable).drive
        or ".." in logical.parts
        or not logical.parts
    ):
        raise _UnsafeChecksumTarget(f"unsafe checksum path {rel!r}")

    normalized = logical.as_posix()
    root_abs = root.resolve()
    target = root_abs
    for index, part in enumerate(logical.parts):
        target = target / part
        try:
            mode = target.lstat().st_mode
        except FileNotFoundError:
            raise
        except OSError as exc:
            raise _UnsafeChecksumTarget(
                f"unreadable checksum target {normalized!r}: {type(exc).__name__}: {exc}"
            ) from exc
        if stat.S_ISLNK(mode):
            raise _UnsafeChecksumTarget(f"unsafe checksum symlink {normalized!r}")
        if index < len(logical.parts) - 1 and not stat.S_ISDIR(mode):
            raise _UnsafeChecksumTarget(
                f"unsafe non-directory checksum path component {normalized!r}"
            )

    if not stat.S_ISREG(mode):
        raise _UnsafeChecksumTarget(
            f"unsafe non-regular checksum target {normalized!r}"
        )
    try:
        target.resolve(strict=True).relative_to(root_abs)
    except (OSError, ValueError) as exc:
        raise _UnsafeChecksumTarget(
            f"unsafe checksum target outside release root {normalized!r}"
        ) from exc
    return target, normalized


def _checksum_manifest_text(root: pathlib.Path) -> tuple[str | None, str | None]:
    """Admit and strictly decode the checksum manifest before parsing rows."""
    name = "SOURCE_CHECKSUMS_SHA256.txt"
    try:
        sums, _normalized = _checksum_target(root, name)
    except FileNotFoundError:
        return None, f"{name} is absent — nothing describes the tree"
    except _UnsafeChecksumTarget as exc:
        return None, f"{name} is not an admitted manifest: {exc}"
    try:
        return sums.read_text(encoding="utf-8", errors="strict"), None
    except UnicodeError as exc:
        return None, f"could not read {name} as strict UTF-8: {type(exc).__name__}: {exc}"
    except OSError as exc:
        return None, f"could not read {name}: {type(exc).__name__}: {exc}"


def checksum_problems(root: pathlib.Path) -> tuple[list[str], dict[str, int]]:
    """Assertions 1 + 2 only: every SOURCE_CHECKSUMS_SHA256.txt entry recomputes to its recorded
    digest and names a file that exists (plus the malformed-line guard, BC2-CRM-01).

    v9.7.409 (CLAUDE identity_verify_content lane): extracted from check() as the single source of
    truth for "does the tree's CONTENT match the checksum manifest?" so verify_release_identity.py
    can fold the same byte-level verdict into its identity gate instead of only cross-checking
    version/engine/build STRINGS. It returns problems (not exit codes) and emits nothing, so a
    caller can prefix or re-render them; check() below is the emitting wrapper. It deliberately
    does NOT include assertion 3 (stamp) or assertion 4 (TIER_MANIFEST membership): those are not
    content-vs-manifest questions and check 4 legitimately fails on an in-place working tree that
    carries extra run artifacts, which must not be conflated with a content mismatch.
    """
    problems: list[str] = []
    n_ok = n_bad = n_missing = 0
    manifest_text, manifest_problem = _checksum_manifest_text(root)
    if manifest_problem is not None:
        problems.append(manifest_problem)
    else:
        bad: list[str] = []
        missing: list[str] = []
        unsafe: list[str] = []
        # BC2-CRM-01 (v9.7.396): a line with `len(parts) != 2` (no filename field — a truncated
        # or corrupted entry) was silently `continue`d, with no count and no mention anywhere in
        # the output. This tool's own docstring exists specifically because "a bundle whose
        # checksum manifest fails on 128 files... passe[d]" every other gate, and warns that "a
        # hand-zipped working tree carries whatever manifest was last written" — a malformed line
        # is a plausible, real variant of that same corruption class (an interrupted/bad
        # regeneration, a bad merge), and it carries no filename to check against the tree, so it
        # can only be surfaced as its own finding, not folded into bad/missing. Reproduced: a
        # checksums file with one valid line plus one truncated line (hash, no filename) reported
        # "PASS (artifacts describe the tree)" with zero mention the file itself was malformed.
        malformed: list[str] = []
        for line in manifest_text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2:
                malformed.append(line[:80])
                continue
            recorded, rel = parts[0], parts[1].strip().lstrip("*")
            rel = rel[2:] if rel.startswith("./") else rel
            try:
                logical = PurePosixPath(rel.replace("\\", "/")).as_posix()
            except (TypeError, ValueError):
                logical = rel
            if logical in SKIP_SELF:
                continue
            try:
                p, rel = _checksum_target(root, rel)
            except FileNotFoundError:
                n_missing += 1
                missing.append(rel)
                continue
            except _UnsafeChecksumTarget as exc:
                unsafe.append(str(exc))
                continue
            try:
                actual = _digest(p)
            except OSError as exc:
                unsafe.append(
                    f"unreadable checksum target {rel!r}: {type(exc).__name__}: {exc}"
                )
                continue
            if actual != recorded:
                n_bad += 1
                bad.append(rel)
            else:
                n_ok += 1
        if bad:
            problems.append(f"{len(bad)} checksum mismatch(es); the manifest describes different content "
                            f"than the tree ships. First: {', '.join(bad[:5])}")
        if missing:
            problems.append(f"{len(missing)} manifest entr(ies) name a file that does not exist. "
                            f"First: {', '.join(missing[:5])}")
        if unsafe:
            problems.append(f"{len(unsafe)} unsafe checksum target(s); manifest entries may address "
                            f"only regular non-symlink files inside the release root. First: "
                            f"{unsafe[0]}")
        if malformed:
            problems.append(f"{len(malformed)} malformed/unparseable line(s) in "
                            f"SOURCE_CHECKSUMS_SHA256.txt — a checksums file with a line that "
                            f"can't be parsed is itself evidence of corruption. First: "
                            f"{malformed[0]!r}")
    return problems, {"n_ok": n_ok, "n_bad": n_bad, "n_missing": n_missing}


def check(root: pathlib.Path, quiet: bool = False) -> int:
    # --- 1 + 2: checksums recompute, and every entry exists -------------------------------
    problems, _stats = checksum_problems(root)
    n_ok, n_bad, n_missing = _stats["n_ok"], _stats["n_bad"], _stats["n_missing"]

    # --- 3: TIER_MANIFEST stamp == BUILD_STAMP build ------------------------------------
    tier = root / "TIER_MANIFEST.txt"
    stamp = root / "BUILD_STAMP.txt"
    tier_stamp = build_stamp = ""
    if tier.is_file():
        m = re.search(r"stamp=(\S+)", tier.read_text(encoding="utf-8", errors="ignore"))
        tier_stamp = m.group(1) if m else ""
    if stamp.is_file():
        m = re.search(r"^build=(\S+)", stamp.read_text(encoding="utf-8", errors="ignore"), re.M)
        build_stamp = m.group(1) if m else ""
    if tier.is_file() and stamp.is_file():
        if not tier_stamp:
            problems.append("TIER_MANIFEST.txt has no stamp= field")
        elif tier_stamp != build_stamp:
            problems.append(f"TIER_MANIFEST stamp={tier_stamp} but BUILD_STAMP build={build_stamp} — "
                            f"the bundle asserts two different builds, and verify_release_identity.py "
                            f"reads only the latter")

    # --- 4: TIER_MANIFEST MEMBERSHIP (SEAL-01, v9.7.336) ---------------------------------
    # Checks 1-3 verify the checksum manifest and the stamp. Nothing verified that
    # TIER_MANIFEST's FILE LIST actually describes the tree — so a bundle could ship a manifest
    # naming a different tree entirely and every gate still passed. That is not hypothetical:
    # the v9.7.334 rev-b handoff source listed 1399 files against a 1438-file tree, omitting 13
    # engine modules (discover.py, genus_appendix.py, mibig_per_gene.py, antismash_tables.py,
    # length_weighted.py, class_believability.py, cohort_context.py, strain_modeb.py,
    # modeb_cards.py, series_common.py, companion_tools.py + 2 data JSONs) — every module added
    # in .330-.333 — while listing three files the tree did not contain. It passed identity,
    # checksums, sync and accretion.
    # NB the exclusion set must match tools/make_public_tier.sh's TIER_MANIFEST generator exactly,
    # or this gate reports phantom drift on a tier the cut just built. Two sources of truth for one
    # file-set is the very failure class this check exists to catch, so keep them in step.
    # NC-001: the builder (make_public_tier.sh --emit-manifest) and this checker consume ONE shared
    # tracked-file policy (tools/tracked_file_policy.py), so they can never enumerate two file-sets.
    # It also excludes the cut's own RELEASE ARTIFACTS (logs / SHA256SUMS / tier ZIP) by a documented
    # rule (NC-002/003): they are created at/after the manifest and the ZIP is self-referential.
    import os as _os, sys as _sys
    _pol_dir = _os.path.dirname(_os.path.abspath(__file__))
    if _pol_dir not in _sys.path:
        _sys.path.insert(0, _pol_dir)
    from tracked_file_policy import is_tracked as _tracked

    if tier.is_file():
        listed = set()
        for line in tier.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                listed.add(line[2:] if line.startswith("./") else line)
        actual = set()
        for fp in root.rglob("*"):
            if not fp.is_file():
                continue
            # Skip VCS metadata: a release tree may be a git checkout (e.g. GitHub
            # Actions), and .git/ internals are never part of the sealed bundle.
            if ".git" in fp.parts:
                continue
            rel = fp.relative_to(root).as_posix()
            if _tracked(rel):
                actual.add(rel)
        unlisted = sorted(actual - listed)
        phantom = sorted(listed - actual)
        if unlisted:
            problems.append(f"TIER_MANIFEST omits {len(unlisted)} file(s) present in the tree "
                            f"(first: {', '.join(unlisted[:5])})")
        if phantom:
            problems.append(f"TIER_MANIFEST names {len(phantom)} file(s) absent from the tree "
                            f"(first: {', '.join(phantom[:5])})")

    if not quiet:
        emit(f"release manifest: {n_ok} verified | {n_bad} mismatched | {n_missing} missing | "
              f"stamp {tier_stamp or '?'} vs build {build_stamp or '?'}")
    if problems:
        emit("check_release_manifest: FAIL")
        for p in problems:
            emit(f"  - {p}")
        return 1
    if not quiet:
        emit("check_release_manifest: PASS (artifacts describe the tree)")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parents[1]))
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)
    return check(pathlib.Path(a.root), quiet=a.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
