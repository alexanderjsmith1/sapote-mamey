"""Real discovery entrypoints with toy metadata and bounded filesystem faults."""
import hashlib
import json
import os
from pathlib import Path

import pytest
from mamey import discover
from mamey import workspace_source_discovery as catalog


@pytest.fixture
def request_files(tmp_path):
    root = tmp_path / "workspace"
    docs = root / "documents"
    docs.mkdir(parents=True)
    (docs / "example.md").write_text("generic source text\n", encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({
        "schema_version": "sapote-source-collection-registry-v1",
        "rules": [{"collection_type": "DOCUMENTS", "directory_regex": "documents",
                   "material_file_regex": r".*\.md$"}],
    }), encoding="utf-8")
    report = tmp_path / "report.md"
    report.write_bytes(b"retained report\n")
    return root, registry, report, tmp_path / "catalog.json", tmp_path / "catalog.tsv"


def request_args(files, **overrides):
    root, registry, report, first, second = files
    args = discover._build_parser().parse_args([
        str(root), "--source-collection-registry", str(registry),
        "--expected-source-collection-registry-sha256", hashlib.sha256(registry.read_bytes()).hexdigest(),
        "--source-root-id", "TOY", "--emit-md", str(report),
        "--emit-source-catalog-json", str(first), "--emit-source-catalog-tsv", str(second),
    ])
    for key, value in overrides.items():
        setattr(args, key, value)
    return args


def refused_call(args):
    try:
        discover.discover_command(args)
    except ValueError as error:
        return error
    return None


@pytest.mark.parametrize("alias", ["same_path", "hardlink"])
def test_report_cannot_replace_registry_evidence(request_files, alias, capsys):
    root, registry, report, first, second = request_files
    if alias == "hardlink":
        report.unlink()
        os.link(registry, report)
    else:
        report = registry
    before = registry.read_bytes()
    error = refused_call(request_args((root, registry, report, first, second)))
    assert registry.read_bytes() == before, "report publication changed the selected registry"
    assert error is not None, "registry/output alias was not refused"
    assert not first.exists() and not second.exists()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("selected", ["json", "tsv"])
@pytest.mark.parametrize("spelling", ["exact", "casefold"])
def test_report_catalog_alias_refuses_before_any_output_change(request_files, selected, spelling, capsys):
    root, registry, _, first, second = request_files
    selected_path = first if selected == "json" else second
    report = selected_path if spelling == "exact" else selected_path.with_name(selected_path.name.upper())
    report.write_bytes(b"retained alias report\n")
    error = refused_call(request_args((root, registry, report, first, second)))
    assert report.read_bytes() == b"retained alias report\n", "alias refusal came after report replacement"
    assert error is not None
    peer = second if selected == "json" else first
    assert not peer.exists()
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("occupied", ["json", "tsv"])
def test_occupied_catalog_preserves_prior_report(request_files, occupied, capsys):
    _, _, report, first, second = request_files
    occupied_path = first if occupied == "json" else second
    peer = second if occupied == "json" else first
    occupied_path.write_bytes(b"retained catalog\n")
    with pytest.raises(ValueError):
        discover.discover_command(request_args(request_files))
    assert report.read_bytes() == b"retained report\n", "occupied catalog was checked after report replacement"
    assert occupied_path.read_bytes() == b"retained catalog\n" and not peer.exists()
    assert capsys.readouterr().out == ""


def test_second_catalog_fault_rolls_back_first_and_preserves_report(request_files, monkeypatch, capsys):
    _, _, report, first, second = request_files
    original = Path.open
    seen = []
    def open_path(path, mode="r", *args, **kwargs):
        if path == second and mode == "xb":
            seen.append(first.is_file())
            raise OSError("injected second catalog write failure")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", open_path)
    with pytest.raises(OSError, match="injected second catalog"):
        discover.discover_command(request_args(request_files))
    assert seen == [True], "fault did not reach the second publication after first creation"
    assert report.read_bytes() == b"retained report\n", "catalog failure left a new report"
    assert not first.exists() and not second.exists()
    assert capsys.readouterr().out == ""


