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
"""
from __future__ import annotations
import ast
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"

# Scripts whose top level is not import-safe today. Deprecated one-offs; delete the entry when the
# file grows a `main()` and a `__main__` guard, or when the file is removed.
NO_MAIN_GUARD_BASELINE = frozenset({
    # DEPRECATED frozen cohort one-off; json.load(open('bgc_data.json')) at line 28.
    "build_master.py",
    # Reads figure_ready/strain_summary.csv at import. Example script, never imported in production.
    "plot_examples.py",
})

# Node types that constitute "work at module import". Assignments and defs are fine; a bare call,
# a with-block, a loop, or a try that runs at top level is not.
_WORKING = (ast.Expr, ast.With, ast.For, ast.While, ast.Try)


def _tool_files():
    return sorted(p for p in TOOLS.glob("*.py") if p.name != "__init__.py")


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


def test_no_new_tool_lacks_a_main_guard():
    """A tool with executable top-level statements must guard them behind __main__."""
    offenders = []
    for p in _tool_files():
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        if _has_main_guard(tree):
            continue
        work = _toplevel_work(tree)
        if work:
            offenders.append(f"{p.name}: {work[0]}")
    new = sorted(o for o in offenders if o.split(":")[0] not in NO_MAIN_GUARD_BASELINE)
    assert not new, (
        "Tool(s) do work at module import and have no `if __name__ == \"__main__\":` guard:\n  "
        + "\n  ".join(new)
        + "\nWrap the script body in a main() and guard it, or add the file to "
          "NO_MAIN_GUARD_BASELINE with a one-line reason."
    )


def test_baseline_is_a_ratchet():
    """A file that grows a guard (or is deleted) must leave the baseline."""
    stale = []
    for name in sorted(NO_MAIN_GUARD_BASELINE):
        p = TOOLS / name
        if not p.exists():
            stale.append(f"{name} (deleted)")
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        if _has_main_guard(tree) or not _toplevel_work(tree):
            stale.append(f"{name} (now import-safe)")
    assert not stale, f"NO_MAIN_GUARD_BASELINE entries no longer offend; delete them: {stale}"


def test_the_two_known_offenders_are_still_detected():
    """Positive control: the gate must actually see what the audit found."""
    detected = set()
    for p in _tool_files():
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        if not _has_main_guard(tree) and _toplevel_work(tree):
            detected.add(p.name)
    assert NO_MAIN_GUARD_BASELINE <= detected, (
        f"gate no longer detects the baselined offenders: {NO_MAIN_GUARD_BASELINE - detected}"
    )
