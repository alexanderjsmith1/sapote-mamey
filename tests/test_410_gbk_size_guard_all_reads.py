"""CLAUDE_410_gbk_size_guard_all_reads — the GBK size / decompression-bomb guard covers EVERY
zip-member read, not only the SeqIO loop.

Fail-before (pristine .409) / pass-after (patched .410).

Verified on the sealed .409 (development/round6_v409/HOSTILE_PIPELINE_INPUTS.md, input #10): the
.409 `_gbk_size_guard` (100 MB / 200x) is applied only at the SeqIO read in read_genbank_records().
Four other reads slurp the full uncompressed member with no cap — `_first_region_header`
(read-only `inspect` path, `zf.read(member)[:6144]`), `_region_orig_bounds_from_zip` and
`read_fasta_sequences_from_zip` (both via `_safe_read_text`), and the `detect_strictness`
saccharide fallback. A 298 KB zip holding a 300 MB member drove RSS to 618 MB (`inspect`) and
940 MB (`parse_bgcs_from_zip`).

The tests below prove "never loaded" deterministically: `zipfile.ZipFile.read` (the unbounded
whole-member read) is instrumented to record which members it is asked for, and the refusal is
asserted through the typed `GbkSizeGuardRefusal` / `GBK_SIZE_GUARD_REFUSED` signal. The crafted
members are small (3 MB) with the cap lowered to 1 MB via `MAMEY_GBK_MAX_BYTES`, so nothing is
ever driven near real memory limits. One fresh-process test measures peak RSS with the default
caps on a 64 MB member (refused on ratio alone) as the direct analogue of the measured finding.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
import warnings
import zipfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_TREE = os.path.dirname(_HERE)

_REGION = "NODE_1.region001.gbk"
_SMALL_CAP = 1_000_000          # MAMEY_GBK_MAX_BYTES used by the in-process tests
_BIG = 3 * 1024 * 1024          # crafted member: 3 MB uncompressed, ~3 KB compressed (ratio ~1000x)

_HEADER = (
    "LOCUS       NODE_1                    5000 bp    DNA     linear   BCT 01-JAN-2026\n"
    "DEFINITION  Streptomyces sp. AS-TEST.\n"
    "SOURCE      Streptomyces sp. AS-TEST\n"
    "  ORGANISM  Streptomyces sp. AS-TEST\n"
    "            Bacteria; Actinomycetota; Streptomycetales; Streptomycetaceae; Streptomyces.\n"
    "COMMENT     ##antiSMASH-Data-START##\n"
    "            Version      :: 7.1.0\n"
    "            Orig. start  :: 1000\n"
    "            Orig. end    :: 2000\n"
    "            ##antiSMASH-Data-END##\n"
    "FEATURES             Location/Qualifiers\n"
)
_NORMAL_GBK = _HEADER + (
    "     region          1..5000\n"
    '                     /product="saccharide"\n'
    "ORIGIN\n"
    "        1 acgt\n"
    "//\n"
)


def _write_zip(path, members: dict[str, bytes]) -> str:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return str(path)


def _bomb_gbk(n_bytes: int = _BIG) -> bytes:
    return _HEADER.encode() + b"A" * n_bytes + b"\nORIGIN\n//\n"


@pytest.fixture
def bomb_zip(tmp_path):
    """Region GBK far over the (lowered) cap; JSON carries no strictness token so the saccharide
    fallback is exercised."""
    return _write_zip(tmp_path / "bomb.zip", {
        _REGION: _bomb_gbk(),
        "AS-TEST.json": b'{"version": "7.1.0", "records": []}',
    })


@pytest.fixture
def normal_zip(tmp_path):
    return _write_zip(tmp_path / "normal.zip", {
        _REGION: _NORMAL_GBK.encode(),
        "AS-TEST.json": b'{"version": "7.1.0", "records": []}',
        "contigs.fasta": b">NODE_1\nACGTACGT\n",
    })


@pytest.fixture
def small_cap(monkeypatch):
    monkeypatch.setenv("MAMEY_GBK_MAX_BYTES", str(_SMALL_CAP))
    monkeypatch.delenv("MAMEY_GBK_MAX_RATIO", raising=False)


@pytest.fixture
def read_spy(monkeypatch):
    """Record every member handed to the unbounded ``ZipFile.read`` (the whole-member load)."""
    seen: list[str] = []
    real = zipfile.ZipFile.read

    def spy(self, name, *a, **k):
        seen.append(name if isinstance(name, str) else name.filename)
        return real(self, name, *a, **k)

    monkeypatch.setattr(zipfile.ZipFile, "read", spy)
    return seen


# --------------------------------------------------------------------------------------
# Path 1 — antismash_input._first_region_header (read-only `inspect` / identify())
# --------------------------------------------------------------------------------------

def test_identify_refuses_overcap_region_header_without_full_read(bomb_zip, small_cap, read_spy):
    from mamey.antismash_input import identify

    res = identify(bomb_zip)
    assert _REGION not in read_spy, "inspect path must never whole-member-read an over-cap region GBK"
    typed = [w for w in res.warnings if w.startswith("GBK_SIZE_GUARD_REFUSED:")]
    assert typed, f"identify() must surface the typed refusal; warnings={res.warnings}"
    assert _REGION in typed[0] and "MAMEY_GBK_MAX_BYTES" in typed[0]
    assert res.n_regions == 1, "region count is metadata-only and must still be reported"
    assert res.is_antismash


def test_identify_header_read_is_bounded_on_normal_member(normal_zip, read_spy):
    """Normal-size member: behaviour preserved (organism / version / strictness parsed) AND the
    header is a bounded peek, not a whole-member read."""
    from mamey.antismash_input import identify

    res = identify(normal_zip)
    assert res.organism and "Streptomyces" in res.organism
    assert res.antismash_version == "7.1.0"
    assert res.n_regions == 1
    assert res.strictness == "loose", res.strictness_evidence      # saccharide heuristic intact
    assert not any(w.startswith("GBK_SIZE_GUARD_REFUSED") for w in res.warnings)
    assert _REGION not in read_spy, "header peek must not whole-member-read even a normal region GBK"


# --------------------------------------------------------------------------------------
# Path 2 — parsers._safe_read_text / _region_orig_bounds_from_zip
# --------------------------------------------------------------------------------------

def test_safe_read_text_raises_typed_refusal(bomb_zip, small_cap, read_spy):
    from mamey import parsers

    with zipfile.ZipFile(bomb_zip) as zf:
        with pytest.raises(parsers.GbkSizeGuardRefusal) as ei:
            parsers._safe_read_text(zf, _REGION)
        assert ei.value.member == _REGION
        assert "MAMEY_GBK_MAX_BYTES" in ei.value.reason
        assert str(ei.value).startswith("GBK_SIZE_GUARD_REFUSED:")
        # Normal-size members still read in full through the same helper.
        assert parsers._safe_read_text(zf, "AS-TEST.json").startswith("{")
    assert _REGION not in read_spy


def test_region_orig_bounds_skips_refused_member_without_full_read(bomb_zip, small_cap, read_spy):
    from mamey.parsers import _region_orig_bounds_from_zip

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = _region_orig_bounds_from_zip(bomb_zip)
    assert out == {}
    assert _REGION not in read_spy
    assert any("GBK_SIZE_GUARD_REFUSED" in str(w.message) for w in caught), \
        "refused region bounds must not be a silent skip"


def test_region_orig_bounds_normal_member_unchanged(normal_zip, small_cap):
    from mamey.parsers import _region_orig_bounds_from_zip

    assert _region_orig_bounds_from_zip(normal_zip) == {_REGION: (1000, 2000)}


# --------------------------------------------------------------------------------------
# Path 3 — parsers.read_fasta_sequences_from_zip
# --------------------------------------------------------------------------------------

def test_read_fasta_refuses_entire_result_when_one_member_is_overcap(tmp_path, small_cap, read_spy):
    from mamey.parsers import GbkSizeGuardRefusal, read_fasta_sequences_from_zip

    zpath = _write_zip(tmp_path / "fasta.zip", {
        "big.fasta": b">bomb\n" + b"A" * _BIG + b"\n",
        "small.fasta": b">NODE_1\nACGT\n",
    })
    with pytest.raises(GbkSizeGuardRefusal, match=r"GBK_SIZE_GUARD_REFUSED: big\.fasta"):
        read_fasta_sequences_from_zip(zpath)
    assert "big.fasta" not in read_spy


# --------------------------------------------------------------------------------------
# Path 4 — antismash_input.detect_strictness saccharide fallback
# --------------------------------------------------------------------------------------

def test_detect_strictness_fallback_skips_refused_member_without_full_read(bomb_zip, small_cap, read_spy):
    from mamey.antismash_input import detect_strictness

    with zipfile.ZipFile(bomb_zip) as zf:
        strictness, evidence = detect_strictness(zf)
    assert strictness == "unknown"
    assert "GBK_SIZE_GUARD_REFUSED" in evidence, evidence
    assert _REGION not in read_spy


def test_detect_strictness_fallback_normal_member_still_streams(normal_zip, read_spy):
    from mamey.antismash_input import detect_strictness

    with zipfile.ZipFile(normal_zip) as zf:
        strictness, evidence = detect_strictness(zf)
    assert strictness == "loose" and "saccharide" in evidence
    assert _REGION not in read_spy, "saccharide scan must stream, never whole-member-read"


# --------------------------------------------------------------------------------------
# Guarded reader — bounded streaming cap (defence against a lying central directory)
# --------------------------------------------------------------------------------------

def test_guarded_read_bounded_even_when_declared_size_passes(bomb_zip, small_cap, monkeypatch):
    """If the declared getinfo() size slipped past the preflight, the streamed read is still
    capped at cap+1 bytes and refused — the member is never decompressed in full."""
    from mamey import parsers

    monkeypatch.setattr(parsers, "_gbk_size_guard", lambda info: None)   # defeat the preflight
    with zipfile.ZipFile(bomb_zip) as zf:
        with pytest.raises(parsers.GbkSizeGuardRefusal) as ei:
            parsers._guarded_read_bytes(zf, _REGION)
        assert "streamed size exceeds" in ei.value.reason
        head = parsers._guarded_read_bytes(zf, _REGION, limit=6144)
        assert len(head) == 6144 and head.startswith(b"LOCUS")


def test_seqio_loop_refusal_unchanged(bomb_zip, small_cap):
    """The .409 guard at the SeqIO loop keeps its behaviour: refused member counted as errored."""
    from mamey.parsers import read_genbank_records

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        recs = list(read_genbank_records(bomb_zip, region_only=True))
    assert recs == []
    assert any("errored" in str(w.message) for w in caught)


# --------------------------------------------------------------------------------------
# Fresh-process RSS analogue of the measured finding (default caps; refused on ratio alone)
# --------------------------------------------------------------------------------------

_RSS_PROBE = r"""
import resource, sys, zipfile
tree, zpath, mode = sys.argv[1:4]
sys.path.insert(0, tree)
def rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / (1024 * 1024) if sys.platform == "darwin" else r / 1024
before = rss_mb()
if mode == "identify":
    from mamey.antismash_input import identify
    identify(zpath)
