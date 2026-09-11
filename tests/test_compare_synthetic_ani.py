"""Offline self-verification of the Gemini ANI (S2) path using a synthetic fixture.

Uses tests/fixtures/synthetic_strainA/B.fasta — a small (~200 kb) synthetic two-strain pair
built at ~3% divergence, so ANI lands in the same-species range by construction. This lets
the S1/S2 path self-verify with NO real genome and NO network. Skips cleanly if pyfastani is
not installed (offline wheels not yet applied).
"""

import os

import pytest

pyfastani = pytest.importorskip("pyfastani")
_FIX = os.path.join(os.path.dirname(__file__), "fixtures")


def _load(fn):
    from Bio import SeqIO
    return [(r.id, str(r.seq)) for r in SeqIO.parse(fn, "fasta")]


def test_synthetic_fixtures_exist():
    assert os.path.exists(os.path.join(_FIX, "synthetic_strainA.fasta"))
    assert os.path.exists(os.path.join(_FIX, "synthetic_strainB.fasta"))


def test_ani_path_same_species_by_construction():
    a = _load(os.path.join(_FIX, "synthetic_strainA.fasta"))
    b = _load(os.path.join(_FIX, "synthetic_strainB.fasta"))
    sk = pyfastani.Sketch()
    sk.add_draft("B", [s.encode() for _, s in b])
    mapper = sk.index()
    hits = list(mapper.query_draft([s.encode() for _, s in a]))
    assert hits, "fixture should produce an ANI hit"
    # built at ~3% divergence -> same-species range (>=95%)
    assert hits[0].identity >= 95.0


def test_compute_ani_prefers_available_backend():
    from mamey import gemini as g
    a = _load(os.path.join(_FIX, "synthetic_strainA.fasta"))
    b = _load(os.path.join(_FIX, "synthetic_strainB.fasta"))
    res = g.compute_ani([s for _, s in a], [s for _, s in b])
    assert res["ok"] is True
    assert res["backend"] in {"pyskani", "pyfastani"}
    assert res["ani"] >= 95.0
    assert res["aligned_fraction"] is not None  # standing rule: ANI never without aligned fraction
