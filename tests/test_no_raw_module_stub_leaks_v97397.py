"""Standing gate: no raw lambda-stub assignments onto module attributes in tests.

The corrupter class proven in the .398 round: ``SomeModule.attr = lambda …`` with no restore
leaks the stub to every later consumer in the pytest process. One instance
(test_audit230_fixes stubbing ``kcb_frontpage.read_frontpage``) silently broke
``test_raw_antismash_triage``'s e2e whenever an unrelated test's over-broad sys.modules purge
wasn't there to accidentally repair it. Use ``monkeypatch.setattr`` (auto-restored) or an
explicit save/``finally``-restore instead.

The scan is a source grep with a reviewed allowlist. Every allowlist entry carries its reason;
a NEW raw stub anywhere else fails this gate with the remedy in the message.
"""
from __future__ import annotations

import ast
import pathlib
import re

TESTS_DIR = pathlib.Path(__file__).resolve().parent

# module-attr lambda stub, excluding monkeypatch lines and local-variable false positives
_STUB_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\.[a-z_][A-Za-z0-9_]*\s*=\s*lambda\b")

# Reviewed-safe instances (file basename -> reason). Keep this SHORT; prefer fixing over listing.
ALLOWLIST = {
    # saves the original and restores in `finally` around every use — reviewed 2026-09-01
    "test_brief_nonblocking_v9752.py": "manual save/finally-restore discipline",
    # stubs attributes of a LOCAL types.ModuleType fake, not a shared real module
    "test_clinker_figure_cleanup_v9_7_383.py": "local ModuleType fake",
    # save/finally-restore added in the .398 round (this gate's sibling fix)
    "test_round_ledger_empty_preexisting_file_v97395.py": "manual save/finally-restore discipline",
}



def _instance_lambda_lines(text):
    """Exclude proven ordinary instance receivers, never a spelling-wide self exemption."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()  # retain the conservative lexical guard if scope is unavailable
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    unittest_modules = {a.asname or a.name for n in tree.body if isinstance(n, ast.Import)
                        for a in n.names if a.name == 'unittest'}
    testcase_names = {a.asname or a.name for n in tree.body if isinstance(n, ast.ImportFrom)
                      and n.module == 'unittest' for a in n.names if a.name == 'TestCase'}
    by_line = {}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)) or not isinstance(node.value, ast.Lambda):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        receivers = [t.value.id for t in targets if isinstance(t, ast.Attribute) and isinstance(t.value, ast.Name)]
        if not receivers:
            continue
        function = parents.get(node)
        while function is not None and not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function = parents.get(function)
        safe = False
        fixture_class = parents.get(function) if function is not None else None
        ordinary_class = (isinstance(fixture_class, ast.ClassDef)
                          and not fixture_class.decorator_list and not fixture_class.keywords
                          and all(isinstance(base, ast.Name) and base.id in testcase_names
                                  or isinstance(base, ast.Attribute) and base.attr == 'TestCase'
                                  and isinstance(base.value, ast.Name) and base.value.id in unittest_modules
                                  for base in fixture_class.bases))
        if function is not None and ordinary_class and not function.decorator_list:
            args = [*function.args.posonlyargs, *function.args.args]
            if args:
                instance = args[0].arg
                rebound = any(
                    isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)) and n.id == instance
                    or n is not function and isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == instance
                    or isinstance(n, ast.ExceptHandler) and n.name == instance
                    or isinstance(n, (ast.Import, ast.ImportFrom)) and any(
                        (a.asname or (a.name.split('.')[0] if isinstance(n, ast.Import) else a.name)) == instance
                        for a in n.names)
                    for n in ast.walk(function)
                )
                safe = not rebound and all(receiver == instance for receiver in receivers)
        by_line.setdefault(node.lineno, []).append(safe)
    # A module mutation sharing the line with a safe instance assignment must still flag.
    return {line for line, assignments in by_line.items() if all(assignments)}


def _scan():
    offenders = []
    for py in sorted(TESTS_DIR.rglob("test_*.py")):
        if py.name in ALLOWLIST or py.name == pathlib.Path(__file__).name:
            continue
        text = py.read_text(encoding="utf-8", errors="replace")
        instance_lines = _instance_lambda_lines(text)
        for i, line in enumerate(text.splitlines(), 1):
            if "monkeypatch" in line or i in instance_lines:
                continue
            if _STUB_RE.match(line):
                offenders.append(f"{py.relative_to(TESTS_DIR.parent)}:{i}: {line.strip()}")
    return offenders


def test_no_raw_module_stub_assignments_in_tests():
    offenders = _scan()
    assert not offenders, (
        "Raw lambda-stub assignment(s) onto module attributes found — these LEAK to every later "
        "test in the process (see the .398 kcb_frontpage incident). Use monkeypatch.setattr, or "
        "save the original and restore in `finally`, then either fix the line or (only with a "
        "written reason) extend the reviewed ALLOWLIST:\n  " + "\n  ".join(offenders)
    )


def test_instance_scope_does_not_hide_real_module_stubs(tmp_path, monkeypatch):
    cases = [
        ("class Fixture:\n def test_case(self):\n  self.proc = lambda pid: pid\n", False),
        ("class Fixture:\n def test_case(instance):\n  instance.proc = lambda pid: pid\n", False),
        ("import unittest\nclass Fixture(unittest.TestCase):\n def test_case(self):\n  self.proc = lambda pid: pid\n", False),
        ("class ModuleFixture(types.ModuleType):\n def test_case(self):\n  self.proc = lambda pid: pid\n", True),
        ("class UnknownFixture(UnknownBase):\n def test_case(self):\n  self.proc = lambda pid: pid\n", True),
        ("module.proc = lambda pid: pid\n", True),
        ("self.proc = lambda pid: pid\n", True),
        ("class Fixture:\n def test_case(self):\n  module.proc = lambda pid: pid\n", True),
        ("class Fixture:\n @staticmethod\n def test_case(self):\n  self.proc = lambda pid: pid\n", True),
        ("class Fixture:\n @classmethod\n def test_case(cls):\n  cls.proc = lambda pid: pid\n", True),
        ("class Fixture:\n def test_case(self):\n  self = module\n  self.proc = lambda pid: pid\n", True),
        ("class Fixture:\n def test_case(self):\n  import module as self\n  self.proc = lambda pid: pid\n", True),
        ("class Fixture:\n def test_case(self):\n  self.proc = lambda pid: pid; module.proc = lambda pid: pid\n", True),
        ("class Fixture:\n def test_case(self):\n  def nested(self):\n   self.proc = lambda pid: pid\n", True),
        ("class Fixture:\n proc = lambda pid: pid\nmodule.proc = lambda pid: pid\n", True),
        ("broken syntax !\nmodule.proc = lambda pid: pid\n", True),
    ]
    monkeypatch.setitem(globals(), 'TESTS_DIR', tmp_path)
    source = tmp_path / 'test_owned_control.py'
    for text, expected in cases:
        source.write_text(text, encoding='utf-8')
        assert bool(_scan()) is expected, (text, expected)
