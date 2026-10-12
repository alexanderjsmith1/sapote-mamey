"""Doctor write-probe preservation and cleanup on isolated synthetic bundle paths.

These checks exercise doctor directly. They do not invoke a release audit or establish release clearance.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pytest
from mamey import cli


@pytest.fixture
def synthetic_bundle(tmp_path, monkeypatch):
    root = tmp_path / "SYNTHETIC_DOCTOR_OUTPUT"
    root.mkdir()
    monkeypatch.setattr(cli, "BUNDLE_ROOT", root)
    monkeypatch.chdir(root)
    return root


def _doctor():
    return cli.doctor_command(argparse.Namespace())


def test_doctor_leaves_no_runs_dir_when_none_pre_existed(synthetic_bundle):
    runs = synthetic_bundle / "runs"
    assert not runs.exists()
    _doctor()
    assert not runs.exists()


def test_doctor_preserves_a_pre_existing_populated_runs_dir(synthetic_bundle):
    marker = synthetic_bundle / "runs" / "SYNTHETIC_DOCTOR_OUTPUT" / "package" / "marker.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("synthetic output must survive", encoding="utf-8")
    _doctor()
    assert marker.read_text() == "synthetic output must survive"
    assert not (synthetic_bundle / "runs" / "_doctor_probe").exists()


def test_doctor_preserves_pre_existing_empty_runs_dir(synthetic_bundle):
    runs = synthetic_bundle / "runs"
    runs.mkdir()
    identity = runs.stat()
    _doctor()
    assert runs.is_dir() and runs.stat().st_ino == identity.st_ino
    assert list(runs.iterdir()) == []


@pytest.mark.parametrize("kind", ["file", "empty_directory", "populated_directory", "symlink", "dangling_symlink"])
def test_occupied_probe_is_refused_without_touching_contents(synthetic_bundle, tmp_path, capsys, kind):
    runs = synthetic_bundle / "runs"; runs.mkdir()
    probe = runs / "_doctor_probe"
    target = tmp_path / "SYNTHETIC_DOCTOR_TARGET"; target.mkdir()
    sentinel = target / "probe.txt"; sentinel.write_bytes(b"synthetic sentinel")
    if kind == "file": probe.write_bytes(b"synthetic occupied probe")
    elif kind in ("empty_directory", "populated_directory"):
        probe.mkdir()
        if kind == "populated_directory": (probe / "probe.txt").write_bytes(b"synthetic occupied contents")
    else: probe.symlink_to(target if kind == "symlink" else tmp_path / "SYNTHETIC_ABSENT", target_is_directory=True)
    before = probe.lstat()
    assert _doctor() == 1
    assert "reserved runs/_doctor_probe is occupied" in capsys.readouterr().out
    assert (probe.lstat().st_dev, probe.lstat().st_ino) == (before.st_dev, before.st_ino)
    assert sentinel.read_bytes() == b"synthetic sentinel"
    if kind == "file": assert probe.read_bytes() == b"synthetic occupied probe"
    if kind == "populated_directory": assert (probe / "probe.txt").read_bytes() == b"synthetic occupied contents"
    if kind == "empty_directory": assert list(probe.iterdir()) == []
    if kind.endswith("symlink"): assert probe.is_symlink()


@pytest.mark.parametrize("dangling", [False, True])
def test_symlink_runs_is_refused_without_target_writes(synthetic_bundle, tmp_path, dangling):
    target = tmp_path / "SYNTHETIC_RUNS_TARGET"
    if not dangling: target.mkdir()
    runs = synthetic_bundle / "runs"; runs.symlink_to(target, target_is_directory=True)
    assert _doctor() == 1
    assert runs.is_symlink()
    assert not (target / "_doctor_probe").exists()
    assert target.exists() is (not dangling)


def test_probe_directory_race_preserves_unowned_sentinel(synthetic_bundle, monkeypatch):
    runs = synthetic_bundle / "runs"; runs.mkdir()
    probe = runs / "_doctor_probe"
    original = Path.mkdir
    def raced(path, *args, **kwargs):
        if path == probe:
            original(path)
            (path / "probe.txt").write_bytes(b"synthetic racing sentinel")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "mkdir", raced)
    assert _doctor() == 1
    assert (probe / "probe.txt").read_bytes() == b"synthetic racing sentinel"


def test_probe_file_race_preserves_unowned_sentinel(synthetic_bundle, monkeypatch):
    probe_file = synthetic_bundle / "runs" / "_doctor_probe" / "probe.txt"
    original = Path.open
    def raced(path, *args, **kwargs):
        if path == probe_file and args and args[0] == "x":
            with original(path, "wb") as stream: stream.write(b"synthetic racing file")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", raced)
    assert _doctor() == 1
    assert probe_file.read_bytes() == b"synthetic racing file"


def test_write_failure_cleans_only_owned_paths(synthetic_bundle, monkeypatch):
    probe_file = synthetic_bundle / "runs" / "_doctor_probe" / "probe.txt"
    original = Path.open
    def refused(path, *args, **kwargs):
        if path == probe_file and args and args[0] == "x": raise PermissionError("synthetic write refusal")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "open", refused)
    assert _doctor() == 1
    assert not (synthetic_bundle / "runs").exists()
