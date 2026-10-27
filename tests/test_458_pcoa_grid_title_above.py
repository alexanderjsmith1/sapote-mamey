"""458_pcoa_grid_title_above: --title-above draws grid-page panel titles above the frame (opt-in; default unchanged)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_flag_is_declared_and_passed_to_the_page():
    src = (ROOT / "tools" / "protein_pcoa_render.py").read_text()
    assert 'add_argument("--title-above", action="store_true"' in src
    assert 'title_above=bool(getattr(a, "title_above", False))' in src


def test_title_above_frees_the_corner_for_labels():
    src = (ROOT / "tools" / "protein_pcoa_render.py").read_text()
    assert 'blocked = [] if getattr(a, "title_above", False) else [' in src


def test_r_draws_title_above_only_when_asked():
    r = (ROOT / "tools" / "protein_pcoa_page.R").read_text()
    assert re.search(r'if \(isTRUE\(page\$title_above\)\) labs\(title = sp\$tag\) else annotate\("text"', r)
    assert 'plot.title = element_text(face = "bold", size = fs, hjust = 0' in r
