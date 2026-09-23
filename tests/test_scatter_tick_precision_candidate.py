"""Distinct scatter tick coordinates need distinct readable tick labels."""
from xml.etree import ElementTree as ET
import pytest
from mamey.interactive_figures.figure_set_renderer import Chart, render_svg

@pytest.mark.parametrize("offset", [0.0, 100000000.0])
def test_distinct_tick_labels_for_small_range(offset):
    chart = Chart("TEST", "scatter", "Precision", "", [{"name": "A", "x": offset + 1, "y": 0}, {"name": "B", "x": offset + 1.001, "y": 0.005}], {"x": "x", "y": "y", "label": "name", "x_label": "x", "y_label": "y"})
    root = ET.fromstring(render_svg(chart))
    ticks = [n.text for n in root.findall(".//{http://www.w3.org/2000/svg}text") if n.get("font-size") == "9" and n.get("text-anchor") == "middle"]
    assert len(ticks) == 6
    assert len(set(ticks)) == len(ticks), ticks
    values = [float(t) for t in ticks]
    assert values == sorted(values)
