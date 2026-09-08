"""test_judgment_dir_split.py — tests for F2 (Opus findings, v9.7.149c).

Splits `_judgment_dir()` into explicit read/write variants so a read-side
probe (e.g. compile_report's narrative-section existence check) doesn't
silently create an empty `judgment/` directory.

Fixtures use AS-XXX only.
"""
from __future__ import annotations

import json
import pathlib

import pytest


def _bare_pkg(tmp_path: pathlib.Path,
              strain_id: str = "AS-XXX") -> pathlib.Path:
    pkg = tmp_path / strain_id / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": strain_id}))
    (pkg / "manifest_short.json").write_text(json.dumps(
        {"strain_id": strain_id}))
    return pkg


def test_judgment_dir_read_does_not_mkdir(tmp_path):
    from mamey.judgment_store import _judgment_dir_read
    pkg = _bare_pkg(tmp_path)
    path = _judgment_dir_read(pkg)
    assert path == pkg / "judgment"
    assert not path.exists(), "_judgment_dir_read must not create the dir"


def test_judgment_dir_write_does_mkdir(tmp_path):
    from mamey.judgment_store import _judgment_dir_write
    pkg = _bare_pkg(tmp_path)
    path = _judgment_dir_write(pkg)
    assert path == pkg / "judgment"
    assert path.is_dir(), "_judgment_dir_write must create the dir"


def test_judgment_dir_write_is_idempotent(tmp_path):
    from mamey.judgment_store import _judgment_dir_write
    pkg = _bare_pkg(tmp_path)
    _judgment_dir_write(pkg)
    _judgment_dir_write(pkg)  # second call must not raise
    assert (pkg / "judgment").is_dir()


def test_judgment_dir_backcompat_alias_still_mkdirs(tmp_path):
    """External callers that imported _judgment_dir directly must still see
    the historical mkdir-on-call behaviour."""
    from mamey.judgment_store import _judgment_dir
    pkg = _bare_pkg(tmp_path)
    _judgment_dir(pkg)
    assert (pkg / "judgment").is_dir()


def test_path_helpers_no_longer_have_side_effects(tmp_path):
    """`_mode_b_path`, `_laypersons_path`, `_fermentation_path` should now
    use the read variant — calling them must NOT create `judgment/`."""
    from mamey.judgment_store import (
        _mode_b_path, _laypersons_path, _fermentation_path,
    )
    pkg = _bare_pkg(tmp_path)
    _mode_b_path(pkg, "BGC001")
    _laypersons_path(pkg)
    _fermentation_path(pkg)
    assert not (pkg / "judgment").exists(), (
        "path helpers must not create judgment/ as a side effect"
    )


def test_compile_report_probe_leaves_judgment_untouched(tmp_path):
    """Highest-impact regression: compile_report.build_report on a package
    without a judgment/ dir must not create one as a side effect of probing
    the narrative-section paths."""
    from mamey import compile_report
    pkg = _bare_pkg(tmp_path)
    compile_report.build_report(pkg, generate_figures=False)
    assert not (pkg / "judgment").exists(), (
        "compile_report probe created judgment/ as a side effect — F2 broken"
    )


def test_writer_creates_judgment_dir_on_demand(tmp_path):
    """`_append_section` and `_atomic_write_text` must mkdir the parent so
    callers don't need to know about the split."""
    from mamey.judgment_store import _append_section, _mode_b_path
    pkg = _bare_pkg(tmp_path)
    mb = _mode_b_path(pkg, "BGC001")
    assert not (pkg / "judgment").exists()
    _append_section(mb, "test content")
    assert (pkg / "judgment").is_dir()
    assert mb.exists()
    assert "test content" in mb.read_text(encoding="utf-8")
