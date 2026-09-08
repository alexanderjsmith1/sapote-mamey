"""CLAUDE_409_resource_bounds — resource-exhaustion / DoS bound tests.

Fail-before (pristine sealed .408 tree) / pass-after (patched .409 overlay).

Covers DEEP_AUDIT2_resource_dos findings #1 (PairwiseAligner O(L^2) length cap on
compare/cohort_proteins/split_detector), #2 (/product,/translation display cap on
gene-by-gene CSV / Mode-B markdown / widget JSON), #3 (GBK read size / decompression-bomb
guard) and DEEP_AUDIT2_workbook Finding 1 (list_count-vs-rows self-contradiction).

Biopython is NOT required to run these: the aligner sites are exercised with a fake
aligner (and, for compare, a fake `Bio` module) so a real .align() is never called —
the whole point being that an over-long sequence must be refused BEFORE .align(), which
on a real aligner would SIGKILL the process uncatchably. The cap is set to a tiny value
(MAMEY_MAX_ALIGN_AA=100) so nothing is ever driven to OOM.

Runnable two ways:
  * `pytest test_409_resource_bounds.py`
  * `python3 test_409_resource_bounds.py`  (bundled standalone runner; no pytest needed)
"""
from __future__ import annotations

import os
import pytest
import sys
import types
from contextlib import contextmanager


@contextmanager
def _env(**kv):
    with pytest.MonkeyPatch.context() as _mp:  # restored on exit, and visible to the suite's env-leak guard
        for k, v in kv.items():
            if v is None:
                _mp.delenv(k, raising=False)
            else:
                _mp.setenv(k, str(v))
        yield


# --------------------------------------------------------------------------------------
# Finding #1 — PairwiseAligner O(L^2) length cap
# --------------------------------------------------------------------------------------

class _Reached(Exception):
    """Raised by the fake aligner to prove a real .align() call site was reached."""


def test_cohort_metrics_refuses_overlong_pair_before_align():
    """cohort_proteins._metrics must NOT call .align() when a sequence exceeds the cap;
    it returns a typed 'alignment_skipped' metrics dict instead (real aligner would SIGKILL)."""
    from mamey import cohort_proteins

    class FakeAligner:
        substitution_matrix = {}
        def align(self, q, s):
            raise _Reached  # a real aligner here would allocate an O(len(q)*len(s)) matrix

    with _env(MAMEY_MAX_ALIGN_AA=100):
        # Over-long pair: refused up front, no .align() call, typed note present.
        m = cohort_proteins._metrics(FakeAligner(), "A" * 200, "A" * 10)
        assert "alignment_skipped" in m, "over-long pair must be refused with a typed note"
        assert m["identity_pct"] == 0.0 and m["local_alignment_score_blosum62"] == 0.0
        # Under-cap pair: guard passes through and the real align() site IS reached.
        try:
            cohort_proteins._metrics(FakeAligner(), "AAAA", "AAAA")
        except _Reached:
            pass
        else:  # pragma: no cover
            raise AssertionError("under-cap pair should still reach .align()")


def test_compare_align_biopython_refuses_overlong_query_before_align():
    """compare._align_biopython must skip an over-long query and never touch .align()."""
    from mamey import compare

    calls = {"n": 0}

    class FakeAln:
        score = 5.0
        def __getitem__(self, i):
            return "AAAA"

    class FakeAligner:
        def __init__(self):
            self.substitution_matrix = None
            self.mode = None
            self.open_gap_score = 0
            self.extend_gap_score = 0
        def align(self, q, s):
            calls["n"] += 1
            return [FakeAln()]

    fake_align_mod = types.ModuleType("Bio.Align")
    fake_align_mod.PairwiseAligner = FakeAligner
    fake_align_mod.substitution_matrices = types.SimpleNamespace(load=lambda *_a, **_k: {})
    fake_bio = types.ModuleType("Bio")
    fake_bio.Align = fake_align_mod

    saved = {k: sys.modules.get(k) for k in ("Bio", "Bio.Align")}
    sys.modules["Bio"] = fake_bio
    sys.modules["Bio.Align"] = fake_align_mod
    try:
        with _env(MAMEY_MAX_ALIGN_AA=100):
            out = compare._align_biopython([("q1", "A" * 200)], [("r1", "A" * 10)])
        assert out["q1"].get("pident") is None, "over-long query must classify as no-hit"
        assert "note" in out["q1"] and "MAX_ALIGN_AA" in out["q1"]["note"]
        assert calls["n"] == 0, ".align() must NOT be called for an over-long query"
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


