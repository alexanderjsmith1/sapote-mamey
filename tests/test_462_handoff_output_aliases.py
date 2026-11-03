"""DREL-036: handoff output and temporary paths never alias or consume a source."""
import json
import os
import zipfile

import pytest

from mamey.handoff import build_handoff


def _package(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SYN-1"}))
    (pkg / "SYN-1_2_inventory.csv").write_text("BGC_ID,Contig,Region\n")
    return pkg


def _input_zip(path):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("SYN.region001.gbk", "LOCUS SYN\n")
    return path


def test_output_equal_to_input_zip_is_refused(tmp_path):
    pkg = _package(tmp_path)
    src = _input_zip(tmp_path / "input.zip")
    before = src.read_bytes()
    with pytest.raises(ValueError, match="aliases a source"):
        build_handoff(pkg, src, src)
    assert src.read_bytes() == before


def test_input_at_old_temp_sibling_is_not_removed(tmp_path):
    pkg = _package(tmp_path)
    src = _input_zip(tmp_path / "handoff.zip.tmp")
    before = src.read_bytes()
    build_handoff(pkg, src, tmp_path / "handoff.zip")
    assert src.read_bytes() == before


def test_output_inside_package_is_refused(tmp_path):
    pkg = _package(tmp_path)
    inventory = pkg / "SYN-1_2_inventory.csv"
    before = inventory.read_bytes()
    with pytest.raises(ValueError, match="outside the package"):
        build_handoff(pkg, None, inventory)
    assert inventory.read_bytes() == before


def test_hardlinked_output_is_refused(tmp_path):
    pkg = _package(tmp_path)
    src = _input_zip(tmp_path / "input.zip")
    link = tmp_path / "out.zip"
    os.link(src, link)
    with pytest.raises(ValueError, match="aliases a source"):
        build_handoff(pkg, src, link)


def test_fresh_destination_still_works_and_leaves_no_temp(tmp_path):
    pkg = _package(tmp_path)
    src = _input_zip(tmp_path / "input.zip")
    out = tmp_path / "out" / "handoff.zip"
    out.parent.mkdir()
    res = build_handoff(pkg, src, out)
    assert res["region_gbks"] == 1
    assert zipfile.ZipFile(out).testzip() is None
    assert [p.name for p in out.parent.iterdir()] == ["handoff.zip"]
