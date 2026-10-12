"""Offline acceptance fixtures for actual pytest node/outcome evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
PYTHON = str(Path(sys.executable).absolute())


def execute(tmp_path, files, *arguments, destination=None):
    root = tmp_path / "source"
    root.mkdir()
    (root / "pytest.ini").write_text("[pytest]\n")
    for name, content in files.items():
        (root / name).write_text(content)
    output = destination or tmp_path / "external-evidence.json"
    env = dict(os.environ, PYTHONPATH=str(TOOLS), PYTHONDONTWRITEBYTECODE="1",
               PYTEST_DISABLE_PLUGIN_AUTOLOAD="1")
    env.pop("PYTEST_ADDOPTS", None)
    result = subprocess.run([PYTHON, "-m", "pytest", "-q", "--rootdir", str(root), "-p", "no:cacheprovider",
                             "-p", "_release_pytest_evidence", "--release-evidence", str(output),
                             *arguments], cwd=root, env=env, capture_output=True, text=True,
                            timeout=30)
    return result, json.loads(output.read_text()) if output.exists() else None


def test_exact_parameter_class_skip_and_subtest_identities(tmp_path):
    result, data = execute(tmp_path, {"test_mixed.py": '''
import pytest
@pytest.mark.parametrize("value", ["a::b", "c"])
def test_parameter(value):
    assert value
class TestGroup:
    def test_method(self):
        pass
@pytest.mark.skip(reason="intentional fixture skip")
def test_skip():
    pass
def test_subtests(subtests):
    for value in range(3):
        with subtests.test(value=value):
            assert value >= 0
''', "test_module_skip.py": 'import pytest\npytest.skip("module unavailable", allow_module_level=True)\n'})
    assert result.returncode == 0, result.stdout + result.stderr
    assert data["exit_code"] == 0
    assert data["counts"] == {"passed": 4, "skipped": 1}
    assert data["subtest_counts"] == {"passed": 3}
    assert len(data["collected"]) == 5
    assert "test_mixed.py::test_parameter[a::b]" in data["collected"]
    assert "test_mixed.py::TestGroup::test_method" in data["collected"]
    assert len(data["collection_skips"]) == 1
    assert "module unavailable" in data["collection_skips"][0]["reason"]
    assert data["duplicate_collected"] == data["unexpected_report_nodes"] == []
    assert data["deselected"] == data["collection_errors"] == []
    assert any("intentional fixture skip" in reason for row in data["outcomes"] for reason in row["reasons"])


@pytest.mark.parametrize(("body", "expected"), [
    ('def test_bad():\n    assert False, "assertion fixture"\n', "failed"),
    ('import pytest\n@pytest.fixture\ndef broken():\n    raise RuntimeError("setup fixture")\ndef test_bad(broken):\n    pass\n', "error"),
    ('import pytest\n@pytest.fixture\ndef broken():\n    yield\n    raise RuntimeError("teardown fixture")\ndef test_bad(broken):\n    pass\n', "error"),
])
def test_red_results_stay_red(tmp_path, body, expected):
    result, data = execute(tmp_path, {"test_bad.py": body})
    assert result.returncode == data["exit_code"] == 1
    assert data["counts"] == {expected: 1}
    assert data["outcomes"][0]["reasons"]


def test_collection_error_is_not_an_empty_success(tmp_path):
    result, data = execute(tmp_path, {"test_bad.py": 'raise RuntimeError("collection fixture")\n'})
    assert result.returncode != 0
    assert data["exit_code"] == result.returncode
    assert data["collection_errors"]
    assert "collection fixture" in data["collection_errors"][0]["reason"]
    assert data["outcomes"] == []


def test_collect_only_and_deselection_are_explicit(tmp_path):
    result, data = execute(tmp_path, {"test_selection.py": 'def test_yes(): pass\ndef test_no(): pass\n'},
                           "--collect-only", "-k", "yes")
    assert result.returncode == 0
    assert data["collected"] == ["test_selection.py::test_yes"]
    assert data["deselected"] == ["test_selection.py::test_no"]
    assert data["counts"] == {"incomplete": 1}


def test_failed_subtest_is_recorded_separately_and_exit_is_red(tmp_path):
    result, data = execute(tmp_path, {"test_sub.py": '''
def test_sub(subtests):
    with subtests.test(value=1):
        assert False, "subtest fixture"
    with subtests.test(value=2):
        assert True
'''})
    assert result.returncode == data["exit_code"] == 1
    assert len(data["collected"]) == len(data["outcomes"]) == 1
    assert data["subtest_counts"] == {"failed": 1, "passed": 1}
    assert any("subtest fixture" in row["reason"] for row in data["subtests"] if row["reason"])


def test_xfail_is_skipped_and_strict_xpass_is_failed(tmp_path):
    result, data = execute(tmp_path, {"test_x.py": '''
import pytest
@pytest.mark.xfail(reason="known fixture")
def test_xfail(): assert False
@pytest.mark.xfail(strict=True, reason="strict fixture")
def test_xpass(): pass
'''})
    assert result.returncode == 1
    assert data["counts"] == {"failed": 1, "skipped": 1}
    assert data["outcomes"][0]["wasxfail"] == ["known fixture"]


def test_output_inside_source_is_refused(tmp_path):
    result, data = execute(tmp_path, {"test_ok.py": 'def test_ok(): pass\n'},
                           destination=tmp_path / "source/receipt.json")
    assert result.returncode != 0
    assert data is None
    assert "outside the source tree" in result.stderr


def test_occupied_output_is_never_overwritten(tmp_path):
    output = tmp_path / "receipt.json"
    output.write_text('{"prior": true}')
    result, data = execute(tmp_path, {"test_ok.py": 'def test_ok(): pass\n'}, destination=output)
    assert result.returncode != 0
    assert data == {"prior": True}
    assert "already exists" in result.stderr
