"""Selected archive-member admission only; never invoke planner or tools."""
import hashlib
import importlib.util
import os
from pathlib import Path
import stat
import sys
import warnings
import zipfile
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("planner_zip_candidate", ROOT / "tools/plan_gtotree_iqtree.py")
tool = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = tool
spec.loader.exec_module(tool)
NAME = "software.fna"
PAYLOAD = b">software_fixture\nAC\n"


def row(path, member=NAME):
    return tool.PanelRow("QUERY", "SOFTWARE", "SOFTWARE", "software", str(path), member, "", 0, "software fixture", 2)


def archive(path, entries):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Duplicate name")
        with zipfile.ZipFile(path, "w") as handle:
            for name, mode, data in entries:
                info = zipfile.ZipInfo(name)
                info.create_system = 3
                info.external_attr = mode << 16
                handle.writestr(info, data)


def read(path, member=NAME):
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    try:
        return tool._read_local_assembly(row(path, member))
    finally:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("name,mode", [(NAME, mode) for mode in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFBLK, stat.S_IFSOCK, stat.S_IFDIR)] + [("__MACOSX/software.fna", stat.S_IFREG), ("._software.fna", stat.S_IFREG), (".DS_Store", stat.S_IFREG), ("directory/", stat.S_IFDIR)])
def test_nondata_member_refused_before_payload_read(tmp_path, monkeypatch, name, mode):
    path = tmp_path / "input.zip"
    archive(path, [(name, mode | 0o600, PAYLOAD)])
    reads = []
    original = zipfile.ZipFile.read
    def tracked(self, member, *args, **kwargs):
        reads.append(member.filename if isinstance(member, zipfile.ZipInfo) else member)
        return original(self, member, *args, **kwargs)
    monkeypatch.setattr(zipfile.ZipFile, "read", tracked)
    refused = False
    try:
        read(path, name)
    except ValueError as error:
        refused = True
        assert "ARCHIVE_MEMBER_NOT_REGULAR_DATA" in str(error)
    assert refused and not reads, {"refused": refused, "reads": reads}


@pytest.mark.parametrize("earlier,final", [(stat.S_IFREG, stat.S_IFREG), (stat.S_IFLNK, stat.S_IFREG), (stat.S_IFREG, stat.S_IFLNK), (stat.S_IFREG, stat.S_IFIFO)])
def test_final_member_controls_selected_namespace(tmp_path, earlier, final):
    path = tmp_path / "duplicate.zip"
    archive(path, [(NAME, earlier | 0o600, b">older\nTT\n"), (NAME, final | 0o600, PAYLOAD)])
    if final != stat.S_IFREG:
        with pytest.raises(ValueError, match="ARCHIVE_MEMBER_NOT_REGULAR_DATA"):
            read(path)
    else:
        data, meta = read(path)
        assert data == PAYLOAD
        assert meta["archive_member_sha256"] == hashlib.sha256(PAYLOAD).hexdigest()
        assert meta["source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize("mode", [stat.S_IFREG | 0o600, 0])
def test_regular_and_unspecified_type_payload_metadata_unchanged(tmp_path, mode):
    path = tmp_path / "regular.zip"
    archive(path, [(NAME, mode, PAYLOAD)])
    data, meta = read(path)
    assert data == PAYLOAD
    assert meta["source_type"] == "zip_member"
    assert meta["archive_member"] == NAME
    assert meta["archive_member_bytes"] == len(PAYLOAD)
    assert meta["contigs"] == 1 and meta["assembled_nt"] == 2


def test_missing_member_keeps_existing_typed_failure(tmp_path):
    path = tmp_path / "missing.zip"
    archive(path, [(NAME, stat.S_IFREG | 0o600, PAYLOAD)])
    with pytest.raises(FileNotFoundError, match="ARCHIVE_MEMBER_NOT_FOUND"):
        read(path, "absent.fna")


def test_local_file_route_keeps_metadata_and_bytes(tmp_path):
    path = tmp_path / "plain.fna"
    path.write_bytes(PAYLOAD)
    data, meta = read(path, "")
    assert data == PAYLOAD and meta["source_type"] == "local_fasta"


def test_unselected_special_member_does_not_reject_regular_selection(tmp_path):
    path = tmp_path / "mixed.zip"
    archive(path, [("unselected.fna", stat.S_IFLNK | 0o600, b"target"), (NAME, stat.S_IFREG | 0o600, PAYLOAD)])
    data, meta = read(path)
    assert data == PAYLOAD and meta["archive_member"] == NAME
