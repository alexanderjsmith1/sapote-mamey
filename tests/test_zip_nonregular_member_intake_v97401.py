"""Regression coverage for non-regular antiSMASH ZIP member admission."""
from __future__ import annotations

import stat
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey.antismash_evidence import parse_antismash_evidence
from mamey.antismash_input import identify
from mamey.package_inspector import inspect_command
from mamey.parsers import _zip_has_record_json, read_genbank_records, region_gbk_count
from mamey.ziputil import regular_file_names, safe_extract_all


_GBK = (
    "LOCUS       NODE_1                  120 bp    DNA     linear   BCT 01-JAN-2026\n"
    "FEATURES             Location/Qualifiers\n"
    "     region          1..120\n"
    '                     /product="NRPS"\n'
    "ORIGIN\n"
    "        1 " + ("atgc" * 30) + "\n//\n"
)


def _symlink(name: str) -> zipfile.ZipInfo:
    member = zipfile.ZipInfo(name)
    member.create_system = 3
    member.external_attr = (stat.S_IFLNK | 0o777) << 16
    return member


def test_only_symlink_region_is_not_admitted_as_antismash(tmp_path):
    archive = tmp_path / "symlink-only.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(_symlink("NODE_1_length_120_cov_1.region001.gbk"),
                    "real.region001.gbk")

    info = identify(str(archive))
    assert info.is_antismash is False
    assert info.n_regions == 0
    assert any(w.startswith("NONREGULAR_ZIP_MEMBERS_IGNORED:")
               for w in info.warnings)
    assert region_gbk_count(archive) == 0


def test_only_appledouble_region_is_not_admitted_as_antismash(tmp_path):
    archive = tmp_path / "appledouble-only.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(
            "__MACOSX/results/._NODE_1_length_120_cov_1.region001.gbk",
            _GBK,
        )

    info = identify(str(archive))
    assert info.is_antismash is False
    assert info.n_regions == 0
    assert region_gbk_count(archive) == 0


def test_mixed_archive_parses_only_regular_region(tmp_path):
    archive = tmp_path / "mixed.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("NODE_1_length_120_cov_1.region001.gbk", _GBK)
        zf.writestr(_symlink("NODE_2_length_120_cov_1.region001.gbk"),
                    "NODE_1_length_120_cov_1.region001.gbk")

    with zipfile.ZipFile(archive) as zf:
        assert regular_file_names(zf) == [
            "NODE_1_length_120_cov_1.region001.gbk"]
    assert identify(str(archive)).n_regions == 1
    assert region_gbk_count(archive) == 1
    assert len(read_genbank_records(archive, region_only=True)) == 1


def test_nonregular_json_is_not_evidence(tmp_path):
    archive = tmp_path / "json-link.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("NODE_1_length_120_cov_1.region001.gbk", _GBK)
        zf.writestr(_symlink("results.json"), "real-results.json")

    assert _zip_has_record_json(archive) is False
    evidence = parse_antismash_evidence(archive, json_mode="bounded")
    assert evidence["json_files"] == []


def test_inspect_does_not_count_nonregular_region(tmp_path, capsys):
    archive = tmp_path / "inspect-link.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr(_symlink("NODE_1_length_120_cov_1.region001.gbk"),
                    "real.region001.gbk")

    assert inspect_command(SimpleNamespace(zip=str(archive))) == 1
    assert "no GBK region files" in capsys.readouterr().out


def test_safe_extract_refuses_special_member_before_any_write(tmp_path):
    archive = tmp_path / "extract-link.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("ordinary.txt", "must not be partially extracted")
        zf.writestr(_symlink("linked.txt"), "ordinary.txt")
    destination = tmp_path / "dest"
    destination.mkdir()

    with zipfile.ZipFile(archive) as zf:
        with pytest.raises(ValueError, match="unsafe non-regular zip member"):
            safe_extract_all(zf, destination)
    assert list(destination.iterdir()) == []


def test_duplicate_member_names_are_resolved_for_parsing_and_refused_for_extract(tmp_path):
    archive = tmp_path / "duplicate.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("same.txt", "first")
        zf.writestr("same.txt", "last")

    with zipfile.ZipFile(archive) as zf:
        assert regular_file_names(zf) == ["same.txt"]
        with pytest.raises(ValueError, match="unsafe duplicate zip member path"):
            safe_extract_all(zf, tmp_path / "dest-duplicate")


def test_last_duplicate_entry_controls_regular_member_admission(tmp_path):
    archive = tmp_path / "duplicate-special-last.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("results.json", '{"records": []}')
        zf.writestr(_symlink("results.json"), "real-results.json")

    with zipfile.ZipFile(archive) as zf:
        assert regular_file_names(zf) == []


def test_core_antismash_archive_readers_share_the_regular_member_namespace():
    root = Path(__file__).resolve().parents[1]
    readers = (
        "mamey/antismash_evidence.py",
        "mamey/antismash_input.py",
        "mamey/cli.py",
        "mamey/clusterblast_genes.py",
        "mamey/gene_by_gene.py",
        "mamey/kcb_locusmap.py",
        "mamey/mibig_per_gene.py",
        "mamey/nrps_predictions.py",
        "mamey/package_inspector.py",
        "mamey/parsers.py",
        "mamey/pks_ks_scan.py",
        "mamey/rggmci.py",
    )
    for relative in readers:
        source = (root / relative).read_text(encoding="utf-8")
        assert "regular_file_names" in source, relative
        assert ".namelist()" not in source, relative
