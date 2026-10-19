"""Same inaccessible metadata condition through either baseline or repaired scanner."""
import hashlib
import json
from pathlib import Path

from mamey import workspace_source_discovery as discovery


def test_inaccessible_file_metadata_cannot_certify_complete(tmp_path, monkeypatch):
    root = tmp_path / "workspace"
    docs = root / "documents"
    docs.mkdir(parents=True)
    selected = docs / "entry.md"
    selected.write_bytes(b"generic metadata fixture\n")
    registry = tmp_path / "registry.json"
    registry.write_text(json.dumps({"schema_version": "sapote-source-collection-registry-v1",
        "rules": [{"collection_type": "DOCUMENTS", "directory_regex": "documents",
                   "material_file_regex": r".*\.md$"}]}))
    expected_sha = hashlib.sha256(registry.read_bytes()).hexdigest()
    stat, lstat = Path.stat, Path.lstat
    calls = []
    def inaccessible(method, original):
        def observed(path, *args, **kwargs):
            if path == selected:
                calls.append(method)
                raise PermissionError(13, "synthetic inaccessible file metadata", str(path))
            return original(path, *args, **kwargs)
        return observed
    monkeypatch.setattr(Path, "stat", inaccessible("stat", stat))
    monkeypatch.setattr(Path, "lstat", inaccessible("lstat", lstat))
    result = discovery.build_source_catalog(root=root, root_id="TOY",
        collection_registry_path=registry, expected_collection_registry_sha256=expected_sha)
    assert calls, "metadata fault did not reach the selected source file"
    assert result["status"] != "PASS_COMPLETE", "inaccessible file was silently omitted from complete discovery"
    assert any(row["reason_code"] == "FILE_STAT_UNAVAILABLE" for row in result["scan_errors"])
