"""The fast/slow partition must key on the test FILE PATH, not the whole node id.

The bundle-root ``conftest.py`` routes every configured test root into default and
opt-in partitions using explicit slow/network markers. Filename, import and parameter
hints must never classify a test as slow.

``item.nodeid`` is not a file path. It is ``path::test_name[param]``, so matching hints
against the whole node id also matches the test's own name and every parametrisation
value. A fast test whose parameter merely names a path such as
``tools/cohort_tailoring/build_atlas.py`` is then silently skipped in the fast partition.
Silently: a deselected test reports as skipped, never as a failure, so the coverage simply
disappears.

This guard runs a real pytest in a temporary directory against a copy of the repository's
conftest, so it measures the partitioner's behaviour rather than its source text.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFTEST = ROOT / "conftest.py"
# conftest.py loads this helper from its own directory (v9.7.443 page-text ratchet); copy it too.
RATCHET = ROOT / "tests" / "figure_page_text_ratchet.py"

# A fast test in a file whose name carries no hint, parametrised with values that do.
INNER = '''
import pytest

@pytest.mark.parametrize("target", [
    "tools/cohort_tailoring/build_atlas.py",
    "docs/some_figure_notes.md",
    "plain_value",
])
def test_fast_but_parametrised_with_hint_words(target):
    assert isinstance(target, str)
'''


def _run(tmp_path):
    shutil.copy(CONFTEST, tmp_path / "conftest.py")
    shutil.copy(RATCHET, tmp_path / "figure_page_text_ratchet.py")
    (tmp_path / "test_partition_probe_v97416.py").write_text(INNER, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
         "test_partition_probe_v97416.py"],
        cwd=tmp_path, capture_output=True, text=True, timeout=300,
    )


def test_conftest_is_available():
    assert CONFTEST.is_file(), f"missing {CONFTEST}"


def test_parametrisation_values_do_not_deselect_a_fast_test(tmp_path):
    proc = _run(tmp_path)
    out = proc.stdout + proc.stderr
    assert "3 passed" in out, (
        "the fast/slow partition skipped a fast test because a PARAMETER value contained a "
        "slow-file hint. Hints must be matched against the file path "
        "(item.nodeid.split('::', 1)[0]), not the whole node id.\n\n" + out[-1500:]
    )
    assert "skipped" not in out.split("\n")[-3:][0] or "3 passed" in out


def test_explicit_slow_marker_is_skipped_and_opt_in_runs(tmp_path):
    """The fix must not widen the fast partition to include genuinely slow files."""
    shutil.copy(CONFTEST, tmp_path / "conftest.py")
    shutil.copy(RATCHET, tmp_path / "figure_page_text_ratchet.py")
    (tmp_path / "test_figure_probe_v97416.py").write_text(
        "import pytest\npytestmark = pytest.mark.slow\ndef test_probe():\n    assert True\n", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q",
         "test_figure_probe_v97416.py"],
        cwd=tmp_path, capture_output=True, text=True, timeout=300,
    )
    out = proc.stdout + proc.stderr
    assert "1 skipped" in out, (
        "An explicit slow marker must keep the test out of the default run.\n" + out[-1500:]
    )

    opted = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "--run-slow", "test_figure_probe_v97416.py"], cwd=tmp_path, capture_output=True, text=True, timeout=300)
    assert opted.returncode == 0 and "1 passed" in opted.stdout
    (tmp_path / "test_figure_probe_v97416.py").write_text("def test_probe():\n    assert True\n")
    unmarked = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-q", "test_figure_probe_v97416.py"], cwd=tmp_path, capture_output=True, text=True, timeout=300)
    assert unmarked.returncode == 0 and "1 passed" in unmarked.stdout


@pytest.mark.parametrize("selectors", [
    ("tests",), ("tools",), ("deliverable_tools",),
    ("tests", "tools", "deliverable_tools"),
])
@pytest.mark.parametrize("flags,passed_per_root", [
    ((), 1), (("--run-slow",), 2), (("--run-network",), 2),
    (("--run-slow", "--run-network"), 4),
])
def test_shared_options_work_for_isolated_and_mixed_roots(tmp_path, selectors, flags,
                                                        passed_per_root):
    """Every configured root parses both flags and preserves independent mark gates."""
    shutil.copy(CONFTEST, tmp_path / "conftest.py")
    (tmp_path / "pytest.ini").write_text(
        "[pytest]\nmarkers =\n    slow: explicit slow test\n"
        "    network: explicit network test\n", encoding="utf-8")
    probe = (
        "import pytest\n"
        "def test_plain():\n    assert True\n"
        "@pytest.mark.slow\ndef test_slow():\n    assert True\n"
        "@pytest.mark.network\ndef test_network():\n    assert True\n"
        "@pytest.mark.slow\n@pytest.mark.network\n"
        "def test_both():\n    assert True\n"
    )
    for root_name in ("tests", "tools", "deliverable_tools"):
        directory = tmp_path / root_name
        directory.mkdir()
        (directory / ("test_" + root_name + "_probe.py")).write_text(probe, encoding="utf-8")
        if root_name == "tests":
            # Exercise coexistence with the real local conftest: duplicate registration
            # must fail rather than being hidden by testing only the root hook copy.
            shutil.copy(ROOT / "tests" / "conftest.py", directory / "conftest.py")
            shutil.copy(RATCHET, directory / "figure_page_text_ratchet.py")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
         *flags, *selectors], cwd=tmp_path, capture_output=True, text=True, timeout=60,
    )
    output = proc.stdout + proc.stderr
    assert proc.returncode == 0, output
    assert f"{len(selectors) * passed_per_root} passed" in proc.stdout, output
    skipped = len(selectors) * (4 - passed_per_root)
    if skipped:
        assert f"{skipped} skipped" in proc.stdout, output
    else:
        assert "skipped" not in proc.stdout, output
