"""v9.7.412 (Razzle Dazzle Rose): the caption field `group_denominators` must be a per-ROLE plotted-row
count, not one `rows=1` entry per tip. Guards the fix at tools/tree_bgc_overlay.py (three cuts open:
first flagged on .408) and its compatibility with the figure_policy validator (`rows=` + a digit)."""
from __future__ import annotations
import importlib.util, os, re
_TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "tree_bgc_overlay.py")
spec = importlib.util.spec_from_file_location("_tbo", _TOOL); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)

ROWS = [
    {"role": "STUDY", "strain": "AS-1"}, {"role": "STUDY", "strain": "AS-2"}, {"role": "STUDY", "strain": "AS-3"},
    {"role": "REFERENCE", "strain": "S. griseus"}, {"role": "REFERENCE", "strain": "S. albus"},
    {"role": "OUTGROUP", "strain": "K. setae"},
]

def test_counts_are_per_role_not_per_tip():
    text = mod.group_denominators(ROWS)
    assert "STUDY(rows=3;" in text and "REFERENCE(rows=2;" in text and "OUTGROUP(rows=1;" in text
    assert "rows=1; strain=" not in text          # the old per-tip hardcode is gone
    assert text.count("rows=") == 3                # one entry per ROLE, not per tip (6)

def test_every_strain_still_enumerated_and_order_canonical():
    text = mod.group_denominators(ROWS)
    for s in ("AS-1", "AS-2", "AS-3", "S. griseus", "S. albus", "K. setae"):
        assert s in text
    assert text.index("STUDY(") < text.index("REFERENCE(") < text.index("OUTGROUP(")

def test_caption_validator_rows_and_digit_contract():
    text = mod.group_denominators(ROWS).casefold()
    assert "rows=" in text and any(c.isdigit() for c in text)   # exactly what figure_policy checks

def test_unknown_role_sorted_after_canonical_and_deterministic():
    rows = ROWS + [{"role": "ZZ_CUSTOM", "strain": "x"}, {"role": "AA_CUSTOM", "strain": "y"}]
    a = mod.group_denominators(rows); b = mod.group_denominators(list(rows))
    assert a == b
    assert a.index("OUTGROUP(") < a.index("AA_CUSTOM(") < a.index("ZZ_CUSTOM(")
