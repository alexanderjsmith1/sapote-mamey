"""Generated full48 contract pages state what the gates actually do.

- The obsolete `Manual BLASTP evidence, if present` heading fails only in a
  numbered slot; as a duplicate §1-§30 heading it is a WARN.
- Section sub-questions are not read by any check; depth findings are length
  checks whose severity depends on strict depth.
- The first-20 facade is `mamey/validators/modeb_full20.py`.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pages():
    spec = importlib.util.spec_from_file_location("regen_464r3c", ROOT / "tools/regen_modeb_contract_docs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    contract = mod.load_contract(mod._DEFAULT_CONTRACT)
    return mod.render_titles_doc(contract), mod.render_contract_doc(contract)


def test_obsolete_heading_rule_names_the_actual_findings():
    titles, _ = _pages()
    assert "must fail the current Full Mode B validator" not in titles
    assert "`TITLE_MISMATCH`" in titles and "`DUPLICATE_SECTION` WARN" in titles


def test_sub_questions_are_not_described_as_checked():
    _, contract = _pages()
    assert "treats them as WARN-only" not in contract
    assert "No check reads the answers" in contract
    assert "--no-strict-depth" in contract


def test_facade_is_named_correctly():
    _, contract = _pages()
    assert "`mamey/validators/modeb_full20.py`, loads that contract and keeps only §1–§20" in contract
