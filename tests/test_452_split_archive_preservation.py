"""Generated split fixtures: retained archives must survive a later split."""
import importlib.util
import os
from pathlib import Path
import stat
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_split(workspace, monkeypatch):
    assert (ROOT / "BUILD_STAMP.txt").is_file(), "Install this fixture in the identified bundle's tests directory"
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(workspace))
    spec = importlib.util.spec_from_file_location(
        "c10_splitter", ROOT / "tools/blastp_crawl/split_multi_panels.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert Path(module.__file__).resolve() == ROOT / "tools/blastp_crawl/split_multi_panels.py"
    from mamey import path_safety
    assert Path(path_safety.__file__).resolve() == ROOT / "mamey/path_safety.py"
    assert module.BR == workspace / "Blastp RESULTS"
    assert module.ATTIC == module.BR / "_SUPERSEDED_MULTI_PANELS"
    assert not workspace.resolve().is_relative_to(ROOT)
    # Establish a valid outside-bundle premise before any accepted collision refusal.
    path_safety.assert_output_outside_bundle(module.BR, module.__file__)
    return module


def stage(workspace):
    gap = workspace / "Blastp RESULTS/_QUERIES_GAP_FIXTURE_K/FIXTURE/_gap"
    gap.mkdir(parents=True)
    source = gap / "panel.faa"
    raw = b">one\nMTEST\n>two\nMOTHER\n"
    source.write_bytes(raw)
    return gap, raw


def snapshot(root):
    entries = {}
    def walk(directory):
        for p in sorted(directory.iterdir()):
            key = p.relative_to(root).as_posix()
            mode = p.lstat().st_mode
            if stat.S_ISLNK(mode):
                entries[key] = ("symlink", os.readlink(p))
            elif stat.S_ISDIR(mode):
                entries[key] = ("directory",)
                walk(p)
            elif stat.S_ISREG(mode):
                entries[key] = ("file", p.read_bytes())
            else:
                raise AssertionError(f"Unexpected fixture entry: {p}")
    walk(root)
    return entries


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling_symlink"])
def test_existing_archive_refuses_before_split_without_losing_any_bytes(tmp_path, monkeypatch, kind):
    workspace = tmp_path / "workspace"
    gap, raw = stage(workspace)
    archive = workspace / "Blastp RESULTS/_SUPERSEDED_MULTI_PANELS/FIXTURE"
    archive.parent.mkdir(parents=True)
    if kind == "directory":
        archive.mkdir()
        (archive / "previous.faa").write_bytes(b"retained earlier archive\n")
    elif kind == "file":
        archive.write_bytes(b"retained archive identity\n")
    elif kind == "symlink":
        preserved = workspace / "preserved_previous_archive"
        preserved.mkdir()
        (preserved / "previous.faa").write_bytes(b"retained symlink target\n")
        archive.symlink_to(preserved, target_is_directory=True)
    else:
        archive.symlink_to(workspace / "absent_previous_archive", target_is_directory=True)
    assert (gap / "panel.faa").read_bytes() == raw and raw.count(b">") == 2
    before = snapshot(workspace)
    module = load_split(workspace, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["split_multi_panels.py", "--execute"])
    try:
        module.main()
    except (ValueError, OSError):
        # The invariant is no mutation on a collision, including an OS refusal.
        pass
    assert snapshot(workspace) == before, "An archive collision must refuse before new output or history loss"
    assert (gap / "panel.faa").read_bytes() == raw
    if kind in ("symlink", "dangling_symlink"):
        assert archive.is_symlink()


def test_dry_run_with_existing_archive_keeps_all_inputs(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    gap, raw = stage(workspace)
    archive = workspace / "Blastp RESULTS/_SUPERSEDED_MULTI_PANELS/FIXTURE"
    archive.mkdir(parents=True)
    (archive / "previous.faa").write_bytes(b"retained previous\n")
    before = snapshot(workspace)
    module = load_split(workspace, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["split_multi_panels.py"])
    module.main()
    assert snapshot(workspace) == before
    assert (gap / "panel.faa").read_bytes() == raw


def test_new_split_preserves_original_archive_bytes(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    gap, raw = stage(workspace)
    module = load_split(workspace, monkeypatch)
    monkeypatch.setattr(sys, "argv", ["split_multi_panels.py", "--execute"])
    module.main()
    archive = workspace / "Blastp RESULTS/_SUPERSEDED_MULTI_PANELS/FIXTURE/panel.faa"
    assert archive.read_bytes() == raw
    assert not gap.exists()
    singles = sorted((archive.parents[2] / "_QUERIES_GAP_FIXTURE_K/FIXTURE").glob("*/*.faa"))
    assert len(singles) == 2
    qdir = archive.parents[2] / "_QUERIES_GAP_FIXTURE_K/FIXTURE"
    assert {p.relative_to(qdir).as_posix(): p.read_bytes() for p in singles} == {
        "FIXTURE_gapK_p0001/FIXTURE__gapK__one.faa": b">one\nMTEST\n",
        "FIXTURE_gapK_p0002/FIXTURE__gapK__two.faa": b">two\nMOTHER\n",
    }

