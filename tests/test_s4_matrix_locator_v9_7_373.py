"""v9.7.373 (BREAK-3) — the shared §4 matrix-table locator.

Codex's 2026-08-21 title decision: ONE shared locator used by both modeb_structure_gate and
modeb_publication_gate, accepting the canonical named-match heading and the legacy heading during
migration, scoped to §4, not fooled by an unrelated §4 table. Acceptance-contract point 5.
"""
from __future__ import annotations

from mamey.modeb_structure_gate import find_s4_matrix_block

_TABLE = (
    "| locus | nr accession | matched protein | organism | identity |\n"
    "|---|---|---|---|---|\n"
    "| ctg1_1 | WP_1 | enzyme | Nocardia testii | 90% |\n"
)


def _s4(heading: str) -> str:
    return f"Intro prose.\n\n#### {heading}\n\n{_TABLE}\n#### Next subsection\nother content\n"


def test_canonical_named_match_title_is_located():
    block = find_s4_matrix_block(_s4("Complete named-match, channel-separated table"))
    assert block is not None and "ctg1_1" in block
    # scoped: the block stops at the next #### and does not swallow the next subsection
    assert "Next subsection" not in block


def test_named_match_gene_table_variant_is_located():
    block = find_s4_matrix_block(_s4("Complete named-match, channel-separated gene table"))
    assert block is not None and "ctg1_1" in block


def test_legacy_blastp_matrix_title_is_accepted():
    block = find_s4_matrix_block(_s4("Complete channel-separated BLASTp matrix"))
    assert block is not None and "ctg1_1" in block


def test_missing_matrix_heading_returns_none():
    # a §4 with a table but no matrix heading is NOT located (caller emits the MISSING finding)
    assert find_s4_matrix_block(f"Intro prose.\n\n{_TABLE}") is None


def test_unrelated_s4_table_is_not_mistaken_for_the_matrix():
    body = (
        "#### Some other subsection\n\n"
        "| a | b |\n|---|---|\n| 1 | 2 |\n"
    )
    assert find_s4_matrix_block(body) is None


def test_empty_body_returns_none():
    assert find_s4_matrix_block("") is None
    assert find_s4_matrix_block(None) is None
