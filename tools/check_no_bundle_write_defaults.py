#!/usr/bin/env python3
"""check_no_bundle_write_defaults.py — stop a tool from defaulting a WRITE into the code bundle.

`workspace_root()` and `os.environ.get(X, os.getcwd())` fall back to the current directory.
Tools run from the bundle root, so an unguarded write under such a root lands inside the sealed
bundle. The fix is `mamey.path_safety.assert_output_outside_bundle(path, __file__)` before the
write (see tools/phylo_place.py and tools/mibig_neighborhoods.py). This check finds sites that
do not do that.

It reads source with `ast` and flags a site only when both hold:

  - the call is a write sink: `open(p, "w"/"a"/...)`, `os.makedirs(p)` / `p.mkdir()`, or
    `add_argument("--out..."/"--dir...", default=p)`;
  - `p` comes from a cwd-fallback root: a name assigned from `os.getcwd()` or
    `workspace_root()`, or a name assigned from one of those names (for example
    `CACHE = os.environ.get("X", f"{ROOT}/cache")`). Names are resolved per function scope;
    `if __name__ == "__main__":` code is module scope.

It does not flag a root anchored to `__file__` (a tool that regenerates its own shipped data),
a marker-walk resolver with a `__file__` fallback, or a write in a function that calls
`assert_output_outside_bundle` directly or through a same-module wrapper function. It does not see `shutil`, pandas or `Path.write_text` writes.

    python3 tools/check_no_bundle_write_defaults.py [BUNDLE_ROOT] [--max N]

Exit 0 when the count of unguarded sites is at most N (default 0), 1 when it is higher, 2 when
the tree could not be scanned. N is a ratchet ceiling: a known backlog does not block a cut, and
a new site does. Lower N as sites adopt the guard. ALLOWLIST is for owner-accepted exceptions;
each entry needs a reason, and an entry is a waiver, not a fix.
"""
import os as _os, sys as _sys  # resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402
import argparse
import ast
import pathlib
import sys

SCAN_DIRS = ("tools", "mamey", "deliverable_tools")
_WRITE_MODES = {"w", "a", "x", "w+", "a+", "wb", "ab", "xb", "wt", "at"}
_OUT_ARG_HINTS = ("--out", "--outdir", "--dir", "--od", "--o")

# Sites accepted by explicit owner decision. Format: "relpath:function" -> reason.
# A waiver, not a fix. Empty: the known backlog is carried by the --max ceiling instead.
ALLOWLIST: dict[str, str] = {}


def _rhs_is_cwd_fallback(rhs: ast.AST) -> bool:
    """True if an assignment RHS derives a root from the CWD fallback — the litter class.

    Matches `os.getcwd()`, a `workspace_root(...)` call, or `os.environ.get(X, os.getcwd())`.
    Does NOT match a `__file__`/dirname-anchored root (a deliberate in-bundle regenerator) or a
    marker-walk resolver with a `__file__` fallback (safe in the normal layout).
    """
    for n in ast.walk(rhs):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
            if name in ("getcwd", "workspace_root"):
                return True
    return False


def _cwd_names_by_scope(tree: ast.AST, func_of: dict):
    """Bucket cwd-fallback-assigned names by their scope.

    Python creates a new scope only for functions, not for `if`/`for`/`with`, so an assignment
    inside a module-level `if __name__ == "__main__":` block is module scope. Returns
    (module_names, {func_node: names}). A sink's visible danger set is the module names plus its
    enclosing function's names — and a same-named local in another function does not leak in.
    """
    # Collect every scope's assignments once, then taint to a fixpoint: a name is dangerous if its
    # RHS is a cwd fallback, OR references a name already dangerous in the same scope (one or more
    # levels of `CACHE = env.get("X", f"{ROOT}/...")` indirection). Only widens via already-danger
    # references, so a __file__-anchored root never becomes dangerous.
    assigns: dict = {}  # scope key (None=module, else id(func)) -> list of (targets, rhs)
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            key = None if func_of.get(n) is None else id(func_of.get(n))
            names = [t.id for t in n.targets if isinstance(t, ast.Name)]
            if names:
                assigns.setdefault(key, []).append((names, n.value))
    danger_by_scope: dict = {}
    for key, items in assigns.items():
        d: set[str] = set()
        changed = True
        while changed:
            changed = False
            for names, rhs in items:
                if any(nm in d for nm in names):
                    continue
                if _rhs_is_cwd_fallback(rhs) or _refs_root(rhs, d):
                    d.update(names)
                    changed = True
        danger_by_scope[key] = d
    module_names = danger_by_scope.get(None, set())
    by_func = {k: v for k, v in danger_by_scope.items() if k is not None}
    return module_names, by_func


def _refs_root(node: ast.AST, danger: set[str]) -> bool:
    """True if the expression references a litter-class root name or calls workspace_root()."""
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in danger:
            return True
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name) and f.id == "workspace_root":
                return True
            if isinstance(f, ast.Attribute) and f.attr == "workspace_root":
                return True
    return False


