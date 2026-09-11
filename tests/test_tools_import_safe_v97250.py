"""v9.7.250 — a tool must be importable without doing work.

Found by the orphan audit (`tools/file_atlas.py --orphans`): of 35 orphan candidates, 33 import
cleanly and **2 perform file I/O at module import**, because they have no
`if __name__ == "__main__":` guard and their top level is a script:

    tools/build_master.py   (325 loc)  json.load(open('bgc_data.json'))  at line 28
    tools/plot_examples.py   (57 loc)  reads figure_ready/strain_summary.csv

Both are already marked DEPRECATED in their own docstrings. That is not the point. The point is
that `import tools.build_master` executes a data pipeline against the current working directory —
so any tool that scans the tree by importing it (a linter, a doc generator, `file_atlas` itself if
it ever moved from `ast` to `import`) triggers that pipeline as a side effect.

This is the same shape as the defects the bunny hop keeps finding: not that the code is wrong, but
that a thing happens which nobody asked for.

Baseline ratchet, per the bundle idiom (`test_no_dangling_tool_paths_v97239.py::PATH_BASELINE`,
`check_duplicate_dict_keys.py::ALLOWLIST`): freeze the known set, fail on anything new. **The
baseline must only ever SHRINK.**

v9.7.416 — SCOPE REPAIR. The rule above is written about "a tool"; the gate only ever looked at
`tools/`. `deliverable_tools/` was never scanned, and it holds SEVEN more modules with the same
shape — measured with this file's own `_has_main_guard` / `_toplevel_work` detectors, unchanged.
Worse than the two baselined readers: several of the seven **write** at module import, into
`$SAPOTE_WORKSPACE_ROOT/sapote_deliverables/`. `import build_novelty_board` rewrites
`AS_cohort_novelty_board.md` and `.csv` before the importer's first statement runs. That is the
exact hazard this file's own rationale describes, one directory over, and it went unmeasured for
166 cuts because the glob said `tools` and the docstring said "a tool".

So: the scan now covers both directories, the baseline is keyed by RELATIVE PATH (two directories
can hold the same basename), and a second, stricter ratchet freezes the subset that WRITES at
import. Nothing here restructures those seven scripts — that is real follow-on work and they
cannot be exercised from inside the bundle — but the set is now measured, named, and can only
shrink. Same defect class as `measured-is-not-correctly-scoped`: the gate was real, the denominator
was not.
"""
from __future__ import annotations
import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCANNED_DIRS = ("tools", "deliverable_tools")

# Scripts whose top level is not import-safe today. Deprecated one-offs; delete the entry when the
# file grows a `main()` and a `__main__` guard, or when the file is removed.
NO_MAIN_GUARD_BASELINE = frozenset({
    # DEPRECATED frozen cohort one-off; json.load(open('bgc_data.json')) at line 28.
    "tools/build_master.py",
    # Reads figure_ready/strain_summary.csv at import. Example script, never imported in production.
    "tools/plot_examples.py",
    # v9.7.416 brought deliverable_tools/ into scope and baselined SEVEN more offenders here.
    # v9.7.417 REPAIRED all seven instead of carrying them: each grew a `__main__` guard, with the
    # body indented and otherwise untouched (AST-verified statement for statement). The baseline is
    # shrink-only and it shrank. Do not re-add them.
})

# The strict subset: module-level statements that WRITE, not merely read. A reader that fires on
# import is untidy; a writer that fires on import edits canonical deliverables. This set exists so
# the difference is visible and so it can only ever get smaller.
WRITES_AT_IMPORT_BASELINE = frozenset({
    # v9.7.417: the seven deliverable_tools/ writers are GONE from this ledger — guarded, not
    # excused. Measured before and after on the v9.7.416 candidate with SAPOTE_WORKSPACE_ROOT
    # pointed at an empty temp directory: importing build_working_genome_set.py wrote
    # `sapote_deliverables/WORKING_GENOME_SET_2026-08-03/WORKING_GENOME_SET.csv` before the guard
    # and nothing after it. (The other six crashed on missing inputs first in an EMPTY workspace —
    # which is the fixture being empty, not those scripts being safe; against a real workspace they
    # proceed.) One entry remains:
    "tools/plot_examples.py",   # savefig at import; DEPRECATED example script, never imported
})

