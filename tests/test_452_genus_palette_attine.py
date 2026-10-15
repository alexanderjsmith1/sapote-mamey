"""v9.7.452: the attine set of mamey/data/genus_palette.json carries the genus colours the owner accepted on 6 Oct for the
attine figures, so those genera no longer all fall back to one grey. Data only; no study IDs."""
import json
import re
from pathlib import Path

PAL = Path(__file__).resolve().parents[1] / "mamey" / "data" / "genus_palette.json"


def test_attine_set_colours_are_distinct_valid_and_not_the_fallback():
    cfg = json.loads(PAL.read_text())
    att = cfg["sets"]["attine"]
    for g in ("Pseudonocardiaceae", "Phytohabitans", "Brachybacterium", "Mycobacterium", "Gordonia", "Citrobacter"):
        assert g in att, g
    assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", c) for c in att.values())
    assert cfg["fallback"] not in att.values()
    # family-level label and its long form share one colour; every other colour in the set is distinct from the rest of the
    # set and from the default colours of the genera the set does not override
    assert att["Pseudonocardiaceae"] == att["Pseudonocardiaceae bacterium"]
    mine = {g: c.upper() for g, c in att.items() if g != "Pseudonocardiaceae bacterium"}
    assert len(mine) == len(set(mine.values())), "two genera in the attine set share a colour"
    # known, accepted overlap: Gordonia's accepted attine colour equals the house Streptosporangium colour (no attine
    # isolate is Streptosporangium); any other overlap with the house colours fails
    clash = {(g, h) for g, c in mine.items() for h, d in cfg["default"].items() if h not in att and d.upper() == c}
    assert clash <= {("Gordonia", "Streptosporangium")}, clash
