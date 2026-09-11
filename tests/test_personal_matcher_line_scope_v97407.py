"""v9.7.407 — PERSONAL must be matched per line, not across the whole file.

`PERSONAL`'s `[^/]+` classes match newlines, so a whole-file `.search()` can run a
single match across many lines. The observed consequence: a test that merely asserts a
home-directory prefix is ABSENT (an `assert "/Use" "rs/" not in text` line) is flagged as CONTAINING
a personal path, because the match starts at that literal and runs on until the next `/`
somewhere further down the file.

This line scope was landed in v9.7.396 on the standalone strict audit and lost when the
strict pass was consolidated into `public_release_audit`. These tests pin it in both
passes so a future move cannot silently revert it again.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))

import public_release_audit as pra


ABSENCE_PROBE = (
    'def test_no_workbench_paths(text):\n'
    '    assert "/Use' 'rs/" not in text and "Traceback" not in text\n'
    '\n'
    '\n'
    'def test_other():\n'
    '    assert render("a/b")\n'
)

# Composed by adjacent-string concatenation so this file does not itself ship a
# home-directory literal on one line -- which is exactly what the gate under test
# flags. The runtime value is identical; only the shipped source is clean. Same
# hermetic-fixture idiom the v9.7.396 codename-scrub cards used.
REAL_PATH = 'ROOT = "/Use' 'rs/someone/project/data"\n'


def test_absence_probe_does_not_match_per_line():
    """The false-positive shape: matches whole-file, must NOT match per line."""
    assert pra.PERSONAL.search(ABSENCE_PROBE), "fixture no longer reproduces the whole-file match"
    assert not any(pra.PERSONAL.search(ln) for ln in ABSENCE_PROBE.splitlines())


def test_real_single_line_path_still_matches():
    """The repair must not blind the gate to a genuine leak."""
    assert any(pra.PERSONAL.search(ln) for ln in REAL_PATH.splitlines())


def test_strict_pass_is_line_scoped(tmp_path):
    (tmp_path / "mamey").mkdir()
    (tmp_path / "mamey" / "__init__.py").write_text("__version__='0'\n")
    (tmp_path / "BUILD_STAMP.txt").write_text("version=0\n")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_absence_probe.py").write_text(ABSENCE_PROBE)
    hits = pra.strict_source_disclosure_findings(tmp_path)
    assert not [h for h in hits if "PERSONAL_PATH" in h or "personal path" in h]


def test_strict_pass_still_catches_a_real_path(tmp_path):
    (tmp_path / "mamey").mkdir()
    (tmp_path / "mamey" / "__init__.py").write_text("__version__='0'\n")
    (tmp_path / "BUILD_STAMP.txt").write_text("version=0\n")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_real.py").write_text(REAL_PATH)
    hits = pra.strict_source_disclosure_findings(tmp_path)
    assert [h for h in hits if "PERSONAL_PATH" in h or "personal path" in h]