# Node types that constitute "work at module import". Assignments and defs are fine; a bare call,
# a with-block, a loop, or a try that runs at top level is not.
_WORKING = (ast.Expr, ast.With, ast.For, ast.While, ast.Try)

# Calls that put bytes on disk. Deliberately conservative: a false positive here would push a
# clean tool into a shrink-only ledger, which is worse than missing one. `open(..., "w"/"a"/"x")`
# is handled by mode; `write`/`writelines` are handled with a stdout/stderr exclusion (terminal
# emission is not a disk write -- `sys.stderr.write` at import is normal and correct); and the
# names that collide with non-filesystem builtins (`copy`, `remove`, `replace`, `rename`, `unlink`
# -- cf. `copy.copy`, `list.remove`, `str.replace`) count only when called on `os` or `shutil`.
_WRITE_CALLS = {"write_text", "write_bytes", "writerow", "writerows", "writeheader",
                "to_csv", "to_excel", "savefig", "makedirs", "copytree", "rmtree"}
_MODULE_QUALIFIED = {"os": {"remove", "unlink", "rename", "replace", "makedirs", "mkdir"},
                     "shutil": {"copy", "copy2", "copytree", "move", "rmtree"}}
_STREAMS = ("stdout", "stderr")


def _tool_files():
    out = []
    for d in SCANNED_DIRS:
        base = ROOT / d
        if not base.is_dir():
            continue
        # v9.7.418 (BLIZZARD_BLUE-418): rglob, not glob. `deliverable_tools/` and `tools/` are NOT
        # flat — 13 modules live one level down (strain_portfolio/, cohort_tailoring/,
        # blastp_monitoring/) and a flat glob never saw any of them, including two build scripts.
        # That is the same miss this file's own docstring records for `deliverable_tools/`: the
        # glob said one thing and the docstring said "a tool". Measured at .417: 358 -> 371 files,
        # and ZERO of the 13 lack a `__main__` guard, so widening the scope adds no baseline debt.
        out += [p for p in base.rglob("*.py")
                if p.name != "__init__.py" and "__pycache__" not in p.parts]
    return sorted(out, key=lambda p: _rel(p))


def _rel(p: pathlib.Path) -> str:
    return p.relative_to(ROOT).as_posix()


def _has_main_guard(tree: ast.Module) -> bool:
    for node in tree.body:
        if isinstance(node, ast.If):
            src = ast.dump(node.test)
            if "__name__" in src and "__main__" in src:
                return True
    return False


def _toplevel_work(tree: ast.Module) -> list[str]:
    """Statements at module level that DO something, excluding docstrings and dunder calls."""
    out = []
    for i, node in enumerate(tree.body):
        if isinstance(node, ast.Expr):
            # a bare string at position 0 is the module docstring
            if i == 0 and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                continue
            if isinstance(node.value, ast.Constant):
                continue  # a stray literal does no work
            out.append(f"line {node.lineno}: bare expression")
        elif isinstance(node, _WORKING[1:]):
            out.append(f"line {node.lineno}: {type(node).__name__} at module level")
    return out


def _is_write_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    name = func.attr if isinstance(func, ast.Attribute) else (func.id if isinstance(func, ast.Name) else "")
    if name in _WRITE_CALLS:
        return True
    if name in ("write", "writelines") and isinstance(func, ast.Attribute):
        return not any(stream in ast.dump(func.value) for stream in _STREAMS)
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        if name in _MODULE_QUALIFIED.get(func.value.id, ()):
            return True
    if name == "open":
        modes = [a for a in node.args[1:] if isinstance(a, ast.Constant)]
        modes += [kw.value for kw in node.keywords
                  if kw.arg == "mode" and isinstance(kw.value, ast.Constant)]
        return any(isinstance(m.value, str) and ("w" in m.value or "a" in m.value or "x" in m.value)
                   for m in modes)
    return False


def _toplevel_writes(tree: ast.Module) -> list[int]:
    """Line numbers of write calls reachable at module import (outside the __main__ guard)."""
    lines = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        if isinstance(node, ast.If):
            src = ast.dump(node.test)
            if "__name__" in src and "__main__" in src:
                continue
        for n in ast.walk(node):
            if _is_write_call(n):
                lines.append(getattr(n, "lineno", -1))
    return sorted(set(lines))