else:
    import warnings
    from mamey.parsers import _region_orig_bounds_from_zip
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _region_orig_bounds_from_zip(zpath)
print(f"{rss_mb() - before:.1f}")
"""


@pytest.mark.parametrize("mode", ["identify", "bounds"])
def test_fresh_process_rss_stays_flat_on_64mb_bomb(tmp_path, monkeypatch, mode):
    """64 MB uncompressed / ~64 KB compressed (ratio ~1000x > 200x default): with the guard on
    every read, peak RSS growth stays far below the member size; the unguarded .409 reads grow
    by at least the member size."""
    zpath = _write_zip(tmp_path / "bomb64.zip", {
        _REGION: _bomb_gbk(64 * 1024 * 1024),
        "AS-TEST.json": b'{"version": "7.1.0", "records": []}',
    })
    monkeypatch.delenv("MAMEY_GBK_MAX_BYTES", raising=False)   # default caps in the child
    monkeypatch.delenv("MAMEY_GBK_MAX_RATIO", raising=False)
    proc = subprocess.run([sys.executable, "-c", _RSS_PROBE, _TREE, zpath, mode],
                          capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, timeout=300)
    assert proc.returncode == 0, proc.stderr
    grew_mb = float(proc.stdout.strip().splitlines()[-1])
    assert grew_mb < 32, f"{mode}: peak RSS grew {grew_mb:.0f} MB — the 64 MB member was loaded"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-q"]))
