"""Drawing rulings (rules 9, 10, 13): plain face for queries, strips off by default, figure id. Text guards on the shipped R script."""
from pathlib import Path
import pytest
RS = Path(__file__).resolve().parent.parent / "tools" / "ggtree_rect_heatmap.R"
def _s():
    assert RS.exists(), "renderer required"
    return RS.read_text()
def test_query_face_is_a_knob_defaulting_to_plain():
    s = _s(); assert 'Sys.getenv("GG_FOCAL_FACE", "plain")' in s and 'fontface = "bold", size = lsize' not in s
def test_strips_are_optional():
    s = _s(); assert 'Sys.getenv("GG_STRIPS"' in s
def test_figure_id_is_stamped():
    assert 'Sys.getenv("GG_FIGID")' in _s()
def test_no_machine_path():
    assert "/Users/" not in _s()
