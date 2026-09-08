"""test_literature_lookup.py — the in-bundle full-abstract corpus reader (.345)."""
import json
from pathlib import Path

import pytest

from mamey import literature_lookup as ll


def _corpus(tmp_path):
    recs = [
        {"pmid": "111", "year": "2026", "doi": "10.1/x", "title": "Antifungal lasso peptide from Streptomyces",
         "abstract": "A novel lasso peptide with antifungal activity against Candida was characterised.",
         "queries": ["streptomyces lasso peptide"]},
        {"pmid": "222", "year": "2024", "doi": "", "title": "Nocardia siderophore genomics",
         "abstract": "Genome mining of Nocardia revealed a siderophore biosynthetic gene cluster.",
         "queries": ["nocardia"]},
        {"pmid": "333", "year": "2025", "doi": "", "title": "Micromonospora enediyne survey",
         "abstract": "", "queries": ["micromonospora"]},
    ]
    p = tmp_path / "literature_corpus.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in recs) + "\n", encoding="utf-8")
    return str(p)


def setup_function(_):
    ll.load_corpus.cache_clear()


def test_load_and_lookup(tmp_path):
    c = _corpus(tmp_path)
    assert ll.stats(c)["records"] == 3
    r = ll.lookup("111", c)
    assert r and r["year"] == "2026"
    assert "Candida" in ll.abstract_for("111", c)
    assert ll.lookup("999", c) is None
    assert ll.abstract_for("333", c) == ""  # entry with no abstract


def test_search_and(tmp_path):
    c = _corpus(tmp_path)
    hits = ll.search("antifungal AND Candida", path=c)
    assert [h["pmid"] for h in hits] == ["111"]
    # AND with a term absent everywhere -> no hits
    assert ll.search("antifungal AND enediyne", path=c) == []


def test_search_or_and_ranking(tmp_path):
    c = _corpus(tmp_path)
    hits = ll.search("siderophore OR lasso", path=c)
    assert {h["pmid"] for h in hits} == {"111", "222"}


def test_absent_corpus_degrades(tmp_path):
    missing = str(tmp_path / "nope.jsonl")
    assert ll.load_corpus(missing) == {}
    assert ll.lookup("111", missing) is None
    assert ll.search("anything", path=missing) == []
    assert ll.stats(missing)["corpus_present"] is False


def test_real_bundle_corpus_present():
    # the shipped corpus should resolve next to the package (skip if purged for a public tier)
    ll.load_corpus.cache_clear()
    if not ll.corpus_path().exists():
        pytest.skip("corpus purged (public tier)")
    s = ll.stats()
    assert s["records"] > 0 and s["corpus_present"]
