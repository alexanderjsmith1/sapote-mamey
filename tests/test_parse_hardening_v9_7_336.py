"""Regression tests for the v9.7.336 parse-hardening fixes.

PARSE-01: multi-line /translation qualifiers must be concatenated with NO interior
          whitespace (the GBK-shim continuation join uses a literal space).
PARSE-02: a bare ">" FASTA header must not raise IndexError.
"""
import io
import zipfile
from pathlib import Path

from mamey._gbk_shim import _parse_qualifiers
from mamey.parsers import read_fasta_sequences_from_zip, read_genbank_records

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "micromonospora_humida_JAFEUC01.zip"


def test_parse01_translation_has_no_whitespace_unit():
    """A /translation split across continuation lines collapses to a gap-free sequence."""
    lines = [
        '                     /gene="foo"',
        '                     /translation="MKTAYIAKQR QISFVKSHFS',
        '                     RQLEERLGLI EVQAPILSRV GDGTQDNLSG',
        '                     AEKAVQVKVK ALPDAQFEVV HSLAKWKR"',
    ]
    q = _parse_qualifiers(lines)
    (val,) = q["translation"]
    assert " " not in val
    assert "\t" not in val
    assert val.startswith("MKTAYIAKQRQISFVKSHFS")
    # A descriptive qualifier keeps its spaces (only translation is collapsed).
    assert q["gene"] == ["foo"]


def test_parse01_translation_gap_free_from_fixture():
    """Every /translation parsed out of the shipped region GBKs is whitespace-free."""
    n_seen = 0
    for _name, rec in read_genbank_records(FIXTURE, region_only=False):
        for feat in rec.features:
            for val in feat.qualifiers.get("translation", []):
                n_seen += 1
                assert " " not in val and "\t" not in val and "\n" not in val
    assert n_seen > 0  # fixture actually exercised the path


def test_parse02_bare_gt_header_does_not_raise():
    """A bare '>' header line is tolerated (no IndexError) and gets a placeholder id."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("bare.fasta", ">\nACGTACGT\n>c2 with desc\nTTTT\n")
    buf.seek(0)
    tmp = Path(__file__).resolve().parent / "fixtures" / "_parse02_tmp.zip"
    tmp.write_bytes(buf.getvalue())
    try:
        seqs = read_fasta_sequences_from_zip(tmp)  # must not raise
    finally:
        tmp.unlink(missing_ok=True)
    assert "ACGTACGT" in seqs.values()
    assert seqs.get("c2") == "TTTT"
    # the bare header still produced a record under a synthesized id
    assert any(k.startswith("unnamed_") for k in seqs)
