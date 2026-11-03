#!/usr/bin/env python3
"""check_license_docs.py — every file granted CC-BY-4.0 in LICENSE-DOCS.txt must actually ship.

v9.7.247 (F5). Licensing metadata is the first thing a downstream user reads. At v9.7.246 the grant
named three files that were not in the bundle. `docs/GITHUB_HYGIENE_CHECKLIST.md` already asks for this
review; nothing enforced it. Same shape as the `date-released` and `TAG build:` misses: a field nobody owns.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LIC = ROOT / "LICENSE-DOCS.txt"


# v9.7.374: the old regex `docs/[A-Za-z0-9_./-]+\.md` only ever matched a LITERAL docs/*.md
# path. It could not match a directory-glob grant line (`docs/standalone/*.md` -- the `*` isn't
# in the character class) or anything outside docs/ (`prompts/*.md`, `templates/*.csv`). Four of
# the ten lines this file actually grants a license to were therefore invisible to the checker --
# if `docs/standalone/`, `docs/troubleshooting/`, `prompts/`, or `templates/` had been dropped
# from a cut entirely, this gate would still report PASS: the exact F5 class of bug ("granted but
# not shipped") this tool exists to catch, just for its own directory-glob grants.
_GLOB_RE = re.compile(r"^([A-Za-z0-9_./-]+/)\*\.([A-Za-z0-9]+)$")
_FILE_RE = re.compile(r"^([A-Za-z0-9_./-]+\.[A-Za-z0-9]+)$")


def main(argv=None) -> int:
    if not LIC.is_file():
        emit("check_license_docs: LICENSE-DOCS.txt missing", file=sys.stderr)
        return 2
    try:
        lines = LIC.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        emit(f"check_license_docs: could not read LICENSE-DOCS.txt: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    # Shipped prose surrounds a grant list. In compact list-only inputs, each
    # non-comment line is a grant. Unknown entries must never disappear.
    marker = "The following files are licensed under CC-BY-4.0:"
    markers = [i for i, line in enumerate(lines) if line.strip() == marker]
    boundary_error = None
    if len(markers) > 1:
        boundary_error = "ambiguous grant-list header"
        entries = []
    elif markers:
        start = markers[0] + 1
        ends = [i for i in range(start, len(lines)) if lines[i].strip().startswith("Copyright (c)")]
        if not ends:
            boundary_error = "missing grant-list end boundary"
            entries = []
        else:
            entries = list(enumerate(lines[start:ends[0]], start + 1))
    else:
        entries = list(enumerate(lines, 1))

    declared_files: list[str] = []
    declared_globs: list[tuple[str, str]] = []
    unrecognized: list[tuple[int, str]] = []
    for number, line in entries:
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        gm = _GLOB_RE.fullmatch(text)
        if gm:
            declared_globs.append((gm.group(1), gm.group(2)))
            continue
        fm = _FILE_RE.fullmatch(text)
        if fm:
            declared_files.append(fm.group(1))
            continue
        unrecognized.append((number, text))
    declared_files = list(dict.fromkeys(declared_files))
    declared_globs = list(dict.fromkeys(declared_globs))

    root = ROOT.resolve()
    def contained(relative):
        logical = pathlib.PurePosixPath(relative)
        if logical.is_absolute() or ".." in logical.parts:
            return False
        try:
            return root in (ROOT / relative).resolve().parents
        except (OSError, RuntimeError, ValueError):
            return False

    missing = []
    unsafe = []
    for name in declared_files:
        if not contained(name):
            unsafe.append(name)
        elif not (ROOT / name).is_file():
            missing.append(name)
    for directory, ext in declared_globs:
        pattern = f"{directory}*.{ext}"
        if not contained(directory):
            unsafe.append(pattern)
            continue
        path = ROOT / directory
        matched_file = False
        if path.is_dir():
            for match in path.glob(f"*.{ext}"):
                if not contained(match.relative_to(ROOT).as_posix()):
                    unsafe.append(match.relative_to(ROOT).as_posix())
                elif match.is_file():
                    matched_file = True
        if not matched_file:
            missing.append(pattern)

    total = len(declared_files) + len(declared_globs)
    messages = [f"LICENSE-DOCS: {total} grant(s) declared "
                f"({len(declared_files)} file(s), {len(declared_globs)} dir-glob(s)), {len(missing)} absent"]
    if boundary_error:
        messages.append("check_license_docs: FAIL — " + boundary_error)
    if total == 0:
        messages.append("check_license_docs: FAIL — no grants recognized in LICENSE-DOCS.txt")
    if unrecognized:
        messages.append("check_license_docs: FAIL — unrecognized grant-list entries:")
        messages.extend(f"  - line {number}: {entry}" for number, entry in unrecognized)
    if unsafe:
        messages.append("check_license_docs: FAIL — unsafe grant paths outside the bundle:")
        messages.extend(f"  - {name}" for name in unsafe)
    if missing:
        messages.append("check_license_docs: FAIL — granted but not shipped:")
        messages.extend(f"  - {name}" for name in missing)
    failed = bool(boundary_error or total == 0 or unrecognized or unsafe or missing)
    if not failed:
        messages.append("check_license_docs: PASS")
    emit("\n".join(messages))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
