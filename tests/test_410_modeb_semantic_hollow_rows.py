"""v9.7.410 hostile audit — what a lazy author can get past the Mode B semantic gates.

Probed against Codex's own passing fixture (tests/test_modeb_semantic_sections_10_12_17_24_v97410):
generic filler is caught (§12 matched-test unspecific, §17 target mismatch), but a §12 row CLONED
with only the hypothesis / competing-explanation labels swapped satisfied "two distinct models".
That is closed here; the pass/fail boundary of the fixture itself is pinned so the new check cannot
drift into rejecting genuinely distinct rows.
"""
from __future__ import annotations

from mamey.modeb_publication_gate import publication_quality_findings
from tests.test_modeb_semantic_sections_10_12_17_24_v97410 import ROSTER, _replace, _structured_card

CLONE = "SECTION_12_HYPOTHESIS_ROWS_CLONED"
HEADER = ("#### Ecological hypothesis matrix\n"
          "| Ecological hypothesis | Locus-specific evidence | Evidence against | Competing explanation | Causality ceiling | Matched discriminating test |\n"
          "|---|---|---|---|---|---|\n")


def _codes(card: str) -> set[str]:
    return {r["code"] for r in publication_quality_findings(card, canonical_loci=ROSTER, check_semantic_sections_v3=True)}


def test_codex_fixture_still_passes_section_12():
    assert not {c for c in _codes(_structured_card()) if c.startswith("SECTION_12")}


def test_cloned_row_with_swapped_labels_is_rejected():
    card = _replace(_structured_card(), 12, HEADER +
        "| chemical competition | ctg1_1 exact-region biosynthetic role | no phenotype measured | nutrient acquisition | testable hypothesis only | matched wild type knockout and complement competition assay |\n"
        "| nutrient acquisition | ctg1_1 exact-region biosynthetic role | no phenotype measured | chemical competition | testable hypothesis only | matched wild type knockout and complement competition assay |\n")
    assert CLONE in _codes(card)


def test_rows_that_differ_in_evidence_or_test_are_not_clones():
    card = _replace(_structured_card(), 12, HEADER +
        "| chemical competition | ctg1_1 exact-region biosynthetic role | no phenotype measured | nutrient acquisition | testable hypothesis only | matched wild type knockout and complement competition assay |\n"
        "| nutrient acquisition | transport context beside ctg1_1 | substrate is unknown | chemical competition | source context not BGC causality | matched wild type knockout and complement competition assay |\n")
    assert CLONE not in _codes(card)


def test_generic_filler_is_still_caught_by_the_existing_checks():
    card = _replace(_structured_card(), 12, HEADER +
        "| model one | ctg1_1 annotation supports the model | none observed | model two | not established | targeted assay with matched controls |\n"
        "| model two | ctg1_1 context is consistent with the model | not measured | model one | remains a hypothesis | matched assay with knockout and complement |\n")
    assert "SECTION_12_MATCHED_TEST_UNSPECIFIC" in _codes(card)
