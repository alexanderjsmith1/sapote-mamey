"""test_parsers_failed_gbk_warning.py — read_genbank_records surfaces skipped GBKs.

A malformed GBK inside an antiSMASH zip must not abort parsing of the others
(resilience), but the skip must no longer be silent: a warning is emitted naming
the count, so a downstream BGC-count mismatch is traceable to the parse failure.
"""
import io
import warnings
import zipfile

import pytest

from mamey.parsers import read_genbank_records, _require_seqio

_SEQIO_AVAILABLE = _require_seqio() is not None


_GOOD_GBK = """\
LOCUS       NODE_1                   60 bp    DNA     linear   BCT 01-JAN-2026
FEATURES             Location/Qualifiers
     source          1..60
                     /organism="Streptomyces sp."
     CDS             1..60
                     /locus_tag="NODE_1_CDS1"
                     /product="hypothetical protein"
ORIGIN
        1 atgaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaaaa aaaaaaaata
//
"""

# Non-numeric LOCUS length + an unparseable join() coordinate forces a real
# exception in the GenBank parser (not just a tolerant warning), exercising the
# except/continue (errored) path.
_BAD_GBK = """\
LOCUS       NODE_2   not_a_number bp DNA linear BCT
FEATURES             Location/Qualifiers
     CDS             complement(join(abc..xyz))
ORIGIN
//
"""

# A structurally-recognizable-but-empty member: the parser yields ZERO records
# without raising. This is the more insidious silent-drop path — the one a real
# strain verification run exposed that a raise-only fixture missed.
_EMPTY_GBK = "not a genbank record at all\njust some text\n"


def _make_zip(members: dict[str, str]) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, text in members.items():
            zf.writestr(name, text)
    buf.seek(0)
    return buf


@pytest.mark.xfail(
    not _SEQIO_AVAILABLE,
    reason=(
        "_gbk_shim is intentionally permissive and parses this GBK without raising; "
        "the 'errored' warning path requires BioPython's strict parser"
    ),
    strict=True,
)
def test_malformed_gbk_warns_but_keeps_good_records(tmp_path):
    zp = tmp_path / "as_output.zip"
    zp.write_bytes(_make_zip({
        "NODE_1.region001.gbk": _GOOD_GBK,
        "NODE_2.region001.gbk": _BAD_GBK,
    }).read())

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        records = read_genbank_records(zp)

    # The good record survives; the bad one is dropped, not fatal.
    assert any("NODE_1" in name for name, _ in records)
    # A warning fired and names the skipped count.
    msgs = [str(w.message) for w in caught]
    assert any("read_genbank_records" in m and "errored" in m for m in msgs), msgs


def test_all_good_gbks_emit_no_warning(tmp_path):
    zp = tmp_path / "clean.zip"
    zp.write_bytes(_make_zip({"NODE_1.region001.gbk": _GOOD_GBK}).read())

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        records = read_genbank_records(zp)

    assert records, "expected at least one parsed record"
    assert not any("read_genbank_records" in str(w.message) for w in caught)


def test_parse_empty_gbk_warns(tmp_path):
    """A GBK that parses without raising but yields zero records must still be
    surfaced. This is the path a real-strain verification run exposed — a raise-only
    warning would miss it, which is precisely how a malformed-but-non-crashing GBK
    disappears into a downstream count mismatch.
    """
    zp = tmp_path / "empty_member.zip"
    zp.write_bytes(_make_zip({
        "NODE_1.region001.gbk": _GOOD_GBK,
        "NODE_2.region001.gbk": _EMPTY_GBK,
    }).read())

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        records = read_genbank_records(zp)

    assert any("NODE_1" in name for name, _ in records)  # good record survives
    msgs = [str(w.message) for w in caught]
    assert any("read_genbank_records" in m and "parsed-empty" in m for m in msgs), msgs
