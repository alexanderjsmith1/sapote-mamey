#!/usr/bin/env python3
"""check_requirements_pyproject_sync.py — freeze the requirements.txt <-> pyproject.toml core-dep drift.

Finding (release-readiness v9.7.285, still open at .296): requirements.txt claimed reportlab was
"NOT imported anywhere" and commented it out, while pyproject.toml lists it as a CORE dependency and
tools/render_deliverable_pdf.py hard-imports it (primary path in tools/md_to_pdf.sh). A
`pip install -r requirements.txt` would omit reportlab and break the primary PDF renderer.

Invariant: every package in pyproject.toml [project].dependencies (CORE) must appear as an ACTIVE
(uncommented) line in requirements.txt. Reverse not enforced (requirements carries extras).
Exit 0 = in sync; exit 1 = a core dep is missing/commented.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import pathlib, re, sys
try:
    import tomllib
except ModuleNotFoundError:
    tomllib = None
ROOT = pathlib.Path(__file__).resolve().parents[1]
_NAME = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)")
def _pkg(spec):
    m = _NAME.match(spec.strip()); return m.group(1).lower().replace("_", "-") if m else None
def pyproject_core_deps(root=ROOT):
    p = root / "pyproject.toml"
    if tomllib is not None:
        d = tomllib.loads(p.read_text(encoding="utf-8"))
        return {n for x in d.get("project", {}).get("dependencies", []) if (n := _pkg(x))}
    m = re.search(r"^\s*dependencies\s*=\s*\[(.*?)\]", p.read_text(encoding="utf-8"), re.S | re.M)
    return {n for it in re.findall(r'"([^"]+)"', m.group(1)) if (n := _pkg(it))} if m else set()
def requirements_active(root=ROOT):
    out = set()
    for line in (root / "requirements.txt").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"): continue
        if (n := _pkg(s.split("#", 1)[0].strip())): out.add(n)
    return out
def check(root=ROOT):
    return sorted(pyproject_core_deps(root) - requirements_active(root))
def main():
    missing = check()
    if missing:
        emit("requirements/pyproject sync: FAIL")
        for m in missing: emit(f"    - {m}  (core dep, not installable via pip install -r requirements.txt)")
        return 1
    emit(f"requirements/pyproject sync: OK ({len(pyproject_core_deps())} core deps all active in requirements.txt)")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
