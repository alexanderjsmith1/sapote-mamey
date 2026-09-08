"""Pin the clinker-consistency of bgc_reference_align (v9.7.298 correction).

Regression guard for the local-vs-global identity bug: the shipped v9.7.296/.297 tool aligned
LOCALLY and called a homolog on local %id + a 30% coverage floor, which overcounted distant/partial
homologs on a real cohort nucleoside BGC [Redacted — publication in preparation]. clinker uses GLOBAL identity with
a 0.3 cutoff; the corrected tool matches it (reporting 4 confident orthologs). These tests need no DB
or network -- they exercise the identity metric directly on synthetic sequences.
"""
import importlib.util, os, pytest
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "bgc_reference_align.py"

def _load():
    pytest.importorskip("Bio")
    spec = importlib.util.spec_from_file_location("bra", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m

def test_aligner_is_global():
    m = _load()
    a = m._aligner()
    assert a.mode == "global", "identity must be measured on a GLOBAL alignment to match clinker"

def test_global_identity_penalizes_partial_coverage():
    """A short identical block inside two otherwise-dissimilar proteins is a partial homolog:
    LOCAL identity over the block is ~100%, but GLOBAL identity over the full length is low.
    The corrected metric must report the low (global) number, so such a hit does NOT pass a 30% bar."""
    m = _load(); al = m._aligner()
    block = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQ"          # ~33 aa shared block
    filler1 = "G" * 110  # long dissimilar tail so the shared block is a minority of the length
    filler2 = "P" * 110
    s1 = block + filler1
    s2 = block + filler2
    score, gid, Lloc = m._score_pid(al, s1, s2)
    # block is ~40% of each sequence; global identity must be well under a 30% "confident" bar,
    # and far below the ~100% a local metric would report over the block.
    assert gid < 30, f"global identity should penalize partial coverage, got {gid:.1f}%"

def test_full_length_homolog_scores_confident():
    """Two nearly-identical full-length proteins must score as a confident (>=30%) global identity."""
    m = _load(); al = m._aligner()
    s1 = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVK"
    s2 = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVR"  # 1 substitution
    score, gid, Lloc = m._score_pid(al, s1, s2)
    assert gid >= 30, f"a near-identical pair must be confident, got {gid:.1f}%"
    assert gid > 90
