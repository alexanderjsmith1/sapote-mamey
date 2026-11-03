"""Selected JSON read errors only; all evidence extractors are software stubs."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deep_admission_candidate", ROOT / "tools/build_deep_data.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


@pytest.mark.parametrize("kind", ["missing", "invalid_json", "invalid_utf8", "permission"])
def test_selected_unreadable_source_does_not_reach_extractor(tmp_path, monkeypatch, kind):
    source = tmp_path / "selected.json"
    if kind == "invalid_json":
        source.write_text("{broken JSON")
    elif kind == "invalid_utf8":
        source.write_bytes(b"{\xff}")
    elif kind == "permission":
        source.write_text("{}")
        def denied(*args, **kwargs):
            raise PermissionError("synthetic read denied")
        monkeypatch.setattr(tool, "_read_json", denied)
    before = source.read_bytes() if source.exists() else None
    calls = []
    monkeypatch.setattr(tool, "extract_finer", lambda *args: calls.append(args) or ([], [], [], []))
    refused = None
    try:
        tool.extract_bounded_finer("SOFTWARE", {}, str(source))
    except ValueError as error:
        refused = error
    assert refused is not None and not calls
    assert "DEEP_DATA_EVIDENCE_READ_HOLD" in str(refused) and str(source) in str(refused)
    assert refused.__cause__ is not None
    assert (source.read_bytes() if source.exists() else None) == before


@pytest.mark.parametrize("value", [{}, {"software": "retained"}, ["schema delegated to extractor"]])
def test_readable_json_passes_through_without_new_schema_policy(tmp_path, monkeypatch, value):
    source = tmp_path / "valid.json"
    source.write_text(json.dumps(value))
    marker = object()
    calls = []
    def extractor(sid, snapshot, evidence):
        calls.append((sid, snapshot, evidence))
        return marker
    monkeypatch.setattr(tool, "extract_finer", extractor)
    assert tool.extract_bounded_finer("SOFTWARE", {"software": True}, str(source)) is marker
    assert calls == [("SOFTWARE", {"software": True}, value)]


def test_no_selected_optional_path_keeps_existing_empty_argument(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(tool, "extract_finer", lambda *args: calls.append(args) or "software_result")
    assert tool.extract_bounded_finer("SOFTWARE", {}, None) == "software_result"
    assert calls == [("SOFTWARE", {}, {})]


def test_programming_error_is_not_swallowed(monkeypatch):
    failure = RuntimeError("synthetic unexpected reader failure")
    def broken(*args):
        raise failure
    monkeypatch.setattr(tool, "_read_json", broken)
    monkeypatch.setattr(tool, "extract_finer", lambda *args: pytest.fail("extractor reached"))
    with pytest.raises(RuntimeError) as caught:
        tool.extract_bounded_finer("SOFTWARE", {}, "selected.json")
    assert caught.value is failure


