"""wishlist #1 (v9.7.206): count_modeb_cards enforces the §1–§30 structure gate in the
completeness path, so a structurally-invalid card cannot flip gold_completeness=COMPLETE.
Default (enforce_structure=False) preserves pure counting for the regex/dedup tests."""
import importlib.util, tempfile, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
_s = importlib.util.spec_from_file_location("sjr", ROOT/"tools"/"sapote_judgment_receipt.py")
sjr = importlib.util.module_from_spec(_s); _s.loader.exec_module(sjr)

def _bad_card(d):
    # has a BGC id (counts under raw) but no §1–§30 structure (fails lint_card)
    p = os.path.join(d, "bad.md")
    open(p, "w").write("<!-- MODE B: BGC001 -->\nbgc: BGC001\nno sections at all\n")
    return os.path.join(d, "*.md")

def test_invalid_card_not_counted_when_enforced():
    with tempfile.TemporaryDirectory() as d:
        g = _bad_card(d)
        assert sjr.count_modeb_cards([g], enforce_structure=True) == 0   # refused
        assert sjr.count_modeb_cards([g], enforce_structure=False) == 1  # raw count unchanged

def test_default_is_pure_count():
    with tempfile.TemporaryDirectory() as d:
        assert sjr.count_modeb_cards([_bad_card(d)]) == 1  # default preserves counting behavior
