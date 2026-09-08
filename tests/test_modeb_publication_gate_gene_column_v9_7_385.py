"""v9.7.385 (BLACK_CHERRY-384-02): §4 publication gate resolves the gene column among
MULTIPLE candidate headers by cell shape, not by header column order.

Regression guard. `.384` fixed the single-candidate case (a mandated identity-column-led
matrix) by picking the first header cell containing "gene"/"locus". But a real table can
have MORE THAN ONE header cell containing that substring -- e.g. a descriptive "Gene
context"/"Gene role" categorical column placed ahead of the true "Locus" identity column.
Picking the first substring match by column order (the `.384` behaviour) reintroduces the
exact bug class `.384` was written to close, just triggered by a different header shape:

  - false positive: many rows legitimately share the same descriptive category value
    ("core biosynthetic gene"), so distinct genes trip PUBLICATION_GENE_TABLE_DUPLICATE.
  - false negative (worse): a genuine duplicate locus tag is silently MASKED because the
    descriptive column's values differ row to row while the real locus column repeats.

Fail-before (first substring match wins): both cases misclassify.
Pass-after (digit-tagged-cell-shape disambiguation): both cases classify correctly.
"""
from __future__ import annotations

from mamey.modeb_publication_gate import _contiguous_homology_table_findings

_HEADING = "#### Complete named-match, channel-separated table"


def _codes(section4: str) -> set[str]:
    return {f["code"] for f in _contiguous_homology_table_findings(section4, None)}


def test_descriptive_gene_column_ahead_of_locus_is_not_falsely_flagged_duplicate():
    # "gene context" matches the substring test and sits BEFORE the real "locus" identity
    # column. Its values legitimately repeat across distinct genes; "locus" values do not.
    s4 = (
        "Intro.\n\n" + _HEADING + "\n\n"
        "| strain | node | region | BGC | gene context | locus | nr accession | organism | identity |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | core biosynthetic gene | ctg9_18 | WP_1 | Nocardia | 90% |\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | core biosynthetic gene | ctg9_19 | WP_2 | Nocardia | 85% |\n"
        "#### Next subsection\nother\n"
    )
    assert "PUBLICATION_GENE_TABLE_DUPLICATE" not in _codes(s4)


def test_real_duplicate_is_not_masked_by_an_earlier_descriptive_gene_column():
    # Same shape, but this time the true "locus" column DOES repeat (a genuine authoring
    # error -- one gene reconciled against two different top hits). The earlier "gene role"
    # column differs row to row, so a column-order-first resolver would silently miss it.
    s4 = (
        "Intro.\n\n" + _HEADING + "\n\n"
        "| strain | node | region | BGC | gene role | locus | nr accession | organism | identity |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | core biosynthetic gene | ctg9_18 | WP_1 | Nocardia | 90% |\n"
        "| AS-846 | NODE_9 | region001 | BGC005 | resistance gene | ctg9_18 | WP_2 | Nocardia | 85% |\n"
        "#### Next subsection\nother\n"
    )
    assert "PUBLICATION_GENE_TABLE_DUPLICATE" in _codes(s4)
    findings = _contiguous_homology_table_findings(s4, None)
    dup = next(f for f in findings if f["code"] == "PUBLICATION_GENE_TABLE_DUPLICATE")
    assert "ctg9_18" in dup["found"]
