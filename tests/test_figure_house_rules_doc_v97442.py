"""The figure house rules page must stay true about what enforces each rule.

`docs/FIGURE_HOUSE_RULES.md` gathers rules that were settled one at a time and kept in chat and
session notes, where a new session could not see them. Its value depends on one thing: when it
says a rule is checked by a named tool or symbol, that tool or symbol has to exist. A page that
names checks that are not there is worse than no page, because it tells the reader a rule is
enforced when nothing enforces it.

These tests read the page, pull out every bundle path and dotted symbol it names in the
"Checked by" column, and check each one against the tree.
"""
import importlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "FIGURE_HOUSE_RULES.md"


def _checked_by_cells():
    rows = []
    for line in DOC.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 4 and cells[0].isdigit():
            rows.append((int(cells[0]), cells[3]))
    return rows


def test_the_page_exists_and_is_reachable_from_both_front_doors():
    assert DOC.is_file()
    assert "docs/FIGURE_HOUSE_RULES.md" in (ROOT / "CURRENT_DOCS_INDEX.md").read_text()
    assert "FIGURE_HOUSE_RULES.md" in (ROOT / "docs" / "FIGURES_START_HERE.md").read_text()


def test_every_rule_row_is_numbered_in_order_and_names_a_checker():
    rows = _checked_by_cells()
    assert [n for n, _ in rows] == list(range(1, len(rows) + 1))
    assert len(rows) >= 10
    for n, cell in rows:
        assert cell, f"rule {n} has an empty 'Checked by' cell; write 'By hand.' if nothing checks it"


def test_every_named_path_in_checked_by_exists():
    for n, cell in _checked_by_cells():
        for rel in re.findall(r"`((?:tools|mamey|docs)/[^`]+)`", cell):
            assert (ROOT / rel).is_file(), f"rule {n} names `{rel}`, which is not in the bundle"


def test_every_named_symbol_in_checked_by_resolves():
    for n, cell in _checked_by_cells():
        for dotted in re.findall(r"`(mamey(?:\.\w+)+)`", cell):
            module, _, attr = dotted.rpartition(".")
            mod = importlib.import_module(module)
            assert hasattr(mod, attr), f"rule {n} names `{dotted}`, which does not exist"


def test_the_page_carries_no_version_stamp_of_its_own():
    """A new unowned version field is the rotting-header failure test_docs_currency_stamp_lock guards."""
    text = DOC.read_text()
    assert not re.search(r"engine Mamey \d|Mamey engine \d|v9\.7\.\d+", text)


def test_the_owner_profile_is_marked_as_study_specific():
    text = DOC.read_text()
    assert "## Owner study profile" in text
    assert "For a different study, replace them" in text
