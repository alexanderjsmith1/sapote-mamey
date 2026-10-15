"""tools/nearest_type_strain_map.py tip text and dots (card .452 nearest_type_map_text_colour).

The owner, 13 Oct: "it looks somewhat janky with the ball nodes at each tip end now that we have the text color coded.
Note the yellow in actinomycetospora is difficult to read." Tip names keep the genus colour, darkened toward black only
until they reach 4.5:1 contrast on white; the dots are off by default (--tip-dots restores them)."""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
spec = importlib.util.spec_from_file_location("ntm_text", HERE / "tools" / "nearest_type_strain_map.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def contrast(h):
    return 1.05 / (m._lum(h) + .05)


def test_light_colours_are_darkened_to_readable():
    for light in ("#EECA3B", "#D4A6C8", "#72B7B2", "#F28E2B"):
        out = m.text_colour(light)
        assert out != light.lower() and contrast(out) >= 4.5
        # same hue family: every channel scaled by one factor
        a = [int(light[i:i + 2], 16) for i in (1, 3, 5)]; b = [int(out[i:i + 2], 16) for i in (1, 3, 5)]
        r = [y / x for x, y in zip(a, b) if x > 20]
        assert max(r) - min(r) < 0.03


def test_dark_colours_unchanged():
    for dark in ("#0F4C5C", "#7E5AA2", "#1B7837"):
        assert m.text_colour(dark) == dark.lower()


def test_tip_dots_option_exists_and_defaults_off():
    import inspect
    assert inspect.signature(m.draw).parameters["tip_dots"].default is False
    assert "--tip-dots" in (HERE / "tools" / "nearest_type_strain_map.py").read_text()
