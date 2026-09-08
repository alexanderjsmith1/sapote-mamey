"""v9.7.396 PARSE-COMPLETENESS: the ZIP's region-GBK count must be counted the way the parser
reads it, and must be reconciled against the BGCs actually produced.

Two defects, both reproduced against the real production functions on a real antiSMASH ZIP
(48 region GBKs) before the fix:

  1. `cli._count_antismash_region_gbks` counted `name.endswith(".gbk") and "region" in name`
     over the raw namelist. In a Finder-made ZIP every region GBK also has an AppleDouble
     shadow (`__MACOSX/.../._X.region001.gbk`) that satisfies both tests, so the count came
     back **96 instead of 48** — double. That count feeds the ChatGPT-safe batch-size guard,
     so a batch that was never too large could be refused. `parsers.is_macos_cruft`'s own
     docstring names this exact hazard ("any consumer that counts ZIP entries by a bare
     extension/substring filter"); this counter was such a consumer.

  2. Nothing compared the source region-GBK count to the parsed BGC count. Truncating three
     region GBKs (they parse to zero records and raise nothing — the "insidious" case
     `read_genbank_records` documents) took a real ZIP from **48 GBKs -> 45 BGCs** with a
     single Python warning and no gate. Every downstream denominator is then short, while the
     package stays internally self-consistent, so `validate_package` still returns
     MAMEY_COMPLETE. That is a silent-coverage failure at the very top of the pipeline, where
     every later claim originates.

The fix puts the selection logic in one place (`parsers.region_gbk_count`, identical to
`read_genbank_records(region_only=True)`), has the CLI counter delegate to it, and reports the
source count alongside the parsed count — loudly on a shortfall, and in the phase receipt so the
receipt audit can see it.
"""
from __future__ import annotations

import zipfile
from pathlib import PurePosixPath

import pytest

from mamey.parsers import region_gbk_count


def _gbk(locus: str = "CONTIG_1", *, empty: bool = False) -> bytes:
    """A minimal GenBank record; `empty=True` yields a header that parses to ZERO records."""
    if empty:
        return b"LOCUS       TRUNCATED\n"
    return (
        f"LOCUS       {locus}             120 bp    DNA     linear   BCT 01-JAN-2026\n"
        f"DEFINITION  test.\nACCESSION   {locus}\nVERSION     {locus}.1\n"
        "FEATURES             Location/Qualifiers\n"
        "     region          1..120\n"
        '                     /product="NRPS"\n'
        "ORIGIN\n"
        "        1 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc\n"
        "       61 atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc atgcatgcat gcatgcatgc\n"
        "//\n"
    ).encode()


def _zip(path, entries: dict[str, bytes]):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return path


def _with_appledouble(entries: dict[str, bytes]) -> dict[str, bytes]:
    """What macOS Finder adds when it zips a folder: a `._` shadow per file."""
    out = dict(entries)
    for name in entries:
        p = PurePosixPath(name)
        out[f"__MACOSX/{p.parent}/._{p.name}"] = b"\x00\x05\x16\x07"
    return out


# --- defect 1: the count must ignore macOS cruft and match on the basename ------------------

def test_region_count_ignores_appledouble_shadows(tmp_path):
    plain = {f"out/NODE_1.region{i:03d}.gbk": _gbk(f"C{i}") for i in (1, 2, 3)}
    assert region_gbk_count(_zip(tmp_path / "plain.zip", plain)) == 3
    assert region_gbk_count(_zip(tmp_path / "macos.zip", _with_appledouble(plain))) == 3, (
        "AppleDouble shadows end in .gbk and contain 'region'; they are not region GBKs")


def test_region_count_matches_on_basename_not_path(tmp_path):
    """A directory called `regions/` must not turn every GBK under it into a region GBK."""
    entries = {"regions/whole_genome.gbk": _gbk("WG"),
               "regions/NODE_1.region001.gbk": _gbk("C1")}
    assert region_gbk_count(_zip(tmp_path / "d.zip", entries)) == 1


def test_region_count_on_unreadable_zip_is_zero(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"not a zip at all")
    assert region_gbk_count(bad) == 0, "unreadable ZIP means 'no expectation', not a crash"


def test_cli_counter_delegates_to_the_shared_selection(tmp_path):
    """The batch-sizing guard and the parser must not disagree about what a region GBK is."""
    from mamey.cli import _count_antismash_region_gbks
    plain = {f"out/NODE_1.region{i:03d}.gbk": _gbk(f"C{i}") for i in (1, 2, 3, 4)}
    macos = _zip(tmp_path / "m.zip", _with_appledouble(plain))
    assert _count_antismash_region_gbks(macos) == region_gbk_count(macos) == 4


# --- defect 2: a region GBK that yields no record must not vanish silently -------------------

def test_truncated_region_gbk_is_a_detectable_shortfall(tmp_path):
    """The parser drops it with only a warning; the counts must therefore disagree, which is
    exactly the signal the run now reports."""
    from mamey.parsers import parse_bgcs_from_zip
    entries = {"out/NODE_1.region001.gbk": _gbk("C1"),
               "out/NODE_1.region002.gbk": _gbk("C2"),
               "out/NODE_1.region003.gbk": _gbk("C3", empty=True)}   # parses to zero records
    z = _zip(tmp_path / "short.zip", entries)
    n_source = region_gbk_count(z)
    with pytest.warns(UserWarning):
        bgcs = parse_bgcs_from_zip(z, json_mode="off")
    assert n_source == 3
    assert len(bgcs) < n_source, "the truncated GBK must actually be lost (defect precondition)"
    assert n_source - len(bgcs) == 1


def test_healthy_zip_shows_no_shortfall(tmp_path):
    """Control: the check must not fire on a clean ZIP, or it is useless."""
    from mamey.parsers import parse_bgcs_from_zip
    entries = {f"out/NODE_1.region{i:03d}.gbk": _gbk(f"C{i}") for i in (1, 2, 3)}
    z = _zip(tmp_path / "ok.zip", entries)
    assert len(parse_bgcs_from_zip(z, json_mode="off")) == region_gbk_count(z) == 3
