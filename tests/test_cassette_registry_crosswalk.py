"""v9.7.86 D1: cassette-family -> registry-id crosswalk is complete and correct.

Guards against the known mis-map: a name-token join sends tomm_azole_ripp to the
T43-IDC indolocarbazole marker (MMK-CCTT-011) on the 'carb-azole' substring. The
explicit CASSETTE_REGISTRY_MAP must resolve it to MMC-011 instead.
"""
from __future__ import annotations
import json, pathlib
import pytest

from mamey.source_scans import CASSETTE_PATTERNS, CASSETTE_REGISTRY_MAP


def _registry():
    p = pathlib.Path(__file__).resolve().parents[1] / "bundle_support/registry_inventory_v1.9.4.json"
    d = json.load(open(p))
    lst = d if isinstance(d, list) else d.get("entries", d.get("inventory", []))
    return {e["id"]: e for e in lst if isinstance(e, dict) and "id" in e}


def test_every_cassette_family_has_a_map_entry():
    assert set(CASSETTE_REGISTRY_MAP) == set(CASSETTE_PATTERNS), \
        "every CASSETTE_PATTERNS family must have a registry-id mapping"


def test_crosswalk_resolves_to_real_mmc_entries():
    reg = _registry()
    for family, mmc_id in CASSETTE_REGISTRY_MAP.items():
        assert mmc_id.startswith("MMC-"), f"{family} -> {mmc_id} is not an MMC id"
        assert mmc_id in reg, f"{family} -> {mmc_id} is not in the registry"


def test_tomm_azole_ripp_maps_to_mmc_011_not_indolocarbazole():
    # the headline mis-map guard
    assert CASSETTE_REGISTRY_MAP["tomm_azole_ripp"] == "MMC-011"
    reg = _registry()
    assert "tomm" in reg["MMC-011"]["name"].lower() or "azole" in reg["MMC-011"]["name"].lower()
    # and it must NOT be the indolocarbazole CCTT marker
    assert CASSETTE_REGISTRY_MAP["tomm_azole_ripp"] != "MMK-CCTT-011"


def test_enriched_mmc_entries_have_distinct_claim_safety():
    # the enrichment replaced boilerplate claim_safety with family-specific lines
    reg = _registry()
    safeties = [reg[m]["claim_safety"] for m in CASSETTE_REGISTRY_MAP.values()
                if reg[m].get("claim_safety")]
    assert len(set(safeties)) >= 12, "enriched MMC claim_safety lines should be largely distinct"
