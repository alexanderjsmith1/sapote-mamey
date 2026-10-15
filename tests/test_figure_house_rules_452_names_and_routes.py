"""Rules 11 and 12 of the figure house rules record two owner rulings of 12 Oct.

Rule 11: ordination pages label points with names (rule 6 form in the caption key), never numbers.
Rule 12: figures are drawn only through a sealed bundle route or a signed-off staged patch, after a
written rule check. These tests keep both rows on the page with their substance intact.
"""
from pathlib import Path

DOC = Path(__file__).resolve().parents[1] / "docs" / "FIGURE_HOUSE_RULES.md"


def _row(n):
    for line in DOC.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0] == str(n):
            return cells[1].lower()
    raise AssertionError(f"rule {n} is missing from {DOC.name}")


def test_rule_11_names_not_numbers_on_ordination_pages():
    rule = _row(11)
    assert "never with numbers" in rule
    assert "ordination" in rule and "caption key" in rule and "accession" in rule


def test_rule_12_sealed_route_and_written_rule_check():
    rule = _row(12)
    assert "sealed bundle route" in rule and "signed off" in rule
    assert "rule check" in rule and "proposal" in rule


def test_figure_style_doc_named_in_rule_12_exists():
    assert (DOC.parent / "FIGURE_STYLE.md").is_file()
