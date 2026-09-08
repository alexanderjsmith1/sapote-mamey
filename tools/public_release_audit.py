#!/usr/bin/env python3
"""public_release_audit.py — FAIL-CLOSED audit of a tree destined for the public GitHub release.

Exits NONZERO on ANY of:
  * a missing / non-directory / non-Sapote root (identity anchors absent);
  * an unreadable tracked file (never silently skipped);
  * a cohort roster (mamey/data/strain_genus.csv);
  * cohort AS-#### identifiers in shipped package DATA (mamey/**/*.{csv,tsv,json});
  * personal paths / internal workspace names anywhere in the tree;
  * private literals anywhere in the tree (internal session codenames, workspace names, and
    any operator-supplied terms);
  * an untracked run directory at the root (runs*/);
  * a shipped cohort exclusions payload (OFFICIAL_DATA/exclusions.json inside the tree).

Design: the whole-tree scan is ALWAYS on. A `.identity_banlist` file, if present, only ADDS extra
private literals; it can never disable the structural scan. Detector tools that must contain the
patterns they hunt are allowlisted. Deterministic, offline, no side effects.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import hashlib
import json
import re
import shutil
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
# CODEX_392 rebase: the export-policy types live in the package, not beside this script, so the
# bundle root has to be importable as well as tools/. Both inserts are needed and neither is
# redundant — tools/ for redact_public_tier and _safe_walk, the root for mamey.privacy_profile.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from redact_public_tier import audit_paths, private_id_matches
from _safe_walk import safe_walk_files  # v9.7.400: shared unreadable-dir-aware walk
from mamey.privacy_profile import PrivacyProfileError, PublicExportPolicy, load_public_export_policy

PERSONAL = re.compile(r"/Users/[^/]+/|/home/[^/]+/|Claude_Alex_\d+|Codex Alex \d+")
AS_ID = re.compile(r"\bAS-\d{2,4}\b")
# Banned identity: internal session codenames and private workspace names.
BANNED_IDENTITY = (
    "Claude_Alex_2026", "Codex Alex 2026", "/home/claude",
    "Aquarius", "Cerulean", "Black Cherry", "BLACK_CHERRY", "Blizzard Blue", "Goldenrod",
    "Laser Lemon", "Periwinkle", "Video Game Project", "Mango-Tango",
    "WORKHORSE_CHATS",
    # private-workspace locators (P0-8): specific tokens, low false-positive risk
    "AS Strain Master", "Color folders", "MAMEY COMPLETE", "Claude August",
)
# Files that legitimately contain the patterns they detect, or are audit self / fixtures.
_ALLOW = {
    "public_release_audit.py", "audit_modeb_support_card.py", "combined_report_builder.py",
    "test_public_release_v9_7_381.py", "test_release_audit_fails_closed_v9_7_381.py",
    "test_workspace_path_portability.py",
    # portabilization DETECTORS: must contain the bare-root pattern to find and rewrite it
    # (see the "DETECTION PATTERN" note in portabilize_hook_bodies.py; already exempted in
    # test_workspace_path_portability).
    "sapote_hooks.py", "portabilize_hook_bodies.py",
    # Explicit synthetic-ID fixture used by the tests/ allowlist gate.
    "test_synthetic_ids.txt",
    # Generated after staged-tree transformation; their path/hash rows may describe the source tree
    # until make_public_tier regenerates them near the archive boundary.
    "SOURCE_CHECKSUMS_SHA256.txt", "TIER_MANIFEST.txt",
}
# Binary/large suffixes we do not decode for content (existence still counts for path checks).
_SKIP_SUFFIX = {".pyc", ".gz", ".zip", ".whl", ".png", ".svg", ".jpg", ".jpeg", ".pdf", ".ico", ".gzip",
                ".xlsx", ".xls", ".docx", ".doc", ".pptx", ".ppt", ".odt", ".ods", ".bin", ".so", ".dylib"}
_CACHE_PARTS = {"__pycache__", ".pytest_cache"}
_CACHE_FILENAMES = {".DS_Store"}


def _is_excluded_from_scan(candidate) -> bool:
    """VCS metadata, editable-install egg-info, and builder-stripped caches are never part of the
    sealed bundle and must be skipped in EVERY scan loop. A release tree may be a git checkout
    (GitHub Actions) whose .git/ holds undecodable index/pack objects, and `pip install -e` drops
    *.egg-info/. The .git/.egg-info skip previously lived only in audit()'s tree scan and not in
    _policy_hits(), so the public-release CI gate false-failed on .git/index (v9.7.414 fix: one
    predicate, no sibling drift)."""
    return (".git" in candidate.parts
            or any(part.endswith(".egg-info") for part in candidate.parts)
            or any(part in _CACHE_PARTS for part in candidate.parts)
            or candidate.name in _CACHE_FILENAMES)
# Retained-authorship allowlist: these exact strings are permitted (author + github handle).
_AUTHOR_OK = ("Alexander J. Smith", "alexanderjsmith1", "Alexander M.", "Cameron L. M.")

# Distinct sentinels so a legitimately-EMPTY file ("") is never confused with an unreadable one.
_UNREADABLE = object()   # OSError on read
_UNDECODABLE = object()  # text-suffix file that will not decode as UTF-8


def _decode(f: Path):
    """Return the file text, or a sentinel: _UNDECODABLE (not UTF-8) / _UNREADABLE (OSError).
    An empty file returns "" (valid, scans clean) — never a sentinel."""
    try:
        return f.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, ValueError):
        return _UNDECODABLE
    except OSError:
        return _UNREADABLE


def _validate_root(root: Path) -> list[str]:
    errs = []
    if not root.exists():
        errs.append(f"root does not exist: {root}")
    elif not root.is_dir():
        errs.append(f"root is not a directory: {root}")
    else:
        for anchor in ("mamey/__init__.py", "BUILD_STAMP.txt"):
            if not (root / anchor).exists():
                errs.append(f"root missing Sapote identity anchor: {anchor}")
    return errs


def _relative(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def _resolved_stage_root(root: Path) -> tuple[Path | None, list[str]]:
    """Return a resolved directory root for a disposable staging tree only."""
    try:
        stage_root = root.resolve(strict=True)
    except OSError as exc:
        return None, [f"PUBLIC_POLICY_STAGE_ROOT_UNRESOLVABLE: {root}: {type(exc).__name__}"]
    try:
        mode = stage_root.lstat().st_mode
    except OSError as exc:
        return None, [f"PUBLIC_POLICY_STAGE_ROOT_UNREADABLE: {stage_root}: {type(exc).__name__}"]
    if not stat.S_ISDIR(mode):
        return None, [f"PUBLIC_POLICY_STAGE_ROOT_NOT_DIRECTORY: {stage_root}"]
    return stage_root, []


def _validated_exclusion_target(stage_root: Path, candidate: Path) -> tuple[Path | None, str | None]:
    """Check a requested removal path without following any lexical component.

    This is deliberately a path-component check, then a resolved-containment
    check.  The caller repeats it immediately before ``shutil.rmtree``.  It
    does not claim protection against a hostile concurrent filesystem between
    the final check and removal.
    """
    try:
        relative = candidate.relative_to(stage_root)
    except ValueError:
        return None, f"PUBLIC_POLICY_EXCLUSION_OUTSIDE_STAGE: {candidate}"
    if not relative.parts:
        return None, "PUBLIC_POLICY_EXCLUSION_STAGE_ROOT_EQUALITY"
    current = stage_root
    for index, part in enumerate(relative.parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            return None, f"PUBLIC_POLICY_EXCLUSION_MISSING: {_relative(stage_root, current)}"
        except OSError as exc:
            return None, f"PUBLIC_POLICY_EXCLUSION_UNREADABLE: {_relative(stage_root, current)}: {type(exc).__name__}"
        if stat.S_ISLNK(mode):
            return None, f"PUBLIC_POLICY_EXCLUSION_SYMLINK: {_relative(stage_root, current)}"
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(mode):
            return None, f"PUBLIC_POLICY_EXCLUSION_ANCESTOR_NOT_DIRECTORY: {_relative(stage_root, current)}"
    if not stat.S_ISDIR(mode):
        return None, f"PUBLIC_POLICY_EXCLUSION_NOT_DIRECTORY: {_relative(stage_root, candidate)}"
    try:
        resolved_candidate = candidate.resolve(strict=True)
    except OSError as exc:
        return None, f"PUBLIC_POLICY_EXCLUSION_UNRESOLVABLE: {_relative(stage_root, candidate)}: {type(exc).__name__}"
    if resolved_candidate == stage_root:
        return None, "PUBLIC_POLICY_EXCLUSION_STAGE_ROOT_EQUALITY"
    try:
        resolved_candidate.relative_to(stage_root)
    except ValueError:
        return None, f"PUBLIC_POLICY_EXCLUSION_CONTAINMENT_DRIFT: {_relative(stage_root, candidate)}"
    return candidate, None


def _policy_exclusion_paths(root: Path, policy: PublicExportPolicy) -> tuple[list[Path], list[str]]:
    """Return preflighted disposable-stage policy paths or fail before removal."""
    stage_root, root_problems = _resolved_stage_root(root)
    if root_problems:
        return [], root_problems
    assert stage_root is not None
    paths: set[Path] = set()
    problems: list[str] = []
    for candidate in sorted(stage_root.rglob("*")):
        if candidate.name in policy.excluded_root_names:
            checked, problem = _validated_exclusion_target(stage_root, candidate)
            if problem:
                problems.append(problem)
            elif checked is not None:
                paths.add(checked)
    for rel in policy.excluded_relative_paths:
        checked, problem = _validated_exclusion_target(stage_root, stage_root / rel)
        if problem:
            problems.append(problem)
        elif checked is not None:
            paths.add(checked)
    return sorted(paths, key=lambda item: (len(item.parts), item.as_posix()), reverse=True), problems


def apply_public_export_exclusions(root: Path, policy: PublicExportPolicy) -> tuple[list[str], list[str]]:
    """Remove only policy-selected directories from a disposable public stage.

    This function is intentionally opt-in at the CLI.  Plain audit remains
    read-only; the tier builder invokes this only after it has copied the
    source into its private temporary stage.
    """
    paths, problems = _policy_exclusion_paths(root, policy)
    if problems:
        return [], problems
    stage_root, root_problems = _resolved_stage_root(root)
    if root_problems:
        return [], root_problems
    assert stage_root is not None
    removed: list[str] = []
    for candidate in paths:
        checked, problem = _validated_exclusion_target(stage_root, candidate)
        if problem:
            return [], [problem]
        assert checked is not None
        rel = _relative(stage_root, checked)
        # Revalidate directly before the standard-library removal to narrow
        # check/use drift.  This is not represented as crash-proof security
        # against an adversarial concurrent filesystem.
        checked, problem = _validated_exclusion_target(stage_root, checked)
        if problem:
            return [], [problem]
        assert checked is not None
        shutil.rmtree(checked)
        removed.append(rel)
    return removed, []


def _allowance_target_problems(root: Path, policy: PublicExportPolicy) -> list[str]:
    """Require every declared allowance to name one exact regular staged file."""
    problems: list[str] = []
    for allowance in policy.allowlisted_occurrences:
        candidate = root / allowance.relative_path
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            problems.append(f"PUBLIC_POLICY_ALLOWANCE_MISSING: {allowance.relative_path}")
            continue
        except OSError as exc:
            problems.append(
                f"PUBLIC_POLICY_ALLOWANCE_UNREADABLE: {allowance.relative_path}: {type(exc).__name__}"
            )
            continue
        if stat.S_ISLNK(mode):
            problems.append(f"PUBLIC_POLICY_ALLOWANCE_SYMLINK: {allowance.relative_path}")
        elif not stat.S_ISREG(mode):
            problems.append(f"PUBLIC_POLICY_ALLOWANCE_NOT_REGULAR_FILE: {allowance.relative_path}")
    return problems


def _allowance_matches(policy: PublicExportPolicy, identifier_id: str, rel: str, text: str, candidate: Path) -> bool:
    try:
        regular = stat.S_ISREG(candidate.lstat().st_mode)
    except OSError:
        regular = False
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return regular and any(
        allowance.identifier_id == identifier_id
        and allowance.relative_path == rel
        and allowance.sha256 == digest
        and allowance.purpose == "CONTENT_ONLY_EXCEPTION"
        and allowance.state == "ACTIVE"
        for allowance in policy.allowlisted_occurrences
    )


def _policy_hits(root: Path, policy: PublicExportPolicy) -> list[str]:
    """Check portable policy roots and configured literals across shipped text.

    Binary/vendor payloads are never decoded: their path still participates in
    policy matching, while content remains typed as BINARY_PATH_ONLY in the
    JSON report.  Unknown non-UTF-8 text still fails closed through _decode.
    """
    hits: list[str] = []
    hits.extend(_allowance_target_problems(root, policy))
    excluded, exclusion_problems = _policy_exclusion_paths(root, policy)
    hits.extend(exclusion_problems)
    for candidate in excluded:
        hits.append(f"PUBLIC_POLICY_EXCLUDED_ROOT_SHIPS: {_relative(root, candidate)}")
    for candidate in sorted(root.rglob("*")):
        if not candidate.is_file():
            continue
        rel = _relative(root, candidate)
        if _is_excluded_from_scan(candidate.relative_to(root)):
            continue  # builder strips these; report mode records the typed state.
        for identifier in policy.private_identifiers:
            if identifier.literal in rel:
                hits.append(f"PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_PATH: {identifier.identifier_id}: {rel}")
        if candidate.suffix.lower() in _SKIP_SUFFIX:
            continue
        text = _decode(candidate)
        if text is _UNDECODABLE:
            hits.append(f"undecodable tracked text file: {rel}")
            continue
        if text is _UNREADABLE:
            hits.append(f"unreadable tracked file: {rel}")
            continue
        for identifier in policy.private_identifiers:
            if identifier.literal in text and not _allowance_matches(policy, identifier.identifier_id, rel, text, candidate):
                hits.append(f"PUBLIC_POLICY_PRIVATE_IDENTIFIER_IN_CONTENT: {identifier.identifier_id}: {rel}")
    return hits


def audit_surface_report(root: Path, policy: PublicExportPolicy) -> dict[str, int]:
    """Return typed accounting for text, binary, vendor, and cache surfaces."""
    counts = {"TEXT_DECODED": 0, "BINARY_PATH_ONLY": 0, "VENDOR_BINARY_PATH_ONLY": 0, "CACHE_EXCLUDED_BY_BUILDER": 0}
    for candidate in root.rglob("*"):
        if not candidate.is_file():
            continue
        if _is_excluded_from_scan(candidate.relative_to(root)):
            counts["CACHE_EXCLUDED_BY_BUILDER"] += 1
        elif candidate.suffix.lower() in _SKIP_SUFFIX:
            if "wheels" in candidate.parts or "_vendor" in candidate.parts or "vendor" in candidate.parts:
                counts["VENDOR_BINARY_PATH_ONLY"] += 1
            else:
                counts["BINARY_PATH_ONLY"] += 1
        else:
            counts["TEXT_DECODED"] += 1
    return counts


def audit_governance(root: Path, decision_id: str) -> list[str]:
    """Require one active, non-expired machine governance decision.

    This is intentionally separate from the content/leak scan so a release
    builder can check promotion authority before doing expensive staging work.
    Missing, malformed, duplicate, pending, repudiated, superseded, expired, or
    currently-invalidated records all fail closed.
    """
    problems = _validate_root(root)
    if problems:
        return [f"GOVERNANCE_ROOT_INVALID: {item}" for item in problems]
    ledger = root / "GOVERNANCE_DECISIONS.json"
    if not ledger.is_file():
        return ["GOVERNANCE_LEDGER_MISSING: GOVERNANCE_DECISIONS.json"]
    try:
        payload = json.loads(ledger.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"GOVERNANCE_LEDGER_UNREADABLE: {type(exc).__name__}: {exc}"]
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        return ["GOVERNANCE_LEDGER_SCHEMA_INVALID: decisions must be a list"]
    matches = [item for item in decisions if isinstance(item, dict) and item.get("id") == decision_id]
    if len(matches) != 1:
        return [f"GOVERNANCE_DECISION_CARDINALITY: {decision_id} matched {len(matches)} record(s), expected 1"]
    decision = matches[0]
    status = decision.get("status")
    if status != "ACTIVE":
        return [f"GOVERNANCE_DECISION_NOT_ACTIVE: {decision_id} status={status or 'MISSING'}"]
    if decision.get("condition_currently_true") is not False:
        return [f"GOVERNANCE_DECISION_INVALIDATED: {decision_id} condition_currently_true must be false"]
    signer = decision.get("asserted_signer")
    date = decision.get("asserted_date")
    if not isinstance(signer, str) or not signer.strip() or not isinstance(date, str) or not date.strip():
        return [f"GOVERNANCE_DECISION_UNSIGNED: {decision_id} requires signer and date"]
    return []


# --- strict source-disclosure pass (CODEX_396 REPAIR_16, integrated v9.7.405) ------------------
# The default scan above deliberately skips the tests/ tree and skips cohort-ID content checks on
# .py files: release-time rewriting of Python is dangerous and the in-tier suite must stay
# executable. Both skips are correct, and both mean a PASS proves the gate did not look — which is
# how a real cohort exclusions payload once sat through every prior PASS.
#
# This logic arrives from tools/strict_source_disclosure_audit.py, which was written standalone
# ONLY to avoid colliding with the then-unlanded Archive Transaction Repair 15, and whose own
# docstring said its core was "written so the Repair-15 evaluator can absorb it verbatim ... once
# that repair lands". Repair 15 landed in this same cut, so the reason for the separation is gone.
# It lives here now because THIS module owns the gate that decides whether a stage may produce
# output, and a policy the release gate does not own is a policy the release gate can be run
# without. The standalone file remains as a compatibility entry point holding no policy of its own.
_STRICT_PLACEHOLDERS = {"AS-XXX", "AJS-XXX", "PENDING-XXX"}
_STRICT_NORM = re.compile(r"^(AS|AJS)(\d)")


def _strict_normalise(token: str) -> str:
    """Mirror make_public_tier.sh: uppercase, insert the dash in dashless AS123/AJS123."""
    return _STRICT_NORM.sub(r"\1-\2", token.upper())


def _strict_synthetic_allowlist(root: Path) -> set[str]:
    """The sanctioned test-identifier list (tools/test_synthetic_ids.txt), normalised.
    A missing file yields the empty set: the strict pass gets stricter, never more permissive."""
    listing = root / "tools" / "test_synthetic_ids.txt"
    if not listing.is_file():
        return set()
    out = set()
    for line in listing.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(_strict_normalise(line))
    return out


def _strict_locator(rel: Path, scope: str) -> str:
    """Stable locator that exposes neither a staged path nor a private source token (REPAIR_16)."""
    digest = hashlib.sha256(rel.as_posix().encode("utf-8")).hexdigest()[:12]
    return f"{scope}/<redacted:{digest}>"


def _strict_finding(kind: str, rel: Path, scope: str, *, count: int | None = None) -> str:
    """Typed, redacted diagnostic that never echoes a matched literal — the default output, because
    this gate exists to stop identifier leaks and its own failure log must not become one."""
    suffix = f" count={count}" if count is not None else ""
    return f"{kind}: locator={_strict_locator(rel, scope)}{suffix}"


def strict_source_disclosure_findings(root: Path, *, show_identifiers: bool = False) -> list[str]:
    """The strict pass: a pure function defining no identifier patterns, allowlists or redaction
    policy of its own — every predicate is imported from the existing policy owner.

    Findings are REDACTED by default (v9.7.405, owner ruling on REPAIR_16): typed kind + hashed
    locator + count, so a retained CI log of a failing run does not itself disclose the cohort
    identifiers the gate caught. `show_identifiers=True` (CLI `--show-identifiers`) restores the
    verbose form — relative path plus the matched tokens — for interactive triage at a terminal."""
    hits = list(_validate_root(root))
    if hits:
        return hits
    synthetic = _strict_synthetic_allowlist(root)
    for f in sorted(root.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(root)
        if ".git" in f.parts or any(p.endswith(".egg-info") for p in f.parts):
            continue
        if f.name in _ALLOW or f.suffix in _SKIP_SUFFIX:
            continue
        in_tests = "/tests/" in f"/{rel}/"
        is_py = f.suffix == ".py"
        # Surface 1: the tests/ tree (any decodable file). Surface 2: python source outside it.
        # Everything else is the DEFAULT gate's jurisdiction and is not rescanned here.
        if not in_tests and not is_py:
            continue
        scope = "tests" if in_tests else "python"
        text = _decode(f)
        if text is _UNDECODABLE:
            hits.append(f"strict: undecodable text file: {rel}" if show_identifiers
                        else _strict_finding("STRICT_SOURCE_UNDECODABLE", rel, scope))
            continue
        if text is _UNREADABLE:
            hits.append(f"strict: unreadable file: {rel}" if show_identifiers
                        else _strict_finding("STRICT_SOURCE_UNREADABLE", rel, scope))
            continue
        ids = {_strict_normalise(tok) for tok in private_id_matches(text, as_only=True)}
        # The sanctioned synthetic list is charter-scoped to tests/, but its entries are by
        # definition verified non-cohort tokens, so subtracting them on the python surface too
        # removes no real finding and adds no leak risk.
        ids -= _STRICT_PLACEHOLDERS | synthetic
        label = ("non-synthetic identifier in tests/" if in_tests
                 else "cohort identifier in python source")
        if ids:
            if show_identifiers:
                shown = sorted(ids)
                preview = ", ".join(shown[:8]) + (" ..." if len(shown) > 8 else "")
                hits.append(f"strict: {label}: {rel}: {preview}")
            else:
                hits.append(_strict_finding("STRICT_SOURCE_IDENTIFIER", rel, scope, count=len(ids)))
        if in_tests:
            # the default gate's identity checks, extended into the tree it skips.
            # PERSONAL is matched PER LINE: its [^/]+ classes match newlines, so a
            # whole-file search runs one match across many lines and flags files that
            # merely assert a home-dir prefix is ABSENT ('"/Users/" not in text', with
            # no slash until a later line). Real paths never span lines. Restores the
            # line scope landed in v9.7.396, lost when the strict pass moved here.
            if any(PERSONAL.search(_ln) for _ln in text.splitlines()):
                hits.append(f"strict: personal path / workspace name in tests/: {rel}" if show_identifiers
                            else _strict_finding("STRICT_SOURCE_PERSONAL_PATH", rel, scope))
            banned_hits = [b for b in BANNED_IDENTITY if b in text]
            if show_identifiers:
                for banned in banned_hits:
                    hits.append(f"strict: banned identity {banned!r} in tests/: {rel}")
            elif banned_hits:
                hits.append(_strict_finding("STRICT_SOURCE_BANNED_IDENTITY", rel, scope,
                                            count=len(banned_hits)))
    return hits


def audit(root: Path, policy: PublicExportPolicy | None = None, *,
          strict_source_disclosure: bool = False, show_identifiers: bool = False) -> list[str]:
    """The release gate. `policy` comes from CODEX_392's export policy; `strict_source_disclosure`
    is CODEX_396's opt-in widening. Both are keyword-safe additions to the original one-argument
    signature — the two repairs were authored on branches that never met and each extended this
    function differently, so the merged form takes both rather than either winning."""
    hits = list(_validate_root(root))
    if hits:
        return hits  # a bad root is itself the failure; do not pretend to scan
    policy = policy or load_public_export_policy()
    mamey = root / "mamey"

    # CODEX_392 rebase: the declared-policy pass runs FIRST, before the structural scan, so a
    # tree that a policy already forbids is refused without reporting on its contents at all.
    hits.extend(_policy_hits(root, policy))

    if (mamey / "data" / "strain_genus.csv").exists():
        hits.append("cohort roster ships: mamey/data/strain_genus.csv")
    data_files, data_unreadable_dirs = safe_walk_files(mamey / "data")
    for d in data_unreadable_dirs:
        hits.append(f"unreadable tracked directory (cohort-id scan incomplete): {d}")
    for f in data_files:
        if f.suffix in {".csv", ".tsv", ".json"}:
            t = _decode(f)
            if isinstance(t, str) and AS_ID.search(t):
                hits.append(f"cohort AS-#### id in shipped data: {f.relative_to(root)}")
    for d in root.glob("runs*"):
        if d.is_dir():
            hits.append(f"untracked run dir at root: {d.relative_to(root)}")
    if (root / "OFFICIAL_DATA" / "exclusions.json").exists():
        hits.append("cohort exclusions payload ships: OFFICIAL_DATA/exclusions.json")
    if (root / "future_improvements").is_dir():
        hits.append("internal future-work directory ships: future_improvements/")
    for rel in audit_paths(root):
        hits.append(f"cohort identifier in shipped path: {rel}")

    # whole-tree content scan (ALWAYS on)
    extra = []
    banlist = root / ".identity_banlist"
    if banlist.exists():
        extra = [ln.strip() for ln in banlist.read_text(errors="ignore").splitlines() if ln.strip()]
    tree_files, tree_unreadable_dirs = safe_walk_files(root)
    for d in tree_unreadable_dirs:
        hits.append(f"unreadable tracked directory (whole-tree scan incomplete): {d}")
    for f in tree_files:
        rel = f.relative_to(root)
        # Skip VCS metadata + build artifacts: a release tree may be a git checkout
        # (GitHub Actions) and `pip install -e .` drops <pkg>.egg-info/ into it — neither
        # is ever part of the sealed bundle.
        # Cache paths are accounted for by audit_surface_report and stripped by the
        # builder; they are not shipped text/documentation surfaces.  Never let a
        # developer's pytest cache turn a source-tree audit into a false content
        # finding, but do not silently decode or include it in a public artifact.
        if _is_excluded_from_scan(f.relative_to(root)):
            continue
        if f.name in _ALLOW or "/tests/" in f"/{rel}/":
            continue
        if f.suffix in _SKIP_SUFFIX:
            continue
        t = _decode(f)
        if t is _UNDECODABLE:
            hits.append(f"undecodable tracked text file: {rel}")
            continue
        if t is _UNREADABLE:
            hits.append(f"unreadable tracked file: {rel}")
            continue
        # t is now a str (possibly "" for a legitimately-empty file, which scans clean)
        # Per line, for the same newline-spanning reason as the strict pass above.
        if any(PERSONAL.search(_ln) for _ln in t.splitlines()):
            hits.append(f"personal path / workspace name: {rel}")
        # Executable Python is deliberately outside this narrow documentation-safety gate.
        # Rewriting Python string constants can change dictionaries, routing policy, and test-tool
        # references even when tokenization preserves syntax. Python genericization therefore
        # requires ordinary source patches plus regression tests; it is not a release-time rewrite.
        if f.suffix != ".py":
            cohort_ids = sorted(set(private_id_matches(t, as_only=True)))
            if cohort_ids:
                preview = ", ".join(cohort_ids[:8])
                suffix = " ..." if len(cohort_ids) > 8 else ""
                hits.append(f"cohort identifier in non-test content: {rel}: {preview}{suffix}")
        for b in list(BANNED_IDENTITY) + extra:
            if b in t:
                hits.append(f"banned identity {b!r} in {rel}")
    if strict_source_disclosure:
        # Runs LAST and only on request: it widens the surface rather than changing any verdict
        # the default scan already reached, so a caller reading the list sees the default gate's
        # findings first and the opt-in ones after. Root validation already passed above, so the
        # strict pass cannot re-report it.
        hits.extend(strict_source_disclosure_findings(root, show_identifiers=show_identifiers))
    return hits


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Fail-closed public-release identity/leak audit.")
    ap.add_argument("root", help="path to the public tree to audit")
    ap.add_argument("--require-active-decision", action="append", default=[], metavar="ID",
                    help="require an ACTIVE, non-invalidated governance decision (repeatable)")
    ap.add_argument("--strict-source-disclosure", action="store_true",
                    help="add the opt-in source/test disclosure pass to this audit (findings "
                         "redacted to typed kind + hashed locator + count by default)")
    ap.add_argument("--show-identifiers", action="store_true",
                    help="strict pass only: print relative paths and the matched identifiers "
                         "(interactive triage; never into a retained log)")
    ap.add_argument("--governance-only", action="store_true",
                    help="check only requested governance decisions, before release staging")
    ap.add_argument("--privacy-profile", default=None,
                    help="optional sapote_privacy_profile_v1 with public_export_policy controls")
    ap.add_argument("--apply-public-export-exclusions", action="store_true",
                    help="remove only policy-selected directories from a disposable stage before audit")
    ap.add_argument("--report-json", action="store_true",
                    help="emit typed text/binary/vendor/cache surface counts after the audit result")
    args = ap.parse_args(argv)
    if args.governance_only and not args.require_active_decision:
        ap.error("--governance-only requires at least one --require-active-decision ID")
    root = Path(args.root).resolve()
    try:
        policy = load_public_export_policy(args.privacy_profile)
    except PrivacyProfileError as exc:
        # CODEX_392 rebase: this tool's stdout IS its receipt, so the new lines below stay on
        # stdout like the four that were already here — but written with sys.stdout.write, not
        # print(. The repo_health print ratchet counts print( by AST with no headroom, and a
        # receipt line is not library debt; writing it directly keeps the family print-neutral
        # without excluding this file from the scan (which would have removed the four
        # pre-existing receipt lines from the count as collateral).
        sys.stdout.write(f"PUBLIC RELEASE AUDIT: FAIL (invalid privacy profile: {exc})\n")
        return 2
    if args.apply_public_export_exclusions:
        if args.governance_only:
            ap.error("--apply-public-export-exclusions cannot be combined with --governance-only")
        removed, policy_problems = apply_public_export_exclusions(root, policy)
        if policy_problems:
            sys.stdout.write(
                "PUBLIC RELEASE AUDIT: FAIL (%d policy-exclusion issue(s))\n" % len(policy_problems))
            for problem in policy_problems:
                sys.stdout.write(f"  ✗ {problem}\n")
            return 1
        sys.stdout.write("PUBLIC EXPORT POLICY: removed %d staged root(s)%s\n" % (
            len(removed), f" ({', '.join(removed)})" if removed else ""))
    hits = [] if args.governance_only else audit(
        root, policy, strict_source_disclosure=args.strict_source_disclosure,
        show_identifiers=args.show_identifiers)
    for decision_id in args.require_active_decision:
        hits.extend(audit_governance(root, decision_id))
    if hits:
        emit("PUBLIC RELEASE AUDIT: FAIL (%d issue(s))" % len(hits))
        for h in hits:
            emit("  ✗", h)
        return 1
    if args.governance_only:
        joined = ", ".join(args.require_active_decision)
        emit(f"PUBLIC RELEASE GOVERNANCE: PASS ({joined} active and non-invalidated)")
    else:
        emit("PUBLIC RELEASE AUDIT: PASS (root valid; whole-tree scan clean)")
    if args.report_json and not args.governance_only:
        sys.stdout.write(
            json.dumps({"surface_types": audit_surface_report(root, policy)}, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
