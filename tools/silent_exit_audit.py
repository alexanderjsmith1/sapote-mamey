#!/usr/bin/env python3
"""Inventory of SILENT SUCCESS EXITS in the guard surface.

The failure class this exists for: a guard that returns success on a condition and says nothing.
`repo_health.py` already ratchets `except ...: pass` (`silent_swallow`) — that catches a swallowed
*error*. This catches a swallowed *verdict*: the guard decided not to act, and the operator cannot
tell that from the guard deciding everything was fine.

Five defects in the v9.7.415 optional hooks were of exactly this shape. Two of the five were
invisible to the whole test suite because the fixture always configured the happy path, so the
silent branch was never entered.

Silence is NOT automatically a defect. A hook that fails open on unparseable stdin is correct; a
detector that says nothing because nothing was ever baselined is correct. So this tool CLASSIFIES
and reports a denominator — it does not accuse. Read the classes, not the total.

    python3 tools/silent_exit_audit.py                     # default scope: hooks/
    python3 tools/silent_exit_audit.py --scope hooks tools # widen
    python3 tools/silent_exit_audit.py --class REVIEW      # only the ones worth a human
    python3 tools/silent_exit_audit.py --ceiling 40        # ratchet mode: exit 1 above the ceiling
"""
from __future__ import annotations

import argparse
import ast
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _console import emit  # noqa: E402  the tools/ terminal-emission seam (v9.7.407)

# An exit is "silent" unless one of these emits on the same path.
# `emit` is this codebase's own console helper (mamey/_console.py). Leaving it out made every
# `emit(...); return 1` error path in mamey/cli.py read as silence — the tool's first engine-wide
# run reported 39 REVIEW, and its top three mamey/cli.py rows were all this false positive.
_EMITTERS = {"print", "emit", "write", "warn", "warning", "error", "info", "debug", "critical",
             "exception", "log", "showwarning", "echo"}

# Classification of the CONDITION that leads to the silent exit.
_UNPARSEABLE = ("json", "loads", "load", "decode", "parse", "valueerror", "except")
_ABSENT_INPUT = ("isfile", "exists", "isdir", "getsize", "listdir", "stat", "access")
_DISPATCH = __import__("re").compile(
    r"\b(mode|tool|tool_name|event|hook_event_name|hookeventname|action|cmd|command|subcommand)\b"
    r"\s*(==|!=|\bin\b|\bnot in\b)")
_NEGATED = __import__("re").compile(r"\bnot\b|!=|\bis none\b")

_EMPTY_VALUE = ("not text", "not txt", "not cmd", "not payload", "strip()", "== \"\"", "is none",
                "not asst", "not user", "not tpath", "not path")


def _emits(node: ast.AST, speakers: frozenset[str] = frozenset()) -> bool:
    """Does anything on this subtree produce operator-visible output?

    `speakers` carries module-level functions whose own body emits, resolved one level deep. Without
    it a branch that delegates its warning to a helper — `_warn_unconfigured(root); return 0` — read
    as silence, which made the tool keep flagging a branch that had just been repaired.
    """
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            f = n.func
            name = getattr(f, "id", None) or getattr(f, "attr", None)
            if name in _EMITTERS or name in speakers:
                return True
    return False


def _speaking_functions(tree: ast.AST) -> frozenset[str]:
    """Module-level functions that emit directly. One level only — deeper chains stay flagged."""
    return frozenset(fn.name for fn in ast.walk(tree)
                     if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and any(_emits(st) for st in fn.body))


def _is_success_exit(node: ast.AST, in_main: bool) -> bool:
    """A VERDICT is a success status, not a value.

    `return None` from a helper such as `_identify()` means "I could not tell", and the caller still
    decides — flagging it produced the tool's only real false positive on its first run
    (`block_subagent_spawn.py:98`). So a bare `return` / `return None` counts only inside the hook's
    own decision function.
    """
    if isinstance(node, ast.Return):
        v = node.value
        if v is None or (isinstance(v, ast.Constant) and v.value is None):
            return in_main
        # `v.value in (0, True)` matched `return 1`, because `True == 1` in Python. A failure
        # status is not a success exit; compare with the bool type excluded.
        if isinstance(v, ast.Constant):
            if isinstance(v.value, bool):
                return v.value is True and in_main
            return v.value in (0, "", [])
        return False
    if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
        f = node.value.func
        if getattr(f, "attr", None) == "exit" and getattr(getattr(f, "value", None), "id", "") == "sys":
            a = node.value.args
            return not a or (isinstance(a[0], ast.Constant) and a[0].value in (0, None))
    if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
        if getattr(node.exc.func, "id", "") == "SystemExit":
            a = node.exc.args
            return not a or (isinstance(a[0], ast.Constant) and a[0].value in (0, None))
    return False


def _is_dispatch(c: str) -> bool:
    """`if mode == 'baseline': return 0` is control flow, not a swallowed verdict.

    An equality or membership test on a mode/tool/event selector routes the call somewhere else; the
    hook is not declining to speak, it is answering a different question. Counting these was what
    made the first run of this tool cry wolf 41 times on 20 files.
    """
    return bool(_DISPATCH.search(c))


def _classify(cond: str, in_handler: bool) -> tuple[str, str]:
    c = cond.lower()
    if in_handler or any(k in c for k in _UNPARSEABLE):
        return "FAIL_OPEN", "error or unparseable input — silence is the documented contract"
    if _is_dispatch(c):
        return "DISPATCH", "routes on a mode/tool selector — not a verdict"
    # Only a NEGATED existence test is the hazard: `if not isfile(x): return 0` means the thing the
    # guard was told to watch is not there, and the operator sees the same nothing either way.
    if any(k in c for k in _ABSENT_INPUT) and _NEGATED.search(c):
        return "REVIEW", "a configured path is ABSENT — silence reads as 'nothing to report'"
    if any(k in c for k in _ABSENT_INPUT):
        return "EMPTY", "a positive existence test — the guard found its input and moved on"
    if any(k in c for k in _EMPTY_VALUE):
        return "EMPTY", "nothing to judge — silence is proportionate"
    return "UNCLASSIFIED", "condition not recognised — read it before trusting the silence"


