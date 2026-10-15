from pathlib import Path
import pytest
from mamey import source_availability as mod

@pytest.mark.parametrize("kind", ["collection_escape", "nested_symlink", "walk_error"])
def test_incomplete_or_escaped_collection_walk_is_not_success(tmp_path, monkeypatch, kind):
    root = tmp_path / "source"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "evidence.txt").write_text("data")
    relative = "collection" if kind == "collection_escape" else "."
    if kind == "collection_escape":(root / relative).symlink_to(outside)
    elif kind == "nested_symlink":(root / "nested").symlink_to(outside)
    roles = [{"source_role": role, "collection_types": ["synthetic"], "path_regex": "unused"} for role in mod.DEFAULT_REQUIRED_ROLES]
    monkeypatch.setattr(mod, "_load_collection_registry", lambda *a: ({"availability_roles": roles}, "hash"))
    monkeypatch.setattr(mod, "_load_catalog_and_decisions", lambda **k: ({"collections": [{"collection_id": "one", "relative_path": relative, "collection_type": "synthetic"}]}, {"one": {"decision": "CONSUME"}}, "hash", "hash"))
    if kind == "walk_error":
        def denied(path, **kwargs):
            kwargs.get("onerror", lambda *args: None)(PermissionError("unreadable subtree"))
            return iter([])
        monkeypatch.setattr(mod.os, "walk", denied)
    with pytest.raises((ValueError, PermissionError)):
        mod.build_source_availability(source_root=root, source_root_id="SYN", source_catalog_path=root, expected_source_catalog_sha256="hash", source_decisions_path=root, expected_source_decisions_sha256="hash", collection_registry_path=root, expected_collection_registry_sha256="hash", target_loci=[])
