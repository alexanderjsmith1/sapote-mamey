"""v9.7.404 — guard: no subprocess in tests/ may spawn a child with a from-scratch env that
lacks PYTHONDONTWRITEBYTECODE.

WHY. `python -B` is a process flag; it never reaches a child. Tests that build a hermetic env
from a dict literal (correctly — they prove hooks behave with no ambient environment) spawned
children that wrote .pyc/__pycache__ into the tree under test: +61 files per full-suite run on
the .403 candidate, 1,325 shipped in the .402 candidate. conftest.hermetic_env() adds the one
flag and nothing else. This test makes the invariant impossible to lose quietly — same shape as
tools/repo_health.py's ratchets and test_scoring_net's handler-persistence lock.

RULE. For every subprocess.run/Popen/call/check_output/check_call with an `env=` argument:
  - a dict literal that spreads `**os.environ` (or any `**` unpack) INHERITS -> OK
    (conftest exports the flag into os.environ at import);
  - a dict literal with the key "PYTHONDONTWRITEBYTECODE" -> OK;
  - a call to hermetic_env(...) -> OK;
  - a Name is resolved to its nearest prior assignment in the same function and judged by the
    same rules; a comprehension / unresolvable value is treated as inheriting (not a literal);
  - anything else -> FAIL, naming file:line and the helper to use.

CLASS A (explicit compilation) — a SECOND leak the env rule cannot see. `python -m py_compile`
and `compileall` WRITE __pycache__/*.pyc by design and ignore -B / PYTHONDONTWRITEBYTECODE
(those govern import caching only). Two syntax-check tests spawned py_compile per file and wrote
53 of the 61 leaked .pyc per full run. Syntax checks use in-process compile(); so: no
"py_compile"/"compileall" as a -m target in any subprocess call, and no py_compile.compile() /
compileall.* call, anywhere in tests/ (this file excepted).
"""
from __future__ import annotations
import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent
FLAG = "PYTHONDONTWRITEBYTECODE"
SPAWNERS = {"run", "Popen", "call", "check_output", "check_call"}
COMPILERS = {"py_compile", "compileall"}


def _is_subprocess_call(node: ast.Call) -> bool:
    f = node.func
    return (isinstance(f, ast.Attribute) and f.attr in SPAWNERS
            and isinstance(f.value, ast.Name) and f.value.id == "subprocess")


def _is_compiler_call(node: ast.Call) -> bool:
    f = node.func
    return (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in COMPILERS)


def _spawns_compiler(node: ast.Call) -> bool:
    """True if a subprocess call's argv contains `-m py_compile` / `-m compileall`."""
    for arg in node.args:
        for elt in getattr(arg, "elts", []) or []:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str) and elt.value in COMPILERS:
                return True
    return False


def _dict_ok(d: ast.Dict) -> bool:
    for k in d.keys:
        if k is None:                       # **spread -> inherits os.environ (or a copy of it)
            return True
        if isinstance(k, ast.Constant) and k.value == FLAG:
            return True
    return False


def _judge(value: ast.AST, scope: list[ast.stmt]) -> bool | None:
    """True=ok, False=violation, None=not a literal (treated as inheriting)."""
    if isinstance(value, ast.Dict):
        return _dict_ok(value)
    if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id == "hermetic_env":
        return True
    if isinstance(value, ast.Name):
        # nearest prior simple assignment to this name in the enclosing function body
        for st in reversed(scope):
            if isinstance(st, ast.Assign) and any(isinstance(t, ast.Name) and t.id == value.id for t in st.targets):
                return _judge(st.value, scope[: scope.index(st)])
        return None
    return None


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: list[str] = []
    scopes: list[list[ast.stmt]] = [
        [st for st in tree.body if not isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    ] + [list(fn.body) for fn in ast.walk(tree) if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))]
    for body in scopes:
        # lookup scope for _judge: statements plus one level of nested bodies (with/if/for/try)
        flat: list[ast.stmt] = []
        for st in body:
            flat.append(st)
            for attr in ("body", "orelse", "finalbody"):
                for inner in getattr(st, attr, None) or []:
                    if isinstance(inner, ast.stmt) and not isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        flat.append(inner)
        for st in body:                                  # walk each top-level statement ONCE
            for node in ast.walk(st):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not st:
                    continue                             # nested defs get their own scope entry
                if isinstance(node, ast.Call) and _is_compiler_call(node):
                    out.append(f"{path.name}:{node.lineno}")
                if isinstance(node, ast.Call) and _is_subprocess_call(node):
                    if _spawns_compiler(node):
                        out.append(f"{path.name}:{node.lineno}")
                    for kw in node.keywords:
                        if kw.arg == "env":
                            upto = [x for x in flat if x.lineno <= node.lineno]
                            if _judge(kw.value, upto) is False:
                                out.append(f"{path.name}:{node.lineno}")
    return sorted(set(out), key=lambda x: int(x.rsplit(":", 1)[1]))


def test_no_hermetic_child_without_bytecode_flag():
    bad: list[str] = []
    for p in sorted(TESTS.rglob("test_*.py")):
        if p.name == Path(__file__).name:
            continue
        bad.extend(_violations(p))
    assert not bad, (
        "subprocess child spawned with a from-scratch env lacking PYTHONDONTWRITEBYTECODE — it "
        "will write .pyc into the tree under test — or an explicit py_compile/compileall, which "
        "writes .pyc by design. Build the env with conftest.hermetic_env(...) (adds only the "
        "flag; hermeticity unchanged); syntax-check with in-process compile():\n  " + "\n  ".join(bad)
    )


def test_hermetic_env_adds_only_the_flag():
    from tests.conftest import hermetic_env
    e = hermetic_env(PATH="/usr/bin:/bin", HOME="/tmp")
    assert e == {"PYTHONDONTWRITEBYTECODE": "1", "PATH": "/usr/bin:/bin", "HOME": "/tmp"}
    assert hermetic_env() == {"PYTHONDONTWRITEBYTECODE": "1"}


def test_guard_catches_a_bare_literal(tmp_path):
    src = ('import subprocess\n'
           'def t():\n'
           '    subprocess.run(["true"], env={"PATH": "/bin"})\n'
           '    env = {"PATH": "/bin"}\n'
           '    subprocess.run(["true"], env=env)\n'
           '    subprocess.run(["true"], env={"PATH": "/bin", "PYTHONDONTWRITEBYTECODE": "1"})\n'
           '    import os\n'
           '    subprocess.run(["true"], env={**os.environ, "X": "1"})\n'
           '    import sys, py_compile\n'
           '    subprocess.run([sys.executable, "-m", "py_compile", "x.py"], env={**os.environ})\n'
           '    py_compile.compile("x.py")\n')
    f = tmp_path / "test_fake.py"; f.write_text(src)
    assert _violations(f) == ["test_fake.py:3", "test_fake.py:5", "test_fake.py:10", "test_fake.py:11"]
