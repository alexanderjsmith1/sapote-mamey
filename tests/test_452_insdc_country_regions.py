"""Deposited INSDC countries on 16S reference records get a display region; unclear places still stop the palette gate."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _phylo_metadata as m  # noqa: E402

PALETTE = ROOT / "tools" / "phylo_display_palette.tsv"


def _geography_palette():
    return {r["value"] for r in csv.DictReader(open(PALETTE), delimiter="\t") if r["field"] == "geography"}


def test_every_mapped_country_has_a_palette_colour():
    pal = _geography_palette()
    for region, countries in m._INSDC_REGION.items():
        assert region in pal
        for c in countries:
            assert m.normalize_geography(c)["display_location"] == region
            assert m.normalize_geography(f"{c}: some locality")["display_location"] == region
            assert m.normalize_geography_continent(c)["display_continent"] == region


def test_examples_from_reference_records():
    assert m.normalize_geography("Kenya")["display_location"] == "Africa"
    assert m.normalize_geography("Panama: Barro Colorado Island")["display_location"] == "North America"
    assert m.normalize_geography("Czechia")["display_location"] == "Europe"
    assert m.normalize_geography("Papua New Guinea")["display_location"] == "Oceania"


def test_named_ocean_with_a_locality_keeps_the_ocean():
    assert m.normalize_geography("Pacific Ocean: off Hawaii")["display_location"] == "Pacific Ocean"
    assert m.normalize_geography("Atlantic Ocean")["display_location"] == "Atlantic Ocean"


def test_unclear_places_stay_unmapped_for_a_ruling():
    for c in ("Armenia", "Azerbaijan", "Cyprus", "Kazakhstan", "French Southern and Antarctic Lands", "Baltic Sea"):
        assert m.normalize_geography(c)["display_location"] == c
        assert c not in _geography_palette()


def test_earlier_rulings_unchanged():
    assert m.normalize_geography("Russia")["display_location"] == "Russia"
    assert m.strip_geography("Russia")["display_location"] == "Europe"
    assert m.normalize_geography("Turkey")["display_location"] == "Asia"
    assert m.normalize_geography("Georgia: Poti")["display_location"] == "Europe"
    assert m.normalize_geography("USA")["display_location"] == "US"
    assert m.normalize_geography("Canada")["display_location"] == "Canada"


def test_insdc_missing_value_terms_are_not_places():
    for g in ("missing: control sample", "missing: lab stock", "not determined", "Not collected", "missing"):
        assert m.normalize_geography(g)["display_location"] == ""
        assert m.normalize_geography(g)["state"] == "NOT_RECORDED"
