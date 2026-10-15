"""Card attine_452_panel_figure_letters_guard: gap_rescue_panel_figure.py refuses --letters that are not letters only.

--letters takes one string, one letter per panel. "A,B" was accepted and the comma became panel B's letter on a
composed page. Anything but letters, or a repeated letter, is now refused before any output is written. Synthetic data.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("matplotlib")
from PIL import Image  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
spec = importlib.util.spec_from_file_location("gpf_452lg", HERE / "tools" / "gap_rescue_panel_figure.py")
gpf = importlib.util.module_from_spec(spec); spec.loader.exec_module(gpf)


def _map(root, name):
    d = root / name
    d.mkdir(parents=True)
    Image.new("RGB", (2100, 600), "white").save(d / "gap_rescue.png", dpi=(300, 300))
    (d / "gap_rescue_key.json").write_text(json.dumps({"classes": ["other"], "class_unclear": False, "key": False}))
    return d


@pytest.mark.parametrize("letters", ["A,B", "a b", "a1", "aa"])
def test_non_letters_or_repeats_are_refused(tmp_path, letters):
    maps = [_map(tmp_path, "m1"), _map(tmp_path, "m2")]
    with pytest.raises(gpf.PanelFigureError, match="letters only"):
        gpf.compose(maps, tmp_path / "out" / "SYN", letters=letters)
    assert not (tmp_path / "out").exists()


def test_plain_letters_still_compose(tmp_path):
    maps = [_map(tmp_path, "m1"), _map(tmp_path, "m2")]
    info = gpf.compose(maps, tmp_path / "out" / "SYN", letters="AB")
    assert [p["letter"] for p in json.loads((tmp_path / "out" / "SYN_RUN_INFO.json").read_text())["panels"]] == ["A", "B"]
    assert info["pages"][0]["letters"] == "AB"
