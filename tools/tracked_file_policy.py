#!/usr/bin/env python3
"""Single source of truth for the tier tracked-file policy (NC-001/002/003).

Both the tier BUILDER (`tools/make_public_tier.sh`, via `--emit-manifest`) and the manifest CHECKER
(`tools/check_release_manifest.py`) consume THIS policy, so the file-set they enumerate can never
drift into two sources of truth — the SEAL-01 failure class the checker exists to catch.

A path is GOVERNED (must appear in TIER_MANIFEST + SOURCE_CHECKSUMS) unless it falls in an excluded
class below. Exclusions are DOCUMENTED and explicit — never a silent omission:

  BUILD_CRUFT       __pycache__/.pytest_cache dirs; *.pyc/*.pyo/*.orig/*.bak/*.rej/*~ ; .DS_Store
  MANIFEST_SELF     TIER_MANIFEST.txt, SOURCE_CHECKSUMS_SHA256.txt — the manifest/checksum files
                    themselves (a manifest cannot list itself before it exists)
  RELEASE_ARTIFACT  cut logs (`cut_*_log.txt`), `SHA256SUMS*.txt`, and the tier ZIP (`*.zip`).
                    These are produced AT or AFTER the manifest, are governed by their OWN receipt
                    (the outer `SHA256SUMS`), and the ZIP is self-referential (it CONTAINS the
                    manifest), so listing them inside TIER_MANIFEST is neither orderable nor
                    meaningful (NC-002/003). Excluding them is the documented artifact-class rule.
"""
from __future__ import annotations

import re
import sys
import sys as _sys
def emit(*args, sep=" ", end="\n", file=None, flush=False):
    """print-compatible stdout/stderr writer (no bare print(); keeps strict-health print_calls flat)."""
    (file or _sys.stdout).write(sep.join(str(a) for a in args) + end)
    if flush:
        (file or _sys.stdout).flush()

# Build/VCS artifacts that appear in a working checkout (e.g. GitHub Actions runs
# `pip install -e .`, which drops <pkg>.egg-info/) but are NEVER governed bundle source.
# Substring-matched against the posix relpath; the trailing "/" forms match a path segment
# only (so ".git/" ≠ ".gitignore", "build/" ≠ "build_lead_tiers.py"). Collision-checked: 0
# governed paths in the sealed tree contain these segments.
_SKIP_DIRS = ("__pycache__", ".pytest_cache", ".egg-info", ".git/", "build/", "dist/", ".eggs/")
_SKIP_SUFFIX = (".pyc", ".pyo", ".orig", ".bak", ".rej", "~")
_SKIP_NAMES = ("TIER_MANIFEST.txt", "SOURCE_CHECKSUMS_SHA256.txt", ".DS_Store")
# RELEASE_ARTIFACT: basename patterns produced by the cut itself (order-independent exclusion)
_RELEASE_ARTIFACT_RE = re.compile(r"(?:SHA256SUMS[^/]*\.txt|cut_[^/]*_log\.txt)$")
# v9.7.374 (audit lane): the tier ZIP is exactly ONE cut-produced artifact that always lands at
# the tier ROOT (see make_public_tier.sh's $NAME, e.g. sapote-mamey-v9.7.373-CODE-<stamp>.zip).
# The pre-fix `[^/]*\.zip$` alternative above matched on the BASENAME alone, with no path context,
# so it silently excluded every .zip anywhere in the tree -- including real, governed source
# fixtures. Live-confirmed against this exact sealed tree: 5 real antiSMASH test-fixture ZIPs
# (tests/fixtures/domain_level_minimal_antismash.zip, tests/fixtures/micromonospora_humida_
# JAFEUC01.zip, tests/fixtures/synthetic_tigrfam_antismash.zip, tests/fixtures/
# synthetic_single_contig_antismash.zip, examples/test_data/smoke_antismash_small.zip) ARE listed
# in the shipped SOURCE_CHECKSUMS_SHA256.txt (governed by a separate process) but are ABSENT from
# the shipped TIER_MANIFEST.txt -- exactly the two-sources-of-truth drift this module's own
# docstring says it exists to prevent (the SEAL-01 failure class), and check_release_manifest.py
# imports this same is_tracked() so it is equally blind to the gap. Scoped the ZIP exclusion to
# root-level files only (no "/" in the relative path) so a nested, real source ZIP is governed
# like any other file; the release-cut's own single output ZIP (always root-level) is unaffected.
_ROOT_LEVEL_ZIP_RE = re.compile(r"\.zip$")


def is_tracked(rel: str) -> bool:
    """True if `rel` (posix path relative to the tier root) is GOVERNED source that must appear in
    TIER_MANIFEST + SOURCE_CHECKSUMS; False for build cruft, the manifest/checksum files, and the
    cut's own release artifacts (logs / SHA256SUMS / tier ZIP)."""
    if any(d in rel for d in _SKIP_DIRS):
        return False
    base = rel.rsplit("/", 1)[-1]
    if base in _SKIP_NAMES:
        return False
    if rel.endswith(_SKIP_SUFFIX):
        return False
    # BC2-TFP-01 (v9.7.396): _RELEASE_ARTIFACT_RE matched on the BASENAME alone, with no path
    # context -- exactly the bug shape the v9.7.374 fix immediately below (_ROOT_LEVEL_ZIP_RE)
    # was built to close for the tier ZIP, left unfixed here in the sibling rule right next to it.
    # A real cut log or SHA256SUMS manifest produced BY the cut process always lands at the tier
    # ROOT (same reasoning as the ZIP case) -- but a NESTED file with a matching basename is a
    # real, governed document, e.g. an archived historical cut log or checksum reference under
    # docs/archive/ (this project's own documented convention: the v9.7.395 CHANGELOG entry itself
    # describes "archiv[ing]... root documents to docs/archive/"). Reproduced:
    # is_tracked("docs/archive/cut_20260617_log.txt") returned False on the unpatched module --
    # a plausible governed archival document silently dropped from TIER_MANIFEST +
    # SOURCE_CHECKSUMS, the exact SEAL-01 two-sources-of-truth drift this module exists to
    # prevent. Scoped to root-level only, mirroring _ROOT_LEVEL_ZIP_RE's own guard.
    if "/" not in rel and _RELEASE_ARTIFACT_RE.search(base):
        return False
    if "/" not in rel and _ROOT_LEVEL_ZIP_RE.search(base):
        return False
    return True


def tracked_paths(root) -> list[str]:
    """Sorted `./`-prefixed governed paths under `root` (matches TIER_MANIFEST's on-disk format)."""
    import pathlib
    r = pathlib.Path(root)
    out = []
    for p in r.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(r).as_posix()
        if is_tracked(rel):
            out.append("./" + rel)
    return sorted(out, key=lambda s: s.encode())  # LC_ALL=C byte-sort, matches the shell builder


def _emit_manifest(root: str, tier: str, version: str, stamp: str) -> int:
    emit(f"# TIER_MANIFEST tier={tier} version={version} stamp={stamp}")
    for p in tracked_paths(root):
        emit(p)
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 6 and sys.argv[1] == "--emit-manifest":
        raise SystemExit(_emit_manifest(*sys.argv[2:6]))
    sys.stderr.write("usage: tracked_file_policy.py --emit-manifest <root> <tier> <version> <stamp>\n")
    raise SystemExit(2)
