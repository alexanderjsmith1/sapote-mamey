"""Tests for mamey.diamond_align — the optional DIAMOND (diamond4py) offline aligner.

These tests do NOT require DIAMOND to be installed: they verify (a) the module imports
and degrades gracefully when the optional binding is absent, and (b) the -outfmt 6 parser
and ortholog gate behave correctly on synthetic tabular input. The actual alignment path
is exercised only when diamond4py is compiled in the environment.
"""

import os
import pytest
import tempfile

from mamey import diamond_align as da


def test_module_imports_without_diamond():
    # importing the module must never require the optional binding
    assert hasattr(da, "align_fasta")
    assert hasattr(da, "build_db")
    assert hasattr(da, "diamond_available")


def test_diamond_available_returns_tuple():
    ok, reason = da.diamond_available()
    assert isinstance(ok, bool)
    assert isinstance(reason, str) and reason


def test_align_fasta_graceful_when_unavailable_or_missing_inputs():
    # with nonexistent inputs (and/or no DIAMOND), must return a clean result, never raise
    r = da.align_fasta("/nonexistent/q.fasta", "/nonexistent/r.fasta")
    assert r["ok"] is False
    assert r["hits"] == []
    assert r["n_hits"] == 0
    assert isinstance(r["reason"], str) and r["reason"]


def test_outfmt6_parser_and_ortholog_gate():
    # synthetic -outfmt 6: one real ortholog (high id + high cov), one motif hit (high id, tiny cov)
    fd, path = tempfile.mkstemp(suffix=".tsv")
    os.close(fd)
    try:
        with open(path, "w") as fh:
            fh.write("geneA\trefX\t81.0\t420\t5\t1\t1\t420\t1\t420\t1e-99\t700.0\t95.0\t92.0\n")
            fh.write("geneB\trefY\t100.0\t12\t0\t0\t1\t12\t50\t61\t2.0\t30.0\t3.0\t2.0\n")
        all_hits = da._parse_outfmt6(path)
        assert len(all_hits) == 2
        assert all_hits[0]["pident"] == 81.0
        assert all_hits[0]["qcovhsp"] == 95.0
        # ortholog gate: qcov >= 50 keeps the real ortholog, drops the 3%-coverage motif hit
        orthologs = da._parse_outfmt6(path, min_qcov=50.0)
        assert len(orthologs) == 1
        assert orthologs[0]["qseqid"] == "geneA"
    finally:
        os.remove(path)


def test_best_hit_per_query():
    hits = [
        {"qseqid": "g1", "sseqid": "a", "bitscore": 100.0},
        {"qseqid": "g1", "sseqid": "b", "bitscore": 250.0},
        {"qseqid": "g2", "sseqid": "c", "bitscore": 50.0},
    ]
    best = da.best_hit_per_query(hits)
    assert best["g1"]["sseqid"] == "b"  # higher bitscore wins
    assert best["g2"]["sseqid"] == "c"


import shutil


@pytest.mark.skipif(shutil.which("diamond") is None,
                    reason="DIAMOND binary not on PATH — fast-path is SPECIFIED_UNVERIFIED "
                           "until a binary is available (see sapote_addons/DIAMOND_STATUS.md)")
def test_diamond_selfhit_is_full_identity():
    """F1 (hostile audit): exercise the DIAMOND path end-to-end when a binary is present.
    A protein aligned against itself must return ~100% identity and ~100% coverage — this is
    the correctness check that catches a pident/qcovhsp parsing error in the outfmt6 wrapper.
    Skipped (not failed) where DIAMOND is absent, so the fast-path's UNVERIFIED status is
    explicit rather than silently assumed-covered."""
    import tempfile, os
    seq = ("MSNNEDIAIIGMAGRFPGADNIDEFWDNLCNGVESITFFSDEELLAAGVDPALLKNPNYVK"
           "AKGVLEDVDKFDAAFFGISPREAELMDPQQRLLLE")
    tmp = tempfile.mkdtemp(prefix="diamond_selfhit_")
    try:
        q = os.path.join(tmp, "q.faa")
        with open(q, "w") as fh:
            fh.write(f">geneA\n{seq}\n")
        res = da.align_fasta(q, q)  # align against itself
        assert res["ok"], f"DIAMOND align failed: {res['reason']}"
        best = da.best_hit_per_query(res["hits"])
        assert "geneA" in best
        h = best["geneA"]
        assert h["pident"] >= 99.0, f"self-hit identity should be ~100%, got {h['pident']}"
        assert h.get("qcovhsp", 0) >= 99.0, f"self-hit coverage should be ~100%, got {h.get('qcovhsp')}"
    finally:
        import shutil as _sh
        _sh.rmtree(tmp, ignore_errors=True)
