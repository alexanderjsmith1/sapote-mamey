"""The house Amycolatopsis colour was grey-like (#9D755D, CIELAB chroma 23) and failed the attine figures' colour check
(owner, 13 Oct: no grey genus groups). It becomes #A6761D, a clearer brown-gold, in the house set, so every paper gives
the genus one colour. With it, every genus the attine figures draw passes the check."""
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("palette_distance_report_452h", HERE / "tools" / "palette_distance_report.py")
pdr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdr)
ATTINE_GENERA = ["Streptomyces", "Pseudonocardia", "Pseudonocardiaceae", "Brachybacterium", "Phytohabitans", "Tsukamurella",
                 "Taibaiella", "Mycobacterium", "Microlunatus", "Microbacterium", "Kribbella", "Gordonia", "Dietzia",
                 "Citrobacter", "Arboricoccus", "Amycolatopsis", "Advenella", "Actinophytocola"]


def test_house_amycolatopsis_is_not_grey_and_has_one_colour():
    pal = json.loads((HERE / "mamey" / "data" / "genus_palette.json").read_text())
    assert pal["default"]["Amycolatopsis"].upper() == "#A6761D"
    assert pdr.chroma("#A6761D") >= 25
    assert all("Amycolatopsis" not in s for s in pal["sets"].values())   # no per-paper override


def test_all_attine_figure_colours_pass(tmp_path):
    rc = pdr.main(["--set", "attine", "--genera", ",".join(ATTINE_GENERA), "--key", "No 16S genus on record=#DDE2E8",
                   "--grey-ok", "No 16S genus on record", "--out", str(tmp_path / "attine.tsv")])
    assert rc == 0, (tmp_path / "attine.md").read_text()
