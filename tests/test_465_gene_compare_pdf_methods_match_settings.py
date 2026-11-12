"""The gene-comparison PDF methods paragraph must describe the run that produced it.

It used to say every CDS pair was aligned, whatever the engine, and it never named the coverage
cutoff. It also printed doubled percent signs.
"""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "cluster_gene_compare.py"


def _load():
    spec = importlib.util.spec_from_file_location("cgc_465_methods", TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_exhaustive_engine_says_every_pair_and_no_coverage_cutoff():
    text = _load().methods_alignment_text(30.0, 0.0, "biopython")
    assert "Every CDS was aligned to every CDS in every other cluster" in text
    assert "engine: biopython" in text
    assert "global identity >= 30.0%; no coverage cutoff was applied" in text
    assert "%%" not in text


def test_prefilter_engine_does_not_claim_every_pair_was_aligned():
    text = _load().methods_alignment_text(45.0, 60.0, "pyswrd")
    assert "Every CDS was aligned" not in text
    assert "max_evalue=1.0, max_alignments=25" in text
    assert "a pair the search did not return was not aligned" in text
    assert "engine: pyswrd" in text
    assert "global identity >= 45.0% and coverage >= 60.0%" in text
    assert "divided by the longer protein length" in text
    assert "%%" not in text


def test_search_parameters_in_the_text_are_the_ones_the_prefilter_uses():
    m = _load()
    assert "max_evalue=1.0, max_alignments=25" in inspect.getsource(m.prefilter)


def test_pdf_builder_receives_the_coverage_cutoff():
    m = _load()
    assert "min_cov" in inspect.signature(m.make_pdf).parameters
    assert "a.min_id, a.engine, a.min_cov)" in inspect.getsource(m.main)
