"""The thesis method diagram does not say the pan-BGC-ome is "not saturated".

Owner ruling (G1): the .459 card removed this sentence from the pangenome summary because the data did not
support it; tools/build_thesis_diagrams.py still drew it on the method diagram.
"""
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "tools" / "build_thesis_diagrams.py"


def test_no_saturation_wording_in_the_diagram_source():
    text = SRC.read_text(encoding="utf-8").lower()
    assert "saturated" not in text
    assert "pan-bgc-ome / novelty" in text     # the node itself is still drawn
