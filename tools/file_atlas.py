#!/usr/bin/env python3
"""file_atlas.py — describe every Python file in the bundle, from the source, with receipts.

v9.7.243. Built for the Bunny Hop Audit Game (debugging_modules/BUNNY_HOP_AUDIT_GAME.md): you cannot audit
what you cannot see. Emits one row per file under mamey/ and tools/ with:

  path, loc, summary (first docstring line), n_defs, n_classes,
  imports_internal (fan-out), imported_by (fan-in), cli_verbs (subcommands registered here),
  test_refs (test files naming this module), orphan (no fan-in, no CLI verb, no test)

Everything is read from the real tree with `ast` — no inference, no hardcoded lists. The `orphan`
column is the interesting one: a module nothing imports, no CLI verb reaches, and no test names is
a candidate for the audit's REDUNDANCY inspector — or for the defect class this project keeps
hitting, where a capability exists and nothing invokes it.

Usage:
  python3 tools/file_atlas.py --out docs/FILE_ATLAS.csv --md docs/FILE_ATLAS.md
  python3 tools/file_atlas.py --orphans        # just the orphan list, for the bunny-hop roll
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import ast
import csv
try:  # v9.7.410 CSV formula-cell guard (CLAUDE_v9.7.410_tools_csv_writer_coverage)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
except ImportError:  # bare-script run: bundle root is one level up
    import os as _cs_os, sys as _cs_sys
    _cs_sys.path.insert(0, _cs_os.path.dirname(_cs_os.path.dirname(_cs_os.path.abspath(__file__))))
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import pathlib
import re
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCAN = ("mamey", "tools")
SKIP_PARTS = {"__pycache__", "_vendor", "data"}


def _py_files():
    out = []
    for d in SCAN:
        for p in sorted((ROOT / d).rglob("*.py")):
            if any(s in p.parts for s in SKIP_PARTS):
                continue
            if p.name == "__init__.py":
                continue
            out.append(p)
    return out


def _parse(p: pathlib.Path):
    try:
        src = p.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(src)
    except Exception:
        return None, "", 0, 0, set()
    doc = (ast.get_docstring(tree) or "").strip().splitlines()
    summary = doc[0] if doc else ""
    defs = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    imports = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if n.module:
                imports.add(n.module.split(".")[-1])
            elif n.level:  # `from . import submod` / `from .. import submod` — n.module is None and
                for a in n.names:  # the imported names ARE submodules; without this fan-in under-counts
                    imports.add(a.name.split(".")[-1])
        elif isinstance(n, ast.Import):
            for a in n.names:
                imports.add(a.name.split(".")[-1])
    return src, summary, defs, classes, imports


def build():
    files = _py_files()
    stems = {p.stem: p for p in files}
    rows = []
    fanin = defaultdict(set)
    parsed = {}

    for p in files:
        src, summary, defs, classes, imports = _parse(p)
        internal = sorted(i for i in imports if i in stems and i != p.stem)
        parsed[p] = (src or "", summary, defs, classes, internal)
        for i in internal:
            fanin[i].add(p.relative_to(ROOT).as_posix())

    # CLI verbs: which module defines each `sub.add_parser("verb")` handler
    cli = ROOT / "mamey" / "cli.py"
    verbs = re.findall(r'add_parser\(\s*["\']([a-z0-9\-]+)["\']', cli.read_text(encoding="utf-8")) if cli.exists() else []

    # shell/CI invocations: a tool called from a .sh or from gate_registry.tsv is NOT an orphan.
    # (verify_release_identity.py is invoked by tools/release.sh — my first pass called it an orphan.)
    shell_refs = defaultdict(set)
    for sh in list(ROOT.rglob("*.sh")) + list(ROOT.rglob("gate_registry.tsv")):
        if any(x in sh.parts for x in SKIP_PARTS):
            continue
        txt = sh.read_text(encoding="utf-8", errors="ignore")
        for s_ in stems:
            if re.search(rf"\b{re.escape(s_)}\.py\b", txt) or re.search(rf"^{re.escape(s_)}\b", txt, re.M):
                shell_refs[s_].add(sh.name)

    # test references, by module stem
    tref = defaultdict(set)
    tdir = ROOT / "tests"
    if tdir.is_dir():
        for t in tdir.rglob("test_*.py"):
            txt = t.read_text(encoding="utf-8", errors="ignore")
            for s in stems:
                if re.search(rf"\b{re.escape(s)}\b", txt):
                    tref[s].add(t.name)

    for p in files:
        src, summary, defs, classes, internal = parsed[p]
        stem = p.stem
        rel = p.relative_to(ROOT).as_posix()
        # a verb "belongs" to a module if the module name appears near the verb registration
        my_verbs = [v for v in verbs if v.replace("-", "_") in stem or stem in v.replace("-", "_")]
        in_deg = sorted(fanin.get(stem, ()))
        tests = sorted(tref.get(stem, ()))
        shells = sorted(shell_refs.get(stem, ()))
        orphan = (not in_deg) and (not my_verbs) and (not tests) and (not shells) and rel != "mamey/cli.py"
        rows.append({
            "path": rel,
            "loc": len(src.splitlines()),
            "summary": summary[:160],
            "n_defs": defs,
            "n_classes": classes,
            "fan_out": len(internal),
            "imports_internal": ";".join(internal),
            "fan_in": len(in_deg),
            "imported_by": ";".join(in_deg[:6]),
            "cli_verbs": ";".join(my_verbs),
            "n_tests": len(tests),
            "test_refs": ";".join(tests[:4]),
            "shell_refs": ";".join(shells),
            "orphan": orphan,
        })
    return rows


COLS = ["path", "loc", "summary", "n_defs", "n_classes", "fan_out", "imports_internal",
        "fan_in", "imported_by", "cli_verbs", "n_tests", "test_refs", "shell_refs", "orphan"]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="CSV output path")
    ap.add_argument("--md", help="Markdown summary path")
    ap.add_argument("--orphans", action="store_true", help="print orphan candidates only")
    a = ap.parse_args(argv)

    rows = build()
    if a.orphans:
        orph = [r for r in rows if r["orphan"]]
        emit(f"{len(orph)} orphan candidate(s) of {len(rows)} files "
              f"(no importer, no CLI verb, no test naming them):")
        for r in sorted(orph, key=lambda r: -r["loc"]):
            emit(f"  {r['loc']:5d} loc  {r['path']:44s} {r['summary'][:60]}")
        return 0

    if a.out:
        with open(a.out, "w", newline="", encoding="utf-8") as fh:
            w = _SafeDictWriter(fh, fieldnames=COLS)
            w.writeheader()
            w.writerows(rows)
        emit(f"wrote {a.out}: {len(rows)} files")

    if a.md:
        orph = [r for r in rows if r["orphan"]]
        hot = sorted(rows, key=lambda r: -r["fan_in"])[:15]
        big = sorted(rows, key=lambda r: -r["loc"])[:15]
        untested = [r for r in rows if r["n_tests"] == 0]
        with open(a.md, "w", encoding="utf-8") as fh:
            fh.write("# File atlas — every module and tool in the bundle\n\n")
            fh.write(f"Generated by `tools/file_atlas.py` from the real source tree. "
                     f"**{len(rows)} files** under `mamey/` and `tools/`.\n\n")
            fh.write(f"- orphan candidates (no importer, no CLI verb, no test): **{len(orph)}**\n")
            fh.write(f"- files no test names at all: **{len(untested)}**\n")
            fh.write(f"- total lines: **{sum(r['loc'] for r in rows):,}**\n\n")
            fh.write("## Highest fan-in (change these carefully)\n\n| file | imported by | loc | summary |\n|---|---:|---:|---|\n")
            for r in hot:
                fh.write(f"| `{r['path']}` | {r['fan_in']} | {r['loc']} | {r['summary'][:70]} |\n")
            fh.write("\n## Largest files\n\n| file | loc | defs | fan-in | summary |\n|---|---:|---:|---:|---|\n")
            for r in big:
                fh.write(f"| `{r['path']}` | {r['loc']} | {r['n_defs']} | {r['fan_in']} | {r['summary'][:60]} |\n")
            fh.write("\n## Orphan candidates — the bunny-hop roll pool\n\n")
            fh.write("A module nothing imports, no CLI verb reaches, and no test names. "
                     "Some are legitimate entry points; some are the defect class this project keeps hitting.\n\n")
            fh.write("| file | loc | summary |\n|---|---:|---|\n")
            for r in sorted(orph, key=lambda r: -r["loc"]):
                fh.write(f"| `{r['path']}` | {r['loc']} | {r['summary'][:80]} |\n")
            fh.write("\n## Every file\n\n| file | loc | fan-in | fan-out | tests | summary |\n|---|---:|---:|---:|---:|---|\n")
            for r in sorted(rows, key=lambda r: r["path"]):
                fh.write(f"| `{r['path']}` | {r['loc']} | {r['fan_in']} | {r['fan_out']} | "
                         f"{r['n_tests']} | {r['summary'][:80]} |\n")
        emit(f"wrote {a.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
