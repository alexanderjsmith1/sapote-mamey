"""Narrow v9.7.396 owner contract for the six held fail-open JSON writers."""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _wbio


def _debris(directory: Path) -> list[Path]:
    return sorted(directory.glob(".*.tmp"))


def test_owned_writer_orders_file_fsync_before_replace_and_parent_fsync_after(
    tmp_path, monkeypatch
):
    destination = tmp_path / "private.json"
    destination.write_text('{"old": true}', encoding="utf-8")
    os.chmod(destination, 0o600)
    events = []
    real_fsync = _wbio.os.fsync
    real_replace = _wbio.os.replace

    def tracking_fsync(fd):
        kind = "dir" if stat.S_ISDIR(os.fstat(fd).st_mode) else "file"
        events.append(f"fsync:{kind}")
        return real_fsync(fd)

    def tracking_replace(source, target):
        events.append("replace")
        return real_replace(source, target)

    monkeypatch.setattr(_wbio.os, "fsync", tracking_fsync)
    monkeypatch.setattr(_wbio.os, "replace", tracking_replace)
    _wbio.atomic_dump_json_owned({"new": True}, destination, owner_dir=tmp_path, indent=1)

    assert events == ["fsync:dir", "fsync:file", "replace", "fsync:dir"]
    assert json.loads(destination.read_text(encoding="utf-8")) == {"new": True}
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert not _debris(tmp_path)


def test_owned_writer_uses_unique_private_sibling_stages(tmp_path, monkeypatch):
    seen = []
    real_mkstemp = _wbio.tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, name = real_mkstemp(*args, **kwargs)
        seen.append((Path(name), stat.S_IMODE(os.fstat(fd).st_mode)))
        return fd, name

    monkeypatch.setattr(_wbio.tempfile, "mkstemp", tracking_mkstemp)
    destination = tmp_path / "out.json"
    _wbio.atomic_dump_json_owned({"n": 1}, destination, owner_dir=tmp_path)
    _wbio.atomic_dump_json_owned({"n": 2}, destination, owner_dir=tmp_path)

    assert len({path.name for path, _ in seen}) == 2
    assert all(path.parent == tmp_path and mode == 0o600 for path, mode in seen)
    assert not _debris(tmp_path)


def test_serialization_and_replace_failures_preserve_prior_and_clean_stage(tmp_path, monkeypatch):
    destination = tmp_path / "out.json"
    destination.write_text('{"prior": true}', encoding="utf-8")

    with pytest.raises(TypeError):
        _wbio.atomic_dump_json_owned({"bad": {1}}, destination, owner_dir=tmp_path)
    assert json.loads(destination.read_text(encoding="utf-8")) == {"prior": True}
    assert not _debris(tmp_path)

    def refusing_replace(source, target):
        raise OSError("simulated rename refusal")

    monkeypatch.setattr(_wbio.os, "replace", refusing_replace)
    with pytest.raises(OSError, match="simulated rename refusal"):
        _wbio.atomic_dump_json_owned({"new": True}, destination, owner_dir=tmp_path)
    assert json.loads(destination.read_text(encoding="utf-8")) == {"prior": True}
    assert not _debris(tmp_path)


def test_containment_symlink_and_preflight_refusals_create_nothing(tmp_path, monkeypatch):
    owner = tmp_path / "owner"
    escape = tmp_path / "escape"
    owner.mkdir()
    escape.mkdir()

    outside = escape / "out.json"
    with pytest.raises(_wbio.AtomicJsonWriteRefused, match="direct child"):
        _wbio.atomic_dump_json_owned({"x": 1}, outside, owner_dir=owner)
    assert not outside.exists() and not _debris(owner) and not _debris(escape)

    target = escape / "target.json"
    target.write_text('{"keep": true}', encoding="utf-8")
    symlink_destination = owner / "link.json"
    try:
        symlink_destination.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(_wbio.AtomicJsonWriteRefused, match="regular file"):
        _wbio.atomic_dump_json_owned({"x": 2}, symlink_destination, owner_dir=owner)
    assert json.loads(target.read_text(encoding="utf-8")) == {"keep": True}
    assert symlink_destination.is_symlink() and not _debris(owner)

    new_destination = owner / "never-created.json"

    def no_directory_fsync(fd):
        raise OSError("directory fsync unavailable")

    monkeypatch.setattr(_wbio.os, "fsync", no_directory_fsync)
    with pytest.raises(_wbio.AtomicJsonWriteRefused, match="required fsync"):
        _wbio.atomic_dump_json_owned({"x": 3}, new_destination, owner_dir=owner)
    assert not new_destination.exists() and not _debris(owner)


def test_postrename_directory_fsync_failure_is_typed_and_reports_publication(tmp_path, monkeypatch):
    destination = tmp_path / "out.json"
    real_fsync = _wbio.os.fsync
    directory_fsync_count = 0

    def fail_second_directory_fsync(fd):
        nonlocal directory_fsync_count
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            directory_fsync_count += 1
            if directory_fsync_count == 2:
                raise OSError("simulated post-rename durability failure")
        return real_fsync(fd)

    monkeypatch.setattr(_wbio.os, "fsync", fail_second_directory_fsync)
    with pytest.raises(_wbio.AtomicJsonDurabilityError) as raised:
        _wbio.atomic_dump_json_owned({"published": True}, destination, owner_dir=tmp_path)

    assert raised.value.destination_published is True
    assert json.loads(destination.read_text(encoding="utf-8")) == {"published": True}
    assert not _debris(tmp_path)


def test_exact_six_consumers_bind_to_owned_writer_without_touching_text_writer_family():
    consumers = [
        "deliverable_tools/backfill_coords_from_antismash.py",
        "deliverable_tools/enrich_swissprot.py",
        "deliverable_tools/enrich_clusterblast.py",
        "deliverable_tools/roster_v2.py",
        "tools/phylo_postflight.py",
        "tools/phylo_preflight.py",
    ]
    for relative in consumers:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "atomic_dump_json_owned as _atomic_write_json" in source, relative
        assert "owner_dir=" in source, relative
        assert "json.dump(rep.items, open(" not in source, relative
        assert "json.dump(roster, open(" not in source, relative
        assert "json.dump(cohort, open(" not in source, relative
        assert "json.dump(r, open(" not in source, relative

    assert not (ROOT / "mamey/io_utils.py").exists()
