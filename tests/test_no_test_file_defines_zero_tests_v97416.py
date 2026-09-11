"""v9.7.416 (BC2): a file named test_*.py that defines no test is invisible, not green.

A test file whose test functions are removed does not fail, does not error, and does not
report a skip — pytest simply collects nothing from it and the suite total drops silently.
The file keeps its name and its docstring, so it still reads as covered.

This is not hypothetical. Between sealed v9.7.413 and sealed v9.7.415,
`tests/test_manifest_a1_a2_a3.py` lost all four of its tests while its module docstring was
rewritten to describe the synthetic-fixture treatment its siblings received. The four
assertions (manifest triage scores, the split_pathway_candidates / RG-GMCI HIGH binding, the
per-BGC bldA tier, and the compound-class annotation field) existed nowhere else in the cut.
Nothing in the suite could report their absence, because "collected zero" is not a result.

The guard is structural rather than textual: it parses each test module and asks whether any
test function or test method is defined at all. Files that are gated on an optional dependency
(`pytest.importorskip`, `pytest.skip(allow_module_level=True)`) still DEFINE their tests, so
they pass this guard — only genuine emptiness is caught.

Claim-safety: test-suite structure only. No scan, scorer, gate, parser or emitted scientific
value is read for meaning or modified.
"""
from __future__ import annotations

import ast
import tomllib
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent

# Files that carry a test_ name but are deliberately standalone scripts with their own
# main() and are run directly, not collected. Each entry needs a reason; the guard fails on
# any NEW empty file so that emptying one is always a deliberate, reviewed act.
# Keyed on the path RELATIVE TO tests/, not the bare filename: with a recursive scan a basename
# would exempt a same-named file in any subdirectory as well.
SCRIPT_SHAPED_EXEMPTIONS = {
    # Runs as `python tests/test_409_post_seal_checksums.py <bundle_root>`; its own docstring
    # states it "needs neither the 104 MB RB68 package nor pytest".
    "tests/test_409_post_seal_checksums.py",
    "tools/cohort_tailoring/test_integration.py",  # Explicit configuration-driven standalone integration script.
    "tools/ladder_test.py",  # Standalone density-rung tree CLI; requires folder, panel and pattern.
}


def _defines_a_test(path: Path) -> bool:
    """True iff the module defines any test function, or a class holding a test method."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        # A file pytest itself cannot parse is a separate, louder failure; not this guard's job.
        return True
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test"):
            return True
        if isinstance(node, ast.ClassDef) and any(
            isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
            and member.name.startswith("test")
            for member in node.body
        ):
            return True
    return False


def _collected_modules() -> list[Path]:
    """Discover all configured test directories and filename patterns."""
    options = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["pytest"]["ini_options"]
    return sorted({p for scope in options["testpaths"]
                   for pattern in options.get("python_files", ["test_*.py", "*_test.py"])
                   for p in (ROOT / scope).rglob(pattern) if "__pycache__" not in p.parts})


def _rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def test_every_test_module_defines_at_least_one_test():
    empty = sorted(
        _rel(p) for p in _collected_modules()
        if _rel(p) not in SCRIPT_SHAPED_EXEMPTIONS and not _defines_a_test(p)
    )
    assert not empty, (
        "these test modules define no test at all, so they contribute zero coverage while "
        "still reading as present: " + ", ".join(empty) + ". Restore the tests, delete the "
        "file, or add it to SCRIPT_SHAPED_EXEMPTIONS with a reason."
    )


def test_guard_detects_an_empty_module(tmp_path):
    """Negative control: the detector must actually fire on an empty module."""
    empty = tmp_path / "test_empty_probe.py"
    empty.write_text('"""Looks like a test file. Defines nothing."""\nimport os\n', encoding="utf-8")
    assert not _defines_a_test(empty)

    populated = tmp_path / "test_populated_probe.py"
    populated.write_text("def test_something():\n    assert True\n", encoding="utf-8")
    assert _defines_a_test(populated)

    classy = tmp_path / "test_class_probe.py"
    classy.write_text(
        "import unittest\n\n\nclass Probe(unittest.TestCase):\n"
        "    def test_method(self):\n        self.assertTrue(True)\n", encoding="utf-8")
    assert _defines_a_test(classy)


def test_exemptions_all_exist():
    """An exemption for a file that no longer exists is stale and must not linger."""
    missing = sorted(n for n in SCRIPT_SHAPED_EXEMPTIONS if not (ROOT / n).exists())
    assert not missing, f"stale exemption(s) for non-existent file(s): {missing}"


def test_the_scan_actually_reaches_subdirectories():
    """Coverage self-check, in the style of test_tools_import_safe's own scan-coverage test.

    Without this, the scope could silently narrow back to the top level and every assertion above
    would keep passing on a smaller set.
    """
    scanned = {_rel(p) for p in _collected_modules()}
    assert any("/" in rel for rel in scanned), (
        "the scan found no test module below tests/ — either the tree changed or the glob stopped "
        "recursing; a guard that quietly narrows its own scope is the defect it exists to catch")
    assert "tests/public/test_public_release_v9_7_381.py" in scanned
