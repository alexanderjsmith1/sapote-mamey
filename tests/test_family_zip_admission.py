"""Effective archive namespace controls; no alignment or sequence analysis."""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import warnings
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("family_candidate", ROOT / "tools/family_rarity_by_window.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
NAME = "software_contig.region001.gbk"
PAYLOAD = b"LOCUS       SOFTWARE_ONLY\nORIGIN\n//\n"


def write_zip(path, entries):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Duplicate name")
        with zipfile.ZipFile(path, "w") as archive:
            for name, mode, payload in entries:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                archive.writestr(info, payload)


def checked_read(path, **kwargs):
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        return tool.read_regions(str(path), **kwargs)
    finally:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("mode", [stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFSOCK, stat.S_IFDIR])
def test_special_member_is_not_region_data(tmp_path, monkeypatch, mode):
    path = tmp_path / "special.zip"
    write_zip(path, [(NAME, mode | 0o600, b"software target")])
    reads = []
    real_read = zipfile.ZipFile.read
    def tracked_read(self, name, *args, **kwargs):
        reads.append(name)
        return real_read(self, name, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "read", tracked_read)
    refused = False
    try:
        checked_read(path)
    except tool.Refusal:
        refused = True
    assert refused and not reads, {"refused": refused, "payload_reads": reads}


@pytest.mark.parametrize("earlier_mode, final_mode, expected", [
    (stat.S_IFREG, stat.S_IFREG, 1),
    (stat.S_IFLNK, stat.S_IFREG, 1),
    (stat.S_IFREG, stat.S_IFLNK, 0),
])
def test_duplicate_name_uses_effective_final_member_once(tmp_path, earlier_mode, final_mode, expected):
    path = tmp_path / "duplicate.zip"
    write_zip(path, [(NAME, earlier_mode | 0o600, b"older entry"), (NAME, final_mode | 0o600, PAYLOAD)])
    if not expected:
        with pytest.raises(tool.Refusal):
            checked_read(path)
    else:
        rows = checked_read(path)
        assert len(rows) == expected
        assert [r["index"] for r in rows] == [0]
        reference = tmp_path / "final_only.zip"
        write_zip(reference, [(NAME, final_mode | 0o600, PAYLOAD)])
        assert rows == checked_read(reference)


def test_duplicate_does_not_create_a_second_selectable_index(tmp_path):
    path = tmp_path / "duplicate.zip"
    write_zip(path, [(NAME, stat.S_IFREG | 0o600, PAYLOAD)] * 2)
    with pytest.raises(tool.Refusal, match="region-index"):
        checked_read(path, only=1)


@pytest.mark.parametrize("mode", [stat.S_IFREG | 0o600, 0])
def test_regular_and_unspecified_type_members_keep_sorted_selection(tmp_path, mode):
    path = tmp_path / "ordinary.zip"
    write_zip(path, [("z_software.region002.gbk", mode, PAYLOAD), ("a_software.region001.gbk", mode, PAYLOAD)])
    rows = checked_read(path)
    assert [r["contig"] for r in rows] == ["a_software", "z_software"]
    assert [r["index"] for r in rows] == [0, 1]
    assert len(checked_read(path, only=1)) == 1


def test_metadata_and_special_entries_do_not_shift_real_index(tmp_path):
    path = tmp_path / "mixed.zip"
    write_zip(path, [("__MACOSX/side.region001.gbk", stat.S_IFREG | 0o600, PAYLOAD), ("._hidden.region001.gbk", stat.S_IFREG | 0o600, PAYLOAD), ("a_symlink.region001.gbk", stat.S_IFLNK | 0o600, b"target"), (NAME, stat.S_IFREG | 0o600, PAYLOAD)])
    rows = checked_read(path, only=0)
    assert len(rows) == 1
    assert rows[0]["contig"] == "software_contig"
