"""v9.7.383: exact canonical matrix rosters accept non-ctg locus tags."""

from mamey.modeb_publication_gate import _contiguous_homology_table_findings
from mamey.modeb_structure_gate import _section4_complete_blastp_matrix_findings


ROSTER = ["ctg15_7", "allorf_013118_013336", "ABC_RS12345"]
S4 = """## §4 Gene-by-gene interpretation

#### Complete named-match, channel-separated table

| Gene / coordinates / SHA | NCBI nr accession + matched protein | nr identity / positives / query coverage | NCBI ClusteredNR accession + matched protein | ClusteredNR identity / positives / query coverage | local Swiss-Prot accession + matched protein | Swiss-Prot identity / positives / query coverage |
|---|---|---|---|---|---|---|
| `ctg15_7`; 1–189; SHA `abc` | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit |
| `allorf_013118_013336`; 190–408; SHA `def` | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit |
| `ABC_RS12345`; 409–999; SHA `ghi` | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit |
"""


def structure_codes(md: str, roster=ROSTER) -> list[str]:
    return [
        finding["code"]
        for finding in _section4_complete_blastp_matrix_findings(
            md,
            {"known_locus_tags": roster, "require_complete_blastp_matrix": True},
        )
    ]


def publication_codes(md: str, roster=ROSTER) -> list[str]:
    section4 = md.split("## §4", 1)[1]
    return [
        finding["code"]
        for finding in _contiguous_homology_table_findings(section4, roster)
    ]


def test_non_ctg_exact_roster_passes_both_gates():
    assert structure_codes(S4) == []
    assert publication_codes(S4) == []


def test_missing_allorf_row_fails_both_gates():
    row = "| `allorf_013118_013336`; 190–408; SHA `def` | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit |\n"
    card = S4.replace(row, "")
    assert structure_codes(card) == ["BLASTP_MATRIX_ROSTER"]
    assert publication_codes(card) == ["PUBLICATION_GENE_TABLE_ROSTER"]


def test_unexpected_non_ctg_row_is_reported_as_extra():
    row = "| `unexpected_precursor_1`; 1000–1100; SHA `jkl` | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit | no bound hit |\n"
    card = S4 + row
    assert structure_codes(card) == ["BLASTP_MATRIX_ROSTER"]
    assert publication_codes(card) == ["PUBLICATION_GENE_TABLE_ROSTER"]
