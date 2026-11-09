"""mamey/data/genus_palette.json: Actinacidiphila and Pseudonocardia must be told apart."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pdr465", ROOT / "tools/palette_distance_report.py")
pdr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pdr)


def test_actinacidiphila_is_not_a_second_navy():
    d = json.loads((ROOT / "mamey/data/genus_palette.json").read_text())["default"]
    a = d["Actinacidiphila"]
    assert pdr.chroma(a) >= 25
    for g, c in d.items():
        if g in ("Actinacidiphila", "Unassigned", "No 16S sequence", "No 16S genus on record"):
            continue
        assert pdr.de2000(a, c) >= 10, (g, c)
    for kind in ("protan", "deutan", "tritan"):
        assert pdr.de2000(pdr.simulate(a, kind), pdr.simulate(d["Pseudonocardia"], kind)) >= 10
