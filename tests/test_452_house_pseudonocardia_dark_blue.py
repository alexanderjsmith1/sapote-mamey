"""House Pseudonocardia dark blue, the attine Taibaiella colour, and the colour-vision check in
tools/palette_distance_report.py (card .452 house_pseudonocardia_dark_blue).

The owner ruled (13 Oct) that Pseudonocardia is dark blue in every figure, and Taibaiella, which held the attine dark blue,
gets its own colour. The report tool now also simulates protan, deutan and tritan vision (Machado, Oliveira & Fernandes
2009) and can fail named pairs that fall too close as seen with a deficiency. Synthetic palette for the tool tests.
"""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("palette_distance_report_452p", HERE / "tools" / "palette_distance_report.py")
pdr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pdr)
PAL = json.loads((HERE / "mamey" / "data" / "genus_palette.json").read_text())
NEIGHBOURS = ("Streptomyces", "Kribbella", "Amycolatopsis")


# Owner ruling 223 (20 Oct), after seeing both colours side by side: the Moss paper keeps Pseudonocardia orange.
# It is the one set allowed to override the house dark blue (card v9.7.461).
SET_OVERRIDES = {"moss": "#F28E2B"}


def test_house_pseudonocardia_is_dark_blue_in_every_set():
    assert PAL["default"]["Pseudonocardia"] == "#14325C"
    for name, s in PAL.get("sets", {}).items():
        if name in SET_OVERRIDES:
            assert s.get("Pseudonocardia") == SET_OVERRIDES[name], f"set {name} must pin Pseudonocardia {SET_OVERRIDES[name]}"
        else:
            assert "Pseudonocardia" not in s, f"set {name} overrides the house Pseudonocardia colour"
    assert PAL["sets"]["attine"]["Taibaiella"] == "#73112E"


def test_simulation_keeps_white_and_black_and_merges_red_green():
    for k in pdr.CVD:
        assert pdr.simulate("#FFFFFF", k) == "#FFFFFF" and pdr.simulate("#000000", k) == "#000000"
    normal = pdr.de2000("#D62728", "#2CA02C")
    assert pdr.de2000(pdr.simulate("#D62728", "deutan"), pdr.simulate("#2CA02C", "deutan")) < normal / 2


def test_pseudonocardia_stays_apart_from_its_neighbours_with_cvd():
    rows = pdr.resolve(PAL, "attine", ["Pseudonocardia", *NEIGHBOURS])
    pairs, fails = pdr.check(rows, cvd=("protan", "deutan", "tritan"), min_de_cvd=20.0,
                             cvd_pairs=[("Pseudonocardia", n) for n in NEIGHBOURS])
    assert not fails, fails
    assert {p["b"] if p["a"] == "Pseudonocardia" else p["a"] for p in pairs if "Pseudonocardia" in (p["a"], p["b"])} == set(NEIGHBOURS)
    assert all("dE00_tritan" in p for p in pairs)


def test_cvd_threshold_fails_only_the_named_pairs(tmp_path):
    pal = {"default": {"SynRed": "#D62728", "SynGreen": "#2CA02C", "SynBlue": "#1F3A93"}, "fallback": "#8C8C8C", "sets": {}}
    rows = pdr.resolve(pal, None, ["SynRed", "SynGreen", "SynBlue"])
    _, fails = pdr.check(rows, cvd=("deutan",), min_de_cvd=30.0)
    assert any("SynGreen" in f and "SynRed" in f and "deutan" in f for f in fails)
    _, fails = pdr.check(rows, cvd=("deutan",), min_de_cvd=30.0, cvd_pairs=[("SynBlue", "SynRed")])
    assert not any("SynGreen" in f for f in fails)
    _, fails = pdr.check(rows, cvd=("deutan",))                       # no threshold: reported, never failed
    assert not fails
    p = tmp_path / "pal.json"
    p.write_text(json.dumps(pal))
    rc = pdr.main(["--palette", str(p), "--genera", "SynRed,SynGreen", "--cvd", "deutan", "--min-de-cvd", "30",
                   "--cvd-pair", "SynRed,SynGreen", "--out", str(tmp_path / "r.tsv")])
    assert rc == 1
    assert "dE00_deutan" in (tmp_path / "r.tsv").read_text()
    assert "as seen with deutan" in (tmp_path / "r.md").read_text()
