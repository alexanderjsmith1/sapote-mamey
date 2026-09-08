"""Pytest configuration: fast-partition support.

A default `pytest` run is the <2-min "fast partition": it auto-deselects the slow figure-render
tests, which dominate wall time (matplotlib renders measured at ~5 s each on v9.7.307:
test_cohort_figures ~5.5 s, test_bee_wasp_master_figures ~5.2 s). CI's tag/dispatch job runs the
full suite with --run-slow --run-network.

Slow classification (any of):
  * an explicit @pytest.mark.slow, or
  * the test file name contains a figure/render hint (seeded from the v9.7.307 --durations run;
    extend _SLOW_FILE_HINTS as new render tests appear), or
  * the test module imports matplotlib (figure tests are the slow ones).
Over-inclusion is deliberately safe: a fast test wrongly marked slow only means it runs in the
full job instead of the fast job. Under-inclusion (a slow test sneaking into the fast partition)
is the failure we avoid.

Network classification: only an explicit @pytest.mark.network. No current test needs live network
(the online-BLASTp path is monkeypatched), so this changes nothing today — it exists so a future
genuinely-live test can be tagged and kept out of the default run.

Deselected tests are SKIPPED, not failed. Include them with --run-slow / --run-network.
"""

# --- v9.7.381 generic-source: bind the cohort pack for the FULL/internal test session ---
# The shipped mamey/exclusions._DEFAULT is empty (generic public default). Cohort-coupled tests
# need the cohort values, and several modules snapshot the exclusion set at IMPORT time, so the
# pack must be bound BEFORE mamey is imported -> do it here at conftest module load.
# v9.7.399: bind UNCONDITIONALLY (was setdefault). The suite's value assertions are pinned to
# tests/fixtures/cohort_pack, so an operator's standing MAMEY_OFFICIAL_DATA/MAMEY_DATA_ROOT
# (now a workspace default via .claude/settings.local.json) made 15 tests fail against the
# real registry (measured 2026-09-01 on sealed .398). The suite is hermetic; operator-env
# RESOLUTION semantics are production behavior, proven by tests that set/unset these vars
# explicitly via monkeypatch. Use the CLIs, not pytest, to check the real registry.
import os as _os381
from pathlib import Path as _Path381
_cohort_pack381 = _Path381(__file__).resolve().parent / "fixtures" / "cohort_pack"
_os381.environ["MAMEY_OFFICIAL_DATA"] = str(_cohort_pack381)
_os381.environ["MAMEY_DATA_ROOT"] = str(_cohort_pack381.parent)

# v9.7.404 (CLAUDE_404_test_bytecode_leak): `python -B` is a PROCESS flag and never crosses a
# subprocess boundary, so children spawned by tests wrote .pyc into whatever tree the suite ran
# in (+61 files per full run on the .403 candidate; 1,325 shipped in the .402 candidate).
# Exporting the env var here covers every child built as {**os.environ, ...}. Children built
# from scratch must use hermetic_env() below; test_hermetic_env_guard_v97404.py enforces it.
_os381.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def hermetic_env(**extra: str) -> dict[str, str]:
    """Minimal from-scratch env for a hook/CLI child, plus the one flag that keeps it from
    writing bytecode into the tree. Adds NOTHING else: hooks never read this variable, so the
    child's hermeticity (no PATH leak, no HOME leak, no operator env) is unchanged. Pass every
    other key explicitly, exactly as the raw dict literal did."""
    env = {"PYTHONDONTWRITEBYTECODE": "1"}
    env.update({k: str(v) for k, v in extra.items()})
    return env
import re

import pytest

_SLOW_FILE_HINTS = ("figure", "atlas", "cohort_fig", "render_fig", "collection_fig", "master_fig")
_matplotlib_cache: dict[str, bool] = {}


@pytest.fixture(scope="session")
def synthetic_single_contig_admitted_zip(tmp_path_factory):
    """Byte-identical synthetic archive with FASTA stored rather than bomb-like deflated.

    The tracked fixture intentionally uses a highly repetitive artificial sequence. Its
    268x DEFLATE ratio now correctly trips the production 200x decompression guard, even
    though these tests exercise unrelated package behavior. Keep the tracked source
    immutable and repackage only the FASTA entry for this pytest session; every member's
    uncompressed bytes must remain identical.
    """
    source = _Path381(__file__).resolve().parent / "fixtures" / "synthetic_single_contig_antismash.zip"
    target = tmp_path_factory.mktemp("admitted_synthetic_fixture") / source.name
    from tools.fixture_inputs import prepare_single_contig_fixture
    prepare_single_contig_fixture(source, target)
    return target


@pytest.fixture(scope="session")
def synthetic_single_contig_full_locus_zip(tmp_path_factory):
    """Explicit full-locus runtime transform for positive package-output tests."""
    source = _Path381(__file__).resolve().parent / "fixtures" / "synthetic_single_contig_antismash.zip"
    target = (
        tmp_path_factory.mktemp("full_locus_synthetic_fixture")
        / "synthetic_single_contig_full_locus_antismash.zip"
    )
    from tools.fixture_inputs import prepare_full_locus_single_contig_fixture
    prepare_full_locus_single_contig_fixture(source, target)
    return target


def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true", default=False,
                     help="include slow tests (figure/plot rendering, cohort builds)")
    parser.addoption("--run-network", action="store_true", default=False,
                     help="include tests marked @pytest.mark.network (need live network)")


def _module_imports_matplotlib(item) -> bool:
    mod = getattr(item, "module", None)
    path = getattr(mod, "__file__", None)
    if not path:
        return False
    if path not in _matplotlib_cache:
        try:
            src = open(path).read()
        except OSError:
            _matplotlib_cache[path] = False
        else:
            _matplotlib_cache[path] = bool(re.search(r"^\s*(import matplotlib|from matplotlib)", src, re.M))
    return _matplotlib_cache[path]


def pytest_collection_modifyitems(config, items):
    run_slow = config.getoption("--run-slow")
    run_network = config.getoption("--run-network")
    skip_slow = pytest.mark.skip(reason="slow test; run with --run-slow")
    skip_network = pytest.mark.skip(reason="network test; run with --run-network")

    for item in items:
        node = item.nodeid.lower()
        is_slow = (
            "slow" in item.keywords
            or any(hint in node for hint in _SLOW_FILE_HINTS)
            or _module_imports_matplotlib(item)
        )
        if is_slow:
            item.add_marker(pytest.mark.slow)
            if not run_slow:
                item.add_marker(skip_slow)
        if "network" in item.keywords and not run_network:
            item.add_marker(skip_network)