def _parse(p: pathlib.Path):
    try:
        return ast.parse(p.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return None


def test_no_new_tool_lacks_a_main_guard():
    """A tool with executable top-level statements must guard them behind __main__."""
    offenders = []
    for p in _tool_files():
        tree = _parse(p)
        if tree is None or _has_main_guard(tree):
            continue
        work = _toplevel_work(tree)
        if work:
            offenders.append((_rel(p), work[0]))
    new = sorted(f"{rel}: {w}" for rel, w in offenders if rel not in NO_MAIN_GUARD_BASELINE)
    assert not new, (
        "Tool(s) do work at module import and have no `if __name__ == \"__main__\":` guard:\n  "
        + "\n  ".join(new)
        + "\nWrap the script body in a main() and guard it, or add the file to "
          "NO_MAIN_GUARD_BASELINE with a one-line reason."
    )


def test_no_new_tool_writes_at_import():
    """Stricter than the guard rule: importing a tool must not put bytes on disk.

    v9.7.416. A reader firing on import is untidy. A writer firing on import edits real
    deliverables — `deliverable_tools/build_novelty_board.py` rewrites
    `<workspace>/sapote_deliverables/AS_cohort_novelty_board.{md,csv}` before the importing
    statement returns. This set may only shrink.
    """
    offenders = []
    for p in _tool_files():
        tree = _parse(p)
        if tree is None:
            continue
        writes = _toplevel_writes(tree)
        if writes:
            offenders.append((_rel(p), writes[:4]))
    new = sorted(f"{rel}: write at line(s) {ls}" for rel, ls in offenders
                 if rel not in WRITES_AT_IMPORT_BASELINE)
    assert not new, (
        "Tool(s) WRITE at module import:\n  " + "\n  ".join(new)
        + "\nMove the write behind a main() + `__main__` guard. Do not extend "
          "WRITES_AT_IMPORT_BASELINE for new code — it is a shrink-only ledger of known one-offs."
    )


def test_baseline_is_a_ratchet():
    """A file that grows a guard (or is deleted) must leave the baseline."""
    stale = []
    for rel in sorted(NO_MAIN_GUARD_BASELINE):
        p = ROOT / rel
        if not p.exists():
            stale.append(f"{rel} (deleted)")
            continue
        tree = _parse(p)
        if tree is None:
            continue
        if _has_main_guard(tree) or not _toplevel_work(tree):
            stale.append(f"{rel} (now import-safe)")
    assert not stale, f"NO_MAIN_GUARD_BASELINE entries no longer offend; delete them: {stale}"


def test_write_baseline_is_a_ratchet():
    """Same shrink-only discipline for the stricter write ledger."""
    stale = []
    for rel in sorted(WRITES_AT_IMPORT_BASELINE):
        p = ROOT / rel
        if not p.exists():
            stale.append(f"{rel} (deleted)")
            continue
        tree = _parse(p)
        if tree is None:
            continue
        if not _toplevel_writes(tree):
            stale.append(f"{rel} (no longer writes at import)")
    assert not stale, f"WRITES_AT_IMPORT_BASELINE entries no longer offend; delete them: {stale}"


def test_the_known_offenders_are_still_detected():
    """Positive control: the gate must actually see what the audits found, in BOTH directories."""
    detected = set()
    for p in _tool_files():
        tree = _parse(p)
        if tree is None:
            continue
        if not _has_main_guard(tree) and _toplevel_work(tree):
            detected.add(_rel(p))
    assert NO_MAIN_GUARD_BASELINE <= detected, (
        f"gate no longer detects the baselined offenders: {NO_MAIN_GUARD_BASELINE - detected}"
    )


def test_the_scan_actually_covers_deliverable_tools():
    """The v9.7.416 scope repair itself, asserted — not just implied by the baseline.

    Without this, someone narrowing `SCANNED_DIRS` back to ("tools",) would still pass every test
    above: the baseline entries would simply stop being detected, and `test_baseline_is_a_ratchet`
    only fires on files that exist and are clean. That is exactly how the blind spot survived.
    """
    scanned = {_rel(p) for p in _tool_files()}
    assert any(rel.startswith("deliverable_tools/") for rel in scanned), (
        "deliverable_tools/ is not being scanned; the v9.7.416 scope repair has been undone")
    assert any(rel.startswith("tools/") for rel in scanned)
