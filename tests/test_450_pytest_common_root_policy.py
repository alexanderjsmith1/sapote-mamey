"""Exercise actual common-root policy in a final tools-only partition."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from tests.test_release_partition_runner import runner_module, environment, make_runner, digest


def configured_suite(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "tests").mkdir()
    (source / "tools").mkdir()
    shutil.copy2(Path(__file__).resolve().parents[1] / "conftest.py", source / "conftest.py")
    (source / "pytest.ini").write_text(
        "[pytest]\ntestpaths = tests tools\nmarkers =\n    slow: slow\n    network: network\n")
    (source / "tests/test_first.py").write_text("def test_first(): pass\n")
    (source / "tools/test_last.py").write_text('''
import pytest
@pytest.mark.slow
def test_slow(request): assert request.config.getoption("--run-slow")
@pytest.mark.network
def test_network(request): assert request.config.getoption("--run-network")
def test_plain(): pass
''')
    return source


@pytest.mark.parametrize("selection", [["tools/test_last.py"], ["tests", "tools"]])
def test_root_policy_keeps_default_skips_and_full_opt_in(tmp_path, selection):
    source = configured_suite(tmp_path)
    for full in [False, True]:
        flags = ["--run-slow", "--run-network"] if full else []
        command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                   "--basetemp", str(tmp_path / ("full-scratch" if full else "default-scratch")),
                   *flags, *selection]
        result = subprocess.run(command, cwd=source, env=environment(),
                                capture_output=True, text=True, timeout=60)
        text = result.stdout + result.stderr
        assert result.returncode == 0, text
        expected_passes = (3 if full else 1) + (len(selection) == 2)
        assert f"{expected_passes} passed" in text
        assert ("2 skipped" in text) is (not full)


def test_partition_runner_covers_tools_only_final_group(runner_module, tmp_path):
    source = configured_suite(tmp_path)
    output = tmp_path / "evidence"
    report = make_runner(runner_module, source, output, environment()).run()
    assert report["status"] == "PASS"
    assert len(report["partitions"]) == 2
    assert report["partitions"][-1]["plan"]["files"] == ["tools/test_last.py"]
    assert report["totals"]["main_counts"] == {"passed": 4}
    assert report["totals"]["main_nodes"] == 4
    receipt = output / "partition.json"
    verified = runner_module.verify_partition_receipt(
        receipt, source, digest(receipt), report["binding"]["environment_identity_sha256"])
    assert verified == report["totals"]
    observed = []
    for stage in report["partitions"]:
        attempt = json.loads((output / stage["active"]["path"]).read_text())
        capture = json.loads((output / attempt["capture"]["path"]).read_text())
        observed.extend(capture["collected"])
        assert attempt["command"].count("--run-slow") == 1
        assert attempt["command"].count("--run-network") == 1
    assert len(observed) == len(set(observed)) == 4
