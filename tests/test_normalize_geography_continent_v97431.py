"""claude-alex-2026-40 — fix for normalize_geography_continent() resolving the wrong field.

Purple's pending PURPLE_431_phylo_metadata_georgia_continent_PATCH.py stages
normalize_geography_continent() reusing normalize_geography()'s own `display_location`, which is
already continent-collapsed for most known countries via `_COUNTRY_TO_DISPLAY`. Looking up
`_COUNTRY_TO_CONTINENT` by that already-collapsed value misses for nearly every country (21/22,
all but Russia). This file pins the corrected behavior: the function must resolve the matched
COUNTRY NAME independently (via `_country_name()`), not reuse `display_location`.

Hermetic: loads the tool by path, calls pure functions, no network, no I/O.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "_phylo_metadata.py"


def _mod():
    if not TOOL.exists():
        pytest.skip(f"tool not present at {TOOL}")
    spec = importlib.util.spec_from_file_location("_c26_40_431_under_test", TOOL)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


# (input, expected display_country, expected display_continent) for every country already in
# _COUNTRY_TO_DISPLAY before this patch — the exact set that was broken by reusing display_location.
ALREADY_COLLAPSING_COUNTRIES = [
    ("USA: Wisconsin", "USA", "North America"),
    ("Canada: Ontario", "Canada", "North America"),
    ("Mexico: Oaxaca", "Mexico", "North America"),
    ("Brazil: Bahia", "Brazil", "South America"),
    ("Austria: Vienna", "Austria", "Europe"),
    ("Finland: Helsinki", "Finland", "Europe"),
    ("Spain: Madrid", "Spain", "Europe"),
    ("United Kingdom", "United Kingdom", "Europe"),
    ("Germany: Berlin", "Germany", "Europe"),
    ("France: Paris", "France", "Europe"),
    ("China: Yunnan", "China", "Asia"),
    ("Japan: Okinawa", "Japan", "Asia"),
    ("Pakistan: Sindh", "Pakistan", "Asia"),
    ("South Korea", "South Korea", "Asia"),
    ("Taiwan: Taipei", "Taiwan", "Asia"),
    ("Vietnam: Hanoi", "Vietnam", "Asia"),
    ("India: Kerala", "India", "Asia"),
    ("Mongolia: Ulaanbaatar", "Mongolia", "Asia"),
    ("South Africa: Cape Town", "South Africa", "Africa"),
    ("Namibia: Windhoek", "Namibia", "Africa"),
    ("Australia: Queensland", "Australia", "Oceania"),
]


@pytest.mark.parametrize("raw,expected_country,expected_continent", ALREADY_COLLAPSING_COUNTRIES)
def test_country_and_continent_both_resolve_for_display_collapsing_countries(
    raw, expected_country, expected_continent
):
    """The regression this card fixes: any country with a _COUNTRY_TO_DISPLAY entry must still
    report its OWN name in display_country and the right continent in display_continent, not a
    miss caused by the continent table being queried with an already-collapsed value."""
    m = _mod()
    result = m.normalize_geography_continent(raw)
    assert result["display_country"] == expected_country
    assert result["display_continent"] == expected_continent


def test_russia_direct_form_resolves_country_and_continent():
    """Russia has no _COUNTRY_TO_DISPLAY entry (pre-existing gap, unrelated to this patch) but is
    a direct (no-colon) input, so display_location already equals 'Russia' — must still resolve."""
    m = _mod()
    result = m.normalize_geography_continent("Russia")
    assert result["display_country"] == "Russia"
    assert result["display_continent"] == "Europe"


def test_unrecognized_location_yields_empty_continent_not_a_crash():
    m = _mod()
    result = m.normalize_geography_continent("Atlantis: Deep Trench")
    assert result["display_continent"] == ""
    assert result["raw"] == "Atlantis: Deep Trench"


def test_not_recorded_input_yields_empty_everything_not_a_crash():
    m = _mod()
    result = m.normalize_geography_continent(None)
    assert result["display_continent"] == ""
    assert result["raw"] == ""


def test_named_ocean_yields_empty_continent_not_a_crash():
    """Named oceans are AS_RECORDED, not a country -- must not raise, continent stays empty."""
    m = _mod()
    result = m.normalize_geography_continent("Pacific Ocean")
    assert result["display_continent"] == ""
    assert result["display_country"] == "Pacific Ocean"


@pytest.mark.parametrize("raw", ["Georgia: Poti", "Georgia"])
def test_georgia_resolves_once_part_a_of_purple_patch_is_also_applied(raw):
    """Only meaningful once Purple's Part A (Georgia -> _KNOWN_COUNTRIES) has also landed; skips
    cleanly against this patch applied alone so it does not falsely fail out of patch order."""
    m = _mod()
    if "Georgia" not in getattr(m, "_KNOWN_COUNTRIES", set()):
        pytest.skip("Purple's Part A (_KNOWN_COUNTRIES += Georgia) not applied in this tree yet")
    result = m.normalize_geography_continent(raw)
    assert result["display_country"] == "Georgia"
    # Alex ruled "Europe" 2026-09-14 (NCBI BioSample convention).
    assert result["display_continent"] == "Europe"


def test_does_not_change_normalize_geography_own_contract():
    """This patch must not alter normalize_geography()'s existing return values."""
    m = _mod()
    assert m.normalize_geography("United Kingdom") == {
        "raw": "United Kingdom", "display_location": "Europe", "state": "REGION_NORMALIZED",
    }
    assert m.normalize_geography("USA: Wisconsin") == {
        "raw": "USA: Wisconsin", "display_location": "US", "state": "COUNTRY_PREFIX",
    }
