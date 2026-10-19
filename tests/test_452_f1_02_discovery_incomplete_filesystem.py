"""Generic directory/alias/error metadata; no scientific parser or subprocess."""
import json
from pathlib import Path

import pytest
from mamey import workspace_source_discovery as discovery


@pytest.fixture
def scan(tmp_path):
    root = tmp_path / "workspace"; root.mkdir()
    docs = root / "documents"; docs.mkdir()
    (docs / "entry.md").write_text("generic evidence\n", encoding="utf-8")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({
        "schema_version": "sapote-source-collection-registry-v1",
        "rules": [{"collection_type": "DOCUMENTS", "directory_regex": "documents",
                   "material_file_regex": r".*\.md$"}],
    }), encoding="utf-8")
    def build(selected=None):
        return discovery.build_source_catalog(root=selected or root, root_id="DEMO",
            collection_registry_path=registry,
            expected_collection_registry_sha256=discovery.sha256_file(registry))
    return root, docs, build


def test_file_root_is_refused(scan):
    root, docs, build = scan
    with pytest.raises(ValueError, match="directory"):
        build(docs / "entry.md")


def test_walk_error_cannot_report_complete(scan, monkeypatch):
    root, docs, build = scan
    original = discovery.os.walk
    def walk(path, *args, onerror=None, **kwargs):
        yield from original(path, *args, onerror=onerror, **kwargs)
        if onerror:
            onerror(PermissionError(13, "synthetic blocked directory", str(root / "blocked")))
    monkeypatch.setattr(discovery.os, "walk", walk)
    result = build()
    assert result["status"] != "PASS_COMPLETE", "walk omissions cannot establish complete discovery"
    assert result["scan_errors"] == [{"relative_path": "blocked", "reason_code": "DIRECTORY_UNREADABLE"}]
    assert str(root) not in json.dumps(result)


def test_unstatable_file_cannot_report_complete(scan, monkeypatch):
    root, docs, build = scan
    selected = docs / "entry.md"
    original = Path.lstat
    def lstat(path, *args, **kwargs):
        if path == selected:
            raise PermissionError("synthetic file metadata refusal")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "lstat", lstat)
    result = build()
    assert result["status"] != "PASS_COMPLETE", "stat omissions cannot establish complete discovery"
    assert any(e["reason_code"] == "FILE_STAT_UNAVAILABLE" for e in result["scan_errors"])


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_symlink_surface_is_not_silently_admitted_or_omitted(scan, tmp_path, kind):
    root, docs, build = scan
    outside = tmp_path / "outside"; outside.mkdir()
    item = outside / "entry.md"; item.write_text("UNOWNED_GENERIC_SENTINEL", encoding="utf-8")
    if kind == "file":
        (docs / "linked.md").symlink_to(item)
    else:
        (root / "linked_documents").symlink_to(outside, target_is_directory=True)
    result = build()
    assert result["status"] != "PASS_COMPLETE", "aliases require an incomplete-scan receipt"
    assert result["scan_counts"]["unadmitted_filesystem_surface_count"] == 1
    assert item.read_text(encoding="utf-8") == "UNOWNED_GENERIC_SENTINEL"


def test_readable_regular_tree_remains_complete(scan):
    root, docs, build = scan
    result = build()
    assert result["status"] == "PASS_COMPLETE"
    assert result["scan_counts"]["files_seen"] == 1
    assert result["collections"][0]["collection_type"] == "DOCUMENTS"
    assert result["collections"][0]["authority_state"] == "DISCOVERED_NOT_ADMITTED"
