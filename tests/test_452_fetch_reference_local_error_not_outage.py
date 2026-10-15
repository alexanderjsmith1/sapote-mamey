"""fetch_reference_cluster.ref_from_ncbi retries only network failures (.452). A local error is raised as itself, not
reported as "NCBI efetch failed" after three retries. Found on Linux without biopython (14 Oct 2026)."""
import importlib.util
import sys
import urllib.error
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def frc(monkeypatch):
    sys.path.insert(0, str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location("frc_452", ROOT / "tools" / "fetch_reference_cluster.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    import time
    monkeypatch.setattr(time, "sleep", lambda s: None)
    return m


def test_local_error_is_raised_as_itself(frc, monkeypatch):
    calls = []
    def broken(*a, **k):
        calls.append(1); raise ModuleNotFoundError("No module named 'Bio'")
    monkeypatch.setattr(frc.urllib.request, "urlopen", broken)
    with pytest.raises(ModuleNotFoundError):
        frc.ref_from_ncbi("NZ_CP123456.1", "x")
    assert calls == [1]


def test_network_error_is_retried_then_named(frc, monkeypatch):
    calls = []
    def down(*a, **k):
        calls.append(1); raise urllib.error.URLError("Temporary failure in name resolution")
    monkeypatch.setattr(frc.urllib.request, "urlopen", down)
    with pytest.raises(RuntimeError, match=r"NCBI efetch failed for NZ_CP123456\.1: URLError"):
        frc.ref_from_ncbi("NZ_CP123456.1", "x")
    assert len(calls) == 3
