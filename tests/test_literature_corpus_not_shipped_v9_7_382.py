"""test_literature_corpus_not_shipped_v9_7_382.py — public-release wheel-content guard.

P0-3 (Codex GitHub due-diligence): the per-genus / per-family literature digests and the
full-abstract corpus are DERIVED from a third-party PubMed/PMC abstract export and must NOT ship in
the public release. Only the fetch/curate TOOLING and the corpus METADATA (PMID/DOI manifest) may
ship, so a user can regenerate the knowledge base from their own PubMed access.

These assertions run against the *installed* package tree (what a wheel would contain), so they fail
if corpus prose is ever re-committed under mamey/data/literature/.
"""
from pathlib import Path

import mamey
from mamey import literature_lookup as ll

LIT = Path(mamey.__file__).resolve().parent / "data" / "literature"

# Genus digests that previously shipped (corpus-derived prose) — must all be absent.
_PURGED_GENUS = (
    "Actinophytocola.md", "Amycolatopsis.md", "Micromonospora.md", "Nocardia.md",
    "Saccharopolyspora.md", "Streptomyces.md", "Streptosporangium.md",
)


def test_no_genus_prose_ships():
    present = [n for n in _PURGED_GENUS if (LIT / n).exists()]
    assert present == [], f"corpus-derived genus prose must not ship: {present}"


def test_no_family_prose_ships():
    fam = LIT / "_families"
    stragglers = sorted(p.name for p in fam.glob("*.md")) if fam.exists() else []
    assert stragglers == [], f"corpus-derived family prose must not ship: {stragglers}"


def test_full_abstract_corpus_not_shipped():
    # the JSONL corpus with full abstract text is the primary redistribution risk
    assert not (LIT / "_corpus" / "literature_corpus.jsonl").exists(), \
        "full-abstract literature corpus must not ship in the public release"


def test_only_readmes_survive_as_markdown():
    # defensive: the only .md left anywhere under literature/ are README files
    non_readme = sorted(
        str(p.relative_to(LIT)) for p in LIT.rglob("*.md") if p.name != "README.md"
    )
    assert non_readme == [], f"unexpected markdown under literature/: {non_readme}"


def test_fetch_tooling_and_metadata_are_kept():
    # the regeneration path must remain: fetch/curate tools + the PMID/DOI metadata manifest
    corpus = LIT / "_corpus"
    for keep in ("pubmed_ingest.py", "curate_kb.py", "_manifest.json"):
        assert (corpus / keep).exists(), f"regeneration asset missing: _corpus/{keep}"


def test_consumer_degrades_when_corpus_absent():
    # with the corpus purged the reader resolves a path but returns an empty knowledge base
    ll.load_corpus.cache_clear()
    if ll.corpus_path().exists():  # an operator-provisioned corpus is allowed; skip if present
        import pytest
        pytest.skip("a literature corpus is provisioned in this environment")
    assert ll.load_corpus() == {}
    assert ll.stats()["corpus_present"] is False
