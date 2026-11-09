"""A failed project-home init removes only what it created."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "tools" / "init_project_data_home.py"
spec = importlib.util.spec_from_file_location("project_home_464r3", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_failed_init_keeps_a_file_another_writer_added(tmp_path, monkeypatch):
    root = tmp_path / "home"
    real = mod._write_tsv
    calls = {"n": 0}

    def flaky(path, header):
        calls["n"] += 1
        if calls["n"] == 1:
            # Another writer drops a file into the new home mid-run.
            (root / "01_AUTHORITY" / "someone_elses_notes.txt").write_text("keep me")
        if calls["n"] == 3:
            raise OSError("synthetic disk failure")
        return real(path, header)

    monkeypatch.setattr(mod, "_write_tsv", flaky)
    with pytest.raises(OSError, match="synthetic disk failure") as info:
        mod.create_home(root, "example")
    foreign = root / "01_AUTHORITY" / "someone_elses_notes.txt"
    assert foreign.read_text() == "keep me"
    # Owned register files and empty owned folders are gone.
    assert not (root / "01_AUTHORITY" / "AUTHORITY_INDEX.tsv").exists()
    assert not (root / "00_INBOX").exists()
    assert any("left these paths in place" in note for note in getattr(info.value, "__notes__", []))


def test_failed_init_on_clean_root_leaves_nothing(tmp_path, monkeypatch):
    root = tmp_path / "home"

    def boom(path, header):
        raise OSError("synthetic")

    monkeypatch.setattr(mod, "_write_tsv", boom)
    with pytest.raises(OSError):
        mod.create_home(root, "example")
    assert not root.exists()


def test_register_write_never_truncates_an_existing_file(tmp_path):
    target = tmp_path / "r.tsv"
    target.write_text("user rows\n")
    with pytest.raises(FileExistsError):
        mod._write_tsv(target, ("a", "b"))
    assert target.read_text() == "user rows\n"
