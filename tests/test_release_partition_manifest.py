"""Source-bound baseline convergence and read-only final manifest checks."""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


@pytest.fixture
def modules(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.syspath_prepend(str(root / "tools"))
    monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    runner = importlib.import_module("_release_partition_runner")
    spec = importlib.util.spec_from_file_location("candidate_manifest", root / "tools/gen_release_manifest.py")
    manifest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manifest)
    return runner, manifest


def source_fixture(tmp_path):
    source = tmp_path / "source"; source.mkdir()
    (source / "mamey").mkdir(); (source / "tests").mkdir()
    (source / "mamey/__init__.py").write_text('__version__ = "9.9.9"\n')
    (source / "CITATION.cff").write_text("version: '8.8.8'\n")
    (source / "BUILD_STAMP.txt").write_text("build=20261009v97449a\n")
    (source / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    (source / "tests/conftest.py").write_text('''
def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true")
    parser.addoption("--run-network", action="store_true")
''')
    (source / "RELEASE_MANIFEST.md").write_text('''# Release Manifest

**Cut/build date:** 2000-01-01
**Bundle version:** `sapote-mamey-v0.0.0`
**Engine:** Mamey v0.0.0
**Build stamp:** OLD

## Validation status

| Gate | Status |
| --- | --- |
| `sync_version --check` | PASS (engine 0.0.0, bundle 0.0.0) |

All four tiers share build stamp `OLD`.
All tracked version anchors at v0.0.0 / Mamey 0.0.0.
`MAMEY_CHATGPT_EXECUTION_PROMPT.md` updated to v0.0.0.
''')
    (source / "tests/test_consumer.py").write_text('''
from pathlib import Path
def test_release_manifest_engine_is_fresh(request):
    assert request.config.getoption("--run-slow")
    assert request.config.getoption("--run-network")
    text = (Path(__file__).parents[1] / "RELEASE_MANIFEST.md").read_text()
    assert "**Engine:** Mamey v9.9.9" in text
''')
    (source / "tests/test_other.py").write_text('''
import pytest
def test_other(): pass
@pytest.mark.skip(reason="explicit fixture skip")
def test_skip(): pass
def test_subtests(subtests):
    for value in range(2):
        with subtests.test(value=value): assert value >= 0
''')
    (source / "tests/test_optional.py").write_text('import pytest\npytest.skip("optional fixture", allow_module_level=True)\n')
    return source


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_real_stale_baseline_converges_and_final_check_does_not_change_source(modules, tmp_path):
    runner, manifest = modules
    source = source_fixture(tmp_path)
    baseline = tmp_path / "baseline"
    measured = runner.PartitionRunner(source, baseline, str(Path(sys.executable).absolute()),
                                      files_per_partition=1, baseline=True).run()
    assert measured["totals"]["main_counts"] == {"failed": 1, "passed": 2, "skipped": 1}
    receipt = baseline / "partition.json"
    admission = tmp_path / "convergence admission"
    assert manifest.main(["--root", str(source), "--fixed-point", "--partition-baseline", str(receipt),
                          "--partition-receipt-sha256", digest(receipt), "--partition-admission", str(admission)]) == 0
    text = (source / "RELEASE_MANIFEST.md").read_text()
    assert "PASS (3 passed, 2 skipped; receipt-bound partitioned profile)" in text
    subsets = sorted((admission / "consumer_subsets").glob("*/subset.json"))
    assert len(subsets) == 4  # one real flip, then a stable iteration
    subset_data = [json.loads(path.read_text()) for path in subsets]
    assert all(data["status"] == "MEASURED" for data in subset_data)
    assert sum(data["watch"]["exit_code"] == 1 for data in subset_data) == 1
    assert all(data["source_before"] == data["source_after"] for data in subset_data)
    # The old baseline cannot be reused after its allowed manifest transition.
    with pytest.raises(ValueError, match="binding differs"):
        runner.verify_partition_receipt(receipt, source, digest(receipt),
            measured["binding"]["environment_identity_sha256"], baseline=True)
    final = tmp_path / "final"
    green = runner.PartitionRunner(source, final, str(Path(sys.executable).absolute()), files_per_partition=1).run()
    assert green["totals"]["main_counts"] == {"passed": 3, "skipped": 1}
    final_receipt = final / "partition.json"
    before = runner.source_digest(source)
    assert manifest.main(["--root", str(source), "--check", "--partition-receipt", str(final_receipt),
                          "--partition-receipt-sha256", digest(final_receipt),
                          "--partition-admission", str(tmp_path / "final verification admission")]) == 0
    assert runner.source_digest(source) == before


@pytest.mark.parametrize("arguments", [
    ["--apply", "--partition-receipt", "missing"],
    ["--check", "--partition-baseline", "missing"],
    ["--fixed-point", "--partition-receipt", "missing"],
    ["--check", "--partition-receipt", "missing", "--tests-passed", "999"],
    ["--fixed-point", "--partition-baseline", "missing", "--pytest-log", "missing.log"],
    ["--check", "--partition-receipt-sha256", "a" * 64],
])
def test_incompatible_or_unbound_structured_options_refuse_without_source_mutation(modules, tmp_path, arguments):
    runner, manifest = modules
    source = source_fixture(tmp_path)
    before = runner.source_digest(source)
    assert manifest.main(["--root", str(source), *arguments]) == 2
    assert runner.source_digest(source) == before
