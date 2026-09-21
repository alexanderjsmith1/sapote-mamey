"""v9.7.436 (Amber): the placement-panel input builder must bin the country "Georgia" to Europe.

Ruling: Georgia -> Europe, 2026-09-14, NCBI BioSample convention (a bare `geo_loc_name` of "Georgia"
is the nation, not the US state). The engine already honours this in tools/_phylo_metadata.py
(_COUNTRY_TO_CONTINENT["Georgia"] == "Europe", pinned by test_normalize_geography_continent_v97431.py
and test_phylo_metadata_georgia_display_v97431.py). tools/build_placement_panel_inputs.py carried a
second, independent GEO_RULES table that put Georgia in Asia; this test pins the fix and guards the
two layers from drifting apart again. The US state ("USA: Georgia") must stay "US".

Drop into tests/. Fails on the .435 tool; passes with AMBER_436 georgia.diff applied.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_BUNDLE = Path(__file__).resolve().parents[1]           # tests/ -> bundle root
_TOOL = _BUNDLE / "tools" / "build_placement_panel_inputs.py"


def _mod():
    # the tool imports `_console` (tools/) and `mamey.*` (bundle root)
    for p in (str(_BUNDLE), str(_BUNDLE / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location("build_placement_panel_inputs_ambertest", _TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize("raw", ["Georgia: Poti", "Georgia"])
def test_georgia_country_bins_to_europe(raw):
    assert _mod().bin_geo(raw) == "Europe"


def test_us_state_georgia_stays_us():
    # the US state is not the country; the ^usa rule must still win
    assert _mod().bin_geo("USA: Georgia") == "US"


def test_ruling_did_not_move_its_asian_neighbours():
    # Armenia/Azerbaijan are not part of the Georgia ruling and stay in Asia
    m = _mod()
    assert m.bin_geo("Armenia") == "Asia"
    assert m.bin_geo("China: Shanghai") == "Asia"


def test_european_siblings_unchanged():
    m = _mod()
    for c in ("Germany", "Moldova", "Cyprus"):
        assert m.bin_geo(c) == "Europe"
