"""Unlisted docs about the retired §1–§20 Mode B contract say so in their first line."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIRED = ["docs/FULL_MODEB_20_SECTION_CONTRACT_v97144.md", "docs/MODE_B_20_SECTION_CANONICAL_TITLES.md",
           "docs/MODE_B_FULL20_CONTRACT_RECONCILIATION.md", "docs/ACCEPTANCE_TESTS_MODE_B_FULL20_CONTRACT.md"]


def test_retired_contract_docs_are_marked_in_their_title():
    for rel in RETIRED:
        first = (ROOT / rel).read_text(encoding="utf-8").splitlines()[0]
        assert "DEPRECATED" in first or "HISTORICAL" in first, rel


def test_retired_contract_docs_are_not_listed_as_current():
    index = (ROOT / "CURRENT_DOCS_INDEX.md").read_text(encoding="utf-8")
    for rel in RETIRED:
        assert rel not in index, rel
