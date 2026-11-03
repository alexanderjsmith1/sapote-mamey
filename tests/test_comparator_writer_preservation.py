"""Writer-only opaque strings; do not invoke comparator parsing or analysis."""
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mamey.comparators.writer_candidate", ROOT / "mamey/comparators/antismash_ingest.py")
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)


def setup(tmp_path, kind):
    source = tmp_path / "retained.bin"
    source.write_bytes(b"unique retained source bytes")
    output = tmp_path / "context.tsv"
    output.write_bytes(b"previous complete output")
    foreign = Path(str(output) + ".tmp")
    if kind == "ordinary":
        foreign.write_bytes(b"foreign staging evidence")
    elif kind == "symlink":
        foreign.symlink_to(source)
    elif kind == "hardlink":
        os.link(source, foreign)
    return source, output, foreign


def snapshot(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}


@pytest.mark.parametrize("kind", ["ordinary", "symlink", "hardlink"])
def test_foreign_stage_survives_success(tmp_path, kind):
    source, output, foreign = setup(tmp_path, kind)
    source_before, foreign_before = source.read_bytes(), foreign.read_bytes()
    inode = foreign.lstat().st_ino
    tool._atomic_write_text(output, "opaque café\r\nsecond line\n")
    assert source.read_bytes() == source_before
    assert foreign.exists() and foreign.read_bytes() == foreign_before
    assert foreign.lstat().st_ino == inode
    assert output.read_bytes() == "opaque café\r\nsecond line\n".encode("utf-8")
    assert set(snapshot(tmp_path)) == {source.name, output.name, foreign.name}


@pytest.mark.parametrize("kind", ["none", "ordinary", "symlink", "hardlink"])
@pytest.mark.parametrize("failure", ["open", "write", "encoding", "commit"])
def test_failure_keeps_original_files_and_discards_only_owned_stage(tmp_path, monkeypatch, kind, failure):
    source, output, foreign = setup(tmp_path, kind)
    before = snapshot(tmp_path)
    if failure == "open":
        def broken_open(*args, **kwargs):
            raise OSError("synthetic open failure")
        monkeypatch.setattr(tool, "open", broken_open, raising=False)
        text, encoding, error = "opaque", "utf-8", OSError
    elif failure == "write":
        real_open = open
        class BrokenFile:
            def __init__(self, *args, **kwargs):
                self.handle = real_open(*args, **kwargs)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.handle.close()
            def write(self, text):
                self.handle.write("partial staged write")
                raise OSError("synthetic write failure")
        monkeypatch.setattr(tool, "open", BrokenFile, raising=False)
        text, encoding, error = "opaque", "utf-8", OSError
    elif failure == "commit":
        def broken_replace(*args, **kwargs):
            raise OSError("synthetic commit failure")
        monkeypatch.setattr(tool.os, "replace", broken_replace)
        text, encoding, error = "opaque", "utf-8", OSError
    else:
        text, encoding, error = "unencodable snowman \u2603", "ascii", UnicodeEncodeError
    with pytest.raises(error):
        tool._atomic_write_text(output, text, encoding)
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("encoding", ["utf-8", "latin-1"])
def test_clean_write_keeps_encoding_and_newlines(tmp_path, encoding):
    output = tmp_path / "output.txt"
    text = "opaque café\r\nlast line\n"
    tool._atomic_write_text(output, text, encoding)
    assert output.read_bytes() == text.encode(encoding)
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit contract")
@pytest.mark.parametrize("mode", [0o600, 0o640, 0o644, 0o660])
def test_existing_mode_applies_only_after_complete_private_write(tmp_path, monkeypatch, mode):
    source, output, foreign = setup(tmp_path, "ordinary")
    output.chmod(mode)
    payload = "complete opaque payload"
    observed = []
    real_open = open
    real_replace = tool.os.replace
    class ObservedFile:
        def __init__(self, *args, **kwargs):
            self.handle = real_open(*args, **kwargs)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.handle.close()
        def write(self, text):
            observed.append(os.fstat(self.handle.fileno()).st_mode & 0o777)
            return self.handle.write(text)
    def checked_replace(stage, destination):
        assert Path(stage).read_text() == payload
        assert Path(stage).stat().st_mode & 0o777 == mode
        assert output.read_bytes() == b"previous complete output"
        return real_replace(stage, destination)
    monkeypatch.setattr(tool, "open", ObservedFile, raising=False)
    monkeypatch.setattr(tool.os, "replace", checked_replace)
    tool._atomic_write_text(output, payload)
    assert observed == [0o600]
    assert output.stat().st_mode & 0o777 == mode
    assert foreign.read_bytes() == b"foreign staging evidence"


def test_mode_copy_failure_preserves_existing_files_and_cleans_private_stage(tmp_path, monkeypatch):
    source, output, foreign = setup(tmp_path, "ordinary")
    before = snapshot(tmp_path)
    mode_before = output.stat().st_mode
    def broken_chmod(*args, **kwargs):
        raise OSError("synthetic chmod failure")
    monkeypatch.setattr(tool.os, "chmod", broken_chmod)
    with pytest.raises(OSError, match="synthetic chmod failure"):
        tool._atomic_write_text(output, "complete opaque payload")
    assert snapshot(tmp_path) == before
    assert output.stat().st_mode == mode_before


@pytest.mark.parametrize("broken", [False, True])
def test_symlink_leaf_metadata_is_not_followed(tmp_path, monkeypatch, broken):
    source = tmp_path / "retained.txt"
    if not broken:
        source.write_bytes(b"retained source")
        source.chmod(0o640)
    output = tmp_path / "report.txt"
    output.symlink_to(source)
    changes = []
    real_chmod = tool.os.chmod
    def tracked_chmod(path, mode, *args, **kwargs):
        changes.append((str(path), mode))
        return real_chmod(path, mode, *args, **kwargs)
    monkeypatch.setattr(tool.os, "chmod", tracked_chmod)
    tool._atomic_write_text(output, "opaque replacement")
    assert changes == []
    assert not output.is_symlink()
    assert output.read_text() == "opaque replacement"
    if os.name == "posix":
        assert output.stat().st_mode & 0o777 == 0o600
    if broken:
        assert not source.exists()
    else:
        assert source.read_bytes() == b"retained source"
        assert source.stat().st_mode & 0o777 == 0o640
