"""v9.7.384 (BLACK_CHERRY-384-01): §4 publication gate resolves the gene column by header.

Regression guard. `.383` narrowed the §4 named-match gene-tag extraction from a whole-row search
to `matrix_gene_tag(row[0])` (column 0 only). A matrix that leads with the mandated identity
columns (`strain / node / region / BGC`) then yields the same column-0 value on every row and
falsely trips PUBLICATION_GENE_TABLE_DUPLICATE — exactly the table shape the Mode B audits
instruct lanes to write. The fix resolves the column whose header contains "gene"/"locus",
falling back to column 0 when neither is present (legacy tables keep working).

Fail-before (col-0 hardcoded): the identity-led case reports PUBLICATION_GENE_TABLE_DUPLICATE.
Pass-after (header-resolved): it does not.
"""
from __future__ import annotations

from mamey.modeb_publication_gate import _contiguous_homology_table_findings

_HEADING = "#### Complete named-match, channel-separated table"


def _codes(section4: str) -> set[str]:
    return {f["code"] for f in _contiguous_homology_table_findings(section4, None)}


def test_identity_led_matrix_is_not_falsely_flagged_duplicate():
    # Gene lives in a later column; column 0 is the strain identity (same on every row).
    s4 = (
        "Intro.\n\n" + _HEADING + "\n\n"
        "| strain | node | region | BGC | gene | nr accession | organism | identity |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | ctg9_18 | WP_1 | Nocardia | 90% |\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | ctg9_19 | WP_2 | Nocardia | 85% |\n"
        "#### Next subsection\nother\n"
    )
    assert "PUBLICATION_GENE_TABLE_DUPLICATE" not in _codes(s4)


def test_identity_led_matrix_with_a_real_repeat_still_flags_duplicate():
    # A genuine duplicate in the gene column must still be caught (fix doesn't blind the check).
    s4 = (
        "Intro.\n\n" + _HEADING + "\n\n"
        "| strain | node | region | BGC | gene | nr accession | organism | identity |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | ctg9_18 | WP_1 | Nocardia | 90% |\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | ctg9_18 | WP_2 | Nocardia | 85% |\n"
        "#### Next subsection\nother\n"
    )
    assert "PUBLICATION_GENE_TABLE_DUPLICATE" in _codes(s4)


def test_legacy_gene_first_matrix_still_works():
    # Column 0 IS the gene (no identity header) — fallback path, distinct genes, no false duplicate.
    s4 = (
        "Intro.\n\n" + _HEADING + "\n\n"
        "| locus | nr accession | matched protein | organism | identity |\n"
        "|---|---|---|---|---|\n"
        "| ctg1_1 | WP_1 | enzyme | Nocardia testii | 90% |\n"
        "| ctg1_2 | WP_2 | enzyme | Nocardia testii | 88% |\n"
        "#### Next subsection\nother\n"
    )
    assert "PUBLICATION_GENE_TABLE_DUPLICATE" not in _codes(s4)