def test_report_commit_fault_rolls_back_both_catalogs(request_files, monkeypatch, capsys):
    _, _, report, first, second = request_files
    original = os.replace
    seen = []
    def replace(source, target, *args, **kwargs):
        if Path(target) == report:
            seen.append((first.is_file(), second.is_file(), report.read_bytes()))
            raise OSError("injected final report commit failure")
        return original(source, target, *args, **kwargs)
    monkeypatch.setattr(os, "replace", replace)
    with pytest.raises(OSError, match="injected final report"):
        discover.discover_command(request_args(request_files))
    assert seen == [(True, True, b"retained report\n")]
    assert report.read_bytes() == b"retained report\n"
    assert not first.exists() and not second.exists()
    assert not list(report.parent.glob(".mamey-report-*"))
    assert capsys.readouterr().out == ""


def test_incomplete_scan_retains_diagnostics_and_returns_three(request_files, monkeypatch, capsys):
    root, _, report, first, second = request_files
    original = catalog.os.walk
    def walk(path, *args, onerror=None, **kwargs):
        yield from original(path, *args, onerror=onerror, **kwargs)
        if onerror is not None:
            onerror(PermissionError(13, "injected unreadable folder", str(root / "blocked")))
    monkeypatch.setattr(catalog.os, "walk", walk)
    result = discover.discover_command(request_args(request_files))
    payload = json.loads(first.read_text(encoding="utf-8"))
    assert payload["status"] == "INCOMPLETE_FILESYSTEM_SCAN"
    assert result == 3, "incomplete governed discovery returned success"
    assert "INCOMPLETE_FILESYSTEM_SCAN" in report.read_text() and second.is_file()
    decisions = report.parent / "decisions.tsv"
    decisions.write_text("collection_id\tdecision\treason\tevidence_receipt\n")
    gate = catalog.validate_report_source_preflight(
        catalog_path=first, expected_catalog_sha256=hashlib.sha256(first.read_bytes()).hexdigest(),
        decisions_path=decisions, expected_decisions_sha256=hashlib.sha256(decisions.read_bytes()).hexdigest(),
        strain_key="TOY", required_collection_types=set())
    assert gate["reason_code"] == "DISCOVERY_CATALOG_NOT_COMPLETE"
    assert "INCOMPLETE_FILESYSTEM_SCAN" in capsys.readouterr().out


def test_standalone_repeat_refuses_before_scanning(request_files, monkeypatch):
    root, registry, _, first, second = request_files
    args = ["scan", str(root), "--root-id", "TOY", "--collection-registry", str(registry),
            "--expected-collection-registry-sha256", hashlib.sha256(registry.read_bytes()).hexdigest(),
            "--out-json", str(first), "--out-tsv", str(second)]
    assert catalog.main(args) == 0
    before = first.read_bytes(), second.read_bytes()
    def forbidden(**kwargs):
        raise AssertionError("occupied output request traversed source before refusal")
    monkeypatch.setattr(catalog, "build_source_catalog", forbidden)
    with pytest.raises(ValueError):
        catalog.main(args)
    assert (first.read_bytes(), second.read_bytes()) == before


def test_registered_report_replacement_and_catalog_pair_stay_coherent(request_files, capsys):
    _, registry, report, first, second = request_files
    registry_before = registry.read_bytes()
    assert discover.discover_command(request_args(request_files)) == 0
    data = json.loads(first.read_text(encoding="utf-8"))
    assert data["status"] == "PASS_COMPLETE" and len(data["collections"]) == 1
    assert data["collections"][0]["collection_type"] == "DOCUMENTS"
    assert "DOCUMENTS" in second.read_text() and "registered collections: 1" in report.read_text()
    assert registry.read_bytes() == registry_before
    assert not list(report.parent.glob(".mamey-report-*"))
    assert "[wrote source catalog:" in capsys.readouterr().out


@pytest.mark.parametrize("missing", ["expected_source_collection_registry_sha256", "source_root_id"])
def test_missing_registry_binding_refuses_before_workspace_traversal(request_files, monkeypatch, missing):
    def forbidden(*args, **kwargs):
        raise AssertionError("invalid registry binding reached workspace traversal")
    monkeypatch.setattr(discover, "_find_packages", forbidden)
    with pytest.raises(ValueError, match="registry SHA-256 and source root ID"):
        discover.discover_command(request_args(request_files, **{missing: None}))
