"""The auto-emitted Figure Factory replaces only its own folder, and only after a good build.

Before: `<target>/figure_factory` was resolved (following a symlink) and removed with
`shutil.rmtree(..., ignore_errors=True)` before the build. A symlink sent the removal
elsewhere; a failed build after the removal left no figure folder at all.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mamey.cli import _auto_emit_figure_factory
from tests.test_figure_factory_next import _fixture

pytestmark = pytest.mark.slow


def _package(tmp_path):
    cfg = _fixture(tmp_path, output_dir="ignored")
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "figure_factory_next_config.json").write_text(cfg.read_text(encoding="utf-8"), encoding="utf-8")
    return pkg


def test_a_symlinked_folder_is_refused_and_its_target_kept(tmp_path, monkeypatch):
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    pkg = _package(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.txt").write_text("user data\n", encoding="utf-8")
    (pkg / "figure_factory").symlink_to(elsewhere, target_is_directory=True)
    res = _auto_emit_figure_factory(pkg, logger=lambda *a: None, source_dir=pkg)
    assert res["status"] == "SKIPPED_FIGURE_FACTORY_TARGET_IS_SYMLINK"
    assert (elsewhere / "keep.txt").is_file()


def test_a_folder_holding_other_files_is_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    pkg = _package(tmp_path)
    (pkg / "figure_factory").mkdir()
    (pkg / "figure_factory" / "my_notes.txt").write_text("x\n", encoding="utf-8")
    res = _auto_emit_figure_factory(pkg, logger=lambda *a: None, source_dir=pkg)
    assert res["status"] == "SKIPPED_FIGURE_FACTORY_TARGET_HOLDS_OTHER_FILES"
    assert (pkg / "figure_factory" / "my_notes.txt").is_file()


def test_a_failed_rebuild_keeps_the_previous_set(tmp_path, monkeypatch):
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    pkg = _package(tmp_path)
    first = _auto_emit_figure_factory(pkg, logger=lambda *a: None, source_dir=pkg)
    assert first["figure_count"] >= 4
    before = sorted(p.name for p in (pkg / "figure_factory").iterdir())
    import mamey.figure_factory_next as ffn
    def boom(_cfg):
        raise RuntimeError("render failed")
    monkeypatch.setattr(ffn, "build", boom)
    res = _auto_emit_figure_factory(pkg, logger=lambda *a: None, source_dir=pkg)
    assert res["status"] == "SKIPPED_RuntimeError"
    assert sorted(p.name for p in (pkg / "figure_factory").iterdir()) == before
    assert not [p for p in pkg.iterdir() if p.name.startswith(".figure_factory.")]


def test_a_rebuild_replaces_its_own_folder_and_leaves_no_staging(tmp_path, monkeypatch):
    monkeypatch.delenv("MAMEY_FIGURE_FACTORY_CONFIG", raising=False)
    pkg = _package(tmp_path)
    _auto_emit_figure_factory(pkg, logger=lambda *a: None, source_dir=pkg)
    res = _auto_emit_figure_factory(pkg, logger=lambda *a: None, source_dir=pkg)
    assert res["figure_count"] >= 4
    assert (pkg / "figure_factory").is_dir() and not (pkg / "figure_factory").is_symlink()
    assert not [p for p in pkg.iterdir() if p.name.startswith(".figure_factory.")]
    assert res["output_dir"] == str(pkg / "figure_factory")
