"""Synthetic adversarial coverage checks before implementing evidence reuse."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def contract(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))
    return importlib.import_module("_release_partitions")


def capture():
    nodes = ["tests/test_one.py::test_parameter[a::b]", "tests/test_one.py::TestClass::test_method",
             "tests/test_two.py::test_skip"]
    phases = []
    outcomes = []
    for index, node in enumerate(nodes):
        skipped = index == 2
        for when in (["setup", "teardown"] if skipped else ["setup", "call", "teardown"]):
            phases.append({"nodeid": node, "when": when,
                           "outcome": "skipped" if skipped and when == "setup" else "passed"})
        outcomes.append({"nodeid": node, "outcome": "skipped" if skipped else "passed"})
    return {"schema": "sapote-mamey.pytest-execution.v1", "exit_code": 0,
            "started_utc": "2026-10-10T00:00:00Z", "completed_utc": "2026-10-10T00:01:00Z",
            "collection_finished": True, "collected": nodes, "testscollected": len(nodes),
            "deselected": [], "collection_errors": [], "duplicate_collected": [],
            "unexpected_report_nodes": [], "collection_skips": [{"nodeid": "tests/test_optional.py", "reason": "optional unavailable"}],
            "outcomes": outcomes, "counts": {"passed": 2, "skipped": 1}, "phase_reports": phases,
            "subtests": [{"nodeid": nodes[0], "when": "call", "outcome": "passed"}],
            "subtest_counts": {"passed": 1}}


NOW = datetime(2026, 10, 10, 0, 2, tzinfo=timezone.utc)


def test_actual_identities_phases_and_subtests_are_reconciled(contract):
    data = capture()
    assert contract.validate_capture(data, data["collected"], now=NOW) == {
        "main_counts": {"passed": 2, "skipped": 1}, "main_nodes": 3,
        "collection_skips": 1, "subtest_counts": {"passed": 1}}


def test_file_plan_is_deterministic_lossless_and_keeps_parameter_identity(contract):
    nodes = capture()["collected"]
    groups = contract.partition_plan(nodes, 1)
    assert groups == contract.partition_plan(nodes, 1)
    assert [g["files"] for g in groups] == [["tests/test_one.py"], ["tests/test_two.py"]]
    assert [n for g in groups for n in g["expected_nodes"]] == nodes


@pytest.mark.parametrize("nodes", [[], ["same.py::test", "same.py::test"],
    ["../outside.py::test"], ["/absolute.py::test"], ["test.txt::test"], [None], ["test.py::bad\nnode"]])
def test_invalid_or_ambiguous_plan_refuses(contract, nodes):
    with pytest.raises(ValueError):
        contract.partition_plan(nodes, 1)


@pytest.mark.parametrize("size", [0, -1, True, 1.5, "20"])
def test_invalid_group_size_refuses(contract, size):
    with pytest.raises(ValueError):
        contract.partition_plan(capture()["collected"], size)


@pytest.mark.parametrize("mutation", [
    lambda d: d.update(exit_code=1),
    lambda d: d.update(collection_finished=False),
    lambda d: d["deselected"].append("tests/test_omitted.py::test"),
    lambda d: d["collection_errors"].append({"reason": "import failed"}),
    lambda d: d["collected"].append(d["collected"][0]),
    lambda d: d["collected"].pop(),
    lambda d: d["outcomes"].pop(),
    lambda d: d["outcomes"].append(dict(d["outcomes"][0])),
    lambda d: d["outcomes"].append({"nodeid": "extra.py::test", "outcome": "passed"}),
    lambda d: d["counts"].update(passed=200),
    lambda d: d["phase_reports"].pop(),
    lambda d: d["phase_reports"].append(dict(d["phase_reports"][0])),
    lambda d: d["phase_reports"][0].update(outcome="failed"),
    lambda d: d["phase_reports"][0].update(nodeid="extra.py::test"),
    lambda d: d["subtests"][0].update(outcome="failed"),
    lambda d: d["subtests"][0].update(nodeid="extra.py::test"),
    lambda d: d["subtest_counts"].update(passed=100),
    lambda d: d["collection_skips"][0].update(reason=""),
    lambda d: d["collection_skips"].append(dict(d["collection_skips"][0])),
    lambda d: d.update(testscollected=999),
])
def test_red_incomplete_or_tampered_evidence_refuses(contract, mutation):
    data = capture()
    expected = list(data["collected"])
    mutation(data)
    with pytest.raises(ValueError):
        contract.validate_capture(data, expected, now=NOW)


def test_selected_node_order_must_match_collection(contract):
    data = capture()
    with pytest.raises(ValueError, match="identities/order"):
        contract.validate_capture(data, list(reversed(data["collected"])), now=NOW)


def test_collection_only_is_unexecuted_and_cannot_be_admitted_as_a_green_partition(contract):
    data = capture()
    data.update(phase_reports=[], subtests=[], subtest_counts={}, counts={"incomplete": 3})
    for row in data["outcomes"]:
        row["outcome"] = "incomplete"
    assert contract.validate_capture(data, collect_only=True, now=NOW)["main_nodes"] == 3
    with pytest.raises(ValueError, match="incomplete main nodes"):
        contract.validate_capture(data, now=NOW)


@pytest.mark.parametrize(("field", "value"), [
    ("started_utc", "2026-10-10T00:00:00"),
    ("completed_utc", "invalidZ"),
    ("completed_utc", "2026-10-09T00:00:00Z"),
    ("completed_utc", "2026-10-10T01:00:00Z"),
])
def test_invalid_or_future_times_refuse(contract, field, value):
    data = capture()
    data[field] = value
    with pytest.raises(ValueError):
        contract.validate_capture(data, now=NOW)


def test_expired_evidence_refuses(contract):
    with pytest.raises(ValueError, match="expired"):
        contract.validate_capture(capture(), now=NOW + timedelta(days=2))


def test_source_environment_machinery_and_group_size_change_binding(contract):
    inputs = dict(source_sha256="a" * 64, environment_sha256="b" * 64,
                  machinery_sha256="c" * 64, files_per_partition=20)
    binding = contract.input_binding(**inputs)
    assert binding["profile"] == "configured-full-suite-partitioned"
    assert binding["flags"][-2:] == ["--run-slow", "--run-network"]
    for key in inputs:
        changed = deepcopy(inputs)
        changed[key] = 19 if key == "files_per_partition" else "d" * 64
        assert contract.input_binding(**changed)["sha256"] != binding["sha256"]
