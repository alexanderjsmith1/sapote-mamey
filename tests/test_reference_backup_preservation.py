"""Backup/library write ownership only; scans and signature inference are stubbed."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reference_candidate", ROOT / "tools/backfill_reference_signatures.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def setup(tmp_path, monkeypatch):
    library = tmp_path / "library.json"
    original = {"entries": [{"accession": "BGC0000000", "genus": "software", "curated_fixture": "retain", "architecture_signature": {"software": "existing"}}]}
    library.write_text(json.dumps(original))
    backup = Path(str(library) + ".bak")
    backup.write_bytes(b"older backup bytes")
    retained = tmp_path / "retained_source.bin"
    retained.write_bytes(b"unique retained source evidence")
    zips = tmp_path / "opaque_names"
    zips.mkdir()
    (zips / "SOFTWARE_BGC0000000.zip").write_bytes(b"opaque software fixture; never opened")
    monkeypatch.setattr(tool, "ledger_for_zip", lambda path: [{}])
    monkeypatch.setattr(tool, "signature_from_row", lambda row: ({}, [], 0.0))
    def forbidden(*args):
        pytest.fail("organism extraction must not run")
    monkeypatch.setattr(tool, "organism_from_zip", forbidden)
    monkeypatch.setattr(sys, "argv", ["backfill_reference_signatures.py", str(zips), "--lib", str(library)])
    return library, backup, retained, original


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def foreign_path(path, target, kind):
    if kind == "ordinary":
        path.write_bytes(b"foreign stage bytes")
    elif kind == "symlink":
        path.symlink_to(target)
    else:
        os.link(target, path)


@pytest.mark.parametrize("stage", ["backup", "library"])
@pytest.mark.parametrize("kind", ["ordinary", "symlink", "hardlink"])
def test_success_preserves_foreign_staging_paths(tmp_path, monkeypatch, stage, kind):
    library, backup, retained, original = setup(tmp_path, monkeypatch)
    foreign = Path(str(backup if stage == "backup" else library) + ".tmp")
    foreign_path(foreign, retained, kind)
    foreign_before, retained_before = foreign.read_bytes(), retained.read_bytes()
    inode = foreign.lstat().st_ino
    tool.main()
    assert retained.read_bytes() == retained_before
    assert foreign.exists() and foreign.read_bytes() == foreign_before
    assert foreign.lstat().st_ino == inode
    assert json.loads(backup.read_text()) == original
    updated = json.loads(library.read_text())
    assert updated["entries"][0]["curated_fixture"] == "retain"
    assert updated["entries"][0]["architecture_signature"] == original["entries"][0]["architecture_signature"]
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted([library.name, backup.name, retained.name, "opaque_names", foreign.name])


def test_backup_temp_alias_of_library_does_not_destroy_source_before_read(tmp_path, monkeypatch):
    library, backup, retained, original = setup(tmp_path, monkeypatch)
    foreign = Path(str(backup) + ".tmp")
    foreign.symlink_to(library)
    inode = foreign.lstat().st_ino
    tool.main()
    assert json.loads(backup.read_text()) == original
    assert json.loads(library.read_text())["entries"][0]["curated_fixture"] == "retain"
    assert foreign.is_symlink() and foreign.lstat().st_ino == inode


@pytest.mark.parametrize("failure_stage", ["backup", "library"])
def test_serialization_failure_preserves_library_and_appropriate_backup(tmp_path, monkeypatch, failure_stage):
    library, backup, retained, original = setup(tmp_path, monkeypatch)
    library_before, backup_before = library.read_bytes(), backup.read_bytes()
    before = snapshot(tmp_path)
    real_dump = tool.json.dump
    calls = 0
    def broken_dump(obj, handle, *args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == (1 if failure_stage == "backup" else 2):
            handle.write("partial staged JSON")
            raise RuntimeError("synthetic serialization failure")
        return real_dump(obj, handle, *args, **kwargs)
    monkeypatch.setattr(tool.json, "dump", broken_dump)
    with pytest.raises(RuntimeError, match="synthetic serialization failure"):
        tool.main()
    assert library.read_bytes() == library_before
    if failure_stage == "backup":
        assert backup.read_bytes() == backup_before
        assert snapshot(tmp_path) == before
    else:
        assert json.loads(backup.read_text()) == original
        assert set(snapshot(tmp_path)) == set(before)
        assert retained.read_bytes() == b"unique retained source evidence"


def test_dry_run_keeps_library_and_backup_unchanged(tmp_path, monkeypatch):
    library, backup, retained, original = setup(tmp_path, monkeypatch)
    monkeypatch.setattr(sys, "argv", sys.argv + ["--dry-run"])
    before = snapshot(tmp_path)
    tool.main()
    assert snapshot(tmp_path) == before


def test_existing_output_modes_follow_native_writer_contract(tmp_path, monkeypatch):
    library, backup, retained, original = setup(tmp_path, monkeypatch)
    library.chmod(0o600)
    backup.chmod(0o640)
    tool.main()
    assert library.stat().st_mode & 0o777 == 0o600
    assert backup.stat().st_mode & 0o777 == 0o640


def test_clean_success_keeps_json_content_and_formatting(tmp_path, monkeypatch):
    library, backup, retained, original = setup(tmp_path, monkeypatch)
    expected = json.loads(json.dumps(original))
    expected["entries"][0]["found_markers"] = []
    expected["entries"][0]["found_size_kb"] = 0.0
    tool.main()
    assert backup.read_bytes() == json.dumps(original, indent=2).encode("utf-8")
    assert library.read_bytes() == json.dumps(expected, indent=2).encode()
    assert len(list(tmp_path.iterdir())) == 4
