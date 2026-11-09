"""`inspect` counts KnownClusterBlast TXT files on their own.

It used to count every TXT with "clusterblast" in its path, so a 62-region archive reported 186
KCB files (KnownClusterBlast + ClusterBlast + SubClusterBlast), and an archive holding only
ClusterBlast output reported KCB as "available".
"""
from __future__ import annotations

import zipfile
from types import SimpleNamespace

import pytest

from mamey import package_inspector as pi


def _zip(tmp_path, members):
    path = tmp_path / "EXAMPLE.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("EXAMPLE.region001.gbk", "LOCUS x\n")
        for name in members:
            zf.writestr(name, "x\n")
    return path


def _inspect(monkeypatch, path, capsys):
    import mamey.parsers as parsers
    monkeypatch.setattr(parsers, "_gbk_size_guard", lambda *a: None)
    monkeypatch.setattr(parsers, "extract_antismash_version", lambda *a, **kw: "8.0.4")
    monkeypatch.setattr("mamey.strain_identity._from_archive", lambda _zip: (None, None))
    rc = pi.inspect_command(SimpleNamespace(zip=str(path)))
    return rc, capsys.readouterr().out


def test_three_clusterblast_kinds_count_as_one_kcb_file(tmp_path, monkeypatch, capsys):
    path = _zip(tmp_path, ["knownclusterblast/region1/c1_mibig_hits.txt",
                           "clusterblast/region1/c1.txt",
                           "subclusterblast/region1/c1.txt"])
    rc, out = _inspect(monkeypatch, path, capsys)
    assert rc == 0
    assert "  KCB TXT files     : 1  (available)" in out
    assert "  Other ClusterBlast TXT : 2  (ClusterBlast and SubClusterBlast; not counted as KCB)" in out


def test_clusterblast_only_archive_reports_kcb_absent(tmp_path, monkeypatch, capsys):
    path = _zip(tmp_path, ["clusterblast/region1/c1.txt"])
    rc, out = _inspect(monkeypatch, path, capsys)
    assert "  KCB TXT files     : 0  (absent — KCB may be blank)" in out
    assert "  Other ClusterBlast TXT : 1" in out


def test_no_clusterblast_output_prints_no_other_line(tmp_path, monkeypatch, capsys):
    path = _zip(tmp_path, [])
    rc, out = _inspect(monkeypatch, path, capsys)
    assert "  KCB TXT files     : 0  (absent — KCB may be blank)" in out
    assert "Other ClusterBlast TXT" not in out
