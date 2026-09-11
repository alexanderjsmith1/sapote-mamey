from __future__ import annotations

import zipfile
from argparse import Namespace
from pathlib import Path

from mamey.package_inspector import classify_antismash_zip, inspect_command


def _single_region_zip(path: Path) -> Path:
    gbk = '''LOCUS       KY089035.1              10000 bp    DNA     linear   BCT 01-JAN-2020
DEFINITION  synthetic single-region antiSMASH fixture.
SOURCE      Streptomyces ahygroscopicus
  ORGANISM  Streptomyces ahygroscopicus
COMMENT     antiSMASH 8.0.4
FEATURES             Location/Qualifiers
ORIGIN
        1 atgc
//
'''
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("index.html", "<html>antiSMASH</html>")
        zf.writestr("regions.js", "var regions = [];")
        zf.writestr("KY089035.1.json", "{}")
        zf.writestr("KY089035.1.gbk", gbk)
        zf.writestr("KY089035.1.region001.gbk", gbk)
        zf.writestr("clusterblast/KY089035.1_c1.txt", "ClusterBlast fixture")
        zf.writestr("knownclusterblast/region1/ARA90604.1.txt", "KnownClusterBlast fixture")
        zf.writestr("subclusterblast/region1/dummy.txt", "SubClusterBlast fixture")
    return path


def test_classify_single_region_accession_zip(tmp_path: Path):
    zpath = _single_region_zip(tmp_path / "KY089035.1.zip")
    with zipfile.ZipFile(zpath) as zf:
        shape = classify_antismash_zip(zf.namelist())
    assert shape["shape"] == "single_region_antismash_accession"
    assert shape["region_gbk_count"] == 1
    assert shape["accession_like"] is True
    assert shape["accession"] == "KY089035.1"
    assert shape["has_knownclusterblast"] is True


def test_inspect_single_region_accession_prints_user_guidance(tmp_path: Path, capsys):
    zpath = _single_region_zip(tmp_path / "KY089035.1.zip")
    rc = inspect_command(Namespace(zip=str(zpath)))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Input shape       : raw antiSMASH single-region accession run" in out
    assert "Public accession  : KY089035.1" in out
    assert "Single-region accession note:" in out
    assert "not a full genome and not a sealed Mamey package" in out
    assert "VERY_POOR / 0% interior" in out
    assert "--mode gold" in out
    assert "--capped-session" in out
    assert "--mode smoke" not in out
    assert "--chatgpt-safe" not in out
