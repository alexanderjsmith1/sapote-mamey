"""v9.7.210 hygiene: #35 figure guards (collection_figures, locus_map) + #24 evaluate_card arg-order guard."""
import mamey.collection_figures as cf
import mamey.locus_map as lm
from mamey.mode_b_quality_gate import evaluate_card
import pytest

def test_collection_figures_guards_matplotlib():
    assert hasattr(cf, "_HAVE_MPL")   # import no longer crashes without matplotlib

def test_locus_map_guards_matplotlib():
    assert hasattr(lm, "_HAVE_MPL")

def test_evaluate_card_rejects_swapped_args():
    card = "## §1 Identity\n" + "domain PKS_KS content. " * 30   # long/multiline = looks like card text
    with pytest.raises(ValueError, match="swapped"):
        evaluate_card(card, "BGC007")          # args swapped
    # correct order still works
    v = evaluate_card("BGC007", card, rank=5)
    assert v.tier in ("FULL", "SHALLOW", "STUB")
