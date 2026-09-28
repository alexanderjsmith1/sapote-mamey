"""Region-only archives: domains and CDS read from region files land on the contig's coordinates.

An antiSMASH archive with no whole-record GenBank file is read from its region files, whose feature coordinates
restart at 1, while BGC bounds come from the same files' `Orig. start`. Without the offset, a region away from its
contig start found none of its own domains or genes (humida JAFEUC010000001.1 / region006 / BGC002 read
"unresolved"), and overlapping local frames credited one region's domains to another.
"""
import zipfile
from pathlib import Path

import pytest

from mamey import parsers
from mamey.class_architecture import derive_architecture

FIX = Path(__file__).resolve().parent / "fixtures"


@pytest.mark.parametrize("name", ["micromonospora_humida_JAFEUC01.zip", "rggmci_public_VWPH00000000.1_subset.zip"])
def test_every_feature_falls_inside_exactly_its_own_region(name):
    z = FIX / name
    bgcs = parsers.parse_bgcs_from_zip(z, json_mode="off")
    for feats in (parsers.extract_domain_features(z), parsers.extract_cds_features(z)):
        assert feats
        for f in feats:
            hosts = [b for b in bgcs if b.contig == f.contig and b.start <= f.start and f.end <= b.end]
            assert len(hosts) == 1, (name, f.contig, f.start, f.end, [b.bgc_id for b in hosts])


def test_humida_nrps_region_sees_its_own_domains():
    z = FIX / "micromonospora_humida_JAFEUC01.zip"
    bgcs = {b.antismash_region: b for b in parsers.parse_bgcs_from_zip(z, json_mode="off")}
    call = derive_architecture(bgcs["region006"], parsers.extract_cds_features(z), parsers.extract_domain_features(z))
    assert "unresolved" not in call.capacity


def test_archives_with_whole_record_files_get_no_offset(tmp_path):
    z = tmp_path / "whole.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("ctg1.gbk", "LOCUS       ctg1 10 bp DNA\n//\n")
        zf.writestr("ctg1.region001.gbk", "LOCUS       ctg1 10 bp DNA\nCOMMENT     Orig. start :: 500\n"
                                          "            Orig. end :: 510\n//\n")
    assert parsers._region_record_offsets(z) == {}