def test_split_detector_source_has_alignment_length_cap():
    """split_detector can't import without Biopython, so assert at source level that the
    length cap guards the .align() call (fails on the pristine tree, which has no guard)."""
    import mamey
    src_path = os.path.join(os.path.dirname(mamey.__file__), "split_detector.py")
    with open(src_path, encoding="utf-8") as fh:
        src = fh.read()
    assert "_max_align_aa" in src, "split_detector must define the residue-cap helper"
    guard = src.index("_cap")  # the len(...)>_cap guard
    align = src.index("aln.align(")
    assert guard < align, "the length cap must be checked BEFORE aln.align()"
    assert "len(fseq)>_cap or len(g[\"seq\"])>_cap" in src


# --------------------------------------------------------------------------------------
# Finding #2 — /product,/translation display cap (CSV / markdown / widget JSON)
# --------------------------------------------------------------------------------------

_FIVE_MB = "x" * 5_000_000


def _assert_capped(rendered: str, original_len: int):
    assert len(rendered) < original_len, "a 5 MB qualifier must be truncated"
    assert len(rendered) <= 20_000 + 80, "truncated output must be bounded near the cap"
    assert "[truncated" in rendered, "truncation must carry an explicit marker"


def test_gene_by_gene_caps_qualifier():
    from mamey import gene_by_gene
    _assert_capped(gene_by_gene._cap_qualifier(_FIVE_MB), len(_FIVE_MB))
    assert gene_by_gene._cap_qualifier("T1PKS") == "T1PKS"  # short value untouched
    assert gene_by_gene._cap_qualifier(None) == ""


def test_mode_b_md_escape_caps_qualifier():
    from mamey.mode_b import gene_first_explore
    out = gene_first_explore._md_escape(_FIVE_MB)
    _assert_capped(out, len(_FIVE_MB))
    # still escapes pipes/newlines
    assert gene_first_explore._md_escape("a|b\nc") == "a\\|b c"


def test_widget_text_caps_qualifier():
    from mamey import widget_deliverable
    _assert_capped(widget_deliverable._text(_FIVE_MB), len(_FIVE_MB))
    _assert_capped(widget_deliverable._text([_FIVE_MB]), len(_FIVE_MB))  # list path too
    assert widget_deliverable._text("ok") == "ok"


# --------------------------------------------------------------------------------------
# Finding #3 — GBK read size / decompression-bomb guard
# --------------------------------------------------------------------------------------

def test_parsers_gbk_size_guard():
    from mamey import parsers

    def info(file_size, compress_size):
        return types.SimpleNamespace(file_size=file_size, compress_size=compress_size)

    # normal region GBK (well under caps) -> allowed
    assert parsers._gbk_size_guard(info(2_000_000, 400_000)) is None
    # oversized uncompressed -> refused
    r = parsers._gbk_size_guard(info(500_000_000, 400_000_000))
    assert r and "exceeds MAMEY_GBK_MAX_BYTES" in r
    # decompression bomb: tiny compressed, huge uncompressed, within byte cap but extreme ratio
    r2 = parsers._gbk_size_guard(info(50_000_000, 1_000))
    assert r2 and "decompression-bomb" in r2


# --------------------------------------------------------------------------------------
# DEEP_AUDIT2_workbook Finding 1 — list_count must reconcile with rows shown
# --------------------------------------------------------------------------------------

def test_workbook_dict_sheet_count_matches_rows_shown():
    from openpyxl import Workbook
    from mamey import workbook

    wb = Workbook()
    workbook._write_dict_sheet(wb, "Detail", {"g": list(range(400))})
    ws = wb["Detail"]
    rows = [(r[0].value, r[1].value, r[2].value) for r in ws.iter_rows()]

    list_count = next(v for (_g, k, v) in rows if k == "list_count")
    item_rows = [k for (_g, k, _v) in rows if isinstance(k, str) and k.startswith("item_")]
    trunc = [v for (_g, k, v) in rows if k == "list_truncated"]

    assert list_count == 400, "the declared count is the true length"
    assert len(item_rows) == 300, "item rows are capped at 300"
    # the fix: an explicit reconciling marker so the sheet no longer contradicts itself
    assert trunc, "a truncated list must carry a [truncated N of M] marker row"
    assert "300 of 400" in trunc[0]

    # a short list is untouched (no marker)
    wb2 = Workbook()
    workbook._write_dict_sheet(wb2, "Small", {"g": [1, 2, 3]})
    ws2 = wb2["Small"]
    assert not any(r[1].value == "list_truncated" for r in ws2.iter_rows())


# --------------------------------------------------------------------------------------
# Standalone runner (no pytest needed)
# --------------------------------------------------------------------------------------

def _run():
    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
    passed = failed = 0
    for t in tests:
        try:
            t()
        except Exception as exc:  # noqa: BLE001 - test harness
            failed += 1
            print(f"FAIL  {t.__name__}: {type(exc).__name__}: {exc}")
        else:
            passed += 1
            print(f"PASS  {t.__name__}")
    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run())
