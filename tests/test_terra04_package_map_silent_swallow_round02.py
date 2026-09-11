"""Round-2 regressions for package-map metadata and inspect diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

from mamey.package_map import build_package_map, _resolve_artifact


def test_package_map_marks_corrupt_manifest_not_analyzable(tmp_path):
    (tmp_path / "manifest.json").write_text("{ corrupt", encoding="utf-8")

    result = build_package_map(tmp_path)

    assert result["package_mode"] == "unreadable"
    assert result["analyzable"] is False
    assert "unreadable" in result["analyzable_note"].lower()


def test_json_key_non_object_is_reported_as_unreadable_evidence(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    state = _resolve_artifact("manifest.json#source_scans", tmp_path, "GENERIC-TEST")

    assert state["present"] is False
    assert "unreadable" in state["note"]


def test_build_map_non_object_manifest_is_typed_and_never_raises(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(["not", "an", "object"]), encoding="utf-8")

    result = build_package_map(tmp_path)

    assert result["package_mode"] == "unreadable"
    assert result["analyzable"] is False
    assert "unreadable" in result["analyzable_note"].lower()
    assert "unreadable" in result["artifacts"]["manifest.json#source_scans"]["resolution_note"]


def test_missing_manifest_stays_unknown_but_not_analyzable(tmp_path):
    result = build_package_map(tmp_path)

    assert result["package_mode"] == "unknown"
    assert result["analyzable"] is False


def test_empty_oserror_still_reports_unreadable(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    original = Path.read_text

    def unreadable(path, *args, **kwargs):
        if path == manifest:
            raise OSError()
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)
    state = _resolve_artifact("manifest.json#source_scans", tmp_path, "GENERIC-TEST")

    assert "unreadable" in state["note"]
    assert "OSError" in state["note"]


def test_malformed_unicode_reports_unreadable(tmp_path):
    (tmp_path / "manifest.json").write_bytes(b"\xff\xfe")

    state = _resolve_artifact("manifest.json#source_scans", tmp_path, "GENERIC-TEST")

    assert "unreadable" in state["note"]


def test_build_map_consumer_preserves_unreadable_resolution_note(tmp_path):
    (tmp_path / "manifest.json").write_text("{ corrupt", encoding="utf-8")

    result = build_package_map(tmp_path)

    assert "unreadable" in result["artifacts"]["manifest.json#source_scans"]["resolution_note"]


def test_manifest_existence_probe_failure_is_unreadable_not_raised(monkeypatch, tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("{}", encoding="utf-8")
    real_exists = Path.exists

    def refuse_manifest_probe(path):
        if path == manifest:
            raise PermissionError("synthetic manifest stat refusal")
        return real_exists(path)

    monkeypatch.setattr(Path, "exists", refuse_manifest_probe)
    result = build_package_map(tmp_path)

    assert result["package_mode"] == "unreadable"
    assert result["analyzable"] is False


def test_plain_artifact_existence_probe_failure_is_typed(monkeypatch, tmp_path):
    artifact = tmp_path / "evidence.csv"
    real_exists = Path.exists

    def refuse_artifact_probe(path):
        if path == artifact:
            raise PermissionError("synthetic artifact stat refusal")
        return real_exists(path)

    monkeypatch.setattr(Path, "exists", refuse_artifact_probe)
    state = _resolve_artifact("evidence.csv", tmp_path, "Example")

    assert state["present"] is False
    assert "existence unreadable" in state["note"]
