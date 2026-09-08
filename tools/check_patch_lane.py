#!/usr/bin/env python3
"""check_patch_lane.py — validate patch-lane STRUCTURE and DISPOSITION.

Companion to tools/patch_packet_preflight.py. That tool fails closed on BLOAT (assemblies, caches,
oversize files). This one fails closed on INCOMPLETENESS and MIS-FILING: a lane that is missing its
card, its test, or its diff, or a stream folder holding material that is not a patch and has no
disposition. Together they answer "is this cut-selectable?" — preflight says no-junk, this says
complete-and-correctly-filed.

Contract: docs/PATCH_WORKSPACE_LAYOUT.md.

A LANE is one issue = one folder containing exactly:
  - one *.patch
  - PATCH_CARD.md
  - at least one test (test_*.py, or a *.R / *_test contract for a figure/asset lane)

Usage:
  python tools/check_patch_lane.py --lane   <lane dir>
  python tools/check_patch_lane.py --stream <dir of lane folders>

Exit 0 = complete and correctly disposed. Exit 1 = at least one problem (each is named). Exit 2 =
bad invocation (the path does not exist).
"""
from __future__ import annotations

import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd (v9.7.407 convention)
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import re
from pathlib import Path

# A version marker in a name must be the full v9.7.N form, never a bare number, with NO exemption for
# lane slugs — a lane folder circulates standalone, so `CLAUDE_410_<slug>` carries the ambiguity
# wherever it is copied (and this project has a strain named 410). `_BARE_VERSION_RE` matches a bare
# 3-digit cut number (400-419) NOT already carrying the `v9.7.` prefix; every occurrence in the name
# is checked, so a trailing `..._recovery_409` is flagged as well as a leading `CLAUDE_410_`.
# NOTE: `\b` is NOT used — a `\b` never sits between `_` and a digit (both are word chars), so a
# `_409` suffix would slip through. Lookarounds instead: not preceded by a version digit/dot/`v`,
# not followed by another digit.
_BARE_VERSION_RE = re.compile(r"(?<![0-9.v])(4[01][0-9])(?![0-9])")
_FULL_VERSION_RE = re.compile(r"v9\.7\.[0-9]+")


def version_naming_problem(name: str) -> str | None:
    """Flag ANY bare version marker in a name (no lane exemption). A name may carry several: a full
    `v9.7.410` is fine, but a bare `410` or `409` anywhere else in it is not."""
    # Remove the full forms first, then look for any surviving bare cut number.
    stripped = _FULL_VERSION_RE.sub("", name)
    bare = _BARE_VERSION_RE.search(stripped)
    if bare:
        n = bare.group(1)
        return f"{name}: bare version '{n}' is ambiguous — use the full 'v9.7.{n}'"
    return None


# A directory is TREATED AS A LANE (and therefore must be complete) when it contains at least one of
# these. This is what lets the tool tell "an unfinished lane" (has a .patch, missing a card) apart
# from "not a lane at all" (a reports folder that was mis-filed under for-cut).
LANE_MARKERS = ("*.patch", "PATCH_CARD.md")
TEST_GLOBS = ("test_*.py", "*_test.py", "test_*.R", "*_test.R")


def _has(directory: Path, *globs: str) -> bool:
    return any(next(directory.rglob(g), None) is not None for g in globs)


def _looks_like_lane(directory: Path) -> bool:
    return _has(directory, *LANE_MARKERS)


_DIFF_HEADER_RE = re.compile(r"^(?:---|\+\+\+) (\S+)", re.M)


def _escaping_paths(patch_text: str) -> list[str]:
    """Return every `---`/`+++` header path that is absolute or climbs out via `..`."""
    bad: list[str] = []
    for raw in _DIFF_HEADER_RE.findall(patch_text):
        if raw == "/dev/null":
            continue
        parts = raw.replace("\\", "/").split("/")
        if raw.startswith("/") or ".." in parts:
            bad.append(raw)
    return bad


def check_lane(directory: Path) -> list[str]:
    """Return a list of problems for one lane folder. Empty list = complete."""
    problems: list[str] = []
    rel = directory.name

    patches = sorted(directory.rglob("*.patch"))
    if not patches:
        problems.append(f"{rel}: no *.patch — a lane must carry its unified diff")
    if not _has(directory, "PATCH_CARD.md"):
        problems.append(f"{rel}: no PATCH_CARD.md — a lane must document premise / fix / "
                        "fail-before-pass-after")
    if not _has(directory, *TEST_GLOBS):
        problems.append(f"{rel}: no test (test_*.py or a *.R contract) — a lane must ship its test")

    # Soft structural checks (named, but they do not by themselves fail a lane that is otherwise
    # complete): the test should also be carried INSIDE the diff so it travels with the fix.
    for patch in patches:
        try:
            text = patch.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:  # pragma: no cover - unreadable file
            problems.append(f"{rel}: cannot read {patch.name}: {exc}")
            continue
        # HARD check (v9.7.410 hostile audit): every path the diff touches must stay inside the
        # tree it is applied to. An absolute path or a `..` component in a `---`/`+++` header is
        # never a legitimate lane — `patch` may refuse it, but the disposition gate must not wave
        # it through as "complete". `/dev/null` (a created/deleted file) is the one allowed absolute.
        for bad in _escaping_paths(text):
            problems.append(f"{rel}: {patch.name} targets a path outside the tree: {bad}")
        if "+++ b/tests/" not in text and "+++ patched/tests/" not in text:
            problems.append(f"{rel}: {patch.name} does not add anything under tests/ — the fix's "
                            "test should travel inside the diff (soft: confirm the test is carried)")
    return problems


