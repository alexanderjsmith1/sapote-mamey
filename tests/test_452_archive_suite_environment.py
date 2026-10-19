"""Synthetic optional-tool provenance checks; no binary or test subprocess runs."""
import importlib.util
import inspect
import json
import os
from pathlib import Path

import pytest


TOOLS = Path(__file__).resolve().parents[1] / "tools"


def load(name):
    path = TOOLS / (name + ".py")
    assert path.is_file(), "required optional-tool provenance implementation is missing"
    spec = importlib.util.spec_from_file_location("c2_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_watched_log_header_precedes_child_output(tmp_path, monkeypatch):
    support = load("_release_validation")
    assert "log_header" in inspect.signature(support.run_watched).parameters, \
        "watched suite logs cannot record optional-binary provenance"
    helper = load("_archive_suite_environment")
    header = helper.suite_tool_header({"PATH": str(tmp_path / "absent")}, tmp_path)
    assert header["missing_optional_tools"] == list(helper.OPTIONAL_TOOLS)
    class Process:
        pid = 987654321
        def poll(self): return 0
        def wait(self): return 0
    def start(*args, **kwargs):
        output = kwargs["stdout"]
        assert (tmp_path / "pytest.log").read_text().startswith("# sapote-suite-environment ")
        output.write("synthetic child output\n")
        output.flush()
        return Process()
    class Tree:
        known = {}; cleanup_events = []
        def __init__(self, pid): pass
        def refresh(self): return {}
        def stop(self, process): return None
    monkeypatch.setattr(support.subprocess, "Popen", start)
    monkeypatch.setattr(support, "_OwnedProcessTree", Tree)
    result = support.run_watched(["NEVER_EXECUTED"], cwd=tmp_path, log=tmp_path / "pytest.log",
        env={"PATH": ""}, min_disk=0, sampler=lambda _: 0, log_header=header)
    lines = (tmp_path / "pytest.log").read_text().splitlines()
    assert json.loads(lines[0].removeprefix("# sapote-suite-environment ")) == header
    assert lines[1] == "synthetic child output"
    assert result["exit_code"] == 0
    assert result["log_sha256"] == support.sha256_file(tmp_path / "pytest.log")


def test_declared_directory_is_explicit_preserved_and_idempotent(tmp_path):
    helper = load("_archive_suite_environment")
    tools = tmp_path / "declared tools"; tools.mkdir()
    original = {"PATH": "/other", "SAPOTE_SUITE_TOOL_DIR": str(tools)}
    changed = helper.declared_environment(original)
    assert changed["PATH"] == str(tools) + os.pathsep + "/other"
    assert original["PATH"] == "/other"
    assert helper.declared_environment(changed) == changed
    assert helper.declared_environment({"PATH": "/other"}) == {"PATH": "/other"}


@pytest.mark.parametrize("directory", ["relative", "", "/definitely-absent-c2-tools"])
def test_invalid_declared_tool_directory_refuses(directory):
    helper = load("_archive_suite_environment")
    with pytest.raises(ValueError, match="existing absolute directory"):
        helper.declared_environment({"PATH": "", "SAPOTE_SUITE_TOOL_DIR": directory})


def test_resolution_uses_child_cwd_and_never_executes_binary(tmp_path):
    helper = load("_archive_suite_environment")
    tools = tmp_path / "bin"; tools.mkdir()
    node = tools / "node"; node.write_text("not executable code; must never be run\n"); node.chmod(0o700)
    header = helper.suite_tool_header({"PATH": "bin"}, tmp_path)
    row = next(r for r in header["tools"] if r["name"] == "node")
    assert row["status"] == "PRESENT" and row["path"] == str(node)
    assert row["sha256"] == __import__("hashlib").sha256(node.read_bytes()).hexdigest()
    assert "node" not in header["missing_optional_tools"]
    assert "pdfinfo" in header["missing_optional_tools"]


def test_partition_environment_admits_explicit_tools_without_mutating_caller(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(TOOLS))
    runner = load("_release_partition_runner")
    directory = tmp_path / "explicit tools"; directory.mkdir()
    supplied = {"PATH": "/other", "SAPOTE_SUITE_TOOL_DIR": str(directory),
                "PYTEST_CURRENT_TEST": "parent context"}
    admitted = runner.test_environment(tmp_path, supplied)
    assert admitted["PATH"].split(os.pathsep)[0] == str(directory)
    assert "PYTEST_CURRENT_TEST" not in admitted
    assert supplied["PATH"] == "/other" and supplied["PYTEST_CURRENT_TEST"] == "parent context"
