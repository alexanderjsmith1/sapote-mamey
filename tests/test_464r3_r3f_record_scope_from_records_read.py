"""The GenBank record scope comes from the records actually read, not from member names.

A whole-record file that yields no records (garbage or empty) is WHOLE_RECORD_UNREADABLE, not
WHOLE_RECORD_GENBANK: the reader then reads nothing, and region records are not used in its
place. A bare GenBank file is scoped like the reader reads it. The first-pass report names
the scope next to the KS-like count instead of calling it genome-wide. Synthetic inputs only.
"""
import importlib.util
import warnings
import zipfile
from pathlib import Path

import pytest

from mamey.parsers import genbank_record_scope, read_genbank_records
from tests.test_464r3_r3e_scan_count_scope import RECORD

ROOT = Path(__file__).resolve().parents[1]


def _zip(path, members):
    with zipfile.ZipFile(path, "w") as zf:
        for name, text in members:
            zf.writestr(name, text)
    return path


@pytest.mark.parametrize("whole_text", ["not genbank at all\n", ""])
def test_unreadable_whole_record_is_not_whole_record_scope(tmp_path, whole_text):
    archive = _zip(tmp_path / "a.zip", [("out/genome.gbk", whole_text), ("out/c1.region001.gbk", RECORD)])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert read_genbank_records(archive, exclude_regions=True) == []
        scope = genbank_record_scope(archive)
    assert scope["state"] == "WHOLE_RECORD_UNREADABLE"
    assert "no records" in scope["note"]


def test_scope_uses_records_a_caller_already_read(tmp_path):
    archive = _zip(tmp_path / "a.zip", [("out/genome.gbk", RECORD)])
    assert genbank_record_scope(archive, records=[])["state"] == "WHOLE_RECORD_UNREADABLE"
    assert genbank_record_scope(archive, records=[("out/genome.gbk", object())])["state"] == "WHOLE_RECORD_GENBANK"


def test_region_members_that_yield_nothing_are_not_region_scope(tmp_path):
    archive = _zip(tmp_path / "a.zip", [("out/c1.region001.gbk", "garbage\n")])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        assert genbank_record_scope(archive)["state"] == "NO_RECORDS_READ"


def test_bare_genbank_file_is_scoped_like_the_reader_reads_it(tmp_path):
    whole = tmp_path / "bare_genome.gbk"
    whole.write_text(RECORD)
    assert [name for name, _r in read_genbank_records(whole)] == ["bare_genome.gbk"]
    assert genbank_record_scope(whole)["state"] == "WHOLE_RECORD_GENBANK"
    region = tmp_path / "c1.region001.gbk"
    region.write_text(RECORD)
    assert genbank_record_scope(region)["state"] == "REGION_RECORDS_ONLY"


def test_first_pass_report_names_the_scope_not_genome_wide():
    spec = importlib.util.spec_from_file_location("fps_464r3f", ROOT / "tools/build_first_pass_scans.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    region = {"state": "REGION_RECORDS_ONLY", "note": "region records only, not the genome"}
    text = module._flbr({"flbr": {"genome_wide_ks_like_count": 7, "count_scope": region}})
    assert "Genome-wide" not in text
    assert "record scope: REGION_RECORDS_ONLY" in text and "**7**" in text
    assert "record scope: NOT_BOUND" in module._flbr({"flbr": {"genome_wide_ks_like_count": 7}})
