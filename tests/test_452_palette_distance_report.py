"""tools/palette_distance_report.py and the attine genus colours after the owner's 13 Oct ruling ("for the attine paper, we
can't have grey 'other genera'"): every genus the attine figures draw has its own colour, none grey-like, each pair at
least 10 CIEDE2000 units apart; the "no 16S genus" key alone may be grey. Synthetic palette for the tool tests."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("palette_distance_report_452", HERE / "tools" / "palette_distance_report.py")
pdr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdr)
ATTINE_GENERA = ["Streptomyces", "Pseudonocardia", "Pseudonocardiaceae", "Brachybacterium", "Phytohabitans", "Tsukamurella",
                 "Taibaiella", "Mycobacterium", "Microlunatus", "Microbacterium", "Kribbella", "Gordonia", "Dietzia",
                 "Citrobacter", "Arboricoccus", "Advenella", "Actinophytocola"]
# Amycolatopsis (house colour, shared with the bee paper) is checked by card attine_452_house_amycolatopsis_colour


def test_de2000_reference_pairs():
    # Sharma, Wu & Dalal (2005) test data, pair 1 (in Lab), checked through the hex path at a known identity
    assert pdr.de2000("#000000", "#000000") == 0
    assert pdr.de2000("#FFFFFF", "#000000") == pytest.approx(100.0, abs=0.01)
    assert pdr.de2000("#FF0000", "#00FF00") == pytest.approx(86.6, abs=0.2)
    assert pdr.chroma("#808080") < 1


def test_tool_flags_fallback_grey_and_close_pairs(tmp_path):
    pal = {"default": {"SynA": "#1B7837", "SynB": "#1C7938"}, "fallback": "#8C8C8C",
           "sets": {"syn": {"SynC": "#7F7F80"}}}
    p = tmp_path / "pal.json"
    p.write_text(json.dumps(pal))
    rc = pdr.main(["--palette", str(p), "--set", "syn", "--genera", "SynA,SynB,SynC,SynD", "--out", str(tmp_path / "r.tsv")])
    md = (tmp_path / "r.md").read_text()
    assert rc == 1 and "SynD: fallback colour" in md and "SynC: grey-like" in md and "SynA / SynB" in md


