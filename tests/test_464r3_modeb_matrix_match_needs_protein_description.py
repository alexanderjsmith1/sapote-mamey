"""A §4/§50 named-match cell must carry a protein description, not only an organism.

`ABC123 — [Example organism]` used to pass BLASTP_MATRIX_SUBJECTS. The check is
syntax only: it does not bind the description to a saved BLASTp source.
"""
import mamey.modeb_structure_gate as G
from tests.test_modeb_complete_blastp_matrix_v9_7_372 import CTX, GOOD


def codes(md):
    return [x["code"] for x in G._section4_complete_blastp_matrix_findings(md, CTX)]


def test_accession_and_bracketed_organism_only_fails():
    bad = GOOD.replace("WP_000001 — synthase [Streptomyces examplei]", "WP_000001 — [Streptomyces examplei]")
    assert codes(bad) == ["BLASTP_MATRIX_SUBJECTS"]


def test_accession_and_bare_genus_only_fails():
    bad = GOOD.replace("WP_000001 — synthase [Streptomyces examplei]", "WP_000001 — Streptomyces examplei")
    assert codes(bad) == ["BLASTP_MATRIX_SUBJECTS"]


def test_description_with_organism_still_passes():
    assert codes(GOOD) == []
    ok = GOOD.replace("WP_000001 — synthase [Streptomyces examplei]",
                      "WP_000001 — hypothetical protein [Streptomyces examplei]")
    assert codes(ok) == []
