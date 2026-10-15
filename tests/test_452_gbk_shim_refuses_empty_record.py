"""Without biopython, the built-in GenBank shim refuses a record with no sequence and no numeric LOCUS length, as
Biopython does, so a corrupt GBK is counted as errored instead of becoming a 0 bp record and a "complete" package.
Found on Linux without biopython (14 Oct 2026). Synthetic data only."""
import io
import warnings
import zipfile

import pytest

import mamey.parsers as parsers
from mamey._gbk_shim import parse_genbank_text

GARBAGE = "LOCUS       broken\nthis is not a GenBank record\n//\n"
GOOD = ("LOCUS       NODE_1                   12 bp    DNA     linear   BCT 01-JAN-2026\n"
        "FEATURES             Location/Qualifiers\n     source          1..12\n"
        "ORIGIN\n        1 atgaaaccct ag\n//\n")
LENGTH_ONLY = "LOCUS       NODE_3                   30 bp    DNA     linear   BCT 01-JAN-2026\n//\n"


def test_garbage_record_is_refused():
    with pytest.raises(ValueError, match="GBK_SHIM_NO_SEQUENCE"):
        parse_genbank_text(GARBAGE)


def test_good_record_still_parses():
    (rec,) = parse_genbank_text(GOOD)
    assert rec.id == "NODE_1" and str(rec.seq).lower() == "atgaaaccctag"


def test_length_only_record_keeps_its_n_sequence():
    (rec,) = parse_genbank_text(LENGTH_ONLY)
    assert len(rec.seq) == 30 and set(rec.seq) == {"N"}


def test_read_genbank_records_counts_the_corrupt_file_as_errored_without_biopython(tmp_path, monkeypatch):
    monkeypatch.setattr(parsers, "_require_seqio", lambda: None)
    zp = tmp_path / "a.zip"
    with zipfile.ZipFile(zp, "w") as zf:
        zf.writestr("r/NODE_1.region001.gbk", GOOD)
        zf.writestr("r/NODE_2.region001.gbk", GARBAGE)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        recs = parsers.read_genbank_records(zp)
    assert [r.id for _, r in recs] == ["NODE_1"]
    assert any("errored" in str(w.message) and "NODE_2" in str(w.message) for w in caught)
