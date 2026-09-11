"""Version-prefix readers must share the canonical archive resource guard."""
from __future__ import annotations

import argparse
import zipfile

import pytest

from mamey.package_inspector import inspect_command
from mamey.parsers import extract_antismash_version


def _archive(path, *, gbk: bytes, json_data: bytes):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as zf:
        zf.writestr("NODE_1.region001.gbk", gbk)
        zf.writestr("results.json", json_data)
    return path


def _gbk(version: str, padding: int = 0) -> bytes:
    return (
        "LOCUS       NODE_1                 1000 bp    DNA     linear   BCT 01-JAN-2026\n"
        "COMMENT     ##antiSMASH-Data-START##\n"
        f"            Version      :: {version}\n"
        "            ##antiSMASH-Data-END##\n"
        "FEATURES             Location/Qualifiers\n"
        "     region          1..1000\n"
        "ORIGIN\n//\n"
        + ("A" * padding)
    ).encode()


def _watch_member_reads(monkeypatch):
    original = zipfile.ZipExtFile.read
    reads = []

    def watched(self, n=-1, *args, **kwargs):
        data = original(self, n, *args, **kwargs)
        reads.append((str(getattr(self, "name", "?")), n, len(data)))
        return data

    monkeypatch.setattr(zipfile.ZipExtFile, "read", watched)
    return reads


def test_overcap_json_prefix_is_refused_without_open_or_retry(tmp_path, monkeypatch):
    archive = _archive(
        tmp_path / "overcap-json.zip",
        gbk=_gbk("8.0.4", padding=2048),
        json_data=b'{"version":"9.9.9","padding":"' + (b"B" * 2048) + b'"}',
    )
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    reads = _watch_member_reads(monkeypatch)

    with pytest.warns(RuntimeWarning, match="GBK_SIZE_GUARD_REFUSED"):
        assert extract_antismash_version(archive) is None

    assert reads == [], "a refused JSON or GBK member must never be opened or retried"


def test_inspect_does_not_reopen_refused_gbk_and_keeps_dev_version(
    tmp_path, monkeypatch, capsys
):
    archive = _archive(
        tmp_path / "refused-gbk.zip",
        gbk=_gbk("8.dev-full", padding=2048),
        json_data=b'{"version":"8.dev"}',
    )
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "512")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    reads = _watch_member_reads(monkeypatch)

    with pytest.warns(RuntimeWarning, match="GBK_SIZE_GUARD_REFUSED") as caught:
        assert inspect_command(argparse.Namespace(zip=str(archive))) == 0

    captured = capsys.readouterr()
    assert "antiSMASH version : 8.dev" in captured.out
    assert len(caught) == 1
    assert [name for name, _n, _size in reads] == ["results.json"]


def test_admitted_json_prefix_version_detection_is_preserved(tmp_path, monkeypatch):
    archive = _archive(
        tmp_path / "admitted-json.zip",
        gbk=_gbk("8.0.4"),
        json_data=b'{"version":"8.0.4"}',
    )
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "4096")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    reads = _watch_member_reads(monkeypatch)

    assert extract_antismash_version(archive) == "8.0.4"
    assert reads == [("results.json", 4096, len(b'{"version":"8.0.4"}'))]


def test_admitted_gbk_fallback_version_detection_is_preserved(tmp_path, monkeypatch):
    archive = _archive(
        tmp_path / "admitted-gbk.zip",
        gbk=_gbk("8.dev-full"),
        json_data=b'{"metadata":{}}',
    )
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", "4096")
    monkeypatch.setenv("MAMEY_GBK_MAX_RATIO", "100000")
    reads = _watch_member_reads(monkeypatch)

    assert extract_antismash_version(archive) == "8.dev-full"
    names = [name for name, _n, _size in reads]
    assert names.count("NODE_1.region001.gbk") == 1
    assert names.count("results.json") == 2
