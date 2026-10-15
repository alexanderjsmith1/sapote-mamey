"""Card attine_452_attine_palette_cvd_separation: four attine-only genus colours moved so no pair nearly merges for
protan or deutan readers.

Simulated colour-vision deficiency (tools/palette_distance_report.py --cvd) showed four attine pairs that nearly
merged: Streptomyces / Arboricoccus 0.3 (deutan), Pseudonocardiaceae / Amycolatopsis 2.8 (deutan), Pseudonocardiaceae /
Citrobacter 3.5 and Phytohabitans / Gordonia 3.7 (protan). Only attine-only colours move (Arboricoccus, Citrobacter,
Gordonia, Pseudonocardiaceae); house colours shared with other figure sets stay. Each moved colour is the one nearest
its old colour that keeps CIEDE2000 >= 12 in normal vision and >= 10 as seen with protan and deutan against every
other attine key. Synthetic data are not needed: the test reads the palette file.
"""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pdr_452cvd", HERE / "tools" / "palette_distance_report.py")
pdr = importlib.util.module_from_spec(spec); spec.loader.exec_module(pdr)
PAL = json.loads((HERE / "mamey" / "data" / "genus_palette.json").read_text())
ATTINE = ["Streptomyces", "Pseudonocardia", "Pseudonocardiaceae", "Brachybacterium", "Phytohabitans", "Tsukamurella",
          "Taibaiella", "Mycobacterium", "Microlunatus", "Microbacterium", "Kribbella", "Gordonia", "Dietzia",
          "Citrobacter", "Arboricoccus", "Amycolatopsis", "Advenella", "Actinophytocola"]
MOVED = {"Arboricoccus": "#9922DD", "Citrobacter": "#006655", "Gordonia": "#881111", "Pseudonocardiaceae": "#33AA88"}
HOUSE_KEPT = {"Streptomyces": "#1B7837", "Pseudonocardia": "#14325C", "Tsukamurella": "#A0522D", "Kribbella": "#54A24B",
              "Amycolatopsis": "#A6761D", "Actinophytocola": "#B5446E"}


def test_moved_colours_are_attine_only_and_house_colours_stay():
    att = PAL["sets"]["attine"]
    for g, h in MOVED.items():
        assert att[g] == h
    assert att["Pseudonocardiaceae bacterium"] == MOVED["Pseudonocardiaceae"]
    for g, h in HOUSE_KEPT.items():
        assert g not in att and PAL["default"][g] == h


def test_moved_keys_stay_apart_in_normal_protan_and_deutan_vision():
    rows = pdr.resolve(PAL, "attine", ATTINE, {"No 16S genus on record": "#DDE2E8"})
    pairs, fails = pdr.check(rows, min_de=10.0, grey_ok={"No 16S genus on record"}, cvd=("protan", "deutan"))
    assert not fails, fails
    for p in pairs:
        if MOVED.keys() & {p["a"], p["b"]}:
            assert p["dE00"] >= 12 and p["dE00_protan"] >= 10 and p["dE00_deutan"] >= 10, p
