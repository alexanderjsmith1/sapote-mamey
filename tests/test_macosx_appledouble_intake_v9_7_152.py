"""v9.7.152 / engine 1.9.101 — strip macOS AppleDouble/__MACOSX shadows on intake.

A macOS-zipped antiSMASH package carries one __MACOSX/.../._<file> AppleDouble
stub per real file. These end in .gbk and contain 'region', so naive
endswith()+substring filters double-count them. See
AUDIT_AS705_macosx_appledouble. Fix = is_macos_cruft() chokepoint applied at
every namelist() consumer (parsers) and before every count (inspector).
"""
import io
import warnings
import zipfile

import pytest

from mamey.parsers import is_macos_cruft, read_genbank_records
from mamey.package_inspector import classify_antismash_zip


def _real_region_gbk(node: str) -> bytes:
    # minimal valid single-record GenBank with one region feature
    return (
        f"LOCUS       {node}            100 bp    DNA     linear   BCT 30-JUN-2026\n"
        "FEATURES             Location/Qualifiers\n"
        "     region          1..100\n"
        "                     /region_number=\"1\"\n"
        "ORIGIN\n"
        "        1 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc\n"
        "//\n"
    ).encode()


def _appledouble_stub() -> bytes:
    # AppleDouble magic; not parseable as GenBank
    return b"\x00\x05\x16\x07" + b"\x00" * 200


def _mixed_zip(n_real: int) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i in range(n_real):
            node = f"NODE_{i}_length_1000_cov_50"
            fn = f"AS-TEST/{node}.region001.gbk"
            zf.writestr(fn, _real_region_gbk(node))
            # its AppleDouble shadow
            zf.writestr(f"__MACOSX/AS-TEST/._{node}.region001.gbk", _appledouble_stub())
        # a couple of KCB txt + their shadows
        for i in range(n_real):
            zf.writestr(f"AS-TEST/clusterblast/region{i}.txt", b"hit\n")
            zf.writestr(f"__MACOSX/AS-TEST/clusterblast/._region{i}.txt", _appledouble_stub())
        # full-assembly gbk + its shadow + a .DS_Store
        zf.writestr("AS-TEST/AS-TEST_full.gbk", _real_region_gbk("FULL"))
        zf.writestr("__MACOSX/AS-TEST/._AS-TEST_full.gbk", _appledouble_stub())
        zf.writestr("AS-TEST/.DS_Store", _appledouble_stub())
    buf.seek(0)
    return buf


def test_is_macos_cruft_predicate():
    assert is_macos_cruft("__MACOSX/x/._a.gbk") is True
    assert is_macos_cruft("x/._a.gbk") is True
    assert is_macos_cruft(".DS_Store") is True
    assert is_macos_cruft("AS-TEST/.DS_Store") is True
    assert is_macos_cruft("NODE_1_length_1000_cov_50.region001.gbk") is False
    assert is_macos_cruft("AS-705_new.gbk") is False
    assert is_macos_cruft("AS-TEST/clusterblast/region0.txt") is False


def test_classify_counts_real_files_only():
    names = zipfile.ZipFile(_mixed_zip(3)).namelist()
    info = classify_antismash_zip(names)
    # 3 real region GBKs, not 6
    assert info["region_gbk_count"] == 3, info


def test_batch_estimate_uses_real_count():
    # 50 real region GBKs + 50 shadows -> estimate must key off 50, not 100
    import math
    names = zipfile.ZipFile(_mixed_zip(50)).namelist()
    info = classify_antismash_zip(names)
    assert info["region_gbk_count"] == 50
    assert math.ceil(info["region_gbk_count"] / 20) == 3  # not ceil(100/20)=5


def test_no_spurious_empty_record_warning():
    z = _mixed_zip(4)
    # read_genbank_records needs a path; write to a temp file
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tf:
        tf.write(z.read())
        path = tf.name
    try:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            recs = read_genbank_records(path, region_only=True)
        empty = [str(x.message) for x in w if "yielded no records" in str(x.message)]
        assert len(recs) == 4, f"expected 4 real records, got {len(recs)}"
        assert empty == [], f"unexpected empty-record warning: {empty}"
    finally:
        os.unlink(path)
