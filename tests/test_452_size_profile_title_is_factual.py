"""The count-versus-size panel title describes what is plotted and claims no bound on a true value."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("size_profile_title", ROOT / "tools/build_size_profile.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_panel_title_is_a_description_of_the_plot():
    title = _load().FRAGMENTATION_PANEL_TITLE.lower()
    assert "correlation" in title and "fragmentation" in title
    assert "truth" not in title and "bracket" not in title


def test_withdrawn_wording_is_gone_from_the_tool():
    assert "bracket the truth" not in (ROOT / "tools/build_size_profile.py").read_text()
