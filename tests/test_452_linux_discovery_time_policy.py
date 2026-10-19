"""Discovery resource-policy admission only; own controls perform no traversal or I/O."""
from dataclasses import FrozenInstanceError, asdict

import pytest

from mamey import workspace_source_discovery as discovery


@pytest.fixture
def intercepted(monkeypatch):
    calls = {"scan": [], "write": [], "emit": []}
    def scan(**kwargs):
        calls["scan"].append(kwargs)
        return {"status": "PASS_COMPLETE"}
    def write(*args):
        calls["write"].append(args)
        return {"status": "PASS_COMPLETE"}
    def forbidden(*args, **kwargs):
        raise AssertionError("policy control traversed or read a resource")
    monkeypatch.setattr(discovery, "build_source_catalog", scan)
    monkeypatch.setattr(discovery, "write_catalog", write)
    monkeypatch.setattr(discovery, "emit", lambda *args, **kwargs: calls["emit"].append(args))
    monkeypatch.setattr(discovery.os, "walk", forbidden)
    monkeypatch.setattr(discovery, "load_collection_registry", forbidden)
    return calls


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf"), float("1e309")],
                         ids=["nan", "positive-inf", "negative-inf", "overflow-inf"])
def test_nonfinite_float_limits_refuse_at_construction(intercepted, value):
    with pytest.raises(ValueError, match="SCAN_TIME_LIMIT_MUST_BE_FINITE"):
        discovery.ScanLimits(max_seconds=value)
    assert not intercepted["scan"] and not intercepted["write"]


def arguments(seconds):
    return ["scan", "inert-root", "--root-id", "INERT", "--collection-registry", "inert-registry",
            "--expected-collection-registry-sha256", "0" * 64, "--out-json", "inert.json",
            "--out-tsv", "inert.tsv", "--max-seconds", seconds]


@pytest.mark.parametrize("value", ["nan", "inf", "1e309"])
def test_cli_nonfinite_float_refuses_before_scan_or_write(intercepted, value):
    with pytest.raises(ValueError, match="SCAN_TIME_LIMIT_MUST_BE_FINITE"):
        discovery.main(arguments(value))
    assert not intercepted["scan"] and not intercepted["write"] and not intercepted["emit"]


@pytest.mark.parametrize("value", [1, 0.25, 60.0, 0.0, -1.0])
def test_existing_finite_values_and_schema_are_preserved(intercepted, value):
    limits = discovery.ScanLimits(max_seconds=value)
    assert asdict(limits) == {"max_depth": 6, "max_files": 100000,
                             "max_apparent_bytes": 20000000000, "max_seconds": value}
    assert not intercepted["scan"] and not intercepted["write"]


def test_finite_cli_policy_reaches_only_intercepted_metadata_calls(intercepted):
    assert discovery.main(arguments("0.25")) == 0
    assert len(intercepted["scan"]) == len(intercepted["write"]) == len(intercepted["emit"]) == 1
    limits = intercepted["scan"][0]["limits"]
    assert limits.max_seconds == 0.25 and limits.max_depth == 6 and limits.max_files == 100000


def test_default_limits_remain_finite_and_unchanged(intercepted):
    assert asdict(discovery.ScanLimits()) == {"max_depth": 6, "max_files": 100000,
        "max_apparent_bytes": 20000000000, "max_seconds": 60.0}


def test_limits_remain_frozen(intercepted):
    limits = discovery.ScanLimits()
    with pytest.raises(FrozenInstanceError):
        limits.max_seconds = 12.0
