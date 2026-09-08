"""v9.7.372: current reference exemplar is full48, clean, and distribution-stamp free."""
from pathlib import Path

from mamey.modeb_structure_gate import extract_section_titles, lint_card, load_contract


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs/reference/modeb_exemplars/phosphonate_reference_full48_no_blastp_exemplar.md"


def test_reference_exemplar_has_exact_full48_sequence_and_titles():
    text = CARD.read_text(encoding="utf-8")
    got = extract_section_titles(text)
    contract = load_contract()
    expected = [(row["number"], row["title"]) for row in contract["sections"]]
    assert got == expected


def test_reference_exemplar_has_all_23_canonical_genes_once():
    text = CARD.read_text(encoding="utf-8")
    genes = [
        "KSE_RS11105", "KSE_RS11110", "KSE_RS11115", "KSE_RS11120", "KSE_RS11125",
        "KSE_RS11130", "KSE_RS11135", "KSE_RS11140", "KSE_RS11145", "KSE_RS39880",
        "KSE_RS11155", "KSE_RS43800", "KSE_RS43805", "KSE_RS11170", "KSE_RS11175",
        "KSE_RS11180", "KSE_RS11185", "KSE_RS11190", "KSE_RS11195", "KSE_RS11200",
        "KSE_RS11205", "KSE_RS11210", "KSE_RS11215",
    ]
    table = text.split("| Order | Gene |", 1)[1].split("No independent nr", 1)[0]
    assert all(table.count(gene) == 1 for gene in genes)


def test_reference_exemplar_avoids_distribution_stamps_and_work_placeholders():
    text = CARD.read_text(encoding="utf-8")
    assert "PUBLIC" not in text
    assert "PRIVATE" not in text
    assert "pending" not in text.lower()


def test_reference_exemplar_clears_current_structure_and_depth_gate():
    text = CARD.read_text(encoding="utf-8")
    assert lint_card(text, check_depth=True) == []
