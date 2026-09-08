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
    text = LIC.read_text(encoding="utf-8")
    body = "\n".join(l for l in text.split("\n") if not l.lstrip().startswith("#"))

    declared_files: list[str] = []
    declared_globs: list[tuple[str, str]] = []
    for line in body.splitlines():
        s = line.strip()
        gm = _GLOB_RE.match(s)
        if gm:
            declared_globs.append((gm.group(1), gm.group(2)))
            continue
        fm = _FILE_RE.match(s)
        if fm:
            declared_files.append(fm.group(1))
    declared_files = list(dict.fromkeys(declared_files))
    declared_globs = list(dict.fromkeys(declared_globs))

    missing = [d for d in declared_files if not (ROOT / d).is_file()]
    for dirpath, ext in declared_globs:
        d = ROOT / dirpath
        if not d.is_dir() or not any(d.glob(f"*.{ext}")):
            missing.append(f"{dirpath}*.{ext}")

    total = len(declared_files) + len(declared_globs)
    emit(f"LICENSE-DOCS: {total} grant(s) declared "
          f"({len(declared_files)} file(s), {len(declared_globs)} dir-glob(s)), {len(missing)} absent")
    if missing:
        emit("check_license_docs: FAIL — granted but not shipped:")
        for m in missing:
            emit(f"  - {m}")
        return 1
    emit("check_license_docs: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
