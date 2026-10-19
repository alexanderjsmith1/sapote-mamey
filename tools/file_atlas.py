#!/usr/bin/env python3
"""file_atlas.py — describe every Python file in the bundle, from the source, with receipts.

v9.7.243. Built for the Bunny Hop Audit Game (debugging_modules/BUNNY_HOP_AUDIT_GAME.md): you cannot audit
what you cannot see. Emits one row per file under mamey/ and tools/ with:

  path, loc, summary (opening source docstring paragraph), n_defs, n_classes,
  imports_internal (fan-out), imported_by (fan-in), cli_verbs (subcommands registered here),
  test_refs (test files naming this module), orphan (no fan-in, no CLI verb, no test)

Everything is read from the real tree with `ast` — no inference, no hardcoded lists. The `orphan`
column is the interesting one: a module nothing imports, no CLI verb reaches, and no test names is
a candidate for the audit's REDUNDANCY inspector — or for the defect class this project keeps
hitting, where a capability exists and nothing invokes it.

Usage:
  python3 tools/file_atlas.py --out docs/FILE_ATLAS.csv --md docs/FILE_ATLAS.md
  python3 tools/file_atlas.py --check         # both bundle-default atlas files, no writes
  python3 tools/file_atlas.py --orphans        # just the orphan list, for the bunny-hop roll
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
from gen_tools_inventory import _catalog_code, _opening_paragraph  # shared catalog display parsing
import argparse
import ast
import csv
import io
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
            if any(s in SKIP_PARTS or s.startswith(".") for s in p.relative_to(ROOT).parts):
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
    summary = _opening_paragraph(ast.get_docstring(tree) or "")
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
    # Keep these same escaped/boundary expressions alive for the whole build.
    # Dynamic searches for every stem/file can churn the finite re cache.
    reference_patterns = {}
    for stem in stems:
        escaped = re.escape(stem)
        reference_patterns[stem] = (
            re.compile(rf"\b{escaped}\b"),
            re.compile(rf"\b{escaped}\.py\b"),
            re.compile(rf"^{escaped}\b", re.M),
        )
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
        if any(x in SKIP_PARTS or x.startswith(".") for x in sh.relative_to(ROOT).parts):
            continue
        txt = sh.read_text(encoding="utf-8", errors="ignore")
        for s_ in stems:
            _, script_pattern, line_pattern = reference_patterns[s_]
            if script_pattern.search(txt) or line_pattern.search(txt):
                shell_refs[s_].add(sh.name)

    # test references, by module stem
    tref = defaultdict(set)
    tdir = ROOT / "tests"
    if tdir.is_dir():
        for t in tdir.rglob("test_*.py"):
            if any(part == "__pycache__" or part.startswith(".") for part in t.relative_to(tdir).parts):
                continue
            txt = t.read_text(encoding="utf-8", errors="ignore")
            for s in stems:
                if reference_patterns[s][0].search(txt):
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
            "summary": summary,
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


def _summary_cell(summary: str) -> str:
    """Escape a Markdown cell without clipping the source description or altering CSV evidence."""
    return summary.replace("|", "\\|")


def _render_csv(rows):
    fh = io.StringIO(newline="")
    writer = _SafeDictWriter(fh, fieldnames=COLS)
    writer.writeheader()
    writer.writerows(rows)
    return fh.getvalue().encode("utf-8")


def _render_md(rows):
    orph = [r for r in rows if r["orphan"]]
    hot = sorted(rows, key=lambda r: -r["fan_in"])[:15]
    big = sorted(rows, key=lambda r: -r["loc"])[:15]
    untested = [r for r in rows if r["n_tests"] == 0]
    fh = io.StringIO()
    fh.write("# File atlas — every module and tool in the bundle\n\n")
    fh.write(f"Generated by `tools/file_atlas.py` from the real source tree. "
             f"**{len(rows)} files** under `mamey/` and `tools/`.\n\n")
    fh.write(f"- orphan candidates (no importer, no CLI verb, no test): **{len(orph)}**\n")
    fh.write(f"- files no test names at all: **{len(untested)}**\n")
    fh.write(f"- total lines: **{sum(r['loc'] for r in rows):,}**\n\n")
    fh.write("## Highest fan-in (change these carefully)\n\n| file | imported by | loc | summary |\n|---|---:|---:|---|\n")
    for r in hot:
        fh.write(f"| {_catalog_code(r['path'], table=True)} | {r['fan_in']} | {r['loc']} | {_summary_cell(r['summary'])} |\n")
    fh.write("\n## Largest files\n\n| file | loc | defs | fan-in | summary |\n|---|---:|---:|---:|---|\n")
    for r in big:
        fh.write(f"| {_catalog_code(r['path'], table=True)} | {r['loc']} | {r['n_defs']} | {r['fan_in']} | {_summary_cell(r['summary'])} |\n")
    fh.write("\n## Orphan candidates — the bunny-hop roll pool\n\n")
    fh.write("A module nothing imports, no CLI verb reaches, and no test names. "
             "Some are legitimate entry points; some are the defect class this project keeps hitting.\n\n")
    fh.write("| file | loc | summary |\n|---|---:|---|\n")
    for r in sorted(orph, key=lambda r: -r["loc"]):
        fh.write(f"| {_catalog_code(r['path'], table=True)} | {r['loc']} | {_summary_cell(r['summary'])} |\n")
    fh.write("\n## Every file\n\n| file | loc | fan-in | fan-out | tests | summary |\n|---|---:|---:|---:|---:|---|\n")
    for r in sorted(rows, key=lambda r: r["path"]):
        fh.write(f"| {_catalog_code(r['path'], table=True)} | {r['loc']} | {r['fan_in']} | {r['fan_out']} | "
                 f"{r['n_tests']} | {_summary_cell(r['summary'])} |\n")
    return fh.getvalue().encode("utf-8")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", help="CSV output path (check default: <bundle>/docs/FILE_ATLAS.csv)")
    ap.add_argument("--md", help="Markdown summary path (check default: <bundle>/docs/FILE_ATLAS.md)")
    ap.add_argument("--orphans", action="store_true", help="print orphan candidates only")
    ap.add_argument("--check", action="store_true", help="compare expected bytes without writing; with neither path, check both bundle defaults")
    a = ap.parse_args(argv)
    if a.check and a.orphans:
        ap.error("--check and --orphans are mutually exclusive")
    if a.check and not a.out and not a.md:
        a.out = str(ROOT / "docs/FILE_ATLAS.csv")
        a.md = str(ROOT / "docs/FILE_ATLAS.md")
    if a.out and a.md and pathlib.Path(a.out).resolve() == pathlib.Path(a.md).resolve():
        ap.error("CSV and Markdown outputs must have different paths")

    rows = build()
    if a.orphans:
        orph = [r for r in rows if r["orphan"]]
        emit(f"{len(orph)} orphan candidate(s) of {len(rows)} files "
              f"(no importer, no CLI verb, no test naming them):")
        for r in sorted(orph, key=lambda r: -r["loc"]):
            emit(f"  {r['loc']:5d} loc  {r['path']:44s} {r['summary']}")
        return 0

    outputs = []
    if a.out:
        outputs.append((pathlib.Path(a.out), _render_csv(rows)))
    if a.md:
        outputs.append((pathlib.Path(a.md), _render_md(rows)))
    failed = False
    for path, expected in outputs:
        message = None
        if a.check:
            try:
                actual = path.read_bytes()
            except OSError as exc:
                message = f"FILE ATLAS UNREADABLE: {path} ({type(exc).__name__})"
                failed = True
            else:
                if actual != expected:
                    message = f"FILE ATLAS STALE: {path}; regenerate with tools/file_atlas.py --out <csv> --md <markdown>"
                    failed = True
        else:
            path.write_bytes(expected)
            message = f"wrote {path}"
        if message is not None:
            emit(message)
    if a.check and not failed:
        emit(f"FILE ATLAS CURRENT: {len(outputs)} output(s), {len(rows)} source files")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
