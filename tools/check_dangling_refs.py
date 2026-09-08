#!/usr/bin/env python3
"""check_dangling_refs.py — list references to `examples/<file>` OR tool/module names that don't
resolve in the tree.

WHY (audit v9.7.95, P-A6; extended v9.7.213-audit). `examples/` was empty at the time of the original
audit; it has since been populated (5 files + 3 subdirs as of this cut), but live docs still point
at exemplar/fixture files under it that may not individually resolve. This
detector surfaces them on demand; the standing guard `tests/test_no_dangling_examples_refs_v9795.py`
enforces a no-new-dangling-ref contract against a documented baseline.

v9.7.213-audit added a SECOND, independent scope: backtick-quoted `<name>.py`/`.sh` tool/module
references. This closes a real gap the examples/-only scope never covered — found by hand in the
same audit: `FIGURES_START_HERE.md` named a `build_bee_wasp_master_figures.py` that does not exist
anywhere in the tree, and `docs/GUIDE/06_Concepts_QandA.md` described a fully-fabricated
`apply_hygiene.sh` (specific fake behavior, zero CHANGELOG/PATCH_APPLY_LOG trace). Neither the
examples/ scanner nor `check_module_accretion.py` (mamey/-only) would ever have caught either.
This is a heuristic, not a semantic understanding of intent: forward-looking specs/wishlists and
docs describing deliberately-per-session glue scripts are excluded by filename pattern
(TOOLS_HIST) or by an explicit allowlist (TOOLS_ALLOW), not by understanding the prose. New
legitimate exceptions need a TOOLS_ALLOW entry with a one-line reason, mirroring the
Consolidates:/Accretion-justified: discipline in check_module_accretion.py — this does not catch
everything, and false negatives from an under-scoped allowlist are possible.

Scope: scans shipped .md/.txt/.html, excluding tests/ and historical docs (CHANGELOG, BUNDLE_PATCH_NOTES_*,
RELEASE_NOTES_*, PATCH_NOTES_*) whose references describe past states. Run from the bundle root or pass --root.

Usage:
  python tools/check_dangling_refs.py                  # examples/ scope only (original, unchanged)
  python tools/check_dangling_refs.py --scope tools     # tool/module-name scope only (new)
  python tools/check_dangling_refs.py --scope all       # both

Exit 0 = nothing dangling in the requested scope(s); 1 = at least one found.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import pathlib
import re
import sys

REF = re.compile(r'examples/[A-Za-z0-9_./-]+\.(?:md|zip|xlsx|csv|json|py|html)')
HIST = re.compile(r"(CHANGELOG\.md$|BUNDLE_PATCH_NOTES_|RELEASE_NOTES_|PATCH_NOTES_)")
# Meta-docs that *describe* the dangling refs (the audit ledger) must not count as committing them,
# or the baseline could never be tightened to zero once the real docs are fixed.
META_SKIP = {"EXAMPLES_REFERENCE_LEDGER.md"}

# --- tools/module-name scope (new, v9.7.213-audit) --------------------------------------------
TOOL_REF = re.compile(r"`([A-Za-z0-9_\-/\.]+\.(?:py|sh))`")
# Forward-looking or explicitly-historical doc classes: a reference here describes a plan, a past
# state, or per-session glue, never a claim that the file ships in THIS tree today.
TOOLS_HIST = re.compile(
    r"(CHANGELOG\.md$|PATCH_NOTES_|RELEASE_NOTES_|BUNDLE_PATCH_NOTES_|_SPEC\.md$|_WISHLIST|"
    r"drift_map|ISSUES_EXPERIENCED|RECONCILIATION_|patch_notes/|history/|working/)"
)
# Placeholder tokens used as generic code-example filler in template/game docs, not real tool claims.
TOOLS_PLACEHOLDER = {"file.py", "main.py", "run.py", "manifest.py", "parsing.py", "scans.py",
                      "validation.py", "some_script.py", "record_processing.py"}
# Confirmed-legitimate exceptions found during the v9.7.213 audit: real capabilities that are
# deliberately NOT shipped as tree files. Each entry needs a one-line reason; add here, don't
# silently suppress.
TOOLS_ALLOW = {
    "build_factsheet.py": "per-session glue script, created on demand — docs/runbooks/AutoPipeline_antiSMASH_to_Compendium.md:9",
    "build_handoff.py": "per-session glue script, created on demand — same runbook",
    "sapote_completeness_audit.py": "per-session glue script — docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md §15.11 says upload/create at session start",
    "sapote_excel_generator.py": "per-session glue script — same convention",
    "sapote_pdf_styles.py": "per-session glue script — same convention",
    # v9.7.242: docs/user_guides/ describe the wider project, not just this bundle's tools/ dir.
    "bunny_hop_audit_game.py": "games/ tree, not shipped in the code tiers — docs/user_guides/tools_reference.md",
    "workbook_status.py": "operator glue script, created on demand — docs/user_guides/tools_reference.md",
    "setup.py": "packaging entry point, not a tools/ script — docs/user_guides/sapote_mamey_wheel_glossary.md",
    # v9.7.382: GToTree's OWN internal files, named in the vendored upstream contribution
    # tools/upstream_gtotree2/ (a patch + author note we ship to send upstream) — not bundle tools.
    "get_ncbi_assembly_data.py": "GToTree-internal file named in tools/upstream_gtotree2/ upstream patch",
    "get_gtdb_data.py": "GToTree-internal file named in tools/upstream_gtotree2/ upstream patch",
    "handle_ncbi_tax_info.py": "GToTree-internal file named in tools/upstream_gtotree2/ upstream patch",
    "data_locations.py": "GToTree-internal file named in tools/upstream_gtotree2/ upstream patch",
}
# v9.7.371: "hooks" and "sapote_hooks" added — the v9.7.370 cut shipped those directories (VGP
# hook_guard_org card) but this detector never learned them, so any doc naming a genuinely-shipped
# hook (e.g. sapote_hooks.py, SEAL_GATE_snippet.sh) was flagged as a dangling reference.
SEARCH_DIRS = ("tools", "mamey", "scripts", "tests", "Wheelhouse", "deliverable_tools", "hooks", "sapote_hooks", ".")


def _warn_unreadable(p: pathlib.Path, root: pathlib.Path, exc: Exception) -> None:
    """BC2-CDR-01 (v9.7.395): both scan() and scan_tools() had `except Exception: continue` with
    no signal of any kind when a candidate .md/.txt/.html file couldn't be read (permission
    error, broken symlink, etc.) — the file was silently excluded from the audit and any real
    dangling reference it contained went unreported. Reproduced: a permission-denied .md file
    containing a genuine dangling `examples/` reference made scan() return `{}` (clean) with zero
    indication the file was ever skipped. Print a visible warning instead — this is a printed
    note, not a new dict key, so it cannot corrupt the dangling-ref result shape any existing
    caller/test relies on."""
    try:
        rel = str(p.relative_to(root))
    except ValueError:
        rel = str(p)
    emit(f"check_dangling_refs: WARNING: could not read {rel} ({exc}); "
          f"this file was NOT scanned for dangling references", file=sys.stderr)


def _existing_tool_names(root: pathlib.Path) -> set[str]:
    names: set[str] = set()
    for d in SEARCH_DIRS:
        base = root / d
        if not base.exists():
            continue
        it = base.glob("*.py") if d == "." else base.rglob("*.py")
        for p in it:
            if "__pycache__" not in str(p):
                names.add(p.name)
        it2 = base.glob("*.sh") if d == "." else base.rglob("*.sh")
        for p in it2:
            names.add(p.name)
    return names


def scan(root: pathlib.Path):
    """Return {target: [referencing_files...]} for unresolved examples/ targets."""
    out: dict[str, set] = {}
    for p in list(root.rglob("*.md")) + list(root.rglob("*.txt")) + list(root.rglob("*.html")):
        parts = p.relative_to(root).parts
        if "tests" in parts or HIST.search(str(p)) or p.name in META_SKIP:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            _warn_unreadable(p, root, e)
            continue
        for tok in {m.group(0) for m in REF.finditer(txt)}:
            if not (root / tok).exists():
                out.setdefault(tok, set()).add(str(p.relative_to(root)))
    return out


def scan_tools(root: pathlib.Path, strict_paths: bool = False):
    """Return {name: [referencing_files...]} for backtick-quoted tool/module names that don't
    resolve anywhere under SEARCH_DIRS, after excluding historical/forward-looking docs, generic
    placeholders, and the explicit TOOLS_ALLOW list.

    v9.7.238 (F03): with `strict_paths=True`, a reference that carries a directory (e.g.
    `tools/sapote_workflow.py`) is resolved as a FULL relative path, not just its basename.
    Basename-only matching let `tools/sapote_workflow.py` be satisfied by `mamey/sapote_workflow.py`,
    so a doc/ledger could cite a path that does not exist — exactly the F01 miss.
    """
    existing = _existing_tool_names(root)
    out: dict[str, set] = {}
    for p in root.rglob("*.md"):
        rel = str(p.relative_to(root))
        parts = p.relative_to(root).parts
        if "tests" in parts or TOOLS_HIST.search(rel) or p.name in META_SKIP:
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            _warn_unreadable(p, root, e)
            continue
        for m in TOOL_REF.finditer(txt):
            raw = m.group(1)
            name = pathlib.Path(raw).name
            if name in TOOLS_PLACEHOLDER or name in TOOLS_ALLOW:
                continue
            if strict_paths and "/" in raw:
                # path-qualified: the exact relative path must exist
                if not (root / raw).exists():
                    out.setdefault(raw, set()).add(rel)
                continue
            if name in existing:
                continue
            out.setdefault(name, set()).add(rel)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict-paths", action="store_true", dest="strict_paths",
                    help="resolve path-qualified refs (tools/X.py) by full relative path, not basename (F03)")
    ap.add_argument("--scope", choices=["examples", "tools", "all"], default="examples",
                     help="examples/ refs only (default, backward-compatible), tool/module-name refs only, or both")
    args = ap.parse_args(argv)
    root = pathlib.Path(args.root).resolve()

    results = {}
    if args.scope in ("examples", "all"):
        results["examples"] = scan(root)
    if args.scope in ("tools", "all"):
        results["tools"] = scan_tools(root, strict_paths=getattr(args, "strict_paths", False))

    any_dangling = any(results.values())
    if args.json:
        import json
        emit(json.dumps(
            {scope: {k: sorted(v) for k, v in sorted(d.items())} for scope, d in results.items()},
            indent=2))
    else:
        if "examples" in results:
            d = results["examples"]
            if not d:
                emit("no dangling examples/ references")
            else:
                emit(f"{len(d)} dangling examples/ target(s):")
                for tok in sorted(d):
                    emit(f"  {tok}")
                    for f in sorted(d[tok]):
                        emit(f"       referenced in {f}")
        if "tools" in results:
            d = results["tools"]
            if not d:
                emit("no dangling tool/module-name references")
            else:
                emit(f"{len(d)} dangling tool/module-name reference(s):")
                for tok in sorted(d):
                    emit(f"  {tok}")
                    for f in sorted(d[tok]):
                        emit(f"       referenced in {f}")
    return 1 if any_dangling else 0


if __name__ == "__main__":
    raise SystemExit(main())
