"""Synthetic JSON/TSV publication only; caller sentinels must survive."""
import hashlib
import json
from pathlib import Path

import pytest
from mamey.workspace_source_discovery import write_catalog


@pytest.fixture
def catalog():
    return {"status": "PASS_COMPLETE", "collections": [{
        "collection_id": "COLL_DEMO", "collection_type": "DOCUMENTS", "relative_path": "=demo",
        "file_count_at_directory": 1, "apparent_bytes_at_directory": 4,
        "strain_keys_observed": [], "strain_count": 0,
        "coverage_extraction_state": "PATH_AND_FILENAME_ONLY",
        "classification_state": "REGISTERED_SIGNATURE", "authority_state": "DISCOVERED_NOT_ADMITTED",
        "generation_state": "UNRESOLVED",
    }]}


@pytest.mark.parametrize("occupied", ["json", "tsv"])
def test_existing_selected_output_preserves_bytes_and_peer_absence(tmp_path, catalog, occupied):
    json_path = tmp_path / "catalog.json"; tsv_path = tmp_path / "catalog.tsv"
    chosen = json_path if occupied == "json" else tsv_path
    peer = tsv_path if occupied == "json" else json_path
    chosen.write_bytes(b"UNOWNED_GENERIC_SENTINEL")
    with pytest.raises((ValueError, FileExistsError)):
        write_catalog(catalog, json_path, tsv_path)
    assert chosen.read_bytes() == b"UNOWNED_GENERIC_SENTINEL"
    assert not peer.exists()


def test_same_output_slot_is_refused_before_write(tmp_path, catalog):
    target = tmp_path / "same"
    with pytest.raises(ValueError, match="collide"):
        write_catalog(catalog, target, target)
    assert not target.exists()


def test_output_ancestor_collision_is_refused_before_parent_creation(tmp_path, catalog):
    target = tmp_path / "would_be_file"
    with pytest.raises(ValueError, match="collide"):
        write_catalog(catalog, target, target / "nested.tsv")
    assert not target.exists()


def test_alias_parent_is_refused_without_touching_external_directory(tmp_path, catalog):
    outside = tmp_path / "outside"; outside.mkdir()
    alias = tmp_path / "alias"; alias.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        write_catalog(catalog, alias / "catalog.json", tmp_path / "catalog.tsv")
    assert list(outside.iterdir()) == [] and not (tmp_path / "catalog.tsv").exists()


def test_serialization_failure_cannot_leave_first_output(tmp_path, catalog):
    catalog["collections"][0]["unexpected_column"] = "generic"
    with pytest.raises(ValueError):
        write_catalog(catalog, tmp_path / "catalog.json", tmp_path / "catalog.tsv")
    assert not (tmp_path / "catalog.json").exists() and not (tmp_path / "catalog.tsv").exists()


def test_racing_second_slot_preserves_unowned_bytes_and_rolls_back_first(tmp_path, catalog, monkeypatch):
    json_path = tmp_path / "catalog.json"; tsv_path = tmp_path / "catalog.tsv"
    original = Path.open
    def open_path(path, mode="r", *args, **kwargs):
        if path == tsv_path and mode in {"xb", "w"}:
            tsv_path.write_bytes(b"RACING_GENERIC_SENTINEL")
        return original(path, mode, *args, **kwargs)
    monkeypatch.setattr(Path, "open", open_path)
    with pytest.raises((ValueError, FileExistsError)):
        write_catalog(catalog, json_path, tsv_path)
    assert tsv_path.read_bytes() == b"RACING_GENERIC_SENTINEL"
    assert not json_path.exists()


def test_fresh_pair_keeps_schema_safe_tsv_and_exact_hashes(tmp_path, catalog):
    json_path = tmp_path / "catalog.json"
    tsv_path = tmp_path / "catalog.tsv"
    result = write_catalog(catalog, json_path, tsv_path)
    assert json.loads(json_path.read_text(encoding="utf-8")) == catalog
    assert "'=demo" in tsv_path.read_text(encoding="utf-8")
    assert result["status"] == "PASS_COMPLETE" and result["collection_count"] == 1
    assert result["catalog_json_sha256"] == hashlib.sha256(json_path.read_bytes()).hexdigest()
    assert result["catalog_tsv_sha256"] == hashlib.sha256(tsv_path.read_bytes()).hexdigest()
