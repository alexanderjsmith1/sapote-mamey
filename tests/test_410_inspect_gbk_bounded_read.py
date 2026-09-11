"""The public ``inspect`` front door must not fully decompress a region GBK.

The parser owns the GBK size policy.  These tests pin that package_inspector
uses that policy before its direct version-header probe and reads only a small
prefix through ``ZipFile.open``.
"""
from __future__ import annotations

import argparse
import zipfile

import pytest

from mamey.package_inspector import inspect_command


GBK = """LOCUS       NODE_1                 1000 bp    DNA     linear   BCT 01-JAN-2026
COMMENT     ##antiSMASH-Data-START##
            Version      :: 8.0.4
            ##antiSMASH-Data-END##
FEATURES             Location/Qualifiers
     region          1..1000
ORIGIN
//
"""


def _archive(tmp_path, *, padding=0):
    path = tmp_path / "input.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("NODE_1.region001.gbk", GBK + ("A" * padding))
        zf.writestr("results.json", '{"version":"8.0.4"}')
    return path


def _watch_full_member_reads(monkeypatch):
    original = zipfile.ZipFile.read
    region_reads = []

    def watched(self, name, *args, **kwargs):
        member = getattr(name, "filename", name)
        if str(member).lower().endswith(".gbk"):
            region_reads.append(str(member))
        return original(self, name, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "read", watched)
    return region_reads


def test_inspect_reads_region_version_header_without_zipfile_read(tmp_path, monkeypatch, capsys):
    archive = _archive(tmp_path)
    region_reads = _watch_full_member_reads(monkeypatch)

    assert inspect_command(argparse.Namespace(zip=str(archive))) == 0

    captured = capsys.readouterr()
    assert "antiSMASH version : 8.0.4" in captured.out
    assert region_reads == []


def test_inspect_preflights_gbk_size_guard_before_header_read(tmp_path, monkeypatch, capsys):
    archive = _archive(tmp_path, padding=4096)
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    region_reads = _watch_full_member_reads(monkeypatch)

    with pytest.warns(
        RuntimeWarning,
        match=r"GBK_SIZE_GUARD_REFUSED: NODE_1\.region001\.gbk",
    ):
        assert inspect_command(argparse.Namespace(zip=str(archive))) == 0

    capsys.readouterr()
    assert region_reads == []
