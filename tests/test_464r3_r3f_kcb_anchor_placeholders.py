"""A placeholder KCB anchor is not a comparator match, in every tool that credits one.

`build_priority_leads.score`, the `build_figures` priority panel and the `tier_of` labels in
`generate_bgc_atlas` and `build_subset_panel` share one rule (`kcb_anchor_named`): blank,
`mamey.missing_values` placeholders, UNRESOLVED (and "UNRESOLVED (...)"), dashes, "?",
"unknown", "N.A.", "n.t.", and a `;`/`,` list of only those name no product. A numeric cell is
not a match and does not crash. Synthetic rows only.
"""
import importlib.util
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def load(rel):
    spec = importlib.util.spec_from_file_location(rel.replace("/", "_") + "_464r3f", ROOT / rel)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BPL = load("tools/build_priority_leads.py")
PLACEHOLDERS = ["", "UNRESOLVED", " unresolved ", "UNRESOLVED (no hit)", "unresolved;", "NA;NA",
                "UNRESOLVED; UNRESOLVED", "-;-", "—", "–", "?", "unknown", "N.A.", "n.t.",
                "nan", "None", None, float("nan"), 0, 5, 2.5]


def _row(anchor):
    return {"ModeB_Status": "", "SARP_support": "", "Regulators": "DasR", "KCB_anchor": anchor,
            "Tier": "1", "signals": ""}


@pytest.mark.parametrize("anchor", PLACEHOLDERS)
def test_placeholder_anchor_earns_no_bonus_and_no_class_c(anchor):
    _score, axes = BPL.score(_row(anchor))
    assert "KCB" not in axes
    assert BPL.confidence_class(_row(anchor), axes) == ""


@pytest.mark.parametrize("anchor", ["nystatin", "NA; nystatin", "UNRESOLVED, candicidin"])
def test_a_named_product_is_still_credited(anchor):
    _score, axes = BPL.score(_row(anchor))
    assert "KCB" in axes and BPL.confidence_class(_row(anchor), axes) == "C"


def test_figure_panel_credits_only_named_or_scored_anchors(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Priority_Leads"
    ws.append(["confidence", "strain", "BGC", "products", "ModeB_class", "regulators", "KCB_anchor", "tier", "evidence"])
    for anchor, evidence in [("UNRESOLVED", ""), ("NA", ""), ("-", ""), ("nystatin", ""),
                             ("nystatin", "ModeB:CONFIRM+SARP"), ("NA", "ModeB:CONFIRM+SARP+KCB")]:
        ws.append(["A", "X1", "r1", "nrps", "c", "SARP", anchor, "1", evidence])
    path = tmp_path / "wb.xlsx"
    wb.save(path)
    rows, _cols = load("tools/build_figures.py").data_priority(str(path))
    assert [r["KCB"] for r in rows] == [0, 0, 0, 1, 0, 1]


@pytest.mark.parametrize("rel", ["tools/generate_bgc_atlas.py", "tools/build_subset_panel.py"])
def test_atlas_and_panel_label_placeholder_anchors_candidate_novel(rel):
    module = load(rel)
    for anchor in ["UNRESOLVED", "NA", "-", "none", "n/a", "?", "NA;NA"]:
        assert module.tier_of({"closest_kcb_product": anchor, "closest_mibig": "BGC0000001"}, "") == "Candidate-novel"
    assert module.tier_of({"closest_kcb_product": "nystatin", "closest_mibig": "BGC0000001"}, "") == "KCB-anchored"
