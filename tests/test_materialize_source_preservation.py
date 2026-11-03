"""Copy/publication controls using opaque bytes and a resolver stub, no ZIP analysis."""
import errno
import hashlib
import importlib.util
import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("materialize_candidate", ROOT / "tools/materialize_strain_data.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
STRAIN = "AS-SOFTWARE"


def setup(tmp_path, monkeypatch):
    source = tmp_path / "original.zip"
    source.write_bytes(b"opaque synthetic source bytes, not a biological archive")
    retained = tmp_path / "retained_evidence.bin"
    retained.write_bytes(b"unique retained evidence bytes")
    monkeypatch.setattr(tool, "SKIP_STRAINS", set())
    monkeypatch.setattr(tool, "resolve_antismash_zip", lambda strain, root: str(source))
    dest = Path(tool.canonical_slot(str(tmp_path), STRAIN))
    dest.parent.mkdir(parents=True)
    return source, retained, dest, Path(str(dest) + ".tmp")


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob("*") if p.is_file()}


def foreign_path(path, retained, kind):
    if kind == "ordinary":
        path.write_bytes(b"foreign temporary evidence")
    elif kind == "symlink":
        path.symlink_to(retained)
    elif kind == "hardlink":
        os.link(retained, path)


@pytest.mark.parametrize("kind", ["ordinary", "symlink", "hardlink"])
def test_foreign_predictable_stage_survives_success(tmp_path, monkeypatch, kind):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    foreign_path(foreign, retained, kind)
    before = snapshot(tmp_path)
    inode = foreign.lstat().st_ino
    tool.materialize(str(tmp_path), [STRAIN], True)
    after = snapshot(tmp_path)
    assert all(after.get(p) == value for p, value in before.items())
    assert foreign.lstat().st_ino == inode
    assert dest.read_bytes() == source.read_bytes()
    assert set(after) - set(before) == {str(dest.relative_to(tmp_path))}


@pytest.mark.parametrize("kind", ["ordinary", "symlink", "hardlink"])
def test_copy_failure_cleans_only_owned_stage(tmp_path, monkeypatch, kind):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    foreign_path(foreign, retained, kind)
    before = snapshot(tmp_path)
    def broken_copy(src, target):
        Path(target).write_bytes(b"partial copy")
        raise OSError("synthetic copy failure")
    monkeypatch.setattr(tool.shutil, "copy2", broken_copy)
    with pytest.raises(OSError, match="synthetic copy failure"):
        tool.materialize(str(tmp_path), [STRAIN], True)
    assert snapshot(tmp_path) == before
    assert not dest.exists()


def test_slot_created_during_copy_is_never_replaced(tmp_path, monkeypatch):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    before = snapshot(tmp_path)
    real_copy = tool.shutil.copy2
    def copy_then_claim(src, target):
        result = real_copy(src, target)
        dest.write_bytes(b"another writer completed this canonical slot")
        return result
    monkeypatch.setattr(tool.shutil, "copy2", copy_then_claim)
    refused = False
    try:
        tool.materialize(str(tmp_path), [STRAIN], True)
    except FileExistsError:
        refused = True
    assert refused
    assert dest.read_bytes() == b"another writer completed this canonical slot"
    after = snapshot(tmp_path)
    assert all(after.get(p) == value for p, value in before.items())
    assert set(after) - set(before) == {str(dest.relative_to(tmp_path))}


def test_unavailable_hardlink_publication_fails_closed(tmp_path, monkeypatch):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    before = snapshot(tmp_path)
    def unsupported(*args, **kwargs):
        raise OSError(errno.EOPNOTSUPP, "synthetic filesystem without hard links")
    monkeypatch.setattr(tool.os, "link", unsupported)
    with pytest.raises(OSError, match="without hard links"):
        tool.materialize(str(tmp_path), [STRAIN], True)
    assert snapshot(tmp_path) == before
    assert not dest.exists()


def test_existing_slot_is_skipped_without_resolving_source(tmp_path, monkeypatch):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    dest.write_bytes(b"existing canonical bytes")
    before = snapshot(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail("existing destination must skip before source resolution")
    monkeypatch.setattr(tool, "resolve_antismash_zip", forbidden)
    tool.materialize(str(tmp_path), [STRAIN], True)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("mode", ["dry", "excluded", "unresolved"])
def test_existing_skip_contracts_keep_all_bytes(tmp_path, monkeypatch, mode):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    before = snapshot(tmp_path)
    if mode == "excluded":
        monkeypatch.setattr(tool, "SKIP_STRAINS", {STRAIN})
    elif mode == "unresolved":
        monkeypatch.setattr(tool, "resolve_antismash_zip", lambda *args, **kwargs: None)
    tool.materialize(str(tmp_path), [STRAIN], mode != "dry")
    assert snapshot(tmp_path) == before


def test_fresh_copy_keeps_source_bytes_mode_and_mtime(tmp_path, monkeypatch):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    source.chmod(0o600)
    before = source.read_bytes()
    mode = source.stat().st_mode & 0o777
    modified = source.stat().st_mtime_ns
    tool.materialize(str(tmp_path), [STRAIN], True)
    assert source.read_bytes() == before == dest.read_bytes()
    assert dest.stat().st_mode & 0o777 == mode
    assert dest.stat().st_mtime_ns == modified
    assert dest.stat().st_nlink == 1
    assert not foreign.exists()
    assert list(dest.parent.iterdir()) == [dest]


def test_missing_owned_stage_is_reported(tmp_path, monkeypatch, caplog):
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    original_unlink = tool.os.unlink
    def vanished(path, *args, **kwargs):
        original_unlink(path, *args, **kwargs)
        raise FileNotFoundError("synthetic stage disappearance")
    monkeypatch.setattr(tool.os, "unlink", vanished)
    tool.materialize(str(tmp_path), [STRAIN], True)
    assert "MATERIALIZE_STAGE_MISSING" in caplog.text
    monkeypatch.undo()
    assert dest.read_bytes() == source.read_bytes()
    assert retained.read_bytes() == b"unique retained evidence bytes"


def test_missing_stage_does_not_mask_copy_error(tmp_path, monkeypatch, caplog):
    import warnings
    source, retained, dest, foreign = setup(tmp_path, monkeypatch)
    def broken_copy(src, target):
        Path(target).unlink()
        raise OSError("synthetic original copy error")
    monkeypatch.setattr(tool.shutil, "copy2", broken_copy)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(OSError, match="synthetic original copy error"):
            tool.materialize(str(tmp_path), [STRAIN], True)
    assert "MATERIALIZE_STAGE_MISSING" in caplog.text
    assert not dest.exists() and source.is_file()
