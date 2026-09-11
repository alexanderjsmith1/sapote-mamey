"""Tests for extract_cluster (v9.7.301) — core logic without pyrodigal/network.

We inject a synthetic `prots` list (as genecall would return) so find_cluster / extract_gbk
are exercised directly, and confirm marker co-occurrence detection, windowing, GBK extraction,
and the present/absent threshold.
"""
import importlib.util
from pathlib import Path
import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "extract_cluster.py"


def _load():
    pyswrd = pytest.importorskip("pyswrd")
    pytest.importorskip("Bio")
    # v9.7.410: an import success is not proof of executability (mamey/compare.py learned the same
    # lesson in .409) — on the arm64 macOS venv `pyswrd.search` raises "no supported SIMD backend
    # available" from pyopal. That is an environment fact, not an extract_cluster defect: skip.
    try:
        list(pyswrd.search(["MKVLAAGIVALLLAAGCS"], ["MKVLAAGIVALLLAAGCS"], max_evalue=10, max_alignments=1))
    except RuntimeError as exc:
        if "SIMD" in str(exc):
            pytest.skip(f"pyswrd/pyopal cannot align on this build: {exc}")
        raise
    spec = importlib.util.spec_from_file_location("ec", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


# three distinct marker proteins
MARK_A = "MKTAYIAKQRQISFVKSHFSRQLEERLGLIEVQAPILSRVGDGTQDNLSGAEKAVQVKVKALPDAQFEVVHSLAKWKR"
MARK_B = "MPQLAFDIGFFAELPKLQPPVRRGVLEAWEKFDRLTLDQLFRDPGLKLESLKNARDKQIRTIRIDRFWRGVVLAPPSG"
MARK_C = "MSDNKQTLVRALKAGDLTAAEELLADLGVDVNAQDDDGRTPLHLAAYNGHLEIVKLLLAKGADVNAKDNDGWTPLHA"
NOISE = "MGGGGGGKKKKKKPPPPPPWWWWWWDDDDDDEEEEEEFFFFFFHHHHHHIIIIIILLLLLLNNNNNNQQQQQQRRRRRR"


def _synthetic_prots():
    # contig1: markers co-localise at genes 40-42; noise elsewhere. contig2: only noise.
    prots = []
    for i in range(1, 60):
        aa = {40: MARK_A, 41: MARK_B, 42: MARK_C}.get(i, NOISE)
        prots.append(("contig1", i, i * 1000, i * 1000 + 900, 1, aa))
    for i in range(1, 20):
        prots.append(("contig2", i, i * 1000, i * 1000 + 900, 1, NOISE))
    seqs = {"contig1": "A" * 62000, "contig2": "A" * 22000}
    return prots, seqs


def test_find_cluster_locates_marker_window():
    m = _load()
    prots, seqs = _synthetic_prots()
    markers = [("markA", MARK_A), ("markB", MARK_B), ("markC", MARK_C)]
    cl = m.find_cluster(prots, markers, min_identity=90, window=25)
    assert cl is not None
    assert cl["contig"] == "contig1"
    assert cl["n_markers"] == 3
    assert 40 <= cl["gene_start"] <= 42


def test_extract_gbk_labels_markers():
    m = _load()
    prots, seqs = _synthetic_prots()
    markers = [("nikJ", MARK_A), ("EPSP", MARK_B), ("oxy", MARK_C)]
    cl = m.find_cluster(prots, markers, min_identity=90, window=25)
    rec, (lo, hi) = m.extract_gbk(prots, seqs, cl, "TESTSTRAIN", flank=2)
    labels = [f.qualifiers.get("gene", [None])[0] for f in rec.features]
    assert "nikJ" in labels and "EPSP" in labels and "oxy" in labels
    assert all(f.qualifiers["locus_tag"][0].startswith("TESTSTRAIN_") for f in rec.features)


def test_present_absent_threshold():
    m = _load()
    prots, seqs = _synthetic_prots()
    # markers present -> PRESENT
    markers = [("nikJ", MARK_A), ("EPSP", MARK_B)]
    cl = m.find_cluster(prots, markers, min_identity=90, window=25)
    assert cl["n_markers"] >= 2
    # a marker set that is NOT in the genome -> not found / below threshold
    absent = [("ghostA", "WYWYWYWYWYWYWYWYWYWYCMCMCMCMCMCMCMCMCMCMKPKPKPKPKPKPKPKPKPKP")]
    cl2 = m.find_cluster(prots, absent, min_identity=90, window=25)
    assert cl2 is None or cl2["n_markers"] == 0
