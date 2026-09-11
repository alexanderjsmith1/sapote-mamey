"""A gate's scope must equal the scope of the thing it guards.

Two guards landed in v9.7.416/.417 with a non-recursive `glob` over a directory that is not flat.
Both were correct about what they looked at and silently wrong about how much:

  * `test_no_test_file_defines_zero_tests_v97416.py` scanned **1238** of the **1241** test modules
    pytest collects. The three it missed are all of `tests/public/` — the public-release disclosure
    gates, 17 tests between them. The old scope covered only tests/, which pytest walks
    recursively, so emptying any of those three would have left the anti-emptying guard green.
  * `test_tools_import_safe_v97250.py` scanned **358** of the **371** modules under `tools/` and
    `deliverable_tools/`. The 13 it missed include two build scripts —
    `deliverable_tools/strain_portfolio/build_portfolio.py` and `tools/cohort_tailoring/build_atlas.py`
    — which are exactly the shape that writes at import time.

Neither miss produced a red test, because a narrowed scope reports success on the smaller set. This
file pins the scope itself, so the next narrowing fails loudly instead of passing quietly.

Claim-safety: test-suite and filesystem structure only. No scan, scorer, gate or emitted scientific
value is read for meaning.
"""
from __future__ import annotations

import importlib.util
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"_scope_{name}", TESTS_DIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _guard_scope(mod) -> set[str]:
    """What the anti-emptying guard actually scans.

    Falls back to the pre-.418 flat glob when the helper is absent, so this file fails with the
    real finding — the modules it misses — rather than with an AttributeError about a helper.
    """
    files = mod._collected_modules() if hasattr(mod, "_collected_modules") \
        else sorted(TESTS_DIR.glob("test_*.py"))
    return {p.relative_to(ROOT).as_posix() for p in files}


def _pytest_collected() -> set[str]:
    """Independently enumerate the configured pytest directories and patterns."""
    options = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    expected = set()
    for directory in options["testpaths"]:
        for pattern in options.get("python_files", ["test_*.py", "*_test.py"]):
            expected.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob(pattern)
                            if "__pycache__" not in p.parts)
    return expected


def test_the_empty_test_guard_sees_every_module_pytest_collects():
    mod = _load("test_no_test_file_defines_zero_tests_v97416")
    scanned = _guard_scope(mod)
    missed = sorted(_pytest_collected() - scanned)
    assert not missed, (
        f"the anti-emptying guard does not scan {len(missed)} module(s) pytest collects: {missed}. "
        "Emptying one of those would not be caught.")


def test_the_public_release_tests_are_inside_that_scope():
    """Named explicitly: these are the highest-consequence files the old glob missed."""
    mod = _load("test_no_test_file_defines_zero_tests_v97416")
    scanned = _guard_scope(mod)
    for name in ("tests/public/test_public_release_v9_7_381.py",
                 "tests/public/test_public_docs_and_membership_v9_7_381.py",
                 "tests/public/test_release_audit_fails_closed_v9_7_381.py"):
        assert name in scanned, f"{name} is collected by pytest but not scanned by the guard"


def test_the_import_safety_scan_reaches_every_tool_module():
    mod = _load("test_tools_import_safe_v97250")
    scanned = {p.resolve() for p in mod._tool_files()}
    expected = set()
    for d in mod.SCANNED_DIRS:
        base = ROOT / d
        if base.is_dir():
            expected |= {p.resolve() for p in base.rglob("*.py")
                         if p.name != "__init__.py" and "__pycache__" not in p.parts}
    missed = sorted(str(p.relative_to(ROOT)) for p in expected - scanned)
    assert not missed, (
        f"the import-safety scan does not reach {len(missed)} module(s): {missed}. A module it "
        "never opens cannot be found to write at import.")


@pytest.mark.parametrize("script", [
    "deliverable_tools/strain_portfolio/build_portfolio.py",
    "tools/cohort_tailoring/build_atlas.py",
])
def test_the_nested_build_scripts_are_in_scope(script):
    """Build scripts one level down are the shape most likely to write at import."""
    mod = _load("test_tools_import_safe_v97250")
    if not (ROOT / script).is_file():
        pytest.skip(f"{script} not present in this tier")
    assert (ROOT / script).resolve() in {p.resolve() for p in mod._tool_files()}
