"""Card 452_bioassay_candida_split_and_label: A01 can draw C. albicans and C. auris as separate panels.

Owner, 12 Oct: split the two Candida species in the activity-by-genus figure. The layout profile key split_candida turns it on
(the moss profile has it); a01_drop_targets leaves named panels out (a figure-side choice). The unassigned row label comes
from the profile. Synthetic data only.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mamey.bioassay_paper import layout_profile, prepare, target_map, write  # noqa: E402


def _inputs(tmp_path, extra=None):
    roster = tmp_path / "roster.tsv"
    write(roster, [dict(strain="SYN-1", genus="Streptomyces", group="GroupA"), dict(strain="SYN-2", genus="Unassigned", group="GroupA")])
    rows = []
    for s in ("SYN-1", "SYN-2"):
        for org, v in (("Candida albicans", "90"), ("Candida auris", "10"), ("Candida (species not named)", "50"), ("MRSA", "85")):
            rows.append(dict(strain=s, organism=org, material="Crude extract", best_pct=v))
    table = tmp_path / "best.tsv"
    write(table, rows)
    aliases = tmp_path / "aliases.json"
    aliases.write_text("{}")
    prof = {"focal_group": "GroupA", "a06_subset_group": "GroupA", "split_larvae": False, "group_axis_label": "Source group",
            "unassigned_label": "No genus label", "plain_rows": [], "a03_genus_keep": None, "a03_source_shape": False,
            "a04_source_shape": False, "a02_width_in": 5.6, "a03_height_in": 4.6, "split_candida": True}
    prof.update(extra or {})
    layouts = tmp_path / "layouts.json"
    layouts.write_text(json.dumps({"synthetic": prof}))
    return table, roster, aliases, layouts


def test_split_profile_maps_each_species_to_its_own_target():
    m = target_map("A01", {"split_candida": True})
    assert m["Candida albicans"] == "C. albicans" and m["Candida auris"] == "C. auris" and m["MRSA"] == "MRSA"
    assert target_map("A01", {"split_candida": False})["Candida auris"] == "Candida sp."
    assert target_map("A06", {"split_candida": True})["Candida auris"] == "Candida sp."   # only A01 splits


def test_a01_plot_has_one_target_per_species(tmp_path):
    table, roster, aliases, layouts = _inputs(tmp_path)
    plot = prepare(table, roster, aliases, "A01", "synthetic", layouts=layouts)["plot"]
    assert {r["target"] for r in plot} == {"C. albicans", "C. auris", "C. albicans or C. auris (not recorded)", "MRSA"}


def test_drop_targets_leave_a_panel_out(tmp_path):
    table, roster, aliases, layouts = _inputs(tmp_path, {"a01_drop_targets": ["C. albicans or C. auris (not recorded)"]})
    plot = prepare(table, roster, aliases, "A01", "synthetic", layouts=layouts)["plot"]
    assert {r["target"] for r in plot} == {"C. albicans", "C. auris", "MRSA"}


def test_moss_profile_uses_the_ruled_label_and_splits():
    prof = layout_profile("moss")
    assert prof["unassigned_label"] == "No 16S genus on record" and prof["split_candida"] is True
