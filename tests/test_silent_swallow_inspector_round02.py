"""Round-2 regressions for inspect version probing and cohort region keys."""

from __future__ import annotations

import argparse
import zipfile

import pytest

from mamey.exact_identity import ExactLocusIdentityError
from mamey.package_inspector import _cohort_locator, inspect_command


def _archive(path):
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("NODE_1_length_1000_cov_1.region001.gbk", "LOCUS       NODE_1\n")
    return path


def test_primary_version_probe_io_failure_is_visible(tmp_path, monkeypatch):
    archive = _archive(tmp_path / "input.zip")
    original = zipfile.ZipFile.getinfo

    def broken_getinfo(self, name):
        if name.endswith(".gbk"):
            raise OSError("member metadata unreadable")
        return original(self, name)

    import mamey.parsers as parsers
    monkeypatch.setattr(zipfile.ZipFile, "getinfo", broken_getinfo)
    monkeypatch.setattr(parsers, "extract_antismash_version", lambda *args, **kwargs: None)

    with pytest.warns(RuntimeWarning, match="ANTISMASH_VERSION_PROBE_UNAVAILABLE"):
        assert inspect_command(argparse.Namespace(zip=str(archive))) == 0


def test_primary_version_probe_unexpected_error_propagates(tmp_path, monkeypatch):
    archive = _archive(tmp_path / "input.zip")
    original = zipfile.ZipFile.getinfo

    def broken_getinfo(self, name):
        if name.endswith(".gbk"):
            raise RuntimeError("unexpected internal failure")
        return original(self, name)

    import mamey.parsers as parsers
    monkeypatch.setattr(zipfile.ZipFile, "getinfo", broken_getinfo)
    monkeypatch.setattr(parsers, "extract_antismash_version", lambda *args, **kwargs: None)

    with pytest.raises(RuntimeError, match="unexpected internal failure"):
        inspect_command(argparse.Namespace(zip=str(archive)))


@pytest.mark.parametrize("region", ["2.5", "not-a-region", "regionXYZ", "0", "-1"])
def test_cohort_locator_rejects_invalid_region_instead_of_emitting_bad_join_key(region):
    with pytest.raises(ExactLocusIdentityError, match="invalid cohort region"):
        _cohort_locator({"Contig": "NODE_1_length_1000_cov_1", "antiSMASH_Region": region})


@pytest.mark.parametrize("region,expected", [("2", "region002"), ("region002", "region002"),
                                               ("REGION2", "region002")])
def test_cohort_locator_keeps_valid_region_forms(region, expected):
    assert _cohort_locator({"Contig": "NODE_1_length_1000_cov_1",
                            "antiSMASH_Region": region}).endswith(expected)