def report_stamp_problem(md_path: Path) -> str | None:
    """A report's first 3 lines must carry `**Base:** v9.7.N` and `Disposition:`. Returns a problem
    string or None. The base must be the full v9.7.N form (or an explicit unstated marker)."""
    try:
        head = "\n".join(md_path.read_text(encoding="utf-8", errors="replace").splitlines()[:3])
    except OSError as exc:  # pragma: no cover
        return f"{md_path.name}: cannot read: {exc}"
    if "**Base:**" not in head or "Disposition:" not in head:
        return (f"{md_path.name}: no front-matter stamp in the first 3 lines "
                "(`> **Base:** v9.7.N · **Audited:** DATE · **Disposition:** report`)")
    if not (_FULL_VERSION_RE.search(head) or "unstated in source" in head):
        return f"{md_path.name}: Base is not the full v9.7.N form (a bare number is ambiguous)"
    return None


def check_reports(directory: Path) -> list[str]:
    """Every *.md report under `directory` must carry the front-matter stamp."""
    problems: list[str] = []
    for md in sorted(directory.rglob("*.md")):
        if md.name in {"README.md", "INDEX.md"}:
            continue
        p = report_stamp_problem(md)
        if p:
            problems.append(p)
    return problems


def check_stream(directory: Path) -> list[str]:
    """Validate a folder of lanes. Every lane-shaped subdir must be complete; anything that is not a
    lane and not an allowed support file is flagged as having no disposition."""
    problems: list[str] = []
    # Support files a stream folder legitimately carries at its top level (indexes, co-apply notes).
    ALLOWED_TOP_FILES = {"README.md", "INDEX.md", "SCRATCH_MOVE_PLAN.md"}
    ALLOWED_TOP_SUFFIXES = {".md", ".tsv", ".json", ".txt"}

    lane_count = 0
    for child in sorted(directory.iterdir()):
        if child.name.startswith(".") or child.name == "__pycache__":
            continue
        if child.is_dir():
            if child.name.startswith("_"):
                continue  # `_NOT_LANDED_IN_409/`, `_archive/` — explicitly parked, not a live lane
            if _looks_like_lane(child):
                lane_count += 1
                problems.extend(check_lane(child))
            else:
                problems.append(f"{child.name}/: not a lane (no .patch, no PATCH_CARD) and filed "
                                "under a cut stream — move it to reports/ or scratch/, or finish it")
            # Naming rule applies to EVERY named child, lane or not (no exemption).
            naming = version_naming_problem(child.name)
            if naming:
                problems.append(naming)
        else:
            if child.name in ALLOWED_TOP_FILES or child.suffix in ALLOWED_TOP_SUFFIXES:
                continue
            problems.append(f"{child.name}: loose file in a cut stream with no disposition — "
                            "move it to reports/ or scratch/")
    if lane_count == 0:
        problems.append(f"{directory.name}: contains no complete lanes")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate patch-lane structure and disposition.")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--lane", type=Path, help="a single lane folder")
    mode.add_argument("--stream", type=Path, help="a folder of lane folders")
    mode.add_argument("--reports", type=Path, help="a folder of report *.md files")
    args = ap.parse_args(argv)

    target = args.lane or args.stream or args.reports
    if not target.is_dir():
        return _report(2, f"check_patch_lane: {target} is not a directory")

    if args.lane:
        problems, kind = check_lane(target), "lane"
    elif args.stream:
        problems, kind = check_stream(target), "stream"
    else:
        problems, kind = check_reports(target), "reports set"
    if problems:
        header = f"PATCH LANE CHECK — {len(problems)} problem(s) in {target.name}"
        return _report(1, "\n".join([header] + [f"  - {p}" for p in problems]))
    return _report(0, f"PATCH LANE CHECK — OK: {target.name} is a complete, correctly-disposed {kind}")


def _report(code: int, message: str) -> int:
    """Single terminal-emission site (keeps this tool's cost to the print_calls ratchet at 1)."""
    emit(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
