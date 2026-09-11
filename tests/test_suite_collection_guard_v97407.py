"""v9.7.407 — a test that cannot be collected is not a test, and nothing says so.

WHY THIS EXISTS
---------------
Sealed v9.7.406 shipped THREE files under tests/ holding SEVEN working regression tests that had
never been collected in any suite, ever: `05b_test_domain_level_mobile_element_gap_v9_7_379.py`
(prefixed `05b_`), `tests_f4_cohort_prevalence.py` and `tests_bug3_card_context.py` (`tests_`
rather than `test_`). `pyproject.toml` sets only `testpaths`, with no `python_files` override, so
pytest's default `test_*.py` / `*_test.py` applies and none of the three matched.

All seven passed when force-run, and all three files were mutation-tested: breaking the behaviour
each protects makes it fail loudly. So the protection was real, written, working — and switched
off. What they guarded was not minor: the domain-level mobile-element exclusion gate (a scoring
guard mirroring `scoring.is_lead_excluded()`'s 3-flag gate), plus two silent-degradation paths
where the original bug returned an empty result and dropped report content without erroring.

The reason this survived roughly 27 bundle versions is that the failure is INVISIBLE. A
miscollected test produces no error, no warning, and no drop in the pass count — the count simply
never included it. The suite reports MORE passing tests than it has, never fewer, so there is
nothing for a human to notice.

WHAT IS CHECKED, AND WHY IT IS BEHAVIOURAL RATHER THAN NOMINAL
--------------------------------------------------------------
The obvious guard is "every .py under tests/ must be named test_*". That is the wrong rule: it
would fail four legitimate helper modules (`_fixtures.py`, `run_engine_case.py`,
`modeb_gene_first_v2_fixture.py`, `_modeb_card_fixtures.py`) which are correctly named as helpers
and hold no tests, and it would need an allowlist that itself drifts.

The rule here targets the HARM instead: a file that DEFINES tests must be COLLECTIBLE. Naming a
helper oddly is fine; shipping a test pytest will never run is not. Verified when written: all four
helpers define zero `test_*` functions, so this guard needs no allowlist at all.
"""
from __future__ import annotations

import ast
from pathlib import Path

TESTS = Path(__file__).resolve().parent


def _collectible(path: Path) -> bool:
    """pytest's default `python_files`. Kept local and explicit so that if the project ever sets a
    custom `python_files`, this guard fails and forces the rule to be restated rather than
    silently diverging from real collection."""
    return path.name.startswith("test_") or path.name.endswith("_test.py")


def _defines_tests(path: Path) -> bool:
    """True if the module defines a pytest-discoverable test at module level: a `test_*` function
    or a `Test*` class. Parsed, not grepped — a commented-out or string-embedded `def test_` is
    not a test, and would make a text search cry wolf."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            return True
    return False


def _py_files() -> list[Path]:
    return [p for p in sorted(TESTS.rglob("*.py")) if "__pycache__" not in p.parts]


def test_every_file_that_defines_tests_is_collectible():
    """The invariant the .406 defect violated."""
    orphans = [p.relative_to(TESTS).as_posix()
               for p in _py_files() if _defines_tests(p) and not _collectible(p)]
    assert not orphans, (
        "these files define tests that pytest will NEVER collect — they pass only if run by "
        "explicit path, and contribute nothing to any gate or cut:\n  "
        + "\n  ".join(orphans)
        + "\nRename each to test_<name>.py. This is exactly the v9.7.406 defect: three files, "
          "seven tests, dark since roughly v9.7.379."
    )


def test_helper_modules_still_hold_no_tests():
    """The other half of the same invariant, and the reason no allowlist is needed.

    If a non-collectible helper ever grows a test, the guard above catches it. This one states the
    complementary fact positively so the helper set stays honest: anything under tests/ that is not
    collectible is a helper, and helpers hold no tests.
    """
    helpers = [p for p in _py_files()
               if not _collectible(p) and p.name not in {"conftest.py", "__init__.py"}]
    assert helpers, "expected at least one helper module under tests/; the guard would be vacuous"
    offenders = [p.relative_to(TESTS).as_posix() for p in helpers if _defines_tests(p)]
    assert not offenders, f"helper modules must not define tests: {offenders}"


def test_no_test_leaks_an_unrestored_os_environ_mutation():
    """A test may set os.environ[K], but it must put it back. pytest restores nothing you assign.

    `test_bigscape_integration` assigned to os.environ["PATH"] and never restored it, while its own
    `finally` deleted the directory it had just put on PATH — so every later test in the process
    carried a phantom entry. `test_logging_setup._capture` set MAMEY_LOG and left it set, so
    whichever level the last test passed leaked into all subsequent ones. Both are order dependence
    through shared process state, the same family as the v9.7.402 bytecode leak.

    THIS RULE IS DELIBERATELY NARROW, and the narrowing is the point. A first draft flagged every
    subscript assignment to os.environ and produced SEVEN hits, six of them legitimate — including
    conftest.py's intentional session-wide fixture-pack export, and a test that pops the key it set,
    and one that restores with `del` in a `finally`. A guard that fails on correct code is worse
    than no guard: it trains people to edit the guard. So a site is exempt when the SAME function
    also restores that key by any of the three real forms — os.environ.pop(K), del os.environ[K],
    or reassignment from a saved value — or uses monkeypatch, which restores automatically.

    Module-level assignments (conftest.py) are out of scope by construction: this walks function
    bodies only, because a session-wide export is a deliberate act, not a leak.
    """
    offenders: list[str] = []
    for path in _py_files():
        if path.name == Path(__file__).name:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for fn in [n for n in ast.walk(tree)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            restored: set[str] = set()
            uses_monkeypatch = False
            for node in ast.walk(fn):
                if isinstance(node, ast.Name) and node.id == "monkeypatch":
                    uses_monkeypatch = True
                # os.environ.pop("K")
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "pop"
                        and isinstance(node.func.value, ast.Attribute)
                        and node.func.value.attr == "environ"
                        and node.args and isinstance(node.args[0], ast.Constant)):
                    restored.add(node.args[0].value)
                # del os.environ["K"]
                if isinstance(node, ast.Delete):
                    for tgt in node.targets:
                        if (isinstance(tgt, ast.Subscript)
                                and isinstance(tgt.value, ast.Attribute)
                                and tgt.value.attr == "environ"
                                and isinstance(tgt.slice, ast.Constant)):
                            restored.add(tgt.slice.value)
            if uses_monkeypatch:
                continue
            for node in ast.walk(fn):
                targets = node.targets if isinstance(node, ast.Assign) else (
                    [node.target] if isinstance(node, ast.AugAssign) else [])
                for tgt in targets:
                    if (isinstance(tgt, ast.Subscript)
                            and isinstance(tgt.value, ast.Attribute)
                            and tgt.value.attr == "environ"):
                        key = tgt.slice.value if isinstance(tgt.slice, ast.Constant) else None
                        if key is None or key not in restored:
                            offenders.append(
                                f"{path.relative_to(TESTS).as_posix()}:{node.lineno} key={key}")
    assert not offenders, (
        "these tests set os.environ[...] inside a function and never restore it, so the value "
        "leaks into every later test in the process:\n  "
        + "\n  ".join(offenders)
        + "\nRestore it (monkeypatch.setenv, or save/restore in a finally)."
    )
