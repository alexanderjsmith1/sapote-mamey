"""Regression for v9.7.413 (BLIZZARD_BLUE_413_silent_swallow_triage, F_BROAD_UNCLASSIFIED):
`mamey/antismash_input.py::detect_strictness`'s saccharide-fallback loop used to wrap the WHOLE
member loop in one `except Exception: pass`. Split into two layers instead: a coarse catch around
LISTING the archive (unchanged in effect -- a corrupt central directory still degrades to
"unknown"), and a per-member catch so evaluating one region GBK cannot abort the scan of every
other region GBK in the same archive.

Honesty note (found while fixing this, not assumed going in): `_stream_find()` already catches its
own read failures internally and returns ``None`` rather than raising, and `_gbk_size_guard()` is
pure arithmetic on already-resolved `ZipInfo` fields that cannot realistically raise for a name
`regular_file_names()` returned. So on the CURRENT source, there is no known live input that
actually drives the old per-member abort -- this is defense-in-depth against a future change to
either helper (e.g. removing `_stream_find`'s own internal guard), not a reproduction of an
observed wrong verdict. The test below proves the isolation via `monkeypatch`, exercising a path
that is not reachable through any real zip content today; that is stated here rather than implied.
"""
from __future__ import annotations

import zipfile

import pytest

_HEADER = (
    "LOCUS       {name}                    5000 bp    DNA     linear   BCT 01-JAN-2026\n"
    "DEFINITION  Streptomyces sp. AS-TEST.\n"
    "SOURCE      Streptomyces sp. AS-TEST\n"
    "  ORGANISM  Streptomyces sp. AS-TEST\n"
    "            Bacteria; Actinomycetota; Streptomycetales; Streptomycetaceae; Streptomyces.\n"
    "COMMENT     ##antiSMASH-Data-START##\n"
    "            Version      :: 7.1.0\n"
    "            ##antiSMASH-Data-END##\n"
    "FEATURES             Location/Qualifiers\n"
)

_NO_SACCHARIDE_GBK = _HEADER.format(name="NODE_1") + (
    '     region          1..5000\n                     /product="NRPS"\nORIGIN\n        1 acgt\n//\n'
)
_SACCHARIDE_GBK = _HEADER.format(name="NODE_2") + (
    '     region          1..5000\n                     /product="saccharide"\nORIGIN\n        1 acgt\n//\n'
)


def _write_zip(path, members: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return str(path)


@pytest.fixture
def two_region_zip(tmp_path):
    # NODE_1 (no saccharide marker) is listed FIRST, NODE_2 (has the marker) SECOND -- if member
    # evaluation aborts the whole scan on NODE_1, NODE_2's real evidence is never reached.
    return _write_zip(tmp_path / "two_region.zip", {
        "NODE_1.region001.gbk": _NO_SACCHARIDE_GBK.encode(),
        "NODE_2.region001.gbk": _SACCHARIDE_GBK.encode(),
        "AS-TEST.json": b'{"version": "7.1.0", "records": []}',
    })


def test_one_bad_member_does_not_blind_the_scan_to_a_later_good_one(two_region_zip, monkeypatch):
    """Force `_gbk_size_guard` to raise on the FIRST region GBK only (simulating a hypothetical
    defect in that helper, since it cannot realistically raise today) and confirm the saccharide
    evidence in the SECOND, unrelated region GBK is still found -- the scan must not abort."""
    from mamey import antismash_input as ai

    real_guard = ai._gbk_size_guard
    calls = []

    def flaky_guard(info):
        calls.append(info.filename)
        if info.filename == "NODE_1.region001.gbk":
            raise RuntimeError("simulated corrupt member metadata")
        return real_guard(info)

    monkeypatch.setattr(ai, "_gbk_size_guard", flaky_guard)
    with zipfile.ZipFile(two_region_zip) as zf:
        strictness, evidence = ai.detect_strictness(zf)
    assert strictness == "loose", f"evidence in NODE_2 must still be found: {evidence!r}"
    assert "NODE_2" in evidence
    assert calls == ["NODE_1.region001.gbk", "NODE_2.region001.gbk"], \
        "both members must be visited -- the failure on NODE_1 must not stop iteration"


def test_corrupt_central_directory_still_degrades_to_unknown(tmp_path, monkeypatch):
    """The OTHER layer: if listing the archive itself fails (regular_file_names ->
    ZipFile.infolist()), the function must still return "unknown" rather than raising -- unchanged
    from .412's behaviour, just now via an explicit, narrow catch instead of one that also covered
    the per-member loop.

    `detect_strictness` calls `regular_file_names(zf)` TWICE -- once to list the JSON members
    (unrelated to this fix, never protected in either .412 or .413) and once inside the saccharide
    fallback (the call this fix wraps). The fake only fails the SECOND call, so this test isolates
    the layer actually under test rather than tripping the unrelated first call."""
    from mamey import antismash_input as ai

    real = ai.regular_file_names
    calls = []

    def boom_on_second_call(z):
        calls.append(1)
        if len(calls) >= 2:
            raise zipfile.BadZipFile("simulated corrupt central directory")
        return real(z)

    monkeypatch.setattr(ai, "regular_file_names", boom_on_second_call)
    p = tmp_path / "empty.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("AS-TEST.json", b'{"version": "7.1.0"}')
    with zipfile.ZipFile(p) as zf:
        strictness, evidence = ai.detect_strictness(zf)
    assert strictness == "unknown"
    assert "no strictness field found in JSON" in evidence
    assert len(calls) == 2, "expected exactly the two known call sites"
