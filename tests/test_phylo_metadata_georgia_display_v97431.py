"""v9.7.431: the deposited country value "Georgia" bins to Europe at the display layer.

Ruling: Georgia -> Europe, 2026-09-14, NCBI BioSample convention (a `geo_loc_name` of "Georgia"
is the nation, not the US state). Before this cut `_COUNTRY_TO_DISPLAY` had no "Georgia" key, so
`normalize_geography()`'s `.get(country, raw)` fell back to the whole raw string and a Georgian
deposit rendered as "Georgia: Poti" in a figure strip whose other European deposits all read
"Europe".

This pins the DISPLAY contract. The continent-bin contract (`normalize_geography_continent`) is
pinned separately in test_normalize_geography_continent_v97431.py, which must keep reporting the
COUNTRY name "Georgia" there -- the two layers answer different questions and this test exists so
a future edit cannot quietly collapse one into the other.
"""
import importlib.util
import pathlib

import pytest

_PATH = pathlib.Path(__file__).resolve().parent.parent / "tools" / "_phylo_metadata.py"


def _mod():
    spec = importlib.util.spec_from_file_location("_phylo_metadata_georgia", _PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("raw", ["Georgia: Poti", "Georgia"])
def test_georgia_displays_as_europe(raw):
    result = _mod().normalize_geography(raw)
    assert result["display_location"] == "Europe"
    assert result["raw"] == raw


def test_georgia_is_a_known_country():
    assert "Georgia" in _mod()._KNOWN_COUNTRIES


def test_european_siblings_are_unchanged():
    """The ruling aligns Georgia WITH its siblings; it must not have moved them."""
    m = _mod()
    for raw, expected in (("Austria: Vienna", "Europe"), ("United Kingdom", "Europe"),
                          ("USA: Wisconsin", "US"), ("Canada: Ontario", "Canada")):
        assert m.normalize_geography(raw)["display_location"] == expected


def test_continent_layer_still_reports_the_country_not_the_continent():
    """Regression guard: the display ruling must not break the continent function's country field."""
    result = _mod().normalize_geography_continent("Georgia: Poti")
    assert result["display_country"] == "Georgia"
    assert result["display_continent"] == "Europe"
