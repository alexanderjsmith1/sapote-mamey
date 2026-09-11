"""AQUARIUS_01: the new Low lead tier must survive every shipped consumer."""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

from mamey.rules import load_inventory_tier_policy
from mamey.scoring import (CORE_HOUSEKEEPING_INVENTORY_CLASSES,
                           HOUSEKEEPING_INVENTORY_CLASSES,
                           INVENTORY_AMBIGUOUS_REVIEW_TOKENS)
from mamey.strain_modeb import _display_lead_tier


ROOT = Path(__file__).resolve().parents[1]


def _cohort_module():
    path = ROOT / "tools" / "build_cohort_html.py"
    spec = importlib.util.spec_from_file_location("build_cohort_html_aquarius", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_registry_is_the_scoring_single_source_of_truth():
    policy = load_inventory_tier_policy()
    assert set(policy["core_housekeeping_classes"]) == set(CORE_HOUSEKEEPING_INVENTORY_CLASSES)
    assert set(policy["housekeeping_classes"]) == set(HOUSEKEEPING_INVENTORY_CLASSES)
    assert set(policy["ambiguous_review_tokens"]) == set(INVENTORY_AMBIGUOUS_REVIEW_TOKENS)
    assert policy["route_labels"] == {
        "specialized_below_medium": "Low",
        "allow_listed_below_medium": "Inventory",
        "unresolved_below_medium": "Inventory",
    }


def test_strain_modeb_keeps_low_separate_from_inventory():
    assert _display_lead_tier("low") == "Low"
    assert _display_lead_tier("Inventory") == "Inventory"
    assert _display_lead_tier("low") != _display_lead_tier("Inventory")


def test_cohort_html_counts_and_filters_low(tmp_path):
    module = _cohort_module()
    strain_dir = tmp_path / "AS-TEST"
    pkg = strain_dir / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({
        "strain_id": "AS-TEST", "taxonomy": "Streptomyces sp.",
        "source": "test", "package_status": "MAMEY_COMPLETE",
        "workflow_version": "test", "assembly": {},
    }), encoding="utf-8")
    fields = ["BGC_ID", "Lead_tier_auto", "Boundary", "Products", "AB_auto",
              "AF_auto", "Novelty_auto", "Node_ID", "antiSMASH_Region",
              "KCB_top", "CCTT_triggers"]
    rows = [
        {"BGC_ID": "BGC001", "Lead_tier_auto": "Low", "Boundary": "Interior",
         "Products": "NRPS", "AB_auto": "20", "AF_auto": "10", "Novelty_auto": "15",
         "Node_ID": "ctg1", "antiSMASH_Region": "region001", "KCB_top": "", "CCTT_triggers": ""},
        {"BGC_ID": "BGC002", "Lead_tier_auto": "Inventory", "Boundary": "Interior",
         "Products": "ectoine", "AB_auto": "5", "AF_auto": "4", "Novelty_auto": "3",
         "Node_ID": "ctg2", "antiSMASH_Region": "region002", "KCB_top": "", "CCTT_triggers": ""},
    ]
    with (pkg / "AS-TEST_4_triage_board.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    record = module.strain_record(strain_dir, set())
    assert record is not None
    assert record["tiers"]["Low"] == 1
    assert record["tiers"]["Inventory"] == 1
    assert sum(record["tiers"].values()) == record["raw_bgc"] == 2
    rendered = module.render([record], "test", None)
    assert "<option>Low</option>" in rendered
    assert ".lt-Low" in rendered


def test_public_docs_name_the_five_value_contract():
    docs = [
        ROOT / "docs" / "user_guides" / "comprehensive_glossary.md",
        ROOT / "docs" / "GUIDE" / "01_User_Manual.md",
        ROOT / "docs" / "GUIDE" / "02_Quick_Guide.md",
        ROOT / "docs" / "reference" / "02_Math_Reference_VolII.md",
        ROOT / "docs" / "reference" / "03_Plumbing_Reference.md",
        ROOT / "docs" / "WORKBOOK_SCHEMA.md",
    ]
    text = "\n".join(p.read_text(encoding="utf-8") for p in docs)
    for label in ("Exceptional", "High", "Medium", "Low", "Inventory"):
        assert label in text
    assert "else Inventory) is `max(AB, AF, novelty)`" not in text
    assert "Exceptional → High → Medium → Inventory" not in text


def test_root_quick_guide_is_explicitly_historical_superseded():
    legacy = ROOT / "docs" / "QUICK_GUIDE.md"
    text = legacy.read_text(encoding="utf-8")
    assert "<!-- SAPOTE_DOC_STATE: HISTORICAL_SUPERSEDED -->" in text
    assert "<!-- SAPOTE_SUPERSEDED_BY: ../CURRENT_DOCS_INDEX.md | GUIDE/02_Quick_Guide.md -->" in text
    assert "[Current Docs Index](../CURRENT_DOCS_INDEX.md)" in text
    assert "[canonical current Quick Guide](GUIDE/02_Quick_Guide.md)" in text
