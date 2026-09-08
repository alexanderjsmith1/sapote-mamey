"""v9.7.405 — gen_release_manifest.py --fixed-point.

Both lanes converged RELEASE_MANIFEST.md's test-count row by hand at .404: apply with a
measured full-suite count, discover that the apply itself flips one or more of the tests that
read RELEASE_MANIFEST.md (a stamp/version/anchor freshness check that was failing against the
STALE manifest and now passes against the freshly-applied one), so the measured count
understated the true post-apply total. `--fixed-point` automates that dance instead of
requiring a full ~5000-test re-run per correction: it re-runs only the small manifest-reading
test subset before and after each apply and adjusts the candidate count by that subset's own
pass/skip delta, converging when the delta reaches zero.

This file never touches the real bundle's own RELEASE_MANIFEST.md or tests/ tree -- every case
builds a throwaway root (mamey/__init__.py, CITATION.cff, BUILD_STAMP.txt, RELEASE_MANIFEST.md,
and its own synthetic tests/ directory) under tmp_path, exactly like
tests/test_release_manifest_count_provenance_v97404.py's `_fake_root`/`_manifest` pattern.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from tests._fixtures import stamp

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("gen_release_manifest",
                                              ROOT / "tools" / "gen_release_manifest.py")
grm = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(grm)


def _fake_root(tmp_path: Path) -> None:
    """The three identity sources `read_truth()` reads, plus an empty tests/ dir a case can
    populate with synthetic manifest-consuming test files."""
    (tmp_path / "mamey").mkdir(exist_ok=True)
    (tmp_path / "mamey" / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
    (tmp_path / "CITATION.cff").write_text("version: '8.8.8'\n", encoding="utf-8")
    (tmp_path / "BUILD_STAMP.txt").write_text(f"build={stamp()}\n", encoding="utf-8")
    (tmp_path / "tests").mkdir(exist_ok=True)


def _manifest(tmp_path: Path, engine: str = "0.0.0", row: str | None = None) -> Path:
    _fake_root(tmp_path)
    body = [
        "# Release Manifest",
        "",
        "**Cut/build date:** 2020-01-01  ",
        "**Bundle version:** `sapote-mamey-v0.0.0`  ",
        f"**Engine:** Mamey v{engine}  ",
        "**Build stamp:** OLD  ",
        "",
        "## Validation status",
        "",
        "| Gate | Status |",
        "| --- | --- |",
    ]
    if row:
        body.append(row)
    body += ["", "All four tiers share build stamp `OLD`.", ""]
    p = tmp_path / "RELEASE_MANIFEST.md"
    p.write_text("\n".join(body) + "\n", encoding="utf-8")
    return p


# --- discovery -----------------------------------------------------------------------------


def test_discover_finds_only_files_naming_the_manifest(tmp_path):
    _fake_root(tmp_path)
    consumer = tmp_path / "tests" / "test_reads_manifest.py"
    consumer.write_text("def test_x():\n    assert 'RELEASE_MANIFEST' or True\n", encoding="utf-8")
    unrelated = tmp_path / "tests" / "test_unrelated.py"
    unrelated.write_text("def test_y():\n    assert True\n", encoding="utf-8")
    found = grm.discover_manifest_reading_tests(tmp_path)
    assert found == [consumer]


def test_discover_returns_empty_list_when_nothing_references_it(tmp_path):
    _fake_root(tmp_path)
    (tmp_path / "tests" / "test_unrelated.py").write_text(
        "def test_y():\n    assert True\n", encoding="utf-8"
    )
    assert grm.discover_manifest_reading_tests(tmp_path) == []


# --- convergence -----------------------------------------------------------------------------


def test_fixed_point_converges_immediately_when_no_consumer_flips(tmp_path):
    """The common case: the manifest-reading subset's pass/skip status is unaffected by this
    apply (no drift to fix) -- converges at iteration 1 with the seed count unchanged."""
    _manifest(tmp_path, engine="9.9.9")  # already fresh -> nothing for the apply to change
    consumer = tmp_path / "tests" / "test_always_passes.py"
    consumer.write_text(
        "def test_release_manifest_is_referenced_but_irrelevant_here():\n"
        "    assert 'RELEASE_MANIFEST' or True\n",
        encoding="utf-8",
    )
    final_passed, final_skipped, iterations = grm.run_fixed_point(
        tmp_path, seed_passed=500, seed_skipped=10, provenance="operator-supplied counts, no log bound"
    )
    assert (final_passed, final_skipped, iterations) == (500, 10, 1)


def test_fixed_point_corrects_count_when_apply_flips_a_consumer_test(tmp_path):
    """The real .404 mechanism: a manifest-consumer test fails against the STALE manifest
    (pre-apply) and passes once gen_release_manifest fixes the stale Engine line (post-apply).
    That one flip must be added to the seed count, not silently dropped."""
    _manifest(tmp_path, engine="0.0.0")  # stale -- read_truth() will derive 9.9.9
    consumer = tmp_path / "tests" / "test_engine_is_fresh.py"
    consumer.write_text(
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[1]\n"
        "def test_release_manifest_engine_matches_truth():\n"
        "    text = (ROOT / 'RELEASE_MANIFEST.md').read_text(encoding='utf-8')\n"
        "    assert '**Engine:** Mamey v9.9.9' in text\n",
        encoding="utf-8",
    )
    final_passed, final_skipped, iterations = grm.run_fixed_point(
        tmp_path, seed_passed=500, seed_skipped=10, provenance="operator-supplied counts, no log bound"
    )
    # iteration 1: base run has the one consumer test FAIL (stale manifest) -> base_passed=0;
    # after the apply fixes the Engine line, that same test PASSES -> after_passed=1, delta=+1,
    # so the candidate count is corrected to 501 and a second iteration runs to confirm the
    # correction is stable (iteration 2's base and after runs both see the now-fresh manifest,
    # delta=0 -> converged). Two iterations is the correct, expected shape of one real flip.
    assert final_passed == 501
    assert final_skipped == 10
    assert iterations == 2


def test_fixed_point_refuses_when_subset_still_fails_after_apply(tmp_path):
    """A manifest-consumer test that fails NO MATTER what the apply does (a genuinely broken
    assertion, not a freshness check) must refuse -- never be absorbed into a "corrected" count."""
    _manifest(tmp_path, engine="9.9.9")
    consumer = tmp_path / "tests" / "test_always_fails.py"
    consumer.write_text(
        "def test_release_manifest_impossible_assertion():\n"
        "    assert 'RELEASE_MANIFEST' and False\n",
        encoding="utf-8",
    )
    with pytest.raises(SystemExit, match="failing AFTER apply"):
        grm.run_fixed_point(tmp_path, seed_passed=500, seed_skipped=10,
                            provenance="operator-supplied counts, no log bound")


def test_fixed_point_refuses_when_no_consumer_tests_exist(tmp_path):
    _manifest(tmp_path)
    with pytest.raises(SystemExit, match="nothing to converge against"):
        grm.run_fixed_point(tmp_path, seed_passed=500, seed_skipped=10,
                            provenance="operator-supplied counts, no log bound")


# --- CLI wiring ------------------------------------------------------------------------------


def test_cli_fixed_point_prints_converged_and_returns_zero(tmp_path, monkeypatch, capsys):
    _manifest(tmp_path, engine="9.9.9")
    (tmp_path / "tests" / "test_noop.py").write_text(
        "def test_x():\n    assert 'RELEASE_MANIFEST' or True\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    rc = grm.main(["--root", str(tmp_path), "--fixed-point",
                  "--tests-passed", "77", "--tests-skipped", "2"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "converged: 77 passed" in out


def test_cli_fixed_point_without_a_seed_count_is_refused(tmp_path, monkeypatch, capsys):
    _manifest(tmp_path)
    (tmp_path / "tests" / "test_noop.py").write_text(
        "def test_x():\n    assert 'RELEASE_MANIFEST' or True\n", encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    rc = grm.main(["--root", str(tmp_path), "--fixed-point"])
    assert rc == 2
