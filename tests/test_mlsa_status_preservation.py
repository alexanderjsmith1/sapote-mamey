"""Status JSON write controls only: never run MLSA, probes or external commands."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mlsa_status_candidate", ROOT / "tools/build_mlsa.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
DETAIL = "opaque café\r\nstring"


def invoke(output):
    tool._write_status(str(output.parent), "SOFTWARE_STATE", DETAIL)


def setup(tmp_path, kind):
    source = tmp_path / "retained.bin"
    source.write_bytes(b"unique retained source bytes")
    output = tmp_path / "run_status.json"
    output.write_bytes(b"previous complete status")
    foreign = Path(str(output) + ".tmp")
    if kind == "ordinary":
        foreign.write_bytes(b"foreign stage evidence")
    elif kind == "symlink":
        foreign.symlink_to(source)
    elif kind == "hardlink":
        os.link(source, foreign)
    return source, output, foreign


def snapshot(root):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}


@pytest.mark.parametrize("kind", ["ordinary", "symlink", "hardlink"])
def test_foreign_stage_survives_status_publication(tmp_path, kind):
    source, output, foreign = setup(tmp_path, kind)
    source_before, foreign_before = source.read_bytes(), foreign.read_bytes()
    inode = foreign.lstat().st_ino
    invoke(output)
    assert source.read_bytes() == source_before
    assert foreign.exists() and foreign.read_bytes() == foreign_before
    assert foreign.lstat().st_ino == inode
    assert json.loads(output.read_text()) == {"status": "SOFTWARE_STATE", "detail": DETAIL, "scope": "mechanical MLSA build only; judgment deferred"}
    assert set(snapshot(tmp_path)) == {source.name, output.name, foreign.name}


@pytest.mark.parametrize("kind", ["none", "ordinary", "symlink", "hardlink"])
@pytest.mark.parametrize("failure", ["open", "write", "commit"])
def test_failures_preserve_prior_status_and_retained_files(tmp_path, monkeypatch, kind, failure):
    source, output, foreign = setup(tmp_path, kind)
    before = snapshot(tmp_path)
    if failure == "open":
        def broken_open(*args, **kwargs):
            raise OSError("synthetic open failure")
        monkeypatch.setattr(tool, "open", broken_open, raising=False)
    elif failure == "write":
        def broken_dump(data, handle, **kwargs):
            handle.write("partial staged status")
            raise OSError("synthetic write failure")
        monkeypatch.setattr(tool.json, "dump", broken_dump)
    else:
        def broken_replace(*args, **kwargs):
            raise OSError("synthetic commit failure")
        monkeypatch.setattr(tool.os, "replace", broken_replace)
    with pytest.raises(OSError, match="synthetic"):
        invoke(output)
    assert snapshot(tmp_path) == before


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes")
@pytest.mark.parametrize("mode", [0o600, 0o640, 0o660])
def test_existing_regular_mode_is_retained_after_private_complete_write(tmp_path, monkeypatch, mode):
    source, output, foreign = setup(tmp_path, "ordinary")
    output.chmod(mode)
    observed = []
    real_dump, real_replace = tool.json.dump, tool.os.replace
    def observed_dump(data, handle, **kwargs):
        observed.append(os.fstat(handle.fileno()).st_mode & 0o777)
        return real_dump(data, handle, **kwargs)
    def checked_replace(stage, final):
        assert json.loads(Path(stage).read_text())["status"] == "SOFTWARE_STATE"
        assert Path(stage).stat().st_mode & 0o777 == mode
        return real_replace(stage, final)
    monkeypatch.setattr(tool.json, "dump", observed_dump)
    monkeypatch.setattr(tool.os, "replace", checked_replace)
    invoke(output)
    assert observed == [0o600]
    assert output.stat().st_mode & 0o777 == mode


@pytest.mark.parametrize("broken", [False, True])
def test_symlink_leaf_metadata_not_followed(tmp_path, broken):
    source = tmp_path / "retained.txt"
    if not broken:
        source.write_bytes(b"retained source")
        source.chmod(0o640)
    output = tmp_path / "run_status.json"
    output.symlink_to(source)
    invoke(output)
    assert not output.is_symlink()
    if os.name == "posix":
        assert output.stat().st_mode & 0o777 == 0o600
    if broken:
        assert not source.exists()
    else:
        assert source.read_bytes() == b"retained source"
        assert source.stat().st_mode & 0o777 == 0o640


def test_chmod_failure_preserves_original_status_and_cleans_own_stage(tmp_path, monkeypatch):
    source, output, foreign = setup(tmp_path, "ordinary")
    before = snapshot(tmp_path)
    def broken_chmod(*args, **kwargs):
        raise OSError("synthetic chmod failure")
    monkeypatch.setattr(tool.os, "chmod", broken_chmod)
    with pytest.raises(OSError, match="chmod failure"):
        invoke(output)
    assert snapshot(tmp_path) == before


def test_stage_reservation_failure_leaves_all_files_untouched(tmp_path, monkeypatch):
    from mamey import packaging
    source, output, foreign = setup(tmp_path, "ordinary")
    before = snapshot(tmp_path)
    def unavailable(*args, **kwargs):
        raise OSError("synthetic stage reservation failure")
    monkeypatch.setattr(packaging, "_unique_tmp", unavailable)
    with pytest.raises(OSError, match="stage reservation failure"):
        invoke(output)
    assert snapshot(tmp_path) == before


def test_clean_status_retains_schema_and_json_bytes(tmp_path):
    output = tmp_path / "run_status.json"
    invoke(output)
    expected = json.dumps({"status": "SOFTWARE_STATE", "detail": DETAIL, "scope": "mechanical MLSA build only; judgment deferred"}, indent=2) + "\n"
    assert output.read_bytes() == expected.encode()
    assert list(tmp_path.iterdir()) == [output]