def _is_rootish(arg: ast.AST | None, danger: set[str]) -> bool:
    if arg is None:
        return False
    # f-string, str() wrap, or a BinOp concat that mentions a litter-class root
    return isinstance(arg, (ast.JoinedStr, ast.BinOp, ast.Call, ast.Name, ast.Attribute)) and _refs_root(arg, danger)


def _enclosing_funcs(tree: ast.AST):
    """Map each node to its nearest enclosing FunctionDef (None at module scope), in one pass."""
    func_of = {}
    stack = [(tree, None)]
    while stack:
        node, fn = stack.pop()
        func_of[node] = fn
        inner = node if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else fn
        for child in ast.iter_child_nodes(node):
            stack.append((child, inner))
    return func_of


_GUARD = "assert_output_outside_bundle"


def _call_name(n: ast.Call) -> str:
    f = n.func
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")


def _guard_wrappers(tree: ast.AST) -> set[str]:
    """Same-module functions whose body calls the guard; calling one counts as guarding."""
    names = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if any(isinstance(c, ast.Call) and _call_name(c) == _GUARD for c in ast.walk(n)):
                names.add(n.name)
    return names


def _func_has_guard(func: ast.AST | None, tree: ast.AST, wrappers: set[str]) -> bool:
    scope = func if func is not None else tree
    for n in ast.walk(scope):
        if isinstance(n, ast.Call) and (_call_name(n) == _GUARD or _call_name(n) in wrappers):
            return True
    return False


def _sinks(tree: ast.AST):
    """Yield (call_node, kind, arg_expr) for every write sink, before the root-class filter."""
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        fname = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else "")
        # 1) open(path, mode)
        if fname == "open" and n.args:
            mode = None
            if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                mode = n.args[1].value
            for kw in n.keywords:
                if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                    mode = kw.value.value
            if mode in _WRITE_MODES:
                yield (n, "open(w)", n.args[0])
        # 2) makedirs / mkdir
        elif fname in ("makedirs", "mkdir") and n.args:
            yield (n, fname, n.args[0])
        # 3) add_argument("--out...", default=<expr>)
        elif fname == "add_argument" and n.args and isinstance(n.args[0], ast.Constant) \
                and isinstance(n.args[0].value, str) and n.args[0].value.startswith(tuple(_OUT_ARG_HINTS)):
            for kw in n.keywords:
                if kw.arg == "default":
                    yield (n, f"argparse {n.args[0].value} default", kw.value)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail on unguarded ROOT-relative write defaults.")
    ap.add_argument("root", nargs="?", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--max", type=int, default=0, help="ratchet ceiling: allowed unguarded sites")
    a = ap.parse_args()
    root = pathlib.Path(a.root)
    files = []
    for d in SCAN_DIRS:
        base = root / d
        if base.is_dir():
            files += sorted(base.rglob("*.py"))
    if not files:
        sys.stderr.write(f"WRITE-DEFAULT CHECK REFUSED — scanned 0 files under {root}. Check the ROOT arg.\n")
        return 2
    findings = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            sys.stderr.write(f"WRITE-DEFAULT CHECK COULD NOT READ {path}: {e}\n")
            return 2
        if "getcwd" not in text and "workspace_root" not in text:
            continue  # no cwd-fallback root can exist in this file
        try:
            tree = ast.parse(text, filename=str(path))
        except (SyntaxError, UnicodeDecodeError) as e:
            sys.stderr.write(f"WRITE-DEFAULT CHECK COULD NOT PARSE {path}: {e}\n")
            return 2
        func_of = _enclosing_funcs(tree)
        module_danger, by_func = _cwd_names_by_scope(tree, func_of)
        wrappers = _guard_wrappers(tree)
        for call_node, kind, arg_expr in _sinks(tree):
            sink_func = func_of.get(call_node)
            danger = module_danger | (by_func.get(id(sink_func), set()) if sink_func is not None else set())
            if not _is_rootish(arg_expr, danger):
                continue
            if _func_has_guard(sink_func, tree, wrappers):
                continue
            rel = str(path.relative_to(root))
            fn = sink_func.name if isinstance(sink_func, (ast.FunctionDef, ast.AsyncFunctionDef)) else "<module>"
            key = f"{rel}:{fn}"
            if key in ALLOWLIST:
                continue
            findings.append((rel, call_node.lineno, fn, kind))
    for rel, lineno, fn, kind in findings:
        emit(f"  {rel}:{lineno}  in {fn}()  [{kind}]")
    if len(findings) > a.max:
        emit(f"BUNDLE-WRITE-DEFAULT CHECK FAILED — {len(findings)} unguarded ROOT-relative write "
             f"default(s), ceiling {a.max}. Adopt mamey.path_safety.assert_output_outside_bundle, "
              f"or add an explicit dated waiver to ALLOWLIST with a reason.")
        return 1
    emit(f"bundle-write-default check OK — {len(findings)} unguarded site(s), ceiling {a.max} "
         f"({len(files):,} file(s) scanned under {root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
