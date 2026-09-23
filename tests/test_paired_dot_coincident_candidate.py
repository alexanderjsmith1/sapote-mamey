import xml.etree.ElementTree as ET

from mamey.interactive_figures.figure_set_renderer import Chart, render_svg


SVG = "{http://www.w3.org/2000/svg}"


def _chart(a, b):
    return Chart(
        "TEST",
        "paired_dot",
        "Coincident values",
        "Both series must remain visible",
        [{"category": "row", "governed": a, "all_packaged": b}],
        {
            "category": "category",
            "a": "governed",
            "b": "all_packaged",
            "a_label": "Governed",
            "b_label": "All packaged",
        },
    )


def test_coincident_pair_uses_ring_and_core_at_one_true_coordinate():
    root = ET.fromstring(render_svg(_chart(5, 5)))
    coincident = [
        node for node in root.findall(f".//{SVG}circle")
        if node.attrib.get("data-coincident") == "true"
    ]
    assert len(coincident) == 2
    assert {(node.attrib["cx"], node.attrib["cy"]) for node in coincident} == {
        (coincident[0].attrib["cx"], coincident[0].attrib["cy"])
    }
    assert {node.attrib.get("data-series") for node in coincident} == {"a", "b"}
    assert any(node.attrib.get("fill") == "none" for node in coincident)
    assert any(node.attrib.get("fill") != "none" for node in coincident)


def test_distinct_pair_remains_two_positioned_points():
    root = ET.fromstring(render_svg(_chart(3, 5)))
    points = [
        node for node in root.findall(f".//{SVG}circle")
        if node.attrib.get("data-series") in {"a", "b"}
        and node.attrib.get("data-legend") != "true"
    ]
    assert len(points) == 2
    assert len({node.attrib["cx"] for node in points}) == 2
    assert not any(node.attrib.get("data-coincident") == "true" for node in points)