def scan_file(path: str) -> list[dict]:
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except SyntaxError:
        return []
    out: list[dict] = []

    class V(ast.NodeVisitor):
        def __init__(self):
            self.stack: list[tuple[str, bool]] = []   # (condition source, inside except handler)
            self.fn: list[str] = []

        def _walk_body(self, body, cond, in_handler):
            self.stack.append((cond, in_handler))
            for st in body:
                self.visit(st)
            self.stack.pop()

        def visit_If(self, node):
            try:
                cond = ast.unparse(node.test)
            except Exception:
                cond = "<unparseable>"
            self._walk_body(node.body, cond, False)
            if node.orelse:
                self._walk_body(node.orelse, f"not ({cond})", False)

        def visit_ExceptHandler(self, node):
            try:
                cond = "except " + (ast.unparse(node.type) if node.type else "")
            except Exception:
                cond = "except"
            self._walk_body(node.body, cond.strip(), True)

        def visit_FunctionDef(self, node):
            self.fn.append(node.name)
            self.generic_visit(node)
            self.fn.pop()

        def generic_visit(self, node):
            in_main = bool(self.fn) and self.fn[-1] == "main"
            if self.stack and _is_success_exit(node, in_main):
                cond, in_handler = self.stack[-1]
                # anything printed earlier in the same guarded block counts as "not silent"
                out.append(dict(path=path, line=node.lineno, cond=cond, in_handler=in_handler,
                                node=node))
            super().generic_visit(node)

    v = V()
    # a second pass marks blocks that DO emit, so we can drop those exits
    for fn in [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        pass
    v.visit(tree)

    # drop exits whose enclosing if/except block emits something
    emitting_lines: set[int] = set()
    speakers = _speaking_functions(tree)
    for n in ast.walk(tree):
        if isinstance(n, (ast.If, ast.ExceptHandler)):
            # Per BRANCH, not per statement. Folding `body + orelse` into one list meant a speaking
            # if-branch marked the whole construct as emitting and MASKED a silent else-branch:
            #
            #     if os.path.isdir(root):
            #         print("found", root)
            #     else:
            #         return 0            <- reported nothing, and this is the exact shape the
            #                                tool exists to find (the state_save_reminder defect
            #                                written as if/else instead of an early return)
            #
            # Reproduced on the sealed .419 tree: the fixture above yielded 0 rows.
            branches = [list(n.body)]
            orelse = list(getattr(n, "orelse", []) or [])
            if orelse:
                branches.append(orelse)
            for branch in branches:
                if not any(_emits(st, speakers) for st in branch):
                    continue
                for st in branch:
                    for sub in ast.walk(st):
                        if hasattr(sub, "lineno"):
                            emitting_lines.add(sub.lineno)

    rows = []
    for r in out:
        if r["line"] in emitting_lines:
            continue
        cls, why = _classify(r["cond"], r["in_handler"])
        rows.append(dict(path=r["path"], line=r["line"], cond=r["cond"], cls=cls, why=why))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    ap.add_argument("--scope", nargs="*", default=["hooks"])
    ap.add_argument("--class", dest="cls",
                    choices=["REVIEW", "UNCLASSIFIED", "FAIL_OPEN", "DISPATCH", "EMPTY"],
                    default=None)
    ap.add_argument("--ceiling", type=int, default=None,
                    help="ratchet mode: exit 1 when the REVIEW count exceeds this")
    a = ap.parse_args(argv)

    rows: list[dict] = []
    files = 0
    for scope in a.scope:
        base = os.path.join(a.root, scope)
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d != "__pycache__"]
            for f in sorted(fn):
                if f.endswith(".py"):
                    files += 1
                    rows.extend(scan_file(os.path.join(dp, f)))

    order = ("REVIEW", "UNCLASSIFIED", "FAIL_OPEN", "DISPATCH", "EMPTY")
    counts = {c: sum(1 for r in rows if r["cls"] == c) for c in order}
    # One emission site, not five. `tools/_console.py::emit` centralises the seam but repo_health
    # counts emission SITES, not the spelling — five report lines would have pushed print_calls
    # 1320 -> 1325, past the waiver's signed observed of 1323, and turned --strict red on a cut.
    # Building the report as lines and writing once is the paydown pattern the ceiling asks for,
    # and it is better code for a report tool besides.
    shown = [r for r in rows if a.cls is None or r["cls"] == a.cls]
    lines: list[str] = []
    for r in sorted(shown, key=lambda r: (order.index(r["cls"]), r["path"], r["line"])):
        rel = os.path.relpath(r["path"], a.root)
        lines.append(f"{r['cls']:<9} {rel}:{r['line']}  if {r['cond'][:70]}")
        lines.append(f"          -> {r['why']}")
    total = len(rows)
    lines.append(f"\n{total} silent success exit(s) across {files} file(s) in "
                 f"{'/'.join(a.scope)}/: " + ", ".join(f"{counts[c]} {c}" for c in order))
    lines.append("REVIEW is not a defect list — it is the set where an operator cannot tell "
                 "'nothing to report' from 'not looking'.")
    over = a.ceiling is not None and counts["REVIEW"] > a.ceiling
    if over:
        lines.append(f"FAIL: REVIEW count {counts['REVIEW']} exceeds ceiling {a.ceiling}")
    emit("\n".join(lines))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
