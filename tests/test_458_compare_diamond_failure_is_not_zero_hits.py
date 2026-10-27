"""A failed DIAMOND run in compare falls back to another aligner instead of reading as zero hits.

Before: _align_diamond returned {} when DIAMOND reported ok=False, so compare wrote a 0-hit table.
"""
import pytest

from mamey import compare


def test_diamond_failure_raises(monkeypatch):
    from mamey import diamond_align
    monkeypatch.setattr(diamond_align, "align_fasta", lambda q, r, threads=1: {"ok": False, "hits": [], "reason": "diamond crashed"})
    with pytest.raises(RuntimeError, match="diamond crashed"):
        compare._align_diamond({"q1": "MSTNPK"}, {"r1": "MSTNPK"}, 1)


def test_dispatcher_falls_back_instead_of_returning_empty(monkeypatch):
    monkeypatch.setattr(compare, "_aligner_backend", lambda: "diamond")
    def boom(*a, **k):
        raise RuntimeError("DIAMOND alignment could not execute: x")
    monkeypatch.setattr(compare, "_align_diamond", boom)
    monkeypatch.setattr(compare, "_align_biopython", lambda q, r: {"q1": {"backend": "biopython"}})
    assert compare.align_genes_to_proteome({"q1": "MSTNPK"}, {"r1": "MSTNPK"}) == {"q1": {"backend": "biopython"}}
