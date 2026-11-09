"""The generator-owned prose in the full48 contract page carries no release or card tags.

The closing block was titled "Single source of truth (W9-C / N10)" and told a
version history ("Before v9.7.150e ..."). Text taken from the JSON is not
checked here: that wording belongs to the contract owner.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _gen():
    spec = importlib.util.spec_from_file_location("regen_464r3", ROOT / "tools/regen_modeb_contract_docs.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_single_source_block_has_no_release_tags():
    mod = _gen()
    md = mod.render_contract_doc(mod.load_contract(mod._DEFAULT_CONTRACT))
    block = md.split("## Single source of truth", 1)[1]
    for tag in ("W9-C", "N10", "v9.7.150", "in CI"):
        assert tag not in block, tag
    assert "modeb_current50_v2_contract.json" in block


def test_both_pages_explain_the_historical_30_in_their_name():
    mod = _gen()
    contract = mod.load_contract(mod._DEFAULT_CONTRACT)
    for md in (mod.render_titles_doc(contract), mod.render_contract_doc(contract)):
        assert "The `30` in this page's file name is historical" in md
        assert "all 48 declared sections" in md


def test_shipped_page_matches_generator():
    mod = _gen()
    assert mod.main(["--check"]) == 0
